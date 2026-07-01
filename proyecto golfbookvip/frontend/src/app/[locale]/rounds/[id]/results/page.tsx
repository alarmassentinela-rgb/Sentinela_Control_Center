'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Printer, ArrowLeft, Loader2, Trophy } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

// ── Types ───────────────────────────────────────────────────────────

interface CourseHole {
  hole_number: number
  par: number
  stroke_index: number | null
}

interface Score {
  hole: number
  gross: number
  net: number
  stableford?: number | null
}

interface BoardEntry {
  user_id: string
  first_name?: string
  last_name?: string
  course_handicap?: number | null
  total_gross: number
  total_net?: number
  total_stableford?: number
  thru?: number
  scores: Score[]
  participant_mode?: string
  withdrawn_at?: string | null
}

interface TeeGroupPlayer {
  user_id: string
  name: string
  handicap_index?: number | null
  course_handicap?: number | null
  tee_color?: string | null
  tee_group?: number | null
}

interface Round {
  id: string
  name: string | null
  game_format: string
  holes_to_play: number
  scheduled_at: string
  status: string
  course_id: string
}

interface Course {
  id: string
  name: string
  par_total: number | null
  course_rating: number | null
  slope_rating: number | null
  city?: string | null
  state?: string | null
  holes: CourseHole[]
}

// ── Helpers ─────────────────────────────────────────────────────────

const FORMAT_LABEL: Record<string, string> = {
  stroke:               'Stroke Play',
  stableford:           'Stableford',
  stableford_modified:  'Stableford Modificado',
  match:                'Match Play',
  skins:                'Skins',
  florida:              'Florida',
}

