'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Plus, Users, Lock, Globe, ChevronRight, Loader2, X } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface GroupItem {
  id: string
  name: string
  description: string | null
  is_private: boolean
  max_members: number | null
  member_count: number
  invite_code: string | null
  my_role: string
}

export default function GroupsPage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [groups, setGroups] = useState<GroupItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showJoin, setShowJoin] = useState(false)
  const [creating, setCreating] = useState(false)
  const [joining, setJoining] = useState(false)
  const [joinCode, setJoinCode] = useState('')
  const [joinError, setJoinError] = useState('')
  const [form, setForm] = useState({ name: '', description: '', is_private: false })
  const [createError, setCreateError] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { router.push(`/${locale}/auth/login`); return }
    api.get('/groups')
      .then(r => setGroups(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [locale, router])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setCreating(true)
    setCreateError('')
    try {
      const r = await api.post('/groups', {
        name: form.name.trim(),
        description: form.description.trim() || null,
        is_private: form.is_private,
      })
      setGroups(prev => [r.data, ...prev])
      setShowCreate(false)
      setForm({ name: '', description: '', is_private: false })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setCreateError(detail ?? lbl('Error al crear el grupo', 'Error creating group'))
    } finally {
      setCreating(false)
    }
  }

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!joinCode.trim()) return
    setJoining(true)
    setJoinError('')
    try {
      const r = await api.post(`/groups/join/${joinCode.trim().toUpperCase()}`)
      router.push(`/${locale}/groups/${r.data.group_id}`)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setJoinError(detail ?? lbl('Código inválido', 'Invalid code'))
      setJoining(false)
    }
  }

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
          <h1 className="font-bold text-white text-lg flex-1">{lbl('Mis grupos', 'My groups')}</h1>
          <button
            onClick={() => { setShowJoin(true); setJoinError('') }}
            className="text-xs text-zinc-400 hover:text-white transition-colors px-3 py-1.5 border border-zinc-700 rounded-lg">
            {lbl('Unirse', 'Join')}
          </button>
          <button
            onClick={() => { setShowCreate(true); setCreateError('') }}
            className="flex items-center gap-1.5 text-xs bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-3 py-1.5 rounded-lg transition-colors">
            <Plus size={14} />
            {lbl('Crear', 'Create')}
          </button>
        </div>
      </header>

      <main className="max-w-xl mx-auto px-4 py-6">
        {groups.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <Users size={28} className="text-emerald-400" />
            </div>
            <h2 className="text-lg font-semibold text-white mb-2">{lbl('Sin grupos', 'No groups yet')}</h2>
            <p className="text-zinc-500 text-sm mb-6">
              {lbl('Crea un grupo para jugar con tus amigos o únete con un código.', 'Create a group to play with friends or join with a code.')}
            </p>
            <div className="flex gap-3 justify-center">
              <button onClick={() => setShowCreate(true)}
                className="bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-5 py-2 rounded-full text-sm transition-colors">
                {lbl('Crear grupo', 'Create group')}
              </button>
              <button onClick={() => setShowJoin(true)}
                className="bg-zinc-800 hover:bg-zinc-700 text-white font-semibold px-5 py-2 rounded-full text-sm transition-colors">
                {lbl('Unirse', 'Join')}
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="divide-y divide-zinc-800">
              {groups.map(g => (
                <Link key={g.id} href={`/${locale}/groups/${g.id}`}
                  className="flex items-center gap-3 px-4 py-4 hover:bg-zinc-800/50 transition-colors group">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-emerald-500/20 transition-colors">
                    <Users size={18} className="text-emerald-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm font-semibold text-white truncate">{g.name}</p>
                      {g.is_private
                        ? <Lock size={11} className="text-zinc-500 flex-shrink-0" />
                        : <Globe size={11} className="text-zinc-600 flex-shrink-0" />
                      }
                    </div>
                    <p className="text-xs text-zinc-500">
                      {g.member_count} {lbl('miembros', 'members')}
                      {g.my_role === 'owner' && ` · ${lbl('Creador', 'Owner')}`}
                      {g.my_role === 'admin' && ` · Admin`}
                    </p>
                  </div>
                  <ChevronRight size={16} className="text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
                </Link>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/70 flex items-end sm:items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-bold text-white">{lbl('Nuevo grupo', 'New group')}</h2>
              <button onClick={() => setShowCreate(false)} className="text-zinc-500 hover:text-white">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-zinc-400 block mb-1.5">{lbl('Nombre del grupo', 'Group name')}</label>
                <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors"
                  placeholder={lbl('Mi grupo de golf', 'My golf group')} required />
              </div>
              <div>
                <label className="text-xs font-medium text-zinc-400 block mb-1.5">{lbl('Descripción (opcional)', 'Description (optional)')}</label>
                <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors resize-none"
                  rows={2} placeholder={lbl('Jugamos los sábados…', 'We play on Saturdays…')} />
              </div>
              <label className="flex items-center gap-3 cursor-pointer">
                <div className={`w-10 h-6 rounded-full transition-colors ${form.is_private ? 'bg-emerald-500' : 'bg-zinc-700'}`}
                  onClick={() => setForm({ ...form, is_private: !form.is_private })}>
                  <div className={`w-5 h-5 rounded-full bg-white mt-0.5 transition-transform ${form.is_private ? 'translate-x-4' : 'translate-x-0.5'}`} />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{lbl('Grupo privado', 'Private group')}</p>
                  <p className="text-xs text-zinc-500">{lbl('Solo con código de invitación', 'Invite code only')}</p>
                </div>
              </label>
              {createError && (
                <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">{createError}</p>
              )}
              <button type="submit" disabled={creating}
                className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-2.5 rounded-xl transition-colors flex items-center justify-center gap-2">
                {creating && <Loader2 size={16} className="animate-spin" />}
                {lbl('Crear grupo', 'Create group')}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Join modal */}
      {showJoin && (
        <div className="fixed inset-0 bg-black/70 flex items-end sm:items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-bold text-white">{lbl('Unirse a un grupo', 'Join a group')}</h2>
              <button onClick={() => setShowJoin(false)} className="text-zinc-500 hover:text-white">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleJoin} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-zinc-400 block mb-1.5">{lbl('Código de invitación', 'Invite code')}</label>
                <input type="text" value={joinCode} onChange={e => setJoinCode(e.target.value.toUpperCase())}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors tracking-widest font-mono uppercase"
                  placeholder="XXXXXXXX" maxLength={8} required />
              </div>
              {joinError && (
                <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">{joinError}</p>
              )}
              <button type="submit" disabled={joining}
                className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-2.5 rounded-xl transition-colors flex items-center justify-center gap-2">
                {joining && <Loader2 size={16} className="animate-spin" />}
                {lbl('Unirse', 'Join')}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
