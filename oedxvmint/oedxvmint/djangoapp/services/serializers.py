"""Pure serializer helpers for VM visibility rules."""


def vm_view_payload(role, state, ips, creds_visible=False, username=None, password=None):
    show_creds = bool(role == "workstation" and creds_visible)
    return {
        "role": role,
        "state": state,
        "ips": ips or [],
        "creds_visible": show_creds,
        "username": username if show_creds else None,
        "password": password if show_creds else None,
    }
