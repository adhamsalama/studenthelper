// This is the "Offline page" service worker

const CACHE = "pwabuilder-page";
const offlineFallbackPage = '/';
const assets = [
    '/',
    '/profile',
    '/schedule',
    '/dues',
    '/notes',
    'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js'
];
// TODO: replace the following with the correct offline fallback page i.e.: const offlineFallbackPage = "offline.html";
//const offlineFallbackPage = "index.html";

// Install stage sets up the offline page in the cache and opens a new cache
self.addEventListener("install", function (event) {
  console.log("[PWA Builder] Install Event processing");

  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      console.log("[PWA Builder] Cached offline page during install");

      /*if (offlineFallbackPage === "index.html") {
        return cache.add(new Response("TODO: Update the value of the offlineFallbackPage constant in the serviceworker."));
      }
      
      return cache.add(offlineFallbackPage);*/
      cache.addAll(assets);
      console.log(assets.length);
      /*for(let i = 0; i < assets.length; i++)
      {
          console.log(assets[i]);
      cache.add(assets[i]);
      }*/
    })
  );
  console.log("Done");
});

// If any fetch fails, it will show the offline page.
self.addEventListener("fetch", function (event) {
  event.respondWith(
    caches.match(event.request).then(cacheRes =>{
      return cacheRes || fetch(event.request)
    })
  )
});

// This is an event that can be fired from your page to tell the SW to update the offline page
/*self.addEventListener("refreshOffline", function () {
  const offlinePageRequest = new Request(offlineFallbackPage);

  return fetch(offlineFallbackPage).then(function (response) {
    return caches.open(CACHE).then(function (cache) {
      console.log("[PWA Builder] Offline page updated from refreshOffline event: " + response.url);
      return cache.put(offlinePageRequest, response);
    });
  });
});*/