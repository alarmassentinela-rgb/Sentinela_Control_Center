'use client'
import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Flag, ArrowLeft, Loader2, Calendar, Info, X } from 'lucide-react'
import { api } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Course { id: string; name: string; city: string | null }

const FORMATS = [
  { value: 'stroke',              labelEs: 'Stroke Play (Medal)', labelEn: 'Stroke Play (Medal)' },
  { value: 'stableford',          labelEs: 'Stableford',          labelEn: 'Stableford' },
  { value: 'stableford_modified', labelEs: 'Stableford Modificado', labelEn: 'Modified Stableford' },
  { value: 'match',               labelEs: 'Match Play',          labelEn: 'Match Play' },
  { value: 'skins',               labelEs: 'Skines',              labelEn: 'Skins' },
  { value: 'florida',             labelEs: 'Florida',             labelEn: 'Florida' },
]

const FORMAT_SHORT: Record<string, { titleEs: string; titleEn: string; descEs: string; descEn: string; rulesEs: {label:string;value:string}[]; rulesEn: {label:string;value:string}[]; egEs: {desc:string;result:string;h?:boolean}[]; egEn: {desc:string;result:string;h?:boolean}[]; noteEs?: string; noteEn?: string }> = {
  stroke: {
    titleEs: 'Stroke Play', titleEn: 'Stroke Play',
    descEs: 'Suma todos tus golpes. El menor total gana. Formato oficial WHS para hándicap.',
    descEn: 'Count every stroke. Lowest total wins. Official WHS handicap format.',
    rulesEs: [{ label:'Birdie (−1)', value:'−1 golpe' },{ label:'Par', value:'0' },{ label:'Bogey (+1)', value:'+1 golpe' },{ label:'Score neto', value:'Bruto − HCP campo' }],
    rulesEn: [{ label:'Birdie (−1)', value:'−1 stroke' },{ label:'Par', value:'0' },{ label:'Bogey (+1)', value:'+1 stroke' },{ label:'Net score', value:'Gross − Course HCP' }],
    egEs: [{ desc:'Juegas 85, HCP 10 → neto 75', result:'75' },{ desc:'Rival: 80, HCP 4 → neto 76', result:'76' },{ desc:'Tú ganas en neto', result:'¡Victoria!', h:true }],
    egEn: [{ desc:'You shoot 85, HCP 10 → net 75', result:'75' },{ desc:'Rival: 80, HCP 4 → net 76', result:'76' },{ desc:'You win net', result:'Win!', h:true }],
  },
  stableford: {
    titleEs: 'Stableford', titleEn: 'Stableford',
    descEs: 'Puntos por hoyo según golpes vs par. Más puntos gana. Los hoyos malos valen 0 (no restan).',
    descEn: 'Points per hole based on strokes vs par. Most points wins. Bad holes score 0 — never negative.',
    rulesEs: [{ label:'Águila −2', value:'4 pts' },{ label:'Birdie −1', value:'3 pts' },{ label:'Par', value:'2 pts' },{ label:'Bogey +1', value:'1 pt' },{ label:'Doble bogey +', value:'0 pts' }],
    rulesEn: [{ label:'Eagle −2', value:'4 pts' },{ label:'Birdie −1', value:'3 pts' },{ label:'Par', value:'2 pts' },{ label:'Bogey +1', value:'1 pt' },{ label:'Double bogey +', value:'0 pts' }],
    egEs: [{ desc:'Hoyo par 4, HCP 18 → recibes 1 golpe extra', result:'' },{ desc:'Haces 5 (par ajustado)', result:'2 pts', h:true },{ desc:'Haces 4 (birdie ajustado)', result:'3 pts', h:true }],
    egEn: [{ desc:'Hole par 4, HCP 18 → get 1 extra stroke', result:'' },{ desc:'Score 5 (adjusted par)', result:'2 pts', h:true },{ desc:'Score 4 (adjusted birdie)', result:'3 pts', h:true }],
  },
  stableford_modified: {
    titleEs: 'Stableford Modificado', titleEn: 'Modified Stableford',
    descEs: 'Como Stableford pero con más variación: birdie da solo 2 pts y los bogeys penalizan. Usado en competencias de alto nivel.',
    descEn: 'Like Stableford but more volatile: birdies score 2 pts and bogeys penalize. Used in elite competitions.',
    rulesEs: [{ label:'Albatros −3', value:'+8 pts' },{ label:'Águila −2', value:'+5 pts' },{ label:'Birdie −1', value:'+2 pts' },{ label:'Par', value:'0' },{ label:'Bogey +1', value:'−1 pt' },{ label:'Doble bogey +', value:'−3 pts' }],
    rulesEn: [{ label:'Albatross −3', value:'+8 pts' },{ label:'Eagle −2', value:'+5 pts' },{ label:'Birdie −1', value:'+2 pts' },{ label:'Par', value:'0' },{ label:'Bogey +1', value:'−1 pt' },{ label:'Double bogey +', value:'−3 pts' }],
    egEs: [{ desc:'Birdie, bogey, par, doble bogey', result:'' },{ desc:'2 + (−1) + 0 + (−3)', result:'−2 pts total', h:true }],
    egEn: [{ desc:'Birdie, bogey, par, double bogey', result:'' },{ desc:'2 + (−1) + 0 + (−3)', result:'−2 pts total', h:true }],
  },
  match: {
    titleEs: 'Match Play', titleEn: 'Match Play',
    descEs: 'Se compite hoyo a hoyo. Ganas el hoyo si haces menos golpes. El partido termina cuando ya no es posible empatar.',
    descEn: 'Compete hole by hole. Win the hole with fewer strokes. Match ends when the deficit is uncatchable.',
    rulesEs: [{ label:'Ganar hoyo', value:'+1 UP' },{ label:'Empatar hoyo', value:'AS (igual)' },{ label:'Perder hoyo', value:'−1' },{ label:'Resultado', value:'"3&2" = 3 hoyos arriba, 2 por jugar' }],
    rulesEn: [{ label:'Win hole', value:'+1 UP' },{ label:'Halve hole', value:'AS (level)' },{ label:'Lose hole', value:'−1' },{ label:'Result', value:'"3&2" = 3 up, 2 to play' }],
    egEs: [{ desc:'H1: tú 4, rival 5 → tú ganas', result:'1UP' },{ desc:'H2: tú 5, rival 5 → empate', result:'1UP' },{ desc:'H3: tú 6, rival 4 → rival gana', result:'AS', h:true }],
    egEn: [{ desc:'H1: you 4, opp 5 → you win', result:'1UP' },{ desc:'H2: you 5, opp 5 → halved', result:'1UP' },{ desc:'H3: you 6, opp 4 → opp wins', result:'AS', h:true }],
  },
  skins: {
    titleEs: 'Skines (Skins)', titleEn: 'Skins',
    descEs: 'Cada hoyo vale una piel ($). Gana quien tenga el score más bajo solo en ese hoyo. Si hay empate, la piel se acumula al siguiente hoyo (carry-over).',
    descEn: 'Each hole is worth a skin ($). Sole lowest score wins the skin. Ties carry the pot to the next hole.',
    rulesEs: [{ label:'Ganador único', value:'Se lleva la piel' },{ label:'Empate', value:'Carry-over al siguiente' },{ label:'Bote máximo', value:'Cuando termina una racha de empates' }],
    rulesEn: [{ label:'Sole winner', value:'Takes the skin' },{ label:'Tie', value:'Carries to next hole' },{ label:'Max pot', value:'When a tie streak ends' }],
    egEs: [{ desc:'H1: A:4, B:4 → empate → carry $100', result:'$100 bote' },{ desc:'H2: A:5, B:4 → empate → carry $200', result:'$200 bote' },{ desc:'H3: A:3, B:4 → A gana solo', result:'A gana $300', h:true }],
    egEn: [{ desc:'H1: A:4, B:4 → tie → carry $100', result:'$100 pot' },{ desc:'H2: A:5, B:4 → tie → carry $200', result:'$200 pot' },{ desc:'H3: A:3, B:4 → A sole winner', result:'A wins $300', h:true }],
  },
  florida: {
    titleEs: 'Florida (Best Ball por equipos)', titleEn: 'Florida (Team Best Ball)',
    descEs: 'Formato por equipos de 2, 3 o 4 jugadores. Cada jugador juega su propia pelota. El score del equipo en cada hoyo es el MEJOR score neto de los integrantes. Gana el equipo con menos golpes netos al final.',
    descEn: 'Team format with 2, 3, or 4 players per team. Each player plays their own ball. The team score on each hole is the BEST net score among teammates. Lowest total net wins.',
    rulesEs: [{ label:'Jugadores/equipo', value:'2, 3 ó 4' },{ label:'Score por hoyo', value:'Mejor score neto del equipo' },{ label:'Score individual', value:'Bruto − HCP campo' },{ label:'Ganador', value:'Equipo con menos golpes netos total' }],
    rulesEn: [{ label:'Players/team', value:'2, 3 or 4' },{ label:'Hole score', value:'Best net score in team' },{ label:'Individual score', value:'Gross − Course HCP' },{ label:'Winner', value:'Team with lowest total net' }],
    egEs: [
      { desc:'Equipo A — hoyo par 4', result:'' },
      { desc:'Jugador 1: 5 bruto, HCP 12 → recibe 1 golpe → 4 neto', result:'4 neto' },
      { desc:'Jugador 2: 6 bruto, HCP 24 → recibe 1 golpe → 5 neto', result:'5 neto' },
      { desc:'Score del equipo en el hoyo', result:'4 (mejor neto)', h:true },
    ],
    egEn: [
      { desc:'Team A — par 4 hole', result:'' },
      { desc:'Player 1: 5 gross, HCP 12 → gets 1 stroke → 4 net', result:'4 net' },
      { desc:'Player 2: 6 gross, HCP 24 → gets 1 stroke → 5 net', result:'5 net' },
      { desc:'Team score on hole', result:'4 (best net)', h:true },
    ],
  },
}

