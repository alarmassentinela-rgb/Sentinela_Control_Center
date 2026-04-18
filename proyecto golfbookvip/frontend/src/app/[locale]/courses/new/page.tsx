'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, Save, Loader2, Plus, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Hole { hole_number: number; par: number; stroke_index: number; distance_yards: number }

const defaultHoles = (n: number): Hole[] =>
  Array.from({ length: n }, (_, i) => ({ hole_number: i + 1, par: 4, stroke_index: i + 1, distance_yards: 0 }))

export default function NewCoursePage() {
  const locale = useLocale()
  const router = useRouter()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [form, setForm] = useState({
    name: '', city: '', country: 'México', holes_count: 18,
    par_total: 72, course_rating: '', slope_rating: '',
  })
  const [holes, setHoles] = useState<Hole[]>(defaultHoles(18))
  const [step, setStep] = useState<1 | 2>(1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const setHole = (i: number, k: keyof Hole, v: number) => {
    const h = [...holes]; h[i] = { ...h[i], [k]: v }; setHoles(h)
  }

  const handleHolesCount = (n: number) => {
    setForm({ ...form, holes_count: n })
    setHoles(defaultHoles(n))
  }

  const handleSubmit = async () => {
    setSaving(true); setError('')
    try {
      const courseRes = await api.post('/courses', {
        name: form.name,
        city: form.city || null,
        country: form.country || null,
        holes_count: form.holes_count,
        par_total: form.par_total || null,
        course_rating: form.course_rating ? parseFloat(form.course_rating) : null,
        slope_rating: form.slope_rating ? parseInt(form.slope_rating) : null,
      })
      const courseId = courseRes.data.id
      await api.post(`/courses/${courseId}/holes`, holes)
      router.push(`/${locale}/courses/${courseId}`)
    } catch {
      setError(lbl('Error al guardar la cancha', 'Error saving course'))
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <button onClick={() => step === 2 ? setStep(1) : router.push(`/${locale}/courses`)}
            className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
              <Flag size={14} className="text-white" />
            </div>
            <span className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></span>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {/* Steps */}
        <div className="flex items-center gap-2 mb-8">
          {[1, 2].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                step >= s ? 'bg-emerald-500 text-white' : 'bg-zinc-800 text-zinc-500'}`}>
                {s}
              </div>
              <span className={`text-sm ${step >= s ? 'text-white' : 'text-zinc-500'}`}>
                {s === 1 ? lbl('Datos del campo', 'Course info') : lbl('Hoyos', 'Holes')}
              </span>
              {s < 2 && <div className="w-8 h-px bg-zinc-700 mx-1" />}
            </div>
          ))}
        </div>

        {step === 1 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
            <h1 className="text-xl font-bold text-white mb-2">{lbl('Nueva cancha', 'New course')}</h1>

            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Nombre del campo *', 'Course name *')}</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                placeholder={lbl('Club de Golf Valle Alto', 'Valle Alto Golf Club')} />
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

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Hoyos', 'Holes')}</label>
                <select value={form.holes_count} onChange={(e) => handleHolesCount(Number(e.target.value))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm">
                  <option value={9}>9</option>
                  <option value={18}>18</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">Par total</label>
                <input type="number" value={form.par_total} onChange={(e) => setForm({ ...form, par_total: Number(e.target.value) })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm" />
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">Course rating</label>
                <input type="number" step="0.1" value={form.course_rating} onChange={(e) => setForm({ ...form, course_rating: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                  placeholder="71.5" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">Slope rating</label>
                <input type="number" value={form.slope_rating} onChange={(e) => setForm({ ...form, slope_rating: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                  placeholder="125" />
              </div>
            </div>

            <button onClick={() => { if (!form.name) { setError(lbl('El nombre es requerido','Name is required')); return } setError(''); setStep(2) }}
              className="w-full bg-emerald-500 hover:bg-emerald-400 text-white font-semibold py-3 rounded-xl transition-colors text-sm mt-2">
              {lbl('Siguiente — Configurar hoyos', 'Next — Configure holes')}
            </button>
            {error && <p className="text-sm text-red-400 text-center">{error}</p>}
          </div>
        )}

        {step === 2 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <h1 className="text-xl font-bold text-white mb-1">{lbl('Configurar hoyos', 'Configure holes')}</h1>
            <p className="text-sm text-zinc-500 mb-5">{form.name} · {form.holes_count} {lbl('hoyos', 'holes')}</p>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-zinc-500 text-xs border-b border-zinc-800">
                    <th className="text-left pb-2 pr-3">{lbl('Hoyo', 'Hole')}</th>
                    <th className="text-left pb-2 pr-3">Par</th>
                    <th className="text-left pb-2 pr-3">Stroke index</th>
                    <th className="text-left pb-2">Yardas</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {holes.map((h, i) => (
                    <tr key={h.hole_number}>
                      <td className="py-2 pr-3">
                        <span className="w-7 h-7 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-bold flex items-center justify-center">
                          {h.hole_number}
                        </span>
                      </td>
                      <td className="py-2 pr-3">
                        <select value={h.par} onChange={(e) => setHole(i, 'par', Number(e.target.value))}
                          className="bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm focus:outline-none focus:border-emerald-500 w-16">
                          {[3, 4, 5].map((p) => <option key={p} value={p}>{p}</option>)}
                        </select>
                      </td>
                      <td className="py-2 pr-3">
                        <input type="number" min={1} max={18} value={h.stroke_index}
                          onChange={(e) => setHole(i, 'stroke_index', Number(e.target.value))}
                          className="bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm focus:outline-none focus:border-emerald-500 w-16" />
                      </td>
                      <td className="py-2">
                        <input type="number" min={0} value={h.distance_yards}
                          onChange={(e) => setHole(i, 'distance_yards', Number(e.target.value))}
                          className="bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-white text-sm focus:outline-none focus:border-emerald-500 w-20" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {error && <p className="text-sm text-red-400 mt-3">{error}</p>}

            <button onClick={handleSubmit} disabled={saving}
              className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors text-sm mt-6">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {lbl('Guardar cancha', 'Save course')}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
