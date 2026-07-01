'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { CheckCircle2, AlertTriangle, Loader2, Flag, ArrowLeft, Trophy } from 'lucide-react'
import { api, isAuthed } from '@/lib/api'
import { useLocale } from '@/components/DictionaryProvider'

interface Score {
  hole: number
  gross: number
  net: number | null
  putts?: number | null
}

interface HoleInfo {
  hole_number: number
  par: number
  stroke_index: number | null
}

interface PlayerInfo {
  user_id: string
  name: string
  is_group_scorer?: boolean
  score_validated_at: string | null
}

export default function ValidatePage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en

  const [loading, setLoading] = useState(true)
  const [round, setRound] = useState<{ status: string; name: string | null; holes_to_play: number; course_id: string } | null>(null)
  const [myUserId, setMyUserId] = useState<string>('')
  const [myScores, setMyScores] = useState<Score[]>([])
  const [holes, setHoles] = useState<HoleInfo[]>([])
  const [validatedAt, setValidatedAt] = useState<string | null>(null)
  const [signing, setSigning] = useState(false)
  const [pendingPlayers, setPendingPlayers] = useState<PlayerInfo[]>([])
  const [allPlayers, setAllPlayers] = useState<PlayerInfo[]>([])

  useEffect(() => {
    if (!isAuthed()) { router.push(`/${locale}/auth/login`); return }
    const load = async () => {
      try {
        const [rRes, meRes] = await Promise.all([api.get(`/rounds/${id}`), api.get('/users/me')])
        const r = rRes.data
        const me = meRes.data
        setMyUserId(me.id)
        setRound({ status: r.status, name: r.name, holes_to_play: r.holes_to_play, course_id: r.course_id })

        if (r.status === 'finished') {
          router.push(`/${locale}/rounds/${id}`)
          return
        }
        if (r.status === 'active') {
          // Aún no está en pending — volver al Play page
          router.push(`/${locale}/rounds/${id}/play`)
          return
        }

        // Holes
        const courseRes = await api.get(`/courses/${r.course_id}`)
        setHoles(courseRes.data.holes)

        // My scores
        const boardRes = await api.get(`/rounds/${id}/scoreboard`)
        type BoardRow = { user_id: string; scores: Score[] }
        const myRow = (boardRes.data as BoardRow[]).find(b => b.user_id === me.id)
        setMyScores(myRow?.scores ?? [])

        // Tee groups → estado de validación
        const tgRes = await api.get(`/rounds/${id}/tee-groups`)
        type TGP = { user_id: string; name: string; is_group_scorer?: boolean; score_validated_at: string | null }
        type TGG = { group_number: number; players: TGP[] }
        const all: PlayerInfo[] = []
        for (const g of (tgRes.data.groups as TGG[])) {
          for (const p of g.players) {
            all.push({ user_id: p.user_id, name: p.name, is_group_scorer: p.is_group_scorer, score_validated_at: p.score_validated_at })
          }
        }
        setAllPlayers(all)
        const myPlayer = all.find(p => p.user_id === me.id)
        setValidatedAt(myPlayer?.score_validated_at ?? null)
        setPendingPlayers(all.filter(p => !p.score_validated_at))
      } finally { setLoading(false) }
    }
    load()
  }, [id, locale, router])

  const handleSign = async () => {
    setSigning(true)
    try {
      const res = await api.post(`/rounds/${id}/players/me/validate-scorecard`)
      setValidatedAt(res.data.validated_at)
      setPendingPlayers(prev => prev.filter(p => p.user_id !== myUserId))
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail ?? lbl('Error al firmar la tarjeta', 'Error signing scorecard'))
    } finally { setSigning(false) }
  }

  const handleReportDifference = () => {
    // Lleva al usuario al Play page donde puede ver el detalle hoyo a hoyo
    // y desde ahí (con captura cruzada) puede iniciar un conflicto.
    // Como flujo simple por ahora, le mostramos un alert sugiriendo abrir un conflicto
    // entrando al detalle de la ronda.
    if (confirm(lbl(
      'Para reportar una diferencia, regresarás al detalle de la ronda donde podrás ver hoyo por hoyo y contactar al capturista. ¿Continuar?',
      'To report a difference, you will be sent to the round detail where you can review hole-by-hole and contact the scorer. Continue?'
    ))) {
      router.push(`/${locale}/rounds/${id}`)
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <Loader2 size={28} className="animate-spin text-emerald-500" />
    </div>
  )

  if (!round) return null

  const totalGross = myScores.reduce((sum, s) => sum + (s.gross || 0), 0)
  const totalNet = myScores.reduce((sum, s) => sum + (s.net ?? s.gross ?? 0), 0)
  const totalPar = holes.slice(0, round.holes_to_play).reduce((sum, h) => sum + h.par, 0)
  const diffPar = totalGross - totalPar
  const allValidated = pendingPlayers.length === 0

  return (
    <div className="min-h-screen bg-zinc-950 pb-12">
      <header className="bg-zinc-900 border-b border-zinc-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Link href={`/${locale}/rounds/${id}`}
            className="text-zinc-400 hover:text-white transition-colors flex items-center gap-1.5 text-sm">
            <ArrowLeft size={15} />
            {lbl('Ronda', 'Round')}
          </Link>
          <div className="flex items-center gap-2">
            <Flag size={14} className="text-emerald-400" />
            <span className="font-bold text-white text-sm">{lbl('Validación', 'Validation')}</span>
          </div>
          <span className="w-12" />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-5 space-y-4">
        {/* Estado */}
        <div className={`rounded-2xl p-4 border ${
          validatedAt
            ? 'bg-emerald-500/10 border-emerald-500/40'
            : 'bg-amber-500/10 border-amber-500/40'
        }`}>
          {validatedAt ? (
            <div className="flex items-start gap-3">
              <CheckCircle2 size={20} className="text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-emerald-300 text-sm">{lbl('Ya firmaste tu tarjeta', 'You signed your scorecard')}</p>
                <p className="text-xs text-emerald-300/70 mt-0.5">
                  {allValidated
                    ? lbl('Todos firmaron. El creador puede cerrar la ronda definitivamente.', 'Everyone signed. The creator can finalize the round.')
                    : lbl(`Esperando firma de ${pendingPlayers.length} jugador(es)`, `Waiting for ${pendingPlayers.length} player(s) to sign`)}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-amber-300 text-sm">{lbl('Revisa tu tarjeta y firma', 'Review your scorecard and sign')}</p>
                <p className="text-xs text-amber-300/70 mt-0.5">
                  {lbl(
                    'Si todo está correcto, firma. Si hay alguna diferencia, repórtala antes.',
                    'If everything looks right, sign. If something is off, report it first.'
                  )}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Resumen */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <p className="text-xs text-zinc-500 uppercase tracking-wide">Gross</p>
            <p className="text-3xl font-black text-white mt-0.5">{totalGross}</p>
            <p className="text-xs text-zinc-500 mt-0.5">{diffPar >= 0 ? `+${diffPar}` : diffPar} {lbl('vs par', 'vs par')}</p>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <p className="text-xs text-zinc-500 uppercase tracking-wide">Net</p>
            <p className="text-3xl font-black text-emerald-400 mt-0.5">{totalNet}</p>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
            <p className="text-xs text-zinc-500 uppercase tracking-wide">Par</p>
            <p className="text-3xl font-black text-zinc-400 mt-0.5">{totalPar}</p>
          </div>
        </div>

        {/* Scorecard hoyo a hoyo */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 bg-zinc-800/30">
            <h3 className="text-sm font-semibold text-white">{lbl('Tu tarjeta', 'Your scorecard')}</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-zinc-500 uppercase tracking-wide">
                <tr className="border-b border-zinc-800">
                  <th className="px-3 py-2 text-left font-semibold">{lbl('Hoyo', 'Hole')}</th>
                  <th className="px-3 py-2 text-center font-semibold">Par</th>
                  <th className="px-3 py-2 text-center font-semibold">SI</th>
                  <th className="px-3 py-2 text-center font-semibold">Gross</th>
                  <th className="px-3 py-2 text-center font-semibold">Net</th>
                </tr>
              </thead>
              <tbody>
                {holes.slice(0, round.holes_to_play).map(h => {
                  const s = myScores.find(sc => sc.hole === h.hole_number)
                  const isBirdie = s && s.gross && s.gross < h.par
                  const isBogey = s && s.gross && s.gross > h.par
                  return (
                    <tr key={h.hole_number} className="border-b border-zinc-800/60">
                      <td className="px-3 py-2 font-bold text-zinc-300">{h.hole_number}</td>
                      <td className="px-3 py-2 text-center text-zinc-400">{h.par}</td>
                      <td className="px-3 py-2 text-center text-zinc-500 text-xs">{h.stroke_index ?? '—'}</td>
                      <td className={`px-3 py-2 text-center font-bold ${
                        isBirdie ? 'text-emerald-400' : isBogey ? 'text-orange-400' : 'text-white'
                      }`}>{s?.gross ?? '—'}</td>
                      <td className="px-3 py-2 text-center text-emerald-300">{s?.net ?? s?.gross ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Estado de firmas del grupo */}
        {allPlayers.length > 1 && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <h3 className="text-sm font-semibold text-white mb-3">{lbl('Firmas del grupo', 'Group signatures')}</h3>
            <div className="space-y-2">
              {allPlayers.map(p => (
                <div key={p.user_id} className="flex items-center justify-between bg-zinc-800/40 rounded-lg px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-white">
                      {p.name}
                      {p.user_id === myUserId && <span className="ml-1.5 text-xs text-emerald-400">{lbl('(tú)', '(you)')}</span>}
                      {p.is_group_scorer && <span className="ml-1.5 text-[10px] text-emerald-300">🎯</span>}
                    </span>
                  </div>
                  {p.score_validated_at ? (
                    <span className="text-xs text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 size={12} /> {lbl('Firmado', 'Signed')}
                    </span>
                  ) : (
                    <span className="text-xs text-amber-400 flex items-center gap-1">
                      <Loader2 size={12} className="animate-spin" /> {lbl('Pendiente', 'Pending')}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Botones de acción */}
        {!validatedAt && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <button
              onClick={handleReportDifference}
              className="flex items-center justify-center gap-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 py-3 rounded-xl text-sm font-medium transition-colors">
              <AlertTriangle size={15} />
              {lbl('Reportar diferencia', 'Report difference')}
            </button>
            <button
              onClick={handleSign}
              disabled={signing}
              className="flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-white py-3 rounded-xl text-sm font-semibold transition-colors">
              {signing ? <Loader2 size={15} className="animate-spin" /> : <Trophy size={15} />}
              {lbl('Firmar tarjeta', 'Sign scorecard')}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
