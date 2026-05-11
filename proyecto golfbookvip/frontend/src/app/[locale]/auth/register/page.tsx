'use client'
import Link from 'next/link'
import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Flag, Eye, EyeOff, Loader2, Info, Crown } from 'lucide-react'
import { api } from '@/lib/api'
import { useT, useLocale } from '@/components/DictionaryProvider'
import AleaCredit from '@/components/layout/AleaCredit'

const isFounderDay = (() => {
  const now = Date.now()
  const start = new Date('2026-04-17T00:00:00-06:00').getTime()
  const end   = new Date('2026-04-20T06:00:00-06:00').getTime()
  return now >= start && now <= end
})()

function RegisterForm() {
  const t = useT('auth')
  const locale = useLocale()
  const router = useRouter()
  const searchParams = useSearchParams()
  const inviteCode = searchParams.get('invite')
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    username: '',
    email: '',
    password: '',
    confirm: '',
  })
  const [handicap, setHandicap] = useState<string>('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      setError(lbl('Las contraseñas no coinciden', 'Passwords do not match'))
      return
    }
    const hcpNum = handicap !== '' ? parseFloat(handicap) : null
    if (hcpNum !== null && (hcpNum < 0 || hcpNum > 54)) {
      setError(lbl('El hándicap debe ser entre 0 y 54', 'Handicap must be between 0 and 54'))
      return
    }

    if (!/^[a-zA-Z0-9_]{3,30}$/.test(form.username)) {
      setError(lbl(
        'Usuario inválido: solo letras, números y guion bajo, sin espacios (ej: juan_garcia)',
        'Invalid username: only letters, numbers and underscores, no spaces (e.g. juan_garcia)'
      ))
      return
    }

    setLoading(true)
    setError('')
    try {
      await api.post('/auth/register', {
        first_name: form.first_name,
        last_name: form.last_name,
        username: form.username,
        email: form.email,
        password: form.password,
        initial_handicap: hcpNum,
      })

      // Auto-login
      const loginRes = await api.post('/auth/login', {
        email: form.email,
        password: form.password,
      })
      localStorage.setItem('access_token', loginRes.data.access_token)

      if (inviteCode) {
        try {
          const joinRes = await api.post(`/rounds/join/${inviteCode}`)
          const roundId = joinRes.data.round_id
          router.push(`/${locale}/rounds/${roundId}`)
        } catch (joinErr: unknown) {
          // If join fails (e.g. round finished), go to dashboard
          const detail = (joinErr as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          if (detail) setError(detail)
          // Still logged in — go to dashboard after brief delay
          setTimeout(() => router.push(`/${locale}/dashboard`), 2000)
        }
      } else {
        router.push(`/${locale}/dashboard`)
      }
    } catch (err: unknown) {
      const rawDetail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      let errorMsg = lbl('Error al crear la cuenta', 'Error creating account')
      if (typeof rawDetail === 'string') {
        errorMsg = rawDetail
      } else if (Array.isArray(rawDetail) && rawDetail.length > 0) {
        const first = rawDetail[0] as { msg?: string }
        errorMsg = first.msg?.replace('Value error, ', '') ?? errorMsg
      }
      setError(errorMsg)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href={`/${locale}`} className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={20} className="text-white" />
            </div>
            <span className="font-bold text-xl text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
          </Link>
          <h1 className="text-2xl font-bold text-white">{t('register_title')}</h1>
          <p className="text-zinc-400 text-sm mt-1">
            {inviteCode
              ? lbl('Regístrate para unirte a la ronda', 'Register to join the round')
              : t('register_subtitle')}
          </p>
        </div>

        {/* Founding Member Banner */}
        {isFounderDay && (
          <div className="rounded-xl overflow-hidden mb-4">
            <div className="bg-gradient-to-r from-amber-500/20 via-yellow-400/15 to-amber-500/20 border border-amber-400/40 px-4 py-3">
              <div className="flex items-center gap-2 mb-1">
                <Crown size={16} className="text-amber-400" />
                <span className="text-amber-300 font-bold text-sm uppercase tracking-wide">
                  {lbl('Miembro Fundador — Premium Vitalicio', 'Founding Member — Lifetime Premium')}
                </span>
              </div>
              <p className="text-xs text-amber-200/80 leading-snug">
                {lbl(
                  'Hoy es el día de inauguración de GolfBookVIP. Tu cuenta tendrá acceso Premium de por vida, sin costo adicional nunca.',
                  "Today is GolfBookVIP's inauguration day. Your account will have Lifetime Premium access, forever at no extra cost."
                )}
              </p>
            </div>
          </div>
        )}

        {inviteCode && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3 mb-4 text-center">
            <p className="text-sm text-emerald-400">
              {lbl(`Invitado con código: ${inviteCode}`, `Invited with code: ${inviteCode}`)}
            </p>
          </div>
        )}

        <div className="bg-zinc-900/85 border border-zinc-800 rounded-2xl p-8 backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Nombre / Apellido */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { k: 'first_name', label: lbl('Nombre', 'First name'), ph: lbl('Juan', 'John') },
                { k: 'last_name',  label: lbl('Apellido', 'Last name'), ph: lbl('García', 'Smith') },
              ].map(({ k, label, ph }) => (
                <div key={k}>
                  <label className="text-sm font-medium text-zinc-300 block mb-1.5">{label}</label>
                  <input type="text" value={form[k as keyof typeof form]} onChange={set(k)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                    placeholder={ph} required />
                </div>
              ))}
            </div>

            {/* Username / Email */}
            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">{t('username')}</label>
              <input type="text" value={form.username} onChange={set('username')}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                placeholder="juan_garcia" required />
              <p className="text-xs text-zinc-600 mt-1">
                {lbl('Solo letras, números y guion bajo. Sin espacios ni acentos.', 'Letters, numbers and underscores only. No spaces or accents.')}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">{t('email')}</label>
              <input type="email" value={form.email} onChange={set('email')}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                placeholder="correo@ejemplo.com" required />
            </div>

            {/* Hándicap inicial */}
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <label className="text-sm font-medium text-zinc-300">
                  {lbl('Hándicap índice', 'Handicap index')}
                  <span className="text-zinc-500 font-normal ml-1">{lbl('(opcional)', '(optional)')}</span>
                </label>
                <div className="group relative">
                  <Info size={13} className="text-zinc-600 cursor-help" />
                  <div className="absolute left-5 bottom-0 w-56 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-400 hidden group-hover:block z-10 pointer-events-none shadow-xl">
                    {lbl(
                      'Tu hándicap WHS oficial (0–54). Si no lo conoces puedes dejarlo en blanco y configurarlo después en tu perfil.',
                      'Your official WHS handicap index (0–54). Leave blank if unknown — you can set it later in your profile.'
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min="0" max="54" step="0.1"
                  value={handicap}
                  onChange={e => setHandicap(e.target.value)}
                  placeholder={lbl('Ej. 18.4', 'e.g. 18.4')}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                />
                {handicap !== '' && (
                  <div className="flex-shrink-0 w-14 text-center bg-emerald-500/10 border border-emerald-500/20 rounded-xl py-3">
                    <span className="text-emerald-400 font-bold text-sm">{parseFloat(handicap).toFixed(1)}</span>
                  </div>
                )}
              </div>
              <p className="text-xs text-zinc-600 mt-1">
                {lbl('Rango 0.0 — 54.0', 'Range 0.0 — 54.0')}
              </p>
            </div>

            {/* Contraseña */}
            {['password', 'confirm'].map((k) => (
              <div key={k}>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">
                  {k === 'password' ? t('password') : t('confirm_password')}
                </label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={form[k as keyof typeof form]}
                    onChange={set(k)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 pr-12 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                    placeholder="••••••••"
                    required
                    minLength={8}
                  />
                  {k === 'password' && (
                    <button type="button" onClick={() => setShowPw(!showPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300">
                      {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  )}
                </div>
              </div>
            ))}

            {error && (
              <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button type="submit" disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 mt-2">
              {loading && <Loader2 size={18} className="animate-spin" />}
              {inviteCode
                ? lbl('Registrarme y unirme', 'Register and join')
                : t('btn_register')}
            </button>
            <p className="text-xs text-zinc-600 text-center">{t('terms')}</p>
          </form>

          <div className="mt-5 text-center text-sm text-zinc-500">
            {t('have_account')}{' '}
            <Link
              href={`/${locale}/auth/login${inviteCode ? `?invite=${inviteCode}` : ''}`}
              className="text-emerald-400 hover:text-emerald-300 font-medium">
              {t('login')}
            </Link>
          </div>
        </div>

        <AleaCredit className="mt-6" />
      </div>
    </div>
  )
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  )
}
