'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Flag, Loader2, MapPin, Users, Radio, RefreshCw, Trophy, Minus, ChevronDown, ChevronUp, Wifi, WifiOff } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

// ─── Types ────────────────────────────────────────────────────────────────────

interface LivePlayer {
  user_id: string
  name: string
  username: string
  team_number: number | null
  course_handicap: number | null
  handicap_index: number | null
  holes_played: number
  total_gross: number
  total_net: number
  stableford: number
}

interface LiveTeam {
  team_number: number
  name: string
  color: string
  players: LivePlayer[]
  holes_won: number
  holes_tied: number
  total_net: number
  stableford: number
}

interface HoleResult {
  hole: number
  winner_team: number | null
  status: 'won' | 'tied' | 'pending'
  team_scores: Record<string, number>
}

interface LiveData {
  round: {
    id: string
    name: string | null
    course_name: string | null
    game_format: string
    status: string
    holes_to_play: number
    scheduled_at: string
    has_teams: boolean
  }
  teams: LiveTeam[]
  hole_results: HoleResult[]
  current_hole: number
  player_scores: LivePlayer[]
}

// ─── Team UI config ───────────────────────────────────────────────────────────

const TEAM_UI: Record<string, {
  bg: string; border: string; text: string; dot: string
  holeWon: string; holeTied: string; holeLost: string
  ring: string
}> = {
  emerald: {
    bg: 'bg-emerald-500/10', border: 'border-emerald-500/30',
    text: 'text-emerald-400', dot: 'bg-emerald-400',
    holeWon: 'bg-emerald-500 text-white', holeTied: 'bg-zinc-600 text-zinc-300',
    holeLost: 'bg-zinc-800 text-zinc-600', ring: 'ring-emerald-400/50',
  },
  blue: {
    bg: 'bg-blue-500/10', border: 'border-blue-500/30',
    text: 'text-blue-400', dot: 'bg-blue-400',
    holeWon: 'bg-blue-500 text-white', holeTied: 'bg-zinc-600 text-zinc-300',
    holeLost: 'bg-zinc-800 text-zinc-600', ring: 'ring-blue-400/50',
  },
  amber: {
    bg: 'bg-amber-500/10', border: 'border-amber-500/30',
    text: 'text-amber-400', dot: 'bg-amber-400',
    holeWon: 'bg-amber-500 text-white', holeTied: 'bg-zinc-600 text-zinc-300',
    holeLost: 'bg-zinc-800 text-zinc-600', ring: 'ring-amber-400/50',
  },
  red: {
    bg: 'bg-red-500/10', border: 'border-red-500/30',
    text: 'text-red-400', dot: 'bg-red-400',
    holeWon: 'bg-red-500 text-white', holeTied: 'bg-zinc-600 text-zinc-300',
    holeLost: 'bg-zinc-800 text-zinc-600', ring: 'ring-red-400/50',
  },
}

