'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, DollarSign, Loader2, Search, TrendingDown, TrendingUp, AlertCircle, ChevronRight } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface AccountSummary {
  account_id: string
  user_id: string
  first_name: string
  last_name: string
  email: string
  balance: number
  credit_limit: number
}

export default function AccountsListPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [accounts, setAccounts] = useState<AccountSummary[]>([])
  const [search, setSearch] = useState('')
  const [onlyDebtors, setOnlyDebtors] = useState(false)
  const [clubName, setClubName] = useState('')

  const fmt = (n: number) => `$${Math.abs(n).toLocaleString(locale === 'es' ? 'es-MX' : 'en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const load = async () => {
    setLoading(true)
    try {
      const [clubRes, accRes] = await Promise.all([
        api.get(`/clubs/${params.id}/dashboard`),
        api.get(`/clubs/${params.id}/accounts`, {
          params: { q: search, only_debtors: onlyDebtors },
        }),
      ])
      setClubName(clubRes.data.name)
      setAccounts(accRes.data || [])
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 403) setForbidden(true)
    } finally { setLoading(false) }
  }

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyDebtors])

  if (loading && accounts.length === 0) return (
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

  const totalDebt = accounts.filter(a => a.balance < 0).reduce((s, a) => s + a.balance, 0)
  const totalCredit = accounts.filter(a => a.balance > 0).reduce((s, a) => s + a.balance, 0)
  const debtorCount = accounts.filter(a => a.balance < 0).length

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
          <Link href={`/${locale}/club/${params.id}`} className="text-zinc-400 hover:text-white flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} /> {clubName || lbl('Club', 'Club')}
          </Link>
          <h1 className="font-bold text-white text-sm flex items-center gap-2">
            <DollarSign size={14} className="text-emerald-400" />
            {lbl('Estado de cuenta', 'Accounts')}
          </h1>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-5 space-y-4">
        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <TrendingDown size={14} className="text-red-400" />
              <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">{lbl('Deuda total', 'Total debt')}</p>
            </div>
            <p className="text-2xl font-black text-red-400">{fmt(totalDebt)}</p>
            <p className="text-xs text-zinc-500">{debtorCount} {lbl('deudores', 'debtors')}</p>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp size={14} className="text-emerald-400" />
              <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">{lbl('Crédito total', 'Total credit')}</p>
            </div>
            <p className="text-2xl font-black text-emerald-400">{fmt(totalCredit)}</p>
            <p className="text-xs text-zinc-500">{lbl('a favor de socios', 'in favor of members')}</p>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign size={14} className="text-blue-400" />
              <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">{lbl('Cuentas', 'Accounts')}</p>
            </div>
            <p className="text-2xl font-black text-blue-400">{accounts.length}</p>
            <p className="text-xs text-zinc-500">{lbl('total con movimientos', 'total with activity')}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-3 flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px] relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') load() }}
              placeholder={lbl('Buscar nombre o email...', 'Search name or email...')}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-9 pr-3 py-2 text-white text-xs focus:outline-none focus:border-emerald-500" />
          </div>
          <button onClick={load}
            className="bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold px-4 py-2 rounded-lg">{lbl('Buscar', 'Search')}</button>
          <label className="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer">
            <input type="checkbox" checked={onlyDebtors} onChange={e => setOnlyDebtors(e.target.checked)}
              className="w-3.5 h-3.5 accent-red-500" />
            {lbl('Solo deudores', 'Only debtors')}
          </label>
        </div>

        {/* Accounts table */}
        {accounts.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <DollarSign size={42} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-400 text-sm">{lbl('No hay cuentas con movimientos todavía', 'No accounts with activity yet')}</p>
            <p className="text-xs text-zinc-500 mt-2">{lbl('Las cuentas se crean automáticamente cuando registras un cargo o pago.', 'Accounts are created automatically when you register a charge or payment.')}</p>
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-800/30">
                    <th className="text-left text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wider">{lbl('Socio', 'Member')}</th>
                    <th className="text-right text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wider">{lbl('Balance', 'Balance')}</th>
                    <th className="text-right text-xs text-zinc-500 px-4 py-3 font-semibold uppercase tracking-wider hidden md:table-cell">{lbl('Límite crédito', 'Credit limit')}</th>
                    <th className="px-3 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {accounts.map(a => (
                    <tr key={a.account_id} className="hover:bg-zinc-800/30 cursor-pointer"
                      onClick={() => router.push(`/${locale}/club/${params.id}/accounts/${a.user_id}`)}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-bold text-emerald-400">
                            {a.first_name.charAt(0)}{a.last_name.charAt(0)}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-white">{a.first_name} {a.last_name}</p>
                            <p className="text-[10px] text-zinc-500 truncate">{a.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`text-sm font-bold ${a.balance < 0 ? 'text-red-400' : a.balance > 0 ? 'text-emerald-400' : 'text-zinc-500'}`}>
                          {a.balance < 0 ? '−' : ''}{fmt(a.balance)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right hidden md:table-cell">
                        <span className="text-xs text-zinc-400">{fmt(a.credit_limit)}</span>
                      </td>
                      <td className="px-3 py-3 text-right">
                        <ChevronRight size={14} className="text-zinc-600" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <p className="text-xs text-zinc-500 text-center">
          {lbl(
            'Para crear movimientos: entra a la cuenta de un socio desde el padrón o desde esta lista.',
            'To create transactions: enter a member account from the roster or from this list.'
          )}
        </p>
      </main>
    </div>
  )
}
