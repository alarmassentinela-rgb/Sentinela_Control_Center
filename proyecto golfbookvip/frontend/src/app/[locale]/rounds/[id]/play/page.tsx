'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { ChevronLeft, ChevronRight, CheckCircle2, Loader2, Minus, Plus, RotateCcw, Table2, Pencil, Trophy, AlertTriangle, Users } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Hole {
  hole_number: number
  par: number
  stroke_index: number | null
  distance_yards_black: number | null
  distance_yards_blue: number | null
  distance_yards_white: number | null
  distance_yards_red: number | null
}

interface Score {
  hole: number
  gross: number
  net: number
  putts?: number
}

interface MatchTeam {
  team_number: number
  name: string
  color: string
  players: { name: string; username: string; course_handicap: number | null }[]
  holes_won: number
  holes_tied: number
  holes_lost: number
  total_net: number
}

interface MatchHole {
  hole: number
  winner_team: number | null
  status: 'team_won' | 'tied' | 'pending'
  team_scores: Record<string, number>
}

interface MatchData {
  has_teams: boolean
  teams: MatchTeam[]
  hole_results: MatchHole[]
  holes_played: number
  current_hole: number
}

interface FloridaTeam {
  team_number: number
  name: string
  color: string
  players: { name: string; course_handicap: number | null }[]
  total_net: number
  holes_completed: number
}

interface FloridaData {
  has_teams: boolean
  teams: FloridaTeam[]
  hole_results: MatchHole[]
  holes_to_play: number
}

interface GroupMate {
  user_id: string
  name: string
  username: string
  course_handicap: number | null
}

interface ConflictItem {
  user_id: string
  player_name: string
  hole_number: number
  score_a: number
  score_b: number
}

const MATCH_TEAM_UI: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  emerald: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  blue:    { bg: 'bg-blue-500/15',    text: 'text-blue-400',    border: 'border-blue-500/30',    dot: 'bg-blue-400'    },
  amber:   { bg: 'bg-amber-500/15',   text: 'text-amber-400',   border: 'border-amber-500/30',   dot: 'bg-amber-400'   },
  red:     { bg: 'bg-red-500/15',     text: 'text-red-400',     border: 'border-red-500/30',     dot: 'bg-red-400'     },
}

const PAR_COLOR: Record<number, string> = {
  3: 'text-blue-400',
  4: 'text-white',
  5: 'text-yellow-400',
}

function scoreLabel(gross: number, par: number) {
  const diff = gross - par
  if (gross === 1) return { text: 'Hoyo en 1!', cls: 'text-yellow-300 font-bold' }
  if (diff === -3) return { text: 'Albatros', cls: 'text-yellow-400 font-bold' }
  if (diff === -2) return { text: 'Eagle', cls: 'text-emerald-300 font-bold' }
  if (diff === -1) return { text: 'Birdie', cls: 'text-emerald-400' }
  if (diff === 0) return { text: 'Par', cls: 'text-zinc-300' }
  if (diff === 1) return { text: 'Bogey', cls: 'text-orange-400' }
  if (diff === 2) return { text: 'Doble bogey', cls: 'text-red-400' }
  return { text: `+${diff}`, cls: 'text-red-500 font-bold' }
}

function scoreCellStyle(gross: number, par: number): string {
  const diff = gross - par
  if (gross === 1) return 'bg-yellow-400 text-zinc-900 font-bold rounded-full'
  if (diff <= -2) return 'bg-yellow-400/20 text-yellow-300 font-bold rounded-full'
  if (diff === -1) return 'bg-emerald-500/30 text-emerald-300 font-semibold rounded-full'
  if (diff === 0) return 'text-zinc-200'
  if (diff === 1) return 'bg-orange-500/20 text-orange-300 rounded'
  return 'bg-red-600/30 text-red-300 font-bold rounded'
}

