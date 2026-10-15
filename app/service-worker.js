/**
 * Focus Flow service worker.
 *
 * Makes the app installable and fully usable offline. The static shell is
 * precached on install; navigation requests are network-first with a cached
 * `index.html` fallback, while the precached assets are cache-first.
 *
 * Privacy: only same-origin, GET requests are ever handled. Cross-origin and
 * non-GET requests fall through to the network untouched, so no third-party
 * traffic is cached, proxied, or inspected, and no telemetry is sent.
 */

const CACHE_NAME = "focus-flow-v14";

const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./styles.css",
  "./main.js",
  "./timer.js",
  "./history.js",
  "./ambient.js",
  "./i18n.js",
  "./manifest.webmanifest",
  "./healthz",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;

  // Never touch non-GET or cross-origin requests.
  if (request.method !== "GET") {
    return;
  }
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  // Network-first for navigations, falling back to the cached shell.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches
            .open(CACHE_NAME)
            .then((cache) => cache.put("./index.html", copy))
            .catch(() => {});
          return response;
        })
        .catch(() =>
          caches
            .match(request)
            .then((cached) => cached || caches.match("./index.html"))
            .then((cached) => cached || Response.error()),
        ),
    );
    return;
  }

  // Cache-first for the precached static assets.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request).then((response) => {
        if (response && response.status === 200 && response.type === "basic") {
          const copy = response.clone();
          caches
            .open(CACHE_NAME)
            .then((cache) => cache.put(request, copy))
            .catch(() => {});
        }
        return response;
      });
    }),
  );
});
