'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Flag, Loader2, MapPin, Users, CheckCircle2, LogIn, UserPlus, Building2 } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface ClubJoinInfo {
  club_id: string
  name: string
  logo_url: string | null
  city: string | null
  country: string | null
  members_count: number
}

export default function JoinClubPage() {
  const locale = useLocale()
  const router = useRouter()
  const { code } = useParams<{ code: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [clubInfo, setClubInfo] = useState<ClubJoinInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [joining, setJoining] = useState(false)
  const [joined, setJoined] = useState(false)
  const [alreadyMember, setAlreadyMember] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  useEffect(() => {
    const token = isAuthed()
    setIsLoggedIn(!!token)

    api.get(`/clubs/by-code/${code}`)
      .then(r => setClubInfo(r.data))
      .catch(() => setError(lbl('Código de invitación inválido o expirado.', 'Invalid or expired invite code.')))
      .finally(() => setLoading(false))
  }, [code])

  const handleJoin = async () => {
    if (!isLoggedIn) {
      router.push(`/${locale}/auth/login?club_code=${code}`)
      return
    }
    setJoining(true)
    try {
      const res = await api.post('/clubs/by-code/join', { invite_code: code })
      if (res.data.already_member) {
        setAlreadyMember(true)
        setTimeout(() => router.push(`/${locale}/club/${res.data.club_id}`), 1200)
      } else {
        setJoined(true)
        setTimeout(() => router.push(`/${locale}/club/${res.data.club_id}`), 1500)
      }
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? lbl('Error al unirse', 'Error joining'))
      setJoining(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center px-4 py-12">
      <div className="flex items-center gap-2 mb-8">
        <div className="w-9 h-9 rounded-full bg-emerald-500 flex items-center justify-center">
          <Flag size={18} className="text-white" />
        </div>
        <span className="font-bold text-xl text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
      </div>

      <div className="w-full max-w-md">
        {error ? (
          <div className="bg-zinc-900 border border-red-500/30 rounded-2xl p-8 text-center mt-6">
            <p className="text-red-400 font-medium mb-4">{error}</p>
            <Link href={`/${locale}/dashboard`} className="text-sm text-zinc-400 hover:text-white transition-colors">
              {lbl('Ir al inicio', 'Go home')}
            </Link>
          </div>
        ) : clubInfo ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl">
            {/* Header del club */}
            <div className="px-6 pt-6 pb-5 border-b border-zinc-800 text-center">
              <div className="flex items-center justify-center gap-2 mb-3">
                <Building2 size={16} className="text-emerald-400" />
                <span className="text-xs text-emerald-400 font-semibold uppercase tracking-widest">
                  {lbl('Invitación de tu club', 'Club invitation')}
                </span>
              </div>

              {clubInfo.logo_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={clubInfo.logo_url} alt={clubInfo.name}
                  className="w-20 h-20 rounded-full object-cover mx-auto mb-3 border border-zinc-700" />
              )}

              <h1 className="text-2xl font-bold text-white leading-tight mb-2">
                {clubInfo.name}
              </h1>

              <p className="text-zinc-400 text-sm leading-relaxed">
                {lbl(
                  'Te damos la bienvenida al padrón digital de tu club.',
                  'Welcome to your club’s digital roster.'
                )}
              </p>
            </div>

            {/* Detalles */}
            <div className="px-6 py-5 space-y-3">
              {(clubInfo.city || clubInfo.country) && (
                <div className="flex items-center gap-3 text-sm text-zinc-300">
                  <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
                    <MapPin size={14} className="text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500 mb-0.5">{lbl('Ubicación', 'Location')}</p>
                    <p className="font-medium text-white">
                      {[clubInfo.city, clubInfo.country].filter(Boolean).join(', ')}
                    </p>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 text-sm text-zinc-300">
                <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
                  <Users size={14} className="text-emerald-400" />
                </div>
                <div>
                  <p className="text-xs text-zinc-500 mb-0.5">{lbl('Socios registrados', 'Registered members')}</p>
                  <p className="font-medium text-white">
                    {clubInfo.members_count}
                  </p>
                </div>
              </div>
            </div>

            {/* CTA */}
            <div className="px-6 pb-6 space-y-3">
              {alreadyMember ? (
                <div className="flex flex-col items-center justify-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold py-5 rounded-2xl">
                  <CheckCircle2 size={28} />
                  <p className="text-base">{lbl('Ya eres socio de este club', 'You are already a member')}</p>
                  <p className="text-xs text-emerald-400/70">{lbl('Llevándote al panel...', 'Taking you to the panel...')}</p>
                </div>
              ) : joined ? (
                <div className="flex flex-col items-center justify-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold py-5 rounded-2xl">
                  <CheckCircle2 size={28} />
                  <p className="text-base">{lbl('¡Bienvenido al club!', 'Welcome to the club!')}</p>
                  <p className="text-xs text-emerald-400/70">{lbl('Redirigiendo...', 'Redirecting...')}</p>
                </div>
              ) : isLoggedIn ? (
                <button onClick={handleJoin} disabled={joining}
                  className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-bold py-4 rounded-2xl transition-colors text-base active:scale-95">
                  {joining ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
                  {lbl('Unirme al club', 'Join the club')}
                </button>
              ) : (
                <>
                  <button onClick={() => router.push(`/${locale}/auth/register?club_code=${code}`)}
                    className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-bold py-4 rounded-2xl transition-colors text-base active:scale-95">
                    <UserPlus size={18} />
                    {lbl('Registrarme y unirme al club', 'Register and join the club')}
                  </button>
                  <button onClick={() => router.push(`/${locale}/auth/login?club_code=${code}`)}
                    className="w-full flex items-center justify-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-white font-medium py-3.5 rounded-2xl transition-colors border border-zinc-700">
                    <LogIn size={16} />
                    {lbl('Ya tengo cuenta — Entrar', 'I have an account — Sign in')}
                  </button>
                </>
              )}
            </div>

            <div className="px-6 pb-5 text-center">
              <p className="text-xs text-zinc-600">
                {lbl('Powered by', 'Powered by')} <span className="text-zinc-500">GolfBookVIP</span>
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
