'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Plus, Users, Loader2, Search, X, Edit2, UserMinus, Mail, Hash, Calendar, CreditCard, AlertCircle, DollarSign, Link2, QrCode, Copy, Check } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Member {
  id: string
  user_id: string
  first_name: string
  last_name: string
  email: string
  username: string
  handicap_index: number | null
  phone: string | null
  member_number: string | null
  status: string
  joined_at: string | null
  expires_at: string | null
  notes: string | null
  membership_type: { id: number; name: string; monthly_fee: number } | null
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

export default function ClubMembersPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [members, setMembers] = useState<Member[]>([])
  const [types, setTypes] = useState<MembershipType[]>([])
  const [myRole, setMyRole] = useState<MyRole | null>(null)
  const [clubName, setClubName] = useState('')

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('active')
  const [typeFilter, setTypeFilter] = useState<number | ''>('')

  const [showAdd, setShowAdd] = useState(false)
  const [addTab, setAddTab] = useState<'invite' | 'search'>('invite')
  const [inviteCode, setInviteCode] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [addForm, setAddForm] = useState({ email: '', member_number: '', membership_type_id: '', joined_at: new Date().toISOString().slice(0, 10), expires_at: '', notes: '' })
  const [adding, setAdding] = useState(false)

  const [editing, setEditing] = useState<Member | null>(null)
  const [editForm, setEditForm] = useState({ member_number: '', membership_type_id: '', status: 'active', expires_at: '', notes: '' })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [meRoleRes, clubRes, typesRes] = await Promise.all([
        api.get(`/clubs/${params.id}/my-role`),
        api.get(`/clubs/${params.id}/dashboard`),
        api.get(`/clubs/${params.id}/membership-types`),
      ])
      setMyRole(meRoleRes.data)
      setClubName(clubRes.data.name)
      setTypes(typesRes.data || [])
      // Si el rol permite gestionar, obtener invite_code para la tab "Compartir invitación"
      if (meRoleRes.data?.can_manage_members) {
        try {
          const settingsRes = await api.get(`/clubs/${params.id}/settings`)
          setInviteCode(settingsRes.data?.invite_code || null)
        } catch { /* sin permiso o sin código todavía */ }
      }
      const membersRes = await api.get(`/clubs/${params.id}/padron`, {
        params: {
          q: search,
          status_filter: statusFilter,
          membership_type_id: typeFilter || undefined,
        },
      })
      setMembers(membersRes.data || [])
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 403) setForbidden(true)
    } finally { setLoading(false) }
  }

  const inviteUrl = (() => {
    if (!inviteCode) return ''
    if (typeof window === 'undefined') return ''
    return `${window.location.origin}/${locale}/join-club/${inviteCode}`
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
    if (!inviteUrl) return
    const svg = document.getElementById('club-invite-qr')
    if (!svg) return
    const serializer = new XMLSerializer()
    const svgStr = serializer.serializeToString(svg)
    const blob = new Blob([svgStr], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `invitacion-${inviteCode}.svg`
    a.click()
    URL.revokeObjectURL(url)
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, typeFilter])

  const handleAdd = async () => {
    if (!addForm.email.trim()) { alert(lbl('Email requerido', 'Email required')); return }
    setAdding(true)
    try {
      const value = addForm.email.trim()
      const payload: Record<string, unknown> = value.includes('@')
        ? { email: value }
        : { username: value }
      if (addForm.member_number) payload.member_number = addForm.member_number
      if (addForm.membership_type_id) payload.membership_type_id = parseInt(addForm.membership_type_id)
      if (addForm.joined_at) payload.joined_at = addForm.joined_at
      if (addForm.expires_at) payload.expires_at = addForm.expires_at
      if (addForm.notes) payload.notes = addForm.notes
      await api.post(`/clubs/${params.id}/padron`, payload)
      setShowAdd(false)
      setAddForm({ email: '', member_number: '', membership_type_id: '', joined_at: new Date().toISOString().slice(0, 10), expires_at: '', notes: '' })
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al agregar', 'Error adding'))
    } finally { setAdding(false) }
  }

  const openEdit = (m: Member) => {
    setEditing(m)
    setEditForm({
      member_number: m.member_number || '',
      membership_type_id: m.membership_type ? String(m.membership_type.id) : '',
      status: m.status,
      expires_at: m.expires_at?.slice(0, 10) || '',
      notes: m.notes || '',
    })
  }

  const handleSave = async () => {
    if (!editing) return
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        member_number: editForm.member_number || null,
        membership_type_id: editForm.membership_type_id ? parseInt(editForm.membership_type_id) : null,
        status: editForm.status,
        expires_at: editForm.expires_at || null,
        notes: editForm.notes || null,
      }
      await api.patch(`/clubs/${params.id}/padron/${editing.user_id}`, payload)
      setEditing(null)
      load()
    } catch {
      alert(lbl('Error al guardar', 'Error saving'))
    } finally { setSaving(false) }
  }

  const handleRemove = async (m: Member) => {
    if (!confirm(lbl(`¿Dar de baja a ${m.first_name} ${m.last_name}?`, `Remove ${m.first_name} ${m.last_name}?`))) return
    try {
      await api.delete(`/clubs/${params.id}/padron/${m.user_id}`)
      load()
    } catch { alert(lbl('Error al dar de baja', 'Error removing')) }
  }

  if (loading && members.length === 0) return (
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

  const canEdit = myRole?.can_manage_members ?? false
  const statusBadge = (st: string) => {
    const map: Record<string, string> = {
      active: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
      inactive: 'bg-zinc-700 text-zinc-400',
      suspended: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    }
    return map[st] || 'bg-zinc-700 text-zinc-300'
  }
  const statusLbl = (st: string) => st === 'active' ? lbl('Activo', 'Active') : st === 'suspended' ? lbl('Suspendido', 'Suspended') : lbl('Inactivo', 'Inactive')

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
          <Link href={`/${locale}/club/${params.id}`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} /> {clubName || lbl('Club', 'Club')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <Users size={14} className="text-blue-400" />
            {lbl('Padrón', 'Members')}
          </h1>
          {canEdit ? (
            <button onClick={() => setShowAdd(true)}
              className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-3 py-1.5 rounded-lg text-xs">
              <Plus size={12} /> {lbl('Agregar', 'Add')}
            </button>
          ) : <div className="w-16" />}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-5 space-y-4">
        {/* Filters */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-3 flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px] relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') load() }}
              placeholder={lbl('Buscar nombre, email, # de socio...', 'Search name, email, member #...')}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-9 pr-3 py-2 text-white text-xs focus:outline-none focus:border-emerald-500" />
          </div>
          <button onClick={load} className="bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold px-4 py-2 rounded-lg">
            {lbl('Buscar', 'Search')}
          </button>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-xs">
            <option value="active">{lbl('Activos', 'Active')}</option>
            <option value="inactive">{lbl('Inactivos', 'Inactive')}</option>
            <option value="suspended">{lbl('Suspendidos', 'Suspended')}</option>
            <option value="all">{lbl('Todos', 'All')}</option>
          </select>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value ? parseInt(e.target.value) : '')}
            className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-xs">
            <option value="">{lbl('Todos los tipos', 'All types')}</option>
            {types.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <Link href={`/${locale}/club/${params.id}/membership-types`}
            className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs px-3 py-2 rounded-lg flex items-center gap-1.5">
            <CreditCard size={12} /> {lbl('Tipos', 'Types')}
          </Link>
          <span className="text-xs text-zinc-500 ml-auto">{members.length} {lbl('miembros', 'members')}</span>
        </div>

        {/* Table */}
        {members.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <Users size={42} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-400 text-sm">{lbl('No hay miembros en el padrón', 'No members in roster')}</p>
            {canEdit && (
              <button onClick={() => setShowAdd(true)}
                className="mt-3 bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold px-4 py-2 rounded-lg">
                {lbl('Agregar el primero', 'Add the first one')}
              </button>
            )}
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-800/30">
                    <th className="text-left text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wider">{lbl('Miembro', 'Member')}</th>
                    <th className="text-left text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wider">#</th>
                    <th className="text-left text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wider hidden md:table-cell">{lbl('Tipo', 'Type')}</th>
                    <th className="text-left text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wider hidden md:table-cell">HCP</th>
                    <th className="text-left text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wider hidden lg:table-cell">{lbl('Ingresó', 'Joined')}</th>
                    <th className="text-center text-xs text-zinc-500 px-3 py-3 font-semibold uppercase tracking-wider">{lbl('Estado', 'Status')}</th>
                    {canEdit && <th className="px-3 py-3" />}
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {members.map(m => (
                    <tr key={m.id} className="hover:bg-zinc-800/30">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-bold text-emerald-400 flex-shrink-0">
                            {m.first_name.charAt(0)}{m.last_name.charAt(0)}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-white truncate">{m.first_name} {m.last_name}</p>
                            <p className="text-[10px] text-zinc-500 truncate">@{m.username} · {m.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-sm text-zinc-300 font-mono">{m.member_number || '—'}</td>
                      <td className="px-3 py-3 hidden md:table-cell">
                        {m.membership_type ? (
                          <span className="text-xs bg-purple-500/15 border border-purple-500/30 text-purple-300 px-2 py-0.5 rounded-md font-semibold">{m.membership_type.name}</span>
                        ) : <span className="text-xs text-zinc-500">—</span>}
                      </td>
                      <td className="px-3 py-3 text-sm text-zinc-300 hidden md:table-cell">{m.handicap_index !== null ? m.handicap_index.toFixed(1) : '—'}</td>
                      <td className="px-3 py-3 text-xs text-zinc-500 hidden lg:table-cell">{m.joined_at ? new Date(m.joined_at).toLocaleDateString(locale === 'es' ? 'es-MX' : 'en-US') : '—'}</td>
                      <td className="px-3 py-3 text-center">
                        <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md border ${statusBadge(m.status)}`}>
                          {statusLbl(m.status)}
                        </span>
                      </td>
                      {canEdit && (
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-2 justify-end">
                            <Link href={`/${locale}/club/${params.id}/accounts/${m.user_id}`} title={lbl('Cuenta', 'Account')}
                              className="text-zinc-500 hover:text-emerald-400">
                              <DollarSign size={14} />
                            </Link>
                            <button onClick={() => openEdit(m)} title={lbl('Editar', 'Edit')}
                              className="text-zinc-500 hover:text-blue-400">
                              <Edit2 size={14} />
                            </button>
                            {m.status === 'active' && (
                              <button onClick={() => handleRemove(m)} title={lbl('Dar de baja', 'Remove')}
                                className="text-zinc-500 hover:text-red-400">
                                <UserMinus size={14} />
                              </button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* Add member modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => !adding && setShowAdd(false)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-md p-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Plus size={14} className="text-emerald-400" />
                {lbl('Agregar miembro al padrón', 'Add member to roster')}
              </h3>
              <button onClick={() => !adding && setShowAdd(false)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-4 bg-zinc-800/60 p-1 rounded-xl">
              <button onClick={() => setAddTab('invite')}
                className={`flex-1 text-xs font-semibold py-2 rounded-lg flex items-center justify-center gap-1.5 transition-colors ${addTab === 'invite' ? 'bg-emerald-500 text-white' : 'text-zinc-400 hover:text-white'}`}>
                <Link2 size={12} /> {lbl('Compartir invitación', 'Share invitation')}
              </button>
              <button onClick={() => setAddTab('search')}
                className={`flex-1 text-xs font-semibold py-2 rounded-lg flex items-center justify-center gap-1.5 transition-colors ${addTab === 'search' ? 'bg-emerald-500 text-white' : 'text-zinc-400 hover:text-white'}`}>
                <Search size={12} /> {lbl('Buscar usuario', 'Search user')}
              </button>
            </div>

            {addTab === 'invite' ? (
              <div className="space-y-4">
                {inviteCode ? (
                  <>
                    <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 text-center">
                      <p className="text-[10px] text-emerald-400/80 uppercase tracking-widest font-semibold mb-2">{lbl('Código de tu club', 'Your club code')}</p>
                      <p className="text-2xl font-bold text-emerald-300 font-mono tracking-wider">{inviteCode}</p>
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
                    <div className="bg-white p-4 rounded-xl flex items-center justify-center">
                      <QRCodeSVG id="club-invite-qr" value={inviteUrl || ' '} size={180} />
                    </div>
                    <button onClick={downloadQr}
                      className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                      <QrCode size={14} /> {lbl('Descargar QR', 'Download QR')}
                    </button>
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                      <p className="text-xs text-blue-200 leading-relaxed">
                        {lbl(
                          'Comparte este link o QR con tus socios. Al registrarse desde aquí, quedarán automáticamente vinculados al padrón. Tú solo ajustas su tipo de membresía y número de socio.',
                          'Share this link or QR with your members. When they register through it, they will be automatically linked to the roster. You only adjust their membership type and member number.'
                        )}
                      </p>
                    </div>
                    <div className="text-center pt-2">
                      <Link href={`/${locale}/club/${params.id}/settings`}
                        className="text-xs text-zinc-500 hover:text-emerald-400 transition-colors">
                        {lbl('Rotar código en Configuración →', 'Rotate code in Settings →')}
                      </Link>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-zinc-500 text-sm">
                    {lbl('No hay código de invitación disponible.', 'No invitation code available.')}
                  </div>
                )}
              </div>
            ) : (
            <>
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 mb-3">
              <p className="text-xs text-blue-200 leading-relaxed">
                {lbl(
                  'El miembro debe tener cuenta previa en golfbookvip.com. Aquí lo agregas al padrón del club por email o username.',
                  'The member must have a registered account at golfbookvip.com. Add them here by email or username.'
                )}
              </p>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Email o username', 'Email or username')} *</label>
                <input value={addForm.email} onChange={e => setAddForm({ ...addForm, email: e.target.value })}
                  placeholder="socio@email.com"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1"># {lbl('de socio', 'member')}</label>
                  <input value={addForm.member_number} onChange={e => setAddForm({ ...addForm, member_number: e.target.value })}
                    placeholder="0001"
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Tipo', 'Type')}</label>
                  <select value={addForm.membership_type_id} onChange={e => setAddForm({ ...addForm, membership_type_id: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                    <option value="">{lbl('-- Sin tipo --', '-- None --')}</option>
                    {types.filter(t => t.is_active).map(t => (
                      <option key={t.id} value={t.id}>{t.name} (${t.monthly_fee.toFixed(0)}/mes)</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Ingresó', 'Joined')}</label>
                  <input type="date" value={addForm.joined_at} onChange={e => setAddForm({ ...addForm, joined_at: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Vence', 'Expires')}</label>
                  <input type="date" value={addForm.expires_at} onChange={e => setAddForm({ ...addForm, expires_at: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Notas', 'Notes')}</label>
                <textarea value={addForm.notes} onChange={e => setAddForm({ ...addForm, notes: e.target.value })}
                  rows={2} placeholder={lbl('Observaciones internas...', 'Internal notes...')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm resize-none" />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowAdd(false)} disabled={adding}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleAdd} disabled={adding || !addForm.email.trim()}
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {adding ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                {lbl('Agregar', 'Add')}
              </button>
            </div>
            </>
            )}
          </div>
        </div>
      )}

      {/* Edit member modal */}
      {editing && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => !saving && setEditing(null)}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-md p-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white text-sm">
                {lbl('Editar', 'Edit')}: {editing.first_name} {editing.last_name}
              </h3>
              <button onClick={() => !saving && setEditing(null)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1"># {lbl('de socio', 'member')}</label>
                  <input value={editForm.member_number} onChange={e => setEditForm({ ...editForm, member_number: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Estado', 'Status')}</label>
                  <select value={editForm.status} onChange={e => setEditForm({ ...editForm, status: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                    <option value="active">{lbl('Activo', 'Active')}</option>
                    <option value="suspended">{lbl('Suspendido', 'Suspended')}</option>
                    <option value="inactive">{lbl('Inactivo', 'Inactive')}</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Tipo de membresía', 'Membership type')}</label>
                <select value={editForm.membership_type_id} onChange={e => setEditForm({ ...editForm, membership_type_id: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="">{lbl('-- Sin tipo --', '-- None --')}</option>
                  {types.filter(t => t.is_active).map(t => (
                    <option key={t.id} value={t.id}>{t.name} (${t.monthly_fee.toFixed(0)}/mes)</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Vence', 'Expires')}</label>
                <input type="date" value={editForm.expires_at} onChange={e => setEditForm({ ...editForm, expires_at: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Notas', 'Notes')}</label>
                <textarea value={editForm.notes} onChange={e => setEditForm({ ...editForm, notes: e.target.value })}
                  rows={2} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm resize-none" />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setEditing(null)} disabled={saving}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleSave} disabled={saving}
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Edit2 size={14} />}
                {lbl('Guardar', 'Save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
