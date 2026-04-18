'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, Play, MapPin, Calendar, Loader2, CheckCircle2, Copy, Check, QrCode, DollarSign, ChevronDown, ChevronUp, Save, Edit2, X, Info, Trash2, Users, Shuffle, Radio, Eye, EyeOff, Send } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Round {
  id: string
  name: string | null
  course_id: string | null
  course_name?: string
  game_format: string
  team_size: number
  status: string
  holes_to_play: number
  scheduled_at: string
  started_at: string | null
  finished_at: string | null
  is_handicap_valid: boolean
  invite_code: string | null
  created_by: string | null
  notes: string | null
}

interface Course { id: string; name: string; city: string | null }

const FORMATS = [
  { value: 'stroke',             labelEs: 'Stroke Play',           labelEn: 'Stroke Play' },
  { value: 'stableford',         labelEs: 'Stableford',            labelEn: 'Stableford' },
  { value: 'stableford_modified',labelEs: 'Stableford Modificado', labelEn: 'Mod. Stableford' },
  { value: 'match',              labelEs: 'Match Play',            labelEn: 'Match Play' },
  { value: 'skins',              labelEs: 'Skines',                labelEn: 'Skins' },
  { value: 'florida',            labelEs: 'Florida',               labelEn: 'Florida' },
]

interface Player {
  user_id: string
  first_name: string
  last_name: string
  username: string
  handicap_index: number | null
  course_handicap: number | null
  tee_color: string | null
  in_bet: boolean
  status: string
}

interface BoardEntry {
  user_id: string
  holes_played: number
  total_gross: number
  scores: { hole: number; gross: number; net: number }[]
}

interface Hole {
  hole_number: number
  par: number
  stroke_index: number | null
  distance_yards_blue: number | null
  distance_yards_white: number | null
}

interface BetConfig {
  entry_fee: number
  nassau_enabled: boolean
  nassau_front9: number
  nassau_back9: number
  nassau_total: number
  per_hole_bet: number
  birdie_prize: number
  eagle_prize: number
  hole_in_one_prize: number
  three_putt_penalty: number
  oyes_enabled: boolean
  oyes_prize: number
  oyes_accumulates: boolean
  skins_enabled: boolean
  skins_value: number
  skins_use_net: boolean
}

interface SkinHole {
  hole: number
  status: 'won' | 'tie' | 'pending' | 'no_score'
  winner_id: string | null
  pot: number
  carry: number
  score?: number
  tied_players?: string[]
}

interface TeamPlayer {
  player_id: string
  user_id: string
  name: string
  username: string
  course_handicap: number | null
  handicap_index: number | null
  team_number: number | null
}
interface TeamData {
  team_number: number
  name: string
  color: string
  players: TeamPlayer[]
  total_handicap: number
}
interface TeamsResponse {
  teams: TeamData[]
  unassigned: TeamPlayer[]
  has_teams: boolean
  teams_published: boolean
}

const TEAM_UI: Record<string, { bg: string; border: string; text: string; dot: string; btn: string }> = {
  emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400', btn: 'bg-emerald-500 hover:bg-emerald-400' },
  blue:    { bg: 'bg-blue-500/10',    border: 'border-blue-500/30',    text: 'text-blue-400',    dot: 'bg-blue-400',    btn: 'bg-blue-500 hover:bg-blue-400' },
  amber:   { bg: 'bg-amber-500/10',   border: 'border-amber-500/30',   text: 'text-amber-400',   dot: 'bg-amber-400',   btn: 'bg-amber-500 hover:bg-amber-400' },
  red:     { bg: 'bg-red-500/10',     border: 'border-red-500/30',     text: 'text-red-400',     dot: 'bg-red-400',     btn: 'bg-red-500 hover:bg-red-400' },
}

function scoreCellCls(gross: number, par: number) {
  const d = gross - par
  if (gross === 1) return 'bg-yellow-400 text-zinc-900 font-bold rounded-full'
  if (d <= -2) return 'bg-yellow-400/20 text-yellow-300 font-bold rounded-full'
  if (d === -1) return 'bg-emerald-500/30 text-emerald-300 font-semibold rounded-full'
  if (d === 0) return 'text-zinc-200'
  if (d === 1) return 'bg-orange-500/20 text-orange-300 rounded'
  return 'bg-red-600/30 text-red-300 font-bold rounded'
}

