'use client'
import { useEffect, useState, useRef, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Eye, Wifi, WifiOff, RefreshCw } from 'lucide-react'
import { api, getAccessToken, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface HoleInfo {
  hole_number: number
  par: number
  stroke_index: number | null
}

interface Player {
  user_id: string
  first_name: string
  last_name: string
  username: string
  tee_color: string | null
  course_handicap: number | null
}

interface HoleScore {
  hole: number
  gross: number
  net: number
}

interface PlayerBoard {
  user_id: string
  holes_played: number
  total_gross: number
  scores: HoleScore[]
}

interface RoundInfo {
  id: string
  name: string | null
  course_name: string | null
  course_id: string | null
  game_format: string
  status: string
  holes_to_play: number
  scheduled_at: string
}

const FORMAT_LABEL: Record<string, { es: string; en: string }> = {
  stroke:              { es: 'Stroke Play',    en: 'Stroke Play' },
  stableford:          { es: 'Stableford',     en: 'Stableford' },
  stableford_modified: { es: 'Stab. Mod.',     en: 'Mod. Stab.' },
  match:               { es: 'Match Play',     en: 'Match Play' },
  skins:               { es: 'Skins',          en: 'Skins' },
  florida:             { es: 'Florida',        en: 'Florida' },
}

const TEE_DOT: Record<string, string> = {
  black: 'bg-zinc-500',
  blue:  'bg-blue-400',
  white: 'bg-white',
  red:   'bg-red-400',
}

function scoreCellStyle(gross: number, par: number): string {
  const d = gross - par
  if (gross === 1)  return 'bg-yellow-400 text-zinc-900 font-bold rounded-full'
  if (d <= -2)      return 'bg-yellow-400/20 text-yellow-300 font-bold rounded-full'
  if (d === -1)     return 'bg-emerald-500/30 text-emerald-300 font-semibold rounded-full'
  if (d === 0)      return 'text-zinc-200'
  if (d === 1)      return 'bg-orange-500/20 text-orange-300 rounded'
  return 'bg-red-600/30 text-red-300 font-bold rounded'
}

function relTotal(gross: number, par: number) {
  const d = gross - par
  if (d === 0) return { txt: 'E', cls: 'text-zinc-300' }
  if (d > 0)   return { txt: `+${d}`, cls: 'text-orange-400' }
  return { txt: String(d), cls: 'text-emerald-400' }
}

export default function SpectatePage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams()
  const roundId = params.id as string
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [round, setRound] = useState<RoundInfo | null>(null)
  const [players, setPlayers] = useState<Player[]>([])
  const [holes, setHoles] = useState<HoleInfo[]>([])
  // scores[userId][hole] = { gross, net }
  const [scores, setScores] = useState<Record<string, Record<number, HoleScore>>>({})
  const [loading, setLoading] = useState(true)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const buildScoreMap = useCallback((board: PlayerBoard[]) => {
    const map: Record<string, Record<number, HoleScore>> = {}
    for (const p of board) {
      map[p.user_id] = {}
      for (const s of p.scores) {
        map[p.user_id][s.hole] = s
      }
    }
    return map
  }, [])

  useEffect(() => {
    if (!isAuthed()) {
      router.push(`/${locale}/auth/login?redirect=${encodeURIComponent(window.location.pathname)}`)
      return
    }

    // Load initial data
    Promise.all([
      api.get(`/rounds/${roundId}`),
      api.get(`/rounds/${roundId}/players`),
      api.get(`/rounds/${roundId}/scoreboard`),
    ])
      .then(async ([rRes, pRes, sbRes]) => {
        const r = rRes.data
        setRound(r)
        setPlayers(pRes.data)
        setScores(buildScoreMap(sbRes.data))

        // Fetch holes for par info
        if (r.course_id) {
          try {
            const cRes = await api.get(`/courses/${r.course_id}`)
            setHoles(cRes.data.holes ?? [])
          } catch {
            // no holes, still show without color
          }
        }

        // Connect WS
        const token = getAccessToken()
        if (!token) return
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.golfbookvip.com'
        const wsBase = apiUrl.replace(/^https/, 'wss').replace(/^http(?!s)/, 'ws')
        const ws = new WebSocket(`${wsBase}/api/v1/ws/rounds/${roundId}`)
        wsRef.current = ws

        ws.onopen = () => {
          ws.send(JSON.stringify({ action: 'auth', token }))
          setWsStatus('connected')
        }
        ws.onclose = () => setWsStatus('disconnected')
        ws.onerror = () => setWsStatus('disconnected')

        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.event === 'score_update') {
              const { user_id, hole, gross, net } = msg
              setScores(prev => ({
                ...prev,
                [user_id]: {
                  ...(prev[user_id] ?? {}),
                  [hole]: { hole, gross, net: net ?? gross },
                },
              }))
            } else if (msg.event === 'pong') {
              // keep-alive ok
            }
          } catch { /* ignore */ }
        }

        // Ping every 30s to keep connection alive
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'ping' }))
          }
        }, 30000)
      })
      .catch(() => router.push(`/${locale}/dashboard`))
      .finally(() => setLoading(false))

    return () => {
      wsRef.current?.close()
      if (pingRef.current) clearInterval(pingRef.current)
    }
  }, [roundId, locale, router, buildScoreMap])

  const reconnect = () => {
    wsRef.current?.close()
    setWsStatus('connecting')
    const token = getAccessToken()
    if (!token || !round) return
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.golfbookvip.com'
    const wsBase = apiUrl.replace(/^https/, 'wss').replace(/^http(?!s)/, 'ws')
    const ws = new WebSocket(`${wsBase}/api/v1/ws/rounds/${roundId}`)
    wsRef.current = ws
    ws.onopen = () => {
      ws.send(JSON.stringify({ action: 'auth', token }))
      setWsStatus('connected')
    }
    ws.onclose = () => setWsStatus('disconnected')
    ws.onerror = () => setWsStatus('disconnected')
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.event === 'score_update') {
          const { user_id, hole, gross, net } = msg
          setScores(prev => ({
            ...prev,
            [user_id]: { ...(prev[user_id] ?? {}), [hole]: { hole, gross, net: net ?? gross } },
          }))
        }
      } catch { /* ignore */ }
    }
    // Refresh scores too
    api.get(`/rounds/${roundId}/scoreboard`)
      .then(r => setScores(buildScoreMap(r.data)))
      .catch(() => {})
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (!round) return null

  const fmt = FORMAT_LABEL[round.game_format]
  const isLive = round.status === 'active'
  const holesArr = holes.length > 0
    ? holes.filter(h => h.hole_number <= round.holes_to_play).sort((a, b) => a.hole_number - b.hole_number)
    : Array.from({ length: round.holes_to_play }, (_, i) => ({ hole_number: i + 1, par: 4, stroke_index: null }))

  const totalPar = holesArr.reduce((s, h) => s + h.par, 0)
  const front = holesArr.filter(h => h.hole_number <= 9)
  const back = holesArr.filter(h => h.hole_number > 9)

  // Sort players by total gross (ascending), with 0 last
  const sortedPlayers = [...players].sort((a, b) => {
    const aScores = scores[a.user_id] ?? {}
    const bScores = scores[b.user_id] ?? {}
    const aTotal = Object.values(aScores).reduce((s, sc) => s + sc.gross, 0)
    const bTotal = Object.values(bScores).reduce((s, sc) => s + sc.gross, 0)
    if (aTotal === 0 && bTotal === 0) return 0
    if (aTotal === 0) return 1
    if (bTotal === 0) return -1
    return aTotal - bTotal
  })

  const renderCell = (userId: string, holeNum: number) => {
    const sc = scores[userId]?.[holeNum]
    const hole = holesArr.find(h => h.hole_number === holeNum)
    if (!sc) return <span className="text-zinc-700 text-xs">—</span>
    const style = hole ? scoreCellStyle(sc.gross, hole.par) : 'text-zinc-300'
    return (
      <span className={`inline-flex items-center justify-center w-7 h-7 text-sm font-semibold ${style}`}>
        {sc.gross}
      </span>
    )
  }

  const playerTotal = (userId: string) => {
    const sc = scores[userId] ?? {}
    return Object.values(sc).reduce((s, v) => s + v.gross, 0)
  }

  const playerHolesPlayed = (userId: string) =>
    Object.keys(scores[userId] ?? {}).length

  const sections = round.holes_to_play === 18
    ? [{ label: lbl('Salida', 'Out'), hs: front }, { label: lbl('Vuelta', 'In'), hs: back }]
    : [{ label: lbl('Total', 'Total'), hs: holesArr }]

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/rounds/${roundId}`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-white truncate text-base">
                {round.name ?? round.course_name ?? lbl('Ronda', 'Round')}
              </h1>
              {isLive && (
                <span className="flex items-center gap-1 text-xs bg-red-500/15 border border-red-500/30 text-red-400 px-2 py-0.5 rounded-full flex-shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                  LIVE
                </span>
              )}
            </div>
            <p className="text-xs text-zinc-500">
              {locale === 'es' ? fmt?.es : fmt?.en}
              {round.course_name && round.name && ` · ${round.course_name}`}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Eye size={14} className="text-zinc-600" />
            <span className="text-xs text-zinc-600">{lbl('Espectador', 'Spectator')}</span>
            <button onClick={reconnect} title={lbl('Reconectar', 'Reconnect')}
              className={`ml-1 transition-colors ${
                wsStatus === 'connected' ? 'text-emerald-400' :
                wsStatus === 'connecting' ? 'text-yellow-400' : 'text-red-400'
              }`}>
              {wsStatus === 'disconnected'
                ? <RefreshCw size={16} />
                : wsStatus === 'connected'
                  ? <Wifi size={16} />
                  : <WifiOff size={16} className="animate-pulse" />
              }
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {sortedPlayers.map((p, idx) => {
            const total = playerTotal(p.user_id)
            const played = playerHolesPlayed(p.user_id)
            const parPlayed = holesArr.slice(0, played).reduce((s, h) => s + h.par, 0)
            const rel = total > 0 && parPlayed > 0 ? relTotal(total, parPlayed) : null
            return (
              <div key={p.user_id} className={`bg-zinc-900 border rounded-2xl p-4 ${
                idx === 0 && total > 0 ? 'border-emerald-500/40' : 'border-zinc-800'
              }`}>
                <div className="flex items-center gap-1.5 mb-2">
                  {idx === 0 && total > 0 && (
                    <span className="text-xs text-yellow-400">🏆</span>
                  )}
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${TEE_DOT[p.tee_color ?? ''] ?? 'bg-zinc-600'}`} />
                  <p className="text-xs text-zinc-400 truncate">{p.first_name} {p.last_name}</p>
                </div>
                <p className="text-2xl font-bold text-white">{total > 0 ? total : '—'}</p>
                {rel && (
                  <p className={`text-xs font-semibold ${rel.cls}`}>{rel.txt}</p>
                )}
                <p className="text-xs text-zinc-600 mt-0.5">
                  {played}/{round.holes_to_play} {lbl('hoyos', 'holes')}
                </p>
              </div>
            )
          })}
        </div>

        {/* Live scorecard table */}
        {sections.map(({ label, hs }) => (
          <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">{label}</p>
              <div className="flex items-center gap-3 text-xs text-zinc-600">
                <span>Par {hs.reduce((s, h) => s + h.par, 0)}</span>
                <span>{hs.length} {lbl('hoyos', 'holes')}</span>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[500px]">
                <thead>
                  <tr className="border-b border-zinc-800">
                    <th className="text-left text-xs text-zinc-500 py-2 px-3 font-medium w-32 sticky left-0 bg-zinc-900">
                      {lbl('Jugador', 'Player')}
                    </th>
                    {hs.map(h => (
                      <th key={h.hole_number} className="text-center text-xs py-2 px-1 w-9">
                        <span className="font-bold text-zinc-400">{h.hole_number}</span>
                        <span className="block text-zinc-600 font-normal">p{h.par}</span>
                      </th>
                    ))}
                    <th className="text-center text-xs text-zinc-500 py-2 px-2 font-medium w-14">
                      {lbl('Tot', 'Tot')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedPlayers.map((p) => {
                    const sectionScores = hs.map(h => scores[p.user_id]?.[h.hole_number])
                    const sectionTotal = sectionScores.reduce((s, sc) => s + (sc?.gross ?? 0), 0)
                    const sectionPar = hs.reduce((s, h) => s + h.par, 0)
                    const sectionRel = sectionTotal > 0 ? relTotal(sectionTotal, sectionPar) : null
                    return (
                      <tr key={p.user_id} className="border-t border-zinc-800/60 hover:bg-zinc-800/30 transition-colors">
                        <td className="py-2 px-3 sticky left-0 bg-zinc-900">
                          <div className="flex items-center gap-1.5">
                            <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${TEE_DOT[p.tee_color ?? ''] ?? 'bg-zinc-600'}`} />
                            <span className="text-xs text-zinc-300 truncate max-w-[88px]">{p.first_name} {p.last_name[0]}.</span>
                          </div>
                        </td>
                        {hs.map(h => (
                          <td key={h.hole_number} className="text-center py-2 px-1">
                            {renderCell(p.user_id, h.hole_number)}
                          </td>
                        ))}
                        <td className="text-center py-2 px-2">
                          {sectionTotal > 0 ? (
                            <div>
                              <span className="text-sm font-bold text-white">{sectionTotal}</span>
                              {sectionRel && (
                                <span className={`block text-xs ${sectionRel.cls}`}>{sectionRel.txt}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-zinc-700 text-xs">—</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}

        {/* WS status bar */}
        <div className={`text-center text-xs rounded-xl py-2 px-4 border ${
          wsStatus === 'connected'
            ? 'bg-emerald-500/5 border-emerald-500/15 text-emerald-600'
            : wsStatus === 'connecting'
              ? 'bg-yellow-500/5 border-yellow-500/15 text-yellow-600'
              : 'bg-red-500/5 border-red-500/15 text-red-500'
        }`}>
          {wsStatus === 'connected' && lbl('Conectado — actualizando en tiempo real', 'Connected — updating in real time')}
          {wsStatus === 'connecting' && lbl('Conectando…', 'Connecting…')}
          {wsStatus === 'disconnected' && (
            <button onClick={reconnect} className="flex items-center gap-2 mx-auto hover:text-red-400 transition-colors">
              <RefreshCw size={12} />
              {lbl('Desconectado. Toca para reconectar.', 'Disconnected. Tap to reconnect.')}
            </button>
          )}
        </div>
      </main>
    </div>
  )
}
