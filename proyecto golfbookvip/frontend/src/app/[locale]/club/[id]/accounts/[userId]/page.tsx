'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, DollarSign, Loader2, X, Plus, Minus, Edit2, AlertCircle, TrendingDown, TrendingUp, Calendar, CreditCard, Printer, ChevronDown } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Account {
  account_id: string
  user_id: string
  first_name: string
  last_name: string
  email: string
  username: string
  balance: number
  credit_limit: number
  member_number: string | null
  member_status: string | null
}

interface Transaction {
  id: string
  type: string
  amount: number
  balance_after: number
  description: string | null
  reference_type: string | null
  created_by_name: string | null
  created_at: string | null
}

interface MyRole {
  role: string | null
  is_superadmin: boolean
  can_manage_members: boolean
  can_manage_membership_types: boolean
}

const CHARGE_TYPES = [
  { value: 'charge', es: 'Cargo general', en: 'General charge' },
  { value: 'membership_fee', es: 'Cuota de membresía', en: 'Membership fee' },
  { value: 'green_fee', es: 'Green fee', en: 'Green fee' },
  { value: 'bet_loss', es: 'Apuesta perdida', en: 'Bet loss' },
]
const PAYMENT_METHODS = [
  { value: 'cash', es: 'Efectivo', en: 'Cash' },
  { value: 'card', es: 'Tarjeta', en: 'Card' },
  { value: 'transfer', es: 'Transferencia', en: 'Transfer' },
  { value: 'other', es: 'Otro', en: 'Other' },
]

