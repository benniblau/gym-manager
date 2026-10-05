// Workout/Template Edit Page JavaScript
// Exercise list (edit, reorder, supersets) and the add-exercise picker.
// Works for both /workouts/<id>/edit and /templates/<id>/edit: a template is a
// workout row, so every request goes to the /workouts/<id>/... routes.
// Each change returns the re-rendered list, which is swapped in place.

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('exercise-list-container');
    if (!container) return;

    const baseUrl = `/workouts/${container.dataset.workoutId}`;
    const countEl = document.getElementById('exercise-count');
    const toggleSelectionBtn = document.getElementById('toggle-selection-mode');
    const supersetToolbar = document.getElementById('superset-toolbar');
    const createSupersetBtn = document.getElementById('create-superset-btn');
    const cancelSelectionBtn = document.getElementById('cancel-selection-btn');
    const selectedCountEl = document.getElementById('selected-count');

    const exerciseUrl = (exerciseId, action) => `${baseUrl}/exercises/${exerciseId}/${action}`;

    // ===== LIST UPDATES =====

    function render(data) {
        container.innerHTML = data.html;
        countEl.textContent = data.count;
        toggleSelectionBtn.hidden = data.count < 2;
        exitSelectionMode();
        initSortable();
    }

    // POST a change and swap in the returned list. Returns true on success.
    async function change(url, body, doneMessage) {
        try {
            render(await gm.post(url, body));
            if (doneMessage) gm.toast(doneMessage, 'success');
            return true;
        } catch (error) {
            gm.toast(error.message, 'danger');
            return false;
        }
    }

    async function reloadList() {
        try {
            const response = await fetch(`${baseUrl}/exercises/list`);
            render(await response.json());
        } catch (error) {
            window.location.reload();
        }
    }

    // ===== EVENT DELEGATION ON THE LIST =====
    // The list markup is replaced after every change, so handlers live on the container.

    container.addEventListener('click', async function(e) {
        const button = e.target.closest('button');

        if (selectionMode) {
            const item = e.target.closest('.exercise-selectable');
            if (item && !e.target.closest('.exercise-actions')) {
                e.preventDefault();
                toggleSelected(item);
            }
            return;
        }
        if (!button) return;

        const exerciseId = button.dataset.exerciseId;

        if (button.classList.contains('edit-exercise')) {
            openTargetModal('edit', button.dataset);
        } else if (button.classList.contains('remove-exercise')) {
            const yes = await gm.confirm(`Remove ${button.dataset.exerciseName}?`, { okLabel: 'Remove', danger: true });
            if (yes) change(exerciseUrl(exerciseId, 'remove'));
        } else if (button.classList.contains('duplicate-exercise')) {
            change(exerciseUrl(exerciseId, 'duplicate'));
        } else if (button.classList.contains('reorder-exercise')) {
            change(exerciseUrl(exerciseId, 'reorder'), new URLSearchParams({ direction: button.dataset.direction }));
        } else if (button.classList.contains('remove-from-superset')) {
            change(exerciseUrl(exerciseId, 'remove-from-superset'));
        } else if (button.classList.contains('dissolve-superset')) {
            const yes = await gm.confirm('Dissolve this superset? Its exercises stay in the workout.', { okLabel: 'Dissolve' });
            if (yes) change(`${baseUrl}/superset/${button.dataset.supersetId}/dissolve`);
        }
    });

    // Planned rounds of a superset
    container.addEventListener('change', async function(e) {
        const input = e.target.closest('.superset-rounds-input');
        if (!input) return;
        try {
            await gm.post(`${baseUrl}/superset/${input.dataset.supersetId}/update-reps`,
                new URLSearchParams({ target_reps: input.value || 0 }));
        } catch (error) {
            gm.toast(error.message, 'danger');
        }
    });

    // ===== TARGET MODAL (add from picker, or edit an entry) =====

    const modalEl = document.getElementById('exerciseModal');
    const targetForm = document.getElementById('exercise-target-form');
    const confirmButton = document.getElementById('confirm-add-exercise');
    const field = id => document.getElementById(id);
    let modalMode = 'add';

    function openTargetModal(mode, data) {
        modalMode = mode;
        field('modal-exercise-name').textContent = data.exerciseName;
        field('modal-exercise-id').value = data.exerciseId;
        field('target-sets').value = mode === 'edit' ? data.targetSets : 3;
        field('target-reps').value = mode === 'edit' ? data.targetReps : 10;
        field('target-weight').value = mode === 'edit' ? data.targetWeight : '';
        field('target-duration').value = mode === 'edit' ? data.targetDuration : '';
        field('exercise-notes').value = mode === 'edit' ? data.notes : '';
        confirmButton.textContent = mode === 'edit' ? 'Save' : 'Add';
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }

    targetForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const exerciseId = field('modal-exercise-id').value;
        const name = field('modal-exercise-name').textContent;
        const body = new URLSearchParams({
            exercise_id: exerciseId,
            target_sets: field('target-sets').value,
            target_reps: field('target-reps').value,
            target_weight: field('target-weight').value,
            target_duration: field('target-duration').value,
            notes: field('exercise-notes').value,
        });
        const url = modalMode === 'edit' ? exerciseUrl(exerciseId, 'update-targets') : `${baseUrl}/exercises/add`;

        confirmButton.disabled = true;
        const ok = await change(url, body, modalMode === 'add' ? `Added ${name}` : null);
        confirmButton.disabled = false;
        if (ok) bootstrap.Modal.getInstance(modalEl).hide();
    });

    // ===== DRAG AND DROP REORDER =====

    let sortables = [];

    function collectOrder() {
        return Array.from(container.querySelectorAll('.exercise-selectable'))
            .map(item => parseInt(item.dataset.exerciseId));
    }

    async function saveOrder() {
        const ok = await change(`${baseUrl}/exercises/set-order`, { order: collectOrder() });
        if (!ok) reloadList();
    }

    function initSortable() {
        sortables.forEach(s => s.destroy());
        sortables = [];
        const list = document.getElementById('current-exercises');
        if (!list || typeof Sortable === 'undefined') return;

        const options = {
            handle: '.drag-handle',
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            onEnd: saveOrder,
        };
        // Top level: standalone exercises and whole superset groups
        sortables.push(Sortable.create(list, { ...options, draggable: '.list-group-item, .superset-group' }));
        // Inside each superset: its own exercises
        list.querySelectorAll('.superset-group').forEach(group => {
            sortables.push(Sortable.create(group, { ...options, draggable: '.list-group-item' }));
        });
    }

    // ===== SUPERSET SELECTION MODE =====

    let selectionMode = false;
    const selected = new Set();

    function updateSelectedCount() {
        selectedCountEl.textContent = selected.size;
        createSupersetBtn.disabled = selected.size < 2;
    }

    function toggleSelected(item) {
        if (item.dataset.supersetId) {
            gm.toast('Already in a superset');
            return;
        }
        const id = item.dataset.exerciseId;
        if (selected.has(id)) selected.delete(id);
        else selected.add(id);
        item.classList.toggle('selected', selected.has(id));
        updateSelectedCount();
    }

    function enterSelectionMode() {
        selectionMode = true;
        selected.clear();
        sortables.forEach(s => s.option('disabled', true));
        container.classList.add('selecting');
        supersetToolbar.hidden = false;
        toggleSelectionBtn.classList.add('active');
        updateSelectedCount();
    }

    function exitSelectionMode() {
        selectionMode = false;
        selected.clear();
        sortables.forEach(s => s.option('disabled', false));
        container.classList.remove('selecting');
        container.querySelectorAll('.selected').forEach(item => item.classList.remove('selected'));
        supersetToolbar.hidden = true;
        toggleSelectionBtn.classList.remove('active');
    }

    toggleSelectionBtn.addEventListener('click', () => (selectionMode ? exitSelectionMode() : enterSelectionMode()));
    cancelSelectionBtn.addEventListener('click', exitSelectionMode);
    createSupersetBtn.addEventListener('click', function() {
        const body = new FormData();
        selected.forEach(id => body.append('exercise_ids[]', id));
        change(`${baseUrl}/superset/create`, body, 'Superset created');
    });

    // ===== EXERCISE PICKER (server-side search, paged) =====

    const pickerEl = document.getElementById('exercise-picker');
    const resultsEl = document.getElementById('exercise-list');
    const searchInput = document.getElementById('exercise-search');
    const categoryFilter = document.getElementById('category-filter');
    const muscleFilter = document.getElementById('muscle-filter');
    const moreButton = document.getElementById('picker-more');
    const pickerCount = document.getElementById('picker-count');
    let nextOffset = 0;
    let requestNumber = 0;

    function resultRow(exercise) {
        const meta = [exercise.category_name, exercise.primary_muscles].filter(Boolean).join(' · ');
        const name = gm.escapeHtml(exercise.name);
        return `
            <div class="picker-row">
                <button type="button" class="picker-add add-exercise" data-exercise-id="${exercise.id}" data-exercise-name="${name}">
                    <span class="picker-name">${name}</span>
                    <span class="picker-meta">${gm.escapeHtml(meta)}</span>
                </button>
                <button type="button" class="btn btn-outline-secondary btn-touch view-exercise-details"
                        data-exercise-id="${exercise.id}" data-exercise-name="${name}" aria-label="Instructions for ${name}">
                    <i class="fa-solid fa-circle-info"></i>
                </button>
            </div>`;
    }

    async function loadExercises(reset) {
        const mine = ++requestNumber;
        const params = new URLSearchParams({
            q: searchInput.value.trim(),
            category: categoryFilter.value,
            muscle: muscleFilter.value,
            offset: reset ? 0 : nextOffset,
        });
        try {
            const response = await fetch(`/exercises/picker?${params}`);
            const data = await response.json();
            if (mine !== requestNumber) return;  // a newer search superseded this one
            if (reset) resultsEl.innerHTML = '';
            resultsEl.insertAdjacentHTML('beforeend', data.exercises.map(resultRow).join(''));
            nextOffset = data.next_offset;
            moreButton.hidden = data.next_offset === null;
            pickerCount.textContent = data.total === 0 ? 'No exercises match.' : `${data.total} exercises`;
        } catch (error) {
            pickerCount.textContent = 'Could not load exercises. Check your connection.';
        }
    }

    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadExercises(true), 250);
    });
    categoryFilter.addEventListener('change', () => loadExercises(true));
    muscleFilter.addEventListener('change', () => loadExercises(true));
    moreButton.addEventListener('click', () => loadExercises(false));
    pickerEl.addEventListener('show.bs.offcanvas', () => { if (!resultsEl.children.length) loadExercises(true); });

    resultsEl.addEventListener('click', function(e) {
        const button = e.target.closest('.add-exercise');
        if (button) openTargetModal('add', button.dataset);
    });

    initSortable();
});
