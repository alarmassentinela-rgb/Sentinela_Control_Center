'use client'
import { Flag, TrendingUp, Users, Eye, BarChart2, DollarSign } from 'lucide-react'
import { useT } from '@/components/DictionaryProvider'

const features = [
  { key: 'scoring', icon: Flag },
  { key: 'handicap', icon: TrendingUp },
  { key: 'bets', icon: DollarSign },
  { key: 'stats', icon: BarChart2 },
  { key: 'social', icon: Users },
  { key: 'spectator', icon: Eye },
] as const

export default function FeaturesSection() {
  const t = useT('features')
  return (
    <section id="features" className="py-24 px-4 bg-zinc-950">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">{t('title')}</h2>
          <p className="text-zinc-400 text-lg max-w-xl mx-auto">{t('subtitle')}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map(({ key, icon: Icon }) => (
            <div key={key}
              className="group bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 rounded-2xl p-6 transition-all">
              <div className="w-11 h-11 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4 group-hover:bg-emerald-500/20 transition-colors">
                <Icon size={22} className="text-emerald-400" />
              </div>
              <h3 className="font-semibold text-white mb-2">{t(`${key}.title`)}</h3>
              <p className="text-sm text-zinc-500 leading-relaxed">{t(`${key}.desc`)}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
