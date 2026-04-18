'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, Save, Loader2, Users } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

export default function NewClubPage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [form, setForm] = useState({
    name: '', description: '', city: '', country: 'México',
    phone: '', email: '', currency: 'MXN',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name) { setError(lbl('El nombre es requerido', 'Name is required')); return }
    setSaving(true); setError('')
    try {
      const res = await api.post('/clubs', {
        name: form.name,
        description: form.description || null,
        city: form.city || null,
        country: form.country || null,
        phone: form.phone || null,
        email: form.email || null,
        currency: form.currency,
      })
      router.push(`/${locale}/clubs/${res.data.id}`)
    } catch {
      setError(lbl('Error al crear el club', 'Error creating club'))
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/clubs`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={14} className="text-white" />
            </div>
            <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Users size={20} className="text-emerald-400" />
            </div>
            <h1 className="text-xl font-bold text-white">{lbl('Nuevo club', 'New club')}</h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Nombre del club *', 'Club name *')}</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                placeholder={lbl('Club de Golf Monterrey', 'Monterrey Golf Club')} />
            </div>

            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Descripción', 'Description')}</label>
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm resize-none"
                placeholder={lbl('Describe tu club...', 'Describe your club...')} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Ciudad', 'City')}</label>
                <input type="text" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                  placeholder="Monterrey" />
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('País', 'Country')}</label>
                <input type="text" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Teléfono', 'Phone')}</label>
                <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                  placeholder="+52 81 1234 5678" />
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">Email</label>
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                  placeholder="contacto@club.com" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Moneda', 'Currency')}</label>
                <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm">
                  <option value="MXN">MXN — Peso mexicano</option>
                  <option value="USD">USD — Dólar</option>
                </select>
              </div>
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button type="submit" disabled={saving}
              className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors text-sm mt-2">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {lbl('Crear club', 'Create club')}
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}
