'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Users, Flag, CheckCircle2, Clock, Play, BarChart2,
  TrendingUp, Trophy, Search, ChevronLeft, ChevronRight,
  ToggleLeft, ToggleRight, Loader2, RefreshCw, ShieldCheck,
  Activity, Hash,
} from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Stats {
  users: { total: number; new_7d: number; new_30d: number; active_30d: number; with_handicap: number }
  rounds: { total: number; scheduled: number; active: number; finished: number; new_7d: number; new_30d: number; by_format: { format: string; count: number }[] }
  scores: { total: number; differentials: number }
  participations: number
  courses_active: number
  generated_at: string
}

interface ChartPoint { day: string; count: number }

interface AdminUser {
  id: string; email: string; first_name: string; last_name: string
  username: string; handicap_index: number | null; is_active: boolean
  is_superadmin: boolean; created_at: string | null; last_login: string | null
}

interface AdminRound {
  id: string; name: string | null; game_format: string; status: string
  holes_to_play: number; player_count: number
  created_by_name: string; created_by_email: string
  scheduled_at: string; created_at: string | null
}

interface TopPlayer { user_id: string; name: string; username: string; handicap_index: number | null; rounds: number }

// ─── Helpers ──────────────────────────────────────────────────────────────────

const FORMAT_LABEL: Record<string, string> = {
  stroke: 'Stroke', stableford: 'Stableford', stableford_modified: 'Stab. Mod.',
  match: 'Match Play', skins: 'Skines', florida: 'Florida',
}

const STATUS_CLS: Record<string, string> = {
  scheduled: 'text-yellow-400 bg-yellow-400/10',
  active:    'text-emerald-400 bg-emerald-400/10',
  finished:  'text-zinc-400 bg-zinc-800',
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })
}

// ─── Mini sparkline (SVG) ─────────────────────────────────────────────────────

