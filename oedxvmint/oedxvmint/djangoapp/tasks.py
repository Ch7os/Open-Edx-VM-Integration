"""Celery tasks for vCenter operations."""

from celery import shared_task
from django.utils import timezone

from .models import LabInstance
from .services.lab_service import LabService


@shared_task(bind=True)
def provision_lab(self, instance_id, user_id=None):
    service = LabService()
    instance = LabInstance.objects.select_related("definition").get(id=instance_id)
    service.provision_topology(instance)
    service.log_action(instance, user_id, "start", result="success", details={"task_id": self.request.id})


@shared_task(bind=True)
def stop_lab(self, instance_id, user_id=None):
    service = LabService()
    instance = LabInstance.objects.get(id=instance_id)
    service.stop_instance(instance)
    service.log_action(instance, user_id, "stop", result="success", details={"task_id": self.request.id})


@shared_task(bind=True)
def reset_lab(self, instance_id, user_id=None):
    service = LabService()
    instance = LabInstance.objects.select_related("definition").get(id=instance_id)
    service.reset_instance(instance)
    service.log_action(instance, user_id, "reset", result="success", details={"task_id": self.request.id})


@shared_task(bind=True)
def delete_lab(self, instance_id, user_id=None):
    service = LabService()
    instance = LabInstance.objects.select_related("definition").get(id=instance_id)
    service.delete_instance(instance)


@shared_task
def cleanup_expired_labs():
    service = LabService()
    for instance in LabInstance.objects.filter(expires_at__lte=timezone.now()):
        service.log_action(instance, None, "expire", result="accepted")
        service.delete_instance(instance)
