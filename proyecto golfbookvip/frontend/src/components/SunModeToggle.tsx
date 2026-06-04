'use client'
import { useState, useEffect } from 'react'

const KEY = 'gbv-sun-mode'

/**
 * Botón flotante "Modo Sol": alto contraste para leer la app bajo el sol
 * en el campo. Pone data-theme="sun" en <html>; el override vive en globals.css.
 * Se persiste en localStorage para que quede como el usuario lo dejó.
 */
export default function SunModeToggle() {
  const [on, setOn] = useState(false)

  useEffect(() => {
    setOn(document.documentElement.getAttribute('data-theme') === 'sun')
  }, [])

  function toggle() {
    const next = !on
    setOn(next)
    if (next) {
      document.documentElement.setAttribute('data-theme', 'sun')
      try { localStorage.setItem(KEY, '1') } catch {}
    } else {
      document.documentElement.removeAttribute('data-theme')
      try { localStorage.setItem(KEY, '0') } catch {}
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label={on ? 'Desactivar Modo Sol' : 'Activar Modo Sol'}
      title={on ? 'Modo Sol activado — tócame para volver al oscuro' : 'Modo Sol — alto contraste para el campo'}
      className={`fixed bottom-6 left-6 z-50 h-14 px-4 rounded-full shadow-lg flex items-center gap-2 font-semibold text-sm transition-all duration-200 active:scale-95 ${
        on
          ? 'bg-amber-400 text-zinc-900 ring-2 ring-amber-300'
          : 'bg-zinc-800/90 text-amber-300 ring-1 ring-zinc-600 backdrop-blur'
      }`}
    >
      <span className="text-xl leading-none">{on ? '☀️' : '🌙'}</span>
      <span>Modo Sol</span>
    </button>
  )
}
