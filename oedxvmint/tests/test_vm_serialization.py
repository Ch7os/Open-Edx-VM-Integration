from oedxvmint.djangoapp.services.serializers import vm_view_payload


def test_target_never_shows_credentials():
    payload = vm_view_payload("target", "running", ["10.0.0.2"], creds_visible=True, username="admin", password="secret")
    assert payload["creds_visible"] is False
    assert payload["username"] is None
    assert payload["password"] is None


def test_workstation_can_show_credentials():
    payload = vm_view_payload("workstation", "running", ["10.0.0.3"], creds_visible=True, username="student", password="pw")
    assert payload["creds_visible"] is True
    assert payload["username"] == "student"
