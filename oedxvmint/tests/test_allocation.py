from oedxvmint.djangoapp.services.allocation import build_allocation_key


def test_allocation_key_unit_mode():
    assert build_allocation_key("unit", "course-v1:A", "block@1", user_id=7) == "unit:course-v1:A:block:block@1:user:7"


def test_allocation_key_course_mode():
    assert build_allocation_key("course", "course-v1:A", "block@1", user_id=7) == "course:course-v1:A:user:7"


def test_allocation_key_team_mode():
    assert build_allocation_key("team", "course-v1:A", "block@1", user_id=7, team_id="red") == "team:course-v1:A:block:block@1:team:red"
