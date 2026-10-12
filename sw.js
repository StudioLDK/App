// Die App ist nach app/ umgezogen. Dieser alte Hintergrunddienst räumt sich selbst auf,
// damit Browser, die die App schon einmal geöffnet hatten, die neue Startseite sehen.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
    .then(() => self.registration.unregister())
    .then(() => self.clients.matchAll({ type:'window' }))
    .then(cs => cs.forEach(c => c.navigate(c.url))));
});
