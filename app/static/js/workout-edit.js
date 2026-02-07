// Workout/Template Edit Page JavaScript
// Consolidated handler for exercise management, supersets, search and filtering.
// Works for both /workouts/<id>/edit and /templates/<id>/edit pages.

document.addEventListener('DOMContentLoaded', function() {

    // ===== URL HELPERS =====

    // Detect page context from URL
    function getBaseUrl() {
        const pathParts = window.location.pathname.split('/');
        const baseType = pathParts[1]; // 'workouts' or 'templates'
        const id = pathParts[2];
        return `/${baseType}/${id}`;
    }

    const baseUrl = getBaseUrl();
    const entityId = baseUrl.split('/')[2];
    const isTemplate = baseUrl.startsWith('/templates');

    // Exercise CRUD endpoints always go through /workouts/ routes
    function exerciseUrl(exerciseId, action) {
        const prefix = isTemplate ? '/workouts' : baseUrl.split('/').slice(0, 2).join('/');
        return `${prefix}/${entityId}/exercises/${exerciseId}/${action}`;
    }

    // Superset endpoints use the current baseUrl (both blueprints have routes)
    function supersetUrl(action) {
        return `${baseUrl}/superset/${action}`;
    }

    // ===== GENERIC POST HELPER =====

    async function postAction(url, body, onSuccess) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: body || undefined
            });
            const data = await response.json();
            if (data.success) {
                if (onSuccess) onSuccess(data);
                else location.reload();
            } else {
                alert(data.error || 'Action failed');
            }
        } catch (error) {
            console.error('Action failed:', error);
            alert('Action failed. Please try again.');
        }
    }

    // ===== EVENT DELEGATION ON CURRENT EXERCISES =====

    const currentExercises = document.getElementById('current-exercises');
    if (currentExercises) {
        currentExercises.addEventListener('click', function(e) {
            const button = e.target.closest('button');
            if (!button) return;

            const exerciseId = button.getAttribute('data-exercise-id');

            // Edit exercise
            if (button.classList.contains('edit-exercise')) {
                e.stopPropagation();
                openEditModal(button);
                return;
            }

            // Remove exercise
            if (button.classList.contains('remove-exercise')) {
                e.stopPropagation();
                if (!confirm('Remove this exercise from the workout?')) return;
                postAction(exerciseUrl(exerciseId, 'remove'));
                return;
            }

            // Duplicate exercise
            if (button.classList.contains('duplicate-exercise')) {
                e.stopPropagation();
                postAction(exerciseUrl(exerciseId, 'duplicate'));
                return;
            }

            // Reorder exercise
            if (button.classList.contains('reorder-exercise')) {
                e.stopPropagation();
                const direction = button.getAttribute('data-direction');
                const formData = new URLSearchParams({ direction: direction });
                postAction(exerciseUrl(exerciseId, 'reorder'), formData);
                return;
            }

            // Remove from superset
            if (button.classList.contains('remove-from-superset')) {
                e.stopPropagation();
                postAction(exerciseUrl(exerciseId, 'remove-from-superset'));
                return;
            }

            // Dissolve superset
            if (button.classList.contains('dissolve-superset')) {
                if (!confirm('Dissolve this superset? Exercises will become standalone.')) return;
                const supersetId = button.getAttribute('data-superset-id');
                postAction(`${baseUrl}/superset/${supersetId}/dissolve`);
                return;
            }

            // Reorder superset (move entire group)
            if (button.classList.contains('reorder-superset')) {
                const supersetId = button.getAttribute('data-superset-id');
                const direction = button.getAttribute('data-direction');
                const supersetGroup = document.querySelector(`.superset-group[data-superset-id="${supersetId}"]`);
                const firstExercise = supersetGroup.querySelector('.list-group-item');
                if (!firstExercise) return;
                const firstExerciseId = firstExercise.dataset.exerciseId;
                const formData = new URLSearchParams({ direction: direction });
                postAction(exerciseUrl(firstExerciseId, 'reorder'), formData);
                return;
            }
        });
    }

    // ===== EDIT EXERCISE MODAL =====

    function openEditModal(button) {
        const exerciseId = button.getAttribute('data-exercise-id');
        const exerciseName = button.getAttribute('data-exercise-name');
        const targetSets = button.getAttribute('data-target-sets');
        const targetReps = button.getAttribute('data-target-reps');
        const targetWeight = button.getAttribute('data-target-weight');
        const targetDuration = button.getAttribute('data-target-duration');
        const notes = button.getAttribute('data-notes');

        document.getElementById('modal-exercise-name').textContent = exerciseName;
        document.getElementById('modal-exercise-id').value = exerciseId;
        document.getElementById('target-sets').value = targetSets || '';
        document.getElementById('target-reps').value = targetReps || '';
        document.getElementById('target-weight').value = targetWeight || '';
        document.getElementById('target-duration').value = targetDuration || '';
        document.getElementById('exercise-notes').value = notes || '';

        document.querySelector('#exerciseModal .modal-title').textContent = 'Edit Exercise';
        document.getElementById('confirm-add-exercise').textContent = 'Update Exercise';
        document.getElementById('confirm-add-exercise').setAttribute('data-mode', 'edit');

        const modal = new bootstrap.Modal(document.getElementById('exerciseModal'));
        modal.show();
    }

    // ===== ADD EXERCISE MODAL (from exercise list) =====
    // Uses delegation on #exercise-list for dynamically loaded items

    const exerciseList = document.getElementById('exercise-list');
    if (exerciseList) {
        exerciseList.addEventListener('click', function(e) {
            const button = e.target.closest('.add-exercise');
            if (!button) return;

            const exerciseId = button.getAttribute('data-exercise-id');
            const exerciseName = button.getAttribute('data-exercise-name');

            document.getElementById('modal-exercise-name').textContent = exerciseName;
            document.getElementById('modal-exercise-id').value = exerciseId;
            document.getElementById('target-sets').value = 3;
            document.getElementById('target-reps').value = 10;
            document.getElementById('target-weight').value = '';
            document.getElementById('target-duration').value = '';
            document.getElementById('exercise-notes').value = '';

            document.querySelector('#exerciseModal .modal-title').textContent = 'Add Exercise';
            document.getElementById('confirm-add-exercise').textContent = 'Add Exercise';
            document.getElementById('confirm-add-exercise').setAttribute('data-mode', 'add');

            const modal = new bootstrap.Modal(document.getElementById('exerciseModal'));
            modal.show();
        });
    }

    // ===== CONFIRM ADD/EDIT EXERCISE =====

    const confirmAddButton = document.getElementById('confirm-add-exercise');
    if (confirmAddButton) {
        confirmAddButton.addEventListener('click', function() {
            const exerciseId = document.getElementById('modal-exercise-id').value;
            const targetSets = document.getElementById('target-sets').value;
            const targetReps = document.getElementById('target-reps').value;
            const targetWeight = document.getElementById('target-weight').value;
            const targetDuration = document.getElementById('target-duration').value;
            const notes = document.getElementById('exercise-notes').value;
            const mode = this.getAttribute('data-mode') || 'add';

            const action = mode === 'edit' ? `${exerciseId}/update-targets` : 'add';
            const url = isTemplate
                ? `/workouts/${entityId}/exercises/${action}`
                : `${baseUrl}/exercises/${action}`;

            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    exercise_id: exerciseId,
                    target_sets: targetSets,
                    target_reps: targetReps,
                    target_weight: targetWeight,
                    target_duration: targetDuration,
                    notes: notes
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    bootstrap.Modal.getInstance(document.getElementById('exerciseModal')).hide();
                    location.reload();
                } else {
                    alert(`Error ${mode === 'edit' ? 'updating' : 'adding'} exercise: ` + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                alert(`Error ${mode === 'edit' ? 'updating' : 'adding'} exercise: ` + error);
            });
        });
    }

    // ===== SUPERSET ROUNDS (workouts only) =====

    document.querySelectorAll('.superset-rounds-input').forEach(input => {
        input.addEventListener('change', async function() {
            const supersetId = this.dataset.supersetId;
            const targetReps = this.value;

            const formData = new FormData();
            if (targetReps) formData.append('target_reps', targetReps);

            postAction(`/workouts/${entityId}/superset/${supersetId}/update-reps`, formData);
        });
    });

    // ===== SUPERSET SELECTION MODE =====

    let selectionMode = false;
    let selectedExercises = new Set();

    const toggleSelectionBtn = document.getElementById('toggle-selection-mode');
    const supersetToolbar = document.getElementById('superset-toolbar');
    const createSupersetBtn = document.getElementById('create-superset-btn');
    const cancelSelectionBtn = document.getElementById('cancel-selection-btn');
    const selectedCountBadge = document.getElementById('selected-count');

    function enterSelectionMode() {
        selectionMode = true;
        selectedExercises.clear();
        supersetToolbar.style.display = 'flex';
        toggleSelectionBtn.classList.add('active');
        toggleSelectionBtn.innerHTML = '<i class="fa-solid fa-check"></i> Done';

        document.querySelectorAll('.exercise-selectable').forEach(item => {
            if (!item.dataset.supersetId) {
                item.addEventListener('click', handleExerciseSelection);
                item.style.cursor = 'pointer';
            }
        });
        updateSelectedCount();
    }

    function exitSelectionMode() {
        selectionMode = false;
        selectedExercises.clear();
        supersetToolbar.style.display = 'none';
        toggleSelectionBtn.classList.remove('active');
        toggleSelectionBtn.innerHTML = '<i class="fa-solid fa-layer-group"></i> Superset Mode';

        document.querySelectorAll('.exercise-selectable').forEach(item => {
            item.classList.remove('selected');
            item.removeEventListener('click', handleExerciseSelection);
            item.style.cursor = '';
        });
    }

    function handleExerciseSelection(e) {
        if (e.target.closest('button') || e.target.closest('.btn-group')) return;

        const exerciseId = this.dataset.exerciseId;
        if (selectedExercises.has(exerciseId)) {
            selectedExercises.delete(exerciseId);
            this.classList.remove('selected');
        } else {
            selectedExercises.add(exerciseId);
            this.classList.add('selected');
        }
        updateSelectedCount();
    }

    function updateSelectedCount() {
        const count = selectedExercises.size;
        selectedCountBadge.textContent = `${count} selected`;

        if (count >= 2) {
            createSupersetBtn.disabled = false;
            selectedCountBadge.classList.remove('bg-secondary');
            selectedCountBadge.classList.add('bg-success');
        } else {
            createSupersetBtn.disabled = true;
            selectedCountBadge.classList.remove('bg-success');
            selectedCountBadge.classList.add('bg-secondary');
        }
    }

    if (toggleSelectionBtn) {
        toggleSelectionBtn.addEventListener('click', function() {
            selectionMode = !selectionMode;
            if (selectionMode) enterSelectionMode();
            else exitSelectionMode();
        });
    }

    if (cancelSelectionBtn) {
        cancelSelectionBtn.addEventListener('click', function() {
            exitSelectionMode();
        });
    }

    if (createSupersetBtn) {
        createSupersetBtn.addEventListener('click', async function() {
            if (selectedExercises.size < 2) return;

            const formData = new FormData();
            selectedExercises.forEach(id => {
                formData.append('exercise_ids[]', id);
            });

            postAction(supersetUrl('create'), formData);
        });
    }

    // ===== AJAX SEARCH AND FILTER =====

    const exerciseSearch = document.getElementById('exercise-search');
    const categoryFilter = document.getElementById('category-filter');
    const muscleFilter = document.getElementById('muscle-filter');

    let searchTimeout;

    if (exerciseSearch) {
        exerciseSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value;

            // If search is cleared, apply filters only (or reload)
            if (query.length === 0) {
                applyFilters();
                return;
            }

            searchTimeout = setTimeout(async () => {
                if (query.length < 2) return;

                try {
                    const response = await fetch(`/exercises/search?q=${encodeURIComponent(query)}`);
                    const data = await response.json();
                    updateExerciseList(data.exercises);
                } catch (error) {
                    console.error('Error searching exercises:', error);
                }
            }, 300);
        });
    }

    if (categoryFilter) {
        categoryFilter.addEventListener('change', applyFilters);
    }
    if (muscleFilter) {
        muscleFilter.addEventListener('change', applyFilters);
    }

    async function applyFilters() {
        const category = categoryFilter ? categoryFilter.value : '';
        const muscle = muscleFilter ? muscleFilter.value : '';
        const search = exerciseSearch ? exerciseSearch.value : '';

        // If everything is cleared, reload to show original list
        if (!category && !muscle && !search) {
            location.reload();
            return;
        }

        // If only search is active, let the search handler deal with it
        if (search.length >= 2 && !category && !muscle) return;

        try {
            const params = new URLSearchParams();
            if (category) params.append('category', category);
            if (muscle) params.append('muscle', muscle);
            if (search) params.append('q', search);
            params.append('limit', 100);

            const response = await fetch(`/exercises/filter?${params.toString()}`);
            const data = await response.json();
            updateExerciseList(data.exercises);
        } catch (error) {
            console.error('Error filtering exercises:', error);
        }
    }

    function updateExerciseList(exercises) {
        const listDiv = document.getElementById('exercise-list');
        if (!listDiv) return;
        listDiv.innerHTML = '';

        exercises.forEach(exercise => {
            const card = document.createElement('div');
            card.className = 'card mb-2 exercise-item';

            card.innerHTML = `
                <div class="card-body p-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${exercise.name}</h6>
                            <small class="text-muted d-block">${exercise.category_name || ''}</small>
                        </div>
                        <div class="btn-group">
                            <button class="btn btn-sm btn-info btn-touch view-exercise-details"
                                    data-exercise-id="${exercise.id}"
                                    data-exercise-name="${exercise.name}"
                                    title="View details">
                                <i class="fa-solid fa-circle-info"></i>
                            </button>
                            <button class="btn btn-sm btn-primary btn-touch add-exercise"
                                    data-exercise-id="${exercise.id}"
                                    data-exercise-name="${exercise.name}"
                                    title="Add to workout">
                                <i class="fa-solid fa-plus"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            listDiv.appendChild(card);
        });
    }
});
