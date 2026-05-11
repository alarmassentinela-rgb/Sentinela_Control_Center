// GolfBookVIP Service Worker
// Strategy:
//   - Static assets  → Cache First (CSS, JS, fonts, images)
//   - API calls      → Network First (always fresh, offline fallback)
//   - Pages (HTML)   → Network First + offline fallback page

const CACHE_NAME = 'golfbookvip-v3'
const OFFLINE_URL = '/offline.html'

// Resources to pre-cache on install
const PRECACHE_URLS = [
  OFFLINE_URL,
  '/manifest.json',
  '/icons/icon-192.svg',
  '/icons/icon-512.svg',
]

// ─── Install ──────────────────────────────────────────────────────────────────

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  )
  self.skipWaiting()
})

// ─── Activate ─────────────────────────────────────────────────────────────────

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  )
  self.clients.claim()
})

// ─── Message handler — allow client to trigger immediate activation ──────────

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

// ─── Fetch ────────────────────────────────────────────────────────────────────

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET and cross-origin (except our API)
  if (request.method !== 'GET') return

  // API calls → Network First
  if (url.pathname.startsWith('/api/') || url.hostname !== self.location.hostname) {
    event.respondWith(networkFirst(request))
    return
  }

  // Next.js internals (_next/data, _next/webpack-hmr) → network only
  if (url.pathname.startsWith('/_next/webpack-hmr')) return

  // Static assets (_next/static, icons, fonts) → Cache First
  if (
    url.pathname.startsWith('/_next/static/') ||
    url.pathname.startsWith('/icons/') ||
    url.pathname.match(/\.(png|svg|ico|webp|jpg|jpeg|woff2?|ttf)$/)
  ) {
    event.respondWith(cacheFirst(request))
    return
  }

  // HTML pages → Network First with offline fallback
  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirstWithOfflineFallback(request))
    return
  }

  // Everything else → Network First
  event.respondWith(networkFirst(request))
})

// ─── Strategies ───────────────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request)
  if (cached) return cached

  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    return new Response('Recurso no disponible offline', { status: 503 })
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    const cached = await caches.match(request)
    if (cached) return cached
    return new Response(JSON.stringify({ detail: 'Sin conexión' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}

async function networkFirstWithOfflineFallback(request) {
  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    const cached = await caches.match(request)
    if (cached) return cached
    const offlinePage = await caches.match(OFFLINE_URL)
    return offlinePage || new Response('<h1>Sin conexión</h1>', {
      headers: { 'Content-Type': 'text/html' },
    })
  }
}

// ─── Background Sync (for score submissions) ──────────────────────────────────

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-scores') {
    event.waitUntil(syncPendingScores())
  }
})

async function syncPendingScores() {
  // Reads pending scores from IndexedDB and sends them when online
  // (Requires app-side code to queue scores in IDB when offline)
  try {
    const db = await openIDB()
    const pending = await getAllPending(db)
    for (const item of pending) {
      try {
        await fetch(item.url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${item.token}` },
          body: JSON.stringify(item.data),
        })
        await deleteFromIDB(db, item.id)
      } catch {
        // Will retry on next sync
      }
    }
  } catch {
    // IDB not available
  }
}

// ─── Push Notifications ───────────────────────────────────────────────────────

self.addEventListener('push', (event) => {
  if (!event.data) return
  let payload
  try { payload = event.data.json() } catch { payload = { title: 'GolfBookVIP', body: event.data.text() } }

  event.waitUntil(
    self.registration.showNotification(payload.title || 'GolfBookVIP', {
      body: payload.body || '',
      icon: '/icons/icon-192.svg',
      badge: '/icons/icon-192.svg',
      data: payload.data || {},
      vibrate: [200, 100, 200],
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      return clients.openWindow(url)
    })
  )
})

// ─── IDB helpers (for background sync) ───────────────────────────────────────

function openIDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('golfbookvip-sync', 1)
    req.onupgradeneeded = (e) => {
      e.target.result.createObjectStore('pending', { keyPath: 'id', autoIncrement: true })
    }
    req.onsuccess = (e) => resolve(e.target.result)
    req.onerror = reject
  })
}

function getAllPending(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending', 'readonly')
    const req = tx.objectStore('pending').getAll()
    req.onsuccess = (e) => resolve(e.target.result)
    req.onerror = reject
  })
}

function deleteFromIDB(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending', 'readwrite')
    tx.objectStore('pending').delete(id).onsuccess = resolve
    tx.onerror = reject
  })
}
