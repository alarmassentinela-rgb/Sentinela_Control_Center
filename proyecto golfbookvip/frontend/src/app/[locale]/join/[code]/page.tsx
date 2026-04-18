'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Flag, Loader2, MapPin, Calendar, Users, CheckCircle2, LogIn, UserPlus, Crown, Trophy } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface RoundInfo {
  id: string
  name: string | null
  course_name: string | null
  game_format: string
  status: string
  holes_to_play: number
  scheduled_at: string
  player_count: number
  invite_code: string
  notes: string | null
}

const FORMAT_LABELS: Record<string, { es: string; en: string }> = {
  stroke: { es: 'Stroke Play', en: 'Stroke Play' },
  stableford: { es: 'Stableford', en: 'Stableford' },
  stableford_modified: { es: 'Stableford Modificado', en: 'Modified Stableford' },
  match: { es: 'Match Play', en: 'Match Play' },
  skins: { es: 'Skins', en: 'Skins' },
  florida: { es: 'Florida', en: 'Florida' },
}

// Inauguration window: April 17–19 2026 (covers MX timezone UTC-6)
const isFounderDay = (() => {
  const now = Date.now()
  const start = new Date('2026-04-17T00:00:00-06:00').getTime()
  const end   = new Date('2026-04-20T06:00:00-06:00').getTime()
  return now >= start && now <= end
})()

