'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Flag, LogOut, User, TrendingUp, Calendar, BarChart2, Settings, MapPin, Users, ChevronRight, Play, Clock, CheckCircle2, UserPlus, Rss, Bell, ShieldCheck, Building2, HelpCircle } from 'lucide-react'
import { api, isAuthed, clearAuth } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'
import AleaCredit from '@/components/layout/AleaCredit'

interface UserProfile {
  first_name: string
  last_name: string
  email: string
  username: string
  handicap_index: number | null
  is_superadmin?: boolean
}

interface Round {
  id: string
  name: string | null
  course_name: string | null
  game_format: string
  status: string
  holes_to_play: number
  scheduled_at: string
  holes_played: number
  total_gross: number | null
}

const FORMAT_LABEL: Record<string, { es: string; en: string }> = {
  stroke: { es: 'Stroke Play', en: 'Stroke Play' },
  gran_premio: { es: 'Gran Premio', en: 'Gran Premio' },
  stableford: { es: 'Stableford', en: 'Stableford' },
  stableford_modified: { es: 'Stableford Mod.', en: 'Mod. Stableford' },
  match: { es: 'Match Play', en: 'Match Play' },
}

export default function DashboardPage() {
  const locale = useLocale()
  const router = useRouter()
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [rounds, setRounds] = useState<Round[]>([])
  const [roundCount, setRoundCount] = useState<number | null>(null)
  const [bestScore, setBestScore] = useState<number | null>(null)
  const [unreadNotifs, setUnreadNotifs] = useState(0)
  const [staffClubs, setStaffClubs] = useState<{ club_id: string; club_name: string; club_slug: string; role: string }[]>([])

  useEffect(() => {
    const token = isAuthed()
    if (!token) { router.push(`/${locale}/auth/login`); return }
    Promise.all([
      api.get('/users/me'),
      api.get('/rounds'),
      api.get('/notifications/unread-count'),
      api.get('/clubs/staff/mine').catch(() => ({ data: [] })),
    ])
      .then(([meRes, roundsRes, notifRes, staffRes]) => {
        setUser(meRes.data)
        const data = roundsRes.data as Round[]
        setRounds(data)
        setRoundCount(data.filter(r => r.status === 'finished').length)
        const finished = data.filter(r => r.total_gross != null && r.status === 'finished')
        if (finished.length) setBestScore(Math.min(...finished.map(r => r.total_gross!)))
        setUnreadNotifs(notifRes.data.count ?? 0)
        setStaffClubs(staffRes.data || [])
      })
      .catch(() => { clearAuth(); router.push(`/${locale}/auth/login`) })
      .finally(() => setLoading(false))
  }, [locale, router])

  const logout = async () => {
    await api.post('/auth/logout').catch(() => {})
    clearAuth()
    router.push(`/${locale}/auth/login`)
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (!user) return null

  const stats = [
    { label: locale === 'es' ? 'Hándicap' : 'Handicap', value: user.handicap_index?.toFixed(1) ?? '—', icon: TrendingUp, color: 'text-emerald-400' },
    { label: locale === 'es' ? 'Rondas jugadas' : 'Rounds played', value: roundCount !== null ? String(roundCount) : '—', icon: Calendar, color: 'text-blue-400' },
    { label: locale === 'es' ? 'Mejor score' : 'Best score', value: bestScore !== null ? String(bestScore) : '—', icon: BarChart2, color: 'text-yellow-400' },
  ]

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={16} className="text-white" />
            </div>
            <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
          </div>
          <div className="flex items-center gap-3">
            {user.is_superadmin && (
              <Link href={`/${locale}/admin`}
                title={locale === 'es' ? 'Panel de administración' : 'Admin panel'}
                className="text-emerald-400 hover:text-emerald-300 transition-colors">
                <ShieldCheck size={20} />
              </Link>
            )}
            <Link href={`/${locale}/ayuda`}
              title={locale === 'es' ? 'Ayuda' : 'Help'}
              className="text-zinc-400 hover:text-white transition-colors">
              <HelpCircle size={20} />
            </Link>
            <Link href={`/${locale}/notifications`}
              className="relative text-zinc-400 hover:text-white transition-colors">
              <Bell size={20} />
              {unreadNotifs > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none">
                  {unreadNotifs > 9 ? '9+' : unreadNotifs}
                </span>
              )}
            </Link>
            <Link href={`/${locale}/profile`}
              className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors">
              <Settings size={16} />
              {locale === 'es' ? 'Perfil' : 'Profile'}
            </Link>
            <button onClick={logout}
              className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors">
              <LogOut size={16} />
              {locale === 'es' ? 'Salir' : 'Logout'}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Welcome */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-14 h-14 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
            <User size={26} className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">
              {locale === 'es' ? `Hola, ${user.first_name}!` : `Hello, ${user.first_name}!`}
            </h1>
            <p className="text-zinc-400 text-sm">@{user.username}</p>
          </div>
        </div>

        {/* Admin shortcut (only for superadmins) */}
        {user.is_superadmin && (
          <Link href={`/${locale}/admin`}
            className="block mb-6 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/15 hover:border-emerald-500/50 rounded-2xl p-4 transition-all group">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                <ShieldCheck size={20} className="text-emerald-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-white text-sm">
                  {locale === 'es' ? 'Panel de administración' : 'Admin panel'}
                </p>
                <p className="text-xs text-emerald-400/70 truncate">
                  {locale === 'es' ? 'Estadísticas, usuarios, hándicaps y links de recuperación' : 'Stats, users, handicaps and recovery links'}
                </p>
              </div>
              <ChevronRight size={18} className="text-emerald-400/60 group-hover:text-emerald-400 transition-colors flex-shrink-0" />
            </div>
          </Link>
        )}

        {/* Club shortcut (for users who are staff of any club) */}
        {staffClubs.length > 0 && (
          <div className="mb-6 space-y-2">
            {staffClubs.map(sc => (
              <Link key={sc.club_id} href={`/${locale}/club/${sc.club_id}`}
                className="block bg-blue-500/10 border border-blue-500/30 hover:bg-blue-500/15 hover:border-blue-500/50 rounded-2xl p-4 transition-all group">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
                    <Building2 size={20} className="text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-white text-sm">
                      {locale === 'es' ? 'Mi Club: ' : 'My Club: '}{sc.club_name}
                    </p>
                    <p className="text-xs text-blue-400/70 truncate">
                      {locale === 'es' ? `Panel del club · rol: ${sc.role || 'staff'}` : `Club panel · role: ${sc.role || 'staff'}`}
                    </p>
                  </div>
                  <ChevronRight size={18} className="text-blue-400/60 group-hover:text-blue-400 transition-colors flex-shrink-0" />
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-3 gap-4 mb-8">
          {stats.map((s) => (
            <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-zinc-500">{s.label}</span>
                <s.icon size={18} className={s.color} />
              </div>
              <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>

        {/* Quick access */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          <Link href={`/${locale}/rounds/new`}
            className="sm:col-span-2 bg-emerald-500 hover:bg-emerald-400 rounded-2xl p-5 flex items-center justify-between group transition-all">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                <Play size={18} className="text-white" />
              </div>
              <div>
                <p className="font-bold text-white">{locale === 'es' ? 'Nueva ronda' : 'New round'}</p>
                <p className="text-xs text-white/70">{locale === 'es' ? 'Iniciar scorecard ahora' : 'Start scorecard now'}</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-white/60" />
          </Link>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
          <Link href={`/${locale}/courses`}
            className="bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 rounded-2xl p-5 flex items-center justify-between group transition-all">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                <MapPin size={18} className="text-emerald-400" />
              </div>
              <div>
                <p className="font-semibold text-white text-sm">{locale === 'es' ? 'Canchas' : 'Courses'}</p>
                <p className="text-xs text-zinc-500">{locale === 'es' ? 'Ver y agregar campos de golf' : 'View and add golf courses'}</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          </Link>

          <Link href={`/${locale}/clubs`}
            className="bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 rounded-2xl p-5 flex items-center justify-between group transition-all">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                <Users size={18} className="text-emerald-400" />
              </div>
              <div>
                <p className="font-semibold text-white text-sm">{locale === 'es' ? 'Clubs' : 'Clubs'}</p>
                <p className="text-xs text-zinc-500">{locale === 'es' ? 'Grupos de golfistas' : 'Golf groups'}</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          </Link>

          <Link href={`/${locale}/feed`}
            className="bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 rounded-2xl p-5 flex items-center justify-between group transition-all">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                <Rss size={18} className="text-emerald-400" />
              </div>
              <div>
                <p className="font-semibold text-white text-sm">{locale === 'es' ? 'Actividad' : 'Activity'}</p>
                <p className="text-xs text-zinc-500">{locale === 'es' ? 'Rondas de jugadores que sigues' : 'Rounds from players you follow'}</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          </Link>

          <Link href={`/${locale}/social`}
            className="bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 rounded-2xl p-5 flex items-center justify-between group transition-all">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                <UserPlus size={18} className="text-emerald-400" />
              </div>
              <div>
                <p className="font-semibold text-white text-sm">{locale === 'es' ? 'Jugadores' : 'Players'}</p>
                <p className="text-xs text-zinc-500">{locale === 'es' ? 'Buscar y seguir golfistas' : 'Find & follow golfers'}</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          </Link>

          <Link href={`/${locale}/groups`}
            className="bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 rounded-2xl p-5 flex items-center justify-between group transition-all">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                <Users size={18} className="text-emerald-400" />
              </div>
              <div>
                <p className="font-semibold text-white text-sm">{locale === 'es' ? 'Mis grupos' : 'My groups'}</p>
                <p className="text-xs text-zinc-500">{locale === 'es' ? 'Grupos de golf privados' : 'Private golf groups'}</p>
              </div>
            </div>
            <ChevronRight size={18} className="text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          </Link>
        </div>

        {/* Rounds section */}
        {rounds.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <Flag size={28} className="text-emerald-400" />
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">
              {locale === 'es' ? 'Aún no tienes rondas' : 'No rounds yet'}
            </h2>
            <p className="text-zinc-500 text-sm max-w-sm mx-auto mb-6">
              {locale === 'es'
                ? 'Comienza a registrar tus rondas para ver tus estadísticas y hándicap WHS aquí.'
                : 'Start recording your rounds to see your stats and WHS handicap here.'}
            </p>
            <Link href={`/${locale}/rounds/new`}
              className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-6 py-2.5 rounded-full transition-colors text-sm">
              {locale === 'es' ? 'Nueva ronda' : 'New round'}
            </Link>
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
              <h2 className="font-semibold text-white text-sm">{locale === 'es' ? 'Rondas recientes' : 'Recent rounds'}</h2>
              <Link href={`/${locale}/rounds`} className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
                {locale === 'es' ? 'Ver todas' : 'View all'}
              </Link>
            </div>
            <div className="divide-y divide-zinc-800">
              {rounds.slice(0, 5).map(r => {
                const fmt = FORMAT_LABEL[r.game_format]
                const date = new Date(r.scheduled_at).toLocaleDateString(
                  locale === 'es' ? 'es-MX' : 'en-US', { dateStyle: 'medium' }
                )
                return (
                  <Link key={r.id} href={`/${locale}/rounds/${r.id}`}
                    className="flex items-center gap-3 px-5 py-3.5 hover:bg-zinc-800/50 transition-colors group">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      r.status === 'active' ? 'bg-emerald-500/20' :
                      r.status === 'finished' ? 'bg-zinc-800' :
                      'bg-yellow-500/10'
                    }`}>
                      {r.status === 'active' ? <Play size={14} className="text-emerald-400" /> :
                       r.status === 'finished' ? <CheckCircle2 size={14} className="text-zinc-400" /> :
                       <Clock size={14} className="text-yellow-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">
                        {r.name ?? r.course_name ?? (locale === 'es' ? 'Ronda' : 'Round')}
                      </p>
                      <p className="text-xs text-zinc-500 truncate">
                        {date} · {locale === 'es' ? fmt?.es : fmt?.en}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {r.total_gross ? (
                        <p className="text-sm font-bold text-white">{r.total_gross}</p>
                      ) : r.status === 'active' ? (
                        <p className="text-xs text-emerald-400">{r.holes_played} {locale === 'es' ? 'jug.' : 'played'}</p>
                      ) : null}
                      <ChevronRight size={14} className="text-zinc-700 group-hover:text-zinc-500 transition-colors ml-auto mt-0.5" />
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        )}

        {/* Footer credit */}
        <AleaCredit />
      </main>
    </div>
  )
}
