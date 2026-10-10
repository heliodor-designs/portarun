/* PortaRun service worker — offline app shell + last-fetched data.
 *
 * Strategy: stale-while-revalidate for same-origin requests (instant loads,
 * refreshed in the background), network-only for cross-origin map tiles (never
 * worth caching, and their opaque responses would bloat storage). Bump CACHE
 * to invalidate old assets after a deploy. */
const CACHE = 'portarun-v3';
const SHELL = [
  './',
  './index.html',
  './config.js',
  './manifest.webmanifest',
  './vendor/leaflet/leaflet.css',
  './vendor/leaflet/leaflet.js',
  './icons/icon-180.png',
  './icons/icon-192.png',
  './icons/icon-512.png',
  'data/potties.geojson',
];

self.addEventListener('install', (event) => {
  // Cache each item independently so one missing file (e.g. data not built
  // yet) doesn't abort the whole install.
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => Promise.allSettled(SHELL.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // let map tiles hit network

  // The dataset refreshes once daily — go network-first so an installed PWA
  // shows the new data on the next open, falling back to cache only offline.
  if (url.pathname.endsWith('/data/potties.geojson')) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // App shell: stale-while-revalidate for instant loads.
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(() => cached); // offline: fall back to whatever we cached
      return cached || network;
    })
  );
});
