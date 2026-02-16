from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, make_response
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.models import Workout, WorkoutExercise, Exercise, StravaConnection, StravaUpload, get_db
from app.blueprints.workouts.forms import WorkoutForm
from app.utils.tcx_export import generate_tcx_xml

workouts_bp = Blueprint('workouts', __name__)


@workouts_bp.route('/')
@login_required
def list():
    """List all workouts for the current user"""
    all_workouts = Workout.get_by_user(current_user.id)
    # Exclude templates from workout list
    workouts = [w for w in all_workouts if not w.is_template]
    return render_template('workouts/list.html', workouts=workouts)


@workouts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new workout"""
    form = WorkoutForm()

    if form.validate_on_submit():
        is_template = request.form.get('is_template') == 'on'

        if is_template:
            # Create as template
            template = Workout.create_template(
                user_id=current_user.id,
                name=form.name.data,
                notes=form.notes.data
            )
            flash(f'Template "{template.name}" created successfully!', 'success')
            return redirect(url_for('templates.edit', template_id=template.id))
        else:
            # Create regular workout
            duration_minutes = form.duration_minutes.data
            scheduled_time = form.scheduled_time.data
            scheduled_date = form.scheduled_date.data

            # Calculate started_at and completed_at if both time and duration provided
            started_at = None
            completed_at = None
            if scheduled_time and duration_minutes:
                try:
                    started_at = datetime.combine(scheduled_date, datetime.strptime(scheduled_time, '%H:%M').time())
                    completed_at = started_at + timedelta(minutes=duration_minutes)
                except (ValueError, TypeError):
                    pass

            workout = Workout.create(
                user_id=current_user.id,
                name=form.name.data,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                duration_minutes=duration_minutes,
                started_at=started_at,
                completed_at=completed_at,
                notes=form.notes.data
            )
            flash(f'Workout "{workout.name}" created successfully!', 'success')
            return redirect(url_for('workouts.edit', workout_id=workout.id))

    from datetime import date
    # Get user's templates for quick selection
    templates = Workout.get_templates_by_user(current_user.id, limit=10)
    return render_template('workouts/create.html', form=form, today=date.today(), templates=templates)


@workouts_bp.route('/<int:workout_id>')
@login_required
def detail(workout_id):
    """View workout details"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    exercises = workout.get_exercises()

    # Check Strava connection and upload status
    strava_connected = StravaConnection.is_connected(current_user.id)
    strava_upload = StravaUpload.get_by_workout_id(workout_id)
    # Allow multiple uploads - don't mark as uploaded, just show last upload info
    last_upload_success = strava_upload is not None and strava_upload['upload_status'] == 'success'
    upload_failed = strava_upload is not None and strava_upload['upload_status'] == 'failed'
    last_strava_activity_id = strava_upload['strava_activity_id'] if strava_upload and last_upload_success else None

    return render_template('workouts/detail.html',
                         workout=workout,
                         exercises=exercises,
                         strava_connected=strava_connected,
                         strava_uploaded=False,  # Always allow re-uploading
                         upload_failed=upload_failed,
                         strava_activity_id=last_strava_activity_id,
                         last_upload_success=last_upload_success)


