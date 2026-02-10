"""Pure helpers for network resource bookkeeping."""


def pick_portgroup_from_pool(pool, used):
    for portgroup in pool:
        if portgroup not in used:
            return portgroup
    raise RuntimeError("No free isolated port groups in pool")


def build_ephemeral_portgroup_name(prefix, allocation_key):
    return f"{prefix}-{allocation_key[-24:].replace(':', '-')}"
