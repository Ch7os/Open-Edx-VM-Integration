"""Simple lab state transitions."""

ALLOWED = {
    "provisioning": {"running", "error", "deleting"},
    "running": {"stopped", "error", "expired", "deleting"},
    "stopped": {"running", "expired", "deleting"},
    "error": {"provisioning", "deleting"},
    "expired": {"deleting"},
    "deleting": set(),
}


def can_transition(current, target):
    return target in ALLOWED.get(current, set())
