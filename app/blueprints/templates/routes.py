from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app.models import Workout, Exercise
from app.blueprints.templates import templates_bp


def _owned_template(template_id):
    """The current user's template, or 404."""
    template = Workout.get_by_id(template_id)
    if not template or template.user_id != current_user.id or not template.is_template:
        abort(404)
    return template


@templates_bp.route('/')
@login_required
def list():
    """List all workout templates with filtering and sorting"""
    visibility = request.args.get('visibility', 'all')
    sort_by = request.args.get('sort', 'name')

    templates = Workout.get_all_templates(
        user_id=current_user.id,
        visibility=visibility,
        order_by=sort_by
    )

    return render_template('templates/list.html',
                          templates=templates,
                          current_visibility=visibility,
                          current_sort=sort_by)


@templates_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new template"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        notes = request.form.get('notes', '').strip() or None
        is_public = 1 if request.form.get('is_public') else 0

        if not name:
            flash('Please give the template a name.', 'danger')
            return render_template('templates/create.html')

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


@templates_bp.route('/<int:template_id>/edit')
@login_required
def edit(template_id):
    """Edit template details and exercises"""
    template = _owned_template(template_id)

    return render_template('templates/edit.html',
                          workout=template,
                          exercises=template.get_exercises(),
                          categories=Exercise.get_all_categories(),
                          muscles=Exercise.get_all_muscles())


@templates_bp.route('/<int:template_id>/delete', methods=['POST'])
@login_required
def delete(template_id):
    """Delete a template"""
    template = _owned_template(template_id)
    template.delete()

    flash(f'Template "{template.name}" deleted', 'success')
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

        try:
            parsed_date = datetime.strptime(scheduled_date or '', '%Y-%m-%d').date()
        except ValueError:
            flash('Please choose a valid date.', 'danger')
            return redirect(url_for('templates.use_template', template_id=template_id))

        # Calculate times if both scheduled_time and duration are provided
        started_at = None
        completed_at = None
        if scheduled_time and duration_minutes:
            try:
                # Combine date and time for start
                started_at = datetime.combine(parsed_date, datetime.strptime(scheduled_time, '%H:%M').time())
                # Add duration for end
                completed_at = started_at + timedelta(minutes=int(duration_minutes))
            except (ValueError, TypeError):
                # If calculation fails, just proceed without times
                pass

        # Create workout from template (usage count auto-increments)
        workout = Workout.create_from_template(
            template_id=template_id,
            user_id=current_user.id,
            scheduled_date=parsed_date,
            scheduled_time=scheduled_time,
            duration_minutes=int(duration_minutes) if duration_minutes else None,
            started_at=started_at,
            completed_at=completed_at,
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
    """Redirect to main templates list with public filter"""
    sort_by = request.args.get('sort', 'usage_count')
    return redirect(url_for('templates.list', visibility='public', sort=sort_by))


@templates_bp.route('/<int:template_id>/toggle-privacy', methods=['POST'])
@login_required
def toggle_privacy(template_id):
    """Toggle template privacy (public/private)"""
    template = _owned_template(template_id)

    try:
        new_status = template.toggle_public()
        status_text = 'public' if new_status else 'private'
        flash(f'Template is now {status_text}', 'success')
    except ValueError as e:
        flash(str(e), 'danger')

    endpoint = 'templates.edit' if request.form.get('from') == 'edit' else 'templates.detail'
    return redirect(url_for(endpoint, template_id=template_id))
