// SETU service worker — precache the app shell so the PWA loads with no
// connectivity after the first visit (offline is a headline SETU feature).

const CACHE = "setu-shell-v1";
const SHELL = [
  "./index.html",
  "./app.js",
  "./manifest.webmanifest",
  "./icon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // never cache API calls (/translate, /languages) — they hit the local engine
  if (url.pathname === "/translate" || url.pathname === "/languages") return;
  // app shell: cache-first so it works fully offline after first load
  event.respondWith(
    caches.match(event.request).then((hit) => hit || fetch(event.request))
  );
});
