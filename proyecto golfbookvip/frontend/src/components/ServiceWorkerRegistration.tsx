'use client'
import { useEffect } from 'react'

export default function ServiceWorkerRegistration() {
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js', { scope: '/' })
        .then((registration) => {
          // Check for updates every hour
          setInterval(() => registration.update(), 3_600_000)
        })
        .catch(() => {
          // SW registration failed silently (private mode, etc.)
        })
    }
  }, [])

  return null
}
