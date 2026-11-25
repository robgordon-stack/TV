// Minimal offline shell for the TV site. Bump CACHE when you change index.html.
const CACHE="tv-archive-v1",SHELL=["./","index.html","manifest.webmanifest"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==CACHE).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{const u=new URL(e.request.url);if(e.request.method!=="GET"||u.origin!==location.origin)return;
  const data=/\.json$/.test(u.pathname); // data: network first, fall back to cache
  e.respondWith(data?fetch(e.request).then(r=>{const c=r.clone();caches.open(CACHE).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request))
    :caches.match(e.request).then(r=>r||fetch(e.request)))});
