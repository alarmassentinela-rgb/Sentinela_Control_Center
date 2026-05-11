'use client'
import { useEffect } from 'react'

export default function ServiceWorkerRegistration() {
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return

    let refreshing = false
    const onControllerChange = () => {
      if (refreshing) return
      refreshing = true
      window.location.reload()
    }
    navigator.serviceWorker.addEventListener('controllerchange', onControllerChange)

    // Si la página viene de BFCache (back/forward navigation), forzar refresh
    // del SW y verificar si hay versión nueva. Esto evita ver snapshots viejos.
    const onPageShow = (e: PageTransitionEvent) => {
      if (e.persisted) {
        navigator.serviceWorker.getRegistration().then(r => r?.update())
      }
    }
    window.addEventListener('pageshow', onPageShow)

    navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then((registration) => {
        // Si ya hay un SW esperando (nueva versión instalada), tomar control
        if (registration.waiting) {
          registration.waiting.postMessage({ type: 'SKIP_WAITING' })
        }
        // Detectar nuevas versiones
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing
          if (!newWorker) return
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // Nueva versión instalada, hay un SW controlando — pedir activación
              newWorker.postMessage({ type: 'SKIP_WAITING' })
            }
          })
        })
        // Check for updates each hour Y al recuperar foco
        setInterval(() => registration.update(), 3_600_000)
        const onVisible = () => {
          if (document.visibilityState === 'visible') registration.update()
        }
        document.addEventListener('visibilitychange', onVisible)
      })
      .catch(() => {
        // SW registration failed silently (private mode, etc.)
      })

    return () => {
      navigator.serviceWorker.removeEventListener('controllerchange', onControllerChange)
      window.removeEventListener('pageshow', onPageShow)
    }
  }, [])

  return null
}
