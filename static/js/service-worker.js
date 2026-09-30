const VERSION = 'stroyma-pwa-v14';
const SHELL_CACHE = `${VERSION}-shell`;
const PUBLIC_CACHE = `${VERSION}-public`;
const MEDIA_CACHE = `${VERSION}-media`;
const OFFLINE_URL = '/static/pwa/offline.html';
const SHELL_URLS = [
    OFFLINE_URL, '/static/pwa/icon-192.png', '/static/pwa/icon-512.png',
];

async function storeResponse(cacheName, request, response, limit) {
    if (!response.ok || response.type !== 'basic' || response.headers.get('cache-control')?.includes('no-store')) return;
    try {
        const cache = await caches.open(cacheName);
        await cache.put(request, response);
        const keys = await cache.keys();
        const removable = keys.filter(key => cacheName !== SHELL_CACHE ||
            !SHELL_URLS.some(url => new URL(url, self.location.origin).href === key.url));
        await Promise.all(removable.slice(0, Math.max(0, keys.length - limit)).map(key => cache.delete(key)));
    } catch (_) { /* Storage quotas must not interrupt browsing. */ }
}

// Only informational pages are kept for reading offline. Orders, account,
// cart, forms and search responses must always come from the server.
const PUBLIC_PATHS = [
    /^\/catalog\/$/, /^\/category\/[^/]+\/$/, /^\/product\/[^/]+\/$/,
    /^\/$/, /^\/services\/$/, /^\/services\/[^/]+\/$/, /^\/about\/$/, /^\/contact\/$/,
    /^\/(?:policy|cookies-policy|offer|delivery|returns)\/$/
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
    if (url.origin !== self.location.origin) return;

    if (request.mode === 'navigate') {
        event.respondWith((async () => {
            const canCache = !url.search && PUBLIC_PATHS.some(pattern => pattern.test(url.pathname));
            try {
                const response = await fetch(request);
                if (canCache && response.ok && response.type === 'basic' &&
                    response.headers.get('content-type')?.includes('text/html') &&
                    !response.headers.get('cache-control')?.includes('no-store')) {
                    const savedResponse = response.clone();
                    event.waitUntil((async () => {
                        const html = await savedResponse.clone().text();
                        const isPublic = html.includes('<meta name="pwa-cache" content="public">') &&
                            !html.includes('name="csrfmiddlewaretoken"');
                        if (isPublic) {
                            await storeResponse(PUBLIC_CACHE, request, savedResponse, 30);
                        }
                    })().catch(() => {}));
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
            // Versioned code and new optimized assets have stable URLs. Reuse
            // them immediately; HTML and unversioned code still check the server.
            const versioned = url.searchParams.has('v') || /\.(?:woff2|png|webp|jpe?g|svg)$/.test(url.pathname);
            if (versioned) {
                const saved = await caches.match(request, { cacheName: SHELL_CACHE });
                if (saved) return saved;
            }
            try {
                const response = await fetch(request);
                event.waitUntil(storeResponse(SHELL_CACHE, request, response.clone(), 120));
                return response;
            } catch (_) {
                return (await caches.match(request)) || Response.error();
            }
        })());
        return;
    }

    if (/^\/media\/(?:products|category_images|services|service_photos)\//.test(url.pathname) && request.destination === 'image') {
        event.respondWith((async () => {
            if (url.pathname.includes('/.thumbnails/')) {
                const saved = await caches.match(request, { cacheName: MEDIA_CACHE });
                if (saved) return saved;
            }
            try {
                const response = await fetch(request);
                event.waitUntil(storeResponse(MEDIA_CACHE, request, response.clone(), 60));
                return response;
            } catch (_) {
                return (await caches.match(request)) || Response.error();
            }
        })());
    }
});
