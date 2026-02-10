import pytest

from oedxvmint.djangoapp.services.network_bookkeeping import (
    build_ephemeral_portgroup_name,
    pick_portgroup_from_pool,
)


def test_pick_pool_network_success():
    assert pick_portgroup_from_pool(["pg1", "pg2"], {"pg1"}) == "pg2"


def test_pick_pool_network_exhausted():
    with pytest.raises(RuntimeError):
        pick_portgroup_from_pool(["pg1"], {"pg1"})


def test_ephemeral_name_format():
    name = build_ephemeral_portgroup_name("htb", "unit:course:block:abc:user:1")
    assert name.startswith("htb-")
