'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Trophy, Medal, Flag } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Row {
  position: number
  user_id: string
  username: string
  first_name: string
  last_name: string
  handicap_index: number | null
  rounds_played: number
  wins: number
  best_net: number | null
}

const MEDAL: Record<number, string> = { 1: 'text-yellow-400', 2: 'text-zinc-300', 3: 'text-amber-600' }

export default function GroupLeaderboardPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams()
  const groupId = params.id as string
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [groupName, setGroupName] = useState('')
  const [rows, setRows] = useState<Row[]>([])
  const [finishedRounds, setFinishedRounds] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { router.push(`/${locale}/auth/login`); return }
    Promise.all([
      api.get(`/groups/${groupId}`),
      api.get(`/groups/${groupId}/leaderboard`),
    ])
      .then(([g, lb]) => {
        setGroupName(g.data.name)
        setRows(lb.data.leaderboard || [])
        setFinishedRounds(lb.data.finished_rounds || 0)
      })
      .catch(() => router.push(`/${locale}/groups/${groupId}`))
      .finally(() => setLoading(false))
  }, [groupId, locale, router])

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/groups/${groupId}`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Trophy size={18} className="text-emerald-400 flex-shrink-0" />
            <div className="min-w-0">
              <h1 className="font-bold text-white text-lg truncate">{lbl('Tabla de posiciones', 'Leaderboard')}</h1>
              <p className="text-xs text-zinc-500 truncate">{groupName}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6">
        <p className="text-xs text-zinc-500 mb-4">
          {finishedRounds > 0
            ? lbl(`Sobre ${finishedRounds} ronda${finishedRounds === 1 ? '' : 's'} finalizada${finishedRounds === 1 ? '' : 's'} del grupo · ordenado por victorias, luego handicap.`,
                  `Over ${finishedRounds} finished group round${finishedRounds === 1 ? '' : 's'} · sorted by wins, then handicap.`)
            : lbl('Aún sin rondas finalizadas — el orden es por handicap.', 'No finished rounds yet — sorted by handicap.')}
        </p>

        {rows.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-10 text-center">
            <Flag size={24} className="text-zinc-700 mx-auto mb-2" />
            <p className="text-sm text-zinc-500">{lbl('No hay miembros para mostrar.', 'No members to show.')}</p>
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            {/* header row */}
            <div className="grid grid-cols-[2rem_1fr_3rem_3rem_3.5rem] gap-2 px-4 py-2.5 border-b border-zinc-800 text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">
              <span className="text-center">#</span>
              <span>{lbl('Jugador', 'Player')}</span>
              <span className="text-center">HCP</span>
              <span className="text-center" title={lbl('Victorias', 'Wins')}>🏆</span>
              <span className="text-right">{lbl('Mejor', 'Best')}</span>
            </div>
            <div className="divide-y divide-zinc-800">
              {rows.map(r => (
                <div key={r.user_id} className="grid grid-cols-[2rem_1fr_3rem_3rem_3.5rem] gap-2 px-4 py-3 items-center">
                  <span className="text-center">
                    {r.position <= 3
                      ? <Medal size={16} className={`${MEDAL[r.position]} mx-auto`} />
                      : <span className="text-sm text-zinc-500">{r.position}</span>}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{r.first_name} {r.last_name}</p>
                    <p className="text-xs text-zinc-500 truncate">
                      @{r.username}{r.rounds_played > 0 ? ` · ${r.rounds_played} ${lbl('rondas', 'rounds')}` : ''}
                    </p>
                  </div>
                  <span className="text-center text-sm text-zinc-300">
                    {r.handicap_index != null ? r.handicap_index.toFixed(1) : '—'}
                  </span>
                  <span className="text-center text-sm font-semibold text-emerald-400">
                    {r.wins > 0 ? r.wins : <span className="text-zinc-600">0</span>}
                  </span>
                  <span className="text-right text-sm text-zinc-300">
                    {r.best_net != null ? r.best_net : <span className="text-zinc-600">—</span>}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <p className="text-center text-xs text-zinc-600 mt-5">
          {lbl('“Victorias” = veces que quedaste 1.º en net en una ronda del grupo. “Mejor” = tu menor net en una ronda completa.',
               '“Wins” = times you finished 1st net in a group round. “Best” = your lowest net in a complete round.')}
        </p>
      </main>
    </div>
  )
}
