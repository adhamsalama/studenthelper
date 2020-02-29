// This is the "Offline page" service worker

const CACHE = "pwabuilder-page";
const offlineFallbackPage = '/';
const assets = [
    '/',
    '/profile',
    '/schedule',
    '/dues',
    '/notes',
    '/static/styles.css',
    '/static/subject_time.js',
    '/static/due.js',
    '/static/logo.png',
    'https://maxcdn.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
    'https://code.jquery.com/jquery-3.3.1.min.js'
];

// Install stage sets up the offline page in the cache and opens a new cache
self.addEventListener("install", function (event) {
  console.log("[PWA Builder] Install Event processing");

  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      console.log("[PWA Builder] Cached offline page during install");
      cache.addAll(assets);
    })
  );
});

// If any fetch fails, it will show the offline page.
self.addEventListener("fetch", function (event) {
  if (event.request.method !== "GET") return;

  event.respondWith(
    fetch(event.request).catch(function (error) {
      // The following validates that the request was for a navigation to a new document


      console.error("[PWA Builder] Network request Failed.");
      return caches.open(CACHE).then(function (cache) {
        return cache.match(event.request);
      });
    })
  );
});


// This is an event that can be fired from your page to tell the SW to update the offline page
self.addEventListener("refreshOffline", function () {
  const req = new Request('/');

  return fetch(req).then(function (response) {
    return caches.open(CACHE).then(function (cache) {
      console.log("[PWA Builder] Offline page updated from refreshOffline event: " + response.url);
      return cache.put(req, response);
    });
  });
});
