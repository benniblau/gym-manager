"""Utility functions for the Gym Manager app"""


def get_exercem_url(exercise_name):
    """
    Generate exercem.us URL from exercise name.

    Example: "3/4 Sit-Up" -> "https://exercem.us/exercises/3.4_Sit-Up"

    Rules:
    - Replace "/" with "."
    - Replace spaces with "_"
    """
    if not exercise_name:
        return None

    # Replace "/" with "." and spaces with "_"
    url_name = exercise_name.replace("/", ".").replace(" ", "_")

    return f"https://exercem.us/exercises/{url_name}"


# ===== TEMPLATE HELPERS =====

from datetime import date, datetime

from markupsafe import Markup

from gymcore.db import parse_dt
from gymcore.sets import describe_plan, fmt_duration

STATUS_LABELS = {'planned': 'Planned', 'in_progress': 'In progress', 'completed': 'Completed'}


def csrf_field():
    """Hidden CSRF input for hand-written POST forms."""
    from flask_wtf.csrf import generate_csrf
    return Markup(f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">')


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = parse_dt(value)
    return parsed.date() if parsed else None


def nice_date(value):
    """'Today', 'Tomorrow', 'Yesterday' or 'Mon 19 Jan' (with the year if it isn't this one)."""
    day = _as_date(value)
    if not day:
        return ''
    today = date.today()
    delta = (day - today).days
    if delta in (-1, 0, 1):
        return ('Yesterday', 'Today', 'Tomorrow')[delta + 1]
    text = f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"
    return text if day.year == today.year else f"{text} {day.year}"


def nice_time(value):
    """'10:00' from '10:00', '10:00:00' or a full timestamp."""
    if not value:
        return ''
    text = str(value)
    if len(text) > 8:
        parsed = parse_dt(text)
        return parsed.strftime('%H:%M') if parsed else ''
    return text[:5]


def nice_datetime(value):
    parsed = parse_dt(value)
    return f"{nice_date(parsed)}, {parsed.strftime('%H:%M')}" if parsed else ''


def duration_text(minutes):
    """'1h 30m' / '45m' from a number of minutes."""
    if not minutes:
        return ''
    hours, rest = divmod(int(minutes), 60)
    if hours and rest:
        return f'{hours}h {rest}m'
    return f'{hours}h' if hours else f'{rest}m'


def status_label(status):
    return STATUS_LABELS.get(status, status or '')


def plan_text(entry):
    """Planned values of a workout exercise, e.g. '3 × 10 @ 50 kg'."""
    return describe_plan(entry)
