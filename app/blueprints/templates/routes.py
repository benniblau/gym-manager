from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app.models import Workout, WorkoutExercise, Exercise
from app.blueprints.templates import templates_bp


@templates_bp.route('/')
@login_required
def list():
    """List all workout templates"""
    templates = Workout.get_templates_by_user(current_user.id)
    return render_template('templates/list.html', templates=templates)


@templates_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new template"""
    if request.method == 'POST':
        name = request.form.get('name')
        notes = request.form.get('notes')
        is_public = 1 if request.form.get('is_public') else 0

        template = Workout.create_template(
            user_id=current_user.id,
            name=name,
            notes=notes,
            is_public=is_public
        )

        flash(f'Template "{name}" created!', 'success')
        return redirect(url_for('templates.edit', template_id=template.id))

    return render_template('templates/create.html')


@templates_bp.route('/<int:template_id>')
@login_required
def detail(template_id):
    """View template details"""
    template_dict = Workout.get_template_with_creator(template_id)

    if not template_dict:
        flash('Template not found', 'danger')
        return redirect(url_for('templates.list'))

    # Get template object for methods
    template = Workout.get_by_id(template_id)

    # Verify access: owner OR public
    is_owner = template.user_id == current_user.id
    if not is_owner and not template.is_public:
        flash('Access denied', 'danger')
        return redirect(url_for('templates.list'))

    exercises = template.get_exercises()
    return render_template('templates/detail.html',
                          template=template,
                          template_dict=template_dict,
                          is_owner=is_owner,
                          exercises=exercises)


@templates_bp.route('/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(template_id):
    """Edit template exercises"""
    template = Workout.get_by_id(template_id)

    # Verify ownership
    if template.user_id != current_user.id or not template.is_template:
        flash('Access denied', 'danger')
        return redirect(url_for('templates.list'))

    exercises = template.get_exercises()

    # Get all available exercises for the dropdown
    all_exercises = Exercise.get_all(limit=2100)  # Get all exercises

    # Get filter options
    categories = Exercise.get_all_categories()
    muscles = Exercise.get_all_muscles()
    equipment_list = Exercise.get_all_equipment()

    return render_template('templates/edit.html',
                          workout=template,
                          exercises=exercises,
                          all_exercises=all_exercises,
                          categories=categories,
                          muscles=muscles,
                          equipment_list=equipment_list)


@templates_bp.route('/<int:template_id>/update-notes', methods=['POST'])
@login_required
def update_notes(template_id):
    """Update template notes"""
    template = Workout.get_by_id(template_id)

    if not template or template.user_id != current_user.id or not template.is_template:
        abort(404)

    notes = request.form.get('notes', '').strip()

    # Update template notes (can be empty)
    template.update(notes=notes if notes else None)

    flash('Template notes updated successfully', 'success')
    return redirect(url_for('templates.edit', template_id=template_id))


@templates_bp.route('/<int:template_id>/delete', methods=['POST'])
@login_required
def delete(template_id):
    """Delete a template"""
    template = Workout.get_by_id(template_id)

    if template.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('templates.list'))

    template_name = template.name
    template.delete()

    flash(f'Template "{template_name}" deleted', 'success')
    return redirect(url_for('templates.list'))


@templates_bp.route('/<int:template_id>/use', methods=['GET', 'POST'])
@login_required
def use_template(template_id):
    """Create workout from template"""
    template_dict = Workout.get_template_with_creator(template_id)

    if not template_dict:
        flash('Template not found', 'danger')
        return redirect(url_for('templates.list'))

    # Get template object
    template = Workout.get_by_id(template_id)

    # Verify access: owner OR public
    is_owner = template.user_id == current_user.id
    if not is_owner and not template.is_public:
        flash('Access denied', 'danger')
        return redirect(url_for('templates.list'))

    if request.method == 'POST':
        scheduled_date = request.form.get('scheduled_date')
        scheduled_time = request.form.get('scheduled_time', '').strip() or None
        duration_minutes = request.form.get('duration_minutes', '').strip() or None
        form_notes = request.form.get('notes', '').strip() or None

        # Use form notes if provided, otherwise fall back to template notes
        notes = form_notes if form_notes else template.notes

        # Parse date
        parsed_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()

        # Calculate end_date and end_time if both scheduled_time and duration are provided
        end_date = None
        end_time = None
        if scheduled_time and duration_minutes:
            try:
                # Combine date and time
                start_datetime = datetime.combine(parsed_date, datetime.strptime(scheduled_time, '%H:%M').time())
                # Add duration
                end_datetime = start_datetime + timedelta(minutes=int(duration_minutes))
                end_date = end_datetime.date()
                end_time = end_datetime.time().strftime('%H:%M')
            except (ValueError, TypeError):
                # If calculation fails, just proceed without end time
                pass

        # Create workout from template (usage count auto-increments)
        workout = Workout.create_from_template(
            template_id=template_id,
            user_id=current_user.id,
            scheduled_date=parsed_date,
            scheduled_time=scheduled_time,
            duration_minutes=int(duration_minutes) if duration_minutes else None,
            end_date=end_date,
            end_time=end_time,
            notes=notes
        )

        flash(f'Workout created from template "{template.name}"', 'success')
        return redirect(url_for('workouts.detail', workout_id=workout.id))

    # Show form to schedule workout
    return render_template('templates/use.html',
                          template=template,
                          template_dict=template_dict,
                          is_owner=is_owner,
                          today=date.today())


@templates_bp.route('/browse')
@login_required
def browse_public():
    """Browse public templates"""
    sort_by = request.args.get('sort', 'usage_count')
    templates = Workout.get_public_templates(order_by=sort_by)

    return render_template('templates/browse_public.html',
                          templates=templates,
                          current_sort=sort_by)


@templates_bp.route('/<int:template_id>/toggle-privacy', methods=['POST'])
@login_required
def toggle_privacy(template_id):
    """Toggle template privacy (public/private)"""
    template = Workout.get_by_id(template_id)

    if not template or template.user_id != current_user.id or not template.is_template:
        abort(404)

    try:
        new_status = template.toggle_public()
        status_text = 'public' if new_status else 'private'
        flash(f'Template is now {status_text}', 'success')
    except ValueError as e:
        flash(str(e), 'danger')

    return redirect(request.referrer or url_for('templates.detail', template_id=template_id))


# ===== SUPERSET ROUTES =====

@templates_bp.route('/<int:template_id>/superset/create', methods=['POST'])
@login_required
def create_superset(template_id):
    """Create a superset from selected exercises (AJAX endpoint)"""
    template = Workout.get_by_id(template_id)

    if not template or template.user_id != current_user.id or not template.is_template:
        return jsonify({'error': 'Unauthorized'}), 403

    exercise_ids = request.form.getlist('exercise_ids[]', type=int)

    if len(exercise_ids) < 2:
        return jsonify({'error': 'Select at least 2 exercises'}), 400

    try:
        group_id = WorkoutExercise.create_superset(exercise_ids)
        return jsonify({'success': True, 'superset_group_id': group_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@templates_bp.route('/<int:template_id>/superset/<int:group_id>/dissolve', methods=['POST'])
@login_required
def dissolve_superset(template_id, group_id):
    """Dissolve a superset entirely (AJAX endpoint)"""
    template = Workout.get_by_id(template_id)

    if not template or template.user_id != current_user.id or not template.is_template:
        return jsonify({'error': 'Unauthorized'}), 403

    WorkoutExercise.dissolve_superset(template_id, group_id)
    return jsonify({'success': True})


@templates_bp.route('/<int:template_id>/exercises/<int:workout_exercise_id>/remove-from-superset', methods=['POST'])
@login_required
def remove_from_superset(template_id, workout_exercise_id):
    """Remove exercise from its superset (AJAX endpoint)"""
    template = Workout.get_by_id(template_id)

    if not template or template.user_id != current_user.id or not template.is_template:
        return jsonify({'error': 'Unauthorized'}), 403

    WorkoutExercise.remove_from_superset(workout_exercise_id)
    return jsonify({'success': True})
