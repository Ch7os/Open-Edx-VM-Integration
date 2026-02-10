from oedxvmint.djangoapp.services.state_machine import can_transition


def test_valid_transitions():
    assert can_transition("running", "stopped")
    assert can_transition("stopped", "running")


def test_invalid_transition():
    assert not can_transition("deleting", "running")
