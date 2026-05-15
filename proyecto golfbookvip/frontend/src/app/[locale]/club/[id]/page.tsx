'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Building2, Users, Shield, Crown, Mail, Phone, MapPin, Globe, Loader2, X, Calendar, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface ClubDashboard {
  id: string
  name: string
  slug: string
  description: string | null
  city: string | null
  country: string | null
  phone: string | null
  email: string | null
  website: string | null
  currency: string
  timezone: string
  is_active: boolean
  is_verified: boolean
  plan: { id: number; code: string; name: string; plan_type: string; price_monthly: number; max_members: number | null } | null
  plan_expires_at: string | null
  member_count: number
  staff_count: number
  created_at: string | null
}

interface StaffMember {
  user_id: string
  first_name: string
  last_name: string
  username: string
  email: string
  role: string
  joined_at: string | null
}

export default function ClubPanelPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const [club, setClub] = useState<ClubDashboard | null>(null)
  const [staff, setStaff] = useState<StaffMember[]>([])
  const [showStaff, setShowStaff] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    const load = async () => {
      try {
        const [dashRes, staffRes] = await Promise.all([
          api.get(`/clubs/${params.id}/dashboard`),
          api.get(`/clubs/${params.id}/staff`).catch(() => ({ data: [] })),
        ])
        setClub(dashRes.data)
        setStaff(staffRes.data || [])
      } catch (e: unknown) {
        const status = (e as { response?: { status?: number } })?.response?.status
        if (status === 403) setForbidden(true)
        else if (status === 404) setNotFound(true)
      } finally { setLoading(false) }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id])

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  if (forbidden) return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 px-4">
      <Shield size={48} className="text-red-500/50" />
      <p className="text-white font-bold text-xl">{lbl('Acceso denegado', 'Access denied')}</p>
      <p className="text-zinc-500 text-sm text-center max-w-sm">
        {lbl('No tienes permisos para ver este panel. Solo el staff del club o súper administradores pueden acceder.',
          'You do not have permission to view this panel. Only club staff or super admins can access.')}
      </p>
      <Link href={`/${locale}/dashboard`} className="mt-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-5 py-2.5 rounded-xl text-sm">
        {lbl('Volver al dashboard', 'Back to dashboard')}
      </Link>
    </div>
  )

  if (notFound || !club) return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 px-4">
      <AlertCircle size={48} className="text-zinc-600" />
      <p className="text-white font-bold text-xl">{lbl('Club no encontrado', 'Club not found')}</p>
      <Link href={`/${locale}/dashboard`} className="mt-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-5 py-2.5 rounded-xl text-sm">
        {lbl('Volver', 'Back')}
      </Link>
    </div>
  )

  const myRole = staff.find(s => s.user_id)?.role ?? null  // placeholder until we wire current user
  const planTone = !club.plan
    ? 'bg-zinc-700 text-zinc-300'
    : club.plan.price_monthly === 0
      ? 'bg-zinc-700 text-zinc-300'
      : club.plan.price_monthly < 100
        ? 'bg-blue-500/20 text-blue-300 border-blue-500/40'
        : 'bg-purple-500/20 text-purple-300 border-purple-500/40'

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} />
            {lbl('Dashboard', 'Dashboard')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <Building2 size={14} className="text-blue-400" />
            {lbl('Panel del Club', 'Club Panel')}
          </h1>
          <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md border ${club.is_active ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-red-500/40 bg-red-500/10 text-red-300'}`}>
            {club.is_active ? lbl('Activo', 'Active') : lbl('Inactivo', 'Inactive')}
          </span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-5 space-y-5">
        {/* Club header card */}
        <div className="bg-gradient-to-br from-blue-500/15 to-zinc-900 border border-blue-500/30 rounded-2xl p-5">
          <div className="flex items-start justify-between mb-3 gap-3 flex-wrap">
            <div>
              <h2 className="text-2xl font-black text-white">{club.name}</h2>
              <p className="text-xs text-zinc-400 font-mono">{club.slug}.golfbookvip.com</p>
              {club.description && <p className="text-sm text-zinc-300 mt-2 max-w-2xl">{club.description}</p>}
            </div>
            <span className={`text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-lg border ${planTone}`}>
              {club.plan?.name ?? lbl('Sin plan', 'No plan')}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">{lbl('Miembros', 'Members')}</p>
              <p className="text-2xl font-black text-blue-400">{club.member_count}</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Staff</p>
              <p className="text-2xl font-black text-emerald-400">{club.staff_count}</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">{lbl('Moneda', 'Currency')}</p>
              <p className="text-2xl font-black text-zinc-200">{club.currency}</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">{lbl('Verificado', 'Verified')}</p>
              <p className={`text-2xl font-black ${club.is_verified ? 'text-emerald-400' : 'text-zinc-500'}`}>{club.is_verified ? '✓' : '—'}</p>
            </div>
          </div>
        </div>

        {/* Contact + Plan info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Mail size={14} className="text-zinc-400" />
              {lbl('Contacto', 'Contact')}
            </h3>
            <div className="space-y-2 text-sm">
              {club.email && (
                <div className="flex items-center gap-2 text-zinc-300">
                  <Mail size={12} className="text-zinc-500" />
                  <a href={`mailto:${club.email}`} className="hover:text-emerald-400">{club.email}</a>
                </div>
              )}
              {club.phone && (
                <div className="flex items-center gap-2 text-zinc-300">
                  <Phone size={12} className="text-zinc-500" />
                  {club.phone}
                </div>
              )}
              {club.website && (
                <div className="flex items-center gap-2 text-zinc-300">
                  <Globe size={12} className="text-zinc-500" />
                  <a href={club.website} target="_blank" rel="noopener noreferrer" className="hover:text-emerald-400 truncate">{club.website}</a>
                </div>
              )}
              {(club.city || club.country) && (
                <div className="flex items-center gap-2 text-zinc-300">
                  <MapPin size={12} className="text-zinc-500" />
                  {[club.city, club.country].filter(Boolean).join(', ')}
                </div>
              )}
              {!club.email && !club.phone && !club.website && !club.city && (
                <p className="text-xs text-zinc-500 italic">{lbl('Sin información de contacto', 'No contact info')}</p>
              )}
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Crown size={14} className="text-purple-400" />
              {lbl('Plan de suscripción', 'Subscription plan')}
            </h3>
            {club.plan ? (
              <div className="space-y-2">
                <p className="text-lg font-bold text-white">{club.plan.name}</p>
                <p className="text-xs text-zinc-500 font-mono">{club.plan.code}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-black text-purple-400">${club.plan.price_monthly.toFixed(0)}</span>
                  <span className="text-xs text-zinc-500">/{lbl('mes', 'mo')}</span>
                </div>
                <p className="text-xs text-zinc-400">
                  {lbl('Hasta', 'Up to')} <strong className="text-zinc-200">{club.plan.max_members ?? '∞'}</strong> {lbl('miembros', 'members')}
                </p>
                {club.plan_expires_at && (
                  <p className="text-xs text-zinc-500 flex items-center gap-1 pt-2 border-t border-zinc-800">
                    <Calendar size={11} />
                    {lbl('Renueva el', 'Renews on')} {new Date(club.plan_expires_at).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US')}
                  </p>
                )}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-zinc-500 mb-2">{lbl('Aún no tienes un plan asignado', 'No plan assigned yet')}</p>
                <p className="text-xs text-zinc-600">{lbl('Contacta al equipo GolfBookVIP para activar tu suscripción.', 'Contact the GolfBookVIP team to activate your subscription.')}</p>
              </div>
            )}
          </div>
        </div>

        {/* Staff list */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Users size={14} className="text-emerald-400" />
              {lbl('Equipo del club', 'Club staff')} <span className="text-xs text-zinc-500 font-normal">({staff.length})</span>
            </h3>
            <button onClick={() => setShowStaff(!showStaff)}
              className="text-xs text-zinc-400 hover:text-white">
              {showStaff ? lbl('Ocultar', 'Hide') : lbl('Ver', 'Show')}
            </button>
          </div>
          {showStaff && (
            <div className="space-y-2">
              {staff.length === 0 ? (
                <p className="text-xs text-zinc-500 italic">{lbl('Sin staff registrado', 'No staff registered')}</p>
              ) : (
                staff.map(s => (
                  <div key={s.user_id} className="bg-zinc-800/50 rounded-lg p-3 flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-bold text-emerald-400">{s.first_name.charAt(0)}{s.last_name.charAt(0)}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white truncate">{s.first_name} {s.last_name}</p>
                      <p className="text-xs text-zinc-500 truncate">@{s.username} · {s.email}</p>
                    </div>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                      s.role === 'owner' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                      s.role === 'admin' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40' :
                      s.role === 'manager' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40' :
                      'bg-zinc-700 text-zinc-300'
                    }`}>
                      {s.role || 'staff'}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Próximas features */}
        <div className="bg-zinc-900 border border-zinc-800 border-dashed rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Building2 size={14} className="text-blue-400" />
            {lbl('Próximamente', 'Coming soon')}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[
              { es: 'Padrón de miembros', en: 'Member roster', sub: { es: 'CRUD + import CSV', en: 'CRUD + CSV import' } },
              { es: 'Reservas de tee times', en: 'Tee time bookings', sub: { es: 'Calendario + horarios', en: 'Calendar + schedule' } },
              { es: 'Estado de cuenta de socios', en: 'Member account statements', sub: { es: 'Cargos, pagos, PDF', en: 'Charges, payments, PDF' } },
              { es: 'Empleados y asistencia', en: 'Employees and attendance', sub: { es: 'Check-in, nómina', en: 'Check-in, payroll' } },
            ].map((f, i) => (
              <div key={i} className="bg-zinc-800/40 rounded-lg p-3 opacity-70">
                <p className="text-sm font-semibold text-zinc-300">{lbl(f.es, f.en)}</p>
                <p className="text-xs text-zinc-500">{lbl(f.sub.es, f.sub.en)}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-zinc-500 mt-4 leading-relaxed">
            {lbl(
              'Estamos construyendo estas funciones para tu club. Te avisaremos cuando estén listas.',
              'We are building these features for your club. We will notify you when they are ready.'
            )}
          </p>
        </div>
      </main>
    </div>
  )
}
