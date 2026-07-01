'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Bell, UserPlus, Play, CheckCircle2, TrendingDown, TrendingUp, CheckCheck, Calendar, CalendarX, Building2 } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Notif {
  id: string
  type: string
  title: string
  body: string
  data: Record<string, unknown>
  is_read: boolean
  created_at: string
}

const TYPE_ICON: Record<string, React.ReactNode> = {
  round_invite:       <UserPlus size={16} className="text-emerald-400" />,
  round_started:      <Play size={16} className="text-blue-400" />,
  round_finished:     <CheckCircle2 size={16} className="text-zinc-400" />,
  handicap_updated:   <TrendingDown size={16} className="text-yellow-400" />,
  score_update:       <Play size={16} className="text-emerald-400" />,
  bet_result:         <CheckCircle2 size={16} className="text-yellow-400" />,
  // v1.20.0 — Clubs SaaS notifications
  booking_confirmed:  <Calendar size={16} className="text-emerald-400" />,
  booking_cancelled:  <CalendarX size={16} className="text-orange-400" />,
  welcome_club:       <Building2 size={16} className="text-emerald-400" />,
  tee_time_reminder:  <Bell size={16} className="text-amber-400" />,
}

const TYPE_BG: Record<string, string> = {
  round_invite:       'bg-emerald-500/10 border-emerald-500/20',
  round_started:      'bg-blue-500/10 border-blue-500/20',
  round_finished:     'bg-zinc-800 border-zinc-700',
  handicap_updated:   'bg-yellow-500/10 border-yellow-500/20',
  score_update:       'bg-emerald-500/10 border-emerald-500/20',
  bet_result:         'bg-yellow-500/10 border-yellow-500/20',
  booking_confirmed:  'bg-emerald-500/10 border-emerald-500/20',
  booking_cancelled:  'bg-orange-500/10 border-orange-500/20',
  welcome_club:       'bg-emerald-500/10 border-emerald-500/20',
  tee_time_reminder:  'bg-amber-500/10 border-amber-500/20',
}

function timeAgo(iso: string, locale: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diff / 60000)
  const h = Math.floor(diff / 3600000)
  const d = Math.floor(diff / 86400000)
  if (min < 1) return locale === 'es' ? 'Ahora' : 'Just now'
  if (min < 60) return locale === 'es' ? `Hace ${min}m` : `${min}m ago`
  if (h < 24) return locale === 'es' ? `Hace ${h}h` : `${h}h ago`
  if (d === 1) return locale === 'es' ? 'Ayer' : 'Yesterday'
  return new Date(iso).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { dateStyle: 'medium' })
}

export default function NotificationsPage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [notifs, setNotifs] = useState<Notif[]>([])
  const [loading, setLoading] = useState(true)
  const [markingAll, setMarkingAll] = useState(false)

  useEffect(() => {
    const token = isAuthed()
    if (!token) { router.push(`/${locale}/auth/login`); return }
    api.get('/notifications')
      .then(r => setNotifs(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [locale, router])

  const markRead = async (id: string) => {
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
    await api.post(`/notifications/${id}/read`).catch(() => {})
  }

  const markAllRead = async () => {
    setMarkingAll(true)
    await api.post('/notifications/read-all').catch(() => {})
    setNotifs(prev => prev.map(n => ({ ...n, is_read: true })))
    setMarkingAll(false)
  }

  const handleClick = (n: Notif) => {
    if (!n.is_read) markRead(n.id)
    const roundId = n.data?.round_id as string | undefined
    if (roundId) router.push(`/${locale}/rounds/${roundId}`)
  }

  const unreadCount = notifs.filter(n => !n.is_read).length

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="font-bold text-white text-lg flex-1">
            {lbl('Notificaciones', 'Notifications')}
            {unreadCount > 0 && (
              <span className="ml-2 text-xs bg-red-500 text-white font-semibold px-1.5 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </h1>
          {unreadCount > 0 && (
            <button onClick={markAllRead} disabled={markingAll}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-emerald-400 transition-colors disabled:opacity-50">
              <CheckCheck size={14} />
              {lbl('Todo leído', 'Mark all read')}
            </button>
          )}
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-4">
        {notifs.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center mt-4">
            <div className="w-16 h-16 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center mx-auto mb-4">
              <Bell size={28} className="text-zinc-600" />
            </div>
            <p className="text-zinc-500 text-sm">{lbl('Sin notificaciones', 'No notifications yet')}</p>
          </div>
        ) : (
          <div className="space-y-2 mt-2">
            {notifs.map(n => {
              const icon = TYPE_ICON[n.type] ?? <Bell size={16} className="text-zinc-400" />
              const bg = TYPE_BG[n.type] ?? 'bg-zinc-800 border-zinc-700'
              return (
                <button key={n.id} onClick={() => handleClick(n)}
                  className={`w-full text-left flex items-start gap-3 p-4 rounded-2xl border transition-all ${
                    n.is_read
                      ? 'bg-zinc-900/50 border-zinc-800/50 opacity-60'
                      : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'
                  }`}>
                  <div className={`w-9 h-9 rounded-xl border flex items-center justify-center flex-shrink-0 mt-0.5 ${bg}`}>
                    {icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className={`text-sm font-semibold leading-snug ${n.is_read ? 'text-zinc-400' : 'text-white'}`}>
                        {n.title}
                      </p>
                      <span className="text-xs text-zinc-600 flex-shrink-0 mt-0.5">
                        {n.created_at ? timeAgo(n.created_at, locale) : ''}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">{n.body}</p>
                  </div>
                  {!n.is_read && (
                    <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0 mt-2" />
                  )}
                </button>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
