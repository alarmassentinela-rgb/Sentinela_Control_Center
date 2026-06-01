'use client'
import { useEffect, useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Loader2, Printer, Calendar, TrendingUp, TrendingDown, DollarSign, Trophy, AlertTriangle } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Breakdown {
  entry_fee: number
  nassau: number
  per_hole: number
  prizes: number
  penalties: number
  skins: number
  oyes: number
  total: number
}

interface HistoryItem {
  round_id: string
  round_name: string | null
  course_name: string | null
  course_city: string | null
  game_format: string
  scheduled_at: string
  finished_at: string | null
  breakdown: Breakdown
}

interface BigEvent { round_id: string; round_name: string | null; amount: number; date: string | null }

interface Summary {
  rounds_played: number
  rounds_won: number
  rounds_lost: number
  rounds_tied: number
  net_balance: number
  total_won: number
  total_paid: number
  biggest_win: BigEvent | null
  biggest_loss: BigEvent | null
  chart_monthly: { month: string; total: number }[]
  by_bet_type: { entry_fee: number; nassau: number; per_hole: number; prizes: number; penalties: number; skins: number; oyes: number }
}

const PRESETS = [
  { id: 'all', es: 'Todo', en: 'All time' },
  { id: 'month', es: 'Este mes', en: 'This month' },
  { id: 'lastmonth', es: 'Mes pasado', en: 'Last month' },
  { id: '3months', es: 'Últimos 3 meses', en: 'Last 3 months' },
  { id: 'year', es: 'Año actual', en: 'This year' },
  { id: 'custom', es: 'Personalizado', en: 'Custom' },
]

function presetToDates(preset: string): { start?: string; end?: string } {
  const now = new Date()
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  switch (preset) {
    case 'month': {
      const start = new Date(now.getFullYear(), now.getMonth(), 1)
      return { start: fmt(start), end: fmt(now) }
    }
    case 'lastmonth': {
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const end = new Date(now.getFullYear(), now.getMonth(), 0)
      return { start: fmt(start), end: fmt(end) }
    }
    case '3months': {
      const start = new Date(now.getFullYear(), now.getMonth() - 2, 1)
      return { start: fmt(start), end: fmt(now) }
    }
    case 'year': {
      const start = new Date(now.getFullYear(), 0, 1)
      return { start: fmt(start), end: fmt(now) }
    }
    default:
      return {}
  }
}

const FORMAT_LABEL: Record<string, string> = {
  stroke: 'Stroke', gran_premio: 'Gran Premio', stableford: 'Stableford', stableford_modified: 'Stab. Mod.',
  match: 'Match', skins: 'Skins', florida: 'Florida',
}

