'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, Loader2, MapPin, Save, Crosshair, Trash2, AlertTriangle, X } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Hole {
  hole_number: number
  par: number
  stroke_index: number | null
  distance_yards_black: number | null
  distance_yards_blue: number | null
  distance_yards_white: number | null
  distance_yards_red: number | null
  green_latitude: number | null
  green_longitude: number | null
  tee_latitude: number | null
  tee_longitude: number | null
}

interface Course {
  id: string
  name: string
  description: string | null
  country: string | null
  city: string | null
  address: string | null
  latitude: number | null
  longitude: number | null
  holes_count: number
  par_total: number | null
  course_rating: number | null
  slope_rating: number | null
  created_by: string | null
  holes: Hole[]
}

// Parsea texto pegado y extrae lat/lng. Acepta:
//  - "25.753905, -97.555131"            (Google Maps "Copy coordinates")
//  - "25.753905,-97.555131"             (sin espacio)
//  - "@25.7539,-97.5551,..."            (URL Google Maps con @)
//  - "?ll=25.7539,-97.5551" / "?q=..."  (URL con parámetros)
function parseLatLng(text: string): { lat: number; lng: number } | null {
  if (!text) return null
  // URL Google Maps con @lat,lng
  const m1 = text.match(/@(-?\d+\.?\d*),(-?\d+\.?\d*)/)
  if (m1) return { lat: parseFloat(m1[1]), lng: parseFloat(m1[2]) }
  // URL con ll= o q=lat,lng
  const m2 = text.match(/[?&](?:ll|q)=(-?\d+\.?\d*),\s*(-?\d+\.?\d*)/)
  if (m2) return { lat: parseFloat(m2[1]), lng: parseFloat(m2[2]) }
  // "lat, lng" plano
  const m3 = text.match(/(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)/)
  if (m3) {
    const lat = parseFloat(m3[1])
    const lng = parseFloat(m3[2])
    if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
      return { lat, lng }
    }
  }
  return null
}

function emptyHole(n: number): Hole {
  return {
    hole_number: n, par: 4, stroke_index: null,
    distance_yards_black: null, distance_yards_blue: null,
    distance_yards_white: null, distance_yards_red: null,
    green_latitude: null, green_longitude: null,
    tee_latitude: null, tee_longitude: null,
  }
}

