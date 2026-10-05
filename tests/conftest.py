import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from gymcore import workouts as core
from gymcore.db import connect
from gymcore.migrations import create_schema

PASSWORD = "correct horse"


def seed(conn):
    """Two users and a tiny exercise library."""
    conn.execute("INSERT INTO categories (id, name) VALUES (1, 'strength'), (2, 'stretching')")
    conn.execute("INSERT INTO muscles (id, name) VALUES (1, 'chest'), (2, 'quadriceps')")
    conn.executemany(
        "INSERT INTO exercises (id, name, category_id, description) VALUES (?, ?, ?, ?)",
        [(1, "Bench Press", 1, "Press the bar"), (2, "Squat", 1, "Squat down"),
         (3, "Hamstring Stretch", 2, "Stretch"), (4, "Push-Up", 1, "Push the floor")],
    )
    conn.execute("INSERT INTO exercise_primary_muscles VALUES (1, 1), (2, 2), (4, 1)")
    for user_id, name in ((1, "alice"), (2, "bob")):
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, name, f"{name}@example.com", generate_password_hash(PASSWORD)),
        )
    conn.commit()


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    conn = connect(path)
    create_schema(conn)
    conn.isolation_level = ""
    seed(conn)
    conn.close()
    return path


@pytest.fixture
def conn(db_path):
    connection = connect(db_path)
    yield connection
    connection.close()


@pytest.fixture
def app(db_path):
    app = create_app("testing")
    app.config["DATABASE_PATH"] = db_path
    return app


def login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    return client


@pytest.fixture
def alice(app):
    return login(app.test_client(), 1)


@pytest.fixture
def bob(app):
    return login(app.test_client(), 2)


@pytest.fixture
def workout(conn):
    """Alice's planned workout: bench 3x10@50, squat 3x5@80, stretch 30s, push-up."""
    with conn:
        workout_id = core.create_workout(conn, 1, "Push day", "2026-01-10")
        entries = [
            core.add_entry(conn, workout_id, 1, target_sets=3, target_reps=10, target_weight=50),
            core.add_entry(conn, workout_id, 2, target_sets=3, target_reps=5, target_weight=80),
            core.add_entry(conn, workout_id, 3, target_duration=30),
            core.add_entry(conn, workout_id, 4),
        ]
    return {"id": workout_id, "entries": entries}
