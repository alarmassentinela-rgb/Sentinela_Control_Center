'use client'
import Link from 'next/link'
import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Flag, Eye, EyeOff, Loader2 } from 'lucide-react'
import { api, setAuth } from '@/lib/api'
import { useT, useLocale } from '@/components/DictionaryProvider'
import AleaCredit from '@/components/layout/AleaCredit'

function LoginForm() {
  const t = useT('auth')
  const locale = useLocale()
  const router = useRouter()
  const searchParams = useSearchParams()
  const inviteCode = searchParams.get('invite')
  const clubCode = searchParams.get('club_code')
  const redirectTo = searchParams.get('redirect')

  const [form, setForm] = useState({ email: '', password: '' })
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.post('/auth/login', { email: form.email, password: form.password })
      setAuth(res.data.access_token)

      if (clubCode) {
        try {
          const joinRes = await api.post('/clubs/by-code/join', { invite_code: clubCode })
          router.push(`/${locale}/club/${joinRes.data.club_id}`)
        } catch {
          router.push(`/${locale}/dashboard`)
        }
      } else if (inviteCode) {
        try {
          const joinRes = await api.post(`/rounds/join/${inviteCode}`)
          router.push(`/${locale}/rounds/${joinRes.data.round_id}`)
        } catch {
          router.push(`/${locale}/dashboard`)
        }
      } else if (redirectTo) {
        router.push(redirectTo)
      } else {
        router.push(`/${locale}/dashboard`)
      }
    } catch {
      setError(locale === 'es' ? 'Credenciales incorrectas' : 'Invalid credentials')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href={`/${locale}`} className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={20} className="text-white" />
            </div>
            <span className="font-bold text-xl text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
          </Link>
          <h1 className="text-2xl font-bold text-white">{t('login_title')}</h1>
          <p className="text-zinc-400 text-sm mt-1">
            {clubCode
              ? (locale === 'es' ? 'Inicia sesión para unirte a tu club' : 'Log in to join your club')
              : inviteCode
                ? (locale === 'es' ? 'Inicia sesión para unirte a la ronda' : 'Log in to join the round')
                : t('login_subtitle')}
          </p>
        </div>

        {clubCode && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3 mb-4 text-center">
            <p className="text-sm text-emerald-400">
              {locale === 'es'
                ? `Te unirás al club al entrar · ${clubCode}`
                : `You'll join the club on login · ${clubCode}`}
            </p>
          </div>
        )}
        {!clubCode && inviteCode && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3 mb-4 text-center">
            <p className="text-sm text-emerald-400">
              {locale === 'es'
                ? `Invitado con código: ${inviteCode}`
                : `Invited with code: ${inviteCode}`}
            </p>
          </div>
        )}

        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">{t('email')}</label>
              <input type="email" value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                placeholder="correo@ejemplo.com" required />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium text-zinc-300">{t('password')}</label>
                <Link href={`/${locale}/auth/forgot-password`}
                  className="text-xs text-zinc-500 hover:text-emerald-400 transition-colors">
                  {locale === 'es' ? '¿Olvidaste tu contraseña?' : 'Forgot password?'}
                </Link>
              </div>
              <div className="relative">
                <input type={showPw ? 'text' : 'password'} value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 pr-12 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                  placeholder="••••••••" required />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300">
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            {error && <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading && <Loader2 size={18} className="animate-spin" />}
              {(clubCode || inviteCode) ? (locale === 'es' ? 'Entrar y unirme' : 'Login and join') : t('btn_login')}
            </button>
          </form>
          <div className="mt-6 text-center text-sm text-zinc-500">
            {t('no_account')}{' '}
            <Link href={`/${locale}/auth/register${clubCode ? `?club_code=${clubCode}` : inviteCode ? `?invite=${inviteCode}` : ''}`}
              className="text-emerald-400 hover:text-emerald-300 font-medium">
              {t('register')}
            </Link>
          </div>
        </div>
        <AleaCredit className="mt-6" />
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
