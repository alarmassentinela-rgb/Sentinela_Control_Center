'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Flag, ArrowLeft, TrendingUp, Edit2, Save, X, Loader2,
  Award, Target, BarChart2, Star, AlertCircle, CheckCircle2,
  Crown, ChevronDown, ChevronUp, Crosshair, Circle
} from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'
import AleaCredit from '@/components/layout/AleaCredit'

// ─── Types ────────────────────────────────────────────────────────────────────

interface UserProfile {
  id: string
  first_name: string; last_name: string
  email: string; username: string
  phone: string | null; city: string | null; country: string | null
  handicap_index: number | null; initial_handicap: number | null
  created_at: string | null
  is_lifetime_member: boolean
}

interface Stats {
  total_rounds: number; total_holes: number
  avg_score: number | null
  avg_putts_per_round: number | null; avg_putts_per_hole: number | null
  fairways_hit_pct: number | null; gir_pct: number | null
  total_eagles: number; total_birdies: number
  total_pars: number; total_bogeys: number
  total_double_bogeys: number; total_worse: number
  total_hole_in_ones: number; total_three_putts: number
  best_score_18: number | null; best_score_9: number | null
  best_differential: number | null
  total_bet_won: number; total_bet_lost: number
}

interface HcpHistory {
  handicap_index: number; previous_index: number | null
  calculation_date: string; rounds_counted: number | null
}

interface RoundHistoryItem {
  round_id: string; name: string | null; course_name: string | null
  game_format: string; holes_to_play: number; played_at: string
  holes_played: number; total_gross: number; total_net: number
  total_putts: number; birdies: number; eagles: number
  bogeys: number; doubles: number; three_putts: number
  differential: number | null
}

// ─── HCP Trend SVG ────────────────────────────────────────────────────────────

function HcpTrendChart({ history, locale }: { history: HcpHistory[]; locale: string }) {
  if (history.length < 2) return null
  const pts = [...history].reverse() // oldest first
  const vals = pts.map(h => h.handicap_index)
  const minV = Math.min(...vals)
  const maxV = Math.max(...vals)
  const range = Math.max(maxV - minV, 1)
  const W = 400; const H = 80; const pad = 12

  const x = (i: number) => pad + (i / (pts.length - 1)) * (W - 2 * pad)
  const y = (v: number) => H - pad - ((v - minV) / range) * (H - 2 * pad)

  const points = pts.map((h, i) => `${x(i)},${y(h.handicap_index)}`).join(' ')
  const areaPoints = `${x(0)},${H} ${points} ${x(pts.length - 1)},${H}`

  const latest = vals[vals.length - 1]
  const trend = vals.length >= 2 ? latest - vals[vals.length - 2] : 0
  const color = trend <= 0 ? '#10b981' : '#f87171'

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-zinc-500">
          {locale === 'es' ? `Tendencia — últimas ${pts.length} actualizaciones` : `Trend — last ${pts.length} updates`}
        </p>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-zinc-600">{locale === 'es' ? 'Máx' : 'High'} {maxV.toFixed(1)}</span>
          <span className="text-zinc-600">{locale === 'es' ? 'Mín' : 'Low'} {minV.toFixed(1)}</span>
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-20" preserveAspectRatio="none">
        <defs>
          <linearGradient id="hcpGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={areaPoints} fill="url(#hcpGrad)" />
        <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        {/* First and last dot */}
        <circle cx={x(0)} cy={y(vals[0])} r="3" fill={color} opacity="0.5" />
        <circle cx={x(pts.length - 1)} cy={y(vals[vals.length - 1])} r="4" fill={color} />
      </svg>
      <div className="flex justify-between text-[10px] text-zinc-700 mt-1">
        <span>{new Date(pts[0].calculation_date).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { month: 'short', year: '2-digit' })}</span>
        <span>{new Date(pts[pts.length - 1].calculation_date).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { month: 'short', year: '2-digit' })}</span>
      </div>
    </div>
  )
}

// ─── Score Distribution Bar ────────────────────────────────────────────────────