function RoundScorecard({
  board, players, holes, holesTotal, status, lbl
}: {
  board: BoardEntry[]
  players: Player[]
  holes: Hole[]
  holesTotal: number
  status: string
  lbl: (es: string, en: string) => string
}) {
  const [activeIdx, setActiveIdx] = useState(0)
  const entry = board[activeIdx]
  if (!entry) return null

  const activeHoles = holes.filter(h => h.hole_number <= holesTotal)
  const front = activeHoles.filter(h => h.hole_number <= 9)
  const back = activeHoles.filter(h => h.hole_number > 9)
  const sections = holesTotal === 18
    ? [{ label: lbl('Salida', 'Out'), hs: front }, { label: lbl('Vuelta', 'In'), hs: back }]
    : [{ label: lbl('Total', 'Total'), hs: activeHoles }]

  const scoreMap: Record<number, { gross: number; net: number }> = {}
  entry.scores.forEach(s => { scoreMap[s.hole] = { gross: s.gross, net: s.net } })

  const sumPar = (hs: Hole[]) => hs.reduce((s, h) => s + h.par, 0)
  const sumGross = (hs: Hole[]) => hs.reduce((s, h) => scoreMap[h.hole_number] ? s + scoreMap[h.hole_number].gross : s, 0)
  const sumNet = (hs: Hole[]) => hs.reduce((s, h) => scoreMap[h.hole_number] ? s + scoreMap[h.hole_number].net : s, 0)
  const played = (hs: Hole[]) => hs.filter(h => scoreMap[h.hole_number]).length

  const totalPar = sumPar(activeHoles)
  const totalGross = sumGross(activeHoles)
  const rel = totalGross - totalPar

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-5 pb-3 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="font-semibold text-white flex items-center gap-2">
          {status === 'finished'
            ? <><CheckCircle2 size={15} className="text-emerald-400" />{lbl('Tarjeta final', 'Final scorecard')}</>
            : <>{lbl('Tarjeta en curso', 'Live scorecard')}</>}
        </h2>
        {totalGross > 0 && (
          <span className={`text-sm font-bold ${rel < 0 ? 'text-emerald-400' : rel > 0 ? 'text-red-400' : 'text-zinc-300'}`}>
            {rel === 0 ? 'E' : rel > 0 ? `+${rel}` : rel} ({totalGross})
          </span>
        )}
      </div>

      {/* Player tabs */}
      {board.length > 1 && (
        <div className="flex gap-1 px-4 py-2 overflow-x-auto border-b border-zinc-800">
          {board.map((b, i) => {
            const p = players.find(pl => pl.user_id === b.user_id)
            return (
              <button key={b.user_id} onClick={() => setActiveIdx(i)}
                className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  activeIdx === i ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
                }`}>
                {p ? `${p.first_name} ${p.last_name.charAt(0)}.` : `J${i+1}`}
              </button>
            )
          })}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <div className="min-w-[380px] px-1 py-2">
          {sections.map(({ label, hs }) => (
            <div key={label} className="mb-2">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="text-left text-xs text-zinc-600 py-1.5 pl-3 w-8">#</th>
                    <th className="text-center text-xs text-zinc-600 py-1.5 w-8">Par</th>
                    <th className="text-center text-xs text-zinc-600 py-1.5 w-8">SI</th>
                    <th className="text-center text-xs text-zinc-600 py-1.5">Yds</th>
                    <th className="text-center text-xs text-emerald-600 py-1.5">{lbl('Gol.', 'Gross')}</th>
                    <th className="text-center text-xs text-blue-600 py-1.5">{lbl('Neto', 'Net')}</th>
                    <th className="text-center text-xs text-zinc-600 py-1.5 w-8">+/−</th>
                  </tr>
                </thead>
                <tbody>
                  {hs.map(h => {
                    const sc = scoreMap[h.hole_number]
                    const diff = sc ? sc.gross - h.par : null
                    return (
                      <tr key={h.hole_number} className="border-t border-zinc-800/50">
                        <td className="py-2 pl-3">
                          <span className="w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 text-xs font-bold text-zinc-400 flex items-center justify-center">
                            {h.hole_number}
                          </span>
                        </td>
                        <td className="text-center text-sm py-2 text-zinc-400">{h.par}</td>
                        <td className="text-center text-xs py-2 text-zinc-600">{h.stroke_index ?? '—'}</td>
                        <td className="text-center text-xs py-2 text-zinc-500">
                          {h.distance_yards_blue ?? h.distance_yards_white ?? '—'}
                        </td>
                        <td className="text-center py-2">
                          {sc ? (
                            <span className={`inline-flex items-center justify-center w-7 h-7 text-sm font-bold ${scoreCellCls(sc.gross, h.par)}`}>
                              {sc.gross}
                            </span>
                          ) : <span className="text-zinc-700 text-sm">—</span>}
                        </td>
                        <td className="text-center text-sm py-2 text-blue-400">
                          {sc ? sc.net : <span className="text-zinc-700">—</span>}
                        </td>
                        <td className={`text-center text-xs py-2 font-medium ${
                          diff === null ? 'text-zinc-700' :
                          diff < 0 ? 'text-emerald-400' :
                          diff > 0 ? 'text-red-400' : 'text-zinc-500'
                        }`}>
                          {diff === null ? '—' : diff === 0 ? 'E' : diff > 0 ? `+${diff}` : diff}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-zinc-700">
                    <td colSpan={1} className="py-2 pl-3">
                      <span className="text-xs font-bold text-zinc-500">{label}</span>
                    </td>
                    <td className="text-center text-sm font-bold text-zinc-300 py-2">{sumPar(hs)}</td>
                    <td /><td />
                    <td className="text-center text-sm font-bold text-white py-2">
                      {played(hs) > 0 ? sumGross(hs) : '—'}
                    </td>
                    <td className="text-center text-sm font-bold text-blue-300 py-2">
                      {played(hs) > 0 ? sumNet(hs) : '—'}
                    </td>
                    <td className={`text-center text-xs font-bold py-2 ${
                      played(hs) === 0 ? 'text-zinc-700' :
                      sumGross(hs) - sumPar(hs) < 0 ? 'text-emerald-400' :
                      sumGross(hs) - sumPar(hs) > 0 ? 'text-red-400' : 'text-zinc-400'
                    }`}>
                      {played(hs) === 0 ? '—' :
                       sumGross(hs) - sumPar(hs) === 0 ? 'E' :
                       sumGross(hs) - sumPar(hs) > 0 ? `+${sumGross(hs)-sumPar(hs)}` : sumGross(hs)-sumPar(hs)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          ))}

          {/* Grand total */}
          {holesTotal === 18 && (
            <div className="mx-3 mb-3 bg-zinc-800 rounded-xl px-4 py-3 flex items-center justify-between">
              <span className="text-xs font-bold text-zinc-400 uppercase tracking-wide">TOTAL</span>
              <div className="flex items-center gap-5">
                <div className="text-center">
                  <p className="text-xs text-zinc-600">Par</p>
                  <p className="text-sm font-bold text-zinc-300">{totalPar}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-zinc-600">{lbl('Bruto', 'Gross')}</p>
                  <p className="text-2xl font-bold text-white">{totalGross > 0 ? totalGross : '—'}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-zinc-600">+/−</p>
                  <p className={`text-xl font-bold ${rel < 0 ? 'text-emerald-400' : rel > 0 ? 'text-red-400' : 'text-zinc-300'}`}>
                    {totalGross === 0 ? '—' : rel === 0 ? 'E' : rel > 0 ? `+${rel}` : rel}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const TEE_CONFIG = {
  black: { label: { es: 'Negra', en: 'Black' }, dot: 'bg-zinc-800 border-2 border-zinc-500', text: 'text-zinc-300' },
  blue:  { label: { es: 'Azul',  en: 'Blue'  }, dot: 'bg-blue-600',  text: 'text-blue-300' },
  white: { label: { es: 'Blanca',en: 'White' }, dot: 'bg-white border border-zinc-400', text: 'text-zinc-200' },
  red:   { label: { es: 'Roja',  en: 'Red'   }, dot: 'bg-red-600',   text: 'text-red-300' },
} as const
type TeeColor = keyof typeof TEE_CONFIG

const FORMAT_LABELS: Record<string, { es: string; en: string }> = {
  stroke:              { es: 'Stroke Play',           en: 'Stroke Play' },
  stableford:          { es: 'Stableford',            en: 'Stableford' },
  stableford_modified: { es: 'Stableford Modificado', en: 'Modified Stableford' },
  match:               { es: 'Match Play',            en: 'Match Play' },
  skins:               { es: 'Skines',                en: 'Skins' },
  florida:             { es: 'Florida',               en: 'Florida' },
}

const STATUS_COLOR: Record<string, string> = {
  scheduled: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  active: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  finished: 'text-zinc-400 bg-zinc-800 border-zinc-700',
}

// ─── Format Info ──────────────────────────────────────────────────────────────

const FORMAT_INFO: Record<string, {
  titleEs: string; titleEn: string
  descEs: string; descEn: string
  rulesEs: { label: string; value: string }[]
  rulesEn: { label: string; value: string }[]
  exampleEs: { hoyo?: string; hole?: never; scores: { desc: string; result: string; highlight?: boolean }[] }
  exampleEn: { scores: { desc: string; result: string; highlight?: boolean }[] }
}> = {
  stroke: {
    titleEs: 'Stroke Play (Medal)',
    titleEn: 'Stroke Play (Medal)',
    descEs: 'Se cuentan todos los golpes de la ronda. Gana quien menos golpes acumule al final de los 18 (o 9) hoyos. Es el formato oficial WHS para hándicap.',
    descEn: 'Every stroke counts throughout the round. The player with the lowest total score wins. This is the official WHS format used for handicap calculations.',
    rulesEs: [
      { label: 'Objetivo', value: 'Menos golpes totales' },
      { label: 'Score bruto', value: 'Golpes reales' },
      { label: 'Score neto', value: 'Bruto − Hándicap del campo' },
      { label: 'Desempate', value: 'Sudden death hoyo a hoyo' },
    ],
    rulesEn: [
      { label: 'Objective', value: 'Fewest total strokes' },
      { label: 'Gross score', value: 'Actual strokes' },
      { label: 'Net score', value: 'Gross − Course handicap' },
      { label: 'Tiebreak', value: 'Sudden death play-off' },
    ],
    exampleEs: {
      hoyo: 'Ejemplo — ronda completa (Par 72)',
      scores: [
        { desc: 'Jugador A — 85 golpes brutos, HCP 10', result: '85 − 10 = 75 neto' },
        { desc: 'Jugador B — 80 golpes brutos, HCP 5',  result: '80 − 5 = 75 neto' },
        { desc: 'Jugador C — 78 golpes brutos, HCP 2',  result: '78 − 2 = 76 neto' },
        { desc: 'Ganador neto: A y B empatan en 75', result: 'Desempate en hoyo 1', highlight: true },
      ],
    },
    exampleEn: {
      scores: [
        { desc: 'Player A — 85 gross, HCP 10', result: '85 − 10 = 75 net' },
        { desc: 'Player B — 80 gross, HCP 5',  result: '80 − 5 = 75 net' },
        { desc: 'Player C — 78 gross, HCP 2',  result: '78 − 2 = 76 net' },
        { desc: 'Net winner: A & B tie at 75', result: 'Play-off from hole 1', highlight: true },
      ],
    },
  },
  stableford: {
    titleEs: 'Stableford',
    titleEn: 'Stableford',
    descEs: 'Cada hoyo da puntos según cuántos golpes arriba o abajo del par lo terminas (considerando tu hándicap). Gana quien más puntos acumule. Los hoyos malos "no penan" porque el mínimo es 0.',
    descEn: 'Points are awarded on each hole based on strokes against par (adjusted by handicap). Most points wins. Bad holes only score 0 — they never drag you below zero.',
    rulesEs: [
      { label: 'Albatros (−3)', value: '5 pts' },
      { label: 'Águila (−2)',   value: '4 pts' },
      { label: 'Birdie (−1)',   value: '3 pts' },
      { label: 'Par (0)',       value: '2 pts' },
      { label: 'Bogey (+1)',    value: '1 pt'  },
      { label: 'Doble bogey +', value: '0 pts' },
    ],
    rulesEn: [
      { label: 'Albatross (−3)', value: '5 pts' },
      { label: 'Eagle (−2)',     value: '4 pts' },
      { label: 'Birdie (−1)',    value: '3 pts' },
      { label: 'Par (0)',        value: '2 pts' },
      { label: 'Bogey (+1)',     value: '1 pt'  },
      { label: 'Double bogey +', value: '0 pts' },
    ],
    exampleEs: {
      hoyo: 'Ejemplo — Hoyo 7, Par 4, SI 5, HCP 18 → recibe 1 golpe → par ajustado = 5',
      scores: [
        { desc: 'Hiciste 4 golpes (birdie ajustado −1)', result: '3 pts', highlight: true },
        { desc: 'Hiciste 5 golpes (par ajustado)',        result: '2 pts' },
        { desc: 'Hiciste 6 golpes (bogey ajustado)',      result: '1 pt'  },
        { desc: 'Hiciste 8 golpes (triple bogey)',        result: '0 pts' },
      ],
    },
    exampleEn: {
      scores: [
        { desc: '4 strokes → adjusted birdie (−1)', result: '3 pts', highlight: true },
        { desc: '5 strokes → adjusted par',          result: '2 pts' },
        { desc: '6 strokes → adjusted bogey',        result: '1 pt'  },
        { desc: '8 strokes → triple bogey',          result: '0 pts' },
      ],
    },
  },
  stableford_modified: {
    titleEs: 'Stableford Modificado',
    titleEn: 'Modified Stableford',
    descEs: 'Variante del Stableford con una tabla de puntos que penaliza más los hoyos malos y premia más los extraordinarios. Muy usado en competencias profesionales (como el Skins Game de la PGA).',
    descEn: 'A Stableford variant that rewards great holes more and penalizes bad ones more. Used in high-stakes competitions like the PGA\'s International tournament.',
    rulesEs: [
      { label: 'Albatros (−3)', value: '+8 pts' },
      { label: 'Águila (−2)',   value: '+5 pts' },
      { label: 'Birdie (−1)',   value: '+2 pts' },
      { label: 'Par (0)',       value: '0 pts'  },
      { label: 'Bogey (+1)',    value: '−1 pt'  },
      { label: 'Doble bogey +', value: '−3 pts' },
    ],
    rulesEn: [
      { label: 'Albatross (−3)', value: '+8 pts' },
      { label: 'Eagle (−2)',     value: '+5 pts' },
      { label: 'Birdie (−1)',    value: '+2 pts' },
      { label: 'Par (0)',        value: '0 pts'  },
      { label: 'Bogey (+1)',     value: '−1 pt'  },
      { label: 'Double bogey +', value: '−3 pts' },
    ],
    exampleEs: {
      hoyo: 'Ejemplo — 4 hoyos jugados',
      scores: [
        { desc: 'Hoyo 1: birdie',        result: '+2' },
        { desc: 'Hoyo 2: bogey',         result: '−1' },
        { desc: 'Hoyo 3: par',           result: '0'  },
        { desc: 'Hoyo 4: doble bogey',   result: '−3' },
        { desc: 'Total acumulado',        result: '−2 pts', highlight: true },
      ],
    },
    exampleEn: {
      scores: [
        { desc: 'Hole 1: birdie',       result: '+2' },
        { desc: 'Hole 2: bogey',        result: '−1' },
        { desc: 'Hole 3: par',          result: '0'  },
        { desc: 'Hole 4: double bogey', result: '−3' },
        { desc: 'Running total',        result: '−2 pts', highlight: true },
      ],
    },
  },
  match: {
    titleEs: 'Match Play',
    titleEn: 'Match Play',
    descEs: 'Se compite hoyo a hoyo, no por total de golpes. Quien hace menos golpes en un hoyo gana ese hoyo. El resultado final se expresa como diferencia de hoyos. Se termina cuando un jugador ya no puede alcanzar al otro.',
    descEn: 'Competition is hole-by-hole, not total strokes. The player with fewer strokes wins the hole. The match ends when one player can no longer mathematically catch up.',
    rulesEs: [
      { label: 'Ganar hoyo',    value: '+1 hoyo a favor' },
      { label: 'Empatar hoyo',  value: 'Hoyo "halved" — sin cambio' },
      { label: 'Perder hoyo',   value: '−1 hoyo' },
      { label: 'Resultado',     value: '"3&2" = ganas 3 hoyos con 2 por jugar' },
      { label: 'Abandono',      value: 'Puedes conceder un golpe o el hoyo' },
    ],
    rulesEn: [
      { label: 'Win hole',     value: '+1 hole up' },
      { label: 'Halve hole',   value: 'No change' },
      { label: 'Lose hole',    value: '−1 hole' },
      { label: 'Result',       value: '"3&2" = 3 holes up with 2 to play' },
      { label: 'Concede',      value: 'You may concede a putt or hole at any time' },
    ],
    exampleEs: {
      hoyo: 'Ejemplo — primeros 5 hoyos (A vs B)',
      scores: [
        { desc: 'Hoyo 1: A hace 4, B hace 5 → A gana',   result: 'A 1UP' },
        { desc: 'Hoyo 2: A hace 5, B hace 5 → empate',   result: 'A 1UP' },
        { desc: 'Hoyo 3: A hace 6, B hace 4 → B gana',   result: 'AS' },
        { desc: 'Hoyo 4: A hace 3, B hace 4 → A gana',   result: 'A 1UP' },
        { desc: 'Hoyo 5: A hace 5, B hace 3 → B gana',   result: 'AS', highlight: true },
      ],
    },
    exampleEn: {
      scores: [
        { desc: 'Hole 1: A scores 4, B scores 5 → A wins',   result: 'A 1UP' },
        { desc: 'Hole 2: A scores 5, B scores 5 → halved',   result: 'A 1UP' },
        { desc: 'Hole 3: A scores 6, B scores 4 → B wins',   result: 'AS' },
        { desc: 'Hole 4: A scores 3, B scores 4 → A wins',   result: 'A 1UP' },
        { desc: 'Hole 5: A scores 5, B scores 3 → B wins',   result: 'AS', highlight: true },
      ],
    },
  },
  skins: {
    titleEs: 'Skines (Skins)',
    titleEn: 'Skins',
    descEs: 'Cada hoyo vale una "piel" (una cantidad de dinero o puntos). Gana la piel el jugador que hace el menor score en ese hoyo solo, sin empate. Si hay empate, la piel se arrastra (carry-over) al siguiente hoyo, acumulando el valor.',
    descEn: 'Each hole is worth a "skin" (a set amount). The player with the sole lowest score on a hole wins the skin. If there is a tie, the skin carries over to the next hole, increasing its value.',
    rulesEs: [
      { label: 'Ganador solo',     value: 'Se lleva la piel del hoyo' },
      { label: 'Empate',           value: 'Piel acumulada al hoyo siguiente' },
      { label: 'Carry-over',       value: 'El bote crece con cada empate' },
      { label: 'Piel no ganada',   value: 'Queda en el bote final' },
      { label: 'Neto vs bruto',    value: 'Configurable — score neto o bruto' },
    ],
    rulesEn: [
      { label: 'Sole winner',      value: 'Takes the skin' },
      { label: 'Tie',              value: 'Skin carries to next hole' },
      { label: 'Carry-over',       value: 'Pot grows with each tie' },
      { label: 'Unclaimed skin',   value: 'Stays in pot — returned or kept' },
      { label: 'Net vs gross',     value: 'Configurable per round' },
    ],
    exampleEs: {
      hoyo: 'Ejemplo — 3 jugadores, $100 por piel',
      scores: [
        { desc: 'Hoyo 1 — A:4, B:4, C:5 → Empate A-B', result: 'Piel acumulada ($100)' },
        { desc: 'Hoyo 2 — A:5, B:4, C:4 → Empate B-C', result: 'Piel acumulada ($200)' },
        { desc: 'Hoyo 3 — A:3, B:4, C:5 → A gana solo', result: 'A gana $300', highlight: true },
        { desc: 'Hoyo 4 — A:4, B:4, C:4 → Triple empate', result: 'Piel acumulada ($100)' },
      ],
    },
    exampleEn: {
      scores: [
        { desc: 'Hole 1 — A:4, B:4, C:5 → A-B tie',     result: 'Carry-over ($100)' },
        { desc: 'Hole 2 — A:5, B:4, C:4 → B-C tie',     result: 'Carry-over ($200)' },
        { desc: 'Hole 3 — A:3, B:4, C:5 → A sole winner', result: 'A wins $300', highlight: true },
        { desc: 'Hole 4 — A:4, B:4, C:4 → three-way tie', result: 'Carry-over ($100)' },
      ],
    },
  },
  florida: {
    titleEs: 'Florida (Best Ball por equipos)',
    titleEn: 'Florida (Team Best Ball)',
    descEs: 'Formato por equipos de 2, 3 o 4 jugadores. Cada jugador juega su propia pelota durante toda la ronda. El score del equipo en cada hoyo es el MEJOR score neto de los integrantes. El equipo con menos golpes netos totales gana.',
    descEn: 'Team format with 2–4 players. Everyone plays their own ball. The team\'s score on each hole is the BEST net score among teammates. Team with lowest total net wins.',
    rulesEs: [
      { label: 'Tamaño de equipo',   value: '2, 3 ó 4 jugadores' },
      { label: 'Pelota por jugador',  value: 'Cada uno juega la suya' },
      { label: 'Score por hoyo',      value: 'Mejor score neto del equipo' },
      { label: 'Score neto',          value: 'Bruto − Hándicap del campo' },
      { label: 'Ganador',             value: 'Equipo con menor total neto' },
    ],
    rulesEn: [
      { label: 'Team size',          value: '2, 3 or 4 players' },
      { label: 'Ball per player',    value: 'Each plays their own' },
      { label: 'Hole score',         value: 'Best net score in team' },
      { label: 'Net score',          value: 'Gross − Course handicap' },
      { label: 'Winner',             value: 'Team with lowest total net' },
    ],
    exampleEs: {
      hoyo: 'Ejemplo — Equipo A (2 jugadores), Hoyo par 4',
      scores: [
        { desc: 'Jugador 1: bruto 5, HCP 12 → 1 golpe extra → neto 4', result: '4 neto' },
        { desc: 'Jugador 2: bruto 6, HCP 24 → 1 golpe extra → neto 5', result: '5 neto' },
        { desc: 'Score del equipo en el hoyo', result: '4 (mejor neto)', highlight: true },
        { desc: 'Equipo B anota 5 en el mismo hoyo', result: 'Equipo A gana el hoyo', highlight: true },
      ],
    },
    exampleEn: {
      scores: [
        { desc: 'Player 1: 5 gross, HCP 12 → 1 stroke → 4 net', result: '4 net' },
        { desc: 'Player 2: 6 gross, HCP 24 → 1 stroke → 5 net', result: '5 net' },
        { desc: 'Team score on the hole', result: '4 (best net)', highlight: true },
        { desc: 'Team B scores 5 on same hole', result: 'Team A wins hole', highlight: true },
      ],
    },
  },
}

function FormatInfoModal({ format, locale, onClose }: { format: string; locale: string; onClose: () => void }) {
  const info = FORMAT_INFO[format]
  if (!info) return null
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const title   = lbl(info.titleEs, info.titleEn)
  const desc    = lbl(info.descEs, info.descEn)
  const rules   = locale === 'es' ? info.rulesEs : info.rulesEn
  const example = locale === 'es' ? info.exampleEs : info.exampleEn

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-2xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
              <Info size={13} className="text-emerald-400" />
            </div>
            <span className="font-bold text-white text-sm">{title}</span>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Description */}
          <p className="text-sm text-zinc-400 leading-relaxed">{desc}</p>

          {/* Rules table */}
          <div className="bg-zinc-800 rounded-xl overflow-hidden">
            <div className="px-3 py-2 border-b border-zinc-700">
              <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                {lbl('Tabla de puntos / reglas', 'Scoring / rules')}
              </span>
            </div>
            <div className="divide-y divide-zinc-700/50">
              {rules.map((r, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-2">
                  <span className="text-xs text-zinc-400">{r.label}</span>
                  <span className="text-xs font-semibold text-white">{r.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Example */}
          <div>
            {info.exampleEs.hoyo && (
              <p className="text-xs text-zinc-500 mb-2">{locale === 'es' ? info.exampleEs.hoyo : lbl(info.exampleEs.hoyo, info.exampleEs.hoyo)}</p>
            )}
            <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl overflow-hidden">
              <div className="px-3 py-2 border-b border-zinc-700/50">
                <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                  {lbl('Ejemplo práctico', 'Practical example')}
                </span>
              </div>
              <div className="divide-y divide-zinc-700/30">
                {example.scores.map((s, i) => (
                  <div key={i} className={`flex items-center justify-between px-3 py-2.5 ${s.highlight ? 'bg-emerald-500/10' : ''}`}>
                    <span className="text-xs text-zinc-400 flex-1 pr-3">{s.desc}</span>
                    <span className={`text-xs font-bold flex-shrink-0 ${s.highlight ? 'text-emerald-400' : 'text-zinc-300'}`}>{s.result}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="px-5 pb-5">
          <button onClick={onClose}
            className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium py-2.5 rounded-xl text-sm transition-colors">
            {lbl('Entendido', 'Got it')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function RoundDetailPage() {
  const locale = useLocale()
  const router = useRouter()
  const { id } = useParams<{ id: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [round, setRound] = useState<Round | null>(null)
  const [players, setPlayers] = useState<Player[]>([])
  const [board, setBoard] = useState<BoardEntry[]>([])
  const [holes, setHoles] = useState<Hole[]>([])
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [myUserId, setMyUserId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [showQr, setShowQr] = useState(false)
  const [savingTee, setSavingTee] = useState(false)
  const [betCfg, setBetCfg] = useState<BetConfig | null>(null)
  const [showBets, setShowBets] = useState(false)
  const [betForm, setBetForm] = useState<BetConfig>({
    entry_fee: 0, nassau_enabled: false, nassau_front9: 0, nassau_back9: 0, nassau_total: 0,
    per_hole_bet: 0, birdie_prize: 0, eagle_prize: 0, hole_in_one_prize: 0,
    three_putt_penalty: 0, oyes_enabled: false, oyes_prize: 0, oyes_accumulates: true,
    skins_enabled: false, skins_value: 0, skins_use_net: false,
  })
  const [savingBet, setSavingBet] = useState(false)
  const [editing, setEditing] = useState(false)
  const [courses, setCourses] = useState<Course[]>([])
  const [editForm, setEditForm] = useState({ name: '', course_id: '', game_format: '', team_size: 2, holes_to_play: 18, scheduled_at: '', is_handicap_valid: true, notes: '' })
  const [savingEdit, setSavingEdit] = useState(false)
  const [skins, setSkins] = useState<SkinHole[]>([])
  const [skinstotals, setSkinsTotal] = useState<Record<string, number>>({})
  const [skinsPotRemaining, setSkinsPotRemaining] = useState(0)
  const [showSkins, setShowSkins] = useState(false)
  const [showFormatInfo, setShowFormatInfo] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [teamsData, setTeamsData] = useState<TeamsResponse | null>(null)
  const [showTeams, setShowTeams] = useState(false)
  const [numTeams, setNumTeams] = useState(2)
  const [generatingTeams, setGeneratingTeams] = useState(false)
  const [movingPlayer, setMovingPlayer] = useState<string | null>(null)
  const [teamsError, setTeamsError] = useState('')
  const [finishing, setFinishing] = useState(false)

  const load = async () => {
    const [roundRes, playersRes, meRes] = await Promise.all([
      api.get(`/rounds/${id}`),
      api.get(`/rounds/${id}/players`),
      api.get('/users/me'),
    ])
    const roundData = roundRes.data
    setRound(roundData)
    setPlayers(playersRes.data)
    setMyUserId(meRes.data.id)
    // Load bet config
    const betRes = await api.get(`/rounds/${id}/bet-config`).catch(() => ({ data: null }))
    if (betRes.data) {
      setBetCfg(betRes.data)
      setBetForm(betRes.data)
    }
    if (betRes.data?.skins_enabled && roundData.status !== 'scheduled') {
      const skinsRes = await api.get(`/rounds/${id}/skins`).catch(() => ({ data: null }))
      if (skinsRes.data) {
        setSkins(skinsRes.data.skins)
        setSkinsTotal(skinsRes.data.totals)
        setSkinsPotRemaining(skinsRes.data.pot_remaining)
      }
    }
    if (roundData.status !== 'scheduled') {
      const [boardRes, courseRes] = await Promise.all([
        api.get(`/rounds/${id}/scoreboard`),
        roundData.course_id ? api.get(`/courses/${roundData.course_id}`) : Promise.resolve(null),
      ])
      setBoard(boardRes.data)
      if (courseRes) setHoles(courseRes.data.holes ?? [])
    }
    // Load teams
    const teamsRes = await api.get(`/rounds/${id}/teams`).catch(() => ({ data: null }))
    if (teamsRes.data) {
      setTeamsData(teamsRes.data)
      if (teamsRes.data.has_teams) setShowTeams(true)
    }
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load().finally(() => setLoading(false))
  }, [id])

  // Auto-refresh every 15s while round is scheduled so guests see when host starts it
  useEffect(() => {
    if (round?.status !== 'scheduled') return
    const interval = setInterval(() => load(), 15_000)
    return () => clearInterval(interval)
  }, [round?.status, id])

  const openEdit = async () => {
    if (courses.length === 0) {
      const r = await api.get('/courses')
      setCourses(r.data)
    }
    if (round) {
      setEditForm({
        name: round.name ?? '',
        course_id: round.course_id ?? '',
        game_format: round.game_format,
        team_size: round.team_size ?? 2,
        holes_to_play: round.holes_to_play,
        scheduled_at: round.scheduled_at.slice(0, 16),
        is_handicap_valid: round.is_handicap_valid,
        notes: round.notes ?? '',
      })
    }
    setEditing(true)
  }

  const saveEdit = async () => {
    setSavingEdit(true)
    try {
      const res = await api.patch(`/rounds/${id}`, {
        name: editForm.name || null,
        course_id: editForm.course_id || null,
        game_format: editForm.game_format,
        team_size: editForm.game_format === 'florida' ? editForm.team_size : 1,
        holes_to_play: editForm.holes_to_play,
        scheduled_at: new Date(editForm.scheduled_at).toISOString(),
        is_handicap_valid: editForm.is_handicap_valid,
        notes: editForm.notes || null,
      })
      setRound(prev => prev ? { ...prev, ...res.data } : prev)
      setEditing(false)
    } finally { setSavingEdit(false) }
  }

  const handleStart = async () => {
    setStarting(true)
    try {
      await api.post(`/rounds/${id}/start`)
      router.push(`/${locale}/rounds/${id}/play`)
    } catch {
      setStarting(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await api.delete(`/rounds/${id}`)
      router.push(`/${locale}/rounds`)
    } catch {
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  const handleGenerateTeams = async () => {
    setGeneratingTeams(true)
    setTeamsError('')
    try {
      const res = await api.post(`/rounds/${id}/teams/generate?num_teams=${numTeams}`)
      setTeamsData(res.data)
      setShowTeams(true)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setTeamsError(detail ?? lbl('Error al generar equipos', 'Error generating teams'))
    } finally {
      setGeneratingTeams(false)
    }
  }

  const handleMovePlayer = async (playerId: string, toTeam: number) => {
    setMovingPlayer(playerId)
    try {
      const res = await api.put(`/rounds/${id}/teams/assign?player_id=${playerId}&team_number=${toTeam}`)
      setTeamsData(res.data)
    } finally {
      setMovingPlayer(null)
    }
  }

  const [publishingTeams, setPublishingTeams] = useState(false)
  const handlePublishTeams = async () => {
    if (!confirm(lbl(
      '¿Publicar equipos? Todos los jugadores podrán verlos al instante.',
      'Publish teams? All players will see them immediately.'
    ))) return
    setPublishingTeams(true)
    try {
      await api.post(`/rounds/${id}/teams/publish`)
      setTeamsData(prev => prev ? { ...prev, teams_published: true } : prev)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setTeamsError(detail ?? lbl('Error al publicar', 'Error publishing'))
    } finally {
      setPublishingTeams(false)
    }
  }

  const handleFinishRound = async () => {
    if (!confirm(lbl('¿Finalizar la ronda? Esta acción no se puede deshacer.', 'Finish the round? This cannot be undone.'))) return
    setFinishing(true)
    try {
      await api.post(`/rounds/${id}/finish`)
      await load()
    } catch {
      setFinishing(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )
  if (!round) return null

  const fmt = FORMAT_LABELS[round.game_format] ?? { es: round.game_format, en: round.game_format }

  const scheduledDate = new Date(round.scheduled_at).toLocaleString(locale === 'es' ? 'es-MX' : 'en-US', {
    dateStyle: 'medium', timeStyle: 'short'
  })
  const inviteUrl = round.invite_code
    ? `${typeof window !== 'undefined' ? window.location.origin : ''}/${locale}/join/${round.invite_code}`
    : null
  const liveUrl = round.invite_code
    ? `${typeof window !== 'undefined' ? window.location.origin : ''}/${locale}/live/${round.invite_code}`
    : null

  const handleCopy = () => {
    if (!inviteUrl) return
    navigator.clipboard.writeText(inviteUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const amCreator = round?.created_by === myUserId
  const isCreator = players.length > 0 && players.find(p => p.user_id === myUserId) !== undefined
    && round?.status !== 'finished'

  const saveBets = async () => {
    setSavingBet(true)
    try {
      await api.post(`/rounds/${id}/bet-config`, betForm)
      setBetCfg({ ...betForm })
      setShowBets(false)
    } finally { setSavingBet(false) }
  }

  const bf = (k: keyof BetConfig) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : parseFloat(e.target.value) || 0
    setBetForm(prev => ({ ...prev, [k]: val }))
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      {showFormatInfo && (
        <FormatInfoModal format={round.game_format} locale={locale} onClose={() => setShowFormatInfo(false)} />
      )}

      {/* Confirm delete modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-sm bg-zinc-900 border border-zinc-700 rounded-2xl overflow-hidden shadow-2xl">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
                <Trash2 size={22} className="text-red-400" />
              </div>
              <h2 className="text-center font-bold text-white text-lg mb-1">
                {lbl('¿Eliminar esta jugada?', 'Delete this round?')}
              </h2>
              <p className="text-center text-sm text-zinc-400 mb-6">
                {lbl(
                  'Se eliminará la ronda y todos los jugadores confirmados serán notificados. Esta acción no se puede deshacer.',
                  'The round and all confirmed players will be removed. This cannot be undone.'
                )}
              </p>
              <div className="flex gap-3">
                <button onClick={() => setConfirmDelete(false)} disabled={deleting}
                  className="flex-1 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium rounded-xl text-sm transition-colors">
                  {lbl('Cancelar', 'Cancel')}
                </button>
                <button onClick={handleDelete} disabled={deleting}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-red-600 hover:bg-red-500 disabled:opacity-60 text-white font-semibold rounded-xl text-sm transition-colors">
                  {deleting ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
                  {lbl('Sí, eliminar', 'Yes, delete')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/rounds`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={14} className="text-white" />
            </div>
            <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-5">
        {/* Round header */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">

          {/* Edit form */}
          {editing ? (
            <div className="space-y-4 mb-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-white">{lbl('Editar ronda', 'Edit round')}</h2>
                <button onClick={() => setEditing(false)} className="text-zinc-500 hover:text-white transition-colors"><X size={18}/></button>
              </div>
              <div>
                <label className="text-xs text-zinc-500 block mb-1">{lbl('Nombre (opcional)', 'Name (optional)')}</label>
                <input value={editForm.name} onChange={e => setEditForm(f => ({...f, name: e.target.value}))}
                  placeholder={lbl('Ej. Torneo del domingo', 'e.g. Sunday tournament')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500" />
              </div>
              <div>
                <label className="text-xs text-zinc-500 block mb-1">{lbl('Cancha', 'Course')}</label>
                <select value={editForm.course_id} onChange={e => setEditForm(f => ({...f, course_id: e.target.value}))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500">
                  <option value="">{lbl('— Sin cambiar —', '— No change —')}</option>
                  {courses.map(c => <option key={c.id} value={c.id}>{c.name}{c.city ? ` — ${c.city}` : ''}</option>)}
                </select>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs text-zinc-500">{lbl('Formato', 'Format')}</label>
                  <button type="button" onClick={() => setShowFormatInfo(true)}
                    className="flex items-center gap-1 text-xs text-zinc-600 hover:text-emerald-400 transition-colors">
                    <Info size={11} />{lbl('¿Cómo funciona cada formato?', 'How does each format work?')}
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {FORMATS.map(f => (
                    <button key={f.value} type="button" onClick={() => setEditForm(ef => ({...ef, game_format: f.value}))}
                      className={`px-3 py-2 rounded-xl text-xs font-medium border transition-all text-left ${
                        editForm.game_format === f.value
                          ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300'
                          : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:border-zinc-500'
                      }`}>
                      {locale === 'es' ? f.labelEs : f.labelEn}
                    </button>
                  ))}
                </div>
              </div>

              {/* Florida: team size */}
              {editForm.game_format === 'florida' && (
                <div className="bg-zinc-800/60 border border-emerald-500/20 rounded-xl p-3">
                  <label className="text-xs text-zinc-400 block mb-2">{lbl('Jugadores por equipo', 'Players per team')}</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[2, 3, 4].map(n => (
                      <button key={n} type="button" onClick={() => setEditForm(ef => ({...ef, team_size: n}))}
                        className={`py-2 rounded-xl text-xs font-bold border transition-all ${
                          editForm.team_size === n
                            ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300'
                            : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                        }`}>
                        {n} {lbl('jug.', 'pl.')}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-zinc-500 block mb-1">{lbl('Hoyos', 'Holes')}</label>
                  <select value={editForm.holes_to_play} onChange={e => setEditForm(f => ({...f, holes_to_play: Number(e.target.value)}))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500">
                    <option value={9}>9 {lbl('hoyos', 'holes')}</option>
                    <option value={18}>18 {lbl('hoyos', 'holes')}</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 block mb-1">{lbl('Fecha y hora', 'Date & time')}</label>
                  <input type="datetime-local" value={editForm.scheduled_at}
                    onChange={e => setEditForm(f => ({...f, scheduled_at: e.target.value}))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500" />
                </div>
              </div>
              <div className="flex items-center gap-3 bg-zinc-800 rounded-xl px-3 py-2.5">
                <input type="checkbox" id="hcp_edit" checked={editForm.is_handicap_valid}
                  onChange={e => setEditForm(f => ({...f, is_handicap_valid: e.target.checked}))}
                  className="w-4 h-4 accent-emerald-500" />
                <label htmlFor="hcp_edit" className="text-sm text-zinc-300">
                  {lbl('Válida para hándicap WHS', 'Count for WHS handicap')}
                </label>
              </div>
              <div>
                <label className="text-xs text-zinc-500 block mb-1">{lbl('Notas', 'Notes')}</label>
                <textarea value={editForm.notes} onChange={e => setEditForm(f => ({...f, notes: e.target.value}))} rows={2}
                  placeholder={lbl('Instrucciones, reglas locales...', 'Instructions, local rules...')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500 resize-none" />
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={saveEdit} disabled={savingEdit}
                  className="flex-1 flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-2.5 rounded-xl text-sm transition-colors">
                  {savingEdit ? <Loader2 size={15} className="animate-spin"/> : <Save size={15}/>}
                  {lbl('Guardar cambios', 'Save changes')}
                </button>
                <button onClick={() => setEditing(false)}
                  className="px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded-xl text-sm transition-colors">
                  {lbl('Cancelar', 'Cancel')}
                </button>
              </div>
            </div>
          ) : (
            <>
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-xl font-bold text-white mb-1">
                {round.name ?? (locale === 'es' ? 'Ronda de golf' : 'Golf round')}
              </h1>
              <div className="flex flex-wrap gap-3 text-sm text-zinc-400">
                {round.course_name && (
                  <span className="flex items-center gap-1"><MapPin size={13} />{round.course_name}</span>
                )}
                <span className="flex items-center gap-1"><Calendar size={13} />{scheduledDate}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {amCreator && round.status === 'scheduled' && (
                <>
                  <button onClick={openEdit}
                    className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-white bg-zinc-800 hover:bg-zinc-700 px-3 py-1.5 rounded-full transition-colors border border-zinc-700">
                    <Edit2 size={12}/>{lbl('Editar', 'Edit')}
                  </button>
                  <button onClick={() => setConfirmDelete(true)}
                    className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-400 bg-zinc-800 hover:bg-red-500/10 px-3 py-1.5 rounded-full transition-colors border border-zinc-700 hover:border-red-500/40">
                    <Trash2 size={12}/>{lbl('Eliminar', 'Delete')}
                  </button>
                </>
              )}
              <span className={`text-xs font-medium px-3 py-1 rounded-full border ${STATUS_COLOR[round.status]}`}>
                {round.status === 'scheduled' ? lbl('Programada', 'Scheduled') :
                 round.status === 'active' ? lbl('En juego', 'In progress') :
                 lbl('Finalizada', 'Finished')}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 text-xs text-zinc-500">
            <button onClick={() => setShowFormatInfo(true)}
              className="flex items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 hover:text-zinc-300 px-3 py-1 rounded-full transition-colors border border-transparent hover:border-zinc-600">
              {locale === 'es' ? fmt.es : fmt.en}
              <Info size={11} className="text-zinc-600 hover:text-emerald-400" />
            </button>
            <span className="bg-zinc-800 px-3 py-1 rounded-full">{round.holes_to_play} {lbl('hoyos', 'holes')}</span>
            {round.game_format === 'florida' && (
              <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-3 py-1 rounded-full">
                {round.team_size ?? 2} {lbl('jug/equipo', 'players/team')}
              </span>
            )}
            {round.is_handicap_valid && (
              <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">
                {lbl('Válida hándicap', 'Handicap valid')}
              </span>
            )}
          </div>
          {round.notes && (
            <div className="mt-3 bg-zinc-800/60 border border-zinc-700/60 rounded-xl px-4 py-3">
              <p className="text-xs text-zinc-500 mb-1 uppercase tracking-wide font-medium">{lbl('Notas', 'Notes')}</p>
              <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">{round.notes}</p>
            </div>
          )}
            </>
          )}

          {/* Waiting banner for non-creator guests on scheduled rounds */}
          {!amCreator && round.status === 'scheduled' && (
            <div className="mt-4 bg-yellow-500/8 border border-yellow-500/20 rounded-2xl px-5 py-4 flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-yellow-500/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Calendar size={15} className="text-yellow-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-yellow-300">
                  {lbl('Ronda programada — en espera', 'Scheduled round — standing by')}
                </p>
                <p className="text-xs text-yellow-400/70 mt-0.5">
                  {lbl(
                    'El organizador iniciará la jugada en su momento. Esta página se actualizará sola.',
                    'The organizer will start the round when ready. This page will update automatically.'
                  )}
                </p>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-5 flex flex-wrap gap-3">
            {amCreator && round.status === 'scheduled' && (
              <button onClick={handleStart} disabled={starting}
                className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold px-6 py-2.5 rounded-full transition-colors text-sm">
                {starting ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
                {lbl('Iniciar ronda', 'Start round')}
              </button>
            )}
            {round.status === 'active' && (
              <Link href={`/${locale}/rounds/${id}/play`}
                className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-6 py-2.5 rounded-full transition-colors text-sm">
                <Play size={15} />
                {lbl('Continuar ronda', 'Continue round')}
              </Link>
            )}
            {amCreator && round.status === 'active' && (
              <button onClick={handleFinishRound} disabled={finishing}
                className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-60 text-zinc-300 hover:text-white font-medium px-5 py-2.5 rounded-full transition-colors text-sm border border-zinc-700">
                {finishing ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle2 size={15} />}
                {lbl('Finalizar ronda', 'Finish round')}
              </button>
            )}
            {amCreator && inviteUrl && round.status !== 'finished' && (
              <>
                <button onClick={handleCopy}
                  className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm font-medium px-4 py-2.5 rounded-full transition-colors border border-zinc-700">
                  {copied ? <Check size={15} className="text-emerald-400" /> : <Copy size={15} />}
                  {copied ? lbl('¡Copiado!', 'Copied!') : lbl('Copiar enlace', 'Copy link')}
                </button>
                <button onClick={() => setShowQr(v => !v)}
                  className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm font-medium px-4 py-2.5 rounded-full transition-colors border border-zinc-700">
                  <QrCode size={15} />
                  QR
                </button>
              </>
            )}
            {/* Live link — visible to everyone once active */}
            {liveUrl && round.status !== 'scheduled' && (
              <a href={liveUrl} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 bg-red-500/15 hover:bg-red-500/25 text-red-400 border border-red-500/30 text-sm font-semibold px-4 py-2.5 rounded-full transition-colors animate-pulse">
                <Radio size={15} />
                {lbl('Ver en vivo', 'Live view')}
              </a>
            )}
            {/* Spectate — detailed per-hole scorecard for authenticated users */}
            {round.status === 'active' && (
              <Link href={`/${locale}/rounds/${id}/spectate`}
                className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 text-sm font-medium px-4 py-2.5 rounded-full transition-colors">
                <Eye size={15} />
                {lbl('Marcador', 'Scoreboard')}
              </Link>
            )}
            {/* Live link — show to creator even when scheduled */}
            {liveUrl && round.status === 'scheduled' && amCreator && (
              <a href={liveUrl} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 border border-zinc-700 text-sm font-medium px-4 py-2.5 rounded-full transition-colors">
                <Radio size={15} />
                {lbl('Pantalla pública', 'Public screen')}
              </a>
            )}
          </div>

          {/* QR Panel */}
          {showQr && inviteUrl && (
            <div className="mt-5 p-5 bg-zinc-800 rounded-2xl flex flex-col items-center gap-4">
              <p className="text-sm text-zinc-400 text-center">
                {lbl('Muestra este QR para invitar jugadores', 'Show this QR to invite players')}
              </p>
              <div className="bg-white p-4 rounded-xl">
                <QRCodeSVG value={inviteUrl} size={180} />
              </div>
              <p className="text-xs text-zinc-500 font-mono break-all text-center">{inviteUrl}</p>
              <p className="text-xs text-zinc-600">
                {lbl('Código:', 'Code:')} <span className="text-zinc-400 font-mono font-bold">{round.invite_code}</span>
              </p>
            </div>
          )}
        </div>

        {/* Players */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <h2 className="font-semibold text-white mb-4">
            {lbl('Jugadores', 'Players')} <span className="text-zinc-500 font-normal text-sm ml-1">({players.length})</span>
          </h2>
          <div className="divide-y divide-zinc-800">
            {players.map((p) => {
              const entry = board.find(b => b.user_id === p.user_id)
              const isMe = p.user_id === myUserId
              const tee = p.tee_color as TeeColor | null
              const teeCfg = tee ? TEE_CONFIG[tee] : null
              const canChangeTee = isMe && round.status === 'scheduled'
              return (
                <div key={p.user_id} className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-sm font-bold text-emerald-400">
                        {p.first_name.charAt(0)}{p.last_name.charAt(0)}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">
                          {p.first_name} {p.last_name}
                          {isMe && <span className="ml-2 text-xs text-emerald-400">(tú)</span>}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <p className="text-xs text-zinc-500">
                            HCP {p.handicap_index?.toFixed(1) ?? '—'}
                            {p.course_handicap != null && ` · CH ${p.course_handicap}`}
                          </p>
                          {teeCfg && (
                            <span className={`flex items-center gap-1 text-xs ${teeCfg.text}`}>
                              <span className={`w-2.5 h-2.5 rounded-full ${teeCfg.dot}`} />
                              {locale === 'es' ? teeCfg.label.es : teeCfg.label.en}
                            </span>
                          )}
                          {!tee && isMe && round.status === 'scheduled' && (
                            <span className="text-xs text-yellow-400">⚠ {lbl('Elige tee', 'Choose tee')}</span>
                          )}
                          {betCfg && (betCfg.entry_fee > 0 || betCfg.nassau_enabled || betCfg.per_hole_bet > 0) && (
                            <span className={`text-xs ${p.in_bet ? 'text-emerald-500' : 'text-zinc-600'}`}>
                              {p.in_bet ? '$ ' + lbl('apuesta', 'bet') : lbl('sin apuesta', 'no bet')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      {entry && entry.holes_played > 0 ? (
                        <>
                          <p className="text-sm font-bold text-white">{entry.total_gross}</p>
                          <p className="text-xs text-zinc-500">{entry.holes_played} {lbl('hoyos', 'holes')}</p>
                        </>
                      ) : (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          p.status === 'confirmed' ? 'text-emerald-400 bg-emerald-400/10' : 'text-zinc-500 bg-zinc-800'
                        }`}>
                          {p.status === 'confirmed' ? lbl('Confirmado', 'Confirmed') : lbl('Invitado', 'Invited')}
                        </span>
                      )}
                    </div>
                  </div>
                  {/* Bet opt-in/out for current user */}
                  {isMe && round.status === 'scheduled' && betCfg && (
                    betCfg.entry_fee > 0 || betCfg.nassau_enabled || betCfg.per_hole_bet > 0 ||
                    betCfg.birdie_prize > 0 || betCfg.eagle_prize > 0
                  ) && (
                    <div className="mt-2 flex items-center gap-2">
                      <button
                        onClick={async () => {
                          const next = !p.in_bet
                          await api.patch(`/rounds/${id}/my-bet-opt?in_bet=${next}`)
                          setPlayers(prev => prev.map(pl => pl.user_id === myUserId ? { ...pl, in_bet: next } : pl))
                        }}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                          p.in_bet
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400'
                            : 'bg-zinc-800 border-zinc-700 text-zinc-500 hover:border-emerald-500/30 hover:text-emerald-400'
                        }`}>
                        <DollarSign size={11} />
                        {p.in_bet
                          ? lbl('En la apuesta — clic para salir', 'In bet — click to opt out')
                          : lbl('Fuera de la apuesta — clic para entrar', 'Out of bet — click to opt in')}
                      </button>
                    </div>
                  )}

                  {/* Tee selector for current user when round is scheduled */}
                  {canChangeTee && (
                    <div className="mt-3 flex gap-2">
                      {(Object.entries(TEE_CONFIG) as [TeeColor, typeof TEE_CONFIG[TeeColor]][]).map(([key, cfg]) => (
                        <button key={key} disabled={savingTee}
                          onClick={async () => {
                            setSavingTee(true)
                            await api.patch(`/rounds/${id}/my-tee?tee_color=${key}`)
                            setPlayers(prev => prev.map(pl => pl.user_id === myUserId ? { ...pl, tee_color: key } : pl))
                            setSavingTee(false)
                          }}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                            tee === key
                              ? 'border-emerald-500 bg-emerald-500/10 text-white'
                              : 'border-zinc-700 bg-zinc-800 hover:border-zinc-500 ' + cfg.text
                          }`}>
                          <span className={`w-3 h-3 rounded-full ${cfg.dot}`} />
                          {locale === 'es' ? cfg.label.es : cfg.label.en}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Equipos ─────────────────────────────────────────────────────── */}
        {(amCreator || teamsData?.has_teams) && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <button onClick={() => setShowTeams(v => !v)}
              className="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/50 transition-colors">
              <div className="flex items-center gap-2">
                <Users size={16} className="text-blue-400" />
                <span className="font-medium text-white">{lbl('Equipos', 'Teams')}</span>
                {teamsData?.has_teams && (
                  <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">
                    {teamsData.teams.length} {lbl('equipos', 'teams')} · {teamsData.teams.reduce((s, t) => s + t.players.length, 0)} {lbl('jugadores', 'players')}
                  </span>
                )}
              </div>
              {showTeams ? <ChevronUp size={16} className="text-zinc-500" /> : <ChevronDown size={16} className="text-zinc-500" />}
            </button>

            {showTeams && (
              <div className="px-6 pb-6 border-t border-zinc-800 pt-4 space-y-4">

                {/* Creator controls */}
                {amCreator && round.status === 'scheduled' && (
                  <div className="space-y-3">
                    <p className="text-sm text-zinc-400">
                      {lbl(
                        'Los equipos se generan por hándicap similar. Puedes mover jugadores entre equipos manualmente antes de publicar.',
                        'Teams are generated by similar handicap. You can manually move players between teams before publishing.'
                      )}
                    </p>
                    <div className="flex gap-2">
                      {[2, 3, 4].map(n => (
                        <button key={n} onClick={() => setNumTeams(n)}
                          className={`flex-1 py-2 rounded-xl text-sm font-bold border transition-all ${
                            numTeams === n
                              ? 'bg-blue-500/20 border-blue-400/50 text-blue-300'
                              : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                          }`}>
                          {n} {lbl('equipos', 'teams')}
                        </button>
                      ))}
                    </div>
                    <button onClick={handleGenerateTeams} disabled={generatingTeams}
                      className="w-full flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-400 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors">
                      {generatingTeams
                        ? <Loader2 size={16} className="animate-spin" />
                        : <Shuffle size={16} />}
                      {teamsData?.has_teams
                        ? lbl('Regenerar equipos', 'Regenerate teams')
                        : lbl('Generar equipos', 'Generate teams')}
                    </button>
                    {teamsError && <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">{teamsError}</p>}
                  </div>
                )}

                {/* Draft/Published indicator + publish button */}
                {amCreator && teamsData?.has_teams && (
                  <div className={`flex items-center justify-between gap-3 px-4 py-3 rounded-xl border ${
                    teamsData.teams_published
                      ? 'bg-emerald-500/8 border-emerald-500/20'
                      : 'bg-amber-500/8 border-amber-500/20'
                  }`}>
                    <div className="flex items-center gap-2">
                      {teamsData.teams_published
                        ? <Eye size={14} className="text-emerald-400" />
                        : <EyeOff size={14} className="text-amber-400" />}
                      <span className={`text-xs font-semibold ${teamsData.teams_published ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {teamsData.teams_published
                          ? lbl('Publicados — todos los jugadores los ven', 'Published — all players can see them')
                          : lbl('Borrador privado — solo tú lo ves', 'Private draft — only you can see this')}
                      </span>
                    </div>
                    {!teamsData.teams_published && (
                      <button onClick={handlePublishTeams} disabled={publishingTeams}
                        className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-bold text-xs px-3 py-1.5 rounded-lg transition-colors flex-shrink-0">
                        {publishingTeams ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                        {lbl('Publicar', 'Publish')}
                      </button>
                    )}
                  </div>
                )}

                {/* Teams display */}
                {teamsData?.has_teams && (
                  <div className="space-y-3">
                    {/* Balance bar */}
                    {teamsData.teams.length > 1 && (
                      <div className="bg-zinc-800/60 rounded-xl p-3">
                        <p className="text-xs text-zinc-500 mb-2">{lbl('Balance de hándicap por equipo', 'Handicap balance per team')}</p>
                        <div className="flex gap-2 flex-wrap">
                          {teamsData.teams.map(t => {
                            const ui = TEAM_UI[t.color] ?? TEAM_UI.emerald
                            const avg = t.players.length ? (t.total_handicap / t.players.length).toFixed(1) : '—'
                            return (
                              <div key={t.team_number} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs ${ui.bg} ${ui.border}`}>
                                <span className={`w-2 h-2 rounded-full ${ui.dot}`} />
                                <span className={`font-semibold ${ui.text}`}>{t.name}</span>
                                <span className="text-zinc-500">HCP prom {avg}</span>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}

                    {/* Team cards */}
                    {teamsData.teams.map(team => {
                      const ui = TEAM_UI[team.color] ?? TEAM_UI.emerald
                      return (
                        <div key={team.team_number} className={`rounded-xl border overflow-hidden ${ui.border}`}>
                          {/* Team header */}
                          <div className={`flex items-center justify-between px-4 py-2.5 ${ui.bg}`}>
                            <div className="flex items-center gap-2">
                              <span className={`w-3 h-3 rounded-full ${ui.dot}`} />
                              <span className={`font-bold text-sm ${ui.text}`}>{team.name}</span>
                              <span className="text-xs text-zinc-500">{team.players.length} {lbl('jugadores', 'players')}</span>
                            </div>
                            <span className="text-xs text-zinc-500">
                              {lbl('Total HCP', 'Total HCP')}: <span className="text-zinc-300 font-semibold">{team.total_handicap}</span>
                            </span>
                          </div>
                          {/* Players */}
                          <div className="divide-y divide-zinc-800">
                            {team.players.map(p => (
                              <div key={p.player_id} className="px-4 py-2.5 bg-zinc-900/60">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <p className="text-sm font-medium text-white">{p.name}</p>
                                    <p className="text-xs text-zinc-500">@{p.username} · HCP {p.course_handicap ?? p.handicap_index ?? '—'}</p>
                                  </div>
                                  {movingPlayer === p.player_id && (
                                    <Loader2 size={14} className="animate-spin text-zinc-400" />
                                  )}
                                </div>
                                {/* Move buttons — creator only, while teams are unpublished */}
                                {amCreator && !teamsData.teams_published && teamsData.teams.length > 1 && (
                                  <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                                    <span className="text-xs text-zinc-600">{lbl('Mover a:', 'Move to:')}</span>
                                    {teamsData.teams
                                      .filter(t2 => t2.team_number !== team.team_number)
                                      .map(t2 => {
                                        const ui2 = TEAM_UI[t2.color] ?? TEAM_UI.emerald
                                        return (
                                          <button key={t2.team_number}
                                            disabled={movingPlayer !== null}
                                            onClick={() => handleMovePlayer(p.player_id, t2.team_number)}
                                            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all disabled:opacity-40 hover:opacity-90 ${ui2.bg} ${ui2.border} ${ui2.text}`}>
                                            <span className={`w-2 h-2 rounded-full ${ui2.dot}`} />
                                            {t2.name}
                                          </button>
                                        )
                                      })}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    })}

                    {/* Unassigned players */}
                    {teamsData.unassigned.length > 0 && (
                      <div className="rounded-xl border border-zinc-700 overflow-hidden">
                        <div className="px-4 py-2.5 bg-zinc-800/50">
                          <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">{lbl('Sin equipo', 'Unassigned')}</span>
                        </div>
                        <div className="divide-y divide-zinc-800">
                          {teamsData.unassigned.map(p => (
                            <div key={p.player_id} className="px-4 py-2.5">
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="text-sm text-zinc-300">{p.name}</p>
                                  <p className="text-xs text-zinc-500">HCP {p.course_handicap ?? '—'}</p>
                                </div>
                                {movingPlayer === p.player_id && (
                                  <Loader2 size={14} className="animate-spin text-zinc-400" />
                                )}
                              </div>
                              {amCreator && !teamsData.teams_published && (
                                <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                                  <span className="text-xs text-zinc-600">{lbl('Asignar a:', 'Assign to:')}</span>
                                  {teamsData.teams.map(t => {
                                    const ui2 = TEAM_UI[t.color] ?? TEAM_UI.emerald
                                    return (
                                      <button key={t.team_number}
                                        disabled={movingPlayer !== null}
                                        onClick={() => handleMovePlayer(p.player_id, t.team_number)}
                                        className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all disabled:opacity-40 hover:opacity-90 ${ui2.bg} ${ui2.border} ${ui2.text}`}>
                                        <span className={`w-2 h-2 rounded-full ${ui2.dot}`} />
                                        {t.name}
                                      </button>
                                    )
                                  })}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Apuestas — creador: editable | invitados: solo lectura si hay config */}
        {(amCreator || betCfg) && round.status !== 'finished' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <button onClick={() => setShowBets(v => !v)}
              className="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/50 transition-colors">
              <div className="flex items-center gap-2">
                <DollarSign size={16} className="text-emerald-400" />
                <span className="font-semibold text-white text-sm">{lbl('Apuestas', 'Bets')}</span>
                {betCfg && (betCfg.entry_fee > 0 || betCfg.nassau_enabled || betCfg.per_hole_bet > 0) && (
                  <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">
                    {lbl('Configuradas', 'Configured')}
                  </span>
                )}
              </div>
              {showBets ? <ChevronUp size={16} className="text-zinc-500" /> : <ChevronDown size={16} className="text-zinc-500" />}
            </button>

            {showBets && (
              <div className="px-6 pb-6 space-y-4 border-t border-zinc-800 pt-4">
                {!amCreator && (
                  <p className="text-xs text-zinc-500 bg-zinc-800/50 rounded-lg px-3 py-2">
                    {lbl('Solo el organizador puede modificar las apuestas.', 'Only the organizer can edit bets.')}
                  </p>
                )}
                {/* Entry fee */}
                <div className="flex items-center justify-between">
                  <label className="text-sm text-zinc-300">{lbl('Entrada (por jugador)', 'Entry fee (per player)')}</label>
                  <div className="flex items-center gap-1">
                    <span className="text-zinc-500 text-sm">$</span>
                    <input type="number" min="0" step="1" value={betForm.entry_fee}
                      onChange={bf('entry_fee')} disabled={round.status !== 'scheduled' || !amCreator}
                      className="w-20 bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm text-right focus:outline-none focus:border-emerald-500 disabled:opacity-50" />
                  </div>
                </div>

                {/* Nassau */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm text-zinc-300">Nassau</label>
                    <input type="checkbox" checked={betForm.nassau_enabled}
                      onChange={bf('nassau_enabled')} disabled={round.status !== 'scheduled' || !amCreator}
                      className="w-4 h-4 accent-emerald-500" />
                  </div>
                  {betForm.nassau_enabled && (
                    <div className="grid grid-cols-3 gap-2 pl-4">
                      {[
                        ['nassau_front9', lbl('Salida','Front')],
                        ['nassau_back9',  lbl('Vuelta','Back')],
                        ['nassau_total',  'Total'],
                      ].map(([k, label]) => (
                        <div key={k}>
                          <p className="text-xs text-zinc-500 mb-1">{label}</p>
                          <div className="flex items-center gap-1">
                            <span className="text-zinc-500 text-xs">$</span>
                            <input type="number" min="0" step="1" value={(betForm as any)[k]}
                              onChange={bf(k as keyof BetConfig)} disabled={round.status !== 'scheduled' || !amCreator}
                              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm text-right focus:outline-none focus:border-emerald-500 disabled:opacity-50" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Por hoyo */}
                <div className="flex items-center justify-between">
                  <label className="text-sm text-zinc-300">{lbl('Por hoyo ganado', 'Per hole won')}</label>
                  <div className="flex items-center gap-1">
                    <span className="text-zinc-500 text-sm">$</span>
                    <input type="number" min="0" step="1" value={betForm.per_hole_bet}
                      onChange={bf('per_hole_bet')} disabled={round.status !== 'scheduled' || !amCreator}
                      className="w-20 bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm text-right focus:outline-none focus:border-emerald-500 disabled:opacity-50" />
                  </div>
                </div>

                {/* Premios especiales */}
                <div className="bg-zinc-800 rounded-xl p-3 space-y-2">
                  <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">{lbl('Premios especiales', 'Special prizes')}</p>
                  {[
                    ['birdie_prize',        lbl('Birdie', 'Birdie'),          false],
                    ['eagle_prize',         lbl('Eagle', 'Eagle'),            false],
                    ['hole_in_one_prize',   lbl('Hoyo en 1', 'Hole in one'), false],
                    ['three_putt_penalty',  lbl('Penalidad 3 putts', '3-putt penalty'), false],
                  ].map(([k, label]) => (
                    <div key={k as string} className="flex items-center justify-between">
                      <span className="text-sm text-zinc-300">{label as string}</span>
                      <div className="flex items-center gap-1">
                        <span className="text-zinc-500 text-sm">$</span>
                        <input type="number" min="0" step="1" value={(betForm as any)[k as string]}
                          onChange={bf(k as keyof BetConfig)} disabled={round.status !== 'scheduled' || !amCreator}
                          className="w-20 bg-zinc-700 border border-zinc-600 rounded-lg px-2 py-1 text-white text-sm text-right focus:outline-none focus:border-emerald-500 disabled:opacity-50" />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Oyes */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm text-zinc-300">Oyes</label>
                    <input type="checkbox" checked={betForm.oyes_enabled}
                      onChange={bf('oyes_enabled')} disabled={round.status !== 'scheduled' || !amCreator}
                      className="w-4 h-4 accent-emerald-500" />
                  </div>
                  {betForm.oyes_enabled && (
                    <div className="flex items-center justify-between pl-4">
                      <span className="text-sm text-zinc-400">{lbl('Premio por oye', 'Oye prize')}</span>
                      <div className="flex items-center gap-1">
                        <span className="text-zinc-500 text-sm">$</span>
                        <input type="number" min="0" step="1" value={betForm.oyes_prize}
                          onChange={bf('oyes_prize')} disabled={round.status !== 'scheduled' || !amCreator}
                          className="w-20 bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm text-right focus:outline-none focus:border-emerald-500 disabled:opacity-50" />
                      </div>
                    </div>
                  )}
                </div>

                {/* Skines */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <label className="text-sm text-zinc-300">Skines</label>
                      <p className="text-xs text-zinc-600">{lbl('Un skin por hoyo, carry-over en empates', 'One skin per hole, carry-over on ties')}</p>
                    </div>
                    <input type="checkbox" checked={betForm.skins_enabled}
                      onChange={bf('skins_enabled')} disabled={round.status !== 'scheduled' || !amCreator}
                      className="w-4 h-4 accent-emerald-500" />
                  </div>
                  {betForm.skins_enabled && (
                    <div className="pl-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-zinc-400">{lbl('Valor por skin (por jugador)', 'Skin value (per player)')}</span>
                        <div className="flex items-center gap-1">
                          <span className="text-zinc-500 text-sm">$</span>
                          <input type="number" min="0" step="1" value={betForm.skins_value}
                            onChange={bf('skins_value')} disabled={round.status !== 'scheduled' || !amCreator}
                            className="w-20 bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm text-right focus:outline-none focus:border-emerald-500 disabled:opacity-50" />
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-zinc-400">{lbl('Usar score neto', 'Use net score')}</span>
                        <input type="checkbox" checked={betForm.skins_use_net}
                          onChange={bf('skins_use_net')} disabled={round.status !== 'scheduled' || !amCreator}
                          className="w-4 h-4 accent-emerald-500" />
                      </div>
                    </div>
                  )}
                </div>

                {amCreator && round.status === 'scheduled' && (
                  <button onClick={saveBets} disabled={savingBet}
                    className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm">
                    {savingBet ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
                    {lbl('Guardar apuestas', 'Save bets')}
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Skines view */}
        {skins.length > 0 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <button onClick={() => setShowSkins(v => !v)}
              className="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/50 transition-colors">
              <div className="flex items-center gap-2">
                <span className="text-lg">🏌️</span>
                <span className="font-semibold text-white text-sm">Skines</span>
                <span className="text-xs text-zinc-500">
                  {skins.filter(s => s.status === 'won').length} {lbl('ganados', 'won')}
                  {skins.filter(s => s.status === 'tie').length > 0 && ` · ${skins.filter(s => s.status === 'tie').length} ${lbl('carry', 'carry')}`}
                </span>
              </div>
              {showSkins ? <ChevronUp size={16} className="text-zinc-500" /> : <ChevronDown size={16} className="text-zinc-500" />}
            </button>

            {showSkins && (
              <div className="border-t border-zinc-800">
                {/* Totals per player */}
                {Object.entries(skinstotals).some(([, v]) => v > 0) && (
                  <div className="px-5 py-3 border-b border-zinc-800 flex flex-wrap gap-3">
                    {Object.entries(skinstotals).map(([uid, total]) => {
                      if (total === 0) return null
                      const p = players.find(pl => pl.user_id === uid)
                      return (
                        <div key={uid} className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
                          <span className="text-xs font-medium text-emerald-400">{p?.first_name ?? uid.slice(0,6)}</span>
                          <span className="text-xs font-bold text-white">${total.toFixed(0)}</span>
                        </div>
                      )
                    })}
                    {skinsPotRemaining > 0 && (
                      <div className="flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/20 px-3 py-1.5 rounded-full">
                        <span className="text-xs text-yellow-400">{lbl('Bote sin reclamar', 'Unclaimed pot')}</span>
                        <span className="text-xs font-bold text-white">${skinsPotRemaining.toFixed(0)}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Hole by hole */}
                <div className="divide-y divide-zinc-800/50">
                  {skins.map(sk => {
                    const winner = sk.winner_id ? players.find(p => p.user_id === sk.winner_id) : null
                    return (
                      <div key={sk.hole} className={`flex items-center gap-3 px-5 py-2.5 ${
                        sk.status === 'won' ? 'bg-emerald-500/5' :
                        sk.status === 'tie' ? 'bg-yellow-500/5' : ''
                      }`}>
                        <span className={`w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0 ${
                          sk.status === 'won' ? 'bg-emerald-500 text-white' :
                          sk.status === 'tie' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                          'bg-zinc-800 text-zinc-500'
                        }`}>{sk.hole}</span>

                        <div className="flex-1 min-w-0">
                          {sk.status === 'won' && winner && (
                            <p className="text-sm font-medium text-white">
                              {winner.first_name} {winner.last_name.charAt(0)}.
                              {sk.score !== undefined && <span className="text-zinc-500 text-xs ml-1">({sk.score})</span>}
                            </p>
                          )}
                          {sk.status === 'tie' && (
                            <p className="text-sm text-yellow-400">
                              {lbl('Empate', 'Tie')}
                              {sk.score !== undefined && <span className="text-zinc-500 text-xs ml-1">({sk.score})</span>}
                              {' · '}{lbl('pasa al siguiente', 'carries over')}
                            </p>
                          )}
                          {sk.status === 'pending' && (
                            <p className="text-sm text-zinc-600">{lbl('Pendiente', 'Pending')}</p>
                          )}
                        </div>

                        <div className="text-right flex-shrink-0">
                          <p className={`text-sm font-bold ${
                            sk.status === 'won' ? 'text-emerald-400' :
                            sk.status === 'tie' ? 'text-yellow-400' : 'text-zinc-700'
                          }`}>
                            ${sk.pot.toFixed(0)}
                          </p>
                          {sk.carry > 0 && (
                            <p className="text-xs text-zinc-600">+{sk.carry} carry</p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Full scorecard (active or finished) */}
        {board.length > 0 && (
          <RoundScorecard
            board={board}
            players={players}
            holes={holes}
            holesTotal={round.holes_to_play}
            status={round.status}
            lbl={lbl}
          />
        )}
      </main>
    </div>
  )
}
