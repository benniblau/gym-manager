import re

import pytest
from flask_bcrypt import generate_password_hash as bcrypt_hash

from gymcore import sets as core_sets
from gymcore import workouts as core
from tests.conftest import PASSWORD, login


def entry_row(conn, entry_id):
    return conn.execute("SELECT * FROM workout_exercises WHERE id = ?", (entry_id,)).fetchone()


# ===== AUTH =====

def test_login_still_works_after_password_change(app, alice):
    response = alice.post("/auth/settings/update-password", data={
        "current_password": PASSWORD, "new_password": "new secret", "confirm_password": "new secret",
    })
    assert response.status_code == 302

    fresh = app.test_client()
    assert fresh.post("/auth/login", data={"username": "alice", "password": PASSWORD}).status_code == 200
    response = fresh.post("/auth/login", data={"username": "alice", "password": "new secret"})
    assert response.status_code == 302 and "/dashboard" in response.headers["Location"]


def test_login_accepts_legacy_bcrypt_hash(app, conn):
    with conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = 2",
                     (bcrypt_hash("old bcrypt").decode(),))
    response = app.test_client().post("/auth/login", data={"username": "bob", "password": "old bcrypt"})
    assert response.status_code == 302


def test_logout_requires_post(alice):
    assert alice.get("/auth/logout").status_code == 405
    assert alice.post("/auth/logout").status_code == 302
    assert alice.get("/dashboard").status_code == 302


def test_settings_never_echoes_strava_tokens(alice, conn):
    with conn:
        conn.execute(
            """INSERT INTO strava_connections (user_id, access_token, refresh_token, expires_at)
               VALUES (1, 'ACCESS-SECRET', 'REFRESH-SECRET', 1)""")
    page = alice.get("/auth/settings").get_data(as_text=True)
    assert "ACCESS-SECRET" not in page and "REFRESH-SECRET" not in page


def test_production_refuses_to_start_without_secret_key(monkeypatch):
    from app import create_app
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app("production")


# ===== CSRF =====

@pytest.fixture
def csrf_app(app):
    app.config["WTF_CSRF_ENABLED"] = True
    return app


def test_posts_without_csrf_token_are_rejected(csrf_app, workout, conn):
    client = login(csrf_app.test_client(), 1)
    assert client.post(f"/workouts/{workout['id']}/delete").status_code == 400
    response = client.post(f"/workouts/{workout['id']}/exercises/{workout['entries'][0]}/remove",
                           headers={"X-Requested-With": "fetch"})
    assert response.status_code == 400 and "error" in response.get_json()
    assert conn.execute("SELECT COUNT(*) FROM workouts").fetchone()[0] == 1

    token = re.search(r'name="csrf-token" content="([^"]+)"', client.get("/dashboard").get_data(as_text=True)).group(1)
    response = client.post(f"/workouts/{workout['id']}/exercises/{workout['entries'][0]}/remove",
                           headers={"X-CSRFToken": token})
    assert response.status_code == 200


# ===== OWNERSHIP =====

def test_cannot_reach_another_users_exercise_through_own_workout(bob, conn, workout):
    with conn:
        bobs = core.create_workout(conn, 2, "Bob's", "2026-01-10")
    target = workout["entries"][0]
    attempts = [
        (f"/workouts/{bobs}/exercises/{target}/remove", {}),
        (f"/workouts/{bobs}/exercises/{target}/update-targets", {"target_sets": 99}),
        (f"/workouts/{bobs}/exercises/{target}/duplicate", {}),
        (f"/workouts/{bobs}/exercises/{target}/reorder", {"direction": "down"}),
        (f"/workouts/{bobs}/exercises/{target}/remove-from-superset", {}),
        (f"/workouts/{bobs}/exercises/{target}/sets/1", {"reps": 1}),
        (f"/workouts/{workout['id']}/exercises/{target}/remove", {}),
        (f"/workouts/{workout['id']}/delete", {}),
        (f"/workouts/{workout['id']}/update-details", {"name": "pwned"}),
    ]
    for url, data in attempts:
        assert bob.post(url, data=data).status_code == 404, url
    assert bob.post(f"/workouts/{bobs}/exercises/set-order", json={"order": workout["entries"]}).status_code == 400
    assert bob.post(f"/workouts/{bobs}/superset/create",
                    data={"exercise_ids[]": workout["entries"][:2]}).status_code == 400

    row = entry_row(conn, target)
    assert row["target_sets"] == 3 and row["order_position"] == 1 and row["superset_group_id"] is None
    assert conn.execute("SELECT COUNT(*) FROM workout_exercises").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM workout_sets").fetchone()[0] == 0
    for page in ("", "/edit", "/log", "/export/tcx"):
        assert bob.get(f"/workouts/{workout['id']}{page}").status_code == 404


