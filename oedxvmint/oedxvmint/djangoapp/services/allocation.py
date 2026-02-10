"""Allocation key and team-scope helpers."""


def build_allocation_key(mode, course_id, block_id, user_id=None, team_id=None):
    if mode == "course":
        return f"course:{course_id}:user:{user_id}"
    if mode == "team":
        if not team_id:
            raise ValueError("team_id required for team mode")
        return f"team:{course_id}:block:{block_id}:team:{team_id}"
    return f"unit:{course_id}:block:{block_id}:user:{user_id}"
