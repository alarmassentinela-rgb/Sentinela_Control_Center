'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, ArrowRight, Loader2, Plus, X, Check, Building2, CreditCard, Users, FileCheck2, Flag } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'
import CsvPadronImport, { ParsedRow } from '@/components/clubs/CsvPadronImport'

interface Plan {
  id: number
  code: string
  name: string
  plan_type: string
  price_monthly: number
  price_yearly: number
  max_members: number | null
}

interface TypeRow {
  key: string
  name: string
  monthly_fee: string
  yearly_fee: string
  description: string
}

type Step = 'basic' | 'types' | 'padron' | 'review'

export default function NewClubWizardPage() {
  const router = useRouter()
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [forbidden, setForbidden] = useState(false)
  const [plans, setPlans] = useState<Plan[]>([])
  const [step, setStep] = useState<Step>('basic')

  // Step 1
  const [basic, setBasic] = useState({
    name: '', city: '', country: 'MX', phone: '', email: '',
    currency: 'MXN', timezone: 'America/Mexico_City', plan_id: '',
  })

  // Step 2
  const [types, setTypes] = useState<TypeRow[]>([])
  const addType = () => setTypes([...types, { key: `t-${Date.now()}-${Math.random()}`, name: '', monthly_fee: '', yearly_fee: '', description: '' }])
  const removeType = (key: string) => setTypes(types.filter(t => t.key !== key))
  const updateType = (key: string, patch: Partial<TypeRow>) => setTypes(types.map(t => t.key === key ? { ...t, ...patch } : t))

  // Step 3
  const [padronRows, setPadronRows] = useState<ParsedRow[]>([])

  // Submit
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitLog, setSubmitLog] = useState<string[]>([])

  useEffect(() => {
    if (!isAuthed()) { router.push(`/${locale}/auth/login`); return }
    api.get('/admin/clubs/plans')
      .then(r => setPlans(r.data))
      .catch((e: unknown) => {
        const status = (e as { response?: { status?: number } })?.response?.status
        if (status === 403) setForbidden(true)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const canNext: Record<Step, boolean> = {
    basic: !!(basic.name.trim() && basic.plan_id),
    types: true,  // todos los pasos siguientes son opcionales
    padron: true,
    review: true,
  }

  const steps: { key: Step; label: string; icon: typeof Building2 }[] = [
    { key: 'basic', label: lbl('Datos básicos', 'Basics'), icon: Building2 },
    { key: 'types', label: lbl('Tipos de membresía', 'Membership types'), icon: CreditCard },
    { key: 'padron', label: lbl('Padrón', 'Roster'), icon: Users },
    { key: 'review', label: lbl('Revisar', 'Review'), icon: FileCheck2 },
  ]
  const stepIndex = steps.findIndex(s => s.key === step)

  const goNext = () => {
    if (!canNext[step]) return
    const next = steps[stepIndex + 1]
    if (next) setStep(next.key)
  }
  const goPrev = () => {
    const prev = steps[stepIndex - 1]
    if (prev) setStep(prev.key)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setSubmitError(null)
    setSubmitLog([])
    const log = (msg: string) => setSubmitLog(prev => [...prev, msg])

    try {
      // 1. Crear club
      log(lbl('Creando club...', 'Creating club...'))
      const clubPayload: Record<string, unknown> = {
        name: basic.name.trim(),
        city: basic.city || null,
        country: basic.country || 'MX',
        phone: basic.phone || null,
        email: basic.email || null,
        currency: basic.currency || 'MXN',
        timezone: basic.timezone || 'America/Mexico_City',
        plan_id: parseInt(basic.plan_id),
      }
      const clubRes = await api.post('/admin/clubs', clubPayload)
      const clubId: string = clubRes.data.id
      log(lbl(`Club creado · ${basic.name}`, `Club created · ${basic.name}`))

      // 2. Crear tipos de membresía
      const validTypes = types.filter(t => t.name.trim())
      if (validTypes.length > 0) {
        log(lbl(`Creando ${validTypes.length} tipos de membresía...`, `Creating ${validTypes.length} membership types...`))
        for (const t of validTypes) {
          try {
            await api.post(`/clubs/${clubId}/membership-types`, {
              name: t.name.trim(),
              description: t.description || null,
              monthly_fee: parseFloat(t.monthly_fee) || 0,
              yearly_fee: parseFloat(t.yearly_fee) || 0,
            })
          } catch {
            log(lbl(`  · Error con tipo "${t.name}" (saltado)`, `  · Error with type "${t.name}" (skipped)`))
          }
        }
        log(lbl(`Tipos creados`, `Types created`))
      }

      // 3. Importar padrón si hay rows válidas
      const importable = padronRows.filter(r => r.status === 'matched')
      let importedCount = 0
      let pendingCount = 0
      if (importable.length > 0) {
        log(lbl(`Importando ${importable.length} socios...`, `Importing ${importable.length} members...`))
        try {
          const importRes = await api.post(`/clubs/${clubId}/padron/import`, {
            rows: padronRows.map(r => ({
              email: r.email,
              member_number: r.member_number || null,
              membership_type_name: r.membership_type_name || null,
              joined_at: r.joined_at || null,
              expires_at: r.expires_at || null,
              notes: r.notes || null,
            })),
            skip_existing: true,
          })
          importedCount = (importRes.data?.created || 0) + (importRes.data?.reactivated || 0)
          pendingCount = importRes.data?.not_found_count || 0
          log(lbl(`Padrón importado: ${importedCount} socios · ${pendingCount} pendientes de registrarse`,
                  `Roster imported: ${importedCount} members · ${pendingCount} pending registration`))
        } catch {
          log(lbl('  · Error al importar padrón (el club ya existe; podrás importar después)',
                  '  · Error importing roster (club exists; you can import later)'))
        }
      }

      // 4. Redirigir
      log(lbl('Redirigiendo al panel del club...', 'Redirecting to club panel...'))
      setTimeout(() => router.push(`/${locale}/club/${clubId}`), 1200)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setSubmitError(typeof detail === 'string' ? detail : lbl('Error al crear club', 'Error creating club'))
      setSubmitting(false)
    }
  }

  if (forbidden) return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 px-4">
      <p className="text-white font-bold text-xl">{lbl('Acceso denegado', 'Access denied')}</p>
      <Link href={`/${locale}/dashboard`} className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-5 py-2.5 rounded-xl text-sm">{lbl('Volver', 'Back')}</Link>
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
          <Link href={`/${locale}/admin/clubs`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} /> {lbl('Clubes', 'Clubs')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <Building2 size={14} className="text-emerald-400" />
            {lbl('Nuevo club', 'New club')}
          </h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-5">
        {/* Stepper */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
          <div className="flex items-center justify-between">
            {steps.map((s, i) => {
              const Icon = s.icon
              const active = s.key === step
              const completed = i < stepIndex
              return (
                <div key={s.key} className="flex items-center flex-1">
                  <div className="flex flex-col items-center gap-1 flex-1">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center border-2 ${
                      completed ? 'bg-emerald-500 border-emerald-500 text-white' :
                      active ? 'bg-emerald-500/15 border-emerald-500 text-emerald-300' :
                      'bg-zinc-800 border-zinc-700 text-zinc-500'
                    }`}>
                      {completed ? <Check size={16} /> : <Icon size={15} />}
                    </div>
                    <span className={`text-[10px] uppercase tracking-wide text-center ${active ? 'text-emerald-300 font-bold' : completed ? 'text-zinc-400' : 'text-zinc-600'}`}>
                      {s.label}
                    </span>
                  </div>
                  {i < steps.length - 1 && (
                    <div className={`flex-1 h-0.5 mx-1 ${i < stepIndex ? 'bg-emerald-500' : 'bg-zinc-700'}`} />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Step content */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
          {step === 'basic' && (
            <div className="space-y-3">
              <h2 className="text-base font-bold text-white">{lbl('Información del club', 'Club information')}</h2>
              <p className="text-xs text-zinc-500">{lbl('Datos básicos para identificar al cliente B2B.', 'Basic data for the B2B client.')}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Nombre', 'Name')} *</label>
                  <input value={basic.name} onChange={e => setBasic({ ...basic, name: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" placeholder={lbl('Club de Golf...', 'Golf Club...')} />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Plan', 'Plan')} *</label>
                  <select value={basic.plan_id} onChange={e => setBasic({ ...basic, plan_id: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                    <option value="">{lbl('— Selecciona —', '— Pick one —')}</option>
                    {plans.map(p => <option key={p.id} value={p.id}>{p.name} · ${p.price_monthly}/mes</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Ciudad', 'City')}</label>
                  <input value={basic.city} onChange={e => setBasic({ ...basic, city: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('País', 'Country')}</label>
                  <input value={basic.country} onChange={e => setBasic({ ...basic, country: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Email', 'Email')}</label>
                  <input type="email" value={basic.email} onChange={e => setBasic({ ...basic, email: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Teléfono', 'Phone')}</label>
                  <input value={basic.phone} onChange={e => setBasic({ ...basic, phone: e.target.value })}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
            </div>
          )}

          {step === 'types' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white">{lbl('Tipos de membresía', 'Membership types')}</h2>
                  <p className="text-xs text-zinc-500 mt-0.5">{lbl('Opcional. Ej. Socio, Honorario, Invitado.', 'Optional. E.g. Member, Honorary, Guest.')}</p>
                </div>
                <button onClick={addType}
                  className="text-xs bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 px-3 py-1.5 rounded-lg flex items-center gap-1">
                  <Plus size={12} /> {lbl('Agregar tipo', 'Add type')}
                </button>
              </div>
              {types.length === 0 ? (
                <div className="bg-zinc-800/50 border border-dashed border-zinc-700 rounded-xl p-6 text-center">
                  <CreditCard size={28} className="text-zinc-600 mx-auto mb-2" />
                  <p className="text-sm text-zinc-400">{lbl('Aún no agregaste tipos', 'No types yet')}</p>
                  <p className="text-[11px] text-zinc-600 mt-1">{lbl('Puedes saltar y agregarlos después desde el panel del club.', 'You can skip and add them later from the club panel.')}</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {types.map((t, idx) => (
                    <div key={t.key} className="bg-zinc-800/50 border border-zinc-700/60 rounded-xl p-3 space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-zinc-500 font-mono w-6">#{idx + 1}</span>
                        <input value={t.name} onChange={e => updateType(t.key, { name: e.target.value })}
                          placeholder={lbl('Nombre del tipo (ej. Socio Activo)', 'Type name (e.g. Active Member)')}
                          className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm" />
                        <button onClick={() => removeType(t.key)} className="text-zinc-500 hover:text-red-400"><X size={14} /></button>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <input type="number" min="0" step="0.01" value={t.monthly_fee}
                          onChange={e => updateType(t.key, { monthly_fee: e.target.value })}
                          placeholder={lbl('Cuota mensual', 'Monthly fee')}
                          className="bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-xs" />
                        <input type="number" min="0" step="0.01" value={t.yearly_fee}
                          onChange={e => updateType(t.key, { yearly_fee: e.target.value })}
                          placeholder={lbl('Cuota anual', 'Yearly fee')}
                          className="bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-xs" />
                      </div>
                      <input value={t.description} onChange={e => updateType(t.key, { description: e.target.value })}
                        placeholder={lbl('Descripción (opcional)', 'Description (optional)')}
                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-xs" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {step === 'padron' && (
            <div className="space-y-3">
              <div>
                <h2 className="text-base font-bold text-white">{lbl('Padrón inicial', 'Initial roster')}</h2>
                <p className="text-xs text-zinc-500 mt-0.5">
                  {lbl(
                    'Opcional. Sube un CSV con los emails de los socios. Solo se vincularán quienes ya tienen cuenta en GolfBookVIP. Los demás recibirán el link de invitación al terminar.',
                    'Optional. Upload a CSV with member emails. Only those with existing GolfBookVIP accounts will be linked. Others will get the invitation link at the end.'
                  )}
                </p>
              </div>
              <CsvPadronImport locale={locale as 'es' | 'en'} clubId={null} onRowsReady={setPadronRows} />
            </div>
          )}

          {step === 'review' && (
            <div className="space-y-4">
              <h2 className="text-base font-bold text-white">{lbl('Revisar y crear', 'Review and create')}</h2>

              <div className="bg-zinc-800/50 rounded-xl p-3 space-y-2">
                <p className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">{lbl('Datos básicos', 'Basics')}</p>
                <p className="text-sm text-white"><span className="font-bold">{basic.name}</span></p>
                <p className="text-xs text-zinc-400">
                  {basic.city && `${basic.city}, `}{basic.country}
                  {basic.email && ` · ${basic.email}`}
                  {basic.phone && ` · ${basic.phone}`}
                </p>
                <p className="text-xs text-emerald-300">
                  {lbl('Plan:', 'Plan:')} {plans.find(p => String(p.id) === basic.plan_id)?.name || '—'}
                </p>
              </div>

              <div className="bg-zinc-800/50 rounded-xl p-3 space-y-1">
                <p className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">{lbl('Tipos de membresía', 'Membership types')}</p>
                {types.filter(t => t.name.trim()).length === 0 ? (
                  <p className="text-xs text-zinc-500">{lbl('Ninguno (podrás agregar después)', 'None (you can add later)')}</p>
                ) : (
                  <ul className="text-xs text-white space-y-0.5">
                    {types.filter(t => t.name.trim()).map((t, i) => (
                      <li key={i}>· {t.name} {t.monthly_fee && `· $${parseFloat(t.monthly_fee).toFixed(0)}/mes`}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="bg-zinc-800/50 rounded-xl p-3 space-y-1">
                <p className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">{lbl('Padrón', 'Roster')}</p>
                {padronRows.length === 0 ? (
                  <p className="text-xs text-zinc-500">{lbl('Sin CSV (importarás después)', 'No CSV (will import later)')}</p>
                ) : (
                  <p className="text-xs text-white">
                    {padronRows.filter(r => r.status === 'matched').length} {lbl('socios listos para vincular', 'members ready to link')}
                    {padronRows.filter(r => r.status === 'not_found').length > 0 && (
                      <span className="text-amber-300"> · {padronRows.filter(r => r.status === 'not_found').length} {lbl('pendientes', 'pending')}</span>
                    )}
                  </p>
                )}
              </div>

              {submitLog.length > 0 && (
                <div className="bg-emerald-500/5 border border-emerald-500/30 rounded-xl p-3 space-y-0.5">
                  {submitLog.map((m, i) => (
                    <p key={i} className="text-xs text-emerald-200 font-mono">{m}</p>
                  ))}
                </div>
              )}

              {submitError && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-xs text-red-300">{submitError}</div>
              )}
            </div>
          )}
        </div>

        {/* Navegación */}
        <div className="flex items-center justify-between gap-3">
          <button onClick={goPrev} disabled={stepIndex === 0 || submitting}
            className="bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-300 px-4 py-2.5 rounded-xl text-sm flex items-center gap-2">
            <ArrowLeft size={14} /> {lbl('Atrás', 'Back')}
          </button>

          {step !== 'review' ? (
            <button onClick={goNext} disabled={!canNext[step]}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-30 text-white font-semibold px-6 py-2.5 rounded-xl text-sm flex items-center gap-2">
              {lbl('Siguiente', 'Next')} <ArrowRight size={14} />
            </button>
          ) : (
            <button onClick={handleSubmit} disabled={submitting}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-white font-bold px-6 py-2.5 rounded-xl text-sm flex items-center gap-2">
              {submitting ? <Loader2 size={14} className="animate-spin" /> : <Flag size={14} />}
              {lbl('Crear club', 'Create club')}
            </button>
          )}
        </div>
      </main>
    </div>
  )
}