def test_private_template_is_not_usable_by_others(bob, conn, workout):
    with conn:
        template = core.save_as_template(conn, 1, workout["id"])
    assert bob.get(f"/templates/{template}/edit").status_code == 404
    assert bob.post(f"/templates/{template}/delete").status_code == 404
    bob.post(f"/templates/{template}/use", data={"scheduled_date": "2026-03-01"})
    assert conn.execute("SELECT COUNT(*) FROM workouts WHERE user_id = 2").fetchone()[0] == 0


# ===== EDITING =====

def test_exercise_changes_return_the_updated_list(alice, conn, workout):
    base = f"/workouts/{workout['id']}"
    data = alice.post(f"{base}/exercises/add", data={"exercise_id": 4, "target_sets": 2, "target_reps": 20}).get_json()
    assert data["success"] and data["count"] == 5 and "Push-Up" in data["html"]

    a, b = workout["entries"][:2]
    assert alice.post(f"{base}/superset/create", data={"exercise_ids[]": [a, b]}).get_json()["success"]
    assert entry_row(conn, a)["superset_group_id"] == entry_row(conn, b)["superset_group_id"] == 1

    alice.post(f"{base}/superset/1/update-reps", data={"target_reps": 4})
    assert entry_row(conn, a)["superset_target_reps"] == 4

    assert alice.post(f"{base}/exercises/add", data={"exercise_id": 9999}).status_code == 404
    assert alice.get(f"{base}/exercises/list").get_json()["count"] == 5


def test_update_details_derives_duration_and_validates(alice, conn, workout):
    url = f"/workouts/{workout['id']}/update-details"
    alice.post(url, data={"name": "Renamed", "notes": "n", "scheduled_date": "2026-01-11",
                          "started_at": "2026-01-11T10:00", "duration_minutes": "50", "completed_at": ""})
    row = conn.execute("SELECT * FROM workouts WHERE id = ?", (workout["id"],)).fetchone()
    assert (row["name"], row["scheduled_date"], row["duration_minutes"]) == ("Renamed", "2026-01-11", 50)
    assert row["completed_at"] == "2026-01-11T10:50:00"

    alice.post(url, data={"name": "", "notes": ""})
    alice.post(url, data={"name": "Bad", "started_at": "2026-01-11T12:00", "completed_at": "2026-01-11T11:00"})
    assert conn.execute("SELECT name FROM workouts WHERE id = ?", (workout["id"],)).fetchone()[0] == "Renamed"


def test_create_workout_and_template_forms(alice, conn):
    response = alice.post("/workouts/create", data={"name": "Legs", "scheduled_date": "2026-02-02", "scheduled_time": "18:30"})
    assert response.status_code == 302 and "/edit" in response.headers["Location"]
    row = conn.execute("SELECT * FROM workouts WHERE name = 'Legs'").fetchone()
    assert (row["scheduled_time"], row["is_template"]) == ("18:30", 0)

    response = alice.post("/workouts/create", data={"name": "Plan", "is_template": "on"})
    assert response.status_code == 302 and "/templates/" in response.headers["Location"]


# ===== LOGGING =====

