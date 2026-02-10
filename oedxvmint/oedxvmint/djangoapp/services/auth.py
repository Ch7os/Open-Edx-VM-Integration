"""Authorization helpers."""


def is_staff(user):
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
