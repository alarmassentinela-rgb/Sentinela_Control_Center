'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { ChevronLeft, ChevronRight, CheckCircle2, Loader2, Minus, Plus, RotateCcw, Table2, Pencil, Trophy, AlertTriangle, Users, X } from 'lucide-react'
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

interface LeaderboardRow {
  user_id: string
  first_name: string
  last_name: string
  course_handicap: number | null
  team_number: number | null
  holes_played: number
  thru: number
  total_gross: number
  total_net: number
  total_stableford: number
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

// ─── Multi-Player Scorecard ───────────────────────────────────────────────────
function MultiPlayerScorecard({
  holes, allScores, holesTotal, players, onEdit, lbl,
}: {
  holes: Hole[]
  allScores: Record<string, Record<number, Score>>
  holesTotal: number
  players: { user_id: string; name: string; course_handicap: number | null; isMe: boolean }[]
  onEdit: (h: number) => void
  lbl: (es: string, en: string) => string
}) {
  const activeHoles = holes.filter(h => h.hole_number <= holesTotal).sort((a, b) => a.hole_number - b.hole_number)
  const front = activeHoles.filter(h => h.hole_number <= 9)
  const back = activeHoles.filter(h => h.hole_number > 9)

  const sumPar = (hs: Hole[]) => hs.reduce((s, h) => s + h.par, 0)
  const sumGross = (uid: string, hs: Hole[]) =>
    hs.reduce((s, h) => {
      const sc = allScores[uid]?.[h.hole_number]
      return sc ? s + sc.gross : s
    }, 0)
  const countPlayed = (uid: string, hs: Hole[]) =>
    hs.filter(h => allScores[uid]?.[h.hole_number]).length

  const sections = holesTotal === 18
    ? [
        { label: lbl('Salida', 'Out'), hs: front },
        { label: lbl('Vuelta', 'In'), hs: back },
      ]
    : [
        { label: lbl('Total', 'Total'), hs: activeHoles },
      ]

  return (
    <div className="space-y-5">
      {sections.map(({ label, hs }) => (
        <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs tabular-nums">
              <thead>
                {/* Hole numbers */}
                <tr className="bg-zinc-950 border-b border-zinc-800">
                  <th className="text-left text-[10px] text-zinc-500 uppercase tracking-wider py-2 px-2 sticky left-0 bg-zinc-950 z-10 min-w-[100px]">
                    {label}
                  </th>
                  {hs.map(h => (
                    <th key={h.hole_number}
                      onClick={() => onEdit(h.hole_number)}
                      className="text-center py-2 px-1 text-[10px] text-zinc-500 font-medium cursor-pointer hover:text-emerald-400 min-w-[26px]">
                      {h.hole_number}
                    </th>
                  ))}
                  <th className="text-center py-2 px-2 text-[10px] text-emerald-400 font-bold uppercase">
                    Tot
                  </th>
                </tr>
                {/* Par */}
                <tr className="border-b border-zinc-800/60">
                  <th className="text-left text-[10px] text-zinc-600 py-1.5 px-2 sticky left-0 bg-zinc-900 z-10 font-medium">
                    {lbl('Par', 'Par')}
                  </th>
                  {hs.map(h => (
                    <td key={h.hole_number}
                      className={`text-center py-1.5 text-xs font-semibold ${PAR_COLOR[h.par] ?? 'text-white'}`}>
                      {h.par}
                    </td>
                  ))}
                  <td className="text-center py-1.5 text-xs font-bold text-zinc-300 px-2">
                    {sumPar(hs)}
                  </td>
                </tr>
                {/* Stroke Index */}
                <tr className="border-b border-zinc-800">
                  <th className="text-left text-[10px] text-zinc-600 py-1.5 px-2 sticky left-0 bg-zinc-900 z-10 font-medium">
                    SI
                  </th>
                  {hs.map(h => (
                    <td key={h.hole_number} className="text-center py-1.5 text-[10px] text-zinc-600">
                      {h.stroke_index ?? '—'}
                    </td>
                  ))}
                  <td />
                </tr>
              </thead>
              <tbody>
                {players.map((p, idx) => {
                  const isLast = idx === players.length - 1
                  const grossTotal = sumGross(p.user_id, hs)
                  const played = countPlayed(p.user_id, hs)
                  const parTotal = sumPar(hs)
                  const diff = played === hs.length ? grossTotal - parTotal : null
                  return (
                    <tr key={p.user_id}
                      className={`${isLast ? '' : 'border-b border-zinc-800/60'} ${p.isMe ? 'bg-emerald-500/5' : ''}`}>
                      <th className={`text-left py-2 px-2 sticky left-0 z-10 ${p.isMe ? 'bg-emerald-500/5' : 'bg-zinc-900'}`}>
                        <p className={`text-xs font-semibold truncate max-w-[90px] ${p.isMe ? 'text-emerald-300' : 'text-zinc-200'}`}>
                          {p.name}
                        </p>
                        {p.course_handicap !== null && (
                          <p className="text-[9px] text-zinc-600 font-normal">HCP {p.course_handicap}</p>
                        )}
                      </th>
                      {hs.map(h => {
                        const sc = allScores[p.user_id]?.[h.hole_number]
                        if (!sc) {
                          return (
                            <td key={h.hole_number}
                              onClick={() => onEdit(h.hole_number)}
                              className="text-center py-2 text-zinc-700 cursor-pointer hover:bg-zinc-800/40">
                              —
                            </td>
                          )
                        }
                        const cellCls = scoreCellStyle(sc.gross, h.par)
                        return (
                          <td key={h.hole_number}
                            onClick={() => onEdit(h.hole_number)}
                            className="text-center py-1.5 px-0.5 cursor-pointer hover:bg-zinc-800/40">
                            <span className={`inline-flex items-center justify-center w-6 h-6 text-xs font-bold ${cellCls}`}>
                              {sc.gross}
                            </span>
                          </td>
                        )
                      })}
                      <td className="text-center py-2 px-2">
                        {played === 0 ? (
                          <span className="text-zinc-700 text-xs">—</span>
                        ) : (
                          <div>
                            <p className="text-sm font-bold text-white">{grossTotal}</p>
                            {diff !== null && (
                              <p className={`text-[9px] font-medium ${
                                diff < 0 ? 'text-emerald-400' :
                                diff > 0 ? 'text-red-400' :
                                'text-zinc-400'
                              }`}>
                                {diff === 0 ? 'E' : diff > 0 ? `+${diff}` : diff}
                              </p>
                            )}
                          </div>
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

      {/* Grand total — 18 holes only */}
      {holesTotal === 18 && (
        <div className="bg-zinc-900 border border-zinc-700 rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 bg-zinc-950 border-b border-zinc-800">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">{lbl('Total ronda', 'Round total')}</p>
          </div>
          <table className="w-full text-xs tabular-nums">
            <tbody>
              {players.map(p => {
                const gT = sumGross(p.user_id, activeHoles)
                const pT = sumPar(activeHoles)
                const played = countPlayed(p.user_id, activeHoles)
                const diff = played === activeHoles.length ? gT - pT : null
                return (
                  <tr key={p.user_id} className={`border-b border-zinc-800/60 ${p.isMe ? 'bg-emerald-500/5' : ''}`}>
                    <th className={`text-left px-4 py-2 ${p.isMe ? 'text-emerald-300' : 'text-zinc-200'} text-sm font-semibold`}>
                      {p.name}
                    </th>
                    <td className="text-center text-zinc-500 text-xs py-2">
                      {played}/{activeHoles.length} {lbl('hoyos', 'holes')}
                    </td>
                    <td className="text-right px-4 py-2">
                      {played === 0 ? (
                        <span className="text-zinc-700">—</span>
                      ) : (
                        <div className="flex items-baseline gap-2 justify-end">
                          <span className="text-xl font-bold text-white">{gT}</span>
                          {diff !== null && (
                            <span className={`text-xs font-medium ${
                              diff < 0 ? 'text-emerald-400' :
                              diff > 0 ? 'text-red-400' :
                              'text-zinc-400'
                            }`}>
                              {diff === 0 ? 'E' : diff > 0 ? `+${diff}` : diff}
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
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
  // scores: solo MIS scores (para mantener la vista Card existente)
  const [scores, setScores] = useState<Record<number, Score>>({})
  // allScores: scores de TODOS los jugadores del grupo (incluye yo + mates)
  const [allScores, setAllScores] = useState<Record<string, Record<number, Score>>>({})
  // rowInputs: estado local del hoyo actual por jugador (gross/putts/dirty)
  const [rowInputs, setRowInputs] = useState<Record<string, { gross: number; putts: number | null; dirty: boolean }>>({})
  const [currentHole, setCurrentHole] = useState(1)
  const [holesTotal, setHolesTotal] = useState(18)
  const [myTee, setMyTee] = useState<string>('blue')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [view, setView] = useState<'input' | 'card' | 'match' | 'leaderboard'>('input')
  const [matchData, setMatchData] = useState<MatchData | null>(null)
  const [matchLoading, setMatchLoading] = useState(false)
  const [amCreator, setAmCreator] = useState(false)
  const [gameFormat, setGameFormat] = useState<string>('')
  const [floridaData, setFloridaData] = useState<FloridaData | null>(null)
  const [floridaLoading, setFloridaLoading] = useState(false)
  const [myUserId, setMyUserId] = useState<string>('')
  const [myCourseHandicap, setMyCourseHandicap] = useState<number | null>(null)
  const [showSiHelp, setShowSiHelp] = useState(false)
  const [myStartingHole, setMyStartingHole] = useState<number | null>(null)
  const [groupMates, setGroupMates] = useState<GroupMate[]>([])
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
      type PlayerRow = {
        user_id: string
        first_name: string
        last_name: string
        username: string
        course_handicap: number | null
        tee_color: string | null
        status: string
      }
      const playersList = playersRes.data as PlayerRow[]
      const myPlayer = playersList.find(p => p.user_id === me.id)
      if (myPlayer?.tee_color) setMyTee(myPlayer.tee_color)
      if (myPlayer?.course_handicap !== undefined) setMyCourseHandicap(myPlayer.course_handicap)
      setAmCreator(round.created_by === me.id)
      setGameFormat(round.game_format)
      const courseRes = await api.get(`/courses/${round.course_id}`)
      setHoles(courseRes.data.holes)

      // Tee groups: encontrar mi grupo y compañeros. Si no hay grupos asignados
      // (ronda legacy), caer a "todos los demás jugadores confirmados".
      let usedGroups = false
      try {
        const tgRes = await api.get(`/rounds/${id}/tee-groups`)
        const tg = tgRes.data
        if (tg.has_groups) {
          type TGP = { user_id: string; name: string; username: string; course_handicap: number | null }
          type TGG = { group_number: number; starting_hole: number | null; players: TGP[] }
          const myGroup = (tg.groups as TGG[]).find(g => g.players.some(p => p.user_id === me.id))
          if (myGroup) {
            usedGroups = true
            setMyStartingHole(myGroup.starting_hole ?? null)
            setGroupMates(myGroup.players.filter(p => p.user_id !== me.id))
            if (myGroup.starting_hole && myGroup.starting_hole > 1) {
              setCurrentHole(myGroup.starting_hole)
            }
          }
        }
      } catch { /* sin grupos — usamos fallback abajo */ }

      if (!usedGroups) {
        // Fallback legacy: todos los demás jugadores confirmados son compañeros
        const mates: GroupMate[] = playersList
          .filter(p => p.user_id !== me.id && ['confirmed', 'playing', 'finished'].includes(p.status))
          .map(p => ({
            user_id: p.user_id,
            name: `${p.first_name} ${p.last_name}`,
            username: p.username,
            course_handicap: p.course_handicap,
          }))
        setGroupMates(mates)
      }

      // Conflictos existentes
      try {
        const cRes = await api.get(`/rounds/${id}/conflicts`)
        setConflicts(cRes.data ?? [])
      } catch { /* ignore */ }

      const boardRes = await api.get(`/rounds/${id}/scoreboard`)
      type BoardRow = { user_id: string; scores: Score[] }
      const all: Record<string, Record<number, Score>> = {}
      for (const row of (boardRes.data as BoardRow[])) {
        const m: Record<number, Score> = {}
        for (const s of (row.scores ?? [])) m[s.hole] = s
        all[row.user_id] = m
      }
      setAllScores(all)
      const myEntry = (boardRes.data as BoardRow[]).find(e => e.user_id === me.id)
      if (myEntry?.scores?.length) {
        const saved: Record<number, Score> = {}
        myEntry.scores.forEach((s: Score) => { saved[s.hole] = s })
        setScores(saved)
        const lastPlayed = Math.max(...myEntry.scores.map((s: Score) => s.hole))
        if (lastPlayed < round.holes_to_play && (!usedGroups)) setCurrentHole(lastPlayed + 1)
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
            if (msg.event === 'score_update') {
              const { user_id, hole, gross, net } = msg
              setAllScores(prev => ({
                ...prev,
                [user_id]: { ...(prev[user_id] ?? {}), [hole]: { hole, gross, net: net ?? gross } },
              }))
              if (user_id === me.id) {
                setScores(prev => ({ ...prev, [hole]: { hole, gross, net: net ?? gross } }))
              }
            } else if (msg.event === 'score_conflict') {
              setConflictBanner({ user_id: msg.user_id, hole: msg.hole, a: msg.score_a, b: msg.score_b })
              try {
                const cRes = await api.get(`/rounds/${id}/conflicts`)
                setConflicts(cRes.data ?? [])
              } catch { /* ignore */ }
            } else if (msg.event === 'conflict_resolved') {
              setConflicts(prev => prev.filter(c => !(c.user_id === msg.user_id && c.hole_number === msg.hole)))
              setConflictBanner(prev => (prev && prev.user_id === msg.user_id && prev.hole === msg.hole) ? null : prev)
              setAllScores(prev => {
                const existing = prev[msg.user_id]?.[msg.hole]
                if (!existing) return prev
                return { ...prev, [msg.user_id]: { ...prev[msg.user_id], [msg.hole]: { ...existing, gross: msg.final_score } } }
              })
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

  // Reset row inputs cuando cambia de hoyo o cambian los jugadores.
  // Preserva filas con dirty=true (edición en curso) — no las pisa con allScores.
  useEffect(() => {
    const hole = holes.find(h => h.hole_number === currentHole)
    if (!hole || !myUserId) return
    setRowInputs(prev => {
      const next: Record<string, { gross: number; putts: number | null; dirty: boolean }> = {}
      const buildFor = (uid: string) => {
        const existing = allScores[uid]?.[currentHole]
        const cur = prev[uid]
        if (cur?.dirty) return cur  // edición en curso, no pisar
        return { gross: existing?.gross ?? hole.par, putts: existing?.putts ?? null, dirty: false }
      }
      next[myUserId] = buildFor(myUserId)
      for (const m of groupMates) next[m.user_id] = buildFor(m.user_id)
      return next
    })
  }, [currentHole, holes, myUserId, groupMates, allScores])

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

  // Refrescar marcador al entrar a la vista y cuando cambian los scores
  const [leaderboardLoading, setLeaderboardLoading] = useState(false)
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([])
  useEffect(() => {
    if (view !== 'leaderboard') return
    setLeaderboardLoading(true)
    api.get(`/rounds/${id}/scoreboard`)
      .then(r => setLeaderboard(r.data ?? []))
      .finally(() => setLeaderboardLoading(false))
  }, [view, id, allScores])

  const submitScore = async () => {
    setSubmitting(true)
    try {
      const dirtyEntries = Object.entries(rowInputs).filter(([, v]) => v.dirty)
      if (dirtyEntries.length === 0) {
        // Nada que enviar — solo avanzar
        if (currentHole < holesTotal) setCurrentHole(currentHole + 1)
        return
      }
      const results = await Promise.allSettled(dirtyEntries.map(([uid, v]) => {
        const payload: Record<string, unknown> = {
          hole_number: currentHole,
          gross_score: v.gross,
          putts: v.putts,
        }
        if (uid !== myUserId) payload.for_user_id = uid
        return api.post(`/rounds/${id}/scores`, payload).then(res => ({ uid, gross: v.gross, putts: v.putts, net: res.data.net_score as number, has_conflict: res.data.has_conflict as boolean }))
      }))

      // Aplicar resultados al estado
      const newAll = { ...allScores }
      let anyConflict = false
      let myUpdated = false
      for (const r of results) {
        if (r.status === 'fulfilled') {
          const { uid, gross, putts, net, has_conflict } = r.value
          if (has_conflict) anyConflict = true
          newAll[uid] = { ...(newAll[uid] ?? {}), [currentHole]: { hole: currentHole, gross, net, putts: putts ?? undefined } }
          if (uid === myUserId) myUpdated = true
        }
      }
      setAllScores(newAll)
      if (myUpdated && newAll[myUserId]) setScores(newAll[myUserId])

      // Limpiar dirty de las filas que sí guardaron
      setRowInputs(prev => {
        const next = { ...prev }
        for (const r of results) {
          if (r.status === 'fulfilled') {
            const { uid } = r.value
            next[uid] = { ...next[uid], dirty: false }
          }
        }
        return next
      })

      if (anyConflict) {
        try {
          const cRes = await api.get(`/rounds/${id}/conflicts`)
          setConflicts(cRes.data ?? [])
        } catch { /* ignore */ }
      }

      // Avanzar al siguiente hoyo si TODOS los míos+mates ya tienen score guardado
      const everyoneSaved = [myUserId, ...groupMates.map(m => m.user_id)]
        .every(uid => newAll[uid]?.[currentHole])
      if (everyoneSaved && currentHole < holesTotal) setCurrentHole(currentHole + 1)
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

  const handleFinish = async (force = false) => {
    if (conflicts.length > 0) {
      alert(lbl(
        `Hay ${conflicts.length} conflicto(s) de score sin resolver. Resuelve todos antes de finalizar.`,
        `There are ${conflicts.length} unresolved score conflict(s). Resolve all before finishing.`
      ))
      return
    }
    if (!force && !confirm(lbl('¿Finalizar la ronda?', 'Finish the round?'))) return
    setFinishing(true)
    try {
      await api.post(`/rounds/${id}/finish`, null, force ? { params: { force: true } } : undefined)
      router.push(`/${locale}/rounds/${id}`)
    } catch (e) {
      type FinishDetail = string | { code?: string; message?: string; incomplete?: { name: string; holes_logged: number; holes_total: number }[] }
      const err = e as { response?: { status?: number; data?: { detail?: FinishDetail } } }
      const detail = err.response?.data?.detail
      if (err.response?.status === 409 && typeof detail === 'object' && detail?.code === 'incomplete_players') {
        const list = (detail.incomplete ?? [])
          .map(p => `• ${p.name} (${p.holes_logged}/${p.holes_total})`).join('\n')
        const ok = confirm(lbl(
          `Hay jugadores con scorecard incompleto:\n\n${list}\n\n¿Finalizar de todos modos?`,
          `Players with incomplete scorecard:\n\n${list}\n\nFinish anyway?`
        ))
        if (ok) { setFinishing(false); return handleFinish(true) }
      } else if (err.response?.status === 409 && typeof detail === 'string') {
        alert(detail)
        // Refrescar lista de conflictos por si cambió
        try {
          const cRes = await api.get(`/rounds/${id}/conflicts`)
          setConflicts(cRes.data ?? [])
        } catch { /* ignore */ }
      } else if (typeof detail === 'string') {
        alert(detail)
      }
      setFinishing(false)
    }
  }

  const goToHole = (h: number) => {
    setCurrentHole(h)
    setView('input')
  }

  if (loading) return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center"
      style={{
        backgroundImage: 'linear-gradient(rgba(9,9,11,0.55), rgba(9,9,11,0.55)), url(/play-bg.jpg)',
      }}>
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
    <div className="min-h-screen flex flex-col relative bg-zinc-950">
      {/* Fondo: foto de campo (pinos + lago) con velo oscuro para legibilidad */}
      <div
        aria-hidden
        className="fixed inset-0 -z-10 pointer-events-none bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: 'url(/play-bg.jpg)' }}
      />
      <div
        aria-hidden
        className="fixed inset-0 -z-10 pointer-events-none bg-zinc-950/55"
      />
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
            {(gameFormat === 'match' || gameFormat === 'florida') && (
              <button onClick={() => setView('match')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  view === 'match' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
                }`}>
                <Trophy size={13} />
                {gameFormat === 'florida' ? 'Florida' : 'Match'}
              </button>
            )}
            {(gameFormat === 'stroke' || gameFormat === 'stableford' || gameFormat === 'stableford_modified' || gameFormat === 'skins') && (
              <button onClick={() => setView('leaderboard')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  view === 'leaderboard' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
                }`}>
                <Trophy size={13} />
                {lbl('Marcador', 'Leaderboard')}
              </button>
            )}
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
          {groupMates.length > 0 ? (
            <MultiPlayerScorecard
              holes={holes}
              allScores={allScores}
              holesTotal={holesTotal}
              players={[
                { user_id: myUserId, name: lbl('Yo', 'Me'), course_handicap: null, isMe: true },
                ...groupMates.map(m => ({
                  user_id: m.user_id, name: m.name, course_handicap: m.course_handicap, isMe: false,
                })),
              ]}
              onEdit={goToHole}
              lbl={lbl}
            />
          ) : (
            <ScorecardTable
              holes={holes}
              scores={scores}
              holesTotal={holesTotal}
              tee={myTee}
              onEdit={goToHole}
              lbl={lbl}
            />
          )}
          {amCreator && (
            <button onClick={() => handleFinish(false)} disabled={finishing}
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
      {/* ── LEADERBOARD VIEW ─────────────────────────────────────────────── */}
      {view === 'leaderboard' && (
        <div className="flex-1 overflow-auto px-4 py-5 max-w-lg mx-auto w-full space-y-3">
          {leaderboardLoading && leaderboard.length === 0 ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-emerald-500" />
            </div>
          ) : leaderboard.length === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-6 py-10 text-center">
              <Trophy size={32} className="text-zinc-600 mx-auto mb-3" />
              <p className="text-zinc-400 font-medium">{lbl('Sin scores aún', 'No scores yet')}</p>
            </div>
          ) : (() => {
            const isStableford = gameFormat === 'stableford' || gameFormat === 'stableford_modified'
            // Ordenar: stableford desc (más pts mejor); el resto: gross asc
            const sorted = [...leaderboard].sort((a, b) => {
              if (isStableford) return b.total_stableford - a.total_stableford
              // Stroke / skins: lowest gross wins; jugadores sin scores van al final
              const av = a.total_gross || 999
              const bv = b.total_gross || 999
              return av - bv
            })
            const parTotal = holes.filter(h => h.hole_number <= holesTotal).reduce((s, h) => s + h.par, 0)
            return (
              <>
                <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
                  <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
                    <h2 className="font-semibold text-white flex items-center gap-2 text-sm">
                      <Trophy size={14} className="text-amber-400" />
                      {lbl('Marcador en vivo', 'Live leaderboard')}
                    </h2>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">
                      {isStableford ? lbl('Puntos Stableford', 'Stableford points')
                        : lbl('Bruto vs Par', 'Gross vs Par')}
                    </span>
                  </div>
                  <div className="divide-y divide-zinc-800">
                    {sorted.map((p, idx) => {
                      const isMe = p.user_id === myUserId
                      const grossPlayed = p.total_gross
                      const parPlayed = holes
                        .filter(h => p.thru > 0 && h.hole_number <= p.thru)
                        .reduce((s, h) => s + h.par, 0)
                      const diff = grossPlayed && parPlayed ? grossPlayed - parPlayed : null
                      const projected = p.holes_played === holesTotal
                        ? diff
                        : (diff !== null ? diff : null)
                      const rank = idx + 1
                      return (
                        <div key={p.user_id}
                          className={`flex items-center gap-3 px-4 py-3 ${isMe ? 'bg-emerald-500/5' : ''}`}>
                          {/* Rank */}
                          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                            rank === 1 ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50' :
                            rank === 2 ? 'bg-zinc-400/15 text-zinc-300 border border-zinc-400/30' :
                            rank === 3 ? 'bg-orange-600/15 text-orange-400 border border-orange-600/30' :
                            'bg-zinc-800 text-zinc-500 border border-zinc-700'
                          }`}>
                            {rank}
                          </div>
                          {/* Name + thru */}
                          <div className="flex-1 min-w-0">
                            <p className={`font-semibold truncate ${isMe ? 'text-emerald-300' : 'text-zinc-100'}`}>
                              {p.first_name} {p.last_name}
                              {isMe && <span className="text-[10px] text-emerald-500 ml-1">({lbl('Tú', 'You')})</span>}
                            </p>
                            <p className="text-[10px] text-zinc-500">
                              HCP {p.course_handicap ?? '—'} ·{' '}
                              {p.thru > 0
                                ? p.thru === holesTotal
                                  ? lbl('Terminó', 'Done')
                                  : `${lbl('Hoyo', 'Thru')} ${p.thru}`
                                : lbl('Sin empezar', 'Not started')}
                            </p>
                          </div>
                          {/* Main stat */}
                          <div className="text-right">
                            {isStableford ? (
                              <>
                                <p className="text-2xl font-bold text-emerald-400 tabular-nums leading-none">
                                  {p.total_stableford}
                                </p>
                                <p className="text-[9px] text-zinc-600 uppercase mt-0.5">pts</p>
                              </>
                            ) : (
                              <>
                                <p className="text-2xl font-bold text-white tabular-nums leading-none">
                                  {p.total_gross || '—'}
                                </p>
                                {projected !== null && (
                                  <p className={`text-[11px] font-semibold mt-0.5 ${
                                    projected < 0 ? 'text-emerald-400' :
                                    projected > 0 ? 'text-red-400' :
                                    'text-zinc-400'
                                  }`}>
                                    {projected === 0 ? 'E' : projected > 0 ? `+${projected}` : projected}
                                  </p>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
                {!isStableford && parTotal > 0 && (
                  <p className="text-[10px] text-zinc-600 text-center">
                    {lbl('Par de la ronda', 'Round par')}: {parTotal}
                  </p>
                )}
                <button
                  onClick={() => {
                    setLeaderboardLoading(true)
                    api.get(`/rounds/${id}/scoreboard`)
                      .then(r => setLeaderboard(r.data ?? []))
                      .finally(() => setLeaderboardLoading(false))
                  }}
                  className="w-full flex items-center justify-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 text-sm py-2.5 rounded-xl border border-zinc-700">
                  <RotateCcw size={13} />
                  {lbl('Actualizar', 'Refresh')}
                </button>
              </>
            )
          })()}
        </div>
      )}

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
              <div className="max-w-lg mx-auto grid grid-cols-3 items-center gap-2">
                {/* Izquierda: Par + SI */}
                <div>
                  <span className={`text-2xl font-bold ${PAR_COLOR[hole.par] ?? 'text-white'}`}>
                    Par {hole.par}
                  </span>
                  {hole.stroke_index && (
                    <button
                      onClick={() => setShowSiHelp(true)}
                      className="flex items-center gap-1 text-xs text-zinc-500 hover:text-emerald-400 transition-colors mt-0.5"
                      title={lbl('Qué significa SI', 'What does SI mean')}>
                      SI {hole.stroke_index}
                      <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-zinc-800 text-[9px] font-bold text-zinc-400">?</span>
                    </button>
                  )}
                </div>
                {/* Centro: HOYO X (protagonista) */}
                <div className="text-center">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-[0.2em] font-medium">
                    {lbl('Hoyo', 'Hole')}
                  </p>
                  <p className="text-4xl font-extrabold text-emerald-400 leading-none tabular-nums">
                    {hole.hole_number}
                  </p>
                </div>
                {/* Derecha: yardaje */}
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
                  ) : <div />
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

            {/* Player rows */}
            {(() => {
              type RosterEntry = { user_id: string; name: string; course_handicap: number | null; isMe: boolean }
              const roster: RosterEntry[] = [
                { user_id: myUserId, name: lbl('Yo', 'Me'), course_handicap: null, isMe: true },
                ...groupMates.map(m => ({ user_id: m.user_id, name: m.name, course_handicap: m.course_handicap, isMe: false })),
              ]
              const anyDirty = Object.values(rowInputs).some(v => v.dirty)
              return (
                <>
                  <div className="w-full space-y-3 mb-5">
                    {roster.map(p => {
                      const row = rowInputs[p.user_id] ?? { gross: hole?.par ?? 4, putts: null, dirty: false }
                      const saved = allScores[p.user_id]?.[currentHole]
                      const lbl_ = hole && row.gross > 0 ? scoreLabel(row.gross, hole.par) : null
                      return (
                        <div key={p.user_id}
                          className={`bg-zinc-900 border rounded-2xl px-4 py-3 transition-colors ${
                            row.dirty
                              ? 'border-emerald-500/50'
                              : saved ? 'border-zinc-700' : 'border-zinc-800'
                          }`}>
                          {/* Row header */}
                          <div className="flex items-baseline justify-between mb-2">
                            <div className="flex items-baseline gap-2 min-w-0">
                              <span className="font-semibold text-white truncate">{p.name}</span>
                              {p.course_handicap !== null && (
                                <span className="text-xs text-zinc-500">HCP {p.course_handicap}</span>
                              )}
                            </div>
                            {saved && !row.dirty && (
                              <span className="flex items-center gap-1 text-xs text-emerald-400">
                                <CheckCircle2 size={12} /> {lbl('Guardado', 'Saved')}
                              </span>
                            )}
                            {row.dirty && (
                              <span className="text-xs text-emerald-300">{lbl('Sin guardar', 'Unsaved')}</span>
                            )}
                          </div>
                          {/* ± + label */}
                          <div className="flex items-center justify-between gap-3">
                            <button
                              onClick={() => setRowInputs(prev => ({
                                ...prev,
                                [p.user_id]: { ...row, gross: Math.max(1, row.gross - 1), dirty: true },
                              }))}
                              className="w-12 h-12 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-white hover:bg-zinc-700 active:scale-95">
                              <Minus size={20} />
                            </button>
                            <div className="flex-1 text-center">
                              <span className="text-5xl font-bold text-white tabular-nums">{row.gross}</span>
                              {lbl_ && (
                                <p className={`text-xs mt-0.5 ${lbl_.cls}`}>{lbl_.text}</p>
                              )}
                            </div>
                            <button
                              onClick={() => setRowInputs(prev => ({
                                ...prev,
                                [p.user_id]: { ...row, gross: row.gross + 1, dirty: true },
                              }))}
                              className="w-12 h-12 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-white hover:bg-zinc-700 active:scale-95">
                              <Plus size={20} />
                            </button>
                          </div>
                          {/* Putts — solo para mí (estadística personal) */}
                          {p.isMe && (
                            <div className="flex items-center justify-between mt-2.5 pt-2.5 border-t border-zinc-800">
                              <span className="text-[10px] text-zinc-600 uppercase tracking-wider">{lbl('Putts', 'Putts')}</span>
                              <div className="flex items-center gap-1.5">
                                {[1, 2, 3, 4].map(n => (
                                  <button key={n}
                                    onClick={() => setRowInputs(prev => ({
                                      ...prev,
                                      [p.user_id]: { ...row, putts: row.putts === n ? null : n, dirty: true },
                                    }))}
                                    className={`w-8 h-8 rounded-full text-xs font-bold border transition-all ${
                                      row.putts === n
                                        ? 'bg-emerald-500 border-emerald-400 text-white'
                                        : 'bg-zinc-800 border-zinc-700 text-zinc-500'
                                    }`}>
                                    {n}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                  {myStartingHole && currentHole === myStartingHole && (
                    <p className="text-[10px] text-zinc-600 mb-3 text-center">
                      {lbl(`Tu grupo arranca en hoyo ${myStartingHole}`, `Your group starts at hole ${myStartingHole}`)}
                    </p>
                  )}
                  {/* Submit */}
                  <button onClick={submitScore} disabled={submitting}
                    className={`w-full flex items-center justify-center gap-2 disabled:opacity-60 text-white font-semibold py-4 rounded-2xl transition-colors text-base active:scale-95 ${
                      anyDirty
                        ? 'bg-emerald-500 hover:bg-emerald-400'
                        : 'bg-zinc-700 hover:bg-zinc-600'
                    }`}>
                    {submitting ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
                    {anyDirty
                      ? lbl('Guardar hoyo', 'Save hole')
                      : lbl('Siguiente hoyo', 'Next hole')}
                  </button>
                </>
              )
            })()}
          </div>

          {/* Stroke Index help modal */}
          {showSiHelp && hole && (
            <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
                 onClick={() => setShowSiHelp(false)}>
              <div onClick={e => e.stopPropagation()}
                   className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5 max-h-[85vh] overflow-y-auto">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-bold text-white text-lg">
                      {lbl('Stroke Index (SI)', 'Stroke Index (SI)')}
                    </h3>
                    <p className="text-xs text-zinc-500">
                      {lbl('Índice de dificultad del hoyo', 'Hole difficulty index')}
                    </p>
                  </div>
                  <button onClick={() => setShowSiHelp(false)} className="text-zinc-500 hover:text-white p-1">
                    <X size={18} />
                  </button>
                </div>

                <p className="text-sm text-zinc-300 leading-relaxed mb-3">
                  {lbl(
                    'Es el ranking de dificultad del hoyo dentro del campo, del 1 al 18:',
                    'It is the difficulty ranking of the hole within the course, from 1 to 18:'
                  )}
                </p>
                <ul className="text-sm text-zinc-400 space-y-1 mb-4 ml-2">
                  <li>• <span className="text-red-400 font-semibold">SI 1</span> = {lbl('hoyo más difícil', 'hardest hole')}</li>
                  <li>• <span className="text-emerald-400 font-semibold">SI 18</span> = {lbl('hoyo más fácil', 'easiest hole')}</li>
                </ul>

                <p className="text-sm text-zinc-300 leading-relaxed mb-3">
                  {lbl(
                    'El SI define en qué hoyos recibes "strokes de ventaja" según tu Course Handicap (CH).',
                    'SI defines in which holes you receive "stroke advantages" based on your Course Handicap (CH).'
                  )}
                </p>

                {/* Ejemplo con este hoyo */}
                <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-3 mb-4">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">
                    {lbl('En este hoyo', 'In this hole')}
                  </p>
                  <div className="flex items-center justify-between gap-3 mb-1">
                    <span className="text-zinc-400 text-sm">{lbl('Hoyo', 'Hole')}</span>
                    <span className="text-white font-semibold">{hole.hole_number} · Par {hole.par}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3 mb-1">
                    <span className="text-zinc-400 text-sm">SI</span>
                    <span className="text-white font-semibold">
                      {hole.stroke_index} {hole.stroke_index && hole.stroke_index <= 6
                        ? lbl('(difícil)', '(hard)')
                        : hole.stroke_index && hole.stroke_index >= 13
                        ? lbl('(fácil)', '(easy)')
                        : lbl('(medio)', '(medium)')}
                    </span>
                  </div>
                  {myCourseHandicap !== null && (
                    <>
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <span className="text-zinc-400 text-sm">{lbl('Tu CH', 'Your CH')}</span>
                        <span className="text-white font-semibold">{myCourseHandicap}</span>
                      </div>
                      <div className="border-t border-zinc-800 pt-2 mt-2">
                        {(() => {
                          const si = hole.stroke_index ?? 18
                          const ch = myCourseHandicap
                          const baseStrokes = Math.floor(ch / 18)
                          const extra = (ch % 18) >= si ? 1 : 0
                          const total = baseStrokes + extra
                          return (
                            <>
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-zinc-300 font-medium">
                                  {lbl('Recibes', 'You receive')}
                                </span>
                                <span className={`text-lg font-bold ${
                                  total > 0 ? 'text-emerald-400' : 'text-zinc-500'
                                }`}>
                                  {total === 0
                                    ? lbl('0 strokes', '0 strokes')
                                    : total === 1
                                    ? lbl('1 stroke', '1 stroke')
                                    : `${total} ${lbl('strokes', 'strokes')}`}
                                </span>
                              </div>
                              <p className="text-[11px] text-zinc-500 mt-1">
                                {total === 0
                                  ? lbl(
                                      `Tu CH (${ch}) < SI (${si}), juegas a la par.`,
                                      `Your CH (${ch}) < SI (${si}), play at par.`
                                    )
                                  : lbl(
                                      `Tu CH (${ch}) ≥ SI (${si}), te corresponde ventaja. Tu Net Par = ${hole.par + total}.`,
                                      `Your CH (${ch}) ≥ SI (${si}), you get the advantage. Your Net Par = ${hole.par + total}.`
                                    )}
                              </p>
                            </>
                          )
                        })()}
                      </div>
                    </>
                  )}
                </div>

                <p className="text-[11px] text-zinc-500 leading-relaxed mb-4">
                  {lbl(
                    'Regla WHS: recibes 1 stroke en los hoyos con SI ≤ tu CH. Si tu CH supera 18, recibes 1 stroke en todos y otro extra en los SI ≤ (CH − 18).',
                    'WHS rule: you receive 1 stroke in holes with SI ≤ your CH. If your CH exceeds 18, you get 1 stroke in all of them plus an extra one in SI ≤ (CH − 18).'
                  )}
                </p>

                <button onClick={() => setShowSiHelp(false)}
                  className="w-full py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-semibold">
                  {lbl('Entendido', 'Got it')}
                </button>
              </div>
            </div>
          )}

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
                  <button onClick={() => handleFinish(false)} disabled={finishing}
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
