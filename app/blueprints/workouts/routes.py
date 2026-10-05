from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, make_response
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date

from gymcore import sets as core_sets
from gymcore import workouts as core
from gymcore.db import parse_dt
from app.models import Workout, Exercise, StravaConnection, StravaUpload, get_db
from wtforms.validators import Optional

from app.blueprints.workouts.forms import WorkoutForm
from app.utils import nice_date, duration_text
from app.utils.tcx_export import generate_tcx_xml

workouts_bp = Blueprint('workouts', __name__)

PER_PAGE = 30


# ===== OWNERSHIP HELPERS =====
# Exercise routes are shared by workouts and templates (a template is a workout
# row), so they only require that the current user owns the parent.

def _owned(workout_id, is_template=None):
    """The current user's workout as a model object, or 404."""
    try:
        row = core.owned_workout(get_db(), current_user.id, workout_id, is_template)
    except core.NotFound:
        abort(404)
    return Workout(**dict(row))


def _owned_entry(workout_id, workout_exercise_id):
    """An exercise entry that belongs to this workout of the current user, or 404."""
    try:
        return core.owned_entry(get_db(), current_user.id, workout_exercise_id, workout_id=workout_id)
    except core.NotFound:
        abort(404)


def _edit_url(workout):
    endpoint = 'templates.edit' if workout.is_template else 'workouts.edit'
    key = 'template_id' if workout.is_template else 'workout_id'
    return url_for(endpoint, **{key: workout.id})


def _exercise_list(workout):
    """JSON for the edit page: the re-rendered exercise list after a change."""
    exercises = workout.get_exercises()
    return jsonify({
        'success': True,
        'count': len(exercises),
        'html': render_template('workouts/_exercise_list.html', exercises=exercises),
    })


def _share_text(workout, exercises):
    """Plain-text summary for the share sheet / clipboard."""
    lines = [nice_date(workout.scheduled_date)] if workout.scheduled_date else []
    if workout.duration_minutes:
        lines.append(f'Duration: {duration_text(workout.duration_minutes)}')
    lines.append('')
    for number, exercise in enumerate(exercises, start=1):
        details = exercise['sets_text'] or core_sets.describe_plan(exercise)
        lines.append(f"{number}. {exercise['exercise_name']}" + (f' - {details}' if details else ''))
    if workout.notes:
        lines += ['', workout.notes]
    return '\n'.join(lines)


# ===== WORKOUT PAGES =====

@workouts_bp.route('/')
@login_required
def list():
    """List the current user's workouts, newest first"""
    page = max(request.args.get('page', 1, type=int), 1)
    workouts = Workout.get_by_user(current_user.id, limit=PER_PAGE + 1, offset=(page - 1) * PER_PAGE)
    return render_template('workouts/list.html',
                           workouts=workouts[:PER_PAGE],
                           page=page,
                           has_next=len(workouts) > PER_PAGE,
                           today=date.today().isoformat())


