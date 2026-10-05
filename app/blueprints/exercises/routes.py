from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required
import math

from app.models import Exercise

exercises_bp = Blueprint('exercises', __name__)


@exercises_bp.route('/')
@login_required
def browse():
    """Browse all exercises with pagination and filters"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    # Get filter parameters
    category = request.args.get('category')
    muscle = request.args.get('muscle')
    equipment = request.args.get('equipment')
    search_query = request.args.get('q')

    exercises, total_count = Exercise.find(
        query=search_query, category=category, muscle=muscle, equipment=equipment,
        limit=per_page, offset=offset
    )

    total_pages = math.ceil(total_count / per_page)

    # Get filter options
    categories = Exercise.get_all_categories()
    muscles = Exercise.get_all_muscles()
    equipment_list = Exercise.get_all_equipment()

    return render_template('exercises/browse.html',
                         exercises=exercises,
                         page=page,
                         total_pages=total_pages,
                         categories=categories,
                         muscles=muscles,
                         equipment_list=equipment_list,
                         selected_category=category,
                         selected_muscle=muscle,
                         selected_equipment=equipment,
                         search_query=search_query)


@exercises_bp.route('/<int:exercise_id>')
@login_required
def detail(exercise_id):
    """View exercise details"""
    exercise = Exercise.get_by_id(exercise_id)

    if not exercise:
        abort(404)

    return render_template('exercises/detail.html', exercise=exercise)


@exercises_bp.route('/<int:exercise_id>/details')
@login_required
def details_json(exercise_id):
    """Get exercise details as JSON for modal display"""
    exercise = Exercise.get_by_id(exercise_id)

    if not exercise:
        return jsonify({'error': 'Exercise not found'}), 404

    # Format primary and secondary muscles
    primary_muscles = ', '.join(exercise.get('primary_muscles', []))
    secondary_muscles = ', '.join(exercise.get('secondary_muscles', []))

    return jsonify({
        'id': exercise['id'],
        'name': exercise['name'],
        'description': exercise.get('description', ''),
        'category_name': exercise.get('category_name', ''),
        'primary_muscles': primary_muscles,
        'secondary_muscles': secondary_muscles,
        'instructions': exercise.get('instructions', []),
        'equipment': exercise.get('equipment', []),
        'video': exercise.get('video'),
        'image1_url': exercise.get('image1_url'),
        'image2_url': exercise.get('image2_url'),
        'garmin_url': exercise.get('garmin_url'),
        'difficulty': exercise.get('difficulty'),
        'focus': exercise.get('focus')
    })


@exercises_bp.route('/picker')
@login_required
def picker():
    """Paged search for the add-exercise sheet on the edit pages (AJAX)"""
    limit = 30
    offset = max(request.args.get('offset', 0, type=int), 0)

    exercises, total = Exercise.find(
        query=request.args.get('q', '').strip() or None,
        category=request.args.get('category') or None,
        muscle=request.args.get('muscle') or None,
        limit=limit, offset=offset
    )

    return jsonify({
        'exercises': [
            {k: e[k] for k in ('id', 'name', 'category_name', 'primary_muscles')} for e in exercises
        ],
        'total': total,
        'next_offset': offset + limit if offset + limit < total else None,
    })
