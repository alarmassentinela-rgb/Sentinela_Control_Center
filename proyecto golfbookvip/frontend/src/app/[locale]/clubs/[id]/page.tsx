'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, Users, MapPin, Phone, Mail, UserPlus, UserMinus, Loader2, TrendingUp, Crown } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Club {
  id: string
  name: string
  description: string | null
  city: string | null
  country: string | null
  phone: string | null
  email: string | null
  currency: string
  member_count: number
  is_member: boolean
  role: string | null
}

interface Member {
  user_id: string
  first_name: string
  last_name: string
  username: string
  handicap_index: number | null
  joined_at: string | null
}

export default function ClubDetailPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [club, setClub] = useState<Club | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [joining, setJoining] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isAuthed()) { router.push(`/${locale}/auth/login`); return }
    Promise.all([
      api.get(`/clubs/${id}`),
      api.get(`/clubs/${id}/members`),
    ]).then(([clubRes, membersRes]) => {
      setClub(clubRes.data)
      setMembers(membersRes.data)
    }).catch(() => setError(lbl('Club no encontrado', 'Club not found')))
      .finally(() => setLoading(false))
  }, [id])

  const handleJoin = async () => {
    setJoining(true)
    try {
      await api.post(`/clubs/${id}/join`)
      const [clubRes, membersRes] = await Promise.all([
        api.get(`/clubs/${id}`),
        api.get(`/clubs/${id}/members`),
      ])
      setClub(clubRes.data)
      setMembers(membersRes.data)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? lbl('Error al unirse', 'Error joining'))
    } finally {
      setJoining(false)
    }
  }

  const handleLeave = async () => {
    if (!confirm(lbl('¿Salir del club?', 'Leave this club?'))) return
    setJoining(true)
    try {
      await api.delete(`/clubs/${id}/leave`)
      const [clubRes, membersRes] = await Promise.all([
        api.get(`/clubs/${id}`),
        api.get(`/clubs/${id}/members`),
      ])
      setClub(clubRes.data)
      setMembers(membersRes.data)
    } finally {
      setJoining(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/clubs`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={14} className="text-white" />
            </div>
            <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {error && !club ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <p className="text-zinc-400">{error}</p>
          </div>
        ) : club && (
          <>
            {/* Club header */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                    <Users size={26} className="text-emerald-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h1 className="text-2xl font-bold text-white">{club.name}</h1>
                      {club.role === 'owner' && (
                        <span className="flex items-center gap-1 text-xs bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 px-2 py-0.5 rounded-full">
                          <Crown size={10} />{lbl('Fundador', 'Founder')}
                        </span>
                      )}
                      {club.is_member && club.role !== 'owner' && (
                        <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                          {lbl('Miembro', 'Member')}
                        </span>
                      )}
                    </div>
                    {(club.city || club.country) && (
                      <div className="flex items-center gap-1.5 text-sm text-zinc-400 mb-2">
                        <MapPin size={13} />
                        {[club.city, club.country].filter(Boolean).join(', ')}
                      </div>
                    )}
                    {club.description && <p className="text-sm text-zinc-400">{club.description}</p>}
                    <div className="flex flex-wrap gap-4 mt-3 text-xs text-zinc-500">
                      <span className="flex items-center gap-1"><Users size={12} />{club.member_count} {lbl('miembros', 'members')}</span>
                      {club.phone && <span className="flex items-center gap-1"><Phone size={12} />{club.phone}</span>}
                      {club.email && <span className="flex items-center gap-1"><Mail size={12} />{club.email}</span>}
                    </div>
                  </div>
                </div>

                {/* Join / Leave button */}
                {club.role !== 'owner' && (
                  <div className="flex-shrink-0">
                    {club.is_member ? (
                      <button onClick={handleLeave} disabled={joining}
                        className="flex items-center gap-2 bg-zinc-800 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/40 border border-zinc-700 text-zinc-300 text-sm font-medium px-4 py-2 rounded-xl transition-all">
                        {joining ? <Loader2 size={14} className="animate-spin" /> : <UserMinus size={14} />}
                        {lbl('Salir', 'Leave')}
                      </button>
                    ) : (
                      <button onClick={handleJoin} disabled={joining}
                        className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-colors">
                        {joining ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} />}
                        {lbl('Unirme', 'Join')}
                      </button>
                    )}
                  </div>
                )}
              </div>
              {error && <p className="text-sm text-red-400 mt-3">{error}</p>}
            </div>

            {/* Members */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
              <h2 className="font-semibold text-white mb-4">
                {lbl('Miembros', 'Members')} <span className="text-zinc-500 font-normal text-sm ml-1">({members.length})</span>
              </h2>
              {members.length === 0 ? (
                <p className="text-zinc-500 text-sm">{lbl('Aún no hay miembros', 'No members yet')}</p>
              ) : (
                <div className="divide-y divide-zinc-800">
                  {members.map((m) => (
                    <div key={m.user_id} className="py-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-sm font-bold text-emerald-400">
                          {m.first_name.charAt(0)}{m.last_name.charAt(0)}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white">{m.first_name} {m.last_name}</p>
                          <p className="text-xs text-zinc-500">@{m.username}</p>
                        </div>
                      </div>
                      {m.handicap_index !== null && (
                        <div className="flex items-center gap-1.5 text-sm">
                          <TrendingUp size={13} className="text-emerald-400" />
                          <span className="font-semibold text-emerald-400">{m.handicap_index.toFixed(1)}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
