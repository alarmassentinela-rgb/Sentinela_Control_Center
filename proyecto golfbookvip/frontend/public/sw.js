// GolfBookVIP Service Worker — KILL SWITCH (v5)
// El SW v3 dejó cache rota (chunks de builds anteriores). Este SW:
//   1. Toma control inmediato (skipWaiting + clients.claim)
//   2. Borra TODOS los caches viejos
//   3. NO intercepta fetch — el browser usa network directo
// Cuando los chunks nuevos cargan limpios, podemos volver a habilitar caching.

const CACHE_NAME = 'golfbookvip-v5-killer'

self.addEventListener('install', (event) => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys()
      await Promise.all(keys.map((key) => caches.delete(key)))
      await self.clients.claim()
      const clients = await self.clients.matchAll({ type: 'window' })
      clients.forEach((c) => c.navigate(c.url))
    })()
  )
})

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

// NO fetch handler intencionalmente — browser maneja todas las requests directamente.