function FormatInfoModal({ format, locale, onClose }: { format: string; locale: string; onClose: () => void }) {
  const info = FORMAT_SHORT[format]
  if (!info) return null
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-2xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
              <Info size={13} className="text-emerald-400" />
            </div>
            <span className="font-bold text-white text-sm">{lbl(info.titleEs, info.titleEn)}</span>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white"><X size={18}/></button>
        </div>
        <div className="px-5 py-4 space-y-4 max-h-[65vh] overflow-y-auto">
          <p className="text-sm text-zinc-400 leading-relaxed">{lbl(info.descEs, info.descEn)}</p>
          <div className="bg-zinc-800 rounded-xl overflow-hidden">
            <div className="px-3 py-2 border-b border-zinc-700">
              <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">{lbl('Puntuación', 'Scoring')}</span>
            </div>
            {(locale === 'es' ? info.rulesEs : info.rulesEn).map((r,i) => (
              <div key={i} className="flex justify-between px-3 py-2 border-b border-zinc-700/40 last:border-0">
                <span className="text-xs text-zinc-400">{r.label}</span>
                <span className="text-xs font-semibold text-white">{r.value}</span>
              </div>
            ))}
          </div>
          <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl overflow-hidden">
            <div className="px-3 py-2 border-b border-zinc-700/50">
              <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">{lbl('Ejemplo', 'Example')}</span>
            </div>
            {(locale === 'es' ? info.egEs : info.egEn).map((s,i) => (
              <div key={i} className={`flex justify-between px-3 py-2.5 border-b border-zinc-700/30 last:border-0 ${s.h ? 'bg-emerald-500/10' : ''}`}>
                <span className="text-xs text-zinc-400 flex-1 pr-3">{s.desc}</span>
                {s.result && <span className={`text-xs font-bold flex-shrink-0 ${s.h ? 'text-emerald-400' : 'text-zinc-300'}`}>{s.result}</span>}
              </div>
            ))}
          </div>
        </div>
        <div className="px-5 pb-5">
          <button onClick={onClose} className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium py-2.5 rounded-xl text-sm transition-colors">
            {lbl('Entendido', 'Got it')}
          </button>
        </div>
      </div>
    </div>
  )
}

