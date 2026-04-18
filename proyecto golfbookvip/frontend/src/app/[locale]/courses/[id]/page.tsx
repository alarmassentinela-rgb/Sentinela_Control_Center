'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, MapPin, Star, Loader2, Hash } from 'lucide-react'
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
}

interface Course {
  id: string
  name: string
  city: string | null
  country: string | null
  holes_count: number
  par_total: number | null
  course_rating: number | null
  slope_rating: number | null
  holes: Hole[]
}

export default function CourseDetailPage() {
  const locale = useLocale()
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [course, setCourse] = useState<Course | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!localStorage.getItem('access_token')) { router.push(`/${locale}/auth/login`); return }
    api.get(`/courses/${id}`)
      .then((r) => setCourse(r.data))
      .catch(() => setError(lbl('Campo no encontrado', 'Course not found')))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <Link href={`/${locale}/courses`} className="text-zinc-400 hover:text-white transition-colors">
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

      <main className="max-w-4xl mx-auto px-4 py-8">
        {error ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-12 text-center">
            <p className="text-zinc-400">{error}</p>
            <Link href={`/${locale}/courses`} className="mt-4 inline-block text-emerald-400 hover:text-emerald-300 text-sm">
              ← {lbl('Volver a canchas', 'Back to courses')}
            </Link>
          </div>
        ) : course && (
          <div className="space-y-6">
            {/* Course header */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                  <Flag size={22} className="text-emerald-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <h1 className="text-2xl font-bold text-white mb-1">{course.name}</h1>
                  {(course.city || course.country) && (
                    <div className="flex items-center gap-1.5 text-sm text-zinc-400 mb-3">
                      <MapPin size={14} />
                      {[course.city, course.country].filter(Boolean).join(', ')}
                    </div>
                  )}
                  <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-400">
                    <span className="bg-zinc-800 px-3 py-1 rounded-full text-xs">
                      {course.holes_count} {lbl('hoyos', 'holes')}
                    </span>
                    {course.par_total && (
                      <span className="flex items-center gap-1.5">
                        <Hash size={13} className="text-emerald-400" />
                        Par {course.par_total}
                      </span>
                    )}
                    {course.course_rating && (
                      <span className="flex items-center gap-1.5">
                        <Star size={13} className="text-yellow-500" />
                        {lbl('Rating', 'Rating')} {course.course_rating.toFixed(1)}
                      </span>
                    )}
                    {course.slope_rating && (
                      <span className="text-zinc-400">
                        Slope {course.slope_rating}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Holes table */}
            {course.holes.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
                <h2 className="font-semibold text-white mb-4">{lbl('Hoyos', 'Holes')}</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-zinc-500 text-xs border-b border-zinc-800">
                        <th className="text-left pb-3 pr-4">{lbl('Hoyo', 'Hole')}</th>
                        <th className="text-center pb-3 pr-4">Par</th>
                        <th className="text-center pb-3 pr-4">SI</th>
                        <th className="text-center pb-3 pr-4 text-zinc-600">{lbl('Neg', 'Blk')}</th>
                        <th className="text-center pb-3 pr-4 text-blue-400">{lbl('Azul', 'Blue')}</th>
                        <th className="text-center pb-3 pr-4 text-white">{lbl('Bco', 'Wht')}</th>
                        <th className="text-center pb-3 text-red-400">{lbl('Roja', 'Red')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800">
                      {course.holes.map((h) => (
                        <tr key={h.hole_number} className="hover:bg-zinc-800/30 transition-colors">
                          <td className="py-2.5 pr-4">
                            <span className="w-7 h-7 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-bold flex items-center justify-center">
                              {h.hole_number}
                            </span>
                          </td>
                          <td className="py-2.5 pr-4 text-center">
                            <span className={`font-semibold ${
                              h.par === 3 ? 'text-blue-400' :
                              h.par === 5 ? 'text-yellow-400' : 'text-white'
                            }`}>{h.par}</span>
                          </td>
                              <td className="py-2.5 pr-4 text-center text-zinc-400">
                            {h.stroke_index ?? '—'}
                          </td>
                          <td className="py-2.5 pr-4 text-center text-zinc-500 text-xs">
                            {h.distance_yards_black ?? '—'}
                          </td>
                          <td className="py-2.5 pr-4 text-center text-blue-300 text-xs">
                            {h.distance_yards_blue ?? '—'}
                          </td>
                          <td className="py-2.5 pr-4 text-center text-zinc-300 text-xs">
                            {h.distance_yards_white ?? '—'}
                          </td>
                          <td className="py-2.5 text-center text-red-300 text-xs">
                            {h.distance_yards_red ?? '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    {/* Totals row */}
                    <tfoot>
                      <tr className="border-t border-zinc-700 text-xs font-semibold text-zinc-300">
                        <td className="pt-3 pr-4">{lbl('Total', 'Total')}</td>
                        <td className="pt-3 pr-4 text-center">{course.holes.reduce((s, h) => s + h.par, 0)}</td>
                        <td className="pt-3 pr-4" />
                        <td className="pt-3 pr-4 text-center text-zinc-500">
                          {course.holes.some(h => h.distance_yards_black) ? course.holes.reduce((s,h) => s+(h.distance_yards_black??0),0) : '—'}
                        </td>
                        <td className="pt-3 pr-4 text-center text-blue-300">
                          {course.holes.some(h => h.distance_yards_blue) ? course.holes.reduce((s,h) => s+(h.distance_yards_blue??0),0) : '—'}
                        </td>
                        <td className="pt-3 pr-4 text-center text-zinc-300">
                          {course.holes.some(h => h.distance_yards_white) ? course.holes.reduce((s,h) => s+(h.distance_yards_white??0),0) : '—'}
                        </td>
                        <td className="pt-3 text-center text-red-300">
                          {course.holes.some(h => h.distance_yards_red) ? course.holes.reduce((s,h) => s+(h.distance_yards_red??0),0) : '—'}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}

            {/* CTA */}
            <div className="flex justify-center">
              <Link href={`/${locale}/rounds/new?course_id=${course.id}`}
                className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold px-8 py-3 rounded-full transition-colors text-sm">
                <Flag size={16} />
                {lbl('Iniciar ronda en esta cancha', 'Start a round here')}
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
