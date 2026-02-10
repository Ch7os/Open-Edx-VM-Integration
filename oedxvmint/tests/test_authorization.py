from types import SimpleNamespace

from oedxvmint.djangoapp.services.auth import is_staff


def test_staff_authorized():
    assert is_staff(SimpleNamespace(is_staff=True, is_superuser=False))


def test_learner_not_staff():
    assert not is_staff(SimpleNamespace(is_staff=False, is_superuser=False))
