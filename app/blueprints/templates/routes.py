from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import datetime, date
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

        template = Workout.create_template(
            user_id=current_user.id,
            name=name,
            notes=notes
        )

        flash(f'Template "{name}" created!', 'success')
        return redirect(url_for('templates.edit', template_id=template.id))

    return render_template('templates/create.html')


@templates_bp.route('/<int:template_id>')
@login_required
def detail(template_id):
    """View template details"""
    template = Workout.get_by_id(template_id)

    # Verify ownership and template status
    if template.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('templates.list'))

    if not template.is_template:
        flash('Not a template', 'danger')
        return redirect(url_for('workouts.list'))

    exercises = template.get_exercises()
    return render_template('templates/detail.html',
                          template=template,
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
    template = Workout.get_by_id(template_id)

    if template.user_id != current_user.id or not template.is_template:
        flash('Invalid template', 'danger')
        return redirect(url_for('templates.list'))

    if request.method == 'POST':
        scheduled_date = request.form.get('scheduled_date')
        scheduled_time = request.form.get('scheduled_time') or None
        notes = request.form.get('notes') or None

        # Create workout from template
        workout = Workout.create_from_template(
            template_id=template_id,
            user_id=current_user.id,
            scheduled_date=datetime.strptime(scheduled_date, '%Y-%m-%d').date(),
            scheduled_time=scheduled_time,
            notes=notes
        )

        flash(f'Workout created from template "{template.name}"', 'success')
        return redirect(url_for('workouts.detail', workout_id=workout.id))

    # Show form to schedule workout
    return render_template('templates/use.html',
                          template=template,
                          today=date.today())
