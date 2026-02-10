"""Network isolation strategies and DB bookkeeping."""

from __future__ import annotations

from django.db import transaction

from ..models import LabInstance
from .network_bookkeeping import build_ephemeral_portgroup_name, pick_portgroup_from_pool


def allocate_network(definition, allocation_key):
    strategy = definition.network_strategy
    cfg = definition.network_config or {}
    if strategy == "shared":
        return {"strategy": "shared", "portgroup_name": cfg.get("shared_portgroup", "shared-pg")}

    if strategy == "pool":
        pool = cfg.get("pool", [])
        used = {
            i.network_allocation.get("portgroup_name")
            for i in LabInstance.objects.exclude(network_allocation={})
            if i.network_allocation.get("strategy") == "pool"
        }
        portgroup = pick_portgroup_from_pool(pool, used)
        return {"strategy": "pool", "portgroup_name": portgroup}

    if strategy == "ephemeral":
        prefix = cfg.get("prefix", "htblab")
        dvs_id = cfg.get("dvs_id")
        name = build_ephemeral_portgroup_name(prefix, allocation_key)
        return {
            "strategy": "ephemeral",
            "portgroup_name": name,
            "dvs_id": dvs_id,
            "ephemeral_created": True,
        }

    raise ValueError(f"Unsupported network strategy: {strategy}")


@transaction.atomic
def release_network(lab_instance):
    payload = dict(lab_instance.network_allocation or {})
    payload["released"] = True
    lab_instance.network_allocation = payload
    lab_instance.save(update_fields=["network_allocation", "updated_at"])
    return payload