function NewRoundForm() {
  const locale = useLocale()
  const router = useRouter()
  const searchParams = useSearchParams()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [courses, setCourses] = useState<Course[]>([])
  const [form, setForm] = useState({
    course_id: searchParams.get('course_id') ?? '',
    name: '',
    game_format: 'stroke',
    team_size: 2,
    holes_to_play: 18,
    is_handicap_valid: true,
    scheduled_at: new Date().toISOString().slice(0, 16),
  })
  const [teeColor, setTeeColor] = useState('blue')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [showFormatInfo, setShowFormatInfo] = useState(false)

  useEffect(() => {
    api.get('/courses').then(r => setCourses(r.data))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.course_id) { setError(lbl('Selecciona una cancha', 'Select a course')); return }
    setSaving(true); setError('')
    try {
      const res = await api.post('/rounds', {
        course_id: form.course_id,
        name: form.name || null,
        game_format: form.game_format,
        team_size: form.game_format === 'florida' ? form.team_size : 1,
        holes_to_play: form.holes_to_play,
        is_handicap_valid: form.is_handicap_valid,
        scheduled_at: new Date(form.scheduled_at).toISOString(),
        scoring_type: 'gross',
      })
      await api.patch(`/rounds/${res.data.id}/my-tee?tee_color=${teeColor}`)
      router.push(`/${locale}/rounds/${res.data.id}`)
    } catch {
      setError(lbl('Error al crear la ronda', 'Error creating round'))
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      {showFormatInfo && (
        <FormatInfoModal format={form.game_format} locale={locale} onClose={() => setShowFormatInfo(false)} />
      )}
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <button onClick={() => router.back()} className="text-zinc-400 hover:text-white transition-colors">
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
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Flag size={20} className="text-emerald-400" />
            </div>
            <h1 className="text-xl font-bold text-white">{lbl('Nueva ronda', 'New round')}</h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Cancha */}
            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Cancha *', 'Course *')}</label>
              <select value={form.course_id} onChange={(e) => setForm({ ...form, course_id: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm">
                <option value="">{lbl('— Selecciona una cancha —', '— Select a course —')}</option>
                {courses.map(c => (
                  <option key={c.id} value={c.id}>{c.name}{c.city ? ` — ${c.city}` : ''}</option>
                ))}
              </select>
            </div>

            {/* Nombre opcional */}
            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Nombre de la ronda (opcional)', 'Round name (optional)')}</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm"
                placeholder={lbl('Ej. Torneo amigos', 'e.g. Friends tournament')} />
            </div>

            {/* Formato */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium text-zinc-300">{lbl('Formato de juego', 'Game format')}</label>
                <button type="button" onClick={() => setShowFormatInfo(true)}
                  className="flex items-center gap-1 text-xs text-zinc-600 hover:text-emerald-400 transition-colors">
                  <Info size={12} />{lbl('¿Cómo funciona?', 'How does it work?')}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {FORMATS.map(f => (
                  <button key={f.value} type="button"
                    onClick={() => setForm({ ...form, game_format: f.value })}
                    className={`px-4 py-3 rounded-xl text-sm font-medium border transition-all text-left ${
                      form.game_format === f.value
                        ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300'
                        : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:border-zinc-500'
                    }`}>
                    {locale === 'es' ? f.labelEs : f.labelEn}
                  </button>
                ))}
              </div>

              {/* Team size — solo visible en Florida */}
              {form.game_format === 'florida' && (
                <div className="mt-3 bg-zinc-800/60 border border-emerald-500/20 rounded-xl p-4">
                  <label className="text-sm font-medium text-zinc-300 block mb-3">
                    {lbl('Jugadores por equipo', 'Players per team')}
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[2, 3, 4].map(n => (
                      <button key={n} type="button"
                        onClick={() => setForm({ ...form, team_size: n })}
                        className={`py-3 rounded-xl text-sm font-bold border transition-all ${
                          form.team_size === n
                            ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300'
                            : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500'
                        }`}>
                        {n} {lbl('jug.', 'players')}
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-zinc-600 mt-2">
                    {lbl(
                      'Cuenta el mejor score neto de cada equipo por hoyo',
                      'Best net score per team counts on each hole'
                    )}
                  </p>
                </div>
              )}
            </div>

            {/* Hoyos y fecha */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Hoyos', 'Holes')}</label>
                <select value={form.holes_to_play} onChange={(e) => setForm({ ...form, holes_to_play: Number(e.target.value) })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm">
                  <option value={9}>9 {lbl('hoyos', 'holes')}</option>
                  <option value={18}>18 {lbl('hoyos', 'holes')}</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-300 block mb-1.5">{lbl('Fecha y hora', 'Date & time')}</label>
                <input type="datetime-local" value={form.scheduled_at}
                  onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm" />
              </div>
            </div>

            {/* Tee de salida */}
            <div>
              <label className="text-sm font-medium text-zinc-300 block mb-2">{lbl('Tu tee de salida *', 'Your tee *')}</label>
              <div className="grid grid-cols-4 gap-2">
                {[
                  { value: 'black', label: lbl('Negra', 'Black'), dot: 'bg-zinc-900 border-2 border-zinc-600', text: 'text-zinc-300' },
                  { value: 'blue',  label: lbl('Azul',  'Blue'),  dot: 'bg-blue-600',  text: 'text-blue-300' },
                  { value: 'white', label: lbl('Blanca','White'), dot: 'bg-white border border-zinc-500', text: 'text-zinc-200' },
                  { value: 'red',   label: lbl('Roja',  'Red'),   dot: 'bg-red-600',   text: 'text-red-300' },
                ].map(t => (
                  <button key={t.value} type="button" onClick={() => setTeeColor(t.value)}
                    className={`flex flex-col items-center gap-2 py-3 px-2 rounded-xl border transition-all ${
                      teeColor === t.value
                        ? 'border-emerald-500 bg-emerald-500/10'
                        : 'border-zinc-700 bg-zinc-800 hover:border-zinc-500'
                    }`}>
                    <div className={`w-5 h-5 rounded-full ${t.dot}`} />
                    <span className={`text-xs font-semibold ${teeColor === t.value ? 'text-white' : t.text}`}>{t.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Hándicap válido */}
            <div className="flex items-center gap-3 bg-zinc-800 rounded-xl px-4 py-3">
              <input type="checkbox" id="hcp_valid" checked={form.is_handicap_valid}
                onChange={(e) => setForm({ ...form, is_handicap_valid: e.target.checked })}
                className="w-4 h-4 accent-emerald-500" />
              <label htmlFor="hcp_valid" className="text-sm text-zinc-300">
                {lbl('Ronda válida para hándicap WHS', 'Count for WHS handicap')}
              </label>
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button type="submit" disabled={saving}
              className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-colors text-sm mt-2">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Calendar size={16} />}
              {lbl('Crear ronda', 'Create round')}
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

export default function NewRoundPage() {
  return <Suspense><NewRoundForm /></Suspense>
}
