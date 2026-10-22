// Hintergrunddienst der App: hält die App-Oberfläche vor, damit sie schnell
// und auch bei schlechtem Netz startet. Daten von Supabase werden NIE
// zwischengespeichert, die kommen immer frisch.
const CACHE = 'ldk-app-v43';
const SHELL = ['./', './index.html', './impressum.html', './datenschutz.html', './anbieter.js', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png', './nuts_de.json', './vendor/supabase.js', './fonts/archivo-latin-wdth-normal.woff2', './fonts/archivo-latin-ext-wdth-normal.woff2'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return; // Supabase, Schriften usw. gehen direkt ins Netz

  if (req.mode === 'navigate') {
    // Seite: immer erst online versuchen, offline die gespeicherte Version zeigen
    // Nur die App selbst wird als index.html gemerkt, andere Seiten (z.B. Impressum) unter ihrem eigenen Namen
    const app = /\/(index\.html)?$/.test(url.pathname);
    const ziel = app ? './index.html' : req;
    e.respondWith(fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(ziel, copy)); }
      return res;
    }).catch(() => caches.match(ziel, { ignoreSearch:true }).then(hit => hit || caches.match('./index.html'))));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
