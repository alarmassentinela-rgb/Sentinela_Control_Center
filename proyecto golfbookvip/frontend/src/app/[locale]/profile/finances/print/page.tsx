'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Breakdown {
  entry_fee: number; nassau: number; per_hole: number; prizes: number;
  penalties: number; skins: number; oyes: number; total: number
}
interface HistoryItem {
  round_id: string; round_name: string | null; course_name: string | null
  course_city: string | null; game_format: string
  scheduled_at: string; finished_at: string | null; breakdown: Breakdown
}
interface BigEvent { round_id: string; round_name: string | null; amount: number; date: string | null }
interface Summary {
  rounds_played: number; rounds_won: number; rounds_lost: number; rounds_tied: number
  net_balance: number; total_won: number; total_paid: number
  biggest_win: BigEvent | null; biggest_loss: BigEvent | null
  chart_monthly: { month: string; total: number }[]
  by_bet_type: { entry_fee: number; nassau: number; per_hole: number; prizes: number; penalties: number; skins: number; oyes: number }
}
interface MeUser { first_name: string; last_name: string; email: string; username: string }

const FORMAT_LABEL: Record<string, string> = {
  stroke: 'Stroke Play', gran_premio: 'Gran Premio', stableford: 'Stableford', stableford_modified: 'Stableford Mod.',
  match: 'Match Play', skins: 'Skins', florida: 'Florida',
}

function fmtMoney(v: number): string {
  return `${v >= 0 ? '+' : '−'}$${Math.abs(v).toFixed(2)}`
}

export default function FinancesPrintPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center"><Loader2 size={28} className="animate-spin text-emerald-500" /></div>}>
      <PrintContent />
    </Suspense>
  )
}

function PrintContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const start = searchParams.get('start')
  const end = searchParams.get('end')
  const autoprint = searchParams.get('autoprint') === 'true'

  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<HistoryItem[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [user, setUser] = useState<MeUser | null>(null)

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    const load = async () => {
      try {
        const params: Record<string, string> = {}
        if (start) params.start_date = start
        if (end) params.end_date = end
        const [meRes, histRes, sumRes] = await Promise.all([
          api.get('/users/me'),
          api.get('/users/me/balance-history', { params }),
          api.get('/users/me/balance-summary', { params }),
        ])
        setUser(meRes.data)
        setItems(histRes.data.items ?? [])
        setSummary(sumRes.data)
      } finally { setLoading(false) }
    }
    load()
  }, [start, end, locale, router])

  useEffect(() => {
    if (autoprint && !loading && summary && user) {
      const t = setTimeout(() => window.print(), 600)
      return () => clearTimeout(t)
    }
  }, [autoprint, loading, summary, user])

  if (loading) return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  if (!user || !summary) return null

  const periodLabel = (() => {
    if (!start && !end) return lbl('Todo el período', 'All time')
    const fmt = (iso: string) => new Date(iso + 'T00:00').toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { day: 'numeric', month: 'long', year: 'numeric' })
    if (start && end) return `${fmt(start)} — ${fmt(end)}`
    if (start) return lbl(`Desde ${fmt(start)}`, `From ${fmt(start)}`)
    if (end) return lbl(`Hasta ${fmt(end)}`, `Until ${fmt(end)}`)
    return ''
  })()

  const monthLabel = (key: string) => {
    const [y, m] = key.split('-')
    const d = new Date(parseInt(y), parseInt(m) - 1, 1)
    return d.toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { month: 'short', year: '2-digit' })
  }

  // Chart sizing
  const chartMax = summary.chart_monthly.length > 0
    ? Math.max(...summary.chart_monthly.map(d => Math.abs(d.total)), 1) : 1
  const chartW = 700
  const chartH = 120

  return (
    <>
      <main className="finances-print">
        {/* HEADER */}
        <header className="fp-header">
          <div className="brand">⛳ GolfBookVIP</div>
          <div className="meta">
            {new Date().toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </div>
        </header>
        <h1 className="fp-title">{lbl('Estado de cuenta', 'Account statement')}</h1>
        <p className="fp-account">
          <b>{user.first_name} {user.last_name}</b> · @{user.username} · {user.email}
        </p>
        <p className="fp-period">{lbl('Período', 'Period')}: <b>{periodLabel}</b></p>

        {/* BALANCE BANNER */}
        <div className={`fp-balance-banner ${summary.net_balance >= 0 ? 'positive' : 'negative'}`}>
          <div className="label">{lbl('Balance neto del período', 'Net balance for period')}</div>
          <div className="amount">{fmtMoney(summary.net_balance)}</div>
          <div className="sub">{summary.rounds_played} {lbl('rondas jugadas', 'rounds played')}</div>
        </div>

        {/* STATS GRID */}
        <section className="fp-section">
          <h2 className="fp-h2">{lbl('Resumen', 'Summary')}</h2>
          <table className="fp-stats">
            <tbody>
              <tr>
                <td><span className="ic">🏆</span> {lbl('Rondas ganadas', 'Rounds won')}</td>
                <td className="num positive">{summary.rounds_won}</td>
                <td><span className="ic">📈</span> {lbl('Total ganado', 'Total won')}</td>
                <td className="num positive">{fmtMoney(summary.total_won)}</td>
              </tr>
              <tr>
                <td><span className="ic">❌</span> {lbl('Rondas perdidas', 'Rounds lost')}</td>
                <td className="num negative">{summary.rounds_lost}</td>
                <td><span className="ic">📉</span> {lbl('Total pagado', 'Total paid')}</td>
                <td className="num negative">{fmtMoney(summary.total_paid)}</td>
              </tr>
              <tr>
                <td><span className="ic">⚖️</span> {lbl('Empates', 'Ties')}</td>
                <td className="num">{summary.rounds_tied}</td>
                <td><span className="ic">🎯</span> {lbl('Total rondas', 'Total rounds')}</td>
                <td className="num">{summary.rounds_played}</td>
              </tr>
              {summary.biggest_win && (
                <tr>
                  <td><span className="ic">⭐</span> {lbl('Mejor jugada', 'Best round')}</td>
                  <td className="num positive">{fmtMoney(summary.biggest_win.amount)}</td>
                  <td colSpan={2} className="detail">{summary.biggest_win.round_name ?? '—'}</td>
                </tr>
              )}
              {summary.biggest_loss && (
                <tr>
                  <td><span className="ic">⚠️</span> {lbl('Peor jugada', 'Worst round')}</td>
                  <td className="num negative">{fmtMoney(summary.biggest_loss.amount)}</td>
                  <td colSpan={2} className="detail">{summary.biggest_loss.round_name ?? '—'}</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        {/* CHART */}
        {summary.chart_monthly.length > 0 && (
          <section className="fp-section">
            <h2 className="fp-h2">{lbl('Balance por mes', 'Balance per month')}</h2>
            <svg viewBox={`0 0 ${chartW} ${chartH + 20}`} className="fp-chart" preserveAspectRatio="xMidYMid meet">
              {/* línea cero */}
              <line x1="20" y1={chartH / 2} x2={chartW - 10} y2={chartH / 2} stroke="#444" strokeWidth="0.5" strokeDasharray="3,2" />
              {summary.chart_monthly.map((d, i) => {
                const barW = (chartW - 30) / summary.chart_monthly.length * 0.7
                const x = 20 + i * ((chartW - 30) / summary.chart_monthly.length)
                const h = (Math.abs(d.total) / chartMax) * (chartH / 2 - 5)
                const y = d.total >= 0 ? chartH / 2 - h : chartH / 2
                const color = d.total > 0 ? '#047857' : '#b91c1c'
                return (
                  <g key={d.month}>
                    <rect x={x} y={y} width={barW} height={h} fill={color} rx="2" />
                    <text x={x + barW / 2} y={chartH + 12} fontSize="9" fill="#333" textAnchor="middle">
                      {monthLabel(d.month)}
                    </text>
                    <text x={x + barW / 2} y={d.total >= 0 ? y - 2 : y + h + 8} fontSize="8" fill={color} textAnchor="middle" fontWeight="bold">
                      {fmtMoney(d.total)}
                    </text>
                  </g>
                )
              })}
            </svg>
          </section>
        )}

        {/* DESGLOSE POR APUESTA */}
        {Object.values(summary.by_bet_type).some(v => Math.abs(v) > 0.01) && (
          <section className="fp-section">
            <h2 className="fp-h2">{lbl('Acumulado por tipo de apuesta', 'Accumulated by bet type')}</h2>
            <table className="fp-bet-types">
              <thead>
                <tr>
                  <th>{lbl('Tipo', 'Type')}</th>
                  <th>{lbl('Balance', 'Balance')}</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>🎫 Entry Fee</td><td className={`num ${summary.by_bet_type.entry_fee > 0 ? 'positive' : summary.by_bet_type.entry_fee < 0 ? 'negative' : ''}`}>{fmtMoney(summary.by_bet_type.entry_fee)}</td></tr>
                <tr><td>🎯 Nassau</td><td className={`num ${summary.by_bet_type.nassau > 0 ? 'positive' : summary.by_bet_type.nassau < 0 ? 'negative' : ''}`}>{fmtMoney(summary.by_bet_type.nassau)}</td></tr>
                <tr><td>⛳ {lbl('Por hoyo', 'Per hole')}</td><td className={`num ${summary.by_bet_type.per_hole > 0 ? 'positive' : summary.by_bet_type.per_hole < 0 ? 'negative' : ''}`}>{fmtMoney(summary.by_bet_type.per_hole)}</td></tr>
                <tr><td>🏅 {lbl('Premios', 'Prizes')}</td><td className={`num ${summary.by_bet_type.prizes > 0 ? 'positive' : summary.by_bet_type.prizes < 0 ? 'negative' : ''}`}>{fmtMoney(summary.by_bet_type.prizes)}</td></tr>
                <tr><td>⚠️ {lbl('Castigos', 'Penalties')}</td><td className={`num ${summary.by_bet_type.penalties > 0 ? 'positive' : summary.by_bet_type.penalties < 0 ? 'negative' : ''}`}>{fmtMoney(summary.by_bet_type.penalties)}</td></tr>
                <tr><td>💎 Skines</td><td className={`num ${summary.by_bet_type.skins > 0 ? 'positive' : summary.by_bet_type.skins < 0 ? 'negative' : ''}`}>{fmtMoney(summary.by_bet_type.skins)}</td></tr>
                {Math.abs(summary.by_bet_type.oyes) > 0.01 && (
                  <tr><td>🎲 Oyes</td><td className={`num ${summary.by_bet_type.oyes > 0 ? 'positive' : 'negative'}`}>{fmtMoney(summary.by_bet_type.oyes)}</td></tr>
                )}
                <tr className="total-row">
                  <td><b>TOTAL</b></td>
                  <td className={`num ${summary.net_balance > 0 ? 'positive' : summary.net_balance < 0 ? 'negative' : ''}`}><b>{fmtMoney(summary.net_balance)}</b></td>
                </tr>
              </tbody>
            </table>
          </section>
        )}

        {/* HISTORIAL POR JUGADA */}
        <section className="fp-section">
          <h2 className="fp-h2">{lbl('Historial por jugada', 'Round history')}</h2>
          {items.length === 0 ? (
            <p className="fp-empty">{lbl('Sin movimientos en este período.', 'No movements in this period.')}</p>
          ) : (
            <table className="fp-history">
              <thead>
                <tr>
                  <th>{lbl('Fecha', 'Date')}</th>
                  <th>{lbl('Torneo / Curso', 'Tournament / Course')}</th>
                  <th>{lbl('Formato', 'Format')}</th>
                  <th>{lbl('Balance', 'Balance')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map(it => {
                  const date = it.finished_at ? new Date(it.finished_at).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'
                  const t = it.breakdown.total
                  return (
                    <tr key={it.round_id}>
                      <td>{date}</td>
                      <td>
                        <b>{it.round_name ?? '—'}</b>
                        {it.course_name && <span className="course"> · {it.course_name}{it.course_city && `, ${it.course_city}`}</span>}
                      </td>
                      <td>{FORMAT_LABEL[it.game_format] ?? it.game_format}</td>
                      <td className={`num ${t > 0.01 ? 'positive' : t < -0.01 ? 'negative' : ''}`}>
                        <b>{fmtMoney(t)}</b>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3} className="tf-label"><b>BALANCE TOTAL DEL PERÍODO</b></td>
                  <td className={`num ${summary.net_balance > 0 ? 'positive' : summary.net_balance < 0 ? 'negative' : ''}`}>
                    <b>{fmtMoney(summary.net_balance)}</b>
                  </td>
                </tr>
              </tfoot>
            </table>
          )}
        </section>

        {/* FOOTER */}
        <footer className="fp-footer">
          <p>{lbl('Generado por GolfBookVIP', 'Generated by GolfBookVIP')} · {new Date().toLocaleString(locale === 'es' ? 'es-MX' : 'en-US')}</p>
          <p className="confidential">{lbl('Documento personal — confidencial', 'Personal document — confidential')}</p>
        </footer>
      </main>

      <style jsx global>{`
        body { background: #fff !important; margin: 0; }
        .finances-print {
          background: #fff; color: #111;
          font-family: ui-sans-serif, system-ui, sans-serif;
          font-size: 10pt; line-height: 1.4;
          padding: 0.6in 0.7in;
          max-width: 8.5in;
          margin: 0 auto;
        }
        .fp-header {
          display: flex; justify-content: space-between; align-items: baseline;
          border-bottom: 2px solid #047857; padding-bottom: 0.5rem; margin-bottom: 0.7rem;
        }
        .fp-header .brand { font-weight: 800; color: #047857; font-size: 13pt; }
        .fp-header .meta { color: #555; font-size: 9pt; }
        .fp-title { font-size: 24pt; font-weight: 900; margin: 0.2rem 0 0.4rem 0; letter-spacing: -0.02em; }
        .fp-account { font-size: 11pt; color: #333; margin: 0; }
        .fp-period { font-size: 10pt; color: #555; margin: 0.2rem 0 1rem 0; }

        .fp-balance-banner {
          padding: 1rem 1.3rem; border-radius: 0.5rem; margin: 0.8rem 0;
          display: flex; align-items: baseline; justify-content: space-between; gap: 1rem;
        }
        .fp-balance-banner.positive { background: #047857; color: #fff; }
        .fp-balance-banner.negative { background: #b91c1c; color: #fff; }
        .fp-balance-banner .label { font-size: 9pt; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; opacity: 0.9; flex: 1; }
        .fp-balance-banner .amount { font-size: 26pt; font-weight: 900; letter-spacing: -0.02em; }
        .fp-balance-banner .sub { font-size: 9pt; opacity: 0.85; }

        .fp-section { margin: 0.9rem 0; break-inside: avoid; }
        .fp-h2 { font-size: 11pt; font-weight: 800; color: #047857; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #047857; padding-bottom: 0.2rem; margin: 0 0 0.4rem 0; }

        .fp-stats { width: 100%; border-collapse: collapse; font-size: 10pt; }
        .fp-stats td { padding: 0.3rem 0.5rem; border-bottom: 1px solid #e5e7eb; }
        .fp-stats td .ic { margin-right: 0.3rem; }
        .fp-stats td.num { text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; }
        .fp-stats td.detail { font-size: 9pt; color: #555; font-style: italic; }
        .fp-stats td.positive, .fp-bet-types td.positive, .fp-history td.positive { color: #047857; }
        .fp-stats td.negative, .fp-bet-types td.negative, .fp-history td.negative { color: #b91c1c; }

        .fp-chart { width: 100%; height: auto; max-height: 2.5in; }

        .fp-bet-types { width: 100%; border-collapse: collapse; font-size: 10pt; }
        .fp-bet-types th { background: #047857; color: #fff; padding: 0.35rem 0.5rem; text-align: left; }
        .fp-bet-types th:last-child { text-align: right; }
        .fp-bet-types td { padding: 0.3rem 0.5rem; border-bottom: 1px solid #e5e7eb; }
        .fp-bet-types td.num { text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; }
        .fp-bet-types .total-row td { border-top: 2px solid #047857; border-bottom: none; background: #f0fdf4; font-size: 11pt; padding: 0.5rem; }

        .fp-history { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
        .fp-history th { background: #047857; color: #fff; padding: 0.35rem 0.5rem; text-align: left; font-size: 9pt; }
        .fp-history th:last-child { text-align: right; }
        .fp-history td { padding: 0.3rem 0.5rem; border-bottom: 1px solid #e5e7eb; }
        .fp-history td .course { color: #666; font-size: 8.5pt; }
        .fp-history td.num { text-align: right; font-variant-numeric: tabular-nums; }
        .fp-history tfoot td { border-top: 2px solid #047857; padding: 0.5rem; background: #fef3c7; font-size: 11pt; }
        .fp-history tfoot td.tf-label { text-align: right; }
        .fp-empty { color: #666; font-style: italic; padding: 1rem 0; }

        .fp-footer { margin-top: 1.5rem; padding-top: 0.5rem; border-top: 1px solid #ccc; font-size: 8pt; color: #888; text-align: center; }
        .fp-footer .confidential { font-style: italic; margin-top: 0.2rem; }

        @media print {
          @page { size: letter; margin: 0; }
          .finances-print { padding: 0.5in 0.6in; max-width: 100%; }
        }
      `}</style>
    </>
  )
}
