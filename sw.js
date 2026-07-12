const CACHE_NAME = 'daves-field-report-v1';

self.addEventListener('install', () => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;
    event.respondWith(
        caches.open(CACHE_NAME).then(async (cache) => {
            try {
                const networkResponse = await fetch(event.request);
                cache.put(event.request, networkResponse.clone());
                return networkResponse;
            } catch (err) {
                const cachedResponse = await cache.match(event.request);
                if (cachedResponse) return cachedResponse;
                throw err;
            }
        })
    );
});
