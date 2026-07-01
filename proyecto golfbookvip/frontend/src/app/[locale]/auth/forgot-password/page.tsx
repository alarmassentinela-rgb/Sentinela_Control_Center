'use client'
import Link from 'next/link'
import { useState, Suspense } from 'react'
import { Flag, Loader2, ArrowLeft, Mail } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'
import AleaCredit from '@/components/layout/AleaCredit'

function ForgotPasswordForm() {
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')
    try {
      const res = await api.post('/auth/forgot-password', { email })
      setMessage(res.data?.message ?? lbl(
        'Si el email está registrado, te enviamos un enlace de restablecimiento.',
        'If the email is registered, we sent you a reset link.'
      ))
    } catch {
      setError(lbl('Error al procesar la solicitud', 'Error processing request'))
    } finally {
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
          <h1 className="text-2xl font-bold text-white">
            {lbl('Recuperar contraseña', 'Recover password')}
          </h1>
          <p className="text-zinc-400 text-sm mt-1">
            {lbl('Ingresa tu email y te guiaremos', 'Enter your email and we\'ll guide you')}
          </p>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">
                {lbl('Correo electrónico', 'Email address')}
              </label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                  placeholder="correo@ejemplo.com"
                  required
                />
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            {message && (
              <p className="text-sm text-emerald-300 bg-emerald-400/10 border border-emerald-400/20 rounded-lg px-3 py-2">
                {message}
              </p>
            )}

            <button type="submit" disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading && <Loader2 size={18} className="animate-spin" />}
              {lbl('Continuar', 'Continue')}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link href={`/${locale}/auth/login`}
              className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-emerald-400 transition-colors">
              <ArrowLeft size={14} />
              {lbl('Volver al inicio de sesión', 'Back to login')}
            </Link>
          </div>
        </div>

        <AleaCredit className="mt-6" />
      </div>
    </div>
  )
}

export default function ForgotPasswordPage() {
  return (
    <Suspense>
      <ForgotPasswordForm />
    </Suspense>
  )
}