const FORMAT_LABELS: Record<string, { es: string; en: string }> = {
  stroke:              { es: 'Stroke Play',           en: 'Stroke Play' },
  stableford:          { es: 'Stableford',            en: 'Stableford' },
  stableford_modified: { es: 'Stableford Modificado', en: 'Modified Stableford' },
  match:               { es: 'Match Play',            en: 'Match Play' },
  skins:               { es: 'Skines',                en: 'Skins' },
  florida:             { es: 'Florida',               en: 'Florida' },
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function LiveScoreboardPage() {
  const locale  = useLocale()
  const { code } = useParams<{ code: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [data, setData]           = useState<LiveData | null>(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [showPlayers, setShowPlayers] = useState<Record<number, boolean>>({})
  const [secondsAgo, setSecondsAgo]   = useState(0)
  const [wsStatus, setWsStatus] = useState<'none' | 'connected' | 'disconnected'>('none')
  const wsRef  = useRef<WebSocket | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const roundIdRef = useRef<string | null>(null)

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true)
    try {
      const res = await api.get(`/rounds/live/${code}`)
      setData(res.data)
      roundIdRef.current = res.data.round.id
      setLastUpdate(new Date())
      setSecondsAgo(0)
      setError(null)
      return res.data
    } catch {
      setError(lbl('Ronda no encontrada o código inválido.', 'Round not found or invalid code.'))
      return null
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code])

  const connectWs = useCallback((roundId: string, token: string) => {
    if (wsRef.current) wsRef.current.close()
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.golfbookvip.com'
    const wsBase = apiUrl.replace(/^https/, 'wss').replace(/^http(?!s)/, 'ws')
    const ws = new WebSocket(`${wsBase}/api/v1/ws/rounds/${roundId}?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => {
      setWsStatus('connected')
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'ping' }))
      }, 30_000)
    }
    ws.onclose = () => { setWsStatus('disconnected'); if (pingRef.current) clearInterval(pingRef.current) }
    ws.onerror = () => setWsStatus('disconnected')
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.event === 'score_update') {
          // Silently refresh full data — keeps team standings in sync without client-side recompute
          fetchData(true)
        }
      } catch { /* ignore */ }
    }
  }, [fetchData])

  // Initial load + setup
  useEffect(() => {
    fetchData().then((d) => {
      if (!d) return
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
      if (token && d.round.status === 'active') {
        connectWs(d.round.id, token)
      }
    })
    // Fallback polling: every 30s (or 20s if no WS)
    const interval = setInterval(() => {
      if (wsStatus !== 'connected') fetchData(true)
    }, 20_000)
    return () => {
      clearInterval(interval)
      wsRef.current?.close()
      if (pingRef.current) clearInterval(pingRef.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchData])

  // Seconds-ago counter
  useEffect(() => {
    if (!lastUpdate) return
    const t = setInterval(() => {
      setSecondsAgo(Math.floor((Date.now() - lastUpdate.getTime()) / 1000))
    }, 1000)
    return () => clearInterval(t)
  }, [lastUpdate])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 size={32} className="animate-spin text-emerald-500" />
    </div>
  )

  if (error || !data) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4">
      <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center">
        <Flag size={20} className="text-white" />
      </div>
      <p className="text-zinc-400 text-center">{error}</p>
      <Link href={`/${locale}`} className="text-emerald-400 text-sm hover:underline">
        {lbl('Ir al inicio', 'Go home')}
      </Link>
    </div>
  )

  const { round, teams, hole_results, current_hole, player_scores } = data
  const isActive   = round.status === 'active'
  const isFinished = round.status === 'finished'
  const holesPlayed = hole_results.filter(h => h.status !== 'pending').length
  const fmt = FORMAT_LABELS[round.game_format] ?? { es: round.game_format, en: round.game_format }

  return (
    <div className="min-h-screen pb-10">
      {/* ── Header ── */}
      <header className="bg-zinc-900/95 border-b border-zinc-800 backdrop-blur-md px-4 py-3 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={14} className="text-white" />
            </div>
            <span className="font-bold text-white text-sm">GolfBook<span className="text-emerald-400">VIP</span></span>
          </div>
          <div className="flex items-center gap-3">
            {isActive && (
              <span className="flex items-center gap-1.5 text-xs font-semibold text-red-400 animate-pulse">
                <Radio size={12} />
                {lbl('EN VIVO', 'LIVE')}
              </span>
            )}
            {wsStatus === 'connected' && (
              <span title={lbl('WebSocket conectado — actualizaciones instantáneas', 'WebSocket connected — instant updates')}>
                <Wifi size={14} className="text-emerald-400" />
              </span>
            )}
            {wsStatus === 'disconnected' && (
              <span title={lbl('Desconectado — usando polling', 'Disconnected — using polling')}>
                <WifiOff size={14} className="text-zinc-600" />
              </span>
            )}
            <button onClick={() => fetchData()} disabled={refreshing}
              className="text-zinc-500 hover:text-white transition-colors">
              <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 space-y-4 pt-4">

        {/* ── Round info ── */}
        <div className="bg-zinc-900/85 border border-zinc-800 rounded-2xl px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-lg font-bold text-white leading-tight">
                {round.name ?? lbl('Ronda de Golf', 'Golf Round')}
              </h1>
              {round.course_name && (
                <div className="flex items-center gap-1.5 mt-1">
                  <MapPin size={12} className="text-zinc-500" />
                  <span className="text-sm text-zinc-400">{round.course_name}</span>
                </div>
              )}
            </div>
            <div className="text-right flex-shrink-0">
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                isActive   ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                isFinished ? 'bg-zinc-800 text-zinc-400 border-zinc-700' :
                             'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
              }`}>
                {isActive ? lbl('En juego', 'In progress') : isFinished ? lbl('Finalizada', 'Finished') : lbl('Programada', 'Scheduled')}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mt-3">
            <span className="text-xs bg-zinc-800 text-zinc-400 px-2.5 py-1 rounded-full">
              {locale === 'es' ? fmt.es : fmt.en}
            </span>
            <span className="text-xs bg-zinc-800 text-zinc-400 px-2.5 py-1 rounded-full">
              {round.holes_to_play} {lbl('hoyos', 'holes')}
            </span>
            {isActive && current_hole > 0 && (
              <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-full font-semibold">
                {lbl('Hoyo', 'Hole')} {current_hole} / {round.holes_to_play}
              </span>
            )}
          </div>

          {/* Last updated */}
          {lastUpdate && (
            <p className="text-xs text-zinc-600 mt-2">
              {lbl('Actualizado hace', 'Updated')} {secondsAgo}s
              {isActive && wsStatus === 'connected'
                ? <span className="ml-1 text-emerald-700">{lbl('· en tiempo real (WS)', '· real-time (WS)')}</span>
                : isActive
                  ? <span className="ml-1">{lbl('· actualiza automáticamente', '· auto-refreshing')}</span>
                  : null
              }
            </p>
          )}
        </div>

        {/* ── Team Standings ── */}
        {round.has_teams && teams.length > 0 && (
          <div className="bg-zinc-900/85 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-zinc-800 flex items-center gap-2">
              <Trophy size={15} className="text-amber-400" />
              <h2 className="font-semibold text-white text-sm">{lbl('Marcador de Equipos', 'Team Standings')}</h2>
              {holesPlayed > 0 && (
                <span className="text-xs text-zinc-500 ml-auto">
                  {holesPlayed} {lbl('hoyos jugados', 'holes played')}
                </span>
              )}
            </div>

            <div className="divide-y divide-zinc-800">
              {teams.map((team, idx) => {
                const ui = TEAM_UI[team.color] ?? TEAM_UI.emerald
                const isLeading = idx === 0 && team.holes_won > 0
                const holesLost = holesPlayed - team.holes_won - team.holes_tied

                return (
                  <div key={team.team_number}
                    className={`px-5 py-4 ${isLeading ? ui.bg : ''} transition-colors`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {/* Position */}
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                          isLeading ? `${ui.dot} text-zinc-900` : 'bg-zinc-800 text-zinc-500'
                        }`}>
                          {idx + 1}
                        </div>
                        {/* Team name + dot */}
                        <div className="flex items-center gap-2">
                          <span className={`w-3 h-3 rounded-full ${ui.dot}`} />
                          <span className={`font-bold text-base ${ui.text}`}>{team.name}</span>
                        </div>
                      </div>

                      {/* Score */}
                      {holesPlayed > 0 ? (
                        <div className="text-right">
                          <div className={`text-2xl font-black ${ui.text}`}>
                            {team.holes_won}
                          </div>
                          <div className="text-xs text-zinc-500">
                            {lbl('hoyos ganados', 'holes won')}
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-zinc-600">{lbl('Sin hoyos aún', 'No holes yet')}</span>
                      )}
                    </div>

                    {/* Win/Tie/Loss pills */}
                    {holesPlayed > 0 && (
                      <div className="flex gap-2 mt-2.5 ml-10">
                        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-semibold">
                          {team.holes_won} {lbl('G', 'W')}
                        </span>
                        {team.holes_tied > 0 && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-700 text-zinc-400">
                            {team.holes_tied} {lbl('E', 'T')}
                          </span>
                        )}
                        {holesLost > 0 && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400">
                            {holesLost} {lbl('P', 'L')}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Players list */}
                    <div className="flex flex-wrap gap-1.5 mt-2 ml-10">
                      {team.players.map(p => (
                        <span key={p.user_id}
                          className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
                          {p.name.split(' ')[0]} <span className="text-zinc-600">HCP {p.course_handicap ?? '—'}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* ── Hole-by-hole results ── */}
        {hole_results.length > 0 && (
          <div className="bg-zinc-900/85 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-zinc-800">
              <h2 className="font-semibold text-white text-sm">{lbl('Hoyo por Hoyo', 'Hole by Hole')}</h2>
            </div>
            <div className="px-4 py-3">
              <div className="flex flex-wrap gap-1.5">
                {hole_results.map(hr => {
                  const winnerTeam = teams.find(t => t.team_number === hr.winner_team)
                  const ui = winnerTeam ? (TEAM_UI[winnerTeam.color] ?? TEAM_UI.emerald) : null
                  const isCurrent = hr.hole === current_hole && isActive

                  return (
                    <div key={hr.hole}
                      className={`relative flex flex-col items-center gap-0.5 w-10 ${isCurrent ? 'ring-2 ring-offset-1 ring-offset-zinc-900 rounded-lg ' + (ui?.ring ?? 'ring-zinc-500') : ''}`}>
                      <span className="text-xs text-zinc-600 leading-none">{hr.hole}</span>
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                        hr.status === 'won'  && ui ? ui.holeWon  :
                        hr.status === 'tied'        ? 'bg-zinc-700 text-zinc-300' :
                                                     'bg-zinc-800/60 text-zinc-600'
                      }`}>
                        {hr.status === 'won' && winnerTeam
                          ? winnerTeam.name.replace('Equipo ', '').replace('Team ', '')
                          : hr.status === 'tied'
                          ? <Minus size={12} />
                          : '·'}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Legend */}
              <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-zinc-800">
                {teams.map(t => {
                  const ui = TEAM_UI[t.color] ?? TEAM_UI.emerald
                  return (
                    <div key={t.team_number} className="flex items-center gap-1.5 text-xs">
                      <span className={`w-6 h-6 rounded flex items-center justify-center text-white text-xs font-bold ${ui.dot}`}>
                        {t.name.replace('Equipo ', '').replace('Team ', '')}
                      </span>
                      <span className="text-zinc-500">{t.name}</span>
                    </div>
                  )
                })}
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="w-6 h-6 rounded bg-zinc-700 flex items-center justify-center">
                    <Minus size={10} className="text-zinc-400" />
                  </span>
                  <span className="text-zinc-500">{lbl('Empate', 'Tie')}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Player scores by team ── */}
        {round.has_teams && teams.length > 0 && (
          <div className="space-y-3">
            {teams.map(team => {
              const ui = TEAM_UI[team.color] ?? TEAM_UI.emerald
              const open = showPlayers[team.team_number] ?? false
              const teamPlayers = player_scores.filter(p => p.team_number === team.team_number)

              return (
                <div key={team.team_number} className={`bg-zinc-900/85 border rounded-2xl overflow-hidden ${ui.border}`}>
                  <button
                    onClick={() => setShowPlayers(prev => ({ ...prev, [team.team_number]: !open }))}
                    className="w-full flex items-center justify-between px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className={`w-3 h-3 rounded-full ${ui.dot}`} />
                      <span className={`font-semibold text-sm ${ui.text}`}>{team.name}</span>
                      <span className="text-xs text-zinc-500">
                        <Users size={11} className="inline mr-0.5" />
                        {teamPlayers.length}
                      </span>
                    </div>
                    {open ? <ChevronUp size={15} className="text-zinc-500" /> : <ChevronDown size={15} className="text-zinc-500" />}
                  </button>

                  {open && (
                    <div className="border-t border-zinc-800">
                      {/* Table header */}
                      <div className="grid grid-cols-4 px-5 py-2 text-xs text-zinc-600 border-b border-zinc-800">
                        <span className="col-span-2">{lbl('Jugador', 'Player')}</span>
                        <span className="text-center">{lbl('Hoyos', 'Holes')}</span>
                        <span className="text-right">{lbl('Score', 'Score')}</span>
                      </div>
                      {teamPlayers
                        .sort((a, b) => a.total_gross - b.total_gross)
                        .map(p => (
                          <div key={p.user_id}
                            className="grid grid-cols-4 items-center px-5 py-3 border-b border-zinc-800/50 last:border-0">
                            <div className="col-span-2">
                              <p className="text-sm font-medium text-white truncate">{p.name}</p>
                              <p className="text-xs text-zinc-600">HCP {p.course_handicap ?? '—'}</p>
                            </div>
                            <p className="text-center text-sm text-zinc-400">{p.holes_played}</p>
                            <div className="text-right">
                              {p.total_gross > 0 ? (
                                <>
                                  <p className="text-sm font-bold text-white">{p.total_gross}</p>
                                  <p className="text-xs text-zinc-600">{lbl('neto', 'net')} {p.total_net}</p>
                                </>
                              ) : (
                                <p className="text-xs text-zinc-600">—</p>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* ── No teams yet ── */}
        {!round.has_teams && round.status !== 'finished' && (
          <div className="bg-zinc-900/85 border border-zinc-800 rounded-2xl px-5 py-8 text-center">
            <Users size={32} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-500 text-sm">
              {lbl('Los equipos aún no han sido asignados.', 'Teams have not been assigned yet.')}
            </p>
            <p className="text-zinc-600 text-xs mt-1">
              {lbl('La página se actualizará automáticamente.', 'This page will update automatically.')}
            </p>
          </div>
        )}

        {/* ── Promo card ── */}
        <div className="rounded-2xl overflow-hidden border border-zinc-700/50" style={{
          background: 'linear-gradient(135deg, rgba(16,24,20,0.95) 0%, rgba(9,9,11,0.95) 100%)'
        }}>
          {/* Top accent line */}
          <div className="h-px bg-gradient-to-r from-transparent via-emerald-500/60 to-transparent" />

          <div className="px-6 py-6">
            {/* Logo + tagline */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-emerald-500/20">
                <Flag size={18} className="text-white" />
              </div>
              <div>
                <p className="font-bold text-white text-lg leading-tight">
                  GolfBook<span className="text-emerald-400">VIP</span>
                </p>
                <p className="text-xs text-zinc-500 leading-tight">
                  {lbl('Tu compañero de golf digital', 'Your digital golf companion')}
                </p>
              </div>
            </div>

            <p className="text-sm text-zinc-300 leading-relaxed mb-5">
              {lbl(
                'Lo que acabas de ver es solo una parte. GolfBookVIP es la plataforma completa para llevar tu golf al siguiente nivel — desde el primer tee hasta el 19.',
                "What you just watched is only a glimpse. GolfBookVIP is the complete platform to take your golf to the next level — from the first tee to the 19th hole."
              )}
            </p>

            {/* Feature grid */}
            <div className="grid grid-cols-2 gap-2.5 mb-5">
              {[
                { icon: '⛳', es: 'Scorecard digital hoyo a hoyo', en: 'Hole-by-hole digital scorecard' },
                { icon: '📊', es: 'Hándicap WHS oficial y automático', en: 'Official WHS handicap, auto-updated' },
                { icon: '🏆', es: 'Equipos y formatos avanzados', en: 'Teams, match play & advanced formats' },
                { icon: '💰', es: 'Apuestas: Nassau, Skins, Oyes', en: 'Bets: Nassau, Skins, Oyes & more' },
                { icon: '📈', es: 'Estadísticas y tendencia de HCP', en: 'Stats, trends & HCP history' },
                { icon: '📱', es: 'Funciona en cualquier celular', en: 'Works on any smartphone' },
              ].map(f => (
                <div key={f.es} className="flex items-start gap-2 bg-zinc-800/40 rounded-xl px-3 py-2.5">
                  <span className="text-base leading-none mt-0.5">{f.icon}</span>
                  <p className="text-xs text-zinc-400 leading-snug">{locale === 'es' ? f.es : f.en}</p>
                </div>
              ))}
            </div>

            {/* CTA */}
            <Link
              href={`/${locale}/auth/register`}
              className="flex items-center justify-center gap-2 w-full bg-emerald-500 hover:bg-emerald-400 text-white font-semibold py-3 rounded-xl transition-colors text-sm shadow-lg shadow-emerald-500/20"
            >
              {lbl('Crear mi cuenta gratis', 'Create my free account')}
            </Link>

            <p className="text-center text-xs text-zinc-600 mt-3">
              {lbl(
                'Sin tarjeta de crédito · Gratis para empezar',
                'No credit card · Free to get started'
              )}
            </p>
          </div>

          {/* Bottom accent line */}
          <div className="h-px bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent" />
        </div>

        {/* ── Footer ── */}
        <p className="text-center text-xs text-zinc-700 pb-4">
          GolfBook<span className="text-zinc-600">VIP</span> ·{' '}
          {lbl('Vista pública de seguimiento en tiempo real', 'Public real-time tracking view')}
        </p>
      </div>
    </div>
  )
}
