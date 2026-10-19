const VERSION='__BUILD_VERSION__',PAGES='love-pages-'+VERSION,MEDIA='love-media-'+VERSION,PRECACHE=__PRECACHE__;
self.addEventListener('install',event=>{event.waitUntil(caches.open(PAGES).then(cache=>cache.addAll(PRECACHE)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('love-')&&![PAGES,MEDIA].includes(key)).map(key=>caches.delete(key)))).then(()=>self.clients.claim()))});
async function put(cacheName,request,response,limit){if(!response.ok)return;try{const cache=await caches.open(cacheName);await cache.put(request,response);const keys=await cache.keys();await Promise.all(keys.slice(0,Math.max(0,keys.length-limit)).map(key=>cache.delete(key)))}catch{}}
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);if(request.method!=='GET'||url.origin!==location.origin||url.pathname.startsWith('/api/')||request.destination==='audio'||request.destination==='video')return;
 if(request.mode==='navigate'){event.respondWith(fetch(request).then(response=>{event.waitUntil(put(PAGES,request,response.clone(),30));return response}).catch(async()=>await caches.match(request)||await caches.match('offline.html')));return}
 if(request.destination==='image'){event.respondWith(caches.match(request).then(cached=>cached||fetch(request).then(response=>{event.waitUntil(put(MEDIA,request,response.clone(),48));return response})));return}
 event.respondWith(fetch(request).then(response=>{event.waitUntil(put(PAGES,request,response.clone(),80));return response}).catch(async()=>{const cached=await caches.match(request,{ignoreSearch:true});if(cached)return cached;return new Response('',{status:503,statusText:'Offline'})}));
});