export default function FinancesPage() {
  const router = useRouter()
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<HistoryItem[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [preset, setPreset] = useState<string>('all')
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')

  const dates = useMemo(() => {
    if (preset === 'custom') {
      return { start: customStart || undefined, end: customEnd || undefined }
    }
    return presetToDates(preset)
  }, [preset, customStart, customEnd])

  const load = async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (dates.start) params.start_date = dates.start
      if (dates.end) params.end_date = dates.end
      const [histRes, sumRes] = await Promise.all([
        api.get('/users/me/balance-history', { params }),
        api.get('/users/me/balance-summary', { params }),
      ])
      setItems(histRes.data.items ?? [])
      setSummary(sumRes.data)
    } finally { setLoading(false) }
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dates.start, dates.end, locale, router])

  const handlePrint = () => {
    const params = new URLSearchParams()
    if (dates.start) params.set('start', dates.start)
    if (dates.end) params.set('end', dates.end)
    params.set('autoprint', 'true')
    window.open(`/${locale}/profile/finances/print?${params.toString()}`, '_blank', 'noopener')
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-4xl lg:max-w-6xl mx-auto flex items-center justify-between">
          <Link href={`/${locale}/profile`} className="text-zinc-400 hover:text-white transition-colors flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} />
            {lbl('Perfil', 'Profile')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <DollarSign size={15} className="text-emerald-400" />
            {lbl('Mi cuenta', 'My account')}
          </h1>
          <button onClick={handlePrint}
            className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-3 py-1.5 rounded-lg text-xs transition-colors">
            <Printer size={12} />
            {lbl('PDF', 'PDF')}
          </button>
        </div>
      </header>

      <main className="max-w-4xl lg:max-w-6xl mx-auto px-4 py-5 space-y-5">
        {/* Filtros de fecha */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Calendar size={14} className="text-zinc-500" />
            <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{lbl('Período', 'Period')}</h2>
          </div>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {PRESETS.map(p => (
              <button key={p.id} onClick={() => setPreset(p.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  preset === p.id ? 'bg-emerald-500 text-white' : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
                }`}>
                {locale === 'es' ? p.es : p.en}
              </button>
            ))}
          </div>
          {preset === 'custom' && (
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">{lbl('Desde', 'From')}</label>
                <input type="date" value={customStart} onChange={e => setCustomStart(e.target.value)}
                  className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-zinc-200 text-xs" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">{lbl('Hasta', 'To')}</label>
                <input type="date" value={customEnd} onChange={e => setCustomEnd(e.target.value)}
                  className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-zinc-200 text-xs" />
              </div>
            </div>
          )}
        </div>

        {/* RESUMEN */}
        {summary && (
          <>
            {/* Banner balance neto */}
            <div className={`rounded-2xl p-5 border-2 ${
              summary.net_balance > 0
                ? 'bg-emerald-500/10 border-emerald-500/40'
                : summary.net_balance < 0
                  ? 'bg-red-500/10 border-red-500/40'
                  : 'bg-zinc-800 border-zinc-700'
            }`}>
              <p className="text-xs text-zinc-400 uppercase tracking-wider font-bold mb-1">
                {lbl('Balance neto del período', 'Net balance for period')}
              </p>
              <p className={`text-5xl font-black tabular-nums ${
                summary.net_balance > 0 ? 'text-emerald-300' : summary.net_balance < 0 ? 'text-red-300' : 'text-zinc-300'
              }`}>
                {summary.net_balance >= 0 ? '+' : '−'}${Math.abs(summary.net_balance).toFixed(2)}
              </p>
              <p className="text-xs text-zinc-500 mt-1">
                {lbl(`${summary.rounds_played} rondas`, `${summary.rounds_played} rounds`)}
              </p>
            </div>

            {/* Stats cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <StatCard icon="🏆" label={lbl('Ganadas', 'Won')} value={summary.rounds_won} color="text-emerald-400" />
              <StatCard icon="❌" label={lbl('Perdidas', 'Lost')} value={summary.rounds_lost} color="text-red-400" />
              <StatCard icon="⚖️" label={lbl('Empate', 'Tied')} value={summary.rounds_tied} color="text-zinc-400" />
              <StatCard icon="🎯" label={lbl('Rondas', 'Rounds')} value={summary.rounds_played} color="text-blue-400" />
              <StatCard icon="📈" label={lbl('Total ganado', 'Total won')} value={`+$${summary.total_won.toFixed(2)}`} color="text-emerald-300" />
              <StatCard icon="📉" label={lbl('Total pagado', 'Total paid')} value={`−$${Math.abs(summary.total_paid).toFixed(2)}`} color="text-red-300" />
              {summary.biggest_win && (
                <StatCard icon="⭐" label={lbl('Mejor jugada', 'Best round')}
                  value={`+$${summary.biggest_win.amount.toFixed(2)}`}
                  sublabel={summary.biggest_win.round_name ?? ''} color="text-yellow-400" />
              )}
              {summary.biggest_loss && (
                <StatCard icon="⚠️" label={lbl('Peor jugada', 'Worst round')}
                  value={`−$${Math.abs(summary.biggest_loss.amount).toFixed(2)}`}
                  sublabel={summary.biggest_loss.round_name ?? ''} color="text-orange-400" />
              )}
            </div>

            {/* Gráfica mensual */}
            {summary.chart_monthly.length > 0 && (
              <MonthlyChart data={summary.chart_monthly} locale={locale} lbl={lbl} />
            )}

            {/* Desglose por tipo de apuesta */}
            {Object.values(summary.by_bet_type).some(v => Math.abs(v) > 0.01) && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
                <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
                  {lbl('Por tipo de apuesta — acumulado del período', 'By bet type — period accumulated')}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                  <BetTypeStat icon="🎫" label="Entry Fee" value={summary.by_bet_type.entry_fee} />
                  <BetTypeStat icon="🎯" label="Nassau" value={summary.by_bet_type.nassau} />
                  <BetTypeStat icon="⛳" label={lbl('Por hoyo', 'Per hole')} value={summary.by_bet_type.per_hole} />
                  <BetTypeStat icon="🏅" label={lbl('Premios', 'Prizes')} value={summary.by_bet_type.prizes} />
                  <BetTypeStat icon="⚠️" label={lbl('Castigos', 'Penalties')} value={summary.by_bet_type.penalties} />
                  <BetTypeStat icon="💎" label="Skines" value={summary.by_bet_type.skins} />
                  {Math.abs(summary.by_bet_type.oyes) > 0.01 && (
                    <BetTypeStat icon="🎲" label="Oyes" value={summary.by_bet_type.oyes} />
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* HISTORIAL POR JUGADA */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
            <h2 className="font-semibold text-white text-sm flex items-center gap-2">
              <TrendingUp size={14} className="text-emerald-400" />
              {lbl('Historial por jugada', 'Round history')}
            </h2>
            <span className="text-[10px] text-zinc-500">
              {lbl(`${items.length} rondas`, `${items.length} rounds`)}
            </span>
          </div>
          {items.length === 0 ? (
            <div className="px-4 py-8 text-center text-zinc-500 text-sm">
              {lbl('Sin movimientos en este período', 'No movements in this period')}
            </div>
          ) : (
            <div className="divide-y divide-zinc-800/40">
              {items.map(it => {
                const t = it.breakdown.total
                const date = it.finished_at ? new Date(it.finished_at).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'
                return (
                  <Link key={it.round_id} href={`/${locale}/rounds/${it.round_id}`}
                    className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-zinc-800/30 transition-colors">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-zinc-200 truncate">{it.round_name ?? lbl('Sin nombre', 'Unnamed')}</p>
                      <p className="text-[10px] text-zinc-500">
                        {date} · {it.course_name ?? '—'} · {FORMAT_LABEL[it.game_format] ?? it.game_format}
                      </p>
                    </div>
                    <span className={`text-base font-bold tabular-nums flex-shrink-0 ${
                      t > 0.01 ? 'text-emerald-400' : t < -0.01 ? 'text-red-400' : 'text-zinc-500'
                    }`}>
                      {t >= 0 ? '+' : '−'}${Math.abs(t).toFixed(2)}
                    </span>
                  </Link>
                )
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function StatCard({ icon, label, value, sublabel, color }: { icon: string; label: string; value: number | string; sublabel?: string; color: string }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">{icon}</span>
        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sublabel && <p className="text-[10px] text-zinc-500 truncate mt-0.5">{sublabel}</p>}
    </div>
  )
}

function BetTypeStat({ icon, label, value }: { icon: string; label: string; value: number }) {
  const cls = Math.abs(value) < 0.01 ? 'text-zinc-500' : value > 0 ? 'text-emerald-400' : 'text-red-400'
  return (
    <div className="bg-zinc-800/40 border border-zinc-800 rounded-lg p-2">
      <div className="flex items-center gap-1.5">
        <span>{icon}</span>
        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold flex-1 truncate">{label}</span>
      </div>
      <p className={`text-base font-bold tabular-nums ${cls}`}>
        {value >= 0 ? '+' : '−'}${Math.abs(value).toFixed(2)}
      </p>
    </div>
  )
}

function MonthlyChart({ data, locale, lbl }: { data: { month: string; total: number }[]; locale: string; lbl: (es: string, en: string) => string }) {
  if (data.length === 0) return null
  const max = Math.max(...data.map(d => Math.abs(d.total)), 1)
  const monthLabel = (key: string) => {
    const [y, m] = key.split('-')
    const d = new Date(parseInt(y), parseInt(m) - 1, 1)
    return d.toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { month: 'short' })
  }
  const yearLabel = (key: string) => key.slice(2, 4)  // "26" de "2026-05"

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
      <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-4">
        {lbl('Balance por mes', 'Balance per month')}
      </h3>
      <div className="overflow-x-auto pb-2">
        <div className="flex items-stretch gap-3 min-w-fit" style={{ minHeight: '200px' }}>
          {data.map(d => {
            const heightPct = (Math.abs(d.total) / max) * 100  // 0-100% del medio container
            const isPositive = d.total >= 0
            return (
              <div key={d.month} className="flex flex-col items-center w-16 flex-shrink-0">
                {/* Half top — positivos crecen aquí (hacia arriba) */}
                <div className="w-full flex flex-col items-center justify-end" style={{ height: '90px' }}>
                  {isPositive && (
                    <>
                      <span className="text-[10px] font-bold text-emerald-400 tabular-nums leading-none mb-1">
                        +${Math.abs(d.total).toFixed(0)}
                      </span>
                      <div className="w-10 bg-gradient-to-t from-emerald-500 to-emerald-400 rounded-t-md transition-all"
                        style={{ height: `${Math.max(2, heightPct)}%` }} />
                    </>
                  )}
                </div>
                {/* Línea cero */}
                <div className="w-full h-px bg-zinc-600" />
                {/* Half bottom — negativos crecen aquí (hacia abajo) */}
                <div className="w-full flex flex-col items-center justify-start" style={{ height: '90px' }}>
                  {!isPositive && Math.abs(d.total) > 0.01 && (
                    <>
                      <div className="w-10 bg-gradient-to-b from-red-500 to-red-600 rounded-b-md transition-all"
                        style={{ height: `${Math.max(2, heightPct)}%` }} />
                      <span className="text-[10px] font-bold text-red-400 tabular-nums leading-none mt-1">
                        −${Math.abs(d.total).toFixed(0)}
                      </span>
                    </>
                  )}
                </div>
                <span className="text-[11px] text-zinc-400 font-medium mt-1 capitalize">
                  {monthLabel(d.month)} <span className="text-zinc-600">'{yearLabel(d.month)}</span>
                </span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="flex items-center gap-4 mt-3 text-[10px] text-zinc-500">
        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-emerald-500 rounded-sm" /> {lbl('Ganaste', 'Won')}</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-500 rounded-sm" /> {lbl('Perdiste', 'Lost')}</span>
      </div>
    </div>
  )
}