export default function CourseEditPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [course, setCourse] = useState<Course | null>(null)
  const [holes, setHoles] = useState<Hole[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [canEdit, setCanEdit] = useState(false)
  const [capturingFor, setCapturingFor] = useState<{ hole: number; kind: 'tee' | 'green' } | null>(null)
  const [activeTab, setActiveTab] = useState<'details' | 'holes'>('details')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cRes, meRes] = await Promise.all([
        api.get(`/courses/${id}`),
        api.get('/users/me'),
      ])
      setCourse(cRes.data)
      const filled: Hole[] = []
      for (let i = 1; i <= (cRes.data.holes_count ?? 18); i++) {
        const existing = (cRes.data.holes as Hole[]).find(h => h.hole_number === i)
        filled.push(existing ?? emptyHole(i))
      }
      setHoles(filled)
      const me = meRes.data
      const ok = me.is_superadmin || !cRes.data.created_by || cRes.data.created_by === me.id
      setCanEdit(ok)
      if (!ok) {
        setError(locale === 'es' ? 'No tienes permiso para editar este campo' : 'You cannot edit this course')
      }
    } catch {
      setError(locale === 'es' ? 'Campo no encontrado' : 'Course not found')
    } finally {
      setLoading(false)
    }
  }, [id, locale])

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    load()
  }, [router, locale, load])

  const updateCourseField = <K extends keyof Course>(key: K, value: Course[K]) => {
    setCourse(prev => prev ? { ...prev, [key]: value } : prev)
  }

  const updateHole = <K extends keyof Hole>(idx: number, key: K, value: Hole[K]) => {
    setHoles(prev => prev.map((h, i) => i === idx ? { ...h, [key]: value } : h))
  }

  const captureGPS = (hole: number, kind: 'tee' | 'green') => {
    if (!navigator.geolocation) {
      alert(lbl('Tu navegador no soporta GPS', 'Your browser does not support GPS'))
      return
    }
    setCapturingFor({ hole, kind })
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const idx = holes.findIndex(h => h.hole_number === hole)
        if (idx < 0) { setCapturingFor(null); return }
        if (kind === 'tee') {
          updateHole(idx, 'tee_latitude', pos.coords.latitude)
          updateHole(idx, 'tee_longitude', pos.coords.longitude)
        } else {
          updateHole(idx, 'green_latitude', pos.coords.latitude)
          updateHole(idx, 'green_longitude', pos.coords.longitude)
        }
        setCapturingFor(null)
      },
      (err) => {
        setCapturingFor(null)
        alert(lbl(`Error GPS: ${err.message}`, `GPS error: ${err.message}`))
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    )
  }

  const saveCourse = async () => {
    if (!course) return
    setSaving(true)
    try {
      await api.put(`/courses/${id}`, {
        name: course.name,
        description: course.description,
        country: course.country,
        city: course.city,
        address: course.address,
        latitude: course.latitude,
        longitude: course.longitude,
        holes_count: course.holes_count,
        course_rating: course.course_rating,
        slope_rating: course.slope_rating,
      })
      // Guardar hoyos en batch
      const holesPayload = holes.map(h => ({
        hole_number: h.hole_number,
        par: h.par,
        stroke_index: h.stroke_index ?? undefined,
        distance_yards_black: h.distance_yards_black ?? undefined,
        distance_yards_blue: h.distance_yards_blue ?? undefined,
        distance_yards_white: h.distance_yards_white ?? undefined,
        distance_yards_red: h.distance_yards_red ?? undefined,
        green_latitude: h.green_latitude ?? undefined,
        green_longitude: h.green_longitude ?? undefined,
        tee_latitude: h.tee_latitude ?? undefined,
        tee_longitude: h.tee_longitude ?? undefined,
      }))
      await api.post(`/courses/${id}/holes`, holesPayload)
      await load()
      alert(lbl('Campo guardado', 'Course saved'))
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      alert(err.response?.data?.detail || lbl('Error al guardar', 'Error saving'))
    } finally {
      setSaving(false)
    }
  }

  const deleteCourse = async () => {
    if (!confirm(lbl(
      '¿Desactivar este campo? Las rondas históricas se preservan, pero ya no aparecerá al crear nuevas rondas.',
      'Deactivate this course? Historical rounds are preserved, but it will no longer appear when creating new rounds.'
    ))) return
    try {
      await api.delete(`/courses/${id}`)
      router.push(`/${locale}/courses`)
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      alert(err.response?.data?.detail || 'Error')
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  if (error || !canEdit) return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/courses/${id}`} className="text-zinc-400 hover:text-white">
            <ArrowLeft size={20} />
          </Link>
          <span className="font-bold text-white">{lbl('Editar campo', 'Edit course')}</span>
        </div>
      </header>
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center max-w-md">
          <AlertTriangle size={32} className="text-amber-400 mx-auto mb-3" />
          <p className="text-zinc-300 mb-4">{error || lbl('Sin permiso', 'No permission')}</p>
          <Link href={`/${locale}/courses/${id}`} className="text-emerald-400 hover:text-emerald-300 text-sm">
            ← {lbl('Volver al campo', 'Back to course')}
          </Link>
        </div>
      </div>
    </div>
  )

  if (!course) return null

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <Link href={`/${locale}/courses/${id}`} className="text-zinc-400 hover:text-white">
              <ArrowLeft size={20} />
            </Link>
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center">
                <Flag size={14} className="text-white" />
              </div>
              <span className="font-bold text-white truncate">{lbl('Editar', 'Edit')}: {course.name}</span>
            </div>
          </div>
          <button onClick={saveCourse} disabled={saving}
            className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold px-4 py-2 rounded-full text-sm">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {lbl('Guardar', 'Save')}
          </button>
        </div>

        {/* Tabs */}
        <div className="max-w-4xl mx-auto mt-3 flex gap-1 bg-zinc-800 rounded-xl p-1 w-fit">
          <button onClick={() => setActiveTab('details')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === 'details' ? 'bg-zinc-700 text-white' : 'text-zinc-500'
            }`}>
            {lbl('Detalles', 'Details')}
          </button>
          <button onClick={() => setActiveTab('holes')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === 'holes' ? 'bg-zinc-700 text-white' : 'text-zinc-500'
            }`}>
            {lbl('Hoyos', 'Holes')} ({holes.length})
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {activeTab === 'details' && (
          <div className="space-y-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-4">
              <div>
                <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium block mb-1.5">
                  {lbl('Nombre', 'Name')}
                </label>
                <input
                  type="text"
                  value={course.name ?? ''}
                  onChange={e => updateCourseField('name', e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium block mb-1.5">
                  {lbl('Descripción', 'Description')}
                </label>
                <textarea
                  value={course.description ?? ''}
                  onChange={e => updateCourseField('description', e.target.value)}
                  rows={2}
                  className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:border-emerald-500 focus:outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium block mb-1.5">
                    {lbl('Ciudad', 'City')}
                  </label>
                  <input type="text" value={course.city ?? ''}
                    onChange={e => updateCourseField('city', e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:border-emerald-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium block mb-1.5">
                    {lbl('País', 'Country')}
                  </label>
                  <input type="text" value={course.country ?? ''}
                    onChange={e => updateCourseField('country', e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:border-emerald-500 focus:outline-none" />
                </div>
              </div>
              <div>
                <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium block mb-1.5">
                  {lbl('Dirección', 'Address')}
                </label>
                <input type="text" value={course.address ?? ''}
                  onChange={e => updateCourseField('address', e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:border-emerald-500 focus:outline-none" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium block mb-1.5">
                    {lbl('Hoyos', 'Holes')}
                  </label>
                  <input type="number" min={9} max={18} value={course.holes_count ?? 18}
                    onChange={e => updateCourseField('holes_count', parseInt(e.target.value) || 18)}
                    className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:border-emerald-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium block mb-1.5">
                    {lbl('Course Rating', 'Course Rating')}
                  </label>
                  <input type="number" step="0.1" value={course.course_rating ?? ''}
                    onChange={e => updateCourseField('course_rating', e.target.value ? parseFloat(e.target.value) : null)}
                    className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:border-emerald-500 focus:outline-none" />
                </div>
                <div>
                  <label className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium block mb-1.5">
                    Slope
                  </label>
                  <input type="number" value={course.slope_rating ?? ''}
                    onChange={e => updateCourseField('slope_rating', e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:border-emerald-500 focus:outline-none" />
                </div>
              </div>

              {/* GPS del campo */}
              <div className="border-t border-zinc-800 pt-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[11px] text-zinc-500 uppercase tracking-wider font-medium flex items-center gap-1.5">
                    <MapPin size={11} /> {lbl('GPS del campo (clubhouse)', 'Course GPS (clubhouse)')}
                  </p>
                  <button
                    onClick={() => {
                      if (!navigator.geolocation) {
                        alert(lbl('Sin GPS', 'No GPS')); return
                      }
                      navigator.geolocation.getCurrentPosition(
                        (pos) => {
                          updateCourseField('latitude', pos.coords.latitude)
                          updateCourseField('longitude', pos.coords.longitude)
                        },
                        (e) => alert(`GPS: ${e.message}`),
                        { enableHighAccuracy: true, timeout: 15000 }
                      )
                    }}
                    className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300">
                    <Crosshair size={12} /> {lbl('Mi ubicación', 'My location')}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <input type="number" step="0.000001" placeholder="Lat" value={course.latitude ?? ''}
                    onChange={e => updateCourseField('latitude', e.target.value ? parseFloat(e.target.value) : null)}
                    className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white text-xs focus:border-emerald-500 focus:outline-none" />
                  <input type="number" step="0.000001" placeholder="Lng" value={course.longitude ?? ''}
                    onChange={e => updateCourseField('longitude', e.target.value ? parseFloat(e.target.value) : null)}
                    className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-white text-xs focus:border-emerald-500 focus:outline-none" />
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button onClick={deleteCourse}
                className="flex items-center gap-1.5 text-red-400 hover:text-red-300 text-sm font-medium px-3 py-2">
                <Trash2 size={14} /> {lbl('Desactivar campo', 'Deactivate course')}
              </button>
            </div>
          </div>
        )}

        {activeTab === 'holes' && (
          <div className="space-y-3">
            <p className="text-xs text-zinc-500 mb-2">
              {lbl(
                'Edita Par, SI, yardajes y coordenadas GPS del tee y green por hoyo. Toca el icono GPS para capturar tu ubicación actual.',
                'Edit par, SI, yardages and GPS coordinates of tee and green per hole. Tap the GPS icon to capture your current location.'
              )}
            </p>
            {holes.map((h, idx) => (
              <div key={h.hole_number}
                className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center font-bold text-emerald-300">
                    {h.hole_number}
                  </div>
                  <div className="flex-1 grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[9px] text-zinc-500 uppercase tracking-wider block mb-1">Par</label>
                      <input type="number" min={3} max={6} value={h.par}
                        onChange={e => updateHole(idx, 'par', parseInt(e.target.value) || 4)}
                        className="w-full bg-zinc-950 border border-zinc-700 rounded px-2 py-1.5 text-white text-sm tabular-nums" />
                    </div>
                    <div>
                      <label className="text-[9px] text-zinc-500 uppercase tracking-wider block mb-1">SI (1-18)</label>
                      <input type="number" min={1} max={18} value={h.stroke_index ?? ''}
                        onChange={e => updateHole(idx, 'stroke_index', e.target.value ? parseInt(e.target.value) : null)}
                        className="w-full bg-zinc-950 border border-zinc-700 rounded px-2 py-1.5 text-white text-sm tabular-nums" />
                    </div>
                  </div>
                </div>

                {/* Yardages */}
                <div>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1.5">
                    {lbl('Yardajes por color de tee', 'Yardage by tee color')}
                  </p>
                  <div className="grid grid-cols-4 gap-2">
                    {([
                      ['distance_yards_black', 'Negra', 'border-zinc-600'],
                      ['distance_yards_blue', 'Azul', 'border-blue-600/40'],
                      ['distance_yards_white', 'Blanca', 'border-zinc-400/30'],
                      ['distance_yards_red', 'Roja', 'border-red-600/40'],
                    ] as const).map(([field, label, border]) => (
                      <div key={field}>
                        <label className="text-[9px] text-zinc-500 block mb-1">{label}</label>
                        <input type="number" placeholder="—" value={h[field] ?? ''}
                          onChange={e => updateHole(idx, field, e.target.value ? parseInt(e.target.value) : null)}
                          className={`w-full bg-zinc-950 border ${border} rounded px-2 py-1.5 text-white text-xs tabular-nums`} />
                      </div>
                    ))}
                  </div>
                </div>

                {/* GPS tee + green */}
                <div className="mt-3 grid grid-cols-2 gap-3">
                  {([
                    ['tee', 'Tee', 'tee_latitude', 'tee_longitude'],
                    ['green', 'Green', 'green_latitude', 'green_longitude'],
                  ] as const).map(([kind, label, latKey, lngKey]) => (
                    <div key={kind} className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-2">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">
                          {label} GPS
                        </span>
                        <button
                          onClick={() => captureGPS(h.hole_number, kind)}
                          disabled={capturingFor?.hole === h.hole_number && capturingFor.kind === kind}
                          className="flex items-center gap-1 text-[10px] text-emerald-400 hover:text-emerald-300 disabled:opacity-60">
                          {capturingFor?.hole === h.hole_number && capturingFor.kind === kind
                            ? <Loader2 size={10} className="animate-spin" />
                            : <Crosshair size={10} />}
                          {lbl('Capturar', 'Capture')}
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-1">
                        <input type="number" step="0.000001" placeholder="Lat"
                          value={h[latKey] ?? ''}
                          onChange={e => updateHole(idx, latKey, e.target.value ? parseFloat(e.target.value) : null)}
                          className="w-full bg-zinc-950 border border-zinc-700 rounded px-1.5 py-1 text-white text-[10px] tabular-nums" />
                        <input type="number" step="0.000001" placeholder="Lng"
                          value={h[lngKey] ?? ''}
                          onChange={e => updateHole(idx, lngKey, e.target.value ? parseFloat(e.target.value) : null)}
                          className="w-full bg-zinc-950 border border-zinc-700 rounded px-1.5 py-1 text-white text-[10px] tabular-nums" />
                      </div>
                      {/* Pegar de Google Maps */}
                      <input
                        type="text"
                        placeholder={lbl('Pegar de Google Maps...', 'Paste from Google Maps...')}
                        onPaste={e => {
                          const text = e.clipboardData.getData('text')
                          const parsed = parseLatLng(text)
                          if (parsed) {
                            updateHole(idx, latKey, parsed.lat)
                            updateHole(idx, lngKey, parsed.lng)
                            e.preventDefault()
                            ;(e.target as HTMLInputElement).value = ''
                          }
                        }}
                        onChange={e => {
                          const parsed = parseLatLng(e.target.value)
                          if (parsed) {
                            updateHole(idx, latKey, parsed.lat)
                            updateHole(idx, lngKey, parsed.lng)
                            e.target.value = ''
                          }
                        }}
                        className="w-full bg-zinc-900 border border-zinc-800 hover:border-emerald-500/40 focus:border-emerald-500 rounded px-2 py-1 text-zinc-400 placeholder-zinc-600 text-[10px] mt-1.5 focus:outline-none transition-colors"
                      />
                      {(h[latKey] !== null && h[lngKey] !== null) && (
                        <button
                          onClick={() => {
                            updateHole(idx, latKey, null)
                            updateHole(idx, lngKey, null)
                          }}
                          className="text-[9px] text-zinc-500 hover:text-red-400 mt-1 flex items-center gap-1">
                          <X size={9} /> {lbl('Limpiar', 'Clear')}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
