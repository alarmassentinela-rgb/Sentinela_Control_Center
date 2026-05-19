'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Settings, Loader2, AlertCircle, Lock, Unlock, Globe, Users, Calendar, CreditCard, CheckCircle2, Info, Link2, QrCode, Copy, Check, RotateCw, Mail } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface ClubSettings {
  access_type: 'private' | 'semi_private' | 'public'
  allow_guests: boolean
  guest_requires_sponsor: boolean
  max_guests_per_booking: number
  max_guest_visits_per_year: number
  guest_fee_to_sponsor: boolean
  members_advance_days: number
  public_advance_days: number
  invite_code: string | null
  default_membership_type_id: number | null
}

interface MembershipType {
  id: number
  name: string
  monthly_fee: number
  is_active: boolean
}

interface MyRole {
  role: string | null
  is_superadmin: boolean
  can_manage_members: boolean
  can_manage_membership_types: boolean
}

const ACCESS_TYPES = [
  {
    value: 'private', icon: Lock, color: 'red',
    es: { name: 'Privado', desc: 'Solo socios y sus invitados (con sponsor). Sin reservas del público.' },
    en: { name: 'Private', desc: 'Members only and their sponsored guests. No public bookings.' },
  },
  {
    value: 'semi_private', icon: Users, color: 'amber',
    es: { name: 'Híbrido', desc: 'Socios con prioridad y precios preferenciales. Público puede reservar con restricciones de horario y tarifa.' },
    en: { name: 'Hybrid', desc: 'Members get priority and member rates. Public can book with time/rate restrictions.' },
  },
  {
    value: 'public', icon: Globe, color: 'emerald',
    es: { name: 'Público', desc: 'Cualquiera reserva pagando tarifa pública. Sin restricciones de padrón.' },
    en: { name: 'Public', desc: 'Anyone can book paying the public rate. No member restrictions.' },
  },
] as const

