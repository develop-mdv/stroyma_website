const VERSION = 'stroyma-pwa-v12';
const SHELL_CACHE = `${VERSION}-shell`;
const PUBLIC_CACHE = `${VERSION}-public`;
const MEDIA_CACHE = `${VERSION}-media`;
const OFFLINE_URL = '/static/pwa/offline.html';
const SHELL_URLS = [
    OFFLINE_URL, '/static/pwa/icon-192.png', '/static/pwa/icon-512.png',
    '/static/css/tailwind.css?v=1', '/static/css/base.css?v=5', '/static/css/mobile.css?v=9',
    '/static/css/home.css?v=9', '/static/css/catalog.css?v=3',
    '/static/vendor/fonts/inter/wght.css?v=1', '/static/vendor/fonts/outfit/wght.css?v=1',
    '/static/vendor/fonts/inter/files/inter-cyrillic-wght-normal.woff2',
    '/static/vendor/fonts/inter/files/inter-latin-wght-normal.woff2',
    '/static/vendor/fonts/outfit/files/outfit-latin-wght-normal.woff2',
    '/static/vendor/fontawesome/css/all.min.css?v=1',
    '/static/vendor/fontawesome/webfonts/fa-solid-900.woff2',
    '/static/vendor/fontawesome/webfonts/fa-regular-400.woff2',
    '/static/vendor/fontawesome/webfonts/fa-brands-400.woff2',
    '/static/js/base.js?v=3', '/static/js/pwa.js?v=3', '/static/js/phone-input.js?v=6',
    '/static/js/home.js?v=12', '/static/js/catalog.js?v=5',
    '/static/images/concrete_texture.jpg', '/static/images/home_materials_hero.webp',
    '/static/images/logo-ma.png?v=2'
];
const EXTERNAL_ASSET_HOSTS = new Set(['cdn.jsdelivr.net']);

// Only informational pages are kept for reading offline. Orders, account,
// cart, forms and search responses must always come from the server.
const PUBLIC_PATHS = [
    /^\/catalog\/$/, /^\/category\/[^/]+\/$/, /^\/product\/[^/]+\/$/,
    /^\/$/, /^\/services\/$/, /^\/services\/[^/]+\/$/, /^\/about\/$/, /^\/contact\/$/,
    /^\/(?:policy|cookies-policy|offer|payment|delivery|returns)\/$/
];

self.addEventListener('install', event => {
    event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
    event.waitUntil(Promise.all([
        caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('stroyma-pwa-') && !key.startsWith(VERSION)).map(key => caches.delete(key)))),
        self.clients.claim()
    ]));
});

self.addEventListener('fetch', event => {
    const request = event.request;
    if (request.method !== 'GET') return;
    const url = new URL(request.url);
    if (url.origin !== self.location.origin) {
        if (!EXTERNAL_ASSET_HOSTS.has(url.hostname)) return;
        event.respondWith((async () => {
            const saved = await caches.match(request);
            if (saved) return saved;
            const response = await fetch(request);
            if (response.ok || response.type === 'opaque') {
                try {
                    const cache = await caches.open(SHELL_CACHE);
                    await cache.put(request, response.clone());
                } catch (_) { /* A full cache must not hide a successful response. */ }
            }
            return response;
        })());
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith((async () => {
            const canCache = !url.search && PUBLIC_PATHS.some(pattern => pattern.test(url.pathname));
            try {
                const response = await fetch(request);
                if (canCache && response.ok && response.type === 'basic' &&
                    response.headers.get('content-type')?.includes('text/html') &&
                    !response.headers.get('cache-control')?.includes('no-store')) {
                    try {
                        const html = await response.clone().text();
                        const isPublic = html.includes('<meta name="pwa-cache" content="public">') &&
                            !html.includes('name="csrfmiddlewaretoken"');
                        if (isPublic) {
                            const cache = await caches.open(PUBLIC_CACHE);
                            await cache.put(request, response.clone());
                        }
                    } catch (_) { /* Keep the network response when storage is unavailable. */ }
                }
                return response;
            } catch (_) {
                if (canCache) {
                    const saved = await caches.match(request);
                    if (saved) return saved;
                }
                return (await caches.match(OFFLINE_URL)) || Response.error();
            }
        })());
        return;
    }

    if (url.pathname.startsWith('/static/') && !url.pathname.startsWith('/static/admin/')) {
        event.respondWith((async () => {
            try {
                const response = await fetch(request);
                if (response.ok && response.type === 'basic') {
                    try {
                        const cache = await caches.open(SHELL_CACHE);
                        await cache.put(request, response.clone());
                    } catch (_) { /* Keep the network response when storage is unavailable. */ }
                }
                return response;
            } catch (_) {
                return (await caches.match(request)) || Response.error();
            }
        })());
        return;
    }

    if (/^\/media\/(?:products|category_images|services|service_photos)\//.test(url.pathname) && request.destination === 'image') {
        event.respondWith((async () => {
            try {
                const response = await fetch(request);
                if (response.ok && response.type === 'basic') {
                    try {
                        const cache = await caches.open(MEDIA_CACHE);
                        await cache.put(request, response.clone());
                        const keys = await cache.keys();
                        if (keys.length > 60) await cache.delete(keys[0]);
                    } catch (_) { /* Keep the network image when storage is unavailable. */ }
                }
                return response;
            } catch (_) {
                return (await caches.match(request)) || Response.error();
            }
        })());
    }
});
