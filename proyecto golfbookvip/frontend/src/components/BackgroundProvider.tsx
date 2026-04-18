'use client'
import { usePathname } from 'next/navigation'
import { useState, useEffect, useRef } from 'react'

const OVERLAY =
  'linear-gradient(to bottom, rgba(9,9,11,0.55) 0%, rgba(9,9,11,0.40) 35%, rgba(9,9,11,0.55) 100%)'

function getBg(pathname: string): string {
  if (/\/auth\//.test(pathname))                return '/golf-auth.jpg'
  if (/\/rounds\/[^/]+\/play/.test(pathname))   return '/golf-play.jpg'
  if (/\/rounds\/new/.test(pathname))            return '/golf-new.jpg'
  if (/\/rounds\/[^/]+/.test(pathname))          return '/golf-detail.jpg'
  if (/\/rounds/.test(pathname))                 return '/golf-rounds.jpg'
  if (/\/dashboard/.test(pathname))              return '/golf-dashboard.jpg'
  if (/\/profile/.test(pathname))                return '/golf-profile.jpg'
  return '/golf-bg.jpg'
}

export default function BackgroundProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const [base, setBase]               = useState<string>(() => getBg(pathname))
  const [next, setNext]               = useState<{ src: string; key: number } | null>(null)
  const [nextVisible, setNextVisible] = useState(false)
  const timerRef    = useRef<ReturnType<typeof setTimeout> | null>(null)
  const keyRef      = useRef(0)
  const currentRef  = useRef(getBg(pathname))

  useEffect(() => {
    const newBg = getBg(pathname)
    if (newBg === currentRef.current) return
    currentRef.current = newBg

    if (timerRef.current) clearTimeout(timerRef.current)

    keyRef.current += 1
    setNext({ src: newBg, key: keyRef.current })
    setNextVisible(false)

    // Allow the new div to mount at opacity-0, then fade it in
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setNextVisible(true))
    })

    // After fade completes: promote next → base, remove overlay
    timerRef.current = setTimeout(() => {
      setBase(newBg)
      setNext(null)
      setNextVisible(false)
    }, 750)
  }, [pathname])

  return (
    <>
      {/* Base layer */}
      <div
        className="fixed inset-0 bg-cover bg-no-repeat"
        style={{
          backgroundImage:    `url('${base}')`,
          backgroundPosition: 'center 30%',
          backgroundAttachment: 'fixed',
          zIndex: -20,
        }}
      />

      {/* Transition layer — cross-fades in on route change */}
      {next && (
        <div
          key={next.key}
          className="fixed inset-0 bg-cover bg-no-repeat"
          style={{
            backgroundImage:    `url('${next.src}')`,
            backgroundPosition: 'center 30%',
            backgroundAttachment: 'fixed',
            opacity:    nextVisible ? 1 : 0,
            transition: 'opacity 0.7s ease',
            zIndex: -19,
          }}
        />
      )}

      {/* Dark gradient overlay — always visible above background layers */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{ background: OVERLAY, zIndex: -10 }}
      />

      {children}
    </>
  )
}
