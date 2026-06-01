'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Play, CheckCircle2, MapPin, UserPlus, Flag } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface FeedPlayer {
  user_id: string
  username: string
  first_name: string
  last_name: string
  handicap_index: number | null
  tee_color: string | null
}

interface FeedItem {
  round_id: string
  name: string | null
  course_name: string | null
  game_format: string
  status: string
  holes_to_play: number
  scheduled_at: string
  finished_at: string | null
  players: FeedPlayer[]
}

const FORMAT_LABEL: Record<string, { es: string; en: string }> = {
  stroke:               { es: 'Stroke Play',     en: 'Stroke Play' },
  gran_premio:          { es: 'Gran Premio',      en: 'Gran Premio' },
  stableford:           { es: 'Stableford',       en: 'Stableford' },
  stableford_modified:  { es: 'Stableford Mod.',  en: 'Mod. Stableford' },
  match:                { es: 'Match Play',       en: 'Match Play' },
  skins:                { es: 'Skins',            en: 'Skins' },
  florida:              { es: 'Florida',          en: 'Florida' },
}

const TEE_COLOR: Record<string, string> = {
  black:  'bg-zinc-900 border-zinc-600',
  blue:   'bg-blue-500/30 border-blue-400',
  white:  'bg-white/20 border-white/40',
  red:    'bg-red-500/30 border-red-400',
}

export default function FeedPage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [feed, setFeed] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { router.push(`/${locale}/auth/login`); return }
    api.get('/users/me/feed')
      .then(r => setFeed(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [locale, router])

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(
      locale === 'es' ? 'es-MX' : 'en-US',
      { dateStyle: 'medium' }
    )

  const timeAgo = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime()
    const h = Math.floor(diff / 3600000)
    const d = Math.floor(diff / 86400000)
    if (h < 1) return lbl('Hace menos de 1h', 'Less than 1h ago')
    if (h < 24) return lbl(`Hace ${h}h`, `${h}h ago`)
    if (d === 1) return lbl('Ayer', 'Yesterday')
    return formatDate(iso)
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="font-bold text-white text-lg flex-1">{lbl('Actividad', 'Activity')}</h1>
          <Link href={`/${locale}/social`}
            className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
            <UserPlus size={14} />
            {lbl('Seguir más', 'Follow more')}
          </Link>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6">
        {feed.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <Flag size={28} className="text-emerald-400" />
            </div>
            <h2 className="text-lg font-semibold text-white mb-2">
              {lbl('Sin actividad reciente', 'No recent activity')}
            </h2>
            <p className="text-zinc-500 text-sm mb-6 max-w-xs mx-auto">
              {lbl(
                'Sigue a otros golfistas para ver sus rondas aquí.',
                'Follow other golfers to see their rounds here.'
              )}
            </p>
            <Link href={`/${locale}/social`}
              className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-5 py-2.5 rounded-full text-sm transition-colors">
              <UserPlus size={15} />
              {lbl('Buscar jugadores', 'Find players')}
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {feed.map(item => {
              const fmt = FORMAT_LABEL[item.game_format]
              const isActive = item.status === 'active'
              const ref = item.finished_at ?? item.scheduled_at

              return (
                <Link key={item.round_id} href={`/${locale}/rounds/${item.round_id}`}
                  className="block bg-zinc-900 border border-zinc-800 hover:border-emerald-500/30 rounded-2xl p-4 transition-all group">

                  {/* Header row */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        isActive ? 'bg-emerald-500/20' : 'bg-zinc-800'
                      }`}>
                        {isActive
                          ? <Play size={13} className="text-emerald-400" />
                          : <CheckCircle2 size={13} className="text-zinc-500" />
                        }
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-white truncate">
                          {item.name ?? item.course_name ?? lbl('Ronda', 'Round')}
                        </p>
                        {item.course_name && item.name && (
                          <div className="flex items-center gap-1 mt-0.5">
                            <MapPin size={10} className="text-zinc-600 flex-shrink-0" />
                            <p className="text-xs text-zinc-500 truncate">{item.course_name}</p>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      {isActive ? (
                        <span className="inline-flex items-center gap-1 text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          {lbl('En curso', 'Live')}
                        </span>
                      ) : (
                        <p className="text-xs text-zinc-600">{timeAgo(ref)}</p>
                      )}
                    </div>
                  </div>

                  {/* Format + holes */}
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-md">
                      {locale === 'es' ? fmt?.es : fmt?.en}
                    </span>
                    <span className="text-xs text-zinc-600">{item.holes_to_play} {lbl('hoyos', 'holes')}</span>
                  </div>

                  {/* Players */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {item.players.map(p => (
                      <div key={p.user_id} className="flex items-center gap-1.5">
                        <div className={`w-6 h-6 rounded-full border flex items-center justify-center ${
                          TEE_COLOR[p.tee_color ?? ''] ?? 'bg-zinc-800 border-zinc-700'
                        }`}>
                          <span className="text-[10px] font-bold text-white">
                            {p.first_name[0]}{p.last_name[0]}
                          </span>
                        </div>
                        <span className="text-xs text-zinc-400">{p.first_name}</span>
                        {p.handicap_index != null && (
                          <span className="text-xs text-zinc-600">({p.handicap_index.toFixed(0)})</span>
                        )}
                      </div>
                    ))}
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