export default function ClubSettingsPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [readOnly, setReadOnly] = useState(false)
  const [settings, setSettings] = useState<ClubSettings | null>(null)
  const [types, setTypes] = useState<MembershipType[]>([])
  const [saving, setSaving] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [clubName, setClubName] = useState('')
  const [copied, setCopied] = useState(false)
  const [rotating, setRotating] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [roleRes, clubRes, settingsRes, typesRes] = await Promise.all([
        api.get(`/clubs/${params.id}/my-role`),
        api.get(`/clubs/${params.id}/dashboard`),
        api.get(`/clubs/${params.id}/settings`),
        api.get(`/clubs/${params.id}/membership-types`),
      ])
      const role: MyRole = roleRes.data
      const canEdit = role.is_superadmin || role.role === 'owner' || role.role === 'admin'
      setReadOnly(!canEdit)
      setClubName(clubRes.data.name)
      setSettings(settingsRes.data)
      setTypes(typesRes.data || [])
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 403) setForbidden(true)
    } finally { setLoading(false) }
  }

  const inviteUrl = (() => {
    if (!settings?.invite_code) return ''
    if (typeof window === 'undefined') return ''
    return `${window.location.origin}/${locale}/join-club/${settings.invite_code}`
  })()

  const copyInvite = async () => {
    if (!inviteUrl) return
    try {
      await navigator.clipboard.writeText(inviteUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch { /* ignore */ }
  }

  const downloadQr = () => {
    if (!inviteUrl || !settings?.invite_code) return
    const svg = document.getElementById('settings-invite-qr')
    if (!svg) return
    const serializer = new XMLSerializer()
    const svgStr = serializer.serializeToString(svg)
    const blob = new Blob([svgStr], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `invitacion-${settings.invite_code}.svg`
    a.click()
    URL.revokeObjectURL(url)
  }

  const rotateCode = async () => {
    if (!confirm(lbl(
      '¿Rotar el código? El código actual dejará de funcionar de inmediato y los socios deberán usar el nuevo.',
      'Rotate the code? The current code will stop working immediately and members must use the new one.'
    ))) return
    setRotating(true)
    try {
      const res = await api.post(`/clubs/${params.id}/invite-code/rotate`)
      if (settings) setSettings({ ...settings, invite_code: res.data.invite_code })
      setSavedFlash(true)
      setTimeout(() => setSavedFlash(false), 1500)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al rotar', 'Error rotating'))
    } finally { setRotating(false) }
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const update = async (patch: Partial<ClubSettings>) => {
    if (!settings || readOnly) return
    setSaving(true)
    try {
      await api.patch(`/clubs/${params.id}/settings`, patch)
      setSettings({ ...settings, ...patch })
      setSavedFlash(true)
      setTimeout(() => setSavedFlash(false), 1500)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al guardar', 'Error saving'))
    } finally { setSaving(false) }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )
  if (forbidden) return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 px-4">
      <AlertCircle size={48} className="text-red-500/50" />
      <p className="text-white font-bold text-xl">{lbl('Acceso denegado', 'Access denied')}</p>
      <Link href={`/${locale}/dashboard`} className="mt-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-5 py-2.5 rounded-xl text-sm">{lbl('Volver', 'Back')}</Link>
    </div>
  )
  if (!settings) return null

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-3">
          <Link href={`/${locale}/club/${params.id}`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} /> {clubName || lbl('Club', 'Club')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <Settings size={14} className="text-zinc-400" />
            {lbl('Configuración', 'Settings')}
          </h1>
          <div className="w-12">
            {savedFlash && <span className="text-xs text-emerald-400 font-semibold animate-pulse">✓ {lbl('Guardado', 'Saved')}</span>}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-5 space-y-5">
        {readOnly && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-3 flex items-center gap-2">
            <Info size={14} className="text-amber-400 flex-shrink-0" />
            <p className="text-xs text-amber-200">{lbl('Vista de solo lectura. Solo Owner y Admin pueden modificar la configuración.', 'Read-only view. Only Owner and Admin can change settings.')}</p>
          </div>
        )}

        {/* Invitación de socios (v1.16.0) */}
        <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
          <h2 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
            <Mail size={14} className="text-emerald-400" />
            {lbl('Invitación de socios', 'Member invitation')}
          </h2>
          <p className="text-xs text-zinc-500 mb-4">
            {lbl(
              'Comparte un link o código QR único. Cuando un socio se registra desde ahí, queda vinculado automáticamente al padrón del club.',
              'Share a unique link or QR code. When members register through it, they are automatically linked to the club roster.'
            )}
          </p>

          {settings.invite_code ? (
            <div className="space-y-4">
              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 text-center">
                <p className="text-[10px] text-emerald-400/80 uppercase tracking-widest font-semibold mb-2">{lbl('Código de tu club', 'Your club code')}</p>
                <p className="text-2xl font-bold text-emerald-300 font-mono tracking-wider">{settings.invite_code}</p>
              </div>

              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Liga de invitación', 'Invitation link')}</label>
                <div className="flex gap-1">
                  <input readOnly value={inviteUrl}
                    onFocus={(e) => e.target.select()}
                    className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-xs font-mono" />
                  <button onClick={copyInvite}
                    className="bg-emerald-500 hover:bg-emerald-400 text-white px-3 rounded-lg text-xs font-semibold flex items-center gap-1.5">
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? lbl('Copiado', 'Copied') : lbl('Copiar', 'Copy')}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-center">
                <div className="bg-white p-3 rounded-xl flex items-center justify-center">
                  <QRCodeSVG id="settings-invite-qr" value={inviteUrl || ' '} size={160} />
                </div>
                <div className="space-y-2">
                  <button onClick={downloadQr}
                    className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                    <QrCode size={14} /> {lbl('Descargar QR', 'Download QR')}
                  </button>
                  {!readOnly && (
                    <button onClick={rotateCode} disabled={rotating}
                      className="w-full bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                      {rotating ? <Loader2 size={14} className="animate-spin" /> : <RotateCw size={14} />}
                      {lbl('Rotar código', 'Rotate code')}
                    </button>
                  )}
                </div>
              </div>

              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">
                  {lbl('Tipo de membresía por defecto', 'Default membership type')}
                </label>
                <select value={settings.default_membership_type_id ?? ''}
                  disabled={readOnly || saving}
                  onChange={e => update({ default_membership_type_id: e.target.value ? parseInt(e.target.value) : null })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm disabled:opacity-60">
                  <option value="">{lbl('— Sin tipo (el admin asigna después) —', '— None (admin assigns later) —')}</option>
                  {types.filter(t => t.is_active).map(t => (
                    <option key={t.id} value={t.id}>{t.name} (${t.monthly_fee.toFixed(0)}/mes)</option>
                  ))}
                </select>
                <p className="text-[10px] text-zinc-500 mt-1 leading-relaxed">
                  {lbl(
                    'Es el tipo que se asigna automáticamente a quien se registra usando este link/QR. Puedes ajustarlo por socio luego desde el padrón.',
                    'This type is automatically assigned to anyone registering via this link/QR. You can adjust it per member from the roster.'
                  )}
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center text-sm text-zinc-500 py-6">
              {lbl('Este club todavía no tiene código de invitación.', 'This club has no invitation code yet.')}
            </div>
          )}
        </section>

        {/* Tipo de acceso */}
        <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
          <h2 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
            <Lock size={14} className="text-blue-400" />
            {lbl('Tipo de acceso', 'Access type')}
          </h2>
          <p className="text-xs text-zinc-500 mb-4">{lbl('Define quién puede reservar tee times en tu club.', 'Defines who can book tee times at your club.')}</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {ACCESS_TYPES.map(t => {
              const selected = settings.access_type === t.value
              const Icon = t.icon
              const colorMap: Record<string, string> = {
                red: 'border-red-500/40 bg-red-500/10 text-red-300',
                amber: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
                emerald: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
              }
              return (
                <button key={t.value} disabled={readOnly || saving}
                  onClick={() => update({ access_type: t.value as ClubSettings['access_type'] })}
                  className={`text-left p-4 rounded-xl border-2 transition-all ${
                    selected
                      ? colorMap[t.color]
                      : 'border-zinc-800 bg-zinc-900 text-zinc-300 hover:border-zinc-700'
                  } ${readOnly ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <Icon size={18} />
                    {selected && <CheckCircle2 size={14} />}
                  </div>
                  <p className="font-bold text-sm">{lbl(t.es.name, t.en.name)}</p>
                  <p className="text-[10px] text-zinc-400 mt-1 leading-relaxed">{lbl(t.es.desc, t.en.desc)}</p>
                </button>
              )
            })}
          </div>
        </section>

        {/* Política de invitados */}
        <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
          <h2 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
            <Users size={14} className="text-purple-400" />
            {lbl('Política de invitados', 'Guest policy')}
          </h2>
          <p className="text-xs text-zinc-500 mb-4">{lbl('Reglas para personas externas que vienen a jugar con socios.', 'Rules for external people coming to play with members.')}</p>

          <div className="space-y-3">
            <Toggle label={lbl('Permitir invitados', 'Allow guests')}
              desc={lbl('Si está apagado, solo socios pueden reservar y jugar.', 'If off, only members can book and play.')}
              value={settings.allow_guests}
              onChange={v => update({ allow_guests: v })}
              disabled={readOnly || saving} />

            <Toggle label={lbl('Invitado requiere sponsor', 'Guest requires sponsor')}
              desc={lbl('El invitado debe venir asociado a un socio que lo invita. Solo aplica en clubes privados o híbridos.', 'Guest must come with a sponsoring member. Only applies in private or hybrid clubs.')}
              value={settings.guest_requires_sponsor}
              onChange={v => update({ guest_requires_sponsor: v })}
              disabled={readOnly || saving || !settings.allow_guests} />

            <Toggle label={lbl('Green fee de invitado lo paga el socio', 'Guest fee paid by sponsor')}
              desc={lbl('Si está activado, los cargos de invitados van a la cuenta del socio que los invita.', 'If on, guest charges go to the sponsoring member account.')}
              value={settings.guest_fee_to_sponsor}
              onChange={v => update({ guest_fee_to_sponsor: v })}
              disabled={readOnly || saving || !settings.allow_guests} />

            <NumField label={lbl('Máximo de invitados por reserva', 'Max guests per booking')}
              desc={lbl('En una reserva de un socio, cuántos invitados puede traer (ej. 3 = foursome con 1 socio + 3 invitados).', 'In a member booking, how many guests they can bring (e.g. 3 = foursome with 1 member + 3 guests).')}
              value={settings.max_guests_per_booking}
              onChange={v => update({ max_guests_per_booking: v })}
              min={0} max={10}
              disabled={readOnly || saving || !settings.allow_guests} />

            <NumField label={lbl('Visitas máximas por invitado al año', 'Max visits per guest per year')}
              desc={lbl('Un mismo invitado solo puede venir N veces al año antes de tener que asociarse como socio.', 'Same guest can come at most N times per year before having to become a member.')}
              value={settings.max_guest_visits_per_year}
              onChange={v => update({ max_guest_visits_per_year: v })}
              min={0} max={365}
              disabled={readOnly || saving || !settings.allow_guests} />
          </div>
        </section>

        {/* Ventanas de reserva */}
        <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
          <h2 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
            <Calendar size={14} className="text-amber-400" />
            {lbl('Ventanas de reserva', 'Booking windows')}
          </h2>
          <p className="text-xs text-zinc-500 mb-4">{lbl('Cuántos días antes pueden socios y público reservar tee times.', 'How many days in advance members and public can book tee times.')}</p>

          <div className="space-y-3">
            <NumField label={lbl('Anticipación para socios (días)', 'Member advance (days)')}
              desc={lbl('Los socios pueden reservar slots con esta anticipación. Típico: 14-30 días.', 'Members can book this many days ahead. Typical: 14-30 days.')}
              value={settings.members_advance_days}
              onChange={v => update({ members_advance_days: v })}
              min={0} max={365}
              disabled={readOnly || saving} />

            <NumField label={lbl('Anticipación para público (días)', 'Public advance (days)')}
              desc={lbl('Solo aplica en híbrido/público. El público puede reservar con esta anticipación. Típico: 7 días.', 'Only applies in hybrid/public. Public can book this many days ahead. Typical: 7 days.')}
              value={settings.public_advance_days}
              onChange={v => update({ public_advance_days: v })}
              min={0} max={365}
              disabled={readOnly || saving || settings.access_type === 'private'} />
          </div>
        </section>
      </main>
    </div>
  )
}

function Toggle({ label, desc, value, onChange, disabled }: {
  label: string; desc: string; value: boolean; onChange: (v: boolean) => void; disabled?: boolean
}) {
  return (
    <div className={`flex items-start justify-between gap-4 py-2 ${disabled ? 'opacity-60' : ''}`}>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="text-xs text-zinc-500 leading-relaxed">{desc}</p>
      </div>
      <button onClick={() => !disabled && onChange(!value)} disabled={disabled}
        className={`w-11 h-6 rounded-full flex-shrink-0 transition-colors relative ${
          value ? 'bg-emerald-500' : 'bg-zinc-700'
        } ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
        <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-transform ${value ? 'left-5' : 'left-0.5'}`} />
      </button>
    </div>
  )
}

function NumField({ label, desc, value, onChange, min, max, disabled }: {
  label: string; desc: string; value: number; onChange: (v: number) => void; min: number; max: number; disabled?: boolean
}) {
  return (
    <div className={`flex items-start justify-between gap-4 py-2 ${disabled ? 'opacity-60' : ''}`}>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="text-xs text-zinc-500 leading-relaxed">{desc}</p>
      </div>
      <input type="number" min={min} max={max} value={value} disabled={disabled}
        onChange={e => {
          const v = parseInt(e.target.value)
          if (!isNaN(v) && v >= min && v <= max) onChange(v)
        }}
        className="w-20 bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm font-bold text-center disabled:cursor-not-allowed" />
    </div>
  )
}
