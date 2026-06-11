'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Copy, Check, Users, Lock, Globe, Crown, Shield, UserMinus, Trash2, LogOut, Loader2, Flag, Plus, ChevronRight, Trophy, MessagesSquare } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Member {
  user_id: string
  username: string
  first_name: string
  last_name: string
  handicap_index: number | null
  role: string
  joined_at: string | null
}

interface GroupDetail {
  id: string
  name: string
  description: string | null
  is_private: boolean
  max_members: number | null
  member_count: number
  invite_code: string | null
  my_role: string | null
  created_by: string
  members: Member[]
}

interface GroupRound {
  id: string
  name: string | null
  course_name: string | null
  game_format: string
  status: string
  holes_to_play: number
  scheduled_at: string | null
  player_count: number
}

const STATUS_BADGE: Record<string, { es: string; en: string; cls: string }> = {
  scheduled: { es: 'Programada', en: 'Scheduled', cls: 'bg-blue-500/15 text-blue-300 border-blue-500/30' },
  active: { es: 'En juego', en: 'In play', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  finished: { es: 'Finalizada', en: 'Finished', cls: 'bg-zinc-700/40 text-zinc-400 border-zinc-700' },
}

const ROLE_ICON: Record<string, React.ReactNode> = {
  owner: <Crown size={12} className="text-yellow-400" />,
  admin: <Shield size={12} className="text-blue-400" />,
}

export default function GroupDetailPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams()
  const groupId = params.id as string
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [group, setGroup] = useState<GroupDetail | null>(null)
  const [rounds, setRounds] = useState<GroupRound[]>([])
  const [loading, setLoading] = useState(true)
  const [myUserId, setMyUserId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [removing, setRemoving] = useState<string | null>(null)
  const [confirming, setConfirming] = useState<'leave' | 'delete' | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { router.push(`/${locale}/auth/login`); return }
    Promise.all([
      api.get(`/groups/${groupId}`),
      api.get('/users/me'),
      api.get(`/groups/${groupId}/rounds`).catch(() => ({ data: [] })),
    ])
      .then(([gRes, meRes, rRes]) => {
        setGroup(gRes.data)
        setMyUserId(meRes.data.id)
        setRounds(rRes.data || [])
      })
      .catch(() => router.push(`/${locale}/groups`))
      .finally(() => setLoading(false))
  }, [groupId, locale, router])

  const copyCode = () => {
    if (!group?.invite_code) return
    navigator.clipboard.writeText(group.invite_code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRemoveMember = async (userId: string) => {
    setRemoving(userId)
    try {
      await api.delete(`/groups/${groupId}/members/${userId}`)
      setGroup(prev => prev ? {
        ...prev,
        member_count: prev.member_count - 1,
        members: prev.members.filter(m => m.user_id !== userId)
      } : prev)
    } catch {
    } finally {
      setRemoving(null)
    }
  }

  const handleLeave = async () => {
    setActionLoading(true)
    try {
      await api.delete(`/groups/${groupId}/leave`)
      router.push(`/${locale}/groups`)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail ?? lbl('Error al salir', 'Error leaving'))
      setActionLoading(false)
      setConfirming(null)
    }
  }

  const handleDelete = async () => {
    setActionLoading(true)
    try {
      await api.delete(`/groups/${groupId}`)
      router.push(`/${locale}/groups`)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail ?? lbl('Error al eliminar', 'Error deleting'))
      setActionLoading(false)
      setConfirming(null)
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (!group) return null

  const isOwner = group.my_role === 'owner'
  const isAdmin = group.my_role === 'admin'
  const canManage = isOwner || isAdmin
  const isMember = group.my_role != null

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/groups`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex-1 min-w-0">
            <h1 className="font-bold text-white text-lg truncate">{group.name}</h1>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {group.is_private
              ? <Lock size={13} className="text-zinc-500" />
              : <Globe size={13} className="text-zinc-600" />
            }
            <span className="text-xs text-zinc-500">{group.member_count} {lbl('miembros', 'members')}</span>
          </div>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-5">
        {/* Description */}
        {group.description && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-4">
            <p className="text-sm text-zinc-300">{group.description}</p>
          </div>
        )}

        {/* Invite code (owner/admin only) */}
        {group.invite_code && canManage && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-4">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-3">
              {lbl('Código de invitación', 'Invite code')}
            </p>
            <div className="flex items-center gap-3">
              <span className="flex-1 font-mono text-2xl font-bold text-emerald-400 tracking-[0.3em]">
                {group.invite_code}
              </span>
              <button onClick={copyCode}
                className="flex items-center gap-1.5 px-3 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-xl text-sm transition-colors text-zinc-300">
                {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                {copied ? lbl('Copiado', 'Copied') : lbl('Copiar', 'Copy')}
              </button>
            </div>
            <p className="text-xs text-zinc-600 mt-2">
              {lbl('Comparte este código para invitar jugadores al grupo.', 'Share this code to invite players to the group.')}
            </p>
          </div>
        )}

        {/* Wall + Leaderboard links */}
        {isMember && (
          <div className="grid grid-cols-2 gap-3">
            <Link href={`/${locale}/groups/${groupId}/wall`}
              className="flex flex-col gap-2 bg-zinc-900 border border-zinc-800 hover:border-emerald-500/30 rounded-2xl px-4 py-4 transition-colors">
              <div className="w-9 h-9 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <MessagesSquare size={16} className="text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">{lbl('Muro', 'Wall')}</p>
                <p className="text-xs text-zinc-500">{lbl('Publica y comenta', 'Post and comment')}</p>
              </div>
            </Link>
            <Link href={`/${locale}/groups/${groupId}/leaderboard`}
              className="flex flex-col gap-2 bg-zinc-900 border border-zinc-800 hover:border-emerald-500/30 rounded-2xl px-4 py-4 transition-colors">
              <div className="w-9 h-9 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <Trophy size={16} className="text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">{lbl('Posiciones', 'Leaderboard')}</p>
                <p className="text-xs text-zinc-500">{lbl('Ranking del grupo', 'Group ranking')}</p>
              </div>
            </Link>
          </div>
        )}

        {/* Group rounds */}
        {isMember && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                {lbl('Rondas del grupo', 'Group rounds')}
              </p>
              <Link
                href={`/${locale}/rounds/new?group_id=${groupId}&group_name=${encodeURIComponent(group.name)}`}
                className="flex items-center gap-1 px-2.5 py-1.5 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 rounded-lg text-xs font-semibold transition-colors">
                <Plus size={13} /> {lbl('Nueva ronda', 'New round')}
              </Link>
            </div>
            {rounds.length === 0 ? (
              <div className="px-5 py-8 text-center">
                <Flag size={22} className="text-zinc-700 mx-auto mb-2" />
                <p className="text-sm text-zinc-500">
                  {lbl('Aún no hay rondas en este grupo.', 'No rounds in this group yet.')}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-zinc-800">
                {rounds.map(r => {
                  const badge = STATUS_BADGE[r.status] ?? STATUS_BADGE.scheduled
                  const when = r.scheduled_at
                    ? new Date(r.scheduled_at).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { day: 'numeric', month: 'short' })
                    : ''
                  return (
                    <Link key={r.id} href={`/${locale}/rounds/${r.id}`}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-zinc-800/40 transition-colors">
                      <div className="w-9 h-9 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                        <Flag size={15} className="text-emerald-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">
                          {r.name || r.course_name || lbl('Ronda', 'Round')}
                        </p>
                        <p className="text-xs text-zinc-500 truncate">
                          {when}{r.course_name && r.name ? ` · ${r.course_name}` : ''} · {r.player_count} {lbl('jugadores', 'players')}
                        </p>
                      </div>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badge.cls}`}>
                        {locale === 'es' ? badge.es : badge.en}
                      </span>
                      <ChevronRight size={15} className="text-zinc-600 flex-shrink-0" />
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Members list */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          <div className="px-5 py-3 border-b border-zinc-800">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
              {lbl('Miembros', 'Members')}
            </p>
          </div>
          <div className="divide-y divide-zinc-800">
            {group.members.map(m => (
              <div key={m.user_id} className="flex items-center gap-3 px-4 py-3">
                <div className="w-9 h-9 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-zinc-400">{m.first_name[0]}{m.last_name[0]}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p className="text-sm font-medium text-white">{m.first_name} {m.last_name}</p>
                    {ROLE_ICON[m.role]}
                  </div>
                  <p className="text-xs text-zinc-500">
                    @{m.username}
                    {m.handicap_index != null && ` · HCP ${m.handicap_index.toFixed(1)}`}
                  </p>
                </div>
                {canManage && m.user_id !== myUserId && m.role !== 'owner' && (
                  <button
                    onClick={() => handleRemoveMember(m.user_id)}
                    disabled={removing === m.user_id}
                    className="p-1.5 text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-50">
                    {removing === m.user_id
                      ? <Loader2 size={14} className="animate-spin" />
                      : <UserMinus size={14} />
                    }
                  </button>
                )}
                {m.user_id === myUserId && (
                  <span className="text-xs text-zinc-600">{lbl('Tú', 'You')}</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        {isMember && (
          <div className="space-y-2">
            {!isOwner && (
              <button onClick={() => setConfirming('leave')}
                className="w-full flex items-center justify-center gap-2 py-3 bg-zinc-900 border border-zinc-800 hover:border-red-500/30 text-zinc-400 hover:text-red-400 rounded-xl text-sm font-medium transition-all">
                <LogOut size={15} />
                {lbl('Salir del grupo', 'Leave group')}
              </button>
            )}
            {isOwner && (
              <button onClick={() => setConfirming('delete')}
                className="w-full flex items-center justify-center gap-2 py-3 bg-red-500/10 border border-red-500/20 hover:border-red-500/40 text-red-400 hover:text-red-300 rounded-xl text-sm font-medium transition-all">
                <Trash2 size={15} />
                {lbl('Eliminar grupo', 'Delete group')}
              </button>
            )}
          </div>
        )}
      </main>

      {/* Confirm modal */}
      {confirming && (
        <div className="fixed inset-0 bg-black/70 flex items-end sm:items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-sm p-6 text-center">
            <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
              {confirming === 'delete' ? <Trash2 size={22} className="text-red-400" /> : <LogOut size={22} className="text-red-400" />}
            </div>
            <h3 className="font-bold text-white mb-2">
              {confirming === 'delete' ? lbl('¿Eliminar el grupo?', 'Delete group?') : lbl('¿Salir del grupo?', 'Leave group?')}
            </h3>
            <p className="text-zinc-400 text-sm mb-6">
              {confirming === 'delete'
                ? lbl('Se eliminará el grupo y todos sus miembros perderán acceso.', 'The group and all member access will be removed.')
                : lbl('Ya no podrás ver ni participar en este grupo.', 'You will no longer be able to see or participate in this group.')}
            </p>
            <div className="flex gap-3">
              <button onClick={() => setConfirming(null)} disabled={actionLoading}
                className="flex-1 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-sm font-medium transition-colors">
                {lbl('Cancelar', 'Cancel')}
              </button>
              <button onClick={confirming === 'delete' ? handleDelete : handleLeave} disabled={actionLoading}
                className="flex-1 py-2.5 bg-red-500 hover:bg-red-400 disabled:opacity-60 text-white rounded-xl text-sm font-semibold transition-colors flex items-center justify-center gap-2">
                {actionLoading && <Loader2 size={14} className="animate-spin" />}
                {confirming === 'delete' ? lbl('Eliminar', 'Delete') : lbl('Salir', 'Leave')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
