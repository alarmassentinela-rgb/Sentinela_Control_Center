'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Plus, Building2, Loader2, Search, Power, Edit2, Crown, MapPin, Mail, Phone, X, Users, UserPlus, UserMinus } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Club {
  id: string
  name: string
  slug: string
  city: string | null
  country: string | null
  currency: string
  phone: string | null
  email: string | null
  plan_id: number | null
  plan_expires_at: string | null
  is_active: boolean
  is_verified: boolean
  member_count: number
  staff_count: number
  created_at: string | null
}

interface Plan {
  id: number
  code: string
  name: string
  plan_type: string
  price_monthly: number
  price_yearly: number
  max_members: number | null
}

export default function AdminClubsPage() {
  const router = useRouter()
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [clubs, setClubs] = useState<Club[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [search, setSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', city: '', country: 'MX', phone: '', email: '', plan_id: '' })
  const [creating, setCreating] = useState(false)
  const [editingClub, setEditingClub] = useState<Club | null>(null)
  const [staffClub, setStaffClub] = useState<Club | null>(null)
  const [staffList, setStaffList] = useState<{ user_id: string; first_name: string; last_name: string; email: string; username: string; role: string }[]>([])
  const [staffLoading, setStaffLoading] = useState(false)
  const [addStaffForm, setAddStaffForm] = useState({ email: '', role: 'admin' })
  const [addingStaff, setAddingStaff] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [clubsRes, plansRes] = await Promise.all([
        api.get(`/admin/clubs`, { params: { q: search, include_inactive: includeInactive } }),
        api.get(`/admin/clubs/plans`),
      ])
      setClubs(clubsRes.data)
      setPlans(plansRes.data)
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 403) setForbidden(true)
    } finally { setLoading(false) }
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeInactive])

  const handleCreate = async () => {
    if (!createForm.name.trim()) { alert(lbl('Nombre requerido', 'Name required')); return }
    setCreating(true)
    try {
      const payload: Record<string, unknown> = {
        name: createForm.name.trim(),
        city: createForm.city || null,
        country: createForm.country || 'MX',
        phone: createForm.phone || null,
        email: createForm.email || null,
      }
      if (createForm.plan_id) payload.plan_id = parseInt(createForm.plan_id)
      await api.post('/admin/clubs', payload)
      setShowCreate(false)
      setCreateForm({ name: '', city: '', country: 'MX', phone: '', email: '', plan_id: '' })
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail ? (typeof detail === 'string' ? detail : JSON.stringify(detail)) : lbl('Error al crear', 'Error creating'))
    } finally { setCreating(false) }
  }

  const handleToggleActive = async (club: Club) => {
    if (!confirm(lbl(
      `¿${club.is_active ? 'Desactivar' : 'Activar'} club "${club.name}"?`,
      `${club.is_active ? 'Deactivate' : 'Activate'} club "${club.name}"?`
    ))) return
    try {
      await api.patch(`/admin/clubs/${club.id}`, { is_active: !club.is_active })
      load()
    } catch {
      alert(lbl('Error al cambiar estado', 'Error toggling status'))
    }
  }

  const handleSetPlan = async (club: Club, planId: number | null) => {
    try {
      await api.patch(`/admin/clubs/${club.id}`, { plan_id: planId })
      load()
      setEditingClub(null)
    } catch {
      alert(lbl('Error al cambiar plan', 'Error changing plan'))
    }
  }

  const openStaff = async (club: Club) => {
    setStaffClub(club)
    setStaffLoading(true)
    setStaffList([])
    setAddStaffForm({ email: '', role: 'admin' })
    try {
      const res = await api.get(`/clubs/${club.id}/staff`)
      setStaffList(res.data || [])
    } catch {
      setStaffList([])
    } finally { setStaffLoading(false) }
  }

  const handleAddStaff = async () => {
    if (!staffClub || !addStaffForm.email.trim()) return
    setAddingStaff(true)
    try {
      const value = addStaffForm.email.trim()
      const payload: Record<string, string> = value.includes('@')
        ? { email: value, role: addStaffForm.role }
        : { username: value, role: addStaffForm.role }
      await api.post(`/admin/clubs/${staffClub.id}/staff`, payload)
      setAddStaffForm({ email: '', role: 'admin' })
      await openStaff(staffClub)
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al agregar staff', 'Error adding staff'))
    } finally { setAddingStaff(false) }
  }

  const handleRemoveStaff = async (userId: string, name: string) => {
    if (!staffClub) return
    if (!confirm(lbl(`¿Quitar a ${name} del staff?`, `Remove ${name} from staff?`))) return
    try {
      await api.delete(`/admin/clubs/${staffClub.id}/staff/${userId}`)
      await openStaff(staffClub)
      load()
    } catch {
      alert(lbl('Error al quitar staff', 'Error removing staff'))
    }
  }

  const planName = (id: number | null) => {
    if (!id) return lbl('Sin plan', 'No plan')
    const p = plans.find(pp => pp.id === id)
    return p ? p.name : `Plan #${id}`
  }

  const planColor = (id: number | null) => {
    if (!id) return 'bg-zinc-700 text-zinc-300'
    const p = plans.find(pp => pp.id === id)
    if (!p) return 'bg-zinc-700 text-zinc-300'
    if (p.price_monthly === 0) return 'bg-zinc-700 text-zinc-300'
    if (p.price_monthly < 100) return 'bg-blue-500/20 text-blue-300 border-blue-500/40'
    return 'bg-purple-500/20 text-purple-300 border-purple-500/40'
  }

  if (loading && clubs.length === 0) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  if (forbidden) return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 px-4">
      <Crown size={48} className="text-red-500/50" />
      <p className="text-white font-bold text-xl">{lbl('Acceso denegado', 'Access denied')}</p>
      <p className="text-zinc-500 text-sm">{lbl('Solo super administradores pueden gestionar clubes.', 'Only super admins can manage clubs.')}</p>
      <Link href={`/${locale}/admin`} className="mt-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-5 py-2.5 rounded-xl text-sm">
        {lbl('Volver', 'Back')}
      </Link>
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link href={`/${locale}/admin`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} />
            Admin
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <Building2 size={14} className="text-emerald-400" />
            {lbl('Clubes (SaaS)', 'Clubs (SaaS)')}
          </h1>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-3 py-1.5 rounded-lg text-xs">
            <Plus size={12} />
            {lbl('Nuevo', 'New')}
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-5 space-y-4">
        {/* Filters */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-3 flex items-center gap-3 flex-wrap">
          <div className="flex-1 min-w-[200px] relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') load() }}
              placeholder={lbl('Buscar nombre, slug, ciudad...', 'Search name, slug, city...')}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-9 pr-3 py-2 text-white text-xs focus:outline-none focus:border-emerald-500"
            />
          </div>
          <button onClick={() => load()}
            className="bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold px-4 py-2 rounded-lg">
            {lbl('Buscar', 'Search')}
          </button>
          <label className="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer">
            <input type="checkbox" checked={includeInactive} onChange={e => setIncludeInactive(e.target.checked)}
              className="w-3.5 h-3.5 accent-emerald-500" />
            {lbl('Incluir inactivos', 'Include inactive')}
          </label>
          <span className="text-xs text-zinc-500 ml-auto">
            {lbl(`${clubs.length} clubes`, `${clubs.length} clubs`)}
          </span>
        </div>

        {/* Clubs list */}
        {clubs.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <Building2 size={42} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-400 text-sm">{lbl('No hay clubes registrados', 'No clubs registered')}</p>
            <button onClick={() => setShowCreate(true)}
              className="mt-3 bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold px-4 py-2 rounded-lg">
              {lbl('Crear el primero', 'Create the first one')}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {clubs.map(c => (
              <div key={c.id}
                className={`bg-zinc-900 border rounded-2xl p-4 ${c.is_active ? 'border-zinc-800' : 'border-zinc-800/50 opacity-60'}`}>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-white text-base truncate">{c.name}</h3>
                    <p className="text-xs text-zinc-500 font-mono">{c.slug}.golfbookvip.com</p>
                  </div>
                  <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md border ${planColor(c.plan_id)}`}>
                    {planName(c.plan_id)}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
                  <div className="bg-zinc-800/50 rounded-lg px-2 py-1.5">
                    <p className="text-[10px] text-zinc-500">{lbl('Miembros', 'Members')}</p>
                    <p className="text-zinc-200 font-bold">{c.member_count}</p>
                  </div>
                  <div className="bg-zinc-800/50 rounded-lg px-2 py-1.5">
                    <p className="text-[10px] text-zinc-500">Staff</p>
                    <p className="text-zinc-200 font-bold">{c.staff_count}</p>
                  </div>
                  <div className="bg-zinc-800/50 rounded-lg px-2 py-1.5">
                    <p className="text-[10px] text-zinc-500">{lbl('Estado', 'Status')}</p>
                    <p className={`font-bold ${c.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
                      {c.is_active ? (lbl('Activo', 'Active')) : (lbl('Inactivo', 'Inactive'))}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 text-[10px] text-zinc-500 mb-3">
                  {c.city && <span className="flex items-center gap-1"><MapPin size={9} /> {c.city}</span>}
                  {c.email && <span className="flex items-center gap-1"><Mail size={9} /> {c.email}</span>}
                  {c.phone && <span className="flex items-center gap-1"><Phone size={9} /> {c.phone}</span>}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => setEditingClub(c)}
                    className="flex-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-3 py-1.5 rounded-lg flex items-center justify-center gap-1.5">
                    <Edit2 size={11} /> {lbl('Plan', 'Plan')}
                  </button>
                  <button onClick={() => openStaff(c)}
                    className="flex-1 text-xs bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 border border-blue-500/30 px-3 py-1.5 rounded-lg flex items-center justify-center gap-1.5">
                    <Users size={11} /> Staff
                  </button>
                  <button onClick={() => handleToggleActive(c)}
                    className={`flex-1 text-xs px-3 py-1.5 rounded-lg flex items-center justify-center gap-1.5 ${
                      c.is_active
                        ? 'bg-red-500/15 hover:bg-red-500/25 text-red-400 border border-red-500/30'
                        : 'bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30'
                    }`}>
                    <Power size={11} /> {c.is_active ? lbl('Desactivar', 'Deactivate') : lbl('Activar', 'Activate')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Planes disponibles */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
          <h2 className="text-sm font-semibold text-white mb-3">{lbl('Planes disponibles', 'Available plans')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
            {plans.map(p => (
              <div key={p.id} className="bg-zinc-800/40 border border-zinc-700 rounded-lg p-3">
                <p className="text-sm font-bold text-white">{p.name}</p>
                <p className="text-[10px] text-zinc-500 font-mono mb-2">{p.code}</p>
                <p className="text-lg font-bold text-emerald-400">
                  ${p.price_monthly.toFixed(0)}<span className="text-[10px] text-zinc-500 font-normal">/mes</span>
                </p>
                <p className="text-[10px] text-zinc-500">
                  {lbl('Hasta', 'Up to')} {p.max_members ?? '∞'} {lbl('miembros', 'members')}
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => !creating && setShowCreate(false)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-md p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white flex items-center gap-2">
                <Building2 size={16} className="text-emerald-400" />
                {lbl('Nuevo club', 'New club')}
              </h3>
              <button onClick={() => !creating && setShowCreate(false)} className="text-zinc-500 hover:text-white">
                <X size={18} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-400 block mb-1 uppercase tracking-wider font-semibold">{lbl('Nombre del club', 'Club name')} *</label>
                <input type="text" value={createForm.name}
                  onChange={e => setCreateForm({ ...createForm, name: e.target.value })}
                  placeholder="Club de Golf Saucito"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 block mb-1 uppercase tracking-wider font-semibold">{lbl('Ciudad', 'City')}</label>
                  <input type="text" value={createForm.city}
                    onChange={e => setCreateForm({ ...createForm, city: e.target.value })}
                    placeholder="Matamoros"
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 block mb-1 uppercase tracking-wider font-semibold">{lbl('País', 'Country')}</label>
                  <input type="text" value={createForm.country}
                    onChange={e => setCreateForm({ ...createForm, country: e.target.value })}
                    placeholder="MX"
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 block mb-1 uppercase tracking-wider font-semibold">{lbl('Teléfono', 'Phone')}</label>
                  <input type="text" value={createForm.phone}
                    onChange={e => setCreateForm({ ...createForm, phone: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 block mb-1 uppercase tracking-wider font-semibold">{lbl('Email', 'Email')}</label>
                  <input type="email" value={createForm.email}
                    onChange={e => setCreateForm({ ...createForm, email: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 block mb-1 uppercase tracking-wider font-semibold">{lbl('Plan inicial', 'Initial plan')}</label>
                <select value={createForm.plan_id}
                  onChange={e => setCreateForm({ ...createForm, plan_id: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="">{lbl('-- Sin plan --', '-- No plan --')}</option>
                  {plans.map(p => (
                    <option key={p.id} value={p.id}>{p.name} (${p.price_monthly.toFixed(0)}/mes)</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowCreate(false)} disabled={creating}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">
                {lbl('Cancelar', 'Cancel')}
              </button>
              <button onClick={handleCreate} disabled={creating || !createForm.name.trim()}
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                {lbl('Crear club', 'Create club')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Change plan modal */}
      {editingClub && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => setEditingClub(null)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-md p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white text-sm">{lbl('Cambiar plan', 'Change plan')}: {editingClub.name}</h3>
              <button onClick={() => setEditingClub(null)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <p className="text-xs text-zinc-500 mb-3">{lbl('Plan actual', 'Current plan')}: <span className="text-zinc-300 font-semibold">{planName(editingClub.plan_id)}</span></p>
            <div className="space-y-2">
              <button onClick={() => handleSetPlan(editingClub, null)}
                className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm px-4 py-2.5 rounded-lg text-left">
                {lbl('Sin plan (gratis sin features)', 'No plan (no features)')}
              </button>
              {plans.map(p => (
                <button key={p.id} onClick={() => handleSetPlan(editingClub, p.id)}
                  className={`w-full text-left px-4 py-2.5 rounded-lg text-sm flex items-center justify-between ${
                    editingClub.plan_id === p.id
                      ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-200'
                      : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-200'
                  }`}>
                  <span>
                    <span className="font-semibold">{p.name}</span>
                    <span className="text-zinc-500 text-xs ml-2">${p.price_monthly.toFixed(0)}/mes</span>
                  </span>
                  {editingClub.plan_id === p.id && <span className="text-xs text-emerald-400">✓ {lbl('Actual', 'Current')}</span>}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Staff management modal */}
      {staffClub && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => setStaffClub(null)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-lg p-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Users size={14} className="text-blue-400" />
                Staff: {staffClub.name}
              </h3>
              <button onClick={() => setStaffClub(null)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>

            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 mb-4">
              <p className="text-xs text-blue-200 leading-relaxed">
                {lbl(
                  'Para que el administrador del club entre a su panel, primero debe crear cuenta normal en golfbookvip.com. Luego escribe aquí su email o username y asígnale rol.',
                  'For the club admin to access their panel, they must first register at golfbookvip.com. Then enter their email or username here and assign a role.'
                )}
              </p>
            </div>

            <div className="bg-zinc-800/50 rounded-lg p-3 mb-4 space-y-2">
              <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">{lbl('Agregar staff por email o username', 'Add staff by email or username')}</label>
              <div className="flex gap-2">
                <input type="text" value={addStaffForm.email}
                  onChange={e => setAddStaffForm({ ...addStaffForm, email: e.target.value })}
                  placeholder="admin@club.com"
                  className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500" />
                <select value={addStaffForm.role}
                  onChange={e => setAddStaffForm({ ...addStaffForm, role: e.target.value })}
                  className="bg-zinc-800 border border-zinc-700 rounded-lg px-2 text-white text-xs">
                  <option value="owner">Owner</option>
                  <option value="admin">Admin</option>
                  <option value="manager">Manager</option>
                  <option value="staff">Staff</option>
                </select>
                <button onClick={handleAddStaff} disabled={addingStaff || !addStaffForm.email.trim()}
                  className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white text-xs font-semibold px-3 py-2 rounded-lg flex items-center gap-1.5">
                  {addingStaff ? <Loader2 size={12} className="animate-spin" /> : <UserPlus size={12} />}
                  {lbl('Agregar', 'Add')}
                </button>
              </div>
            </div>

            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              {lbl('Staff actual', 'Current staff')} ({staffList.length})
            </h4>
            {staffLoading ? (
              <div className="flex justify-center py-6"><Loader2 size={20} className="animate-spin text-emerald-500" /></div>
            ) : staffList.length === 0 ? (
              <p className="text-xs text-zinc-500 italic text-center py-4">{lbl('Sin staff registrado todavía', 'No staff yet')}</p>
            ) : (
              <div className="space-y-2">
                {staffList.map(s => (
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
                    <button onClick={() => handleRemoveStaff(s.user_id, `${s.first_name} ${s.last_name}`)}
                      title={lbl('Quitar', 'Remove')}
                      className="text-zinc-500 hover:text-red-400 transition-colors">
                      <UserMinus size={15} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