@workouts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new workout"""
    form = WorkoutForm()
    is_template = request.form.get('is_template') == 'on'
    if is_template:
        # Templates have no schedule; the date inputs are disabled in the form
        form.scheduled_date.validators = [Optional()]

    if form.validate_on_submit():

        if is_template:
            template = Workout.create_template(
                user_id=current_user.id,
                name=form.name.data,
                notes=form.notes.data
            )
            flash(f'Template "{template.name}" created.', 'success')
            return redirect(url_for('templates.edit', template_id=template.id))

        duration_minutes = form.duration_minutes.data
        scheduled_time = form.scheduled_time.data
        scheduled_date = form.scheduled_date.data

        # Calculate started_at and completed_at if both time and duration provided
        started_at = None
        completed_at = None
        if scheduled_time and duration_minutes:
            started_at = datetime.combine(scheduled_date, scheduled_time)
            completed_at = started_at + timedelta(minutes=duration_minutes)

        workout = Workout.create(
            user_id=current_user.id,
            name=form.name.data,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time.strftime('%H:%M') if scheduled_time else None,
            duration_minutes=duration_minutes,
            started_at=started_at,
            completed_at=completed_at,
            notes=form.notes.data
        )
        return redirect(url_for('workouts.edit', workout_id=workout.id))

    templates = Workout.get_templates_by_user(current_user.id, limit=10)
    return render_template('workouts/create.html', form=form, today=date.today(), templates=templates)


@workouts_bp.route('/<int:workout_id>')
@login_required
def detail(workout_id):
    """View workout details"""
    workout = _owned(workout_id, is_template=False)
    exercises = workout.get_exercises()

    strava_connected = StravaConnection.is_connected(current_user.id)
    strava_upload = StravaUpload.get_by_workout_id(workout_id)
    last_upload_success = strava_upload is not None and strava_upload['upload_status'] == 'success'
    upload_failed = strava_upload is not None and strava_upload['upload_status'] == 'failed'
    last_strava_activity_id = strava_upload['strava_activity_id'] if last_upload_success else None

    return render_template('workouts/detail.html',
                           workout=workout,
                           exercises=exercises,
                           share_text=_share_text(workout, exercises),
                           logged_count=sum(1 for e in exercises if e['sets']),
                           strava_connected=strava_connected,
                           upload_failed=upload_failed,
                           strava_activity_id=last_strava_activity_id,
                           last_upload_success=last_upload_success)


@workouts_bp.route('/<int:workout_id>/edit')
@login_required
def edit(workout_id):
    """Edit workout (details, add/remove/reorder exercises)"""
    workout = _owned(workout_id, is_template=False)

    return render_template('workouts/edit.html',
                           workout=workout,
                           exercises=workout.get_exercises(),
                           categories=Exercise.get_all_categories(),
                           muscles=Exercise.get_all_muscles())


@workouts_bp.route('/<int:workout_id>/update-details', methods=['POST'])
@login_required
def update_details(workout_id):
    """Update name, notes and (for workouts) date and times in one go"""
    workout = _owned(workout_id)
    back = redirect(_edit_url(workout))

    name = request.form.get('name', '').strip()
    if not name:
        flash('The name cannot be empty.', 'danger')
        return back

    fields = {'name': name[:100], 'notes': request.form.get('notes', '').strip() or None}

    if not workout.is_template:
        started_raw = request.form.get('started_at', '').strip()
        completed_raw = request.form.get('completed_at', '').strip()
        duration_raw = request.form.get('duration_minutes', '').strip()

        start_dt = parse_dt(started_raw)
        end_dt = parse_dt(completed_raw)
        if (started_raw and not start_dt) or (completed_raw and not end_dt):
            flash('Invalid date/time format.', 'danger')
            return back

        duration_minutes = None
        if duration_raw:
            try:
                duration_minutes = int(duration_raw)
            except ValueError:
                flash('Invalid duration.', 'danger')
                return back

        # End time wins when all three are given; otherwise fill in the missing one
        if start_dt and end_dt:
            if start_dt >= end_dt:
                flash('Start time must be before end time.', 'danger')
                return back
            duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        elif start_dt and duration_minutes:
            end_dt = start_dt + timedelta(minutes=duration_minutes)

        fields.update(started_at=start_dt, completed_at=end_dt, duration_minutes=duration_minutes)

        scheduled_date = request.form.get('scheduled_date', '').strip()
        if scheduled_date:
            try:
                fields['scheduled_date'] = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date.', 'danger')
                return back
        scheduled_time = request.form.get('scheduled_time', '').strip()
        fields['scheduled_time'] = scheduled_time[:5] or None

    workout.update(**fields)
    flash('Saved.', 'success')
    return back


# ===== EXERCISE ENTRIES (AJAX, shared by workout and template edit pages) =====

@workouts_bp.route('/<int:workout_id>/exercises/list')
@login_required
def exercise_list(workout_id):
    """Current exercise list as an HTML fragment"""
    return _exercise_list(_owned(workout_id))


@workouts_bp.route('/<int:workout_id>/exercises/add', methods=['POST'])
@login_required
def add_exercise(workout_id):
    """Add exercise to workout"""
    workout = _owned(workout_id)

    exercise_id = request.form.get('exercise_id', type=int)
    if not exercise_id:
        return jsonify({'error': 'Exercise ID required'}), 400

    db = get_db()
    try:
        with db:
            core.add_entry(
                db, workout_id, exercise_id,
                target_sets=request.form.get('target_sets', type=int),
                target_reps=request.form.get('target_reps', type=int),
                target_weight=request.form.get('target_weight', type=float),
                target_duration=request.form.get('target_duration', type=int),
                notes=request.form.get('notes') or None,
            )
    except core.NotFound as e:
        return jsonify({'error': str(e)}), 404

    return _exercise_list(workout)


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/update-targets', methods=['POST'])
@login_required
def update_exercise_targets(workout_id, workout_exercise_id):
    """Update exercise target values"""
    workout = _owned(workout_id)
    _owned_entry(workout_id, workout_exercise_id)

    db = get_db()
    with db:
        core.update_entry(
            db, workout_exercise_id,
            target_sets=request.form.get('target_sets', type=int),
            target_reps=request.form.get('target_reps', type=int),
            target_weight=request.form.get('target_weight', type=float),
            target_duration=request.form.get('target_duration', type=int),
            notes=request.form.get('notes') or None,
        )

    return _exercise_list(workout)


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/duplicate', methods=['POST'])
@login_required
def duplicate_exercise(workout_id, workout_exercise_id):
    """Duplicate an exercise in the workout"""
    workout = _owned(workout_id)
    _owned_entry(workout_id, workout_exercise_id)

    db = get_db()
    with db:
        core.duplicate_entry(db, workout_exercise_id)

    return _exercise_list(workout)


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/remove', methods=['POST'])
@login_required
def remove_exercise(workout_id, workout_exercise_id):
    """Remove exercise from workout"""
    workout = _owned(workout_id)
    _owned_entry(workout_id, workout_exercise_id)

    db = get_db()
    with db:
        core.remove_entry(db, workout_exercise_id)

    return _exercise_list(workout)


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/reorder', methods=['POST'])
@login_required
def reorder_exercise(workout_id, workout_exercise_id):
    """Move an exercise (or its whole superset) up or down"""
    workout = _owned(workout_id)
    _owned_entry(workout_id, workout_exercise_id)

    direction = request.form.get('direction')
    if direction not in ['up', 'down']:
        return jsonify({'error': 'Invalid direction'}), 400

    db = get_db()
    with db:
        core.move_entry(db, workout_exercise_id, direction)

    return _exercise_list(workout)


@workouts_bp.route('/<int:workout_id>/exercises/set-order', methods=['POST'])
@login_required
def set_exercise_order(workout_id):
    """Bulk reorder all exercises via drag-and-drop"""
    workout = _owned(workout_id)

    data = request.get_json(silent=True)
    if not data or not data.get('order'):
        return jsonify({'error': 'No exercises provided'}), 400

    db = get_db()
    try:
        with db:
            core.set_order(db, workout_id, data['order'])
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return _exercise_list(workout)


# ===== SUPERSETS =====

@workouts_bp.route('/<int:workout_id>/superset/create', methods=['POST'])
@login_required
def create_superset(workout_id):
    """Create a superset from selected exercises"""
    workout = _owned(workout_id)

    exercise_ids = request.form.getlist('exercise_ids[]', type=int)
    if len(exercise_ids) < 2:
        return jsonify({'error': 'Select at least 2 exercises'}), 400

    db = get_db()
    try:
        with db:
            core.create_superset(db, workout_id, exercise_ids)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return _exercise_list(workout)


@workouts_bp.route('/<int:workout_id>/superset/<int:group_id>/dissolve', methods=['POST'])
@login_required
def dissolve_superset(workout_id, group_id):
    """Dissolve a superset entirely"""
    workout = _owned(workout_id)

    db = get_db()
    with db:
        core.dissolve_superset(db, workout_id, group_id)

    return _exercise_list(workout)


@workouts_bp.route('/<int:workout_id>/superset/<int:group_id>/update-reps', methods=['POST'])
@login_required
def update_superset_reps(workout_id, group_id):
    """Update superset planned or performed rounds"""
    workout = _owned(workout_id)

    data = request.get_json(silent=True) or request.form

    def rounds(name):
        try:
            return max(int(data[name]), 0)
        except (KeyError, TypeError, ValueError):
            return None

    db = get_db()
    with db:
        core.set_superset_reps(
            db, workout_id, group_id,
            target_reps=rounds('target_reps'),
            actual_reps=rounds('actual_reps'),
        )
        if not workout.is_template and rounds('actual_reps'):
            core.start_workout(db, workout_id)

    return jsonify({'success': True})


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/remove-from-superset', methods=['POST'])
@login_required
def remove_from_superset(workout_id, workout_exercise_id):
    """Remove exercise from its superset"""
    workout = _owned(workout_id)
    _owned_entry(workout_id, workout_exercise_id)

    db = get_db()
    with db:
        core.remove_from_superset(db, workout_exercise_id)

    return _exercise_list(workout)


# ===== LOGGING =====

def _prepare_log_rows(exercise, last):
    """Add what the logging page needs to an exercise dict.

    'rows' has one entry per set to show: logged sets as they were recorded,
    the rest pre-filled from the plan or, failing that, from last time.
    Nothing is saved until the user ticks a set.
    """
    logged = {s['set_number']: s for s in exercise['sets']}
    last_sets = last['sets'] if last else []

    def default(field, target, index):
        if exercise[target]:
            return exercise[target]
        if last_sets:
            return last_sets[min(index, len(last_sets) - 1)][field]
        return None

    count = max([exercise['target_sets'] or len(last_sets) or 1] + [n for n in logged])
    rows = []
    for number in range(1, count + 1):
        done = logged.get(number)
        rows.append({
            'number': number,
            'done': done is not None,
            'reps': done['reps'] if done else default('reps', 'target_reps', number - 1),
            'weight': done['weight'] if done else default('weight', 'target_weight', number - 1),
            'duration': done['duration'] if done else default('duration', 'target_duration', number - 1),
        })

    has = lambda field: any(row[field] for row in rows)
    exercise['rows'] = rows
    exercise['last'] = last
    # Timed exercises show only a time field; everything else shows reps and weight
    exercise['show_duration'] = has('duration')
    exercise['show_reps'] = has('reps') or not exercise['show_duration']
    exercise['show_weight'] = has('weight') or exercise['show_reps']


@workouts_bp.route('/<int:workout_id>/log')
@login_required
def log(workout_id):
    """Mobile logging interface: one set at a time"""
    workout = _owned(workout_id, is_template=False)
    exercises = workout.get_exercises()
    previous = core_sets.last_performance(
        get_db(), current_user.id, [e['exercise_id'] for e in exercises], exclude_workout_id=workout_id
    )
    for exercise in exercises:
        _prepare_log_rows(exercise, previous.get(exercise['exercise_id']))

    # Display blocks: a superset is one block of several exercises
    blocks, by_group = [], {}
    for exercise in exercises:
        group = exercise['superset_group_id']
        if group and group in by_group:
            by_group[group]['exercises'].append(exercise)
            continue
        block = {'superset_id': group, 'exercises': [exercise]}
        blocks.append(block)
        if group:
            by_group[group] = block

    return render_template('workouts/log.html', workout=workout, exercises=exercises, blocks=blocks)


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/sets/<int:set_number>', methods=['POST'])
@login_required
def log_set(workout_id, workout_exercise_id, set_number):
    """Record one performed set. Repeating the same request is harmless (offline retry)."""
    _owned(workout_id, is_template=False)
    _owned_entry(workout_id, workout_exercise_id)

    data = request.get_json(silent=True) or request.form
    db = get_db()
    try:
        with db:
            if data.get('done') in (False, 'false', '0', 0):
                core_sets.clear_set(db, workout_exercise_id, set_number)
            else:
                core_sets.log_set(
                    db, workout_exercise_id, set_number,
                    reps=data.get('reps'), weight=data.get('weight'), duration=data.get('duration'),
                )
                core.start_workout(db, workout_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid set values'}), 400

    return jsonify({'success': True})


@workouts_bp.route('/<int:workout_id>/start', methods=['POST'])
@login_required
def start(workout_id):
    """Mark workout as started"""
    _owned(workout_id, is_template=False)

    db = get_db()
    with db:
        core.start_workout(db, workout_id)

    return redirect(url_for('workouts.log', workout_id=workout_id))


@workouts_bp.route('/<int:workout_id>/complete', methods=['POST'])
@login_required
def complete(workout_id):
    """Mark workout as completed; optionally log untouched exercises as planned"""
    _owned(workout_id, is_template=False)

    db = get_db()
    with db:
        if request.form.get('fill') == 'planned':
            core_sets.log_as_planned(db, workout_id)
        core.complete_workout(db, workout_id)

    flash('Workout completed. Nice work!', 'success')
    return redirect(url_for('workouts.detail', workout_id=workout_id))


@workouts_bp.route('/<int:workout_id>/delete', methods=['POST'])
@login_required
def delete(workout_id):
    """Delete a workout"""
    workout = _owned(workout_id, is_template=False)
    workout.delete()

    flash('Workout deleted.', 'info')
    return redirect(url_for('workouts.list'))


@workouts_bp.route('/<int:workout_id>/save-as-template', methods=['POST'])
@login_required
def save_as_template(workout_id):
    """Create a template from an existing workout"""
    _owned(workout_id, is_template=False)

    db = get_db()
    with db:
        template_id = core.save_as_template(db, current_user.id, workout_id)

    flash('Template created from this workout.', 'success')
    return redirect(url_for('templates.detail', template_id=template_id))


@workouts_bp.route('/<int:workout_id>/export/tcx')
@login_required
def export_tcx(workout_id):
    """Export workout as TCX file"""
    workout = _owned(workout_id, is_template=False)

    if not workout.started_at or not workout.completed_at:
        flash('Please set start and end times before exporting to TCX', 'danger')
        return redirect(url_for('workouts.detail', workout_id=workout_id))

    exercises = workout.get_exercises()
    if not exercises:
        flash('Cannot export workout without exercises', 'warning')
        return redirect(url_for('workouts.detail', workout_id=workout_id))

    tcx_xml = generate_tcx_xml(workout, exercises)

    filename = ''.join(c if c.isalnum() or c in '-_' else '_' for c in workout.name)
    response = make_response(tcx_xml)
    response.headers['Content-Type'] = 'application/vnd.garmin.tcx+xml'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}_{workout.id}.tcx"'

    return response
