// Service worker (served as /sw.js): keeps the app shell available offline.
// Pages themselves are always fetched fresh; only static files are cached.
// Bump VERSION when the list of shell files changes.
const VERSION = 'gm-shell-v1';

const SHELL = [
    '/offline',
    '/static/vendor/bootstrap.min.css',
    '/static/vendor/bootstrap.bundle.min.js',
    '/static/fontawesome/css/fontawesome.min.css',
    '/static/fontawesome/css/solid.min.css',
    '/static/fontawesome/css/brands.min.css',
    '/static/css/custom.css',
    '/static/js/app.js',
    '/static/svg/ARISE.svg',
];

// Files that change with a deploy: prefer the network, fall back to the cache
const FRESH_FIRST = ['/static/css/', '/static/js/'];

self.addEventListener('install', event => {
    event.waitUntil(caches.open(VERSION).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(keys.filter(key => key !== VERSION).map(key => caches.delete(key))))
            .then(() => self.clients.claim())
    );
});

async function fromNetwork(request) {
    const response = await fetch(request);
    if (response.ok) {
        const cache = await caches.open(VERSION);
        cache.put(request, response.clone());
    }
    return response;
}

self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    if (request.method !== 'GET' || url.origin !== self.location.origin) return;

    if (request.mode === 'navigate') {
        // Never cache pages (they are per-user); show the offline page when the network is gone
        event.respondWith(fetch(request).catch(() => caches.match('/offline')));
        return;
    }

    if (!url.pathname.startsWith('/static/')) return;

    if (FRESH_FIRST.some(prefix => url.pathname.startsWith(prefix))) {
        event.respondWith(fromNetwork(request).catch(() => caches.match(request)));
    } else {
        // Vendor files, fonts and images: serve the cached copy, refresh it in the background
        event.respondWith(
            caches.match(request).then(cached => {
                const refreshed = fromNetwork(request).catch(() => cached);
                return cached || refreshed;
            })
        );
    }
});
