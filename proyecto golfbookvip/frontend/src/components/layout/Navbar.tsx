'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { CreditCard, Menu, X, Flag } from 'lucide-react'
import { useState } from 'react'
import { useT, useLocale } from '@/components/DictionaryProvider'

export default function Navbar() {
  const t = useT('nav')
  const locale = useLocale()
  const pathname = usePathname()
  const router = useRouter()
  const [open, setOpen] = useState(false)

  const otherLocale = locale === 'es' ? 'en' : 'es'
  const newPath = pathname.replace(`/${locale}`, `/${otherLocale}`)

  const links = [
    { href: `/${locale}#features`, label: t('features') },
    { href: `/${locale}#about`, label: t('about') },
    { href: `/${locale}/billing`, label: locale === 'es' ? 'Planes' : 'Plans' },
  ]

  return (
    <nav className="fixed top-0 inset-x-0 z-50 bg-zinc-950/80 backdrop-blur border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href={`/${locale}`} className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={16} className="text-white" />
            </div>
            <span className="font-bold text-lg text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
          </Link>

          <div className="hidden md:flex items-center gap-6">
            {links.map((l) => (
              <Link key={l.href} href={l.href} className="text-sm text-zinc-400 hover:text-white transition-colors">
                {l.label}
              </Link>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            <button onClick={() => router.push(newPath)}
              className="text-xs font-semibold text-zinc-400 hover:text-white border border-zinc-700 rounded px-2 py-1 transition-colors">
              {otherLocale.toUpperCase()}
            </button>
            <Link href={`/${locale}/auth/login`} className="text-sm text-zinc-300 hover:text-white transition-colors">
              {t('login')}
            </Link>
            <Link href={`/${locale}/auth/register`}
              className="text-sm font-semibold bg-emerald-500 hover:bg-emerald-400 text-white px-4 py-2 rounded-full transition-colors">
              {t('register')}
            </Link>
          </div>

          <button className="md:hidden text-zinc-400" onClick={() => setOpen(!open)}>
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden bg-zinc-900 border-t border-zinc-800 px-4 py-4 flex flex-col gap-3">
          {links.map((l) => (
            <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="text-sm text-zinc-300 hover:text-white">
              {l.label}
            </Link>
          ))}
          <hr className="border-zinc-800" />
          <Link href={`/${locale}/auth/login`} className="text-sm text-zinc-300">{t('login')}</Link>
          <Link href={`/${locale}/billing`} className="text-sm text-zinc-300 flex items-center gap-2">
            <CreditCard size={15} />
            {locale === 'es' ? 'Planes/Facturación' : 'Plans/Billing'}
          </Link>
          <Link href={`/${locale}/auth/register`}
            className="text-sm font-semibold bg-emerald-500 text-white px-4 py-2 rounded-full text-center">
            {t('register')}
          </Link>
          <button onClick={() => router.push(newPath)} className="text-xs text-zinc-500 text-left">
            {locale === 'es' ? 'Switch to English' : 'Cambiar a Español'}
          </button>
        </div>
      )}
    </nav>
  )
}
