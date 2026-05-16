'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Plus, CreditCard, Loader2, X, Edit2, Trash2, AlertCircle, Power } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface MembershipType {
  id: number
  name: string
  description: string | null
  monthly_fee: number
  yearly_fee: number
  benefits: Record<string, unknown> | null
  is_active: boolean
  member_count: number
}

interface MyRole {
  can_manage_membership_types: boolean
}

export default function MembershipTypesPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [types, setTypes] = useState<MembershipType[]>([])
  const [includeInactive, setIncludeInactive] = useState(false)
  const [canEdit, setCanEdit] = useState(false)
  const [clubName, setClubName] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState<MembershipType | null>(null)
  const blank = { name: '', description: '', monthly_fee: '0', yearly_fee: '0' }
  const [form, setForm] = useState(blank)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [roleRes, clubRes, listRes] = await Promise.all([
        api.get(`/clubs/${params.id}/my-role`),
        api.get(`/clubs/${params.id}/dashboard`),
        api.get(`/clubs/${params.id}/membership-types`, { params: { include_inactive: includeInactive } }),
      ])
      const role: MyRole = roleRes.data
      setCanEdit(role.can_manage_membership_types)
      setClubName(clubRes.data.name)
      setTypes(listRes.data || [])
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

  const openCreate = () => { setForm(blank); setShowCreate(true) }
  const openEdit = (t: MembershipType) => {
    setEditing(t)
    setForm({
      name: t.name,
      description: t.description || '',
      monthly_fee: String(t.monthly_fee),
      yearly_fee: String(t.yearly_fee),
    })
  }

  const handleSubmit = async () => {
    if (!form.name.trim()) { alert(lbl('Nombre requerido', 'Name required')); return }
    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description || null,
        monthly_fee: parseFloat(form.monthly_fee) || 0,
        yearly_fee: parseFloat(form.yearly_fee) || 0,
      }
      if (editing) {
        await api.patch(`/clubs/${params.id}/membership-types/${editing.id}`, payload)
      } else {
        await api.post(`/clubs/${params.id}/membership-types`, payload)
      }
      setShowCreate(false)
      setEditing(null)
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al guardar', 'Error saving'))
    } finally { setSaving(false) }
  }

  const handleToggleActive = async (t: MembershipType) => {
    try {
      await api.patch(`/clubs/${params.id}/membership-types/${t.id}`, { is_active: !t.is_active })
      load()
    } catch { alert(lbl('Error', 'Error')) }
  }

  const handleDelete = async (t: MembershipType) => {
    if (t.member_count > 0) {
      alert(lbl(`No se puede eliminar: ${t.member_count} miembros activos tienen este tipo. Reasígnalos primero.`,
        `Cannot delete: ${t.member_count} active members have this type. Reassign first.`))
      return
    }
    if (!confirm(lbl(`¿Eliminar tipo "${t.name}"?`, `Delete type "${t.name}"?`))) return
    try {
      await api.delete(`/clubs/${params.id}/membership-types/${t.id}`)
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al eliminar', 'Error deleting'))
    }
  }

  if (loading && types.length === 0) return (
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
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
          <Link href={`/${locale}/club/${params.id}`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} /> {clubName || lbl('Club', 'Club')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <CreditCard size={14} className="text-purple-400" />
            {lbl('Tipos de membresía', 'Membership types')}
          </h1>
          {canEdit ? (
            <button onClick={openCreate}
              className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-3 py-1.5 rounded-lg text-xs">
              <Plus size={12} /> {lbl('Nuevo', 'New')}
            </button>
          ) : <div className="w-16" />}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-5 space-y-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-3 flex items-center justify-between flex-wrap gap-3">
          <p className="text-xs text-zinc-400">
            {lbl(
              'Define los planes de membresía que ofrece tu club (Socio Honorario, Familiar, Junior, etc.). Cada miembro del padrón se asigna a uno.',
              'Define the membership plans your club offers (Honorary, Family, Junior, etc.). Each roster member is assigned one.'
            )}
          </p>
          <label className="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer">
            <input type="checkbox" checked={includeInactive} onChange={e => setIncludeInactive(e.target.checked)}
              className="w-3.5 h-3.5 accent-emerald-500" />
            {lbl('Incluir inactivos', 'Include inactive')}
          </label>
        </div>

        {types.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <CreditCard size={42} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-400 text-sm">{lbl('No hay tipos de membresía aún', 'No membership types yet')}</p>
            {canEdit && (
              <button onClick={openCreate}
                className="mt-3 bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold px-4 py-2 rounded-lg">
                {lbl('Crear el primero', 'Create the first one')}
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {types.map(t => (
              <div key={t.id}
                className={`bg-zinc-900 border rounded-2xl p-4 ${t.is_active ? 'border-zinc-800' : 'border-zinc-800/50 opacity-60'}`}>
                <div className="flex items-start justify-between mb-2 gap-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-white text-base truncate">{t.name}</h3>
                    {t.description && <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{t.description}</p>}
                  </div>
                  <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md ${t.is_active ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-zinc-700 text-zinc-400'}`}>
                    {t.is_active ? lbl('Activo', 'Active') : lbl('Inactivo', 'Inactive')}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 my-3">
                  <div className="bg-zinc-800/50 rounded-lg p-2">
                    <p className="text-[9px] text-zinc-500 uppercase tracking-wider">{lbl('Cuota mensual', 'Monthly fee')}</p>
                    <p className="text-lg font-black text-emerald-400">${t.monthly_fee.toFixed(0)}</p>
                  </div>
                  <div className="bg-zinc-800/50 rounded-lg p-2">
                    <p className="text-[9px] text-zinc-500 uppercase tracking-wider">{lbl('Anual', 'Yearly')}</p>
                    <p className="text-lg font-black text-blue-400">${t.yearly_fee.toFixed(0)}</p>
                  </div>
                </div>
                <p className="text-xs text-zinc-500 mb-3">
                  <strong className="text-zinc-300">{t.member_count}</strong> {lbl('miembros activos', 'active members')}
                </p>
                {canEdit && (
                  <div className="flex gap-2">
                    <button onClick={() => openEdit(t)}
                      className="flex-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-3 py-1.5 rounded-lg flex items-center justify-center gap-1.5">
                      <Edit2 size={11} /> {lbl('Editar', 'Edit')}
                    </button>
                    <button onClick={() => handleToggleActive(t)}
                      className={`flex-1 text-xs px-3 py-1.5 rounded-lg flex items-center justify-center gap-1.5 ${
                        t.is_active
                          ? 'bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30'
                          : 'bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 border border-emerald-500/30'
                      }`}>
                      <Power size={11} /> {t.is_active ? lbl('Desactivar', 'Deactivate') : lbl('Activar', 'Activate')}
                    </button>
                    <button onClick={() => handleDelete(t)} title={lbl('Eliminar', 'Delete')}
                      className="text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-1.5 rounded-lg">
                      <Trash2 size={11} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create / edit modal */}
      {(showCreate || editing) && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4"
          onClick={() => !saving && (setShowCreate(false), setEditing(null))}>
          <div onClick={e => e.stopPropagation()}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-md p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <CreditCard size={14} className="text-purple-400" />
                {editing ? lbl('Editar tipo', 'Edit type') : lbl('Nuevo tipo de membresía', 'New membership type')}
              </h3>
              <button onClick={() => { setShowCreate(false); setEditing(null) }} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Nombre', 'Name')} *</label>
                <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder={lbl('Socio Activo, Familiar, Junior...', 'Active member, Family, Junior...')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Descripción', 'Description')}</label>
                <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                  rows={2} placeholder={lbl('Beneficios y condiciones...', 'Benefits and conditions...')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm resize-none" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Cuota mensual', 'Monthly fee')}</label>
                  <input type="number" step="0.01" value={form.monthly_fee} onChange={e => setForm({ ...form, monthly_fee: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Cuota anual', 'Yearly fee')}</label>
                  <input type="number" step="0.01" value={form.yearly_fee} onChange={e => setForm({ ...form, yearly_fee: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => { setShowCreate(false); setEditing(null) }} disabled={saving}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleSubmit} disabled={saving || !form.name.trim()}
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {saving ? <Loader2 size={14} className="animate-spin" /> : (editing ? <Edit2 size={14} /> : <Plus size={14} />)}
                {editing ? lbl('Guardar', 'Save') : lbl('Crear', 'Create')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