function fmtDate(iso: string, locale: string) {
  return new Date(iso).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US',
    { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
}

function posOrdinal(pos: number, locale: string) {
  if (locale === 'es') return `${pos}°`
  const suffix = pos === 1 ? 'st' : pos === 2 ? 'nd' : pos === 3 ? 'rd' : 'th'
  return `${pos}${suffix}`
}

// ── Stats computation ───────────────────────────────────────────────

interface Stats {
  lowest_gross: { user: string; value: number } | null
  lowest_net: { user: string; value: number } | null
  highest_stableford: { user: string; value: number } | null
  most_birdies: { user: string; value: number } | null
  most_pars: { user: string; value: number } | null
  lowest_front: { user: string; value: number } | null
  lowest_back: { user: string; value: number } | null
  best_par3: { user: string; value: number } | null
  best_par4: { user: string; value: number } | null
  best_par5: { user: string; value: number } | null
  lowest_hole: { user: string; hole: number; value: number } | null
  eagles_or_better: { user: string; count: number }[]
  holes_in_one: { user: string; hole: number }[]
}

function computeStats(board: BoardEntry[], course: Course, holesTotal: number, playerName: (uid: string) => string): Stats {
  const holes = course.holes.filter(h => h.hole_number <= holesTotal)
  const holeMap: Record<number, CourseHole> = {}
  holes.forEach(h => { holeMap[h.hole_number] = h })

  const playable = board.filter(b => b.total_gross > 0 && b.participant_mode !== 'observer' && !b.withdrawn_at)

  const stats: Stats = {
    lowest_gross: null, lowest_net: null, highest_stableford: null,
    most_birdies: null, most_pars: null,
    lowest_front: null, lowest_back: null,
    best_par3: null, best_par4: null, best_par5: null,
    lowest_hole: null,
    eagles_or_better: [], holes_in_one: [],
  }

  for (const b of playable) {
    const name = playerName(b.user_id) || b.user_id

    // Totals
    if (!stats.lowest_gross || b.total_gross < stats.lowest_gross.value) {
      stats.lowest_gross = { user: name, value: b.total_gross }
    }
    const net = b.total_net ?? b.total_gross
    if (!stats.lowest_net || net < stats.lowest_net.value) {
      stats.lowest_net = { user: name, value: net }
    }
    const stable = b.total_stableford ?? 0
    if (!stats.highest_stableford || stable > stats.highest_stableford.value) {
      stats.highest_stableford = { user: name, value: stable }
    }

    // Birdies, pares, eagles+, HIO
    let birdies = 0, pars = 0, eaglesOrBetter = 0
    for (const s of b.scores) {
      const par = holeMap[s.hole]?.par
      if (!par) continue
      const diff = s.gross - par
      if (diff === 0) pars++
      else if (diff === -1) birdies++
      else if (diff <= -2) eaglesOrBetter++
      if (s.gross === 1) stats.holes_in_one.push({ user: name, hole: s.hole })
      if (!stats.lowest_hole || s.gross < stats.lowest_hole.value) {
        stats.lowest_hole = { user: name, hole: s.hole, value: s.gross }
      }
    }
    if (!stats.most_birdies || birdies > stats.most_birdies.value) stats.most_birdies = { user: name, value: birdies }
    if (!stats.most_pars || pars > stats.most_pars.value) stats.most_pars = { user: name, value: pars }
    if (eaglesOrBetter > 0) {
      const existing = stats.eagles_or_better.find(e => e.user === name)
      if (existing) existing.count += eaglesOrBetter
      else stats.eagles_or_better.push({ user: name, count: eaglesOrBetter })
    }

    // Front 9, Back 9
    if (holesTotal === 18) {
      const sumGrossRange = (lo: number, hi: number) => b.scores
        .filter(s => s.hole >= lo && s.hole <= hi).reduce((a, s) => a + s.gross, 0)
      const playedRange = (lo: number, hi: number) => b.scores.filter(s => s.hole >= lo && s.hole <= hi).length
      if (playedRange(1, 9) === 9) {
        const f = sumGrossRange(1, 9)
        if (!stats.lowest_front || f < stats.lowest_front.value) stats.lowest_front = { user: name, value: f }
      }
      if (playedRange(10, 18) === 9) {
        const bk = sumGrossRange(10, 18)
        if (!stats.lowest_back || bk < stats.lowest_back.value) stats.lowest_back = { user: name, value: bk }
      }
    }

    // Par 3, Par 4, Par 5 sumas (solo si jugó todos los de esa categoría)
    const byPar = (parVal: number) => {
      const ohs = holes.filter(h => h.par === parVal)
      if (ohs.length === 0) return null
      const played = b.scores.filter(s => ohs.some(h => h.hole_number === s.hole))
      if (played.length !== ohs.length) return null
      return played.reduce((a, s) => a + s.gross, 0)
    }
    const p3 = byPar(3)
    if (p3 !== null && (!stats.best_par3 || p3 < stats.best_par3.value)) stats.best_par3 = { user: name, value: p3 }
    const p4 = byPar(4)
    if (p4 !== null && (!stats.best_par4 || p4 < stats.best_par4.value)) stats.best_par4 = { user: name, value: p4 }
    const p5 = byPar(5)
    if (p5 !== null && (!stats.best_par5 || p5 < stats.best_par5.value)) stats.best_par5 = { user: name, value: p5 }
  }

  return stats
}

// ── Master sheet ────────────────────────────────────────────────────

type BalBreak = { entry_fee: number; nassau: number; per_hole: number; prizes: number; penalties: number; skins: number; oyes: number; total: number }
type BalPlayer = { user_id: string; name: string; course_handicap: number | null; breakdown: BalBreak }
type BalData = { has_bets: boolean; players: BalPlayer[]; lines: { kind: string; detail: string; amounts: Record<string, number> }[] }

function MasterResults({
  round, course, board, players, gameFormat, locale, balances, printSection = 'all', playerParam,
}: {
  round: Round; course: Course; board: BoardEntry[]; players: TeeGroupPlayer[]
  gameFormat: string; locale: string; balances: BalData | null
  printSection?: string
  playerParam?: string | null
}) {
  // Si printSection != 'all', solo renderizamos esa sección específica
  const showLeaderboard = printSection === 'all' || printSection === 'leaderboard'
  const showAwards = printSection === 'all' || printSection === 'premios'
  const showWinnerBanner = printSection === 'all' || printSection === 'leaderboard'
  const showBalances = printSection === 'all' || printSection === 'balances' || printSection === 'gran-total' || printSection === 'ticket' || printSection.startsWith('bet-')
  const showFooter = true
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const playerNameByUid = (uid: string) => {
    const p = players.find(pl => pl.user_id === uid)
    if (p) return p.name
    const b = board.find(bb => bb.user_id === uid)
    if (b) return `${b.first_name ?? ''} ${b.last_name ?? ''}`.trim()
    return uid.slice(0, 8)
  }

  // Sort by relevant metric for the game format
  const sortedBoard = [...board].filter(b => b.participant_mode !== 'observer' && !b.withdrawn_at)
  if (gameFormat === 'stableford' || gameFormat === 'stableford_modified') {
    sortedBoard.sort((a, b) => (b.total_stableford ?? 0) - (a.total_stableford ?? 0))
  } else {
    sortedBoard.sort((a, b) => {
      const av = a.total_gross > 0 ? a.total_gross : 9999
      const bv = b.total_gross > 0 ? b.total_gross : 9999
      return av - bv
    })
  }

  const stats = computeStats(board, course, round.holes_to_play, playerNameByUid)
  const winner = sortedBoard[0]
  const winnerName = winner ? playerNameByUid(winner.user_id) : '—'
  const totalPar = course.holes.filter(h => h.hole_number <= round.holes_to_play).reduce((s, h) => s + h.par, 0)

  return (
    <div className="tee-card master-results">
      <header className="card-header">
        <div className="brand">⛳ GolfBookVIP</div>
        <div className="meta">{fmtDate(round.scheduled_at, locale)}</div>
      </header>
      <h1 className="tournament-name">{round.name ?? lbl('Ronda sin nombre', 'Untitled round')}</h1>
      <p className="course-line">
        {course.name}{course.city && ` · ${course.city}`}{course.state && `, ${course.state}`}
      </p>
      <p className="format-line">
        {FORMAT_LABEL[round.game_format] ?? round.game_format} ·{' '}
        {round.holes_to_play} {lbl('hoyos', 'holes')}{course.par_total && ` · Par ${course.par_total}`}
        {course.course_rating && ` · CR ${course.course_rating}`}{course.slope_rating && ` · Slope ${course.slope_rating}`}
      </p>

      {/* Winner banner */}
      {showWinnerBanner && winner && winner.total_gross > 0 && (
        <div className="winner-banner">
          <div className="trophy">🏆</div>
          <div>
            <p className="label">{lbl('GANADOR', 'WINNER')}</p>
            <p className="name">{winnerName}</p>
          </div>
          <div className="winner-score">
            {gameFormat === 'stableford' || gameFormat === 'stableford_modified'
              ? <><span className="big">{winner.total_stableford ?? 0}</span><span className="unit">pts</span></>
              : <><span className="big">{winner.total_gross}</span><span className="unit">gross</span></>}
          </div>
        </div>
      )}

      {showLeaderboard && (<>
      <h2 className="section-title">{lbl('Tabla de posiciones', 'Leaderboard')}</h2>
      <table className="leaderboard">
        <thead>
          <tr>
            <th className="pos">{lbl('Pos', 'Pos')}</th>
            <th>{lbl('Jugador', 'Player')}</th>
            <th>HCP</th>
            <th>Gross</th>
            <th>vs Par</th>
            <th>Net</th>
            <th>Pts</th>
            <th>{lbl('Thru', 'Thru')}</th>
          </tr>
        </thead>
        <tbody>
          {sortedBoard.map((b, i) => {
            const name = playerNameByUid(b.user_id)
            const rel = b.total_gross > 0 ? b.total_gross - totalPar : null
            const isWinner = i === 0
            return (
              <tr key={b.user_id} className={isWinner ? 'winner-row' : ''}>
                <td className="pos">{posOrdinal(i + 1, locale)}</td>
                <td className="player-name">{name}{isWinner && <span className="medal"> 🏆</span>}</td>
                <td className="num">{b.course_handicap ?? '—'}</td>
                <td className="num"><b>{b.total_gross || '—'}</b></td>
                <td className={`num rel ${rel !== null && rel < 0 ? 'under' : rel !== null && rel > 0 ? 'over' : ''}`}>
                  {rel === null ? '—' : rel === 0 ? 'E' : rel > 0 ? `+${rel}` : rel}
                </td>
                <td className="num">{b.total_net ?? '—'}</td>
                <td className="num">{b.total_stableford ?? '—'}</td>
                <td className="num">{b.thru === round.holes_to_play ? 'F' : (b.thru ?? '—')}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      </>)}

      {/* Pro stats — "Best of" awards */}
      {showAwards && (<>
      <h2 className="section-title">{lbl('Premios especiales', 'Special awards')}</h2>
      <div className="awards-grid">
        {stats.lowest_gross && (
          <div className="award"><span className="lbl">🎯 {lbl('Mejor gross', 'Lowest gross')}</span><span className="val">{stats.lowest_gross.user} · <b>{stats.lowest_gross.value}</b></span></div>
        )}
        {stats.lowest_net && (
          <div className="award"><span className="lbl">⚡ {lbl('Mejor net', 'Lowest net')}</span><span className="val">{stats.lowest_net.user} · <b>{stats.lowest_net.value}</b></span></div>
        )}
        {stats.highest_stableford && stats.highest_stableford.value > 0 && (
          <div className="award"><span className="lbl">🏅 {lbl('Mejor stableford', 'Best stableford')}</span><span className="val">{stats.highest_stableford.user} · <b>{stats.highest_stableford.value} pts</b></span></div>
        )}
        {stats.most_birdies && stats.most_birdies.value > 0 && (
          <div className="award"><span className="lbl">🐦 {lbl('Más birdies', 'Most birdies')}</span><span className="val">{stats.most_birdies.user} · <b>{stats.most_birdies.value}</b></span></div>
        )}
        {stats.most_pars && stats.most_pars.value > 0 && (
          <div className="award"><span className="lbl">🎖 {lbl('Más pars', 'Most pars')}</span><span className="val">{stats.most_pars.user} · <b>{stats.most_pars.value}</b></span></div>
        )}
        {stats.lowest_front && (
          <div className="award"><span className="lbl">⬆️ {lbl('Mejor salida (1-9)', 'Best front 9')}</span><span className="val">{stats.lowest_front.user} · <b>{stats.lowest_front.value}</b></span></div>
        )}
        {stats.lowest_back && (
          <div className="award"><span className="lbl">⬇️ {lbl('Mejor vuelta (10-18)', 'Best back 9')}</span><span className="val">{stats.lowest_back.user} · <b>{stats.lowest_back.value}</b></span></div>
        )}
        {stats.best_par3 && (
          <div className="award"><span className="lbl">🎯 {lbl('Mejor par 3', 'Best par 3')}</span><span className="val">{stats.best_par3.user} · <b>{stats.best_par3.value}</b></span></div>
        )}
        {stats.best_par4 && (
          <div className="award"><span className="lbl">🎯 {lbl('Mejor par 4', 'Best par 4')}</span><span className="val">{stats.best_par4.user} · <b>{stats.best_par4.value}</b></span></div>
        )}
        {stats.best_par5 && (
          <div className="award"><span className="lbl">🎯 {lbl('Mejor par 5', 'Best par 5')}</span><span className="val">{stats.best_par5.user} · <b>{stats.best_par5.value}</b></span></div>
        )}
        {stats.lowest_hole && (
          <div className="award"><span className="lbl">⚪ {lbl('Score más bajo en un hoyo', 'Lowest single hole')}</span><span className="val">{stats.lowest_hole.user} · {lbl('Hoyo', 'Hole')} {stats.lowest_hole.hole} · <b>{stats.lowest_hole.value}</b></span></div>
        )}
        {stats.eagles_or_better.length > 0 && (
          <div className="award award-special"><span className="lbl">🦅 {lbl('Eagles o mejor', 'Eagles or better')}</span><span className="val">{stats.eagles_or_better.map(e => `${e.user} (${e.count})`).join(' · ')}</span></div>
        )}
        {stats.holes_in_one.length > 0 && (
          <div className="award award-hio"><span className="lbl">⛳ {lbl('¡HOYO EN UNO!', 'HOLE IN ONE!')}</span><span className="val">{stats.holes_in_one.map(h => `${h.user} (H${h.hole})`).join(' · ')}</span></div>
        )}
      </div>
      </>)}

      {/* Balance de apuestas — solo se imprime si hay bets */}
      {showBalances && balances && balances.has_bets && balances.players.length > 0 && balances.players.some(p => Math.abs(p.breakdown.total) > 0.01) && (
        <PrintableBalances balances={balances} locale={locale} printSection={printSection} playerParam={playerParam} />
      )}

      <p className="footer-note">
        {lbl(`${sortedBoard.length} jugadores · `, `${sortedBoard.length} players · `)}
        {lbl('Generado por GolfBookVIP', 'Generated by GolfBookVIP')} · {new Date().toLocaleString(locale === 'es' ? 'es-MX' : 'en-US')}
      </p>
    </div>
  )
}

// ── Helpers para print balances ──────────────────────────────────────

function shortenForPlayerPrint(detail: string, kind: string, amount: number, locale: string): string {
  const isEs = locale === 'es'
  if (kind === 'entry_fee') {
    return amount > 0 ? (isEs ? 'Entry fee — premio' : 'Entry fee — prize') : (isEs ? 'Aportación entry fee' : 'Entry fee contribution')
  }
  if (kind === 'nassau') {
    const segMatch = detail.match(/(Salida|Vuelta|Total|Front|Back)/)
    const seg = segMatch?.[0] ?? ''
    return amount > 0
      ? (isEs ? `Nassau ${seg} — ganaste el pot` : `Nassau ${seg} — won pot`)
      : (isEs ? `Aportación Nassau ${seg}` : `Nassau ${seg} contribution`)
  }
  if (kind === 'per_hole') {
    return amount > 0 ? (isEs ? 'Por hoyo — neto ganado' : 'Per hole — net won') : (isEs ? 'Por hoyo — perdiste' : 'Per hole — lost')
  }
  const cut = detail.split('→')[0].trim()
  return cut || detail
}

const iconForKindPrint = (kind: string): string => {
  switch (kind) {
    case 'entry_fee': return '🎫'
    case 'nassau': return '🎯'
    case 'per_hole': return '⛳'
    case 'prize': return '🏅'
    case 'penalty': return '⚠️'
    case 'skins': return '💎'
    default: return '•'
  }
}

// ── Ticket personal por jugador (1 por hoja al imprimir) ──────────────

function PlayerLedgerCard({ player, lines, locale, position }: {
  player: BalPlayer
  lines: { kind: string; detail: string; amounts: Record<string, number> }[]
  locale: string
  position: number
}) {
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const rows = lines
    .map(l => ({ ...l, amount: l.amounts[player.user_id] ?? 0 }))
    .filter(r => Math.abs(r.amount) > 0.01)
  const gains = rows.filter(r => r.amount > 0)
  const losses = rows.filter(r => r.amount < 0)
  const sumGains = gains.reduce((s, r) => s + r.amount, 0)
  const sumLosses = losses.reduce((s, r) => s + r.amount, 0)
  const net = sumGains + sumLosses
  return (
    <div className="player-ledger-card">
      <div className="ledger-header">
        <div className="ledger-pos">{position === 1 ? '🏆' : position === 2 ? '🥈' : position === 3 ? '🥉' : `#${position}`}</div>
        <div className="ledger-name">
          <h2>{player.name}</h2>
          <p>HCP {player.course_handicap ?? '—'}</p>
        </div>
      </div>
      <table className="ledger-table">
        <thead>
          <tr>
            <th className="gain-col">{lbl('GANÓ (+)', 'WON (+)')}</th>
            <th className="loss-col">{lbl('PAGÓ (−)', 'PAID (−)')}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="gain-cell">
              {gains.length === 0 ? (
                <p className="ledger-empty">{lbl('Sin ganancias', 'No gains')}</p>
              ) : (
                <table className="ledger-mini">
                  <tbody>
                    {gains.map((r, i) => (
                      <tr key={i}>
                        <td className="mini-detail">{iconForKindPrint(r.kind)} {shortenForPlayerPrint(r.detail, r.kind, r.amount, locale)}</td>
                        <td className="mini-amount gain">+${r.amount.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </td>
            <td className="loss-cell">
              {losses.length === 0 ? (
                <p className="ledger-empty">{lbl('Sin pagos', 'No payments')}</p>
              ) : (
                <table className="ledger-mini">
                  <tbody>
                    {losses.map((r, i) => (
                      <tr key={i}>
                        <td className="mini-detail">{iconForKindPrint(r.kind)} {shortenForPlayerPrint(r.detail, r.kind, r.amount, locale)}</td>
                        <td className="mini-amount loss">−${Math.abs(r.amount).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </td>
          </tr>
          <tr className="subtotal-row">
            <td className="gain-cell">
              <div className="subtotal gain">
                <span>{lbl('Subtotal', 'Subtotal')}</span>
                <b>+${sumGains.toFixed(2)}</b>
              </div>
            </td>
            <td className="loss-cell">
              <div className="subtotal loss">
                <span>{lbl('Subtotal', 'Subtotal')}</span>
                <b>−${Math.abs(sumLosses).toFixed(2)}</b>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div className={`ledger-net ${net >= 0 ? 'positive' : 'negative'}`}>
        <span>{lbl('TOTAL NETO', 'NET TOTAL')}</span>
        <b>{net >= 0 ? `+$${net.toFixed(2)}` : `−$${Math.abs(net).toFixed(2)}`}</b>
      </div>
    </div>
  )
}

// ── Printable balances detallados por tipo + gran total ─────────────

function PrintableBalances({ balances, locale, printSection = 'all', playerParam }: {
  balances: BalData; locale: string; printSection?: string; playerParam?: string | null
}) {
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const playerName = (uid: string) => balances.players.find(p => p.user_id === uid)?.name ?? uid.slice(0, 8)

  // Filtros por sección
  const showAllBets = printSection === 'all' || printSection === 'balances'
  const showBetEntryFee = showAllBets || printSection === 'bet-entry_fee'
  const showBetNassau = showAllBets || printSection === 'bet-nassau'
  const showBetPerHole = showAllBets || printSection === 'bet-per_hole'
  const showBetPrize = showAllBets || printSection === 'bet-prize'
  const showBetPenalty = showAllBets || printSection === 'bet-penalty'
  const showBetSkins = showAllBets || printSection === 'bet-skins'
  const showAnyBet = showBetEntryFee || showBetNassau || showBetPerHole || showBetPrize || showBetPenalty || showBetSkins
  const showGranTotal = printSection === 'all' || printSection === 'balances' || printSection === 'gran-total'
  const showTickets = printSection === 'all' || printSection === 'ticket'

  // Agrupar lines por kind
  const byKind: Record<string, { detail: string; amounts: Record<string, number> }[]> = {}
  for (const l of balances.lines) {
    byKind[l.kind] = byKind[l.kind] ?? []
    byKind[l.kind].push(l)
  }

  const fmt = (v: number) => v >= 0 ? `+$${v.toFixed(2)}` : `−$${Math.abs(v).toFixed(2)}`

  const renderBetSection = (kind: string, titleEs: string, titleEn: string, icon: string) => {
    const lines = byKind[kind]
    if (!lines || lines.length === 0) return null
    return (
      <div key={kind} className="bet-block">
        <h3 className="bet-block-title">{icon} {lbl(titleEs, titleEn)}</h3>
        {lines.map((line, idx) => {
          const moved = Object.entries(line.amounts).filter(([, v]) => Math.abs(v) > 0.01)
          const winners = moved.filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])
          const losers = moved.filter(([, v]) => v < 0).sort((a, b) => a[1] - b[1])
          const allLosersEqual = losers.length > 3 && losers.every(([, v]) => Math.abs(v - losers[0][1]) < 0.01)
          return (
            <div key={idx} className="bet-line">
              <p className="bet-detail">{line.detail}</p>
              <table className="bet-line-table">
                <tbody>
                  {winners.map(([uid, v]) => (
                    <tr key={uid} className="winner">
                      <td>✓ {playerName(uid)}</td>
                      <td className="amount plus">{fmt(v)}</td>
                    </tr>
                  ))}
                  {allLosersEqual ? (
                    <tr className="loser">
                      <td className="grouped">{losers.length} {lbl('jugadores pagaron', 'players paid')}</td>
                      <td className="amount minus">{fmt(losers[0][1])} {lbl('c/u', 'each')}</td>
                    </tr>
                  ) : (
                    losers.map(([uid, v]) => (
                      <tr key={uid} className="loser">
                        <td>× {playerName(uid)}</td>
                        <td className="amount minus">{fmt(v)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )
        })}
      </div>
    )
  }

  // Filtrar jugadores para tickets si se pidió uno específico
  const ticketPlayers = playerParam
    ? balances.players.filter(p => p.user_id === playerParam)
    : balances.players

  return (
    <>
      {showAnyBet && (<>
        <h2 className="section-title">{lbl('Pérdidas y ganancias — Desglose', 'Gains & losses — Breakdown')}</h2>
        <div className="balances-detailed">
          {showBetEntryFee && renderBetSection('entry_fee', 'Entrada (Entry Fee)', 'Entry Fee', '🎫')}
          {showBetNassau && renderBetSection('nassau', 'Nassau', 'Nassau', '🎯')}
          {showBetPerHole && renderBetSection('per_hole', 'Por hoyo ganado', 'Per hole won', '⛳')}
          {showBetPrize && renderBetSection('prize', 'Premios (birdie/eagle/HIO)', 'Prizes (birdie/eagle/HIO)', '🏅')}
          {showBetPenalty && renderBetSection('penalty', 'Castigos (3 putts)', 'Penalties (3-putts)', '⚠️')}
          {showBetSkins && renderBetSection('skins', 'Skines (carry-over)', 'Skins (carry-over)', '💎')}
        </div>
      </>)}

      {showGranTotal && (<>
      <h2 className="section-title">🏆 {lbl('GRAN TOTAL POR JUGADOR', 'GRAND TOTAL PER PLAYER')}</h2>
      <table className="balances-table">
        <thead>
          <tr>
            <th className="pos">#</th>
            <th>{lbl('Jugador', 'Player')}</th>
            <th>{lbl('Entrada', 'Entry')}</th>
            <th>Nassau</th>
            <th>{lbl('Por hoyo', 'Per hole')}</th>
            <th>{lbl('Premio', 'Prize')}</th>
            <th>{lbl('Castigo', 'Penalty')}</th>
            <th>{lbl('Skines', 'Skins')}</th>
            <th>TOTAL</th>
          </tr>
        </thead>
        <tbody>
          {balances.players.map((p, i) => {
            const t = p.breakdown.total
            const cellClass = (v: number) => Math.abs(v) < 0.01 ? '' : v > 0 ? 'plus' : 'minus'
            return (
              <tr key={p.user_id} className={i === 0 ? 'top' : ''}>
                <td className="pos">{posOrdinal(i + 1, locale)}</td>
                <td className="player-name">{p.name}</td>
                <td className={`num ${cellClass(p.breakdown.entry_fee)}`}>{fmt(p.breakdown.entry_fee)}</td>
                <td className={`num ${cellClass(p.breakdown.nassau)}`}>{fmt(p.breakdown.nassau)}</td>
                <td className={`num ${cellClass(p.breakdown.per_hole)}`}>{fmt(p.breakdown.per_hole)}</td>
                <td className={`num ${cellClass(p.breakdown.prizes)}`}>{fmt(p.breakdown.prizes)}</td>
                <td className={`num ${cellClass(p.breakdown.penalties)}`}>{fmt(p.breakdown.penalties)}</td>
                <td className={`num ${cellClass(p.breakdown.skins)}`}>{fmt(p.breakdown.skins)}</td>
                <td className={`num total ${cellClass(t)}`}><b>{fmt(t)}</b></td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="balances-note">
        {lbl(
          'Cada apuesta calculada de forma independiente y sumada al gran total. Entry fee 60/30/10 a low net · Nassau pot al low net del segmento · Por hoyo low net cobra a los demás · Premios/castigos pay-each-other · Skines con carry-over.',
          'Each bet calculated independently and summed. Entry fee 60/30/10 low net · Nassau pot to segment low net · Per hole low net charges others · Prizes/penalties pay-each-other · Skins with carry-over.'
        )}
      </p>
      </>)}

      {/* Tickets personales por jugador — 1 por hoja al imprimir */}
      {showTickets && (
        <div className="player-ledger-container">
          {ticketPlayers.map((p) => {
            const originalPos = balances.players.findIndex(pp => pp.user_id === p.user_id) + 1
            return (
              <PlayerLedgerCard key={p.user_id} player={p} lines={balances.lines} locale={locale} position={originalPos} />
            )
          })}
        </div>
      )}
    </>
  )
}

// ── Per-player card ─────────────────────────────────────────────────

function PlayerResultCard({
  round, course, board, allBoard, player, position, gameFormat, locale,
}: {
  round: Round; course: Course; board: BoardEntry; allBoard: BoardEntry[]; player: TeeGroupPlayer; position: number; gameFormat: string; locale: string
}) {
  void allBoard
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const holes = course.holes.filter(h => h.hole_number <= round.holes_to_play)
  const front = holes.slice(0, 9)
  const back  = holes.slice(9, 18)

  const scoreByHole: Record<number, Score> = {}
  board.scores.forEach(s => { scoreByHole[s.hole] = s })

  const sumGross = (hs: CourseHole[]) => hs.reduce((s, h) => s + (scoreByHole[h.hole_number]?.gross ?? 0), 0)
  const sumNet   = (hs: CourseHole[]) => hs.reduce((s, h) => s + (scoreByHole[h.hole_number]?.net ?? 0), 0)
  const sumStab  = (hs: CourseHole[]) => hs.reduce((s, h) => s + (scoreByHole[h.hole_number]?.stableford ?? 0), 0)
  const sumPar   = (hs: CourseHole[]) => hs.reduce((s, h) => s + h.par, 0)

  const Grid = ({ label, hs, startNum }: { label: string; hs: CourseHole[]; startNum: number }) => {
    void startNum
    return (
    <table className="result-grid">
      <thead>
        <tr>
          <th className="row-label">{label}</th>
          {hs.map(h => <th key={h.hole_number} className="hole-num">{h.hole_number}</th>)}
          <th className="tot-col">TOT</th>
        </tr>
        <tr className="par-row">
          <th>Par</th>
          {hs.map(h => <td key={h.hole_number}>{h.par}</td>)}
          <td className="tot-col"><b>{sumPar(hs)}</b></td>
        </tr>
        <tr className="si-row">
          <th>SI</th>
          {hs.map(h => <td key={h.hole_number}>{h.stroke_index ?? '—'}</td>)}
          <td className="tot-col">—</td>
        </tr>
      </thead>
      <tbody>
        <tr className="player-row">
          <th className="row-label">Gross</th>
          {hs.map(h => {
            const sc = scoreByHole[h.hole_number]
            const par = h.par
            if (!sc) return <td key={h.hole_number} className="score-cell">—</td>
            const diff = sc.gross - par
            const cls = diff <= -2 ? 'eagle' : diff === -1 ? 'birdie' : diff === 0 ? 'par' : diff === 1 ? 'bogey' : 'over'
            return <td key={h.hole_number} className={`score-cell ${cls}`}>{sc.gross}</td>
          })}
          <td className="tot-col"><b>{sumGross(hs)}</b></td>
        </tr>
        <tr className="net-row">
          <th className="row-label">Net</th>
          {hs.map(h => {
            const sc = scoreByHole[h.hole_number]
            return <td key={h.hole_number} className="score-cell-net">{sc?.net ?? '—'}</td>
          })}
          <td className="tot-col"><b>{sumNet(hs)}</b></td>
        </tr>
        {(gameFormat === 'stableford' || gameFormat === 'stableford_modified') && (
          <tr className="stab-row">
            <th className="row-label">Pts</th>
            {hs.map(h => {
              const sc = scoreByHole[h.hole_number]
              return <td key={h.hole_number} className="score-cell-stab">{sc?.stableford ?? '—'}</td>
            })}
            <td className="tot-col"><b>{sumStab(hs)}</b></td>
          </tr>
        )}
      </tbody>
    </table>
  )}

  const totalGross = sumGross(holes)
  const totalNet = sumNet(holes)
  const totalStab = sumStab(holes)
  const totalPar = sumPar(holes)
  const rel = totalGross - totalPar

  // Count special outcomes
  let birdies = 0, pars = 0, eagles = 0, bogeys = 0, doubles = 0
  for (const h of holes) {
    const sc = scoreByHole[h.hole_number]
    if (!sc) continue
    const d = sc.gross - h.par
    if (d <= -2) eagles++
    else if (d === -1) birdies++
    else if (d === 0) pars++
    else if (d === 1) bogeys++
    else doubles++
  }

  return (
    <div className="tee-card result-card">
      <header className="card-header">
        <div className="brand">⛳ GolfBookVIP</div>
        <div className="meta">{fmtDate(round.scheduled_at, locale)}</div>
      </header>
      <h1 className="tournament-name">{round.name ?? lbl('Ronda sin nombre', 'Untitled round')}</h1>
      <p className="course-line">
        {course.name}{course.city && ` · ${course.city}`}{course.state && `, ${course.state}`}
      </p>
      <p className="format-line">
        {FORMAT_LABEL[round.game_format] ?? round.game_format} · {round.holes_to_play} {lbl('hoyos', 'holes')}{course.par_total && ` · Par ${course.par_total}`}
      </p>

      {/* Player + position header */}
      <div className="player-header">
        <div className="position">
          {position === 1 ? <span className="medal-1">🏆</span> : position === 2 ? <span className="medal-2">🥈</span> : position === 3 ? <span className="medal-3">🥉</span> : null}
          <span className="pos-num">{posOrdinal(position, locale)}</span>
        </div>
        <div className="player-info">
          <p className="player-name">{player.name}</p>
          <p className="player-meta">
            HCP {player.handicap_index?.toFixed(1) ?? '—'} · C-HCP {player.course_handicap ?? '—'}
            {player.tee_color && ` · Tee ${player.tee_color}`}
          </p>
        </div>
        <div className="player-totals">
          <div><span className="lbl">Gross</span><span className="val">{totalGross || '—'}</span></div>
          <div><span className="lbl">Net</span><span className="val">{totalNet || '—'}</span></div>
          <div><span className="lbl">vs Par</span><span className="val">{rel === 0 ? 'E' : rel > 0 ? `+${rel}` : rel}</span></div>
          {(gameFormat === 'stableford' || gameFormat === 'stableford_modified') && (
            <div><span className="lbl">Pts</span><span className="val">{totalStab || '—'}</span></div>
          )}
        </div>
      </div>

      {/* Scorecard grids */}
      <h3 className="section-title">{lbl('Tarjeta final', 'Final scorecard')}</h3>
      <Grid label={lbl('Salida', 'Front')} hs={front} startNum={1} />
      {back.length > 0 && <Grid label={lbl('Vuelta', 'Back')} hs={back} startNum={10} />}

      {/* Hole performance summary */}
      <h3 className="section-title">{lbl('Rendimiento', 'Performance')}</h3>
      <div className="perf-grid">
        <div className="perf-cell perf-eagle"><span>Eagles</span><b>{eagles}</b></div>
        <div className="perf-cell perf-birdie"><span>Birdies</span><b>{birdies}</b></div>
        <div className="perf-cell perf-par"><span>Pars</span><b>{pars}</b></div>
        <div className="perf-cell perf-bogey"><span>Bogeys</span><b>{bogeys}</b></div>
        <div className="perf-cell perf-over"><span>Doubles+</span><b>{doubles}</b></div>
      </div>

      <div className="signature-section">
        <div className="sig-block">
          <div className="sig-line"></div>
          <p>{lbl('Firma del jugador', 'Player signature')}</p>
        </div>
        <div className="sig-block">
          <div className="sig-line"></div>
          <p>{lbl('Firma del marker', 'Marker signature')}</p>
        </div>
      </div>

      <p className="footer-note">
        {lbl('Generado por GolfBookVIP', 'Generated by GolfBookVIP')} · {new Date().toLocaleString(locale === 'es' ? 'es-MX' : 'en-US')}
      </p>
    </div>
  )
}

// ── Main page ───────────────────────────────────────────────────────

export default function ResultsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-zinc-950 flex items-center justify-center"><Loader2 size={28} className="animate-spin text-emerald-500" /></div>}>
      <ResultsContent />
    </Suspense>
  )
}

function ResultsContent() {
  const router = useRouter()
  const params = useParams()
  const searchParams = useSearchParams()
  const id = params.id as string
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  // URL params para modo "imprimir sección específica"
  const section = searchParams.get('section') ?? 'all'  // all, leaderboard, premios, balances, gran-total, ticket
  const autoprint = searchParams.get('autoprint') === 'true'
  const playerParam = searchParams.get('player')  // user_id para ticket específico

  const [loading, setLoading] = useState(true)
  const [round, setRound] = useState<Round | null>(null)
  const [course, setCourse] = useState<Course | null>(null)
  const [board, setBoard] = useState<BoardEntry[]>([])
  const [players, setPlayers] = useState<TeeGroupPlayer[]>([])
  type BBreak = { entry_fee: number; nassau: number; per_hole: number; prizes: number; penalties: number; skins: number; oyes: number; total: number }
  type BPlayer = { user_id: string; name: string; course_handicap: number | null; breakdown: BBreak }
  type BData = { has_bets: boolean; players: BPlayer[]; lines: { kind: string; detail: string; amounts: Record<string, number> }[] }
  const [balances, setBalances] = useState<BData | null>(null)
  const [view, setView] = useState<'master' | 'cards'>('master')

  useEffect(() => {
    if (!isAuthed()) { router.push(`/${locale}/auth/login`); return }
    const load = async () => {
      try {
        const rRes = await api.get(`/rounds/${id}`)
        setRound(rRes.data)
        const [cRes, bRes, tgRes, balRes] = await Promise.all([
          api.get(`/courses/${rRes.data.course_id}`),
          api.get(`/rounds/${id}/scoreboard`),
          api.get(`/rounds/${id}/tee-groups`).catch(() => ({ data: { groups: [], ungrouped: [] } })),
          api.get(`/rounds/${id}/balances`, { params: { lang: locale } }).catch(() => ({ data: null })),
        ])
        setCourse(cRes.data)
        setBoard(bRes.data)
        if (balRes.data) setBalances(balRes.data)
        // Flatten players from tee-groups for name lookup
        const all: TeeGroupPlayer[] = []
        const tg = tgRes.data
        type RawTGP = { user_id: string; name: string; handicap_index?: number | null; course_handicap?: number | null; tee_color?: string | null; tee_group?: number | null }
        for (const g of (tg.groups ?? []) as { players: RawTGP[]; group_number: number }[]) {
          for (const p of g.players) {
            all.push({ user_id: p.user_id, name: p.name, handicap_index: p.handicap_index, course_handicap: p.course_handicap, tee_color: p.tee_color, tee_group: g.group_number })
          }
        }
        for (const p of (tg.ungrouped ?? []) as RawTGP[]) {
          all.push({ user_id: p.user_id, name: p.name, handicap_index: p.handicap_index, course_handicap: p.course_handicap, tee_color: p.tee_color, tee_group: null })
        }
        setPlayers(all)
      } finally { setLoading(false) }
    }
    load()
  }, [id, locale, router])

  // Auto-disparar diálogo de impresión cuando la data ya cargó (modo print)
  useEffect(() => {
    if (autoprint && !loading && round && course) {
      const t = setTimeout(() => window.print(), 600)
      return () => clearTimeout(t)
    }
  }, [autoprint, loading, round, course])

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  if (!round || !course) return null

  // Sort board for per-player cards
  const playerNameByUid = (uid: string) => {
    const p = players.find(pl => pl.user_id === uid)
    if (p) return p.name
    const b = board.find(bb => bb.user_id === uid)
    if (b) return `${b.first_name ?? ''} ${b.last_name ?? ''}`.trim()
    return uid.slice(0, 8)
  }

  const sortedBoard = [...board].filter(b => b.participant_mode !== 'observer' && !b.withdrawn_at)
  if (round.game_format === 'stableford' || round.game_format === 'stableford_modified') {
    sortedBoard.sort((a, b) => (b.total_stableford ?? 0) - (a.total_stableford ?? 0))
  } else {
    sortedBoard.sort((a, b) => {
      const av = a.total_gross > 0 ? a.total_gross : 9999
      const bv = b.total_gross > 0 ? b.total_gross : 9999
      return av - bv
    })
  }

  return (
    <>
      <div className="no-print bg-zinc-900 border-b border-zinc-800 sticky top-0 z-30 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-2">
          <Link href={`/${locale}/rounds/${id}`}
            className="text-zinc-400 hover:text-white transition-colors flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} />
            {lbl('Ronda', 'Round')}
          </Link>
          <div className="flex items-center gap-2">
            <div className="flex gap-1 bg-zinc-800 border border-zinc-700 rounded-lg p-0.5">
              <button onClick={() => setView('master')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  view === 'master' ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}>
                <Trophy size={11} className="inline mr-1" />
                {lbl('Maestra', 'Master')}
              </button>
              <button onClick={() => setView('cards')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  view === 'cards' ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}>
                {lbl('Tarjetas', 'Cards')}
              </button>
            </div>
            <button onClick={() => window.print()}
              className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-4 py-2 rounded-lg text-sm transition-colors">
              <Printer size={14} />
              {lbl('Imprimir', 'Print')}
            </button>
          </div>
        </div>
        <p className="max-w-5xl mx-auto text-[10px] text-zinc-500 mt-1.5 text-center">
          {lbl(
            'Tip: en el diálogo de imprimir, desactiva encabezados/pies del navegador para una salida más limpia.',
            'Tip: disable browser headers/footers in the print dialog for a cleaner output.'
          )}
        </p>
      </div>

      <main className="print-area bg-zinc-950 text-zinc-100">
        {view === 'master' ? (
          <MasterResults round={round} course={course} board={board} players={players} gameFormat={round.game_format} locale={locale} balances={balances} printSection={section} playerParam={playerParam} />
        ) : (
          sortedBoard.map((b, i) => {
            const player = players.find(p => p.user_id === b.user_id) ?? {
              user_id: b.user_id,
              name: playerNameByUid(b.user_id),
            }
            return (
              <PlayerResultCard
                key={b.user_id}
                round={round}
                course={course}
                board={b}
                allBoard={board}
                player={player}
                position={i + 1}
                gameFormat={round.game_format}
                locale={locale}
              />
            )
          })
        )}
      </main>

      <style jsx global>{`
        /* ── Estilos compartidos con tee-cards (sheet "papel") ── */
        .tee-card {
          background: #fff; color: #111;
          margin: 1.5rem auto; padding: 1.5rem 2rem;
          width: 8.5in; max-width: 100%;
          box-shadow: 0 2px 20px rgba(0,0,0,0.3);
          font-family: ui-sans-serif, system-ui, sans-serif;
          font-size: 11pt; line-height: 1.4;
        }
        .tee-card .card-header {
          display: flex; justify-content: space-between; align-items: baseline;
          border-bottom: 2px solid #047857; padding-bottom: 0.4rem; margin-bottom: 0.7rem;
        }
        .tee-card .brand { font-weight: 800; color: #047857; font-size: 12pt; letter-spacing: 0.02em; }
        .tee-card .meta { color: #555; font-size: 10pt; }
        .tee-card .tournament-name { font-size: 22pt; font-weight: 900; margin: 0.2rem 0; letter-spacing: -0.02em; color: #111; }
        .tee-card .course-line { color: #444; font-size: 11pt; margin: 0; }
        .tee-card .format-line { color: #666; font-size: 9pt; margin: 0.15rem 0 0.6rem 0; font-style: italic; }
        .tee-card .section-title { font-size: 11pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #047857; margin: 0.7rem 0 0.3rem 0; }
        .tee-card .footer-note { font-size: 8pt; color: #888; text-align: center; margin-top: 1rem; }

        /* Winner banner (master) */
        .winner-banner {
          background: linear-gradient(135deg, #fef3c7 0%, #fbbf24 100%);
          border: 2px solid #d97706; border-radius: 0.7rem;
          padding: 0.6rem 1rem; margin: 0.6rem 0 0.8rem 0;
          display: flex; align-items: center; gap: 0.8rem;
        }
        .winner-banner .trophy { font-size: 32pt; line-height: 1; }
        .winner-banner .label { font-size: 9pt; color: #92400e; font-weight: 700; letter-spacing: 0.1em; margin: 0; text-transform: uppercase; }
        .winner-banner .name { font-size: 17pt; font-weight: 900; color: #78350f; margin: 0; line-height: 1.1; }
        .winner-banner .winner-score { margin-left: auto; text-align: right; }
        .winner-banner .big { font-size: 26pt; font-weight: 900; color: #78350f; line-height: 1; }
        .winner-banner .unit { font-size: 9pt; color: #92400e; margin-left: 0.3rem; }

        /* Leaderboard table */
        .leaderboard { width: 100%; border-collapse: collapse; font-size: 9.5pt; margin-bottom: 0.7rem; }
        .leaderboard th { background: #047857; color: #fff; padding: 0.4rem 0.5rem; text-align: left; }
        .leaderboard th.pos, .leaderboard th:nth-child(n+3) { text-align: center; }
        .leaderboard td { padding: 0.35rem 0.5rem; border-bottom: 1px solid #e5e7eb; }
        .leaderboard td.pos { text-align: center; font-weight: 700; font-variant-numeric: tabular-nums; }
        .leaderboard td.player-name { font-weight: 600; }
        .leaderboard td.num { text-align: center; font-variant-numeric: tabular-nums; }
        .leaderboard td.rel.under { color: #047857; font-weight: 700; }
        .leaderboard td.rel.over { color: #b91c1c; }
        .leaderboard tr.winner-row { background: #fef3c7; }
        .leaderboard tr.winner-row td { font-weight: 700; }
        .leaderboard .medal { margin-left: 0.2rem; }

        /* Awards grid */
        .awards-grid {
          display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem 0.8rem;
          font-size: 9pt; margin-bottom: 0.6rem;
        }
        .award {
          background: #f9fafb; border: 1px solid #e5e7eb; border-left: 3px solid #047857;
          border-radius: 0.3rem; padding: 0.4rem 0.6rem;
          display: flex; justify-content: space-between; gap: 0.5rem;
        }
        .award .lbl { color: #444; }
        .award .val { color: #111; text-align: right; }
        .award-special { background: #f3e8ff; border-left-color: #7c3aed; grid-column: 1 / -1; }
        .award-hio { background: #fef2f2; border-left-color: #dc2626; grid-column: 1 / -1; }

        /* Balances table */
        .balances-table { width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-bottom: 0.4rem; }
        .balances-table th { background: #b45309; color: #fff; padding: 0.35rem 0.4rem; text-align: center; font-weight: 700; }
        .balances-table th:nth-child(2) { text-align: left; }
        .balances-table td { padding: 0.25rem 0.4rem; border-bottom: 1px solid #e5e7eb; text-align: center; font-variant-numeric: tabular-nums; }
        .balances-table td.pos { font-weight: 700; }
        .balances-table td.player-name { text-align: left; font-weight: 600; color: #111; }
        .balances-table td.num { font-size: 8pt; }
        .balances-table td.num.plus { color: #111; }
        .balances-table td.num.minus { color: #b91c1c; }
        .balances-table td.total { font-size: 9pt; border-left: 1px solid #ccc; background: #fef3c7; }
        .balances-table tr.top td { background: #fef3c7; font-weight: 700; }
        .balances-table tr.top td.total { background: #fde68a; }
        .balances-note { font-size: 7.5pt; color: #666; font-style: italic; margin: 0 0 0.5rem 0; }

        /* Detailed balances per bet type */
        .balances-detailed { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.6rem; }
        .bet-block {
          background: #f9fafb; border: 1px solid #e5e7eb; border-left: 3px solid #b45309;
          border-radius: 0.3rem; padding: 0.4rem 0.6rem; break-inside: avoid;
        }
        .bet-block-title { font-size: 9pt; font-weight: 700; color: #78350f; margin: 0 0 0.3rem 0; text-transform: uppercase; letter-spacing: 0.03em; }
        .bet-line { margin-bottom: 0.4rem; }
        .bet-line:last-child { margin-bottom: 0; }
        .bet-detail { font-size: 7.5pt; color: #555; margin: 0 0 0.15rem 0; font-style: italic; line-height: 1.3; }
        .bet-line-table { width: 100%; border-collapse: collapse; font-size: 8pt; }
        .bet-line-table td { padding: 0.1rem 0.15rem; border: none; }
        .bet-line-table td.amount { text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; }
        .bet-line-table td.amount.plus { color: #047857; }
        .bet-line-table td.amount.minus { color: #b91c1c; }
        .bet-line-table td.grouped { color: #666; font-style: italic; }
        .bet-line-table tr.winner td:first-child { color: #047857; }
        .bet-line-table tr.loser td:first-child { color: #999; }

        /* Player Ledger Cards — 1 por hoja al imprimir */
        .player-ledger-container { margin-top: 1rem; }
        .player-ledger-card {
          background: #fff; color: #111;
          border: 1.5px solid #047857;
          border-radius: 0.5rem;
          padding: 0.6rem 0.8rem;
          margin-bottom: 0.5rem;
          break-inside: avoid;
          page-break-before: always;
          font-size: 9pt;
        }
        .player-ledger-card:first-child { page-break-before: avoid; }

        .ledger-header { display: flex; align-items: center; gap: 0.7rem; border-bottom: 2px solid #047857; padding-bottom: 0.4rem; margin-bottom: 0.5rem; }
        .ledger-pos { font-size: 24pt; font-weight: 900; line-height: 1; color: #047857; min-width: 2.5rem; text-align: center; }
        .ledger-name h2 { font-size: 16pt; font-weight: 900; margin: 0; color: #111; line-height: 1.1; }
        .ledger-name p { font-size: 9pt; color: #666; margin: 0; }

        .ledger-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        .ledger-table thead th { padding: 0.25rem 0.5rem; font-size: 8pt; font-weight: 700; text-align: left; text-transform: uppercase; letter-spacing: 0.05em; }
        .ledger-table .gain-col { background: #dcfce7; color: #047857; border: 1px solid #86efac; }
        .ledger-table .loss-col { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        .ledger-table td { padding: 0.2rem; vertical-align: top; border: 1px solid #e5e7eb; }
        .ledger-table .gain-cell { background: #f0fdf4; }
        .ledger-table .loss-cell { background: #fef2f2; }
        .ledger-empty { font-size: 8pt; color: #999; font-style: italic; margin: 0.3rem; }

        .ledger-mini { width: 100%; border-collapse: collapse; font-size: 8pt; }
        .ledger-mini td { padding: 0.15rem 0.3rem; border: none; border-bottom: 1px dotted #e5e7eb; }
        .ledger-mini .mini-detail { color: #333; }
        .ledger-mini .mini-amount { text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; white-space: nowrap; width: 1%; }
        .ledger-mini .mini-amount.gain { color: #047857; }
        .ledger-mini .mini-amount.loss { color: #b91c1c; }

        .ledger-table .subtotal-row td { padding: 0.25rem; background: #fef3c7; border-top: 2px solid #d97706; }
        .subtotal { display: flex; justify-content: space-between; font-size: 9pt; font-weight: 700; }
        .subtotal.gain { color: #047857; }
        .subtotal.loss { color: #b91c1c; }

        .ledger-net {
          margin-top: 0.5rem;
          padding: 0.5rem 0.8rem;
          border-radius: 0.4rem;
          display: flex; justify-content: space-between; align-items: center;
          font-size: 11pt; font-weight: 900;
          border: 2px solid;
        }
        .ledger-net.positive { background: #047857; color: #fff; border-color: #064e3b; }
        .ledger-net.negative { background: #b91c1c; color: #fff; border-color: #7f1d1d; }
        .ledger-net span { letter-spacing: 0.05em; }
        .ledger-net b { font-size: 16pt; }

        /* Per-player card */
        .player-header {
          display: grid; grid-template-columns: auto 1fr auto; gap: 1rem; align-items: center;
          background: #f9fafb; border: 1px solid #d1d5db; border-radius: 0.5rem;
          padding: 0.7rem 1rem; margin: 0.6rem 0;
        }
        .player-header .position { display: flex; flex-direction: column; align-items: center; min-width: 4rem; }
        .player-header .pos-num { font-size: 22pt; font-weight: 900; color: #047857; line-height: 1; }
        .player-header .medal-1, .player-header .medal-2, .player-header .medal-3 { font-size: 22pt; line-height: 1; }
        .player-header .player-name { font-size: 16pt; font-weight: 800; margin: 0; color: #111; }
        .player-header .player-meta { font-size: 9.5pt; color: #555; margin: 0.1rem 0 0 0; }
        .player-header .player-totals { display: flex; gap: 0.8rem; align-items: flex-end; }
        .player-header .player-totals > div { text-align: center; }
        .player-header .player-totals .lbl { display: block; font-size: 8pt; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }
        .player-header .player-totals .val { display: block; font-size: 15pt; font-weight: 800; color: #047857; line-height: 1; margin-top: 0.1rem; }

        /* Scorecard grid (result) */
        .result-grid { width: 100%; border-collapse: collapse; font-size: 9pt; margin-bottom: 0.4rem; }
        .result-grid th, .result-grid td { border: 1px solid #999; padding: 0.25rem 0.15rem; text-align: center; font-variant-numeric: tabular-nums; }
        .result-grid .row-label { background: #047857; color: #fff; font-weight: 700; text-align: left; padding-left: 0.4rem; min-width: 50px; }
        .result-grid .hole-num { background: #047857; color: #fff; font-weight: 700; width: 6%; }
        .result-grid .par-row td, .result-grid .si-row td { background: #f3f4f6; font-size: 8.5pt; color: #444; font-weight: 600; }
        .result-grid .tot-col { background: #fef3c7; font-weight: 700; }
        .result-grid .player-row .score-cell, .result-grid .net-row .score-cell-net, .result-grid .stab-row .score-cell-stab { background: #fff; font-weight: 600; }
        .result-grid .score-cell.eagle { background: #fbbf24; color: #78350f; font-weight: 900; }
        .result-grid .score-cell.birdie { background: #dcfce7; color: #047857; font-weight: 800; }
        .result-grid .score-cell.par { color: #111; }
        .result-grid .score-cell.bogey { color: #c2410c; }
        .result-grid .score-cell.over { background: #fef2f2; color: #b91c1c; }

        /* Performance grid */
        .perf-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.4rem; margin-bottom: 0.7rem; }
        .perf-cell { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 0.4rem; padding: 0.4rem; text-align: center; font-size: 9pt; }
        .perf-cell span { display: block; font-size: 8pt; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }
        .perf-cell b { display: block; font-size: 17pt; font-weight: 900; margin-top: 0.15rem; color: #047857; }
        .perf-eagle b { color: #d97706; }
        .perf-birdie b { color: #047857; }
        .perf-par b { color: #111; }
        .perf-bogey b { color: #c2410c; }
        .perf-over b { color: #b91c1c; }

        /* Signature */
        .signature-section { display: flex; gap: 2rem; margin-top: 0.8rem; }
        .signature-section .sig-block { flex: 1; text-align: center; }
        .signature-section .sig-line { border-bottom: 1.5px solid #444; margin-bottom: 0.2rem; height: 1.5rem; }
        .signature-section .sig-block p { margin: 0; font-size: 9pt; color: #555; }

        /* Print */
        @media print {
          body { background: #fff !important; }
          .no-print { display: none !important; }
          .print-area { background: #fff !important; }
          .tee-card { width: 100%; max-width: 100%; box-shadow: none; padding: 0.5in 0.6in; margin: 0; page-break-after: always; }
          .tee-card:last-child { page-break-after: auto; }
          @page { size: letter; margin: 0; }
        }
      `}</style>
    </>
  )
}
