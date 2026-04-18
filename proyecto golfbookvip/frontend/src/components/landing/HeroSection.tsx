'use client'
import Link from 'next/link'
import { Flag, ArrowRight, CheckCircle2 } from 'lucide-react'
import { useT, useLocale } from '@/components/DictionaryProvider'

export default function HeroSection() {
  const t = useT('hero')
  const locale = useLocale()
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-zinc-950 via-zinc-900 to-emerald-950/40" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-500/10 rounded-full blur-3xl" />
      <div className="relative z-10 max-w-5xl mx-auto px-4 text-center pt-24 pb-16">
        <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium px-4 py-1.5 rounded-full mb-6">
          <Flag size={14} />{t('badge')}
        </div>
        <h1 className="text-4xl sm:text-6xl font-extrabold text-white leading-tight tracking-tight mb-6">
          {t('title').split(' ').slice(0, -2).join(' ')}{' '}
          <span className="text-emerald-400">{t('title').split(' ').slice(-2).join(' ')}</span>
        </h1>
        <p className="text-lg sm:text-xl text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">{t('subtitle')}</p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href={`/${locale}/auth/register`}
            className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-8 py-3.5 rounded-full transition-all shadow-lg shadow-emerald-500/20">
            {t('cta_primary')} <ArrowRight size={18} />
          </Link>
          <Link href={`/${locale}/auth/login`}
            className="flex items-center gap-2 border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white font-semibold px-8 py-3.5 rounded-full transition-all">
            {t('cta_secondary')}
          </Link>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-6 mt-14 text-sm text-zinc-500">
          {['WHS Official', 'Real-time GPS', 'iOS & Android'].map((b) => (
            <div key={b} className="flex items-center gap-1.5">
              <CheckCircle2 size={15} className="text-emerald-500" /><span>{b}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
