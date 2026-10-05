import json

import pytest

from gymcore import workouts as core
from mcp_server.auth import AuthContext, set_current_auth
from mcp_server.tools import register_all_tools


class FakeMCP:
    """Collects the registered tool functions so they can be called directly."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function
        return register


@pytest.fixture
def tools(conn):
    mcp = FakeMCP()
    register_all_tools(mcp, conn)
    return mcp.tools


def test_tools_only_touch_the_callers_rows(tools, conn, workout):
    entry = workout["entries"][0]
    set_current_auth(AuthContext(user_id=2, scope="readwrite"))
    for name, args in [
        ("log_set", dict(workout_exercise_id=entry, set_number=1, reps=5)),
        ("log_exercise", dict(workout_exercise_id=entry, actual_sets=1)),
        ("update_workout_exercise", dict(workout_exercise_id=entry, target_sets=9)),
        ("remove_workout_exercise", dict(workout_exercise_id=entry)),
        ("add_workout_exercise", dict(workout_id=workout["id"], exercise_id=1)),
        ("complete_workout", dict(workout_id=workout["id"])),
        ("delete_workout", dict(workout_id=workout["id"])),
        ("get_workout", dict(workout_id=workout["id"])),
    ]:
        with pytest.raises(ValueError):
            tools[name](**args)
    assert conn.execute("SELECT COUNT(*) FROM workout_exercises").fetchone()[0] == 4


def test_read_scope_cannot_write(tools, workout):
    set_current_auth(AuthContext(user_id=1, scope="read"))
    with pytest.raises(PermissionError):
        tools["log_set"](workout_exercise_id=workout["entries"][0], set_number=1, reps=5)
    assert tools["get_workout"](workout_id=workout["id"])["name"] == "Push day"


def test_logging_through_tools_matches_the_web_model(tools, conn, workout):
    set_current_auth(AuthContext(user_id=1, scope="readwrite"))
    bench, squat = workout["entries"][:2]

    tools["log_set"](workout_exercise_id=bench, set_number=1, reps=10, weight=50)
    tools["log_set"](workout_exercise_id=bench, set_number=2, reps=8, weight=55)
    tools["log_exercise"](workout_exercise_id=squat, actual_sets=3, actual_reps=5, actual_weight=80)
    tools["log_exercise"](workout_exercise_id=squat, actual_weight=85)   # keeps 3 x 5
    tools["remove_set"](workout_exercise_id=bench, set_number=2)
    tools["complete_workout"](workout_id=workout["id"], duration_minutes=40)

    result = tools["get_workout"](workout_id=workout["id"])
    by_id = {e["id"]: e for e in result["exercises"]}
    assert [(s["reps"], s["weight"]) for s in by_id[bench]["sets"]] == [(10, 50.0)]
    assert [(s["reps"], s["weight"]) for s in by_id[squat]["sets"]] == [(5, 85.0)] * 3
    assert by_id[squat]["actual_sets"] == 3 and result["status"] == "completed"
    assert result["duration_minutes"] == 40 and result["started_at"]

    history = json.loads(tools["get_exercise_history"](exercise_id=2))
    assert len(history) == 1 and len(history[0]["sets"]) == 3


def test_template_tools_round_trip(tools, conn, workout):
    set_current_auth(AuthContext(user_id=1, scope="readwrite"))
    template = tools["create_template"](name="Plan", is_public=False)["template_id"]
    tools["add_workout_exercise"](workout_id=template, exercise_id=1, target_sets=3, target_reps=10)
    tools["update_template"](template_id=template, name="Plan B")
    created = tools["create_workout_from_template"](template_id=template, scheduled_date="2026-04-01")["workout_id"]
    assert [e["exercise_id"] for e in core.list_entries(conn, created)] == [1]

    set_current_auth(AuthContext(user_id=2, scope="readwrite"))
    with pytest.raises(ValueError):
        tools["create_workout_from_template"](template_id=template)
    with pytest.raises(ValueError):
        tools["delete_template"](template_id=template)

    set_current_auth(AuthContext(user_id=1, scope="readwrite"))
    tools["delete_template"](template_id=template)
    assert conn.execute("SELECT COUNT(*) FROM workouts WHERE id = ?", (template,)).fetchone()[0] == 0
