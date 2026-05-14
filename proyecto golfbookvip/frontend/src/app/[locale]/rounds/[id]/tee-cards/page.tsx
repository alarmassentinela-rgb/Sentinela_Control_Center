'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Printer, ArrowLeft, Flag, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

// ── Types ───────────────────────────────────────────────────────────

interface CourseHole {
  hole_number: number
  par: number
  stroke_index: number | null
  distance_yards_black: number | null
  distance_yards_blue: number | null
  distance_yards_white: number | null
  distance_yards_red: number | null
}

interface TeeCardPlayer {
  player_id: string
  user_id: string
  name: string
  username: string
  handicap_index: number | null
  course_handicap: number | null
  tee_color: string | null
  is_group_scorer?: boolean
}

interface TeeGroup {
  group_number: number
  starting_hole: number | null
  players: TeeCardPlayer[]
  scorer_user_id?: string | null
}

interface Round {
  id: string
  name: string | null
  game_format: string
  holes_to_play: number
  scheduled_at: string
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

const TEE_COLOR_HEX: Record<string, { bg: string; label: string }> = {
  black:  { bg: '#000000', label: 'Negro' },
  blue:   { bg: '#1d4ed8', label: 'Azul' },
  white:  { bg: '#ffffff', label: 'Blanco' },
  red:    { bg: '#dc2626', label: 'Rojo' },
  gold:   { bg: '#ca8a04', label: 'Oro' },
}

function strokesReceived(courseHcp: number | null, holeSI: number | null): number {
  if (!courseHcp || !holeSI) return 0
  const base = Math.floor(courseHcp / 18)
  const extra = (courseHcp % 18) >= holeSI ? 1 : 0
  return base + extra
}

function distanceFor(hole: CourseHole, tee: string | null): number | null {
  switch (tee) {
    case 'black': return hole.distance_yards_black
    case 'blue':  return hole.distance_yards_blue
    case 'white': return hole.distance_yards_white
    case 'red':   return hole.distance_yards_red
    default:      return hole.distance_yards_white
  }
}

const FORMAT_LABEL: Record<string, string> = {
  stroke:               'Stroke Play',
  stableford:           'Stableford',
  stableford_modified:  'Stableford Modificado',
  match:                'Match Play',
  skins:                'Skins',
  florida:              'Florida',
}

function fmtDate(iso: string, locale: string) {
  const d = new Date(iso)
  return d.toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
}

// ── Master sheet (resumen) ──────────────────────────────────────────

function MasterSheet({ round, course, groups, locale }: { round: Round; course: Course; groups: TeeGroup[]; locale: string }) {
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  return (
    <div className="tee-card master-sheet">
      <header className="card-header">
        <div className="brand">⛳ GolfBookVIP</div>
        <div className="meta">{fmtDate(round.scheduled_at, locale)}</div>
      </header>
      <h1 className="tournament-name">{round.name ?? lbl('Ronda sin nombre', 'Untitled round')}</h1>
      <p className="course-line">
        {course.name}
        {course.city && ` · ${course.city}`}
        {course.state && `, ${course.state}`}
      </p>
      <p className="format-line">
        {FORMAT_LABEL[round.game_format] ?? round.game_format} ·{' '}
        {round.holes_to_play} {lbl('hoyos', 'holes')}
        {course.par_total && ` · Par ${course.par_total}`}
        {course.course_rating && ` · CR ${course.course_rating}`}
        {course.slope_rating && ` · Slope ${course.slope_rating}`}
      </p>
      <h2 className="section-title">{lbl('Hoja de salida', 'Tee sheet')}</h2>
      <table className="master-table">
        <thead>
          <tr>
            <th>{lbl('Grupo', 'Group')}</th>
            <th>{lbl('Hoyo', 'Hole')}</th>
            <th>{lbl('Jugadores', 'Players')}</th>
            <th>{lbl('Capturista', 'Scorer')}</th>
          </tr>
        </thead>
        <tbody>
          {groups.map(g => {
            const scorer = g.players.find(p => p.is_group_scorer)
            return (
              <tr key={g.group_number}>
                <td className="grp-cell">G{g.group_number}</td>
                <td className="hole-cell">H{g.starting_hole ?? 1}</td>
                <td>
                  {g.players.map(p => (
                    <div key={p.player_id} className="master-player">
                      <span className="name">{p.name}</span>
                      <span className="hcp">HCP {p.handicap_index?.toFixed(1) ?? '—'} · C-HCP {p.course_handicap ?? '—'}</span>
                    </div>
                  ))}
                </td>
                <td className="scorer-cell">{scorer ? scorer.name : '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="footer-note">
        {lbl('Generado por GolfBookVIP', 'Generated by GolfBookVIP')} · {new Date().toLocaleString(locale === 'es' ? 'es-MX' : 'en-US')}
      </p>
    </div>
  )
}

// ── Tarjeta individual por grupo ────────────────────────────────────

function GroupCard({ round, course, group, locale }: { round: Round; course: Course; group: TeeGroup; locale: string }) {
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const holes = course.holes.slice(0, round.holes_to_play)
  const front = holes.slice(0, 9)
  const back  = holes.slice(9, 18)
  const scorer = group.players.find(p => p.is_group_scorer)

  const sumPar = (hs: CourseHole[]) => hs.reduce((s, h) => s + (h.par ?? 0), 0)

  return (
    <div className="tee-card group-card">
      <header className="card-header">
        <div className="brand">⛳ GolfBookVIP</div>
        <div className="meta">{fmtDate(round.scheduled_at, locale)}</div>
      </header>
      <h1 className="tournament-name">{round.name ?? lbl('Ronda sin nombre', 'Untitled round')}</h1>
      <p className="course-line">
        {course.name}
        {course.city && ` · ${course.city}`}
        {course.state && `, ${course.state}`}
      </p>
      <p className="format-line">
        {FORMAT_LABEL[round.game_format] ?? round.game_format} · {round.holes_to_play} {lbl('hoyos', 'holes')}
        {course.par_total && ` · Par ${course.par_total}`}
      </p>

      <div className="group-banner">
        <div className="group-num">{lbl('GRUPO', 'GROUP')} {group.group_number}</div>
        <div className="start-hole">{lbl('Salida', 'Start')}: {lbl('Hoyo', 'Hole')} {group.starting_hole ?? 1}</div>
      </div>
      {scorer && (
        <p className="scorer-line">🎯 {lbl('Capturista designado', 'Designated scorer')}: <b>{scorer.name}</b></p>
      )}

      {/* Tabla de jugadores */}
      <table className="players-table">
        <thead>
          <tr>
            <th>{lbl('Jugador', 'Player')}</th>
            <th>HCP</th>
            <th>C-HCP</th>
            <th>{lbl('Tee', 'Tee')}</th>
            <th>{lbl('Firma', 'Signature')}</th>
          </tr>
        </thead>
        <tbody>
          {group.players.map(p => {
            const tee = p.tee_color ?? 'white'
            const teeInfo = TEE_COLOR_HEX[tee]
            return (
              <tr key={p.player_id}>
                <td className="player-name">
                  {p.name}
                  {p.is_group_scorer && <span className="scorer-badge">🎯</span>}
                </td>
                <td className="num">{p.handicap_index?.toFixed(1) ?? '—'}</td>
                <td className="num">{p.course_handicap ?? '—'}</td>
                <td>
                  <span className="tee-dot" style={{ backgroundColor: teeInfo?.bg ?? '#fff', borderColor: tee === 'white' ? '#aaa' : teeInfo?.bg }} />
                  <span className="tee-label">{teeInfo?.label ?? tee}</span>
                </td>
                <td className="signature-line"></td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {/* Scorecard grid Front 9 */}
      <h3 className="section-title">{lbl('Tarjeta de anotación', 'Scorecard')}</h3>
      <ScorecardGrid label={lbl('Salida', 'Front')} holes={front} players={group.players} startHole={1} />
      {back.length > 0 && (
        <ScorecardGrid label={lbl('Vuelta', 'Back')} holes={back} players={group.players} startHole={10} />
      )}

      {/* Totales */}
      <table className="totals-table">
        <tbody>
          <tr>
            <td className="label">{lbl('Par salida', 'Par front')}</td>
            <td>{sumPar(front)}</td>
            {back.length > 0 && (<>
              <td className="label">{lbl('Par vuelta', 'Par back')}</td>
              <td>{sumPar(back)}</td>
              <td className="label">{lbl('Par total', 'Par total')}</td>
              <td>{sumPar(front) + sumPar(back)}</td>
            </>)}
          </tr>
        </tbody>
      </table>

      <div className="rules-line">
        <span className="label">{lbl('Reglas locales:', 'Local rules:')}</span>
        <span className="rule-blank">_________________________________________________</span>
      </div>

      <div className="signatures">
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

function ScorecardGrid({ label, holes, players, startHole }: { label: string; holes: CourseHole[]; players: TeeCardPlayer[]; startHole: number }) {
  void startHole // markup-only helper, startHole displayed via hole.hole_number
  const sumGross = (hs: CourseHole[]) => hs.reduce((s, h) => s + (h.par ?? 0), 0)
  return (
    <table className="scorecard-grid">
      <thead>
        <tr>
          <th className="row-label">{label}</th>
          {holes.map(h => <th key={h.hole_number} className="hole-num">{h.hole_number}</th>)}
          <th className="tot-col">TOT</th>
        </tr>
        <tr className="par-row">
          <th>Par</th>
          {holes.map(h => <td key={h.hole_number}>{h.par}</td>)}
          <td className="tot-col"><b>{sumGross(holes)}</b></td>
        </tr>
        <tr className="si-row">
          <th>SI</th>
          {holes.map(h => <td key={h.hole_number}>{h.stroke_index ?? '—'}</td>)}
          <td className="tot-col">—</td>
        </tr>
      </thead>
      <tbody>
        {players.map(p => (
          <tr key={p.player_id} className="player-row">
            <th className="row-label player-row-name">{p.name.split(' ')[0]}</th>
            {holes.map(h => {
              const strokes = strokesReceived(p.course_handicap, h.stroke_index)
              return (
                <td key={h.hole_number} className="score-cell">
                  {strokes > 0 && <span className="stroke-dot">{'•'.repeat(Math.min(2, strokes))}</span>}
                </td>
              )
            })}
            <td className="tot-col score-cell"></td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ── Main page ───────────────────────────────────────────────────────

export default function TeeCardsPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [round, setRound] = useState<Round | null>(null)
  const [course, setCourse] = useState<Course | null>(null)
  const [groups, setGroups] = useState<TeeGroup[]>([])
  const [view, setView] = useState<'cards' | 'master'>('cards')

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    const load = async () => {
      try {
        const rRes = await api.get(`/rounds/${id}`)
        setRound(rRes.data)
        const [cRes, tgRes] = await Promise.all([
          api.get(`/courses/${rRes.data.course_id}`),
          api.get(`/rounds/${id}/tee-groups`),
        ])
        setCourse(cRes.data)
        setGroups(tgRes.data.groups ?? [])
      } finally { setLoading(false) }
    }
    load()
  }, [id, locale, router])

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  if (!round || !course) return null

  if (groups.length === 0) return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 px-4">
      <p className="text-white font-bold">{lbl('Esta ronda aún no tiene grupos de salida configurados.', 'This round has no tee groups configured yet.')}</p>
      <Link href={`/${locale}/rounds/${id}`} className="text-emerald-400 underline">{lbl('Volver a la ronda', 'Back to round')}</Link>
    </div>
  )

  return (
    <>
      {/* Toolbar — no se imprime */}
      <div className="no-print bg-zinc-900 border-b border-zinc-800 sticky top-0 z-30 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-2">
          <Link href={`/${locale}/rounds/${id}`}
            className="text-zinc-400 hover:text-white transition-colors flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} />
            {lbl('Ronda', 'Round')}
          </Link>
          <div className="flex items-center gap-2">
            <div className="flex gap-1 bg-zinc-800 border border-zinc-700 rounded-lg p-0.5">
              <button onClick={() => setView('cards')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  view === 'cards' ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}>
                {lbl('Tarjetas', 'Cards')}
              </button>
              <button onClick={() => setView('master')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  view === 'master' ? 'bg-zinc-700 text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}>
                {lbl('Maestra', 'Master')}
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
            'Tip: al imprimir, usa "Más opciones" → desactivar encabezados/pies del navegador para una salida más limpia.',
            'Tip: in the print dialog, use "More settings" → disable browser headers/footers for a cleaner output.'
          )}
        </p>
      </div>

      {/* Contenido imprimible */}
      <main className="print-area bg-zinc-950 text-zinc-100">
        {view === 'master' ? (
          <MasterSheet round={round} course={course} groups={groups} locale={locale} />
        ) : (
          groups.map(g => (
            <GroupCard key={g.group_number} round={round} course={course} group={g} locale={locale} />
          ))
        )}
      </main>

      {/* Estilos */}
      <style jsx global>{`
        /* ── Pantalla: vista oscura previa, estilo "papel" centrado ── */
        .tee-card {
          background: #fff;
          color: #111;
          margin: 1.5rem auto;
          padding: 1.5rem 2rem;
          width: 8.5in;
          max-width: 100%;
          box-shadow: 0 2px 20px rgba(0,0,0,0.3);
          font-family: ui-sans-serif, system-ui, sans-serif;
          font-size: 11pt;
          line-height: 1.4;
        }
        .tee-card .card-header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          border-bottom: 2px solid #047857;
          padding-bottom: 0.4rem;
          margin-bottom: 0.7rem;
        }
        .tee-card .brand { font-weight: 800; color: #047857; font-size: 12pt; letter-spacing: 0.02em; }
        .tee-card .meta { color: #555; font-size: 10pt; }
        .tee-card .tournament-name { font-size: 22pt; font-weight: 900; margin: 0.2rem 0; letter-spacing: -0.02em; color: #111; }
        .tee-card .course-line { color: #444; font-size: 11pt; margin: 0; }
        .tee-card .format-line { color: #666; font-size: 9pt; margin: 0.15rem 0 1rem 0; font-style: italic; }

        .group-banner {
          background: #047857;
          color: #fff;
          padding: 0.7rem 1rem;
          border-radius: 0.5rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.6rem;
        }
        .group-banner .group-num { font-size: 16pt; font-weight: 900; letter-spacing: 0.04em; }
        .group-banner .start-hole { font-size: 13pt; font-weight: 700; }

        .scorer-line { font-size: 10pt; color: #444; margin: 0.2rem 0 0.6rem 0; }

        .players-table { width: 100%; border-collapse: collapse; margin-bottom: 0.7rem; font-size: 10pt; }
        .players-table th { background: #f3f4f6; color: #111; font-weight: 700; padding: 0.35rem 0.5rem; text-align: left; border: 1px solid #d1d5db; }
        .players-table td { padding: 0.4rem 0.5rem; border: 1px solid #e5e7eb; }
        .players-table .player-name { font-weight: 600; }
        .players-table .num { text-align: center; font-variant-numeric: tabular-nums; }
        .players-table .signature-line { background-image: repeating-linear-gradient(to right, #aaa 0, #aaa 4px, transparent 4px, transparent 8px); background-size: 100% 1px; background-position: 0 50%; background-repeat: no-repeat; min-width: 130px; }
        .players-table .scorer-badge { margin-left: 0.3rem; }
        .tee-dot { display: inline-block; width: 0.7rem; height: 0.7rem; border-radius: 50%; border: 1px solid #888; margin-right: 0.3rem; vertical-align: middle; }
        .tee-label { font-size: 9.5pt; color: #333; }

        .section-title { font-size: 11pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #047857; margin: 0.7rem 0 0.3rem 0; }

        .scorecard-grid { width: 100%; border-collapse: collapse; font-size: 9pt; margin-bottom: 0.4rem; }
        .scorecard-grid th, .scorecard-grid td { border: 1px solid #999; padding: 0.25rem 0.15rem; text-align: center; font-variant-numeric: tabular-nums; }
        .scorecard-grid .row-label { background: #047857; color: #fff; font-weight: 700; text-align: left; padding-left: 0.4rem; min-width: 60px; }
        .scorecard-grid .hole-num { background: #047857; color: #fff; font-weight: 700; width: 6%; }
        .scorecard-grid .par-row td, .scorecard-grid .si-row td { background: #f3f4f6; font-size: 8.5pt; color: #444; font-weight: 600; }
        .scorecard-grid .player-row .score-cell { height: 1.7rem; background: #fff; }
        .scorecard-grid .player-row-name { font-size: 9.5pt; }
        .scorecard-grid .tot-col { background: #fef3c7; font-weight: 700; }
        .scorecard-grid .stroke-dot { color: #dc2626; font-size: 12pt; font-weight: 900; line-height: 0.8; }

        .totals-table { width: 100%; border-collapse: collapse; margin-bottom: 0.7rem; font-size: 10pt; }
        .totals-table td { border: 1px solid #ccc; padding: 0.35rem 0.6rem; text-align: center; font-weight: 700; font-variant-numeric: tabular-nums; }
        .totals-table .label { background: #f3f4f6; font-weight: 600; text-align: left; }

        .rules-line { font-size: 9.5pt; color: #555; margin: 0.4rem 0; display: flex; gap: 0.5rem; align-items: baseline; }
        .rules-line .rule-blank { color: #bbb; letter-spacing: 0.05em; }

        .signatures { display: flex; gap: 2rem; margin-top: 1rem; }
        .signatures .sig-block { flex: 1; text-align: center; }
        .signatures .sig-line { border-bottom: 1.5px solid #444; margin-bottom: 0.2rem; height: 1.5rem; }
        .signatures .sig-block p { margin: 0; font-size: 9pt; color: #555; }

        .footer-note { font-size: 8pt; color: #888; text-align: center; margin-top: 1rem; }

        /* ── Master sheet ── */
        .master-table { width: 100%; border-collapse: collapse; font-size: 10pt; margin-top: 0.5rem; }
        .master-table th { background: #047857; color: #fff; padding: 0.5rem; text-align: left; }
        .master-table td { border: 1px solid #d1d5db; padding: 0.5rem; vertical-align: top; }
        .master-table .grp-cell { background: #fef3c7; font-weight: 900; font-size: 13pt; text-align: center; width: 4rem; }
        .master-table .hole-cell { background: #ecfdf5; font-weight: 700; text-align: center; width: 4rem; color: #047857; }
        .master-table .scorer-cell { color: #555; font-style: italic; width: 8rem; }
        .master-player { padding: 0.15rem 0; }
        .master-player .name { font-weight: 600; }
        .master-player .hcp { color: #666; margin-left: 0.4rem; font-size: 9pt; }

        /* ── Print ── */
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
