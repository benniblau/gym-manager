// Shared page behavior: CSRF on fetch and forms, toasts, confirm dialog, service worker.
(function() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    // ===== FETCH WRAPPER =====
    // Same-origin requests carry the CSRF token and a marker header so the
    // server answers errors as JSON instead of HTML pages.
    const nativeFetch = window.fetch.bind(window);
    window.fetch = function(input, init = {}) {
        const url = new URL(typeof input === 'string' ? input : input.url, window.location.href);
        if (url.origin === window.location.origin) {
            const headers = new Headers(init.headers || {});
            headers.set('X-Requested-With', 'fetch');
            if ((init.method || 'GET').toUpperCase() !== 'GET') headers.set('X-CSRFToken', csrfToken);
            init = { ...init, headers };
        }
        return nativeFetch(input, init);
    };

    // POST JSON or form data and return the parsed JSON; throws Error(message) on failure.
    async function post(url, body) {
        const init = { method: 'POST' };
        if (body instanceof FormData || body instanceof URLSearchParams) {
            init.body = body;
        } else if (body !== undefined) {
            init.body = JSON.stringify(body);
            init.headers = { 'Content-Type': 'application/json' };
        }
        const response = await fetch(url, init);
        let data = {};
        try { data = await response.json(); } catch (e) { /* non-JSON error page */ }
        if (!response.ok || data.error) {
            throw new Error(data.error || `Request failed (${response.status})`);
        }
        return data;
    }

    // ===== TOASTS =====
    function toast(message, type = 'info') {
        const container = document.getElementById('gm-toasts');
        const el = document.createElement('div');
        el.className = `toast gm-toast gm-toast-${type}`;
        el.setAttribute('role', type === 'danger' ? 'alert' : 'status');
        const body = document.createElement('div');
        body.className = 'toast-body';
        body.textContent = message;
        el.appendChild(body);
        container.appendChild(el);
        el.addEventListener('hidden.bs.toast', () => el.remove());
        new bootstrap.Toast(el, { delay: type === 'danger' ? 6000 : 2500 }).show();
    }

    // ===== CONFIRM DIALOG =====
    function confirmDialog(message, { okLabel = 'OK', danger = false } = {}) {
        return new Promise(resolve => {
            const el = document.getElementById('gm-confirm');
            const ok = document.getElementById('gm-confirm-ok');
            document.getElementById('gm-confirm-message').textContent = message;
            ok.textContent = okLabel;
            ok.className = `btn btn-touch flex-fill ${danger ? 'btn-danger' : 'btn-primary'}`;
            const modal = bootstrap.Modal.getOrCreateInstance(el);
            let answer = false;
            const onOk = () => { answer = true; modal.hide(); };
            ok.addEventListener('click', onOk);
            el.addEventListener('hidden.bs.modal', () => {
                ok.removeEventListener('click', onOk);
                resolve(answer);
            }, { once: true });
            modal.show();
        });
    }

    // ===== FORMS =====
    // <form data-confirm="Delete?" data-confirm-ok="Delete" data-confirm-danger> asks first.
    // Any POST form without a CSRF field gets one, so no form can be forgotten.
    document.addEventListener('submit', function(event) {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) return;

        if ((form.getAttribute('method') || '').toUpperCase() === 'POST' && !form.querySelector('[name="csrf_token"]')) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'csrf_token';
            input.value = csrfToken;
            form.appendChild(input);
        }

        if (form.dataset.confirm && !form.dataset.confirmed) {
            event.preventDefault();
            const submitter = event.submitter;
            confirmDialog(form.dataset.confirm, {
                okLabel: form.dataset.confirmOk || 'OK',
                danger: 'confirmDanger' in form.dataset,
            }).then(yes => {
                if (!yes) return;
                form.dataset.confirmed = '1';
                if (form.requestSubmit) form.requestSubmit(submitter || undefined);
                else form.submit();
            });
        }
    });

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    // ===== SAVE QUEUE =====
    // Writes that must survive a dropped connection (logged sets). Items are kept
    // in localStorage and sent in order; a newer item with the same key replaces
    // an unsent older one. Requests must be safe to repeat.
    const QUEUE_KEY = 'gm-save-queue';
    const queue = {
        items: [],
        sending: false,
        running: null,
        needsLogin: false,
        listeners: [],

        load() {
            try { this.items = JSON.parse(localStorage.getItem(QUEUE_KEY)) || []; } catch (e) { this.items = []; }
        },
        persist() {
            try { localStorage.setItem(QUEUE_KEY, JSON.stringify(this.items)); } catch (e) { /* storage unavailable: memory only */ }
            this.listeners.forEach(listener => listener(this));
        },
        onChange(listener) { this.listeners.push(listener); },
        add(key, url, body, meta = {}) {
            this.items = this.items.filter(item => item.key !== key);
            this.items.push({ key, url, body, ...meta });
            this.persist();
            this.flush();
        },
        // Send everything that is waiting. Resolves when the queue is empty or sending had to stop.
        // Calls made while a send is running wait for that same run.
        flush() {
            if (!this.running) {
                this.running = this.sendAll().finally(() => { this.running = null; });
            }
            return this.running;
        },
        async sendAll() {
            this.sending = true;
            this.persist();
            while (this.items.length) {
                const item = this.items[0];
                let response;
                try {
                    response = await fetch(item.url, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(item.body),
                    });
                } catch (e) {
                    break;  // offline: keep everything, try again later
                }
                const isJson = (response.headers.get('Content-Type') || '').includes('json');
                if (response.redirected || (response.ok && !isJson)) {
                    this.needsLogin = true;  // session ended: got the login page instead
                    break;
                }
                if (response.status >= 500) break;
                this.needsLogin = false;
                if (!response.ok) {
                    let message = `Could not save (${response.status})`;
                    try { message = (await response.json()).error || message; } catch (e) { /* keep default */ }
                    toast(message, 'danger');
                }
                // Done (or rejected for good): drop it unless a newer item replaced it meanwhile
                if (this.items[0] === item) this.items.shift();
                this.persist();
            }
            this.sending = false;
            this.persist();
        },
    };
    queue.load();
    window.addEventListener('online', () => queue.flush());
    document.addEventListener('visibilitychange', () => { if (!document.hidden) queue.flush(); });
    setInterval(() => { if (queue.items.length) queue.flush(); }, 10000);
    if (queue.items.length) queue.flush();

    window.gm = { post, toast, confirm: confirmDialog, escapeHtml, csrfToken, queue };

    // ===== SERVICE WORKER =====
    if ('serviceWorker' in navigator && window.isSecureContext) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js').catch(() => {});
        });
    }
})();