export default function AccountDetailPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams<{ id: string; userId: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const fmt = (n: number) => `$${Math.abs(n).toLocaleString(locale === 'es' ? 'es-MX' : 'en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [account, setAccount] = useState<Account | null>(null)
  const [txs, setTxs] = useState<Transaction[]>([])
  const [myRole, setMyRole] = useState<MyRole | null>(null)
  const [clubName, setClubName] = useState('')

  const [showCharge, setShowCharge] = useState(false)
  const [chargeForm, setChargeForm] = useState({ amount: '', type: 'charge', description: '' })
  const [showPayment, setShowPayment] = useState(false)
  const [paymentForm, setPaymentForm] = useState({ amount: '', method: 'cash', description: '' })
  const [showAdjust, setShowAdjust] = useState(false)
  const [adjustForm, setAdjustForm] = useState({ amount: '', description: '' })
  const [showLimit, setShowLimit] = useState(false)
  const [limitForm, setLimitForm] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [roleRes, clubRes, accRes, txRes] = await Promise.all([
        api.get(`/clubs/${params.id}/my-role`),
        api.get(`/clubs/${params.id}/dashboard`),
        api.get(`/clubs/${params.id}/accounts/${params.userId}`),
        api.get(`/clubs/${params.id}/accounts/${params.userId}/transactions`, { params: { limit: 200 } }),
      ])
      setMyRole(roleRes.data)
      setClubName(clubRes.data.name)
      setAccount(accRes.data)
      setTxs(txRes.data || [])
      setLimitForm(String(accRes.data.credit_limit))
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 403) setForbidden(true)
    } finally { setLoading(false) }
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const isAdmin = myRole && (myRole.role === 'owner' || myRole.role === 'admin' || myRole.is_superadmin)
  const isManager = myRole && (isAdmin || myRole.role === 'manager')

  const handleCharge = async () => {
    if (!account || !chargeForm.amount) return
    const amt = parseFloat(chargeForm.amount)
    if (!(amt > 0)) { alert(lbl('Monto inválido', 'Invalid amount')); return }
    setSubmitting(true)
    try {
      await api.post(`/clubs/${params.id}/accounts/${params.userId}/charge`, {
        amount: amt, type: chargeForm.type, description: chargeForm.description || null,
      })
      setShowCharge(false)
      setChargeForm({ amount: '', type: 'charge', description: '' })
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al cargar', 'Error charging'))
    } finally { setSubmitting(false) }
  }

  const handlePayment = async () => {
    if (!account || !paymentForm.amount) return
    const amt = parseFloat(paymentForm.amount)
    if (!(amt > 0)) { alert(lbl('Monto inválido', 'Invalid amount')); return }
    setSubmitting(true)
    try {
      await api.post(`/clubs/${params.id}/accounts/${params.userId}/payment`, {
        amount: amt, method: paymentForm.method, description: paymentForm.description || null,
      })
      setShowPayment(false)
      setPaymentForm({ amount: '', method: 'cash', description: '' })
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error al pagar', 'Error paying'))
    } finally { setSubmitting(false) }
  }

  const handleAdjust = async () => {
    if (!account || !adjustForm.amount || !adjustForm.description) return
    const amt = parseFloat(adjustForm.amount)
    if (amt === 0 || isNaN(amt)) { alert(lbl('Monto inválido', 'Invalid amount')); return }
    setSubmitting(true)
    try {
      await api.post(`/clubs/${params.id}/accounts/${params.userId}/adjust`, {
        amount: amt, description: adjustForm.description,
      })
      setShowAdjust(false)
      setAdjustForm({ amount: '', description: '' })
      load()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || lbl('Error en ajuste', 'Error adjusting'))
    } finally { setSubmitting(false) }
  }

  const handleSetLimit = async () => {
    const lim = parseFloat(limitForm)
    if (lim < 0 || isNaN(lim)) { alert(lbl('Límite debe ser ≥ 0', 'Limit must be ≥ 0')); return }
    setSubmitting(true)
    try {
      await api.patch(`/clubs/${params.id}/accounts/${params.userId}/credit-limit`, null, { params: { credit_limit: lim } })
      setShowLimit(false)
      load()
    } catch {
      alert(lbl('Error', 'Error'))
    } finally { setSubmitting(false) }
  }

  const txTypeLabel = (t: string) => {
    const m: Record<string, { es: string; en: string }> = {
      charge: { es: 'Cargo', en: 'Charge' },
      payment: { es: 'Pago', en: 'Payment' },
      membership_fee: { es: 'Cuota', en: 'Fee' },
      green_fee: { es: 'Green fee', en: 'Green fee' },
      bet_loss: { es: 'Apuesta', en: 'Bet' },
      bet_win: { es: 'Ganancia', en: 'Win' },
      credit: { es: 'Crédito', en: 'Credit' },
      refund: { es: 'Reembolso', en: 'Refund' },
      other: { es: 'Ajuste', en: 'Adjustment' },
    }
    return m[t] ? lbl(m[t].es, m[t].en) : t
  }

  const txTypeTone = (t: string) => {
    if (['charge', 'membership_fee', 'green_fee', 'bet_loss'].includes(t)) return 'text-red-400 bg-red-500/10 border-red-500/30'
    if (['payment', 'credit', 'refund', 'bet_win'].includes(t)) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
    return 'text-zinc-300 bg-zinc-700/40'
  }

  if (loading && !account) return (
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
  if (!account) return null

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30 print:hidden">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-3">
          <Link href={`/${locale}/club/${params.id}/accounts`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} /> {lbl('Cuentas', 'Accounts')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <DollarSign size={14} className="text-emerald-400" />
            {lbl('Estado de cuenta', 'Account statement')}
          </h1>
          <button onClick={() => window.print()} title={lbl('Imprimir', 'Print')}
            className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 p-1.5 rounded-lg">
            <Printer size={14} />
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-5 space-y-4 print:bg-white">
        {/* Member header card */}
        <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800 rounded-2xl p-5 print:bg-white print:border-zinc-300">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                <span className="text-sm font-bold text-emerald-400 print:text-emerald-700">{account.first_name.charAt(0)}{account.last_name.charAt(0)}</span>
              </div>
              <div>
                <h2 className="text-xl font-black text-white print:text-zinc-900">{account.first_name} {account.last_name}</h2>
                <p className="text-xs text-zinc-500 print:text-zinc-600">{account.email}</p>
                {account.member_number && <p className="text-[10px] text-zinc-400 font-mono">#{account.member_number}</p>}
              </div>
            </div>
            <div className="text-right">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold print:text-zinc-600">{lbl('Balance actual', 'Current balance')}</p>
              <p className={`text-3xl font-black ${account.balance < 0 ? 'text-red-400' : account.balance > 0 ? 'text-emerald-400' : 'text-zinc-300'} print:text-zinc-900`}>
                {account.balance < 0 ? '−' : ''}{fmt(account.balance)}
              </p>
              <p className="text-[10px] text-zinc-500 print:text-zinc-600">
                {account.balance < 0 ? lbl('Adeuda', 'Owes') : account.balance > 0 ? lbl('A favor', 'In favor') : lbl('Sin saldo', 'Zero balance')}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            <div className="bg-zinc-800/50 rounded-lg p-2 print:bg-zinc-100">
              <p className="text-[10px] text-zinc-500 uppercase">{lbl('Límite de crédito', 'Credit limit')}</p>
              <div className="flex items-center justify-between mt-0.5">
                <p className="text-zinc-200 font-bold print:text-zinc-900">{fmt(account.credit_limit)}</p>
                {isAdmin && (
                  <button onClick={() => setShowLimit(true)} className="text-zinc-500 hover:text-blue-400 print:hidden">
                    <Edit2 size={11} />
                  </button>
                )}
              </div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-2 print:bg-zinc-100">
              <p className="text-[10px] text-zinc-500 uppercase">{lbl('Estado del socio', 'Member status')}</p>
              <p className="text-zinc-200 font-bold capitalize print:text-zinc-900">{account.member_status || '—'}</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-2 print:bg-zinc-100">
              <p className="text-[10px] text-zinc-500 uppercase">{lbl('Movimientos', 'Transactions')}</p>
              <p className="text-zinc-200 font-bold print:text-zinc-900">{txs.length}</p>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        {isManager && (
          <div className="grid grid-cols-3 gap-2 print:hidden">
            <button onClick={() => setShowPayment(true)}
              className="bg-emerald-500 hover:bg-emerald-400 text-white font-semibold py-3 rounded-xl text-sm flex items-center justify-center gap-2">
              <Plus size={14} /> {lbl('Pago', 'Payment')}
            </button>
            <button onClick={() => setShowCharge(true)}
              className="bg-red-500 hover:bg-red-400 text-white font-semibold py-3 rounded-xl text-sm flex items-center justify-center gap-2">
              <Minus size={14} /> {lbl('Cargo', 'Charge')}
            </button>
            <button onClick={() => setShowAdjust(true)} disabled={!isAdmin}
              className="bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 text-zinc-200 font-semibold py-3 rounded-xl text-sm flex items-center justify-center gap-2">
              <Edit2 size={14} /> {lbl('Ajuste', 'Adjust')}
            </button>
          </div>
        )}

        {/* Transactions */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden print:bg-white print:border-zinc-300">
          <div className="px-4 py-3 border-b border-zinc-800 print:border-zinc-300">
            <h3 className="text-sm font-semibold text-white print:text-zinc-900 flex items-center gap-2">
              <Calendar size={14} className="text-blue-400" />
              {lbl('Historial de movimientos', 'Transaction history')}
            </h3>
          </div>
          {txs.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-xs text-zinc-500 print:text-zinc-600">{lbl('Sin movimientos todavía', 'No transactions yet')}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-800/30 print:bg-zinc-100">
                    <th className="text-left text-xs text-zinc-500 px-4 py-2 font-semibold uppercase tracking-wider print:text-zinc-700">{lbl('Fecha', 'Date')}</th>
                    <th className="text-left text-xs text-zinc-500 px-3 py-2 font-semibold uppercase tracking-wider print:text-zinc-700">{lbl('Tipo', 'Type')}</th>
                    <th className="text-left text-xs text-zinc-500 px-3 py-2 font-semibold uppercase tracking-wider print:text-zinc-700">{lbl('Concepto', 'Description')}</th>
                    <th className="text-right text-xs text-zinc-500 px-3 py-2 font-semibold uppercase tracking-wider print:text-zinc-700">{lbl('Monto', 'Amount')}</th>
                    <th className="text-right text-xs text-zinc-500 px-4 py-2 font-semibold uppercase tracking-wider print:text-zinc-700">{lbl('Saldo', 'Balance')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60 print:divide-zinc-200">
                  {txs.map(t => {
                    const isCharge = ['charge', 'membership_fee', 'green_fee', 'bet_loss'].includes(t.type)
                    const isCredit = ['payment', 'credit', 'refund', 'bet_win'].includes(t.type)
                    const displayedAmt = isCharge ? -t.amount : isCredit ? t.amount : t.amount
                    return (
                      <tr key={t.id} className="hover:bg-zinc-800/30 print:hover:bg-transparent">
                        <td className="px-4 py-2 text-xs text-zinc-400 print:text-zinc-700">
                          {t.created_at ? new Date(t.created_at).toLocaleString(locale === 'es' ? 'es-MX' : 'en-US', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${txTypeTone(t.type)} print:bg-transparent print:border-zinc-400 print:text-zinc-700`}>
                            {txTypeLabel(t.type)}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm text-zinc-300 print:text-zinc-900">
                          <p className="truncate max-w-xs">{t.description || '—'}</p>
                          {t.created_by_name && <p className="text-[10px] text-zinc-500 print:text-zinc-600">{lbl('por', 'by')} {t.created_by_name}</p>}
                        </td>
                        <td className={`px-3 py-2 text-sm font-bold text-right ${displayedAmt < 0 ? 'text-red-400' : 'text-emerald-400'} print:text-zinc-900`}>
                          {displayedAmt < 0 ? '−' : '+'}{fmt(displayedAmt)}
                        </td>
                        <td className="px-4 py-2 text-sm font-mono text-zinc-300 text-right print:text-zinc-900">
                          {t.balance_after < 0 ? '−' : ''}{fmt(t.balance_after)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* CHARGE modal */}
      {showCharge && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4" onClick={() => !submitting && setShowCharge(false)}>
          <div onClick={e => e.stopPropagation()} className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white text-sm flex items-center gap-2"><Minus size={14} className="text-red-400" /> {lbl('Nuevo cargo', 'New charge')}</h3>
              <button onClick={() => setShowCharge(false)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Tipo', 'Type')}</label>
                <select value={chargeForm.type} onChange={e => setChargeForm({ ...chargeForm, type: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                  {CHARGE_TYPES.map(c => <option key={c.value} value={c.value}>{lbl(c.es, c.en)}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Monto', 'Amount')} *</label>
                <input type="number" step="0.01" min="0.01" value={chargeForm.amount} onChange={e => setChargeForm({ ...chargeForm, amount: e.target.value })}
                  placeholder="0.00" className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-lg font-bold" autoFocus />
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Concepto', 'Description')}</label>
                <input value={chargeForm.description} onChange={e => setChargeForm({ ...chargeForm, description: e.target.value })}
                  placeholder={lbl('Carrito hoyo 18, caddie, etc.', 'Cart, caddie, etc.')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowCharge(false)} disabled={submitting}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleCharge} disabled={submitting || !chargeForm.amount}
                className="flex-1 bg-red-500 hover:bg-red-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Minus size={14} />}
                {lbl('Aplicar cargo', 'Apply charge')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PAYMENT modal */}
      {showPayment && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4" onClick={() => !submitting && setShowPayment(false)}>
          <div onClick={e => e.stopPropagation()} className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white text-sm flex items-center gap-2"><Plus size={14} className="text-emerald-400" /> {lbl('Registrar pago', 'Register payment')}</h3>
              <button onClick={() => setShowPayment(false)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Método', 'Method')}</label>
                <select value={paymentForm.method} onChange={e => setPaymentForm({ ...paymentForm, method: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm">
                  {PAYMENT_METHODS.map(p => <option key={p.value} value={p.value}>{lbl(p.es, p.en)}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Monto', 'Amount')} *</label>
                <input type="number" step="0.01" min="0.01" value={paymentForm.amount} onChange={e => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                  placeholder="0.00" className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-lg font-bold" autoFocus />
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Referencia (opcional)', 'Reference (optional)')}</label>
                <input value={paymentForm.description} onChange={e => setPaymentForm({ ...paymentForm, description: e.target.value })}
                  placeholder={lbl('# de transferencia, factura, etc.', 'Transfer #, invoice, etc.')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowPayment(false)} disabled={submitting}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handlePayment} disabled={submitting || !paymentForm.amount}
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                {lbl('Registrar', 'Register')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ADJUST modal */}
      {showAdjust && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4" onClick={() => !submitting && setShowAdjust(false)}>
          <div onClick={e => e.stopPropagation()} className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2"><Edit2 size={14} className="text-blue-400" /> {lbl('Ajuste manual', 'Manual adjustment')}</h3>
              <button onClick={() => setShowAdjust(false)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <p className="text-xs text-zinc-400 mb-3">
              {lbl(
                'Usa monto con signo: positivo suma al saldo, negativo lo resta. Requiere descripción.',
                'Use signed amount: positive adds to balance, negative subtracts. Description required.'
              )}
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Monto (con signo)', 'Amount (signed)')} *</label>
                <input type="number" step="0.01" value={adjustForm.amount} onChange={e => setAdjustForm({ ...adjustForm, amount: e.target.value })}
                  placeholder="+/- 100.00" className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-lg font-bold" autoFocus />
              </div>
              <div>
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-1">{lbl('Motivo del ajuste', 'Reason')} *</label>
                <input value={adjustForm.description} onChange={e => setAdjustForm({ ...adjustForm, description: e.target.value })}
                  placeholder={lbl('Corrección de cargo errado, ...', 'Correction of wrong charge, ...')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowAdjust(false)} disabled={submitting}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleAdjust} disabled={submitting || !adjustForm.amount || !adjustForm.description}
                className="flex-1 bg-blue-500 hover:bg-blue-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Edit2 size={14} />}
                {lbl('Aplicar', 'Apply')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CREDIT LIMIT modal */}
      {showLimit && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4" onClick={() => !submitting && setShowLimit(false)}>
          <div onClick={e => e.stopPropagation()} className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-sm p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2"><CreditCard size={14} className="text-amber-400" /> {lbl('Límite de crédito', 'Credit limit')}</h3>
              <button onClick={() => setShowLimit(false)} className="text-zinc-500 hover:text-white"><X size={18} /></button>
            </div>
            <p className="text-xs text-zinc-400 mb-3">{lbl('Saldo negativo máximo permitido. 0 = no permite deuda.', 'Maximum negative balance allowed. 0 = no debt allowed.')}</p>
            <input type="number" step="0.01" min="0" value={limitForm} onChange={e => setLimitForm(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-lg font-bold" autoFocus />
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowLimit(false)} disabled={submitting}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2.5 rounded-xl text-sm">{lbl('Cancelar', 'Cancel')}</button>
              <button onClick={handleSetLimit} disabled={submitting}
                className="flex-1 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm">{lbl('Guardar', 'Save')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