export default function JoinRoundPage() {
  const locale = useLocale()
  const router = useRouter()
  const { code } = useParams<{ code: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [roundInfo, setRoundInfo] = useState<RoundInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [joining, setJoining] = useState(false)
  const [joined, setJoined] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    setIsLoggedIn(!!token)

    api.get(`/rounds/join/${code}`)
      .then(r => setRoundInfo(r.data))
      .catch(() => setError(lbl('Código de invitación inválido o expirado.', 'Invalid or expired invite code.')))
      .finally(() => setLoading(false))
  }, [code])

  const handleJoin = async () => {
    if (!isLoggedIn) {
      router.push(`/${locale}/auth/login?invite=${code}`)
      return
    }
    setJoining(true)
    try {
      await api.post(`/rounds/join/${code}`)
      setJoined(true)
      setTimeout(() => router.push(`/${locale}/rounds/${roundInfo?.id}`), 1500)
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

  const roundName = roundInfo?.name ?? (locale === 'es' ? 'Ronda de golf' : 'Golf round')
  const formattedDate = roundInfo
    ? new Date(roundInfo.scheduled_at).toLocaleString(
        locale === 'es' ? 'es-MX' : 'en-US',
        { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }
      )
    : ''

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center px-4 py-12">
      {/* Logo */}
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
              <Link href={`/${locale}/dashboard`}
                className="text-sm text-zinc-400 hover:text-white transition-colors">
                {lbl('Ir al inicio', 'Go home')}
              </Link>
            </div>

          ) : roundInfo ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl">

              {/* ── Invitation headline ─────────────────────────────────── */}
              <div className="px-6 pt-6 pb-5 border-b border-zinc-800 text-center">
                <div className="flex items-center justify-center gap-2 mb-3">
                  <Trophy size={16} className="text-emerald-400" />
                  <span className="text-xs text-emerald-400 font-semibold uppercase tracking-widest">
                    {lbl('Invitación a jugar golf', 'Golf round invitation')}
                  </span>
                </div>

                <h1 className="text-2xl font-bold text-white leading-tight mb-2">
                  {roundName}
                </h1>

                <p className="text-zinc-400 text-sm leading-relaxed">
                  {lbl(
                    'Te invitamos a esta jugada de golf.',
                    'You have been invited to this golf round.'
                  )}
                  {' '}
                  <span className="text-white font-medium">
                    {lbl('Da clic para confirmar tu asistencia.', 'Click below to confirm your attendance.')}
                  </span>
                </p>
              </div>

              {/* ── Details ─────────────────────────────────────────────── */}
              <div className="px-6 py-5 space-y-3">
                {roundInfo.course_name && (
                  <div className="flex items-center gap-3 text-sm text-zinc-300">
                    <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
                      <MapPin size={14} className="text-emerald-400" />
                    </div>
                    <div>
                      <p className="text-xs text-zinc-500 mb-0.5">{lbl('Campo', 'Course')}</p>
                      <p className="font-medium text-white">{roundInfo.course_name}</p>
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-3 text-sm text-zinc-300">
                  <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
                    <Calendar size={14} className="text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500 mb-0.5">{lbl('Fecha y hora', 'Date & time')}</p>
                    <p className="font-medium text-white capitalize">{formattedDate}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-sm text-zinc-300">
                  <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
                    <Users size={14} className="text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500 mb-0.5">{lbl('Confirmados', 'Confirmed')}</p>
                    <p className="font-medium text-white">
                      {roundInfo.player_count} {lbl('jugador(es)', 'player(s)')}
                    </p>
                  </div>
                </div>

                {/* Notes */}
                {roundInfo.notes && (
                  <div className="bg-zinc-800/60 border border-zinc-700/60 rounded-xl px-4 py-3 mt-1">
                    <p className="text-xs text-zinc-500 mb-1 uppercase tracking-wide font-medium">
                      {lbl('Notas', 'Notes')}
                    </p>
                    <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">
                      {roundInfo.notes}
                    </p>
                  </div>
                )}

                {/* Pills */}
                <div className="flex flex-wrap gap-2 pt-1">
                  <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full font-medium">
                    {FORMAT_LABELS[roundInfo.game_format]?.[locale === 'es' ? 'es' : 'en'] ?? roundInfo.game_format}
                  </span>
                  <span className="text-xs bg-zinc-800 text-zinc-400 px-3 py-1 rounded-full">
                    {roundInfo.holes_to_play} {lbl('hoyos', 'holes')}
                  </span>
                  {roundInfo.status === 'active' && (
                    <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full animate-pulse">
                      {lbl('En juego ahora', 'In progress now')}
                    </span>
                  )}
                </div>
              </div>

              {/* ── CTA ─────────────────────────────────────────────────── */}
              <div className="px-6 pb-6 space-y-3">
                {joined ? (
                  <div className="flex flex-col items-center justify-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold py-5 rounded-2xl">
                    <CheckCircle2 size={28} />
                    <p className="text-base">{lbl('¡Asistencia confirmada!', 'Attendance confirmed!')}</p>
                    <p className="text-xs text-emerald-400/70">{lbl('Redirigiendo...', 'Redirecting...')}</p>
                  </div>

                ) : roundInfo.status === 'finished' ? (
                  <p className="text-center text-sm text-zinc-500 py-4">
                    {lbl('Esta ronda ya finalizó.', 'This round has ended.')}
                  </p>

                ) : isLoggedIn ? (
                  <button onClick={handleJoin} disabled={joining}
                    className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-bold py-4 rounded-2xl transition-colors text-base active:scale-95">
                    {joining ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
                    {lbl('Confirmar asistencia', 'Confirm attendance')}
                  </button>

                ) : (
                  <>
                    {/* ── Founding Member Banner ── */}
                    {isFounderDay && (
                      <div className="rounded-xl overflow-hidden">
                        <div className="bg-gradient-to-r from-amber-500/20 via-yellow-400/15 to-amber-500/20 border border-amber-400/40 px-4 py-3">
                          <div className="flex items-center gap-2 mb-1">
                            <Crown size={15} className="text-amber-400 flex-shrink-0" />
                            <span className="text-amber-300 font-bold text-sm tracking-wide uppercase">
                              {lbl('Miembro Fundador', 'Founding Member')}
                            </span>
                          </div>
                          <p className="text-xs text-amber-200/80 leading-snug">
                            {lbl(
                              'Al registrarte hoy — día de inauguración — obtienes acceso Premium Vitalicio a GolfBookVIP sin costo adicional, para siempre.',
                              'By registering today — inauguration day — you get Lifetime Premium access to GolfBookVIP at no extra cost, forever.'
                            )}
                          </p>
                        </div>
                      </div>
                    )}

                    <button onClick={() => router.push(`/${locale}/auth/register?invite=${code}`)}
                      className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-bold py-4 rounded-2xl transition-colors text-base active:scale-95">
                      <UserPlus size={18} />
                      {lbl('Registrarme y confirmar asistencia', 'Register & confirm attendance')}
                    </button>
                    <button onClick={() => router.push(`/${locale}/auth/login?invite=${code}`)}
                      className="w-full flex items-center justify-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-white font-medium py-3.5 rounded-2xl transition-colors border border-zinc-700">
                      <LogIn size={16} />
                      {lbl('Ya tengo cuenta — Entrar', 'I have an account — Sign in')}
                    </button>
                  </>
                )}
              </div>

              {/* Footer note */}
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
