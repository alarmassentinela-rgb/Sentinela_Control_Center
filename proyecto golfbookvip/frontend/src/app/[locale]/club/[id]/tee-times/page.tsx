'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Calendar, Loader2, X, Plus, Wand2, Lock, Unlock, Trash2, ChevronLeft, ChevronRight, Clock, Users, AlertCircle, CalendarDays } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Booking {
  id: string
  user_id: string
  user_name: string
  user_email: string
  players_count: number
  status: string
  notes: string | null
  booked_at: string | null
}
interface Slot {
  id: number
  date: string
  time: string
  max_players: number
  available_spots: number
  booked_count: number
  is_blocked: boolean
  block_reason: string | null
  tier: 'members_only' | 'members_priority' | 'public'
  green_fee_member: number
  green_fee_guest: number
  green_fee_public: number
  bookings: Booking[]
}
interface MyRole {
  role: string | null
  can_manage_members: boolean
  is_superadmin: boolean
}

function fmtDayLabel(iso: string, locale: string) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US', { weekday: 'short', day: 'numeric', month: 'short' })
}

export default function TeeTimesPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [slots, setSlots] = useState<Slot[]>([])
  const [myRole, setMyRole] = useState<MyRole | null>(null)
  const [clubName, setClubName] = useState('')

  // Navegación por día
  const todayIso = new Date().toISOString().slice(0, 10)
  const [currentDate, setCurrentDate] = useState(todayIso)

  // Modales
  const [showGen, setShowGen] = useState(false)
  const [genForm, setGenForm] = useState({
    date_from: todayIso,
    date_to: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
    time_start: '07:00', time_end: '14:00',
    interval_minutes: 10, max_players: 4,
    tier: 'members_only' as 'members_only' | 'members_priority' | 'public',
    green_fee_member: 0, green_fee_guest: 0, green_fee_public: 0,
  })
  const [generating, setGenerating] = useState(false)

  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({
    date: todayIso, time: '07:00', max_players: 4,
    tier: 'members_only' as 'members_only' | 'members_priority' | 'public',
    green_fee_member: 0, green_fee_guest: 0, green_fee_public: 0,
  })
  const [creating, setCreating] = useState(false)

  const [blockingSlot, setBlockingSlot] = useState<Slot | null>(null)
  const [blockReason, setBlockReason] = useState('')

  const [bookingSlot, setBookingSlot] = useState<Slot | null>(null)
  const [bookForm, setBookForm] = useState({ players_count: 1, notes: '' })
  const [booking, setBooking] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [roleRes, clubRes, slotsRes] = await Promise.all([
        api.get(`/clubs/${params.id}/my-role`),
        api.get(`/clubs/${params.id}/dashboard`),
        api.get(`/clubs/${params.id}/tee-times`, {
          params: { date_from: currentDate, date_to: currentDate },
        }),
      ])
      setMyRole(roleRes.data)
      setClubName(clubRes.data.name)
      setSlots(slotsRes.data || [])
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 403) setForbidden(true)
    } finally { setLoading(false) }
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentDate])

  const canConfig = myRole?.can_manage_members ?? false  // admin+ can configure
  const isAdmin = myRole && (myRole.role === 'admin' || myRole.role === 'owner' || myRole.is_superadmin)

  const shiftDate = (days: number) => {
    const d = new Date(currentDate + 'T00:00:00')
    d.setDate(d.getDate() + days)
    setCurrentDate(d.toISOString().slice(0, 10))
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const res = await api.post(`/clubs/${params.id}/tee-times/generate`, genForm)
      alert(lbl(`✓ Generados ${res.data.created} slots (${res.data.skipped} duplicados omitidos)`,
        `✓ Created ${res.data.created} slots (${res.data.skipped} duplicates skipped)`))
      setShowGen(false)
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al generar', 'Error generating'))
    } finally { setGenerating(false) }
  }

  const handleCreate = async () => {
    setCreating(true)
    try {
      await api.post(`/clubs/${params.id}/tee-times`, createForm)
      setShowCreate(false)
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al crear', 'Error creating'))
    } finally { setCreating(false) }
  }

  const handleBlock = async () => {
    if (!blockingSlot) return
    try {
      await api.patch(`/clubs/${params.id}/tee-times/${blockingSlot.id}`, {
        is_blocked: !blockingSlot.is_blocked,
        block_reason: !blockingSlot.is_blocked ? blockReason : null,
      })
      setBlockingSlot(null)
      setBlockReason('')
      load()
    } catch { alert(lbl('Error', 'Error')) }
  }

  const handleDelete = async (slot: Slot) => {
    if (!confirm(lbl(`¿Eliminar slot ${slot.time}?`, `Delete ${slot.time} slot?`))) return
    try {
      await api.delete(`/clubs/${params.id}/tee-times/${slot.id}`)
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error', 'Error'))
    }
  }

  const handleBook = async () => {
    if (!bookingSlot) return
    setBooking(true)
    try {
      await api.post(`/clubs/${params.id}/tee-times/${bookingSlot.id}/book`, bookForm)
      setBookingSlot(null)
      setBookForm({ players_count: 1, notes: '' })
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al reservar', 'Error booking'))
    } finally { setBooking(false) }
  }

  const handleCancelBooking = async (bookingId: string) => {
    if (!confirm(lbl('¿Cancelar reserva?', 'Cancel booking?'))) return
    try {
      await api.delete(`/clubs/${params.id}/tee-times/bookings/${bookingId}`)
      load()
    } catch { alert(lbl('Error', 'Error')) }
  }

  if (loading && slots.length === 0) return (
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

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
          <Link href={`/${locale}/club/${params.id}`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} /> {clubName || lbl('Club', 'Club')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <Calendar size={14} className="text-amber-400" />
            {lbl('Tee times', 'Tee times')}
          </h1>
          {isAdmin ? (
            <div className="flex gap-1.5">
              <button onClick={() => setShowGen(true)}
                className="flex items-center gap-1.5 bg-purple-500 hover:bg-purple-400 text-white font-semibold px-3 py-1.5 rounded-lg text-xs">
                <Wand2 size={11} /> {lbl('Generar', 'Generate')}
              </button>
              <button onClick={() => setShowCreate(true)}
                className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-3 py-1.5 rounded-lg text-xs">
                <Plus size={11} /> {lbl('Nuevo', 'New')}
              </button>
            </div>
          ) : <div className="w-16" />}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-5 space-y-4">
        {/* Day picker */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-3 flex items-center gap-3">
          <button onClick={() => shiftDate(-1)}
            className="w-9 h-9 bg-zinc-800 hover:bg-zinc-700 rounded-lg flex items-center justify-center text-zinc-400 hover:text-white">
            <ChevronLeft size={16} />
          </button>
          <input type="date" value={currentDate} onChange={e => setCurrentDate(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm flex-1 text-center" />
          <button onClick={() => shiftDate(1)}
            className="w-9 h-9 bg-zinc-800 hover:bg-zinc-700 rounded-lg flex items-center justify-center text-zinc-400 hover:text-white">
            <ChevronRight size={16} />
          </button>
          {currentDate !== todayIso && (
            <button onClick={() => setCurrentDate(todayIso)}
              className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-2 rounded-lg text-xs">{lbl('Hoy', 'Today')}</button>
          )}
        </div>

        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-lg font-bold text-white capitalize">{fmtDayLabel(currentDate, locale)}</h2>
          <span className="text-xs text-zinc-500">{slots.length} {lbl('slots', 'slots')}</span>
        </div>

        {/* Slots grid */}
        {slots.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <CalendarDays size={42} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-400 text-sm mb-2">{lbl('No hay slots para este día', 'No slots for this day')}</p>
            {isAdmin && (
              <button onClick={() => setShowGen(true)}
                className="mt-3 bg-purple-500 hover:bg-purple-400 text-white text-xs font-semibold px-4 py-2 rounded-lg inline-flex items-center gap-1.5">
                <Wand2 size={12} /> {lbl('Generar slots', 'Generate slots')}
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {slots.map(s => {
              const full = s.available_spots <= 0
              const pct = (s.booked_count / s.max_players) * 100
              return (
                <div key={s.id}
                  className={`bg-zinc-900 border rounded-2xl p-4 ${
                    s.is_blocked ? 'border-red-500/30 bg-red-500/5' :
                    full ? 'border-orange-500/30' :
                    'border-zinc-800'
                  }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="text-2xl font-black text-white flex items-center gap-2">
                        <Clock size={16} className="text-amber-400" />
                        {s.time}
                      </p>
                      {s.is_blocked && (
                        <p className="text-[10px] text-red-300 uppercase tracking-wider font-bold mt-1">
                          🚫 {lbl('Bloqueado', 'Blocked')}{s.block_reason ? `: ${s.block_reason}` : ''}
                        </p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-zinc-500 uppercase">{lbl('Cupo', 'Slots')}</p>
                      <p className={`text-sm font-bold ${full ? 'text-orange-400' : 'text-emerald-400'}`}>
                        {s.booked_count}/{s.max_players}
                      </p>
                    </div>
                  </div>
                  {/* Tier + pricing */}
                  <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${
                      s.tier === 'members_only' ? 'bg-red-500/15 text-red-300 border-red-500/40' :
                      s.tier === 'members_priority' ? 'bg-amber-500/15 text-amber-300 border-amber-500/40' :
                      'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
                    }`}>
                      {s.tier === 'members_only' ? lbl('Solo socios', 'Members only') :
                       s.tier === 'members_priority' ? lbl('Prioridad socios', 'Member priority') :
                       lbl('Público', 'Public')}
                    </span>
                    {(s.green_fee_member > 0 || s.green_fee_guest > 0 || s.green_fee_public > 0) && (
                      <div className="flex gap-1.5 text-[10px] font-mono">
                        {s.green_fee_member > 0 && <span className="text-emerald-400" title={lbl('Socio', 'Member')}>S ${s.green_fee_member.toFixed(0)}</span>}
                        {s.green_fee_guest > 0 && <span className="text-purple-400" title={lbl('Invitado', 'Guest')}>I ${s.green_fee_guest.toFixed(0)}</span>}
                        {s.green_fee_public > 0 && <span className="text-amber-400" title={lbl('Público', 'Public')}>P ${s.green_fee_public.toFixed(0)}</span>}
                      </div>
                    )}
                  </div>

                  {!s.is_blocked && (
                    <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden mb-3">
                      <div className={`h-full ${pct >= 100 ? 'bg-orange-500' : pct >= 50 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                        style={{ width: `${Math.min(pct, 100)}%` }} />
                    </div>
                  )}

                  {/* Bookings list */}
                  {s.bookings.length > 0 && (
                    <div className="space-y-1.5 mb-3">
                      {s.bookings.map(b => (
                        <div key={b.id} className="bg-zinc-800/50 rounded-lg px-2 py-1.5 flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <Users size={11} className="text-zinc-500 flex-shrink-0" />
                            <div className="min-w-0">
                              <p className="text-xs text-zinc-200 truncate">{b.user_name}</p>
                              <p className="text-[10px] text-zinc-500">{b.players_count} {lbl('jug.', 'pl.')}</p>
                            </div>
                          </div>
                          {(isAdmin || b.user_id === (myRole?.role ? '' : '')) && (
                            <button onClick={() => handleCancelBooking(b.id)}
                              title={lbl('Cancelar reserva', 'Cancel booking')}
                              className="text-zinc-500 hover:text-red-400">
                              <X size={12} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-1.5">
                    {!s.is_blocked && !full && (
                      <button onClick={() => setBookingSlot(s)}
                        className="flex-1 text-xs bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-3 py-1.5 rounded-lg">
                        {lbl('Reservar', 'Book')}
                      </button>
                    )}
                    {!s.is_blocked && full && (
                      <span className="flex-1 text-xs bg-orange-500/15 text-orange-300 border border-orange-500/30 px-3 py-1.5 rounded-lg text-center font-semibold">
                        {lbl('Lleno', 'Full')}
                      </span>
                    )}
                    {isAdmin && (
                      <>
                        <button onClick={() => { setBlockingSlot(s); setBlockReason(s.block_reason || '') }}
                          title={s.is_blocked ? lbl('Desbloquear', 'Unblock') : lbl('Bloquear', 'Block')}
                          className={`text-xs px-2 py-1.5 rounded-lg ${
                            s.is_blocked
                              ? 'bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30'
                              : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
                          }`}>
                          {s.is_blocked ? <Unlock size={11} /> : <Lock size={11} />}
                        </button>
                        <button onClick={() => handleDelete(s)} title={lbl('Eliminar', 'Delete')}
                          className="text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-1.5 rounded-lg">
                          <Trash2 size={11} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </main>

      {/* Generate slots modal */}
      {showGen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => !generating && setShowGen(false)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-md p-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Wand2 size={14} className="text-purple-400" />
                {lbl('Generar slots automáticamente', 'Auto-generate slots')}
              </h3>
              <button onClick={() => !generating && setShowGen(false)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Desde', 'From')}</label>
                  <input type="date" value={genForm.date_from} onChange={e => setGenForm({ ...genForm, date_from: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Hasta', 'To')}</label>
                  <input type="date" value={genForm.date_to} onChange={e => setGenForm({ ...genForm, date_to: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Primer slot', 'First slot')}</label>
                  <input type="time" value={genForm.time_start} onChange={e => setGenForm({ ...genForm, time_start: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Último slot', 'Last slot')}</label>
                  <input type="time" value={genForm.time_end} onChange={e => setGenForm({ ...genForm, time_end: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Intervalo (min)', 'Interval (min)')}</label>
                  <input type="number" min="2" max="60" value={genForm.interval_minutes} onChange={e => setGenForm({ ...genForm, interval_minutes: parseInt(e.target.value) || 10 })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Cupo / slot', 'Max / slot')}</label>
                  <input type="number" min="1" max="8" value={genForm.max_players} onChange={e => setGenForm({ ...genForm, max_players: parseInt(e.target.value) || 4 })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
              {/* Tier + pricing */}
              <div className="border-t border-zinc-800 pt-3 space-y-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Acceso (tier)', 'Access tier')}</label>
                  <select value={genForm.tier} onChange={e => setGenForm({ ...genForm, tier: e.target.value as 'members_only' | 'members_priority' | 'public' })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                    <option value="members_only">{lbl('Solo socios', 'Members only')}</option>
                    <option value="members_priority">{lbl('Prioridad socios', 'Member priority')}</option>
                    <option value="public">{lbl('Público', 'Public')}</option>
                  </select>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[9px] text-emerald-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Socio $', 'Member $')}</label>
                    <input type="number" min="0" step="0.01" value={genForm.green_fee_member} onChange={e => setGenForm({ ...genForm, green_fee_member: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm" />
                  </div>
                  <div>
                    <label className="text-[9px] text-purple-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Invitado $', 'Guest $')}</label>
                    <input type="number" min="0" step="0.01" value={genForm.green_fee_guest} onChange={e => setGenForm({ ...genForm, green_fee_guest: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm" />
                  </div>
                  <div>
                    <label className="text-[9px] text-amber-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Público $', 'Public $')}</label>
                    <input type="number" min="0" step="0.01" value={genForm.green_fee_public} onChange={e => setGenForm({ ...genForm, green_fee_public: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm" />
                  </div>
                </div>
              </div>
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 text-xs text-purple-200">
                {lbl(
                  'Se generarán slots cada N minutos entre las horas especificadas, para cada día del rango. Duplicados se omiten.',
                  'Slots will be created every N minutes between the specified hours, for each day in the range. Duplicates are skipped.'
                )}
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowGen(false)} disabled={generating}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleGenerate} disabled={generating}
                className="flex-1 bg-purple-500 hover:bg-purple-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {generating ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                {lbl('Generar', 'Generate')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create slot modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => !creating && setShowCreate(false)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Plus size={14} className="text-emerald-400" />
                {lbl('Crear slot individual', 'Create slot')}
              </h3>
              <button onClick={() => setShowCreate(false)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Fecha', 'Date')}</label>
                <input type="date" value={createForm.date} onChange={e => setCreateForm({ ...createForm, date: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Hora', 'Time')}</label>
                  <input type="time" value={createForm.time} onChange={e => setCreateForm({ ...createForm, time: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Cupo', 'Max')}</label>
                  <input type="number" min="1" max="8" value={createForm.max_players} onChange={e => setCreateForm({ ...createForm, max_players: parseInt(e.target.value) || 4 })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Tier', 'Tier')}</label>
                <select value={createForm.tier} onChange={e => setCreateForm({ ...createForm, tier: e.target.value as 'members_only' | 'members_priority' | 'public' })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="members_only">{lbl('Solo socios', 'Members only')}</option>
                  <option value="members_priority">{lbl('Prioridad socios', 'Member priority')}</option>
                  <option value="public">{lbl('Público', 'Public')}</option>
                </select>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-[9px] text-emerald-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Socio $', 'Member $')}</label>
                  <input type="number" min="0" step="0.01" value={createForm.green_fee_member} onChange={e => setCreateForm({ ...createForm, green_fee_member: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[9px] text-purple-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Invitado $', 'Guest $')}</label>
                  <input type="number" min="0" step="0.01" value={createForm.green_fee_guest} onChange={e => setCreateForm({ ...createForm, green_fee_guest: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[9px] text-amber-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Público $', 'Public $')}</label>
                  <input type="number" min="0" step="0.01" value={createForm.green_fee_public} onChange={e => setCreateForm({ ...createForm, green_fee_public: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowCreate(false)} disabled={creating}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleCreate} disabled={creating}
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                {lbl('Crear', 'Create')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Block/unblock modal */}
      {blockingSlot && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => setBlockingSlot(null)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                {blockingSlot.is_blocked
                  ? <><Unlock size={14} className="text-emerald-400" /> {lbl('Desbloquear slot', 'Unblock slot')}</>
                  : <><Lock size={14} className="text-red-400" /> {lbl('Bloquear slot', 'Block slot')}</>}
              </h3>
              <button onClick={() => setBlockingSlot(null)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <p className="text-xs text-zinc-400 mb-3">
              {blockingSlot.time} · {blockingSlot.booked_count > 0 && lbl(`Hay ${blockingSlot.booked_count} reserva(s) activa(s) que no se cancelarán.`, `There are ${blockingSlot.booked_count} active booking(s) that will NOT be cancelled.`)}
            </p>
            {!blockingSlot.is_blocked && (
              <div className="mb-3">
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Razón (opcional)', 'Reason (optional)')}</label>
                <input value={blockReason} onChange={e => setBlockReason(e.target.value)}
                  placeholder={lbl('Mantenimiento, torneo privado...', 'Maintenance, private tournament...')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={() => setBlockingSlot(null)}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleBlock}
                className={`flex-1 font-semibold py-2.5 rounded-xl text-sm ${
                  blockingSlot.is_blocked ? 'bg-emerald-500 hover:bg-emerald-400' : 'bg-red-500 hover:bg-red-400'
                } text-white`}>
                {blockingSlot.is_blocked ? lbl('Desbloquear', 'Unblock') : lbl('Bloquear', 'Block')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Book modal */}
      {bookingSlot && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => !booking && setBookingSlot(null)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Calendar size={14} className="text-emerald-400" />
                {lbl('Reservar tee time', 'Book tee time')}
              </h3>
              <button onClick={() => !booking && setBookingSlot(null)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 mb-3">
              <p className="text-sm font-bold text-emerald-300">
                {fmtDayLabel(bookingSlot.date, locale)} · {bookingSlot.time}
              </p>
              <p className="text-xs text-emerald-200/70">
                {bookingSlot.available_spots} {lbl('cupos disponibles de', 'of')} {bookingSlot.max_players}
              </p>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Jugadores', 'Players')}</label>
                <input type="number" min="1" max={bookingSlot.available_spots} value={bookForm.players_count}
                  onChange={e => setBookForm({ ...bookForm, players_count: Math.min(parseInt(e.target.value) || 1, bookingSlot.available_spots) })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Notas (opcional)', 'Notes (optional)')}</label>
                <textarea value={bookForm.notes} onChange={e => setBookForm({ ...bookForm, notes: e.target.value })}
                  rows={2} placeholder={lbl('Carrito, caddie, invitado...', 'Cart, caddie, guest...')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm resize-none" />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setBookingSlot(null)} disabled={booking}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleBook} disabled={booking}
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {booking ? <Loader2 size={14} className="animate-spin" /> : <Calendar size={14} />}
                {lbl('Reservar', 'Book')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
