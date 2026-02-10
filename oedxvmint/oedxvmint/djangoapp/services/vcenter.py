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
        self._session_id = None
        
        # Authenticate on init if not in stub mode
        if not self.stub and self.base_url:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with vCenter REST API and store session ID."""
        username = self.cfg.get("VCENTER_USERNAME")
        password = self.cfg.get("VCENTER_PASSWORD")
        
        if not username or not password:
            logger.warning("vCenter credentials not configured - authentication will fail")
            return
        
        try:
            # vCenter REST API session creation
            auth_url = f"{self.base_url}/api/session"
            response = self.session.post(
                auth_url,
                auth=(username, password),
                timeout=30
            )
            response.raise_for_status()
            
            # Extract session ID from response
            self._session_id = response.json().get("value")
            
            # Set session ID in headers for subsequent requests
            if self._session_id:
                self.session.headers.update({
                    "vmware-api-session-id": self._session_id
                })
                logger.info("Successfully authenticated with vCenter")
            else:
                logger.error("Failed to obtain session ID from vCenter")
        except Exception as exc:  # noqa: BLE001
            logger.error("vCenter authentication failed: %s", exc)
            raise

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
        
        # Apply network allocation to VM
        if network_allocation and network_allocation.get("portgroup_name"):
            portgroup = network_allocation.get("portgroup_name")
            payload["nics"] = [{
                "network": portgroup,
                "type": "VMXNET3",  # Default to VMXNET3, can be made configurable
            }]
            logger.info(
                "Applying network allocation to VM clone",
                extra={"vm_name": vm_name, "portgroup": portgroup, "strategy": network_allocation.get("strategy")}
            )
        
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
