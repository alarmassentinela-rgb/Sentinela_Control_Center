'use client'
import Link from 'next/link'
import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Flag, Loader2, Eye, EyeOff, CheckCircle2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

function ResetPasswordForm() {
  const locale = useLocale()
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) {
      setError(lbl('Las contraseñas no coinciden', 'Passwords do not match'))
      return
    }
    if (!token) {
      setError(lbl('Token inválido. Solicita un nuevo enlace.', 'Invalid token. Request a new link.'))
      return
    }
    setLoading(true)
    setError('')
    try {
      await api.post('/auth/reset-password', { token, new_password: password })
      setDone(true)
      setTimeout(() => router.push(`/${locale}/auth/login`), 2500)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? lbl('Error al restablecer la contraseña', 'Error resetting password'))
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center mx-auto">
            <CheckCircle2 size={32} className="text-emerald-400" />
          </div>
          <h2 className="text-xl font-bold text-white">
            {lbl('¡Contraseña actualizada!', 'Password updated!')}
          </h2>
          <p className="text-zinc-400 text-sm">
            {lbl('Redirigiendo al inicio de sesión…', 'Redirecting to login…')}
          </p>
        </div>
      </div>
    )
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
          <h1 className="text-2xl font-bold text-white">
            {lbl('Nueva contraseña', 'New password')}
          </h1>
          <p className="text-zinc-400 text-sm mt-1">
            {lbl('Elige una contraseña segura (mínimo 8 caracteres)', 'Choose a secure password (minimum 8 characters)')}
          </p>
        </div>

        {!token && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-4 text-center">
            <p className="text-sm text-red-400">
              {lbl('Enlace inválido. ', 'Invalid link. ')}
              <Link href={`/${locale}/auth/forgot-password`} className="underline hover:text-red-300">
                {lbl('Solicitar uno nuevo', 'Request a new one')}
              </Link>
            </p>
          </div>
        )}

        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {['password', 'confirm'].map(k => (
              <div key={k}>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">
                  {k === 'password'
                    ? lbl('Nueva contraseña', 'New password')
                    : lbl('Confirmar contraseña', 'Confirm password')}
                </label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={k === 'password' ? password : confirm}
                    onChange={e => k === 'password' ? setPassword(e.target.value) : setConfirm(e.target.value)}
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

            <button type="submit" disabled={loading || !token}
              className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading && <Loader2 size={18} className="animate-spin" />}
              {lbl('Guardar contraseña', 'Save password')}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-zinc-500">
            <Link href={`/${locale}/auth/login`} className="text-emerald-400 hover:text-emerald-300">
              {lbl('Volver al inicio de sesión', 'Back to login')}
            </Link>
          </div>
        </div>

        <p className="text-center text-xs text-zinc-700 mt-6">
          {lbl('Desarrollado por', 'Developed by')} <span className="text-zinc-500">AleaSystems</span>
        </p>
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  )
}