@workouts_bp.route('/<int:workout_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(workout_id):
    """Edit workout (add/remove exercises)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    exercises = workout.get_exercises()

    # Get all available exercises for the dropdown
    all_exercises = Exercise.get_all(limit=872)  # Get all exercises

    # Get filter options
    categories = Exercise.get_all_categories()
    muscles = Exercise.get_all_muscles()
    equipment_list = Exercise.get_all_equipment()

    return render_template('workouts/edit.html',
                         workout=workout,
                         exercises=exercises,
                         all_exercises=all_exercises,
                         categories=categories,
                         muscles=muscles,
                         equipment_list=equipment_list)


@workouts_bp.route('/<int:workout_id>/update-name', methods=['POST'])
@login_required
def update_name(workout_id):
    """Update workout name"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    new_name = request.form.get('name', '').strip()

    if not new_name:
        flash('Workout name cannot be empty', 'danger')
        return redirect(url_for('workouts.edit', workout_id=workout_id))

    # Update workout name
    workout.update(name=new_name)

    flash('Workout name updated successfully', 'success')
    return redirect(url_for('workouts.edit', workout_id=workout_id))


@workouts_bp.route('/<int:workout_id>/update-times', methods=['POST'])
@login_required
def update_times(workout_id):
    """Update workout start/end times and duration"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    started_at = request.form.get('started_at', '').strip()
    completed_at = request.form.get('completed_at', '').strip()
    duration_str = request.form.get('duration_minutes', '').strip()

    update_params = {}
    start_dt = None
    end_dt = None
    duration_minutes = None

    # Parse started_at
    if started_at:
        try:
            start_dt = datetime.fromisoformat(started_at)
            update_params['started_at'] = start_dt
        except ValueError:
            flash('Invalid start date/time format', 'danger')
            return redirect(url_for('workouts.edit', workout_id=workout_id))
    else:
        update_params['started_at'] = None

    # Parse completed_at
    if completed_at:
        try:
            end_dt = datetime.fromisoformat(completed_at)
            update_params['completed_at'] = end_dt
        except ValueError:
            flash('Invalid end date/time format', 'danger')
            return redirect(url_for('workouts.edit', workout_id=workout_id))
    else:
        update_params['completed_at'] = None

    # Parse duration
    if duration_str:
        try:
            duration_minutes = int(duration_str)
        except ValueError:
            flash('Invalid duration', 'danger')
            return redirect(url_for('workouts.edit', workout_id=workout_id))

    # Auto-calculate missing fields
    if start_dt and duration_minutes and not end_dt:
        # Calculate end time from start + duration
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        update_params['completed_at'] = end_dt
    elif start_dt and end_dt and not duration_minutes:
        # Calculate duration from start and end times
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    elif start_dt and end_dt and duration_minutes:
        # All three provided - end time takes precedence, recalculate duration
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

    update_params['duration_minutes'] = duration_minutes

    # Validate that start is before end
    if update_params.get('started_at') and update_params.get('completed_at'):
        if update_params['started_at'] >= update_params['completed_at']:
            flash('Start time must be before end time', 'danger')
            return redirect(url_for('workouts.edit', workout_id=workout_id))

    workout.update(**update_params)

    flash('Workout times updated successfully', 'success')
    return redirect(url_for('workouts.edit', workout_id=workout_id))


@workouts_bp.route('/<int:workout_id>/update-notes', methods=['POST'])
@login_required
def update_notes(workout_id):
    """Update workout notes"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    notes = request.form.get('notes', '').strip()

    # Update workout notes (can be empty)
    workout.update(notes=notes if notes else None)

    flash('Workout notes updated successfully', 'success')
    return redirect(url_for('workouts.edit', workout_id=workout_id))


@workouts_bp.route('/<int:workout_id>/exercises/add', methods=['POST'])
@login_required
def add_exercise(workout_id):
    """Add exercise to workout (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    exercise_id = request.form.get('exercise_id', type=int)
    target_sets = request.form.get('target_sets', type=int)
    target_reps = request.form.get('target_reps', type=int)
    target_weight = request.form.get('target_weight', type=float)
    target_duration = request.form.get('target_duration', type=int)
    notes = request.form.get('notes')

    if not exercise_id:
        return jsonify({'error': 'Exercise ID required'}), 400

    # Get the next order position
    order_position = WorkoutExercise.get_next_order_position(workout_id)

    # Add exercise to workout
    workout_exercise_id = WorkoutExercise.add_to_workout(
        workout_id=workout_id,
        exercise_id=exercise_id,
        order_position=order_position,
        target_sets=target_sets,
        target_reps=target_reps,
        target_weight=target_weight,
        target_duration=target_duration,
        notes=notes
    )

    # Get the exercise details
    exercise = WorkoutExercise.get_by_id(workout_exercise_id)

    return jsonify({
        'success': True,
        'exercise': exercise
    })


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/update-targets', methods=['POST'])
@login_required
def update_exercise_targets(workout_id, workout_exercise_id):
    """Update exercise target values (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get form data
    target_sets = request.form.get('target_sets', type=int)
    target_reps = request.form.get('target_reps', type=int)
    target_weight = request.form.get('target_weight', type=float)
    target_duration = request.form.get('target_duration', type=int)
    notes = request.form.get('notes')

    # Update the exercise
    WorkoutExercise.update(
        workout_exercise_id,
        target_sets=target_sets,
        target_reps=target_reps,
        target_weight=target_weight,
        target_duration=target_duration,
        notes=notes
    )

    return jsonify({'success': True})


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/duplicate', methods=['POST'])
@login_required
def duplicate_exercise(workout_id, workout_exercise_id):
    """Duplicate an exercise in the workout (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get the original exercise
    original = WorkoutExercise.get_by_id(workout_exercise_id)
    if not original:
        return jsonify({'error': 'Exercise not found'}), 404

    # Get the order position right after the original
    new_order = original['order_position'] + 1

    # Shift all exercises after this position
    db = get_db()
    db.execute('''
        UPDATE workout_exercises
        SET order_position = order_position + 1
        WHERE workout_id = ? AND order_position >= ?
    ''', (workout_id, new_order))
    db.commit()

    # Create the duplicate
    new_exercise_id = WorkoutExercise.add_to_workout(
        workout_id=workout_id,
        exercise_id=original['exercise_id'],
        order_position=new_order,
        target_sets=original.get('target_sets'),
        target_reps=original.get('target_reps'),
        target_weight=original.get('target_weight'),
        target_duration=original.get('target_duration'),
        notes=original.get('notes')
    )

    # Get the new exercise details
    new_exercise = WorkoutExercise.get_by_id(new_exercise_id)

    return jsonify({
        'success': True,
        'exercise': new_exercise
    })


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/remove', methods=['POST'])
@login_required
def remove_exercise(workout_id, workout_exercise_id):
    """Remove exercise from workout (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    WorkoutExercise.delete(workout_exercise_id)

    return jsonify({'success': True})


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/reorder', methods=['POST'])
@login_required
def reorder_exercise(workout_id, workout_exercise_id):
    """Reorder exercise in workout (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    direction = request.form.get('direction')  # 'up' or 'down'

    if direction not in ['up', 'down']:
        return jsonify({'error': 'Invalid direction'}), 400

    WorkoutExercise.reorder(workout_exercise_id, direction)

    return jsonify({'success': True})


@workouts_bp.route('/<int:workout_id>/log', methods=['GET', 'POST'])
@login_required
def log(workout_id):
    """Mobile-optimized logging interface"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    if request.method == 'POST':
        # Handle bulk update from form submission
        for exercise in workout.get_exercises():
            actual_sets = request.form.get(f'sets_{exercise["id"]}', type=int)
            actual_reps = request.form.get(f'reps_{exercise["id"]}', type=int)
            actual_weight = request.form.get(f'weight_{exercise["id"]}', type=float)

            if actual_sets or actual_reps or actual_weight:
                WorkoutExercise.update(
                    exercise['id'],
                    actual_sets=actual_sets,
                    actual_reps=actual_reps,
                    actual_weight=actual_weight
                )

        # Mark workout as in_progress if not already
        if workout.status == 'planned':
            update_params = {'status': 'in_progress'}
            if not workout.started_at:
                update_params['started_at'] = datetime.now()
            workout.update(**update_params)

        flash('Workout logged successfully!', 'success')
        return redirect(url_for('workouts.log', workout_id=workout_id))

    exercises = workout.get_exercises()

    return render_template('workouts/log.html', workout=workout, exercises=exercises)


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/update', methods=['POST'])
@login_required
def update_exercise(workout_id, workout_exercise_id):
    """Update exercise actual values (AJAX endpoint for auto-save)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    actual_sets = request.form.get('actual_sets', type=int)
    actual_reps = request.form.get('actual_reps', type=int)
    actual_weight = request.form.get('actual_weight', type=float)
    actual_duration = request.form.get('actual_duration', type=int)

    WorkoutExercise.update(
        workout_exercise_id,
        actual_sets=actual_sets,
        actual_reps=actual_reps,
        actual_weight=actual_weight,
        actual_duration=actual_duration
    )

    # Mark workout as in_progress if not already
    if workout.status == 'planned':
        update_params = {'status': 'in_progress'}
        if not workout.started_at:
            update_params['started_at'] = datetime.now()
        workout.update(**update_params)

    return jsonify({'success': True})


@workouts_bp.route('/<int:workout_id>/start', methods=['POST'])
@login_required
def start(workout_id):
    """Mark workout as started"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    update_params = {'status': 'in_progress'}
    if not workout.started_at:
        update_params['started_at'] = datetime.now()
    workout.update(**update_params)

    flash('Workout started! Good luck!', 'success')
    return redirect(url_for('workouts.log', workout_id=workout_id))


@workouts_bp.route('/<int:workout_id>/complete', methods=['POST'])
@login_required
def complete(workout_id):
    """Mark workout as completed"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    now = datetime.now()
    update_params = {'status': 'completed'}

    # Only set completed_at if not already set
    if not workout.completed_at:
        update_params['completed_at'] = now

    # Only set started_at if not already set
    if not workout.started_at:
        if workout.scheduled_date and workout.scheduled_time:
            try:
                start_dt = datetime.combine(
                    datetime.strptime(workout.scheduled_date, '%Y-%m-%d').date(),
                    datetime.strptime(workout.scheduled_time, '%H:%M').time()
                )
                update_params['started_at'] = start_dt
            except (ValueError, TypeError):
                update_params['started_at'] = now
        else:
            update_params['started_at'] = now

    # Only calculate duration if not already set
    if not workout.duration_minutes:
        start = update_params.get('started_at') or (
            datetime.fromisoformat(workout.started_at) if isinstance(workout.started_at, str) else workout.started_at
        )
        end = update_params.get('completed_at') or (
            datetime.fromisoformat(workout.completed_at) if isinstance(workout.completed_at, str) else workout.completed_at
        )
        if start and end and start < end:
            update_params['duration_minutes'] = int((end - start).total_seconds() / 60)

    workout.update(**update_params)

    flash('Workout completed! Great job!', 'success')
    return redirect(url_for('workouts.detail', workout_id=workout_id))


@workouts_bp.route('/<int:workout_id>/delete', methods=['POST'])
@login_required
def delete(workout_id):
    """Delete a workout"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    workout.delete()

    flash('Workout deleted successfully.', 'info')
    return redirect(url_for('workouts.list'))


@workouts_bp.route('/<int:workout_id>/save-as-template', methods=['POST'])
@login_required
def save_as_template(workout_id):
    """Create a template from an existing workout"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    # Create a new template with the workout's name
    template = Workout.create_template(
        user_id=current_user.id,
        name=f"{workout.name} Template",
        notes=workout.notes
    )

    # Copy all exercises with their target values
    exercises = workout.get_exercises()
    for ex in exercises:
        WorkoutExercise.add_to_workout(
            workout_id=template.id,
            exercise_id=ex['exercise_id'],
            order_position=ex['order_position'],
            target_sets=ex['target_sets'],
            target_reps=ex['target_reps'],
            target_weight=ex['target_weight'],
            target_duration=ex['target_duration'],
            notes=ex['notes']
        )

    flash(f'Template "{template.name}" created from workout!', 'success')
    return redirect(url_for('templates.detail', template_id=template.id))


@workouts_bp.route('/<int:workout_id>/export/tcx')
@login_required
def export_tcx(workout_id):
    """Export workout as TCX file"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        abort(404)

    # Check that workout has start and end times
    if not workout.started_at or not workout.completed_at:
        flash('Please set start and end times before exporting to TCX', 'danger')
        return redirect(url_for('workouts.detail', workout_id=workout_id))

    # Get workout exercises
    exercises = workout.get_exercises()

    if not exercises:
        flash('Cannot export workout without exercises', 'warning')
        return redirect(url_for('workouts.detail', workout_id=workout_id))

    # Generate TCX XML
    tcx_xml = generate_tcx_xml(workout, exercises)

    # Create response with TCX file
    response = make_response(tcx_xml)
    response.headers['Content-Type'] = 'application/vnd.garmin.tcx+xml'
    response.headers['Content-Disposition'] = f'attachment; filename="{workout.name.replace(" ", "_")}_{workout.id}.tcx"'

    return response


# ===== SUPERSET ROUTES =====

@workouts_bp.route('/<int:workout_id>/superset/create', methods=['POST'])
@login_required
def create_superset(workout_id):
    """Create a superset from selected exercises (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    exercise_ids = request.form.getlist('exercise_ids[]', type=int)

    if len(exercise_ids) < 2:
        return jsonify({'error': 'Select at least 2 exercises'}), 400

    try:
        group_id = WorkoutExercise.create_superset(exercise_ids)
        return jsonify({'success': True, 'superset_group_id': group_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@workouts_bp.route('/<int:workout_id>/superset/<int:group_id>/dissolve', methods=['POST'])
@login_required
def dissolve_superset(workout_id, group_id):
    """Dissolve a superset entirely (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    WorkoutExercise.dissolve_superset(workout_id, group_id)
    return jsonify({'success': True})


@workouts_bp.route('/<int:workout_id>/superset/<int:group_id>/update-reps', methods=['POST'])
@login_required
def update_superset_reps(workout_id, group_id):
    """Update superset target or actual reps (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    target_reps = request.form.get('target_reps', type=int)
    actual_reps = request.form.get('actual_reps', type=int)

    WorkoutExercise.update_superset_reps(
        workout_id, group_id,
        target_reps=target_reps,
        actual_reps=actual_reps
    )

    return jsonify({'success': True})


@workouts_bp.route('/<int:workout_id>/exercises/<int:workout_exercise_id>/remove-from-superset', methods=['POST'])
@login_required
def remove_from_superset(workout_id, workout_exercise_id):
    """Remove exercise from its superset (AJAX endpoint)"""
    workout = Workout.get_by_id(workout_id)

    if not workout or workout.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    WorkoutExercise.remove_from_superset(workout_exercise_id)
    return jsonify({'success': True})
