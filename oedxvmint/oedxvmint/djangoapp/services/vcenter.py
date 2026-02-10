"""REST-first vCenter client with stub fallback for local development."""

from __future__ import annotations

import logging
import time
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class VCenterClient:
    def __init__(self):
        self.cfg = settings.HTBLAB
        self.stub = self.cfg.get("VCENTER_STUB", False)
        self.base_url = self.cfg.get("VCENTER_URL", "").rstrip("/")
        self.session = requests.Session()
        self.session.verify = not self.cfg.get("VCENTER_INSECURE", True)

    def _rest(self, method, path, payload=None):
        if self.stub:
            return {"value": str(uuid.uuid4())}
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json() if response.text else {}

    def clone_vm(self, template_ref, vm_name, network_allocation, cpu=None, ram_mb=None):
        logger.info("Clone requested", extra={"vm_name": vm_name, "template_ref": template_ref})
        if self.stub:
            time.sleep(0.2)
            return {"vm": f"vm-{uuid.uuid4()}", "task": f"task-{uuid.uuid4()}"}
        payload = {
            "name": vm_name,
            "placement": {
                "folder": self.cfg.get("VCENTER_FOLDER"),
                "resource_pool": self.cfg.get("VCENTER_RESOURCE_POOL"),
                "datastore": self.cfg.get("VCENTER_DATASTORE"),
            },
            "source": template_ref,
            "guest_customization": {},
        }
        if cpu:
            payload["cpu"] = {"count": cpu}
        if ram_mb:
            payload["memory"] = {"size_MiB": ram_mb}
        data = self._rest("POST", "/api/vcenter/vm?action=clone", payload)
        return {"vm": data.get("value"), "task": data.get("task", "")}

    def power_on(self, vm_id):
        if self.stub:
            return {"task": f"task-{uuid.uuid4()}"}
        return self._rest("POST", f"/api/vcenter/vm/{vm_id}/power/start")

    def power_off(self, vm_id):
        if self.stub:
            return {"task": f"task-{uuid.uuid4()}"}
        return self._rest("POST", f"/api/vcenter/vm/{vm_id}/power/stop")

    def delete_vm(self, vm_id):
        if self.stub:
            return {"task": f"task-{uuid.uuid4()}"}
        return self._rest("DELETE", f"/api/vcenter/vm/{vm_id}")

    def revert_snapshot(self, vm_id, snapshot_ref):
        if self.stub:
            return {"task": f"task-{uuid.uuid4()}"}
        return self._rest("POST", f"/api/vcenter/vm/{vm_id}/snapshots/{snapshot_ref}?action=revert")

    def get_vm_ips(self, vm_id):
        if self.stub:
            return [f"10.10.{abs(hash(vm_id)) % 200}.10"]
        data = self._rest("GET", f"/api/vcenter/vm/{vm_id}/guest/networking/interfaces")
        ips = []
        for iface in data.get("value", []):
            ips.extend([ip.get("ip_address") for ip in iface.get("ip", {}).get("ip_addresses", []) if ip.get("ip_address")])
        return ips