// ─── Full Scorecard Table ─────────────────────────────────────────────────────
function ScorecardTable({
  holes, scores, holesTotal, tee, onEdit, lbl
}: {
  holes: Hole[]
  scores: Record<number, Score>
  holesTotal: number
  tee: string
  onEdit: (h: number) => void
  lbl: (es: string, en: string) => string
}) {
  const activeHoles = holes.filter(h => h.hole_number <= holesTotal)
  const front = activeHoles.filter(h => h.hole_number <= 9)
  const back = activeHoles.filter(h => h.hole_number > 9)

  const sumPar = (hs: Hole[]) => hs.reduce((s, h) => s + h.par, 0)
  const sumGross = (hs: Hole[]) => hs.reduce((s, h) => {
    const sc = scores[h.hole_number]
    return sc ? s + sc.gross : s
  }, 0)
  const sumNet = (hs: Hole[]) => hs.reduce((s, h) => {
    const sc = scores[h.hole_number]
    return sc ? s + sc.net : s
  }, 0)
  const countPlayed = (hs: Hole[]) => hs.filter(h => scores[h.hole_number]).length

  const totalGross = sumGross(activeHoles)
  const totalPar = sumPar(activeHoles)
  const relTotal = totalGross - totalPar

  const sections = holesTotal === 18
    ? [
        { label: lbl('Salida', 'Out'), hs: front },
        { label: lbl('Vuelta', 'In'), hs: back },
      ]
    : [
        { label: lbl('Total', 'Total'), hs: activeHoles },
      ]

  const headerCls = 'text-center text-xs text-zinc-500 py-2 px-1 font-medium uppercase tracking-wide'
  const cellCls = 'text-center text-sm py-2 px-1 border-t border-zinc-800'

  return (
    <div className="overflow-x-auto pb-4">
      <div className="min-w-[420px]">
        {sections.map(({ label, hs }) => (
          <div key={label} className="mb-4">
            <table className="w-full">
              <thead>
                <tr className="bg-zinc-900">
                  <th className={`${headerCls} w-8 text-left pl-3`}>#</th>
                  <th className={`${headerCls} w-8`}>Par</th>
                  <th className={`${headerCls} w-8`}>SI</th>
                  <th className={`${headerCls}`}>{lbl('Yds', 'Yds')}</th>
                  <th className={`${headerCls} text-emerald-400`}>{lbl('Golpes', 'Gross')}</th>
                  <th className={`${headerCls} text-blue-400`}>{lbl('Neto', 'Net')}</th>
                  <th className={`${headerCls} w-8`}>+/-</th>
                  <th className={`${headerCls} w-6`} />
                </tr>
              </thead>
              <tbody>
                {hs.map((h) => {
                  const sc = scores[h.hole_number]
                  const diff = sc ? sc.gross - h.par : null
                  return (
                    <tr key={h.hole_number}
                      className="border-t border-zinc-800/60 hover:bg-zinc-800/40 transition-colors">
                      {/* Hole number */}
                      <td className="py-2 pl-3">
                        <span className="w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 text-xs font-bold text-zinc-300 flex items-center justify-center">
                          {h.hole_number}
                        </span>
                      </td>
                      {/* Par */}
                      <td className={`${cellCls} font-medium ${PAR_COLOR[h.par] ?? 'text-white'}`}>
                        {h.par}
                      </td>
                      {/* SI */}
                      <td className={`${cellCls} text-zinc-500`}>
                        {h.stroke_index ?? '—'}
                      </td>
                      {/* Yards */}
                      <td className={`${cellCls} text-zinc-400`}>
                        {(tee === 'black' ? h.distance_yards_black
                          : tee === 'blue'  ? h.distance_yards_blue
                          : tee === 'red'   ? h.distance_yards_red
                          : h.distance_yards_white) ?? '—'}
                      </td>
                      {/* Gross */}
                      <td className={`${cellCls}`}>
                        {sc ? (
                          <span className={`inline-flex items-center justify-center w-7 h-7 text-sm font-bold ${scoreCellStyle(sc.gross, h.par)}`}>
                            {sc.gross}
                          </span>
                        ) : (
                          <span className="text-zinc-700">—</span>
                        )}
                      </td>
                      {/* Net */}
                      <td className={`${cellCls} text-blue-300`}>
                        {sc ? sc.net : <span className="text-zinc-700">—</span>}
                      </td>
                      {/* +/- */}
                      <td className={`${cellCls} text-xs font-medium ${
                        diff === null ? 'text-zinc-700' :
                        diff < 0 ? 'text-emerald-400' :
                        diff > 0 ? 'text-red-400' :
                        'text-zinc-400'
                      }`}>
                        {diff === null ? '—' :
                         diff === 0 ? 'E' :
                         diff > 0 ? `+${diff}` : diff}
                      </td>
                      {/* Edit */}
                      <td className="py-2 pr-2">
                        <button onClick={() => onEdit(h.hole_number)}
                          className="w-6 h-6 flex items-center justify-center text-zinc-600 hover:text-emerald-400 transition-colors">
                          <Pencil size={11} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              {/* Subtotal row */}
              <tfoot>
                <tr className="bg-zinc-900 border-t-2 border-zinc-700">
                  <td colSpan={1} className="py-2.5 pl-3">
                    <span className="text-xs font-bold text-zinc-400">{label}</span>
                  </td>
                  <td className="py-2.5 text-center text-sm font-bold text-white">{sumPar(hs)}</td>
                  <td />
                  <td />
                  <td className="py-2.5 text-center text-sm font-bold text-white">
                    {countPlayed(hs) > 0 ? sumGross(hs) : '—'}
                  </td>
                  <td className="py-2.5 text-center text-sm font-bold text-blue-300">
                    {countPlayed(hs) > 0 ? sumNet(hs) : '—'}
                  </td>
                  <td className={`py-2.5 text-center text-sm font-bold ${
                    countPlayed(hs) === 0 ? 'text-zinc-700' :
                    sumGross(hs) - sumPar(hs) < 0 ? 'text-emerald-400' :
                    sumGross(hs) - sumPar(hs) > 0 ? 'text-red-400' :
                    'text-zinc-300'
                  }`}>
                    {countPlayed(hs) === 0 ? '—' :
                     sumGross(hs) - sumPar(hs) === 0 ? 'E' :
                     sumGross(hs) - sumPar(hs) > 0 ? `+${sumGross(hs) - sumPar(hs)}` :
                     sumGross(hs) - sumPar(hs)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        ))}

        {/* Grand total (18 holes only) */}
        {holesTotal === 18 && (
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3 flex items-center justify-between">
            <span className="text-sm font-bold text-zinc-300">{lbl('TOTAL', 'TOTAL')}</span>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-xs text-zinc-500 mb-0.5">Par</p>
                <p className="text-sm font-bold text-white">{totalPar}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-zinc-500 mb-0.5">{lbl('Bruto', 'Gross')}</p>
                <p className="text-2xl font-bold text-white">{totalGross > 0 ? totalGross : '—'}</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-zinc-500 mb-0.5">+/−</p>
                <p className={`text-xl font-bold ${
                  relTotal < 0 ? 'text-emerald-400' :
                  relTotal > 0 ? 'text-red-400' :
                  'text-zinc-300'
                }`}>
                  {totalGross === 0 ? '—' :
                   relTotal === 0 ? 'E' :
                   relTotal > 0 ? `+${relTotal}` : relTotal}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function PlayRoundPage() {
  const locale = useLocale()
  const router = useRouter()
  const { id } = useParams<{ id: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [holes, setHoles] = useState<Hole[]>([])
  const [scores, setScores] = useState<Record<number, Score>>({})
  const [currentHole, setCurrentHole] = useState(1)
  const [grossInput, setGrossInput] = useState(4)
  const [puttsInput, setPuttsInput] = useState<number | null>(null)
  const [holesTotal, setHolesTotal] = useState(18)
  const [myTee, setMyTee] = useState<string>('blue')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [view, setView] = useState<'input' | 'card' | 'match'>('input')
  const [matchData, setMatchData] = useState<MatchData | null>(null)
  const [matchLoading, setMatchLoading] = useState(false)
  const [amCreator, setAmCreator] = useState(false)
  const [gameFormat, setGameFormat] = useState<string>('')
  const [floridaData, setFloridaData] = useState<FloridaData | null>(null)
  const [floridaLoading, setFloridaLoading] = useState(false)
  const [myUserId, setMyUserId] = useState<string>('')
  const [myStartingHole, setMyStartingHole] = useState<number | null>(null)
  const [groupMates, setGroupMates] = useState<GroupMate[]>([])
  const [targetUserId, setTargetUserId] = useState<string>('')   // empty = self
  const [conflicts, setConflicts] = useState<ConflictItem[]>([])
  const [resolvingFor, setResolvingFor] = useState<ConflictItem | null>(null)
  const [resolvingValue, setResolvingValue] = useState<number>(0)
  const [resolving, setResolving] = useState(false)
  const [conflictBanner, setConflictBanner] = useState<{ user_id: string; hole: number; a: number; b: number } | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    Promise.all([api.get(`/rounds/${id}`), api.get(`/rounds/${id}/players`), api.get('/users/me')]).then(async ([rRes, playersRes, meRes]) => {
      const round = rRes.data
      setHolesTotal(round.holes_to_play)
      if (round.status !== 'active') { router.push(`/${locale}/rounds/${id}`); return }
      const me = meRes.data
      setMyUserId(me.id)
      const myPlayer = (playersRes.data as { user_id: string; tee_color: string | null }[])
        .find(p => p.user_id === me.id)
      if (myPlayer?.tee_color) setMyTee(myPlayer.tee_color)
      setAmCreator(round.created_by === me.id)
      setGameFormat(round.game_format)
      const courseRes = await api.get(`/courses/${round.course_id}`)
      setHoles(courseRes.data.holes)

      // Tee groups: encontrar mi grupo y compañeros (excluyéndome)
      try {
        const tgRes = await api.get(`/rounds/${id}/tee-groups`)
        const tg = tgRes.data
        if (tg.has_groups) {
          type TGP = { user_id: string; name: string; username: string; course_handicap: number | null }
          type TGG = { group_number: number; starting_hole: number | null; players: TGP[] }
          const myGroup = (tg.groups as TGG[]).find(g => g.players.some(p => p.user_id === me.id))
          if (myGroup) {
            setMyStartingHole(myGroup.starting_hole ?? null)
            setGroupMates(myGroup.players.filter(p => p.user_id !== me.id))
            if (myGroup.starting_hole && myGroup.starting_hole > 1) {
              setCurrentHole(myGroup.starting_hole)
            }
          }
        }
      } catch { /* sin grupos asignados — flujo normal */ }

      // Conflictos existentes
      try {
        const cRes = await api.get(`/rounds/${id}/conflicts`)
        setConflicts(cRes.data ?? [])
      } catch { /* ignore */ }

      const boardRes = await api.get(`/rounds/${id}/scoreboard`)
      const myEntry = boardRes.data.find((e: { user_id: string }) => e.user_id === me.id)
      if (myEntry?.scores?.length) {
        const saved: Record<number, Score> = {}
        myEntry.scores.forEach((s: Score) => { saved[s.hole] = s })
        setScores(saved)
        const lastPlayed = Math.max(...myEntry.scores.map((s: Score) => s.hole))
        if (lastPlayed < round.holes_to_play) setCurrentHole(lastPlayed + 1)
      }

      // WebSocket — eventos de conflicto y resolución
      const token = localStorage.getItem('access_token')
      if (token) {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.golfbookvip.com'
        const wsBase = apiUrl.replace(/^https/, 'wss').replace(/^http(?!s)/, 'ws')
        const ws = new WebSocket(`${wsBase}/api/v1/ws/rounds/${id}?token=${token}`)
        wsRef.current = ws
        ws.onmessage = async (e) => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.event === 'score_conflict') {
              setConflictBanner({ user_id: msg.user_id, hole: msg.hole, a: msg.score_a, b: msg.score_b })
              try {
                const cRes = await api.get(`/rounds/${id}/conflicts`)
                setConflicts(cRes.data ?? [])
              } catch { /* ignore */ }
            } else if (msg.event === 'conflict_resolved') {
              setConflicts(prev => prev.filter(c => !(c.user_id === msg.user_id && c.hole_number === msg.hole)))
              setConflictBanner(prev => (prev && prev.user_id === msg.user_id && prev.hole === msg.hole) ? null : prev)
              // Si es mi score, refrescar valor visible
              if (msg.user_id === me.id) {
                setScores(prev => {
                  const existing = prev[msg.hole]
                  if (!existing) return prev
                  return { ...prev, [msg.hole]: { ...existing, gross: msg.final_score } }
                })
              }
            }
          } catch { /* ignore */ }
        }
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'ping' }))
        }, 30000)
      }
    }).finally(() => setLoading(false))

    return () => {
      wsRef.current?.close()
      if (pingRef.current) clearInterval(pingRef.current)
    }
  }, [id, locale, router])

  useEffect(() => {
    const hole = holes.find(h => h.hole_number === currentHole)
    if (hole) {
      const existing = scores[currentHole]
      setGrossInput(existing?.gross ?? hole.par)
      setPuttsInput(existing?.putts ?? null)
    }
  }, [currentHole, holes])

  useEffect(() => {
    if (view !== 'match') return
    if (gameFormat === 'florida') {
      setFloridaLoading(true)
      api.get(`/rounds/${id}/florida-scores`)
        .then(r => setFloridaData(r.data))
        .finally(() => setFloridaLoading(false))
    } else {
      setMatchLoading(true)
      api.get(`/rounds/${id}/match-scores`)
        .then(r => setMatchData(r.data))
        .finally(() => setMatchLoading(false))
    }
  }, [view, id, gameFormat])

  const submitScore = async () => {
    setSubmitting(true)
    try {
      const payload: Record<string, unknown> = {
        hole_number: currentHole,
        gross_score: grossInput,
        putts: puttsInput,
      }
      if (targetUserId && targetUserId !== myUserId) payload.for_user_id = targetUserId
      const res = await api.post(`/rounds/${id}/scores`, payload)

      // Solo actualizar tabla local si estoy capturando para mí
      if (!targetUserId || targetUserId === myUserId) {
        setScores(prev => ({
          ...prev,
          [currentHole]: { hole: currentHole, gross: grossInput, net: res.data.net_score, putts: puttsInput ?? undefined }
        }))
        if (currentHole < holesTotal) setCurrentHole(currentHole + 1)
      } else {
        // Captura cruzada — si vino con conflicto, refrescar lista
        if (res.data.has_conflict) {
          try {
            const cRes = await api.get(`/rounds/${id}/conflicts`)
            setConflicts(cRes.data ?? [])
          } catch { /* ignore */ }
        }
      }
    } finally {
      setSubmitting(false)
    }
  }

  const resolveConflict = async () => {
    if (!resolvingFor) return
    setResolving(true)
    try {
      await api.post(
        `/rounds/${id}/scores/${resolvingFor.hole_number}/resolve`,
        null,
        { params: { correct_score: resolvingValue, target_user_id: resolvingFor.user_id } }
      )
      setConflicts(prev => prev.filter(c => !(c.user_id === resolvingFor.user_id && c.hole_number === resolvingFor.hole_number)))
      if (resolvingFor.user_id === myUserId) {
        setScores(prev => {
          const existing = prev[resolvingFor.hole_number]
          if (!existing) return prev
          return { ...prev, [resolvingFor.hole_number]: { ...existing, gross: resolvingValue } }
        })
      }
      setResolvingFor(null)
      setConflictBanner(null)
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      alert(err.response?.data?.detail || lbl('No se pudo resolver el conflicto', 'Could not resolve conflict'))
    } finally {
      setResolving(false)
    }
  }

  const handleFinish = async () => {
    if (conflicts.length > 0) {
      alert(lbl(
        `Hay ${conflicts.length} conflicto(s) de score sin resolver. Resuelve todos antes de finalizar.`,
        `There are ${conflicts.length} unresolved score conflict(s). Resolve all before finishing.`
      ))
      return
    }
    if (!confirm(lbl('¿Finalizar la ronda?', 'Finish the round?'))) return
    setFinishing(true)
    try {
      await api.post(`/rounds/${id}/finish`)
      router.push(`/${locale}/rounds/${id}`)
    } catch (e) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } }
      if (err.response?.status === 409) {
        alert(err.response?.data?.detail || lbl('Hay conflictos sin resolver.', 'There are unresolved conflicts.'))
        // Refrescar lista por si cambió
        try {
          const cRes = await api.get(`/rounds/${id}/conflicts`)
          setConflicts(cRes.data ?? [])
        } catch { /* ignore */ }
      }
      setFinishing(false)
    }
  }

  const goToHole = (h: number) => {
    setCurrentHole(h)
    setView('input')
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  const hole = holes.find(h => h.hole_number === currentHole)
  const allPlayed = Object.keys(scores).length >= holesTotal
  const totalGross = Object.values(scores).reduce((s, sc) => s + sc.gross, 0)
  const totalPar = holes.slice(0, holesTotal).reduce((s, h) => s + h.par, 0)
  const relativeToPar = totalGross - totalPar
  const holesPlayed = Object.keys(scores).length

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* Header */}
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <button onClick={() => router.push(`/${locale}/rounds/${id}`)} className="text-zinc-400 hover:text-white">
            <ChevronLeft size={22} />
          </button>
          {/* View toggle */}
          <div className="flex items-center gap-1 bg-zinc-800 rounded-xl p-1">
            <button onClick={() => setView('input')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                view === 'input' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
              }`}>
              <Pencil size={13} />
              {lbl('Hoyo', 'Hole')} {currentHole}
            </button>
            <button onClick={() => setView('card')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                view === 'card' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
              }`}>
              <Table2 size={13} />
              {lbl('Tarjeta', 'Card')}
            </button>
            <button onClick={() => setView('match')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                view === 'match' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
              }`}>
              <Trophy size={13} />
              {gameFormat === 'florida' ? 'Florida' : 'Match'}
            </button>
          </div>
          {/* Running total */}
          <div className="text-right min-w-[3rem]">
            <span className={`text-sm font-bold ${
              relativeToPar < 0 ? 'text-emerald-400' : relativeToPar > 0 ? 'text-red-400' : 'text-zinc-300'
            }`}>
              {totalGross > 0 ? (relativeToPar > 0 ? `+${relativeToPar}` : relativeToPar === 0 ? 'E' : relativeToPar) : '—'}
            </span>
            <p className="text-xs text-zinc-600">{holesPlayed}/{holesTotal}</p>
          </div>
        </div>
      </header>

      {/* ── CARD VIEW ─────────────────────────────────────────────────────── */}
      {view === 'card' && (
        <div className="flex-1 overflow-auto px-4 py-5 max-w-lg mx-auto w-full">
          <ScorecardTable
            holes={holes}
            scores={scores}
            holesTotal={holesTotal}
            tee={myTee}
            onEdit={goToHole}
            lbl={lbl}
          />
          {amCreator && (
            <button onClick={handleFinish} disabled={finishing}
              className={`w-full mt-4 flex items-center justify-center gap-2 disabled:opacity-60 text-white font-semibold py-3.5 rounded-2xl transition-colors ${
                allPlayed
                  ? 'bg-emerald-500 hover:bg-emerald-400'
                  : 'bg-zinc-700 hover:bg-zinc-600 border border-zinc-600'
              }`}>
              {finishing ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
              {allPlayed
                ? lbl('Finalizar ronda', 'Finish round')
                : lbl(
                    `Finalizar (${holesTotal - Object.keys(scores).length} hoyos pendientes)`,
                    `Finish (${holesTotal - Object.keys(scores).length} holes pending)`
                  )}
            </button>
          )}
        </div>
      )}

      {/* ── MATCH / FLORIDA VIEW ─────────────────────────────────────────── */}
      {view === 'match' && gameFormat === 'florida' && (
        <div className="flex-1 overflow-auto px-4 py-5 max-w-lg mx-auto w-full space-y-4">
          {floridaLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-emerald-500" />
            </div>
          ) : !floridaData?.has_teams ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-6 py-10 text-center">
              <Trophy size={32} className="text-zinc-600 mx-auto mb-3" />
              <p className="text-zinc-400 font-medium mb-1">{lbl('Sin equipos publicados', 'No teams published')}</p>
              <p className="text-xs text-zinc-600">{lbl('El organizador debe generar y publicar los equipos', 'The organizer must generate and publish teams')}</p>
            </div>
          ) : floridaData ? (
            <>
              {/* Florida standings — lowest total_net wins */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
                <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
                  <h2 className="font-semibold text-white flex items-center gap-2">
                    <Trophy size={15} className="text-amber-400" />
                    {lbl('Clasificación Florida', 'Florida Standings')}
                  </h2>
                  <span className="text-xs text-zinc-500">
                    {lbl('Mejor neto acumulado', 'Cumulative best net')}
                  </span>
                </div>
                <div className="divide-y divide-zinc-800">
                  {floridaData.teams.map((team, idx) => {
                    const ui = MATCH_TEAM_UI[team.color] ?? MATCH_TEAM_UI.emerald
                    const isLeader = idx === 0 && team.holes_completed > 0
                    return (
                      <div key={team.team_number} className={`px-5 py-4 flex items-center justify-between ${isLeader ? ui.bg : ''}`}>
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border ${ui.bg} ${ui.border} ${ui.text}`}>
                            {team.name.slice(-1)}
                          </div>
                          <div>
                            <p className={`font-semibold text-sm ${ui.text}`}>{team.name}</p>
                            <p className="text-xs text-zinc-500">
                              {team.players.map(p => p.name.split(' ')[0]).join(', ')}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-right">
                          <div className="text-center">
                            <p className="text-xs text-zinc-600 mb-0.5">{lbl('Neto', 'Net')}</p>
                            <p className={`text-2xl font-bold ${team.holes_completed > 0 ? ui.text : 'text-zinc-600'}`}>
                              {team.holes_completed > 0 ? team.total_net : '—'}
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-zinc-600 mb-0.5">{lbl('Hoyos', 'Holes')}</p>
                            <p className="text-sm font-medium text-zinc-400">{team.holes_completed}</p>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Hole-by-hole Florida grid */}
              {floridaData.hole_results.length > 0 && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
                  <div className="px-5 py-3 border-b border-zinc-800">
                    <h3 className="text-sm font-medium text-zinc-300">{lbl('Mejor neto por hoyo', 'Best net per hole')}</h3>
                  </div>
                  <div className="px-5 py-4">
                    <div className="flex flex-wrap gap-2">
                      {floridaData.hole_results.map(hr => {
                        const winner = floridaData.teams.find(t => t.team_number === hr.winner_team)
                        const ui = winner ? (MATCH_TEAM_UI[winner.color] ?? MATCH_TEAM_UI.emerald) : null
                        const scores = hr.team_scores as Record<string, number>
                        const bestNet = Object.values(scores).length > 0 ? Math.min(...Object.values(scores)) : null
                        return (
                          <div key={hr.hole}
                            className={`w-10 h-10 rounded-full flex flex-col items-center justify-center border text-xs font-bold transition-all ${
                              hr.status === 'pending'
                                ? 'bg-zinc-800 border-zinc-700 text-zinc-600'
                                : hr.status === 'tied'
                                ? 'bg-zinc-700 border-zinc-600 text-zinc-300'
                                : ui
                                ? `${ui.bg} ${ui.border} ${ui.text}`
                                : 'bg-zinc-800 border-zinc-700 text-zinc-500'
                            }`}>
                            <span>{hr.hole}</span>
                            {hr.status !== 'pending' && bestNet !== null && (
                              <span className="text-[9px] leading-none mt-0.5">{bestNet}</span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                    <div className="flex flex-wrap gap-3 mt-4 pt-3 border-t border-zinc-800">
                      {floridaData.teams.map(team => {
                        const ui = MATCH_TEAM_UI[team.color] ?? MATCH_TEAM_UI.emerald
                        return (
                          <div key={team.team_number} className="flex items-center gap-1.5">
                            <span className={`w-3 h-3 rounded-full ${ui.dot}`} />
                            <span className={`text-xs ${ui.text}`}>{team.name} ({team.total_net || '—'})</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={() => {
                  setFloridaLoading(true)
                  api.get(`/rounds/${id}/florida-scores`)
                    .then(r => setFloridaData(r.data))
                    .finally(() => setFloridaLoading(false))
                }}
                className="w-full flex items-center justify-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white text-sm py-2.5 rounded-xl transition-colors border border-zinc-700">
                <RotateCcw size={13} />
                {lbl('Actualizar', 'Refresh')}
              </button>
            </>
          ) : null}
        </div>
      )}

      {view === 'match' && gameFormat !== 'florida' && (
        <div className="flex-1 overflow-auto px-4 py-5 max-w-lg mx-auto w-full space-y-4">
          {matchLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-emerald-500" />
            </div>
          ) : !matchData?.has_teams ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-6 py-10 text-center">
              <Trophy size={32} className="text-zinc-600 mx-auto mb-3" />
              <p className="text-zinc-400 font-medium mb-1">{lbl('Sin equipos asignados', 'No teams assigned')}</p>
              <p className="text-xs text-zinc-600">{lbl('Genera los equipos desde la pantalla de la ronda', 'Generate teams from the round screen')}</p>
            </div>
          ) : matchData ? (
            <>
              {/* Standings */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
                <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
                  <h2 className="font-semibold text-white flex items-center gap-2">
                    <Trophy size={15} className="text-amber-400" />
                    {lbl('Clasificación', 'Standings')}
                  </h2>
                  <span className="text-xs text-zinc-500">
                    {matchData.holes_played} {lbl('hoyos jugados', 'holes played')}
                  </span>
                </div>
                <div className="divide-y divide-zinc-800">
                  {[...matchData.teams]
                    .sort((a, b) => b.holes_won - a.holes_won || a.holes_lost - b.holes_lost)
                    .map((team, idx) => {
                      const ui = MATCH_TEAM_UI[team.color] ?? MATCH_TEAM_UI.emerald
                      const isLeader = idx === 0 && team.holes_won > 0
                      return (
                        <div key={team.team_number} className={`px-5 py-4 flex items-center justify-between ${isLeader ? ui.bg : ''}`}>
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border ${ui.bg} ${ui.border} ${ui.text}`}>
                              {team.name.slice(-1)}
                            </div>
                            <div>
                              <p className={`font-semibold text-sm ${ui.text}`}>{team.name}</p>
                              <p className="text-xs text-zinc-500">
                                {team.players.map(p => p.name.split(' ')[0]).join(', ')}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-4 text-right">
                            <div className="text-center">
                              <p className="text-xs text-zinc-600 mb-0.5">{lbl('Gan', 'Won')}</p>
                              <p className={`text-lg font-bold ${team.holes_won > 0 ? ui.text : 'text-zinc-500'}`}>{team.holes_won}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-xs text-zinc-600 mb-0.5">{lbl('Emp', 'Tie')}</p>
                              <p className="text-sm font-medium text-zinc-400">{team.holes_tied}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-xs text-zinc-600 mb-0.5">{lbl('Perd', 'Lost')}</p>
                              <p className={`text-sm font-medium ${team.holes_lost > 0 ? 'text-red-400' : 'text-zinc-500'}`}>{team.holes_lost}</p>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                </div>
              </div>

              {/* Hole-by-hole grid */}
              {matchData.hole_results.length > 0 && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
                  <div className="px-5 py-3 border-b border-zinc-800">
                    <h3 className="text-sm font-medium text-zinc-300">{lbl('Resultado por hoyo', 'Hole results')}</h3>
                  </div>
                  <div className="px-5 py-4">
                    <div className="flex flex-wrap gap-2">
                      {matchData.hole_results.map(hr => {
                        const winner = matchData.teams.find(t => t.team_number === hr.winner_team)
                        const ui = winner ? (MATCH_TEAM_UI[winner.color] ?? MATCH_TEAM_UI.emerald) : null
                        return (
                          <div key={hr.hole}
                            className={`w-10 h-10 rounded-full flex flex-col items-center justify-center border text-xs font-bold transition-all ${
                              hr.status === 'pending'
                                ? 'bg-zinc-800 border-zinc-700 text-zinc-600'
                                : hr.status === 'tied'
                                ? 'bg-zinc-700 border-zinc-600 text-zinc-300'
                                : ui
                                ? `${ui.bg} ${ui.border} ${ui.text}`
                                : 'bg-zinc-800 border-zinc-700 text-zinc-500'
                            }`}>
                            <span>{hr.hole}</span>
                            {hr.status !== 'pending' && (
                              <span className="text-[9px] leading-none mt-0.5">
                                {hr.status === 'tied' ? '=' : winner?.name.slice(-1)}
                              </span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                    {/* Legend */}
                    <div className="flex flex-wrap gap-3 mt-4 pt-3 border-t border-zinc-800">
                      {matchData.teams.map(team => {
                        const ui = MATCH_TEAM_UI[team.color] ?? MATCH_TEAM_UI.emerald
                        return (
                          <div key={team.team_number} className="flex items-center gap-1.5">
                            <span className={`w-3 h-3 rounded-full ${ui.dot}`} />
                            <span className={`text-xs ${ui.text}`}>{team.name}</span>
                          </div>
                        )
                      })}
                      <div className="flex items-center gap-1.5">
                        <span className="w-3 h-3 rounded-full bg-zinc-600" />
                        <span className="text-xs text-zinc-500">{lbl('Empate', 'Tie')}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Refresh button */}
              <button
                onClick={() => {
                  setMatchLoading(true)
                  api.get(`/rounds/${id}/match-scores`)
                    .then(r => setMatchData(r.data))
                    .finally(() => setMatchLoading(false))
                }}
                className="w-full flex items-center justify-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white text-sm py-2.5 rounded-xl transition-colors border border-zinc-700">
                <RotateCcw size={13} />
                {lbl('Actualizar marcador', 'Refresh scoreboard')}
              </button>
            </>
          ) : null}
        </div>
      )}

      {/* ── INPUT VIEW ────────────────────────────────────────────────────── */}
      {view === 'input' && (
        <>
          {/* Hole info bar */}
          {hole && (
            <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
              <div className="max-w-lg mx-auto flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 text-sm font-bold flex items-center justify-center">
                      {hole.hole_number}
                    </span>
                    <span className={`text-2xl font-bold ${PAR_COLOR[hole.par] ?? 'text-white'}`}>
                      Par {hole.par}
                    </span>
                  </div>
                  {hole.stroke_index && (
                    <p className="text-xs text-zinc-500 pl-10">Stroke Index {hole.stroke_index}</p>
                  )}
                </div>
                {(() => {
                  const yds = myTee === 'black' ? hole.distance_yards_black
                    : myTee === 'blue'  ? hole.distance_yards_blue
                    : myTee === 'red'   ? hole.distance_yards_red
                    : hole.distance_yards_white
                  const teeColor = myTee === 'black' ? 'text-zinc-300'
                    : myTee === 'blue'  ? 'text-blue-400'
                    : myTee === 'red'   ? 'text-red-400'
                    : 'text-white'
                  const teeLbl = myTee === 'black' ? lbl('yds negra', 'black yds')
                    : myTee === 'blue'  ? lbl('yds azul', 'blue yds')
                    : myTee === 'red'   ? lbl('yds roja', 'red yds')
                    : lbl('yds blanca', 'white yds')
                  return yds ? (
                    <div className="text-right">
                      <p className={`text-lg font-bold ${teeColor}`}>{yds}</p>
                      <p className="text-xs text-zinc-500">{teeLbl}</p>
                    </div>
                  ) : null
                })()}
              </div>
            </div>
          )}

          {/* Score input */}
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 max-w-lg mx-auto w-full">
            {/* Conflict banner (live) */}
            {conflictBanner && (
              <div className="w-full mb-4 bg-red-500/10 border border-red-500/40 rounded-xl px-4 py-3 flex items-start gap-3">
                <AlertTriangle size={18} className="text-red-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1 text-sm">
                  <p className="font-semibold text-red-300">
                    {lbl('Conflicto de score', 'Score conflict')} — {lbl('Hoyo', 'Hole')} {conflictBanner.hole}
                  </p>
                  <p className="text-zinc-400 text-xs mt-0.5">
                    {lbl('Valores en disputa', 'Disputed values')}: {conflictBanner.a} vs {conflictBanner.b}
                  </p>
                </div>
                <button
                  onClick={() => setConflictBanner(null)}
                  className="text-red-300 hover:text-red-200 text-xs underline">
                  {lbl('Cerrar', 'Close')}
                </button>
              </div>
            )}

            {/* Pending conflicts list */}
            {conflicts.length > 0 && (
              <div className="w-full mb-4 bg-amber-500/10 border border-amber-500/40 rounded-xl px-4 py-3">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={15} className="text-amber-400" />
                  <p className="text-sm font-semibold text-amber-300">
                    {conflicts.length} {lbl('conflicto(s) pendiente(s)', 'pending conflict(s)')}
                  </p>
                </div>
                <div className="space-y-1.5">
                  {conflicts.map((c) => (
                    <div key={`${c.user_id}-${c.hole_number}`}
                      className="flex items-center justify-between text-xs bg-zinc-900/50 rounded-lg px-3 py-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-zinc-200 truncate">{c.player_name}</p>
                        <p className="text-zinc-500">{lbl('Hoyo', 'Hole')} {c.hole_number} · {c.score_a} vs {c.score_b}</p>
                      </div>
                      {(c.user_id === myUserId || amCreator) && (
                        <button
                          onClick={() => { setResolvingFor(c); setResolvingValue(c.score_a) }}
                          className="ml-2 px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-zinc-900 font-semibold rounded-md text-xs">
                          {lbl('Resolver', 'Resolve')}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Target selector (only if I have group mates) */}
            {groupMates.length > 0 && (
              <div className="w-full mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <Users size={13} className="text-zinc-500" />
                  <p className="text-xs text-zinc-500 uppercase tracking-wider">
                    {lbl('Capturar score de', 'Recording score for')}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setTargetUserId('')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                      !targetUserId
                        ? 'bg-emerald-500 border-emerald-400 text-white'
                        : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                    }`}>
                    {lbl('Yo', 'Me')}
                  </button>
                  {groupMates.map(m => (
                    <button
                      key={m.user_id}
                      onClick={() => setTargetUserId(m.user_id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                        targetUserId === m.user_id
                          ? 'bg-blue-500 border-blue-400 text-white'
                          : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                      }`}>
                      {m.name.split(' ')[0]}
                    </button>
                  ))}
                </div>
                {myStartingHole && (
                  <p className="text-[10px] text-zinc-600 mt-1.5">
                    {lbl('Tu grupo arranca en hoyo', 'Your group starts at hole')} {myStartingHole}
                  </p>
                )}
              </div>
            )}

            {scores[currentHole] && (!targetUserId || targetUserId === myUserId) && (
              <div className="mb-4 flex items-center gap-2 text-sm text-emerald-400">
                <CheckCircle2 size={15} />
                {lbl('Hoyo registrado — puedes corregir', 'Hole recorded — you can correct')}
              </div>
            )}
            {targetUserId && targetUserId !== myUserId && (
              <div className="mb-4 flex items-center gap-2 text-sm text-blue-400">
                <Users size={15} />
                {lbl(
                  `Capturando para ${groupMates.find(m => m.user_id === targetUserId)?.name.split(' ')[0] ?? ''}`,
                  `Recording for ${groupMates.find(m => m.user_id === targetUserId)?.name.split(' ')[0] ?? ''}`
                )}
              </div>
            )}

            {/* Gross */}
            <div className="text-center mb-6 w-full">
              <p className="text-xs text-zinc-500 mb-3 uppercase tracking-wider">{lbl('Golpes', 'Strokes')}</p>
              <div className="flex items-center justify-center gap-6">
                <button onClick={() => setGrossInput(Math.max(1, grossInput - 1))}
                  className="w-14 h-14 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-white hover:bg-zinc-700 active:scale-95 transition-all">
                  <Minus size={22} />
                </button>
                <div className="text-center">
                  <span className="text-7xl font-bold text-white tabular-nums">{grossInput}</span>
                  {hole && grossInput > 0 && (() => {
                    const { text, cls } = scoreLabel(grossInput, hole.par)
                    return <p className={`text-sm mt-1 ${cls}`}>{text}</p>
                  })()}
                </div>
                <button onClick={() => setGrossInput(grossInput + 1)}
                  className="w-14 h-14 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-white hover:bg-zinc-700 active:scale-95 transition-all">
                  <Plus size={22} />
                </button>
              </div>
            </div>

            {/* Putts */}
            <div className="text-center mb-8 w-full">
              <p className="text-xs text-zinc-500 mb-3 uppercase tracking-wider">{lbl('Putts (opcional)', 'Putts (optional)')}</p>
              <div className="flex items-center justify-center gap-4">
                {[1, 2, 3, 4].map(n => (
                  <button key={n} onClick={() => setPuttsInput(puttsInput === n ? null : n)}
                    className={`w-11 h-11 rounded-full text-sm font-bold border transition-all ${
                      puttsInput === n
                        ? 'bg-emerald-500 border-emerald-400 text-white'
                        : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                    }`}>
                    {n}
                  </button>
                ))}
              </div>
            </div>

            {/* Submit */}
            <button onClick={submitScore} disabled={submitting}
              className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-4 rounded-2xl transition-colors text-base active:scale-95">
              {submitting ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
              {lbl('Registrar hoyo', 'Record hole')}
            </button>
          </div>

          {/* Resolve conflict modal */}
          {resolvingFor && (
            <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
                 onClick={() => !resolving && setResolvingFor(null)}>
              <div onClick={e => e.stopPropagation()}
                   className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle size={18} className="text-amber-400" />
                  <h3 className="font-semibold text-white">
                    {lbl('Resolver conflicto', 'Resolve conflict')}
                  </h3>
                </div>
                <p className="text-sm text-zinc-400 mb-1">
                  <span className="text-zinc-200 font-medium">{resolvingFor.player_name}</span>
                  {' · '}{lbl('Hoyo', 'Hole')} {resolvingFor.hole_number}
                </p>
                <p className="text-xs text-zinc-500 mb-4">
                  {lbl('Valores en disputa', 'Disputed values')}: <span className="text-zinc-300">{resolvingFor.score_a}</span>
                  {' '}{lbl('vs', 'vs')}{' '}
                  <span className="text-zinc-300">{resolvingFor.score_b}</span>
                </p>

                <div className="flex items-center justify-center gap-4 mb-4">
                  <button onClick={() => setResolvingValue(Math.max(1, resolvingValue - 1))}
                    className="w-11 h-11 rounded-full bg-zinc-800 border border-zinc-700 text-white hover:bg-zinc-700 flex items-center justify-center">
                    <Minus size={18} />
                  </button>
                  <span className="text-5xl font-bold text-white tabular-nums w-16 text-center">{resolvingValue}</span>
                  <button onClick={() => setResolvingValue(resolvingValue + 1)}
                    className="w-11 h-11 rounded-full bg-zinc-800 border border-zinc-700 text-white hover:bg-zinc-700 flex items-center justify-center">
                    <Plus size={18} />
                  </button>
                </div>

                <div className="flex gap-2 mb-4">
                  <button onClick={() => setResolvingValue(resolvingFor.score_a)}
                    className={`flex-1 py-2 rounded-lg text-xs font-medium border ${
                      resolvingValue === resolvingFor.score_a
                        ? 'bg-emerald-500 border-emerald-400 text-white'
                        : 'bg-zinc-800 border-zinc-700 text-zinc-400'
                    }`}>
                    {lbl('Usar', 'Use')} {resolvingFor.score_a}
                  </button>
                  <button onClick={() => setResolvingValue(resolvingFor.score_b)}
                    className={`flex-1 py-2 rounded-lg text-xs font-medium border ${
                      resolvingValue === resolvingFor.score_b
                        ? 'bg-emerald-500 border-emerald-400 text-white'
                        : 'bg-zinc-800 border-zinc-700 text-zinc-400'
                    }`}>
                    {lbl('Usar', 'Use')} {resolvingFor.score_b}
                  </button>
                </div>

                <div className="flex gap-2">
                  <button onClick={() => setResolvingFor(null)} disabled={resolving}
                    className="flex-1 py-2.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm font-medium">
                    {lbl('Cancelar', 'Cancel')}
                  </button>
                  <button onClick={resolveConflict} disabled={resolving}
                    className="flex-1 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-60 text-zinc-900 text-sm font-semibold flex items-center justify-center gap-1.5">
                    {resolving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                    {lbl('Confirmar', 'Confirm')}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Bottom: hole dots + nav */}
          <div className="bg-zinc-900 border-t border-zinc-800 px-4 py-3">
            <div className="max-w-lg mx-auto">
              <div className="flex gap-1 justify-center mb-3 flex-wrap">
                {Array.from({ length: holesTotal }, (_, i) => i + 1).map(h => {
                  const sc = scores[h]
                  const holeData = holes.find(x => x.hole_number === h)
                  const diff = sc && holeData ? sc.gross - holeData.par : null
                  return (
                    <button key={h} onClick={() => setCurrentHole(h)}
                      className={`w-7 h-7 rounded-full text-xs font-bold transition-all ${
                        h === currentHole ? 'ring-2 ring-emerald-400 ring-offset-1 ring-offset-zinc-900' : ''
                      } ${
                        !sc ? 'bg-zinc-800 text-zinc-500' :
                        diff! < 0 ? 'bg-emerald-500 text-white' :
                        diff === 0 ? 'bg-zinc-600 text-white' :
                        diff === 1 ? 'bg-orange-500/80 text-white' :
                        'bg-red-600 text-white'
                      }`}>
                      {h}
                    </button>
                  )
                })}
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setCurrentHole(Math.max(1, currentHole - 1))}
                  disabled={currentHole === 1}
                  className="flex-1 flex items-center justify-center gap-1 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 text-white py-2 rounded-xl text-sm transition-colors">
                  <ChevronLeft size={16} />{lbl('Anterior', 'Prev')}
                </button>
                {allPlayed ? (
                  <button onClick={handleFinish} disabled={finishing}
                    className="flex-1 flex items-center justify-center gap-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-2 rounded-xl text-sm transition-colors">
                    {finishing ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                    {lbl('Finalizar', 'Finish')}
                  </button>
                ) : (
                  <button onClick={() => setCurrentHole(Math.min(holesTotal, currentHole + 1))}
                    disabled={currentHole === holesTotal}
                    className="flex-1 flex items-center justify-center gap-1 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 text-white py-2 rounded-xl text-sm transition-colors">
                    {lbl('Siguiente', 'Next')}<ChevronRight size={16} />
                  </button>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