def test_log_sets_then_finish_as_planned(alice, conn, workout):
    base = f"/workouts/{workout['id']}"
    bench, squat, stretch, pushup = workout["entries"]

    assert alice.post(f"{base}/exercises/{bench}/sets/1", json={"done": True, "reps": "10", "weight": "52.5"}).get_json()["success"]
    assert alice.post(f"{base}/exercises/{bench}/sets/2", json={"done": True, "reps": "8", "weight": "52.5", "duration": ""}).status_code == 200
    assert alice.post(f"{base}/exercises/{bench}/sets/2", json={"done": False}).status_code == 200
    assert alice.post(f"{base}/exercises/{bench}/sets/1", json={"done": True, "reps": "abc"}).status_code == 400

    status = conn.execute("SELECT status, started_at FROM workouts WHERE id = ?", (workout["id"],)).fetchone()
    assert status["status"] == "in_progress" and status["started_at"]

    assert alice.post(f"{base}/complete", data={"fill": "planned"}).status_code == 302
    sets = core_sets.sets_for(conn, workout["entries"])
    assert [(s["reps"], s["weight"]) for s in sets[bench]] == [(10, 52.5)]
    assert len(sets[squat]) == 3 and sets[stretch][0]["duration"] == 30 and sets[pushup] == []
    assert conn.execute("SELECT status FROM workouts WHERE id = ?", (workout["id"],)).fetchone()[0] == "completed"


def test_finishing_without_fill_invents_nothing(alice, conn, workout):
    alice.post(f"/workouts/{workout['id']}/complete", data={"fill": ""})
    assert conn.execute("SELECT COUNT(*) FROM workout_sets").fetchone()[0] == 0


def test_templates_cannot_be_logged(alice, conn, workout):
    with conn:
        template = core.save_as_template(conn, 1, workout["id"])
        entry = conn.execute("SELECT id FROM workout_exercises WHERE workout_id = ?", (template,)).fetchone()[0]
    assert alice.post(f"/workouts/{template}/exercises/{entry}/sets/1", json={"reps": 5}).status_code == 404
    assert alice.get(f"/workouts/{template}/log").status_code == 404


# ===== PAGES =====

def test_every_page_renders(alice, conn, workout):
    bench, squat, _, _ = workout["entries"]
    with conn:
        core.create_superset(conn, workout["id"], [bench, squat])
        core_sets.log_set(conn, bench, 1, reps=10, weight=50)
        template = core.save_as_template(conn, 1, workout["id"])
        done = core.create_from_template(conn, 1, template, "2026-01-02")
        core_sets.log_as_planned(conn, done)
        core.complete_workout(conn, done)

    pages = [
        "/dashboard", "/workouts/", "/workouts/create",
        f"/workouts/{workout['id']}", f"/workouts/{workout['id']}/edit", f"/workouts/{workout['id']}/log",
        f"/workouts/{done}", f"/workouts/{done}/log", f"/workouts/{done}/export/tcx",
        "/templates/", "/templates/?visibility=public&sort=usage_count", "/templates/create",
        f"/templates/{template}", f"/templates/{template}/edit", f"/templates/{template}/use",
        "/exercises/", "/exercises/?q=press&category=strength&muscle=chest", "/exercises/1", "/exercises/1/details",
        "/exercises/picker?q=s", "/auth/settings", "/auth/invitations", "/auth/invite",
        "/offline", "/sw.js", "/manifest.webmanifest", f"/strava/generate-text/{done}",
    ]
    for page in pages:
        assert alice.get(page).status_code == 200, page
    assert alice.get("/workouts/9999").status_code == 404
    assert alice.get("/exercises/9999").status_code == 404

    log_page = alice.get(f"/workouts/{workout['id']}/log").get_data(as_text=True)
    assert log_page.count('class="set-row ') == 3 + 3 + 1 + 1 and 'class="set-row done"' in log_page
    assert "Last time" in log_page  # the completed copy counts as previous performance


def test_dashboard_counts_exclude_templates(alice, conn, workout):
    with conn:
        core.save_as_template(conn, 1, workout["id"])
    page = alice.get("/dashboard").get_data(as_text=True)
    assert re.search(r'stat-value">1</div>\s*<div class="stat-label">All workouts', page)


def test_picker_searches_whole_library_with_filters(alice):
    data = alice.get("/exercises/picker?q=p").get_json()
    assert [e["name"] for e in data["exercises"]][:1] == ["Push-Up"]   # name-prefix matches first
    assert data["total"] == 2 and data["next_offset"] is None
    assert alice.get("/exercises/picker?muscle=quadriceps").get_json()["exercises"][0]["name"] == "Squat"
