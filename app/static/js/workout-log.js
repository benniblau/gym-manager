// Workout logging page: set-by-set logging, rest timer, progress, finish.
// Ticking a set is what records it; values are sent through gm.queue so they
// survive a dropped connection and are retried until the server has them.

document.addEventListener('DOMContentLoaded', function() {
    const page = document.getElementById('log-page');
    if (!page) return;

    const workoutId = page.dataset.workoutId;
    const isCompleted = page.dataset.status === 'completed';
    const sections = Array.from(page.querySelectorAll('.log-ex'));

    // ===== SET ROWS =====

    const rowsOf = section => Array.from(section.querySelectorAll('.set-row'));
    const doneCount = section => section.querySelectorAll('.set-row.done').length;
    const isComplete = section => rowsOf(section).every(row => row.classList.contains('done'));

    function rowValues(row) {
        const values = {};
        row.querySelectorAll('.set-input').forEach(input => { values[input.dataset.field] = input.value; });
        return values;
    }

    function setDone(row, done) {
        row.classList.toggle('done', done);
        row.querySelector('.set-check').setAttribute('aria-pressed', done ? 'true' : 'false');
    }

    function queueSet(section, row) {
        const entryId = section.dataset.entryId;
        const number = row.dataset.set;
        const done = row.classList.contains('done');
        gm.queue.add(
            `${workoutId}:set:${entryId}:${number}`,
            `/workouts/${workoutId}/exercises/${entryId}/sets/${number}`,
            done ? { done: true, ...rowValues(row) } : { done: false },
            { workoutId, entryId, number }
        );
    }

    function addRow(section) {
        const rows = rowsOf(section);
        const last = rows[rows.length - 1];
        const row = last.cloneNode(true);
        const number = parseInt(last.dataset.set) + 1;
        row.dataset.set = number;
        row.querySelector('.set-num').textContent = number;
        row.querySelector('.set-check').setAttribute('aria-label', `Set ${number} done`);
        setDone(row, false);
        last.after(row);
        return row;
    }

    // ===== PROGRESS =====

    function updateSection(section) {
        const total = rowsOf(section).length;
        const done = doneCount(section);
        const progress = section.querySelector('.log-ex-progress');
        section.classList.toggle('complete', done >= total);
        section.classList.toggle('started', done > 0);
        progress.innerHTML = done >= total ? '<i class="fa-solid fa-circle-check"></i>' : `${done}/${total}`;
        section.querySelector('.all-done').hidden = done >= total;
    }

    function updateProgress() {
        const complete = sections.filter(isComplete).length;
        document.getElementById('progress-text').textContent = complete;
        const bar = document.getElementById('progress-bar');
        if (bar) {
            bar.style.width = `${sections.length ? (complete / sections.length) * 100 : 0}%`;
            bar.parentElement.setAttribute('aria-valuenow', complete);
        }
    }

    // ===== ONE EXERCISE OPEN AT A TIME =====

    function open(section, scroll) {
        sections.forEach(other => {
            const isTarget = other === section;
            other.classList.toggle('open', isTarget);
            other.querySelector('.log-ex-body').hidden = !isTarget;
            other.querySelector('.log-ex-head').setAttribute('aria-expanded', isTarget ? 'true' : 'false');
        });
        if (scroll && section) {
            const top = section.getBoundingClientRect().top + window.scrollY - 70;
            window.scrollTo({ top, behavior: 'smooth' });
        }
    }

    function nextIncomplete(after) {
        const index = sections.indexOf(after);
        return sections.slice(index + 1).find(s => !isComplete(s)) || sections.find(s => !isComplete(s));
    }

    function afterSetDone(section) {
        updateSection(section);
        updateProgress();
        if (isComplete(section)) {
            const next = nextIncomplete(section);
            if (next) open(next, true);
        }
        if (!isCompleted && section.dataset.rest === 'yes') startRest();
    }

    // ===== EVENTS =====

    page.addEventListener('click', function(e) {
        const head = e.target.closest('.log-ex-head');
        if (head) {
            const section = head.closest('.log-ex');
            open(section.classList.contains('open') ? null : section, false);
            return;
        }

        const section = e.target.closest('.log-ex');
        if (!section) return;

        const check = e.target.closest('.set-check');
        if (check) {
            const row = check.closest('.set-row');
            const done = !row.classList.contains('done');
            setDone(row, done);
            queueSet(section, row);
            if (done) {
                afterSetDone(section);
            } else {
                updateSection(section);
                updateProgress();
            }
            return;
        }

        if (e.target.closest('.add-set')) {
            addRow(section).querySelector('.set-input')?.focus();
            updateSection(section);
            updateProgress();
            return;
        }

        if (e.target.closest('.all-done')) {
            tickAll(section);
            afterSetDone(section);
        }
    });

    // Remember the value before an edit so a change can carry over to the sets below
    page.addEventListener('focusin', function(e) {
        if (e.target.classList.contains('set-input')) e.target.dataset.before = e.target.value;
    });

    page.addEventListener('change', function(e) {
        const input = e.target;

        if (input.classList.contains('superset-rounds-input')) {
            const supersetId = input.dataset.supersetId;
            gm.queue.add(
                `${workoutId}:rounds:${supersetId}`,
                `/workouts/${workoutId}/superset/${supersetId}/update-reps`,
                { actual_reps: input.value || 0 },
                { workoutId }
            );
            return;
        }

        if (!input.classList.contains('set-input')) return;
        const row = input.closest('.set-row');
        const section = input.closest('.log-ex');

        // Sets below that still held the same value follow the change (e.g. weight for all sets)
        let below = row.nextElementSibling;
        while (below) {
            const other = below.querySelector(`.set-input[data-field="${input.dataset.field}"]`);
            if (other && !below.classList.contains('done') && other.value === input.dataset.before) {
                other.value = input.value;
            }
            below = below.nextElementSibling;
        }
        input.dataset.before = input.value;

        if (row.classList.contains('done')) queueSet(section, row);
    });

    // ===== REST TIMER =====

    const restChip = document.getElementById('rest-chip');
    const restTime = document.getElementById('rest-time');
    const restLabel = document.getElementById('rest-setting-label');
    let restSeconds = 90;
    let restEnds = 0;
    let restInterval = null;

    try {
        const stored = localStorage.getItem('gm-rest-seconds');
        if (stored !== null) restSeconds = parseInt(stored) || 0;
    } catch (e) { /* default */ }

    const clock = seconds => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

    function showRestSetting() {
        restLabel.textContent = restSeconds ? clock(restSeconds) : 'Off';
        document.querySelectorAll('#rest-options [data-rest-seconds]').forEach(option => {
            option.classList.toggle('active', parseInt(option.dataset.restSeconds) === restSeconds);
        });
    }

    function stopRest() {
        clearInterval(restInterval);
        restInterval = null;
        restChip.hidden = true;
        restChip.classList.remove('rest-over');
    }

    function tickRest() {
        const left = Math.ceil((restEnds - Date.now()) / 1000);
        if (left > 0) {
            restTime.textContent = clock(left);
            return;
        }
        clearInterval(restInterval);
        restInterval = null;
        restTime.textContent = 'Go';
        restChip.classList.add('rest-over');
        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
        setTimeout(() => { if (!restInterval) stopRest(); }, 5000);
    }

    function startRest() {
        if (!restSeconds) return;
        stopRest();
        restEnds = Date.now() + restSeconds * 1000;
        restChip.hidden = false;
        tickRest();
        restInterval = setInterval(tickRest, 250);
    }

    restChip.addEventListener('click', stopRest);
    document.getElementById('rest-options').addEventListener('click', function(e) {
        const option = e.target.closest('[data-rest-seconds]');
        if (!option) return;
        restSeconds = parseInt(option.dataset.restSeconds);
        try { localStorage.setItem('gm-rest-seconds', restSeconds); } catch (err) { /* not persisted */ }
        showRestSetting();
        if (!restSeconds) stopRest();
    });

    // ===== SAVE STATUS =====

    const syncStatus = document.getElementById('sync-status');

    function showSyncStatus(queue) {
        const waiting = queue.items.length;
        syncStatus.classList.toggle('waiting', waiting > 0 && !queue.sending);
        if (!waiting) {
            syncStatus.innerHTML = '<i class="fa-solid fa-cloud"></i> Saved';
        } else if (queue.needsLogin) {
            syncStatus.innerHTML = '<a href="/auth/login">Log in again</a> to save';
        } else if (queue.sending) {
            syncStatus.innerHTML = '<i class="fa-solid fa-rotate fa-spin"></i> Saving';
        } else {
            syncStatus.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> ${waiting} waiting to save`;
        }
    }

    gm.queue.onChange(showSyncStatus);

    // Sets ticked earlier that have not reached the server yet (page reloaded while offline)
    gm.queue.items.filter(item => item.workoutId === workoutId && item.entryId).forEach(item => {
        const section = document.getElementById(`log-ex-${item.entryId}`);
        if (!section) return;
        let row = section.querySelector(`.set-row[data-set="${item.number}"]`);
        while (!row && rowsOf(section).length < item.number) {
            const added = addRow(section);
            if (parseInt(added.dataset.set) === parseInt(item.number)) row = added;
        }
        if (!row) return;
        setDone(row, item.body.done !== false);
        row.querySelectorAll('.set-input').forEach(input => {
            if (item.body[input.dataset.field] !== undefined) input.value = item.body[input.dataset.field];
        });
    });

    // ===== FINISH =====

    const finishBtn = document.getElementById('finish-btn');
    const finishForm = document.getElementById('finish-form');

    function tickAll(section) {
        rowsOf(section).filter(row => !row.classList.contains('done')).forEach(row => {
            setDone(row, true);
            queueSet(section, row);
        });
        updateSection(section);
    }

    async function waitForSaves() {
        await gm.queue.flush();
        if (!gm.queue.items.some(item => item.workoutId === workoutId)) return true;
        gm.toast('Some sets are not saved yet. They are kept on this device; finish once you are back online.', 'danger');
        return false;
    }

    if (finishBtn) {
        finishBtn.addEventListener('click', async function() {
            finishBtn.disabled = true;
            const saved = await waitForSaves();
            finishBtn.disabled = false;
            if (!saved) return;

            const untouched = sections.filter(section => doneCount(section) === 0).length;
            if (!untouched) {
                if (await gm.confirm('Finish this workout?', { okLabel: 'Finish' })) finishForm.submit();
                return;
            }
            document.getElementById('finish-modal-text').textContent =
                `${untouched} of ${sections.length} exercises have no sets logged.`;
            bootstrap.Modal.getOrCreateInstance(document.getElementById('finish-modal')).show();
        });

        document.querySelectorAll('#finish-modal [data-finish]').forEach(button => {
            button.addEventListener('click', async function() {
                if (button.dataset.finish === 'shown') {
                    // Record the untouched exercises with the values on screen, then finish
                    sections.filter(section => doneCount(section) === 0).forEach(tickAll);
                    updateProgress();
                    if (!await waitForSaves()) {
                        bootstrap.Modal.getInstance(document.getElementById('finish-modal')).hide();
                        return;
                    }
                }
                finishForm.submit();
            });
        });
    }

    // Leaving an already-completed workout: make sure edits are on the server first
    const leaveBtn = document.getElementById('leave-btn');
    if (leaveBtn) {
        leaveBtn.addEventListener('click', async function(e) {
            if (!gm.queue.items.length) return;
            e.preventDefault();
            if (await waitForSaves()) window.location.href = leaveBtn.href;
        });
    }

    // ===== SCREEN WAKE LOCK =====
    // Keep the phone awake between sets; the lock is released by the browser when the tab is hidden.
    async function keepAwake() {
        if (isCompleted || !('wakeLock' in navigator) || document.hidden) return;
        try { await navigator.wakeLock.request('screen'); } catch (e) { /* not allowed: fine */ }
    }
    document.addEventListener('visibilitychange', keepAwake);
    keepAwake();

    // ===== INITIAL STATE =====

    sections.forEach(updateSection);
    updateProgress();
    showRestSetting();
    showSyncStatus(gm.queue);
    open(sections.find(section => !isComplete(section)) || null, false);
});
