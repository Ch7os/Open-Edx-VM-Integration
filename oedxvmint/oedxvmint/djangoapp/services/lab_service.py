"""Lab provisioning and control orchestration."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from ..models import LabActionLog, LabDefinition, LabInstance, VMInstance
from .allocation import build_allocation_key
from .network import allocate_network, release_network
from .serializers import vm_view_payload
from .state_machine import can_transition
from .vcenter import VCenterClient

logger = logging.getLogger(__name__)


class LabService:
    def __init__(self):
        self.vc = VCenterClient()

    def ensure_definition(self, *, course_id, block_id, xblock_config):
        return LabDefinition.objects.update_or_create(
            usage_key=block_id,
            defaults={
                "course_id": course_id,
                "block_id": block_id,
                "display_name": xblock_config.get("display_name", "HTB Lab"),
                "mode": xblock_config.get("mode", "unit"),
                "ttl_minutes": xblock_config.get("ttl_minutes", 120),
                "max_instances_per_scope": xblock_config.get("max_instances", 1),
                "cooldown_seconds": xblock_config.get("cooldown_seconds", 5),
                "allow_extend": xblock_config.get("allow_extend", True),
                "extend_minutes": xblock_config.get("extend_minutes", 30),
                "network_strategy": xblock_config.get("network_strategy", "pool"),
                "network_config": xblock_config.get("network_config", {}),
                "vm_specs": xblock_config.get("vm_specs", []),
                "author_hint_text": xblock_config.get("author_hint_text", ""),
            },
        )[0]

    def allocation_for(self, definition, user_id, team_id=None):
        return build_allocation_key(definition.mode, definition.course_id, definition.block_id, user_id=user_id, team_id=team_id)

    def serialize_instance(self, instance):
        return {
            "operation_id": None,
            "state": instance.state,
            "message": "ok",
            "instance_id": instance.id,
            "allocation_key": instance.allocation_key,
            "expires_at": instance.expires_at.isoformat() if instance.expires_at else None,
            "vms": [
                vm_view_payload(
                    role=vm.role,
                    state=vm.state,
                    ips=vm.ip_addresses,
                    creds_visible=vm.creds_visible,
                    username=vm.username,
                    password=vm.password,
                )
                for vm in instance.vms.all()
            ],
        }

    def check_rate_limit(self, instance, cooldown_seconds):
        if timezone.now() - instance.last_action_at < timedelta(seconds=cooldown_seconds):
            raise RuntimeError("Action rate limited")

    def lock_instance(self, instance, seconds=90):
        now = timezone.now()
        if instance.locked_until and instance.locked_until > now:
            raise RuntimeError("Instance is busy")
        instance.locked_until = now + timedelta(seconds=seconds)
        instance.last_action_at = now
        instance.save(update_fields=["locked_until", "last_action_at", "updated_at"])

    def unlock_instance(self, instance):
        instance.locked_until = None
        instance.save(update_fields=["locked_until", "updated_at"])

    def log_action(self, instance, user_id, action, result="accepted", details=None):
        return LabActionLog.objects.create(
            lab_instance=instance,
            user_id=user_id,
            action=action,
            result=result,
            details=details or {},
            completed_at=timezone.now() if result in {"success", "error"} else None,
        )

    def create_instance(self, definition, user_id, team_id=None):
        allocation_key = self.allocation_for(definition, user_id=user_id, team_id=team_id)
        existing = LabInstance.objects.filter(allocation_key=allocation_key).first()
        if existing:
            return existing, False

        network = allocate_network(definition, allocation_key)
        instance = LabInstance.objects.create(
            definition=definition,
            allocation_key=allocation_key,
            user_id=None if definition.mode == "team" else user_id,
            team_id=team_id if definition.mode == "team" else None,
            state="provisioning",
            expires_at=timezone.now() + timedelta(minutes=definition.ttl_minutes),
            network_allocation=network,
        )
        return instance, True

    def start_existing(self, instance):
        if not can_transition(instance.state, "running") and instance.state != "running":
            raise RuntimeError(f"Cannot start from state {instance.state}")
        for vm in instance.vms.all():
            self.vc.power_on(vm.vm_moid)
            vm.state = "running"
            vm.ip_addresses = self.vc.get_vm_ips(vm.vm_moid)
            vm.save(update_fields=["state", "ip_addresses", "updated_at"])
        instance.state = "running"
        instance.expires_at = timezone.now() + timedelta(minutes=instance.definition.ttl_minutes)
        instance.save(update_fields=["state", "expires_at", "updated_at"])

    def provision_topology(self, instance):
        definition = instance.definition
        for index, spec in enumerate(definition.vm_specs):
            name = spec.get("name") or f"{instance.allocation_key.split(':')[-1]}-{index}"
            clone = self.vc.clone_vm(
                template_ref=spec["template_ref"],
                vm_name=name,
                network_allocation=instance.network_allocation,
                cpu=spec.get("cpu"),
                ram_mb=spec.get("ram_mb"),
            )
            vm = VMInstance.objects.create(
                lab_instance=instance,
                role=spec.get("role", "target"),
                vm_moid=clone.get("vm", ""),
                vm_name=name,
                state="provisioning",
                creds_visible=bool(spec.get("role") == "workstation" and spec.get("show_credentials")),
                username=spec.get("username") if spec.get("show_credentials") else None,
                password=spec.get("password") if spec.get("show_credentials") else None,
                vcenter_task_ids=[clone.get("task")],
            )
            self.vc.power_on(vm.vm_moid)
            vm.state = "running"
            vm.ip_addresses = self.vc.get_vm_ips(vm.vm_moid)
            vm.save(update_fields=["state", "ip_addresses", "updated_at"])
        instance.state = "running"
        instance.expires_at = timezone.now() + timedelta(minutes=definition.ttl_minutes)
        instance.save(update_fields=["state", "expires_at", "updated_at"])

    def stop_instance(self, instance):
        for vm in instance.vms.all():
            self.vc.power_off(vm.vm_moid)
            vm.state = "stopped"
            vm.save(update_fields=["state", "updated_at"])
        instance.state = "stopped"
        instance.save(update_fields=["state", "updated_at"])

    def extend_instance(self, instance):
        if not instance.definition.allow_extend:
            raise RuntimeError("Extension is disabled for this lab")
        instance.expires_at = instance.expires_at + timedelta(minutes=instance.definition.extend_minutes)
        instance.save(update_fields=["expires_at", "updated_at"])

    def reset_instance(self, instance):
        for vm, spec in zip(instance.vms.all(), instance.definition.vm_specs):
            snapshot = spec.get("snapshot_ref")
            if snapshot:
                self.vc.revert_snapshot(vm.vm_moid, snapshot)
                self.vc.power_on(vm.vm_moid)
                vm.state = "running"
                vm.ip_addresses = self.vc.get_vm_ips(vm.vm_moid)
                vm.save(update_fields=["state", "ip_addresses", "updated_at"])
            else:
                self.vc.delete_vm(vm.vm_moid)
                vm.delete()
        if not instance.vms.exists():
            self.provision_topology(instance)

    def delete_instance(self, instance):
        instance.state = "deleting"
        instance.save(update_fields=["state", "updated_at"])
        for vm in list(instance.vms.all()):
            self.vc.power_off(vm.vm_moid)
            self.vc.delete_vm(vm.vm_moid)
            vm.delete()
        release_network(instance)
        instance.delete()
