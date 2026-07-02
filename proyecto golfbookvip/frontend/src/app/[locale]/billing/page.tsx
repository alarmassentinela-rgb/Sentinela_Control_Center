'use client'
import { useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Building2, CheckCircle2, CreditCard, Loader2, Sparkles, User, XCircle } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Plan {
  id: number
  code: string
  name: string
  plan_type: 'player' | 'club'
  price_monthly: number | null
  price_yearly: number | null
  limits: {
    max_members: number | null
    max_courses: number | null
    max_groups: number | null
    max_rounds_history: number | null
  }
}

interface UsageItem {
  current: number
  limit: number | null
  upgrade_to: string | null
}

interface PlanUsage {
  plan: Plan
  usage: Record<string, UsageItem>
}

interface PlansResponse {
  player: Plan[]
  club: Plan[]
}

export default function BillingPage() {
  const locale = useLocale()
  const router = useRouter()
  const searchParams = useSearchParams()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const clubId = searchParams.get('club_id')
  const status = searchParams.get('status')
  const limit = searchParams.get('limit')

  const [loading, setLoading] = useState(true)
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null)
  const [cycle, setCycle] = useState<'monthly' | 'yearly'>('monthly')
  const [plans, setPlans] = useState<PlansResponse>({ player: [], club: [] })
  const [userUsage, setUserUsage] = useState<PlanUsage | null>(null)
  const [clubUsage, setClubUsage] = useState<PlanUsage | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthed()) { router.push(`/${locale}/auth/login`); return }
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const calls = [
          api.get('/users/me/plan'),
          api.get('/billing/plans'),
          clubId ? api.get(`/clubs/${clubId}/plan`) : Promise.resolve({ data: null }),
        ]
        const [userRes, plansRes, clubRes] = await Promise.all(calls)
        setUserUsage(userRes.data)
        setPlans(plansRes.data)
        setClubUsage(clubRes.data)
      } catch {
        setError(locale === 'es' ? 'No se pudo cargar la facturación.' : 'Could not load billing.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [locale, router, clubId])

  const selectedPlans = useMemo(() => {
    const base = clubId && clubUsage ? plans.club : plans.player
    const currentCode = clubId && clubUsage ? clubUsage.plan.code : userUsage?.plan.code
    return base.filter(p => p.code !== currentCode && ((cycle === 'monthly' ? p.price_monthly : p.price_yearly) || 0) > 0)
  }, [plans, userUsage, clubUsage, clubId, cycle])

  const startCheckout = async (plan: Plan) => {
    setCheckoutLoading(plan.code)
    setError(null)
    try {
      const res = await api.post('/billing/checkout', {
        plan_code: plan.code,
        cycle,
        club_id: plan.plan_type === 'club' ? clubId : null,
      })
      window.location.href = res.data.checkout_url
    } catch {
      setError(lbl('No se pudo iniciar el pago.', 'Could not start checkout.'))
      setCheckoutLoading(null)
    }
  }

  const renderUsage = (usage: PlanUsage | null) => {
    if (!usage) return null
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {Object.entries(usage.usage).map(([key, item]) => {
          const pct = item.limit ? Math.min(100, Math.round((item.current / item.limit) * 100)) : 0
          return (
            <div key={key} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-300">
                  {key === 'groups' ? lbl('Grupos', 'Groups') :
                    key === 'rounds_history' ? lbl('Historial', 'History') :
                    key === 'members' ? lbl('Socios', 'Members') : lbl('Canchas', 'Courses')}
                </span>
                <span className="text-xs text-zinc-500">
                  {item.current}{item.limit === null ? ' / ∞' : ` / ${item.limit}`}
                </span>
              </div>
              <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
                <div className="h-full bg-emerald-500" style={{ width: `${item.limit === null ? 100 : pct}%` }} />
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={30} className="animate-spin text-emerald-500" />
    </div>
  )

  const activeUsage = clubId && clubUsage ? clubUsage : userUsage
  const activeTitle = clubId && clubUsage ? lbl('Plan del club', 'Club plan') : lbl('Plan del jugador', 'Player plan')

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white transition-colors">
              <ArrowLeft size={20} />
            </Link>
            <div>
              <h1 className="text-lg font-bold text-white">{lbl('Planes y facturación', 'Plans & billing')}</h1>
              <p className="text-xs text-zinc-500">{activeTitle}</p>
            </div>
          </div>
          <div className="inline-flex bg-zinc-800 border border-zinc-700 rounded-lg p-1">
            {(['monthly', 'yearly'] as const).map(opt => (
              <button key={opt} onClick={() => setCycle(opt)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${cycle === opt ? 'bg-emerald-500 text-white' : 'text-zinc-400 hover:text-white'}`}>
                {opt === 'monthly' ? lbl('Mensual', 'Monthly') : lbl('Anual', 'Yearly')}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        {status === 'success' && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-center gap-3 text-emerald-300">
            <CheckCircle2 size={20} /> {lbl('¡Plan activado!', 'Plan activated!')}
          </div>
        )}
        {status === 'cancel' && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 flex items-center gap-3 text-yellow-300">
            <XCircle size={20} /> {lbl('Pago cancelado.', 'Payment cancelled.')}
          </div>
        )}
        {limit && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-200 text-sm">
            {lbl('Límite alcanzado. Elige un plan superior para continuar.', 'Limit reached. Choose a higher plan to continue.')}
          </div>
        )}
        {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-200 text-sm">{error}</div>}

        <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-11 h-11 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
              {clubId && clubUsage ? <Building2 size={20} className="text-emerald-400" /> : <User size={20} className="text-emerald-400" />}
            </div>
            <div>
              <p className="text-sm text-zinc-500">{activeTitle}</p>
              <h2 className="text-xl font-bold text-white">{activeUsage?.plan.name}</h2>
            </div>
          </div>
          {renderUsage(activeUsage)}
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={18} className="text-emerald-400" />
            <h2 className="font-semibold text-white">{lbl('Opciones de upgrade', 'Upgrade options')}</h2>
          </div>
          {selectedPlans.length === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center">
              <CheckCircle2 size={28} className="text-emerald-400 mx-auto mb-3" />
              <p className="text-sm text-white font-medium">
                {(activeUsage?.plan?.price_monthly || 0) > 0
                  ? lbl('Ya estás en el plan más completo disponible.', "You're already on the most complete plan available.")
                  : lbl('No hay upgrades disponibles para este alcance.', 'No upgrades available for this scope.')}
              </p>
              {!clubId && (
                <p className="text-xs text-zinc-500 mt-2">
                  {lbl('¿Administras un club? Abre el club para gestionar su plan.', 'Manage a club? Open the club to manage its plan.')}
                </p>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {selectedPlans.map(plan => {
                const price = cycle === 'monthly' ? plan.price_monthly : plan.price_yearly
                return (
                  <div key={plan.code} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 flex flex-col">
                    <div className="mb-4">
                      <h3 className="text-lg font-bold text-white">{plan.name}</h3>
                      <p className="text-3xl font-bold text-emerald-400 mt-2">
                        ${price?.toFixed(0)}
                        <span className="text-sm text-zinc-500 font-normal">/{cycle === 'monthly' ? lbl('mes', 'mo') : lbl('año', 'yr')}</span>
                      </p>
                    </div>
                    <ul className="text-sm text-zinc-400 space-y-2 flex-1">
                      {plan.limits.max_members !== null && <li>{plan.limits.max_members} {lbl('socios', 'members')}</li>}
                      {plan.limits.max_courses !== null && <li>{plan.limits.max_courses} {lbl('canchas', 'courses')}</li>}
                      {plan.limits.max_groups !== null && <li>{plan.limits.max_groups} {lbl('grupos', 'groups')}</li>}
                      {plan.limits.max_rounds_history !== null && <li>{plan.limits.max_rounds_history} {lbl('rondas visibles', 'visible rounds')}</li>}
                      {Object.values(plan.limits).every(v => v === null) && <li>{lbl('Límites ilimitados', 'Unlimited limits')}</li>}
                    </ul>
                    <button onClick={() => startCheckout(plan)} disabled={checkoutLoading !== null}
                      className="mt-5 w-full inline-flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:bg-zinc-700 disabled:text-zinc-400 text-white font-semibold rounded-xl px-4 py-2.5 transition-colors text-sm">
                      {checkoutLoading === plan.code ? <Loader2 size={16} className="animate-spin" /> : <CreditCard size={16} />}
                      {lbl('Subir a', 'Upgrade to')} {plan.name}
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