function ScoreDistribution({ stats, locale }: { stats: Stats; locale: string }) {
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const total = stats.total_holes
  if (!total) return null

  const categories = [
    { key: 'eagles',  label: lbl('Eagle-', 'Eagle-'), count: stats.total_eagles + stats.total_hole_in_ones,  color: 'bg-yellow-400', text: 'text-yellow-400' },
    { key: 'birdies', label: 'Birdie',  count: stats.total_birdies,        color: 'bg-emerald-400', text: 'text-emerald-400' },
    { key: 'pars',    label: 'Par',     count: stats.total_pars,           color: 'bg-blue-400',    text: 'text-blue-400'    },
    { key: 'bogeys',  label: 'Bogey',   count: stats.total_bogeys,         color: 'bg-orange-400',  text: 'text-orange-400'  },
    { key: 'doubles', label: '+2',      count: stats.total_double_bogeys,  color: 'bg-red-400',     text: 'text-red-400'     },
    { key: 'worse',   label: '+3+',     count: stats.total_worse,          color: 'bg-red-700',     text: 'text-red-600'     },
  ].filter(c => c.count > 0)

  return (
    <div className="mt-5">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-3">
        {lbl('Distribución de scores', 'Score distribution')}
      </p>
      {/* Stacked bar */}
      <div className="flex rounded-lg overflow-hidden h-5 mb-3">
        {categories.map(c => (
          <div key={c.key}
            style={{ width: `${(c.count / total) * 100}%` }}
            className={`${c.color} transition-all`}
            title={`${c.label}: ${c.count} (${((c.count / total) * 100).toFixed(1)}%)`}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {categories.map(c => (
          <div key={c.key} className="flex items-center gap-1.5 text-xs">
            <span className={`w-2.5 h-2.5 rounded-sm ${c.color}`} />
            <span className="text-zinc-500">{c.label}</span>
            <span className={`font-semibold ${c.text}`}>{c.count}</span>
            <span className="text-zinc-700">({((c.count / total) * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const FORMAT_SHORT: Record<string, { es: string; en: string }> = {
  stroke:              { es: 'Stroke', en: 'Stroke' },
  stableford:          { es: 'Stab.',  en: 'Stab.'  },
  stableford_modified: { es: 'Stab.M', en: 'Stab.M' },
  match:               { es: 'Match',  en: 'Match'  },
  skins:               { es: 'Skins',  en: 'Skins'  },
  florida:             { es: 'Flor.',  en: 'Flor.'  },
}

export default function ProfilePage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [user, setUser]         = useState<UserProfile | null>(null)
  const [stats, setStats]       = useState<Stats | null>(null)
  const [history, setHistory]   = useState<HcpHistory[]>([])
  const [rounds, setRounds]     = useState<RoundHistoryItem[]>([])
  const [loading, setLoading]   = useState(true)
  const [editing, setEditing]   = useState(false)
  const [saving, setSaving]     = useState(false)
  const [showHistory, setShowHistory]   = useState(false)
  const [showRounds, setShowRounds]     = useState(false)
  const [hcpInitMode, setHcpInitMode]   = useState(false)
  const [hcpInitVal, setHcpInitVal]     = useState('')
  const [hcpSaving, setHcpSaving]       = useState(false)
  const [error, setError]       = useState('')
  const [form, setForm] = useState({ first_name: '', last_name: '', phone: '', city: '', country: '' })

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    Promise.all([
      api.get('/users/me'),
      api.get('/users/me/handicap-history').catch(() => ({ data: [] })),
      api.get('/users/me/stats').catch(() => ({ data: null })),
      api.get('/users/me/round-history').catch(() => ({ data: [] })),
    ]).then(([meRes, histRes, statsRes, roundsRes]) => {
      const u = meRes.data as UserProfile
      setUser(u)
      setForm({ first_name: u.first_name, last_name: u.last_name, phone: u.phone ?? '', city: u.city ?? '', country: u.country ?? '' })
      setHistory(histRes.data)
      if (statsRes.data) setStats(statsRes.data)
      setRounds(roundsRes.data)
    }).finally(() => setLoading(false))
  }, [locale, router])

  const handleSave = async () => {
    setSaving(true); setError('')
    try {
      const res = await api.patch('/users/me', {
        first_name: form.first_name, last_name: form.last_name,
        phone: form.phone || null, city: form.city || null, country: form.country || null,
      })
      setUser(res.data); setEditing(false)
    } catch { setError(lbl('Error al guardar', 'Save error')) }
    finally { setSaving(false) }
  }

  const handleHcpInit = async () => {
    const val = parseFloat(hcpInitVal)
    if (isNaN(val) || val < 0 || val > 54) { setError(lbl('Valor inválido (0–54)', 'Invalid value (0–54)')); return }
    setHcpSaving(true); setError('')
    try {
      const res = await api.post('/users/me/handicap-init', { initial_handicap: val })
      setUser(res.data); setHcpInitMode(false)
    } catch (e: unknown) { setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error') }
    finally { setHcpSaving(false) }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )
  if (!user) return null

  const memberSince = user.created_at
    ? new Date(user.created_at).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { month: 'long', year: 'numeric' })
    : '—'

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white transition-colors">
              <ArrowLeft size={20} />
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
                <Flag size={14} className="text-white" />
              </div>
              <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
            </div>
          </div>
          {!editing ? (
            <button onClick={() => setEditing(true)}
              className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors">
              <Edit2 size={15} />{lbl('Editar', 'Edit')}
            </button>
          ) : (
            <div className="flex gap-3">
              <button onClick={() => { setEditing(false); setError('') }}
                className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-white transition-colors">
                <X size={15} />{lbl('Cancelar', 'Cancel')}
              </button>
              <button onClick={handleSave} disabled={saving}
                className="flex items-center gap-1.5 text-sm text-emerald-400 hover:text-emerald-300 font-semibold transition-colors">
                {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
                {lbl('Guardar', 'Save')}
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-5">

        {/* ── Avatar + datos ── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <div className="flex items-center gap-4 mb-5">
            <div className="relative">
              <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-2xl font-bold text-emerald-400">
                {user.first_name.charAt(0)}{user.last_name.charAt(0)}
              </div>
              {user.is_lifetime_member && (
                <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-amber-400 flex items-center justify-center shadow-lg">
                  <Crown size={13} className="text-zinc-900" />
                </div>
              )}
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">{user.first_name} {user.last_name}</h1>
              <p className="text-sm text-zinc-500">@{user.username}</p>
              {user.is_lifetime_member ? (
                <span className="inline-flex items-center gap-1 mt-1 bg-gradient-to-r from-amber-500/20 to-yellow-400/20 border border-amber-400/40 text-amber-300 text-xs font-semibold px-2 py-0.5 rounded-full">
                  <Crown size={10} />{lbl('Miembro Fundador · Premium Vitalicio', 'Founding Member · Lifetime Premium')}
                </span>
              ) : (
                <p className="text-xs text-zinc-600 mt-0.5">{lbl('Miembro desde', 'Member since')} {memberSince}</p>
              )}
            </div>
          </div>

          {editing ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                {(['first_name', 'last_name'] as const).map(k => (
                  <div key={k}>
                    <label className="text-xs text-zinc-500 block mb-1">
                      {k === 'first_name' ? lbl('Nombre', 'First name') : lbl('Apellido', 'Last name')}
                    </label>
                    <input value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500" />
                  </div>
                ))}
              </div>
              {([['phone', lbl('Teléfono','Phone'), '+52 812 000 0000'], ['city', lbl('Ciudad','City'), 'Monterrey'], ['country', lbl('País','Country'), 'México']] as [keyof typeof form, string, string][]).map(([k, label, ph]) => (
                <div key={k}>
                  <label className="text-xs text-zinc-500 block mb-1">{label}</label>
                  <input value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}
                    placeholder={ph}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500" />
                </div>
              ))}
              {error && <p className="text-sm text-red-400">{error}</p>}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[[lbl('Email','Email'), user.email], [lbl('Teléfono','Phone'), user.phone ?? '—'], [lbl('Ciudad','City'), user.city ?? '—'], [lbl('País','Country'), user.country ?? '—']].map(([label, value]) => (
                <div key={label}>
                  <p className="text-xs text-zinc-600 mb-0.5">{label}</p>
                  <p className="text-zinc-300">{value}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Hándicap + Trend Chart ── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <TrendingUp size={16} className="text-emerald-400" />
              {lbl('Hándicap WHS', 'WHS Handicap')}
            </h2>
            {history.length > 0 && (
              <button onClick={() => setShowHistory(v => !v)}
                className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
                {lbl('Historial', 'History')}
                {showHistory ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
              </button>
            )}
          </div>

          {user.handicap_index !== null ? (
            <>
              <div className="flex items-end gap-3 mb-1">
                <span className="text-5xl font-bold text-emerald-400">{user.handicap_index.toFixed(1)}</span>
                {history.length > 0 && history[0].previous_index !== null && (
                  <span className={`text-sm mb-1 font-medium ${user.handicap_index < history[0].previous_index ? 'text-emerald-400' : 'text-red-400'}`}>
                    {user.handicap_index < history[0].previous_index
                      ? `↓ ${(history[0].previous_index - user.handicap_index).toFixed(1)}`
                      : `↑ ${(user.handicap_index - history[0].previous_index).toFixed(1)}`}
                  </span>
                )}
              </div>
              {history.length > 0 && (
                <p className="text-xs text-zinc-500 mb-1">
                  {lbl('Actualizado', 'Updated')} {new Date(history[0].calculation_date)
                    .toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { dateStyle: 'medium' })}
                  {stats?.best_differential != null && (
                    <span className="ml-3 text-zinc-600">{lbl('Mejor diferencial:', 'Best differential:')} <span className="text-yellow-400 font-semibold">{stats.best_differential.toFixed(1)}</span></span>
                  )}
                </p>
              )}

              {/* SVG Trend Chart */}
              <HcpTrendChart history={history} locale={locale} />

              {/* History list */}
              {showHistory && (
                <div className="border-t border-zinc-800 pt-3 mt-3 space-y-2">
                  {history.map((h, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="text-zinc-600 text-xs">
                        {new Date(h.calculation_date).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { dateStyle: 'medium' })}
                      </span>
                      <div className="flex items-center gap-3">
                        {h.previous_index !== null && <span className="text-zinc-600 text-xs">{h.previous_index.toFixed(1)}</span>}
                        <span className={`font-bold ${h.previous_index === null ? 'text-zinc-300' : h.handicap_index < h.previous_index ? 'text-emerald-400' : 'text-red-400'}`}>
                          {h.handicap_index.toFixed(1)}
                        </span>
                        {h.rounds_counted && <span className="text-zinc-700 text-xs">({h.rounds_counted})</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : hcpInitMode ? (
            <div className="space-y-3">
              <p className="text-sm text-zinc-400">{lbl('Ingresa tu hándicap índice actual (0.0 – 54.0)', 'Enter your current handicap index (0.0 – 54.0)')}</p>
              <div className="flex gap-2">
                <input type="number" step="0.1" min="0" max="54" value={hcpInitVal}
                  onChange={e => setHcpInitVal(e.target.value)} placeholder="18.5"
                  className="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500 text-sm" />
                <button onClick={handleHcpInit} disabled={hcpSaving}
                  className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold px-4 py-2.5 rounded-xl text-sm transition-colors">
                  {hcpSaving ? <Loader2 size={15} className="animate-spin"/> : <CheckCircle2 size={15}/>}
                  {lbl('Guardar', 'Save')}
                </button>
                <button onClick={() => { setHcpInitMode(false); setError('') }}
                  className="px-3 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded-xl text-sm transition-colors">
                  <X size={15}/>
                </button>
              </div>
              {error && <p className="text-sm text-red-400">{error}</p>}
            </div>
          ) : (
            <div className="flex items-start gap-3">
              <AlertCircle size={18} className="text-yellow-400 flex-shrink-0 mt-0.5"/>
              <div>
                <p className="text-sm text-zinc-300 mb-3">
                  {lbl('Aún no tienes hándicap. Juega 3 rondas o ingresa tu hándicap inicial.', 'No handicap yet. Play 3 rounds or enter your initial handicap.')}
                </p>
                <button onClick={() => setHcpInitMode(true)}
                  className="text-sm text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
                  {lbl('Ingresar hándicap inicial →', 'Enter initial handicap →')}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Estadísticas avanzadas ── */}
        {stats ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-5">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <BarChart2 size={16} className="text-emerald-400"/>
              {lbl('Estadísticas', 'Statistics')}
            </h2>

            {/* Main grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: lbl('Rondas', 'Rounds'),         value: String(stats.total_rounds),              icon: Target,    color: 'text-blue-400'    },
                { label: lbl('Mejor score', 'Best score'),value: String(stats.best_score_18 ?? '—'),       icon: Award,     color: 'text-yellow-400'  },
                { label: lbl('Score prom.', 'Avg score'), value: stats.avg_score?.toFixed(1) ?? '—',      icon: BarChart2, color: 'text-zinc-300'    },
                { label: lbl('Mejor 9H', 'Best 9H'),      value: String(stats.best_score_9 ?? '—'),        icon: Award,     color: 'text-blue-300'    },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="bg-zinc-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-zinc-500">{label}</span>
                    <Icon size={14} className={color}/>
                  </div>
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                </div>
              ))}
            </div>

            {/* Putting / course management */}
            <div>
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-3">
                {lbl('Gestión del campo', 'Course management')}
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: lbl('Putts/ronda', 'Putts/round'), value: stats.avg_putts_per_round?.toFixed(1) ?? '—', icon: Circle,    color: 'text-purple-400' },
                  { label: lbl('Putts/hoyo',  'Putts/hole'),  value: stats.avg_putts_per_hole?.toFixed(2)  ?? '—', icon: Circle,    color: 'text-purple-300' },
                  { label: 'GIR %',                            value: stats.gir_pct != null ? `${stats.gir_pct.toFixed(0)}%` : '—', icon: Crosshair, color: 'text-teal-400'   },
                  { label: lbl('3-Putts', '3-Putts'),          value: String(stats.total_three_putts),              icon: Circle,    color: 'text-red-400'    },
                ].map(({ label, value, icon: Icon, color }) => (
                  <div key={label} className="bg-zinc-800 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-zinc-500">{label}</span>
                      <Icon size={14} className={color}/>
                    </div>
                    <p className={`text-xl font-bold ${color}`}>{value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Score highlights */}
            <div>
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-3">
                {lbl('Highlights', 'Highlights')}
              </p>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Eagles+', value: stats.total_eagles + stats.total_hole_in_ones, color: 'text-yellow-400', icon: '⚡' },
                  { label: 'Birdies', value: stats.total_birdies,                           color: 'text-emerald-400', icon: '🐦' },
                  { label: lbl('Hoyo en 1', 'Hole in 1'), value: stats.total_hole_in_ones,  color: 'text-purple-400', icon: '⭐' },
                ].map(c => (
                  <div key={c.label} className="bg-zinc-800 rounded-xl p-4 text-center">
                    <p className="text-xl mb-1">{c.icon}</p>
                    <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">{c.label}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Score distribution */}
            <ScoreDistribution stats={stats} locale={locale} />

            {/* Bets */}
            {(stats.total_bet_won > 0 || stats.total_bet_lost > 0) && (
              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-zinc-800">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 text-center">
                  <p className="text-xs text-zinc-500 mb-1">{lbl('Ganado en apuestas', 'Bet won')}</p>
                  <p className="text-lg font-bold text-emerald-400">${stats.total_bet_won.toFixed(0)}</p>
                </div>
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-center">
                  <p className="text-xs text-zinc-500 mb-1">{lbl('Perdido en apuestas', 'Bet lost')}</p>
                  <p className="text-lg font-bold text-red-400">${stats.total_bet_lost.toFixed(0)}</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center">
            <BarChart2 size={28} className="text-zinc-700 mx-auto mb-2"/>
            <p className="text-sm text-zinc-500">{lbl('Juega rondas para ver tus estadísticas', 'Play rounds to see your stats')}</p>
          </div>
        )}

        {/* ── Mi cuenta / Historial financiero ── */}
        <Link href={`/${locale}/profile/finances`}
          className="block bg-gradient-to-br from-emerald-500/15 to-yellow-500/10 border border-emerald-500/30 hover:border-emerald-500/60 rounded-2xl px-5 py-4 transition-colors">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center flex-shrink-0">
              <span className="text-xl">💰</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-bold text-white text-sm">{lbl('Mi cuenta — Historial financiero', 'My account — Financial history')}</p>
              <p className="text-xs text-emerald-300/80 truncate">
                {lbl('Pérdidas y ganancias por jugada · estado de cuenta · gráfica · PDF', 'Gains & losses per round · statement · chart · PDF')}
              </p>
            </div>
            <ChevronDown size={16} className="text-emerald-400 -rotate-90 flex-shrink-0" />
          </div>
        </Link>

        {/* ── Historial de rondas ── */}
        {rounds.length > 0 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <button
              onClick={() => setShowRounds(v => !v)}
              className="w-full flex items-center justify-between px-5 py-4">
              <h2 className="font-semibold text-white flex items-center gap-2 text-sm">
                <Star size={15} className="text-emerald-400"/>
                {lbl('Historial de rondas', 'Round history')}
                <span className="text-xs text-zinc-600 font-normal">({rounds.length})</span>
              </h2>
              {showRounds ? <ChevronUp size={16} className="text-zinc-600"/> : <ChevronDown size={16} className="text-zinc-600"/>}
            </button>

            {showRounds && (
              <div className="border-t border-zinc-800">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[480px] text-xs">
                    <thead>
                      <tr className="border-b border-zinc-800">
                        <th className="text-left text-zinc-600 font-medium py-2 px-4">{lbl('Fecha', 'Date')}</th>
                        <th className="text-left text-zinc-600 font-medium py-2 px-2">{lbl('Cancha', 'Course')}</th>
                        <th className="text-center text-zinc-600 font-medium py-2 px-2">{lbl('Golpes', 'Gross')}</th>
                        <th className="text-center text-zinc-600 font-medium py-2 px-2">{lbl('Putts', 'Putts')}</th>
                        <th className="text-center text-emerald-600 font-medium py-2 px-2">Birdies</th>
                        <th className="text-center text-orange-600 font-medium py-2 px-2">Bogeys</th>
                        <th className="text-center text-zinc-600 font-medium py-2 px-2">Diff</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rounds.map(r => {
                        const fmt = FORMAT_SHORT[r.game_format]
                        return (
                          <tr key={r.round_id} className="border-t border-zinc-800/60 hover:bg-zinc-800/30 transition-colors">
                            <td className="py-2.5 px-4">
                              <Link href={`/${locale}/rounds/${r.round_id}`} className="hover:text-emerald-400 transition-colors">
                                <p className="text-zinc-300 font-medium">
                                  {new Date(r.played_at).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { month: 'short', day: 'numeric' })}
                                </p>
                                <p className="text-zinc-600">{locale === 'es' ? fmt?.es : fmt?.en} · {r.holes_to_play}H</p>
                              </Link>
                            </td>
                            <td className="py-2.5 px-2 text-zinc-500 max-w-[100px] truncate">
                              {r.course_name ?? r.name ?? '—'}
                            </td>
                            <td className="py-2.5 px-2 text-center font-bold text-white">
                              {r.total_gross > 0 ? r.total_gross : '—'}
                            </td>
                            <td className="py-2.5 px-2 text-center text-purple-400">
                              {r.total_putts > 0 ? r.total_putts : '—'}
                            </td>
                            <td className="py-2.5 px-2 text-center text-emerald-400 font-semibold">
                              {r.birdies > 0 ? r.birdies : <span className="text-zinc-700">0</span>}
                            </td>
                            <td className="py-2.5 px-2 text-center text-orange-400">
                              {r.bogeys > 0 ? r.bogeys : <span className="text-zinc-700">0</span>}
                            </td>
                            <td className="py-2.5 px-2 text-center">
                              {r.differential != null
                                ? <span className="text-yellow-400 font-semibold">{r.differential.toFixed(1)}</span>
                                : <span className="text-zinc-700">—</span>
                              }
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        <AleaCredit className="mt-0" />
      </main>
    </div>
  )
}