function Sparkline({ data, color = '#10b981' }: { data: ChartPoint[]; color?: string }) {
  if (data.length < 2) return null
  const vals = data.map(d => d.count)
  const max = Math.max(...vals, 1)
  const w = 200; const h = 40; const pad = 2
  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2)
    const y = h - pad - ((d.count / max) * (h - pad * 2))
    return `${x},${y}`
  }).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-10">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({
  label, value, sub, icon: Icon, color, chart, chartColor,
}: {
  label: string; value: number | string; sub?: string
  icon: React.ElementType; color: string; chart?: ChartPoint[]; chartColor?: string
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium mb-1">{label}</p>
          <p className={`text-3xl font-black ${color}`}>{value.toLocaleString()}</p>
          {sub && <p className="text-xs text-zinc-500 mt-0.5">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color.replace('text-', 'bg-').replace('-400', '-500/10').replace('-300', '-500/10')}`}>
          <Icon size={18} className={color} />
        </div>
      </div>
      {chart && chart.length > 1 && (
        <Sparkline data={chart} color={chartColor ?? '#10b981'} />
      )}
    </div>
  )
}

// ─── Bar chart for formats ────────────────────────────────────────────────────

function FormatBar({ data }: { data: { format: string; count: number }[] }) {
  if (!data.length) return null
  const max = Math.max(...data.map(d => d.count), 1)
  const colors = ['bg-emerald-500', 'bg-blue-500', 'bg-amber-500', 'bg-purple-500', 'bg-red-500', 'bg-cyan-500']
  return (
    <div className="space-y-2">
      {data.map((d, i) => (
        <div key={d.format} className="flex items-center gap-3">
          <span className="text-xs text-zinc-400 w-24 flex-shrink-0 truncate">{FORMAT_LABEL[d.format] ?? d.format}</span>
          <div className="flex-1 bg-zinc-800 rounded-full h-2">
            <div className={`h-2 rounded-full ${colors[i % colors.length]}`}
              style={{ width: `${(d.count / max) * 100}%` }} />
          </div>
          <span className="text-xs font-bold text-zinc-300 w-8 text-right">{d.count}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const locale = useLocale()
  const router = useRouter()

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [stats, setStats] = useState<Stats | null>(null)
  const [signupsChart, setSignupsChart] = useState<ChartPoint[]>([])
  const [roundsChart, setRoundsChart] = useState<ChartPoint[]>([])
  const [topPlayers, setTopPlayers] = useState<TopPlayer[]>([])

  // Users tab
  const [usersPage, setUsersPage] = useState(1)
  const [usersTotal, setUsersTotal] = useState(0)
  const [usersPages, setUsersPages] = useState(1)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [userSearch, setUserSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [togglingUser, setTogglingUser] = useState<string | null>(null)

  // Rounds tab
  const [roundsPage, setRoundsPage] = useState(1)
  const [roundsTotal, setRoundsTotal] = useState(0)
  const [roundsPages, setRoundsPages] = useState(1)
  const [rounds, setRounds] = useState<AdminRound[]>([])

  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'rounds'>('overview')
  const [refreshing, setRefreshing] = useState(false)

  const loadOverview = async () => {
    const [statsRes, signupsRes, roundsChtRes, topRes] = await Promise.all([
      api.get('/admin/stats'),
      api.get('/admin/signups-chart'),
      api.get('/admin/rounds-chart'),
      api.get('/admin/top-players'),
    ])
    setStats(statsRes.data)
    setSignupsChart(signupsRes.data)
    setRoundsChart(roundsChtRes.data)
    setTopPlayers(topRes.data)
  }

  const loadUsers = async (page = usersPage, q = userSearch) => {
    const res = await api.get(`/admin/users?page=${page}&q=${encodeURIComponent(q)}`)
    setUsers(res.data.users)
    setUsersTotal(res.data.total)
    setUsersPages(res.data.pages)
  }

  const loadRounds = async (page = roundsPage) => {
    const res = await api.get(`/admin/rounds?page=${page}`)
    setRounds(res.data.rounds)
    setRoundsTotal(res.data.total)
    setRoundsPages(res.data.pages)
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    const init = async () => {
      try {
        await loadOverview()
      } catch (e: unknown) {
        const status = (e as { response?: { status?: number } })?.response?.status
        if (status === 403) { setForbidden(true); return }
      } finally { setLoading(false) }
    }
    init()
  }, [])

  useEffect(() => { if (activeTab === 'users') loadUsers(usersPage, userSearch) }, [activeTab, usersPage, userSearch])
  useEffect(() => { if (activeTab === 'rounds') loadRounds(roundsPage) }, [activeTab, roundsPage])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      if (activeTab === 'overview') await loadOverview()
      else if (activeTab === 'users') await loadUsers()
      else await loadRounds()
    } finally { setRefreshing(false) }
  }

  const handleToggleUser = async (userId: string) => {
    setTogglingUser(userId)
    try {
      const res = await api.patch(`/admin/users/${userId}/toggle-active`)
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: res.data.is_active } : u))
    } finally { setTogglingUser(null) }
  }

  // ── Loading / forbidden ───────────────────────────────────────────────────

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  if (forbidden) return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 px-4">
      <ShieldCheck size={48} className="text-red-500/50" />
      <p className="text-white font-bold text-xl">Acceso denegado</p>
      <p className="text-zinc-500 text-sm">Solo superadministradores pueden ver esta página.</p>
      <button onClick={() => router.push(`/${locale}/dashboard`)}
        className="mt-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-5 py-2.5 rounded-xl text-sm transition-colors">
        Ir al Dashboard
      </button>
    </div>
  )

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-zinc-950">

      {/* Header */}
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
              <ShieldCheck size={15} className="text-emerald-400" />
            </div>
            <div>
              <h1 className="font-bold text-white text-sm">Super Admin</h1>
              <p className="text-xs text-zinc-500">GolfBookVIP</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleRefresh} disabled={refreshing}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white bg-zinc-800 hover:bg-zinc-700 px-3 py-1.5 rounded-lg transition-colors border border-zinc-700 disabled:opacity-50">
              <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
              Actualizar
            </button>
            {stats && (
              <span className="text-xs text-zinc-600 hidden sm:block">
                {fmtDate(stats.generated_at)}
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-5">

        {/* Tabs */}
        <div className="flex gap-1 bg-zinc-900 border border-zinc-800 rounded-xl p-1 w-fit">
          {(['overview', 'users', 'rounds'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
              }`}>
              {tab === 'overview' ? 'Resumen' : tab === 'users' ? `Usuarios${usersTotal ? ` (${usersTotal})` : ''}` : `Rondas${roundsTotal ? ` (${roundsTotal})` : ''}`}
            </button>
          ))}
        </div>

        {/* ── OVERVIEW TAB ──────────────────────────────────────────────── */}
        {activeTab === 'overview' && stats && (
          <>
            {/* Stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              <StatCard label="Usuarios total" value={stats.users.total}
                sub={`+${stats.users.new_7d} esta semana`}
                icon={Users} color="text-emerald-400"
                chart={signupsChart} chartColor="#10b981" />
              <StatCard label="Activos 30d" value={stats.users.active_30d}
                sub={`${stats.users.with_handicap} con hándicap`}
                icon={Activity} color="text-blue-400" />
              <StatCard label="Rondas total" value={stats.rounds.total}
                sub={`+${stats.rounds.new_7d} esta semana`}
                icon={Flag} color="text-purple-400"
                chart={roundsChart} chartColor="#a855f7" />
              <StatCard label="En curso" value={stats.rounds.active}
                sub={`${stats.rounds.scheduled} prog. · ${stats.rounds.finished} fin.`}
                icon={Play} color="text-yellow-400" />
              <StatCard label="Scores totales" value={stats.scores.total}
                sub={`${stats.scores.differentials} diferenciales`}
                icon={Hash} color="text-orange-400" />
              <StatCard label="Participaciones" value={stats.participations}
                sub="inscripciones a rondas"
                icon={TrendingUp} color="text-pink-400" />
              <StatCard label="Canchas activas" value={stats.courses_active}
                icon={CheckCircle2} color="text-cyan-400" />
              <StatCard label="Nuevos 30d" value={stats.users.new_30d}
                sub="registros del mes"
                icon={Clock} color="text-zinc-300" />
            </div>

            {/* Formats + Top players row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

              {/* Formats */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart2 size={15} className="text-purple-400" />
                  <h2 className="font-semibold text-white text-sm">Rondas por formato</h2>
                </div>
                <FormatBar data={stats.rounds.by_format} />
              </div>

              {/* Top players */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Trophy size={15} className="text-amber-400" />
                  <h2 className="font-semibold text-white text-sm">Top jugadores</h2>
                </div>
                <div className="space-y-2">
                  {topPlayers.map((p, i) => (
                    <div key={p.user_id} className="flex items-center gap-3">
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black flex-shrink-0 ${
                        i === 0 ? 'bg-amber-500 text-zinc-900' :
                        i === 1 ? 'bg-zinc-400 text-zinc-900' :
                        i === 2 ? 'bg-orange-700 text-white' : 'bg-zinc-800 text-zinc-500'
                      }`}>{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">{p.name}</p>
                        <p className="text-xs text-zinc-500">@{p.username}{p.handicap_index !== null ? ` · HCP ${p.handicap_index}` : ''}</p>
                      </div>
                      <span className="text-sm font-bold text-emerald-400 flex-shrink-0">{p.rounds}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Sparkline charts */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
                <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium mb-3">Registros últimos 30 días</p>
                <Sparkline data={signupsChart} color="#10b981" />
                <div className="flex justify-between mt-1">
                  <span className="text-[10px] text-zinc-700">{signupsChart[0]?.day ?? ''}</span>
                  <span className="text-[10px] text-zinc-700">{signupsChart[signupsChart.length - 1]?.day ?? ''}</span>
                </div>
              </div>
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
                <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium mb-3">Rondas creadas últimos 30 días</p>
                <Sparkline data={roundsChart} color="#a855f7" />
                <div className="flex justify-between mt-1">
                  <span className="text-[10px] text-zinc-700">{roundsChart[0]?.day ?? ''}</span>
                  <span className="text-[10px] text-zinc-700">{roundsChart[roundsChart.length - 1]?.day ?? ''}</span>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── USERS TAB ─────────────────────────────────────────────────── */}
        {activeTab === 'users' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            {/* Search bar */}
            <div className="px-5 py-4 border-b border-zinc-800 flex gap-3 items-center">
              <div className="relative flex-1 max-w-sm">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <input
                  type="text" placeholder="Buscar por nombre, email, username…"
                  value={searchInput}
                  onChange={e => setSearchInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { setUserSearch(searchInput); setUsersPage(1) } }}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl pl-9 pr-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 placeholder:text-zinc-600" />
              </div>
              <button onClick={() => { setUserSearch(searchInput); setUsersPage(1) }}
                className="bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-medium px-4 py-2 rounded-xl transition-colors">
                Buscar
              </button>
              {userSearch && (
                <button onClick={() => { setSearchInput(''); setUserSearch(''); setUsersPage(1) }}
                  className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
                  Limpiar
                </button>
              )}
              <span className="ml-auto text-xs text-zinc-500">{usersTotal} usuarios</span>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-800/30">
                    <th className="text-left text-xs text-zinc-500 px-5 py-3 font-semibold uppercase tracking-wide">Usuario</th>
                    <th className="text-left text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wide hidden md:table-cell">Email</th>
                    <th className="text-center text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wide">HCP</th>
                    <th className="text-left text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wide hidden lg:table-cell">Registro</th>
                    <th className="text-left text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wide hidden lg:table-cell">Último login</th>
                    <th className="text-center text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wide">Estado</th>
                    <th className="px-3 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {users.map(u => (
                    <tr key={u.id} className={`hover:bg-zinc-800/30 transition-colors ${!u.is_active ? 'opacity-50' : ''}`}>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-bold text-emerald-400 flex-shrink-0">
                            {u.first_name.charAt(0)}{u.last_name.charAt(0)}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">
                              {u.first_name} {u.last_name}
                              {u.is_superadmin && (
                                <ShieldCheck size={11} className="inline ml-1 text-emerald-400" />
                              )}
                            </p>
                            <p className="text-xs text-zinc-500">@{u.username}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="text-xs text-zinc-400 font-mono">{u.email}</span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <span className="text-sm font-semibold text-white">
                          {u.handicap_index !== null ? u.handicap_index.toFixed(1) : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className="text-xs text-zinc-500">{fmtDate(u.created_at)}</span>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className="text-xs text-zinc-500">{fmtDate(u.last_login)}</span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${u.is_active ? 'text-emerald-400 bg-emerald-400/10' : 'text-zinc-500 bg-zinc-800'}`}>
                          {u.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        {!u.is_superadmin && (
                          <button
                            onClick={() => handleToggleUser(u.id)}
                            disabled={togglingUser === u.id}
                            title={u.is_active ? 'Desactivar' : 'Activar'}
                            className="text-zinc-500 hover:text-zinc-300 transition-colors disabled:opacity-40">
                            {togglingUser === u.id
                              ? <Loader2 size={16} className="animate-spin" />
                              : u.is_active
                                ? <ToggleRight size={20} className="text-emerald-500" />
                                : <ToggleLeft size={20} />}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-5 py-4 border-t border-zinc-800 flex items-center justify-between">
              <span className="text-xs text-zinc-500">Página {usersPage} de {usersPages}</span>
              <div className="flex gap-2">
                <button onClick={() => setUsersPage(p => Math.max(1, p - 1))} disabled={usersPage === 1}
                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-white disabled:opacity-30 transition-colors">
                  <ChevronLeft size={14} />
                </button>
                <button onClick={() => setUsersPage(p => Math.min(usersPages, p + 1))} disabled={usersPage === usersPages}
                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-white disabled:opacity-30 transition-colors">
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── ROUNDS TAB ────────────────────────────────────────────────── */}
        {activeTab === 'rounds' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
              <h2 className="font-semibold text-white text-sm">Todas las rondas</h2>
              <span className="text-xs text-zinc-500">{roundsTotal} total</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-800/30">
                    <th className="text-left text-xs text-zinc-500 px-5 py-3 font-semibold uppercase tracking-wide">Ronda</th>
                    <th className="text-left text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wide hidden sm:table-cell">Formato</th>
                    <th className="text-center text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wide">Estado</th>
                    <th className="text-center text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wide">Jug.</th>
                    <th className="text-left text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wide hidden lg:table-cell">Creador</th>
                    <th className="text-left text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wide hidden lg:table-cell">Fecha</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {rounds.map(r => (
                    <tr key={r.id} className="hover:bg-zinc-800/30 transition-colors">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center flex-shrink-0">
                            <Flag size={11} className="text-emerald-400" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white truncate max-w-[160px]">
                              {r.name ?? 'Ronda sin nombre'}
                            </p>
                            <p className="text-xs text-zinc-500">{r.holes_to_play} hoyos</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <span className="text-xs bg-zinc-800 border border-zinc-700 px-2 py-0.5 rounded-full text-zinc-300">
                          {FORMAT_LABEL[r.game_format] ?? r.game_format}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_CLS[r.status] ?? 'text-zinc-400'}`}>
                          {r.status === 'scheduled' ? 'Prog.' : r.status === 'active' ? 'Activa' : 'Final.'}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <span className="text-sm font-bold text-zinc-300">{r.player_count}</span>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <p className="text-xs text-zinc-300">{r.created_by_name}</p>
                        <p className="text-xs text-zinc-600 font-mono truncate max-w-[180px]">{r.created_by_email}</p>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className="text-xs text-zinc-500">{fmtDate(r.created_at)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-5 py-4 border-t border-zinc-800 flex items-center justify-between">
              <span className="text-xs text-zinc-500">Página {roundsPage} de {roundsPages}</span>
              <div className="flex gap-2">
                <button onClick={() => setRoundsPage(p => Math.max(1, p - 1))} disabled={roundsPage === 1}
                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-white disabled:opacity-30 transition-colors">
                  <ChevronLeft size={14} />
                </button>
                <button onClick={() => setRoundsPage(p => Math.min(roundsPages, p + 1))} disabled={roundsPage === roundsPages}
                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-white disabled:opacity-30 transition-colors">
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  )
}
