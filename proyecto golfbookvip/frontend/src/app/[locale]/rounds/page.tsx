'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, Plus, Loader2, MapPin, Calendar, CheckCircle2, Play, Clock } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Round {
  id: string
  name: string | null
  course_name: string | null
  game_format: string
  status: string
  holes_to_play: number
  scheduled_at: string
  holes_played: number
  total_gross: number | null
}

const FORMAT_LABEL: Record<string, { es: string; en: string }> = {
  stroke: { es: 'Stroke Play', en: 'Stroke Play' },
  gran_premio: { es: 'Gran Premio', en: 'Gran Premio' },
  stableford: { es: 'Stableford', en: 'Stableford' },
  stableford_modified: { es: 'Stableford Mod.', en: 'Mod. Stableford' },
  match: { es: 'Match Play', en: 'Match Play' },
  skins: { es: 'Skines', en: 'Skins' },
}

export default function RoundsPage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const [rounds, setRounds] = useState<Round[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthed()) { router.push(`/${locale}/auth/login`); return }
    api.get('/rounds').then(r => setRounds(r.data)).finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-4xl lg:max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white transition-colors">
              <ArrowLeft size={20} />
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
                <Flag size={14} className="text-white" />
              </div>
              <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
            </div>
          </div>
          <Link href={`/${locale}/rounds/new`}
            className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-semibold px-4 py-2 rounded-full transition-colors">
            <Plus size={16} />{lbl('Nueva ronda', 'New round')}
          </Link>
        </div>
      </header>

      <main className="max-w-4xl lg:max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-white mb-6">{lbl('Mis rondas', 'My rounds')}</h1>

        {loading ? (
          <div className="flex justify-center py-16"><Loader2 size={28} className="animate-spin text-emerald-500" /></div>
        ) : rounds.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <Flag size={24} className="text-emerald-400" />
            </div>
            <h2 className="text-lg font-semibold text-white mb-2">{lbl('Sin rondas aún', 'No rounds yet')}</h2>
            <p className="text-zinc-500 text-sm mb-5">{lbl('Comienza tu primera ronda de golf', 'Start your first round of golf')}</p>
            <Link href={`/${locale}/rounds/new`}
              className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-5 py-2.5 rounded-full transition-colors text-sm">
              <Plus size={16} />{lbl('Nueva ronda', 'New round')}
            </Link>
          </div>
        ) : (
          <div className="space-y-3 lg:space-y-0 lg:grid lg:grid-cols-2 xl:grid-cols-3 lg:gap-4">
            {rounds.map((r) => {
              const fmt = FORMAT_LABEL[r.game_format]
              const date = new Date(r.scheduled_at).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { dateStyle: 'medium' })
              return (
                <Link key={r.id} href={`/${locale}/rounds/${r.id}`}
                  className="bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 rounded-2xl p-5 flex items-center justify-between gap-4 transition-all group">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      r.status === 'active' ? 'bg-emerald-500/20 border border-emerald-500/30' :
                      r.status === 'finished' ? 'bg-zinc-800 border border-zinc-700' :
                      'bg-yellow-500/10 border border-yellow-500/20'
                    }`}>
                      {r.status === 'active' ? <Play size={16} className="text-emerald-400" /> :
                       r.status === 'finished' ? <CheckCircle2 size={16} className="text-zinc-400" /> :
                       <Clock size={16} className="text-yellow-400" />}
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-white truncate">
                        {r.name ?? r.course_name ?? lbl('Ronda', 'Round')}
                      </p>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-zinc-500 mt-0.5">
                        {r.course_name && r.name && <span className="flex items-center gap-1"><MapPin size={10} />{r.course_name}</span>}
                        <span className="flex items-center gap-1"><Calendar size={10} />{date}</span>
                        <span>{locale === 'es' ? fmt?.es : fmt?.en}</span>
                        <span>{r.holes_to_play} {lbl('hoyos', 'holes')}</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    {r.total_gross ? (
                      <p className="text-xl font-bold text-white">{r.total_gross}</p>
                    ) : r.status === 'active' ? (
                      <p className="text-sm font-medium text-emerald-400">{r.holes_played} {lbl('jug.', 'played')}</p>
                    ) : null}
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
