'use client'
import { useState } from 'react'
import Link from 'next/link'
import { Flag, ArrowLeft, ChevronDown, ChevronUp, HelpCircle, User, Trophy } from 'lucide-react'
import { useLocale } from '@/components/DictionaryProvider'

interface Section { id: string; titleEs: string; titleEn: string; es: string[]; en: string[] }

const PLAYER: Section[] = [
  { id: 'cuenta', titleEs: 'Crear tu cuenta', titleEn: 'Create your account', es: [
    'Entra a golfbookvip.com y toca Crear cuenta.',
    'Registra tu correo (será tu usuario), nombre y contraseña.',
    'Ingresa tu handicap inicial (0–54). Si no lo sabes, pon un estimado: el sistema lo afina con tus tarjetas.',
    'Si entraste desde un link de invitación, quedas automáticamente en esa ronda.',
  ], en: [
    'Go to golfbookvip.com and tap Create account.',
    'Register your email (your username), name and password.',
    'Enter your initial handicap (0–54). If unknown, put an estimate: the system refines it with your cards.',
    'If you came from an invite link, you join that round automatically.',
  ]},
  { id: 'instalar', titleEs: 'Instalar la app en tu celular', titleEn: 'Install the app on your phone', es: [
    'Es una PWA: se instala sin tienda.',
    '• iPhone (Safari): Compartir → Agregar a inicio.',
    '• Android (Chrome): menú ⋮ → Instalar app.',
  ], en: [
    'It is a PWA: installs without a store.',
    '• iPhone (Safari): Share → Add to Home Screen.',
    '• Android (Chrome): ⋮ menu → Install app.',
  ]},
  { id: 'password', titleEs: 'Recuperar tu contraseña', titleEn: 'Recover your password', es: [
    'En Iniciar sesión → ¿Olvidaste tu contraseña?',
    'Escribe tu correo. La app te lleva directo a poner una nueva (no esperas correo).',
  ], en: [
    'On Log in → Forgot your password?',
    'Type your email. The app takes you straight to set a new one (no email wait).',
  ]},
  { id: 'unirse', titleEs: 'Unirte a una ronda', titleEn: 'Join a round', es: [
    'Tu organizador te comparte un link, QR o código.',
    'Toca el link o escanea el QR → entras (o te registras y quedas en la ronda).',
    'O en tu panel: Unirme con código.',
  ], en: [
    'Your organizer shares a link, QR or code.',
    'Tap the link or scan the QR → you join (or register and join).',
    'Or on your dashboard: Join with code.',
  ]},
  { id: 'tee', titleEs: 'Elegir tu tee', titleEn: 'Pick your tee', es: [
    'Antes de empezar elige el tee desde el que juegas. Con eso se calculan tus golpes de juego para ese campo.',
    'Tu handicap index (ej. 12) es portátil; tus golpes de juego pueden diferir según el campo (ej. 14). Es normal.',
  ], en: [
    'Before starting pick the tee you play from. That sets your playing strokes for the course.',
    'Your handicap index (e.g. 12) is portable; your playing strokes may differ by course (e.g. 14). Normal.',
  ]},
  { id: 'score', titleEs: 'Capturar tu score hoyo a hoyo', titleEn: 'Enter your score hole by hole', es: [
    'Verás una fila por jugador de tu grupo.',
    'Ajusta golpes con +/− y captura tus putts (solo en tu fila). Toca Guardar hoyo → Siguiente hoyo.',
    '• GPS al pin: toca GPS para ver metros/yardas al green en vivo.',
    '• Pickup / X: si recoges la bola, marca X (pone el máximo permitido).',
    '• Vista Tarjeta: ve la tarjeta tradicional del grupo.',
    '• Sin conexión: los scores se guardan en tu teléfono y se sincronizan solos al volver la señal.',
  ], en: [
    'You will see one row per player in your group.',
    'Adjust strokes with +/− and enter your putts (only on your row). Tap Save hole → Next hole.',
    '• GPS to pin: tap GPS to see live meters/yards to the green.',
    '• Pickup / X: if you pick up, mark X (sets the max allowed).',
    '• Card view: see the traditional group scorecard.',
    '• Offline: scores save on your phone and sync automatically when signal returns.',
  ]},
  { id: 'handicap', titleEs: 'Tu handicap WHS', titleEn: 'Your WHS handicap', es: [
    'Tu índice se actualiza solo al terminar cada ronda (WHS oficial).',
    '• Provisional (menos de 20 tarjetas): aún se está afinando.',
    '• Establecido (20+): promedio de tus mejores 8 diferenciales.',
    'En Perfil → Hándicap WHS → "¿Cómo se calcula mi handicap?" ves la regla, tus últimas 20 tarjetas y cuáles cuentan (✓).',
    'Si aún no tienes handicap: juega 3 rondas o ingresa tu handicap inicial en el perfil.',
  ], en: [
    'Your index updates automatically when each round finishes (official WHS).',
    '• Provisional (fewer than 20 cards): still being refined.',
    '• Established (20+): average of your best 8 differentials.',
    'In Profile → WHS Handicap → "How is my handicap calculated?" you see the rule, your last 20 cards and which count (✓).',
    'No handicap yet: play 3 rounds or enter your initial handicap in the profile.',
  ]},
  { id: 'perfil', titleEs: 'Perfil y estadísticas', titleEn: 'Profile and stats', es: [
    'En tu Perfil: tendencia de handicap, estadísticas (rondas, mejor score, GIR%, putts, birdies/eagles) e historial de rondas.',
  ], en: [
    'In your Profile: handicap trend, stats (rounds, best score, GIR%, putts, birdies/eagles) and round history.',
  ]},
  { id: 'apuestas-j', titleEs: 'Apuestas y notificaciones', titleEn: 'Bets and notifications', es: [
    'Si hay apuestas, puedes entrar o salir antes de jugar (botón en tu fila). Al final ves en balances tu resultado (solo el tuyo).',
    'Notificaciones: in-app, correo y Telegram. Conecta Telegram en Perfil → Notificaciones.',
    'CaddyAI: el asistente con IA responde dudas con tus datos reales.',
  ], en: [
    'If there are bets, you can opt in/out before playing (button on your row). At the end you see your own result in balances.',
    'Notifications: in-app, email and Telegram. Connect Telegram in Profile → Notifications.',
    'CaddyAI: the AI assistant answers questions using your real data.',
  ]},
]

const ORGANIZER: Section[] = [
  { id: 'crear', titleEs: 'Crear una ronda y elegir formato', titleEn: 'Create a round and pick a format', es: [
    'Nueva ronda → campo, fecha/hora y formato. Como creador gestionas equipos, grupos, handicaps y apuestas.',
    'Formatos: Stroke Play, Gran Premio, Stableford, Stableford Mod., Match Play, Florida.',
    'Skins ya no es formato: es una apuesta (se juega encima de cualquier formato).',
  ], en: [
    'New round → course, date/time and format. As creator you manage teams, groups, handicaps and bets.',
    'Formats: Stroke Play, Gran Premio, Stableford, Modified Stableford, Match Play, Florida.',
    'Skins is no longer a format: it is a bet (played on top of any format).',
  ]},
  { id: 'jugadores', titleEs: 'Invitar, agregar y quitar jugadores', titleEn: 'Invite, add and remove players', es: [
    'Comparte el link/QR para que se unan solos.',
    'Agregar a mano: en Jugadores → ➕ Agregar jugador → busca por nombre/usuario → Agregar. Útil si no traen internet.',
    'Quitar un no-show: toca la ✕ roja junto al jugador.',
  ], en: [
    'Share the link/QR so they join on their own.',
    'Add manually: in Players → ➕ Add player → search by name/username → Add. Useful if they have no internet.',
    'Remove a no-show: tap the red ✕ next to the player.',
  ]},
  { id: 'handicap-o', titleEs: 'Ajustar el handicap de juego', titleEn: 'Adjust the playing handicap', es: [
    'En Jugadores, junto al jugador, toca ✎ Hcp y escribe los golpes (0–54) con los que compite en esta ronda.',
    'Aplica solo a esta ronda; no toca su handicap global. Si ya hay scores, se recalculan.',
  ], en: [
    'In Players, next to the player, tap ✎ Hcp and type the strokes (0–54) they compete with this round.',
    'Applies only to this round; does not touch their global handicap. If scores exist, they recalculate.',
  ]},
  { id: 'equipos', titleEs: 'Equipos y grupos de salida', titleEn: 'Teams and tee groups', es: [
    'Rápido: elige número de equipos → Auto-armar equipos + grupos. Hace equipos parejos por handicap + grupos con un jugador de cada equipo, y publica.',
    'Manual: Generar equipos → mover → Publicar. Grupos: Asignar grupos, elige cuántos; puedes dejar grupos de distinto tamaño.',
  ], en: [
    'Quick: choose number of teams → Auto-build teams + groups. Balanced teams by handicap + groups with one player per team, then publishes.',
    'Manual: Generate teams → move → Publish. Groups: Assign groups, choose how many; different sizes allowed.',
  ]},
  { id: 'granpremio', titleEs: 'Formato Gran Premio', titleEn: 'Gran Premio format', es: [
    'Medal play por equipos: cada grupo mezcla un jugador de cada equipo y reparten puntos por posición NETA.',
    '• 1.º +2 · 2.º +1 · último −1 (siempre) · resto 0.',
    'Empates por tarjeta (countback). Gana el equipo con más puntos — aparece en la vista en vivo.',
    'Arma con Auto-armar: # de equipos = jugadores por grupo (foursomes → 4 equipos).',
  ], en: [
    'Team medal play: each group mixes one player per team and they award points by NET position.',
    '• 1st +2 · 2nd +1 · last −1 (always) · rest 0.',
    'Ties by scorecard (countback). Team with most points wins — shows in the live view.',
    'Build with Auto-build: # of teams = players per group (foursomes → 4 teams).',
  ]},
  { id: 'apuestas-o', titleEs: 'Apuestas', titleEn: 'Bets', es: [
    'Se configuran al crear/editar la ronda y se combinan.',
    '• Entrada: pot a los 3 mejores neto (60/30/10).',
    '• Nassau: 1-9, 10-18 y Total; low neto toma cada pot.',
    '• Por hoyo: low neto cobra a los demás.',
    '• Premios birdie/eagle/HIO y castigo de 3 putts: pago entre jugadores.',
    '• Skins: low score sin empate; empate hace carry-over.',
    '• Oyes: aún no calculada por el sistema.',
  ], en: [
    'Configured when creating/editing the round; can combine.',
    '• Entry: pot to top 3 net (60/30/10).',
    '• Nassau: 1-9, 10-18 and Total; low net takes each pot.',
    '• Per hole: low net collects from the rest.',
    '• Birdie/eagle/HIO prizes and 3-putt penalty: paid between players.',
    '• Skins: outright low score; ties carry over.',
    '• Oyes: not yet computed by the system.',
  ]},
  { id: 'pl', titleEs: 'Pérdidas y ganancias', titleEn: 'Profit and loss', es: [
    'En balances se calcula quién gana y quién paga sumando todas las apuestas.',
    'Como creador ves la tabla completa; cada jugador ve solo lo suyo.',
  ], en: [
    'In balances it computes who wins and who pays, summing all bets.',
    'As creator you see the full table; each player sees only their own.',
  ]},
  { id: 'live', titleEs: 'Iniciar, en vivo y finalizar', titleEn: 'Start, live and finish', es: [
    'Iniciar habilita la captura. Comparte el link público golfbookvip.com/live/CÓDIGO para que cualquiera siga el marcador.',
    'Finalizar cierra la captura, calcula resultados y actualiza handicaps. Se bloquea con conflictos o tarjetas incompletas.',
  ], en: [
    'Start enables capture. Share the public link golfbookvip.com/live/CODE so anyone follows the scoreboard.',
    'Finish closes capture, computes results and updates handicaps. Blocked with conflicts or incomplete cards.',
  ]},
]

function Accordion({ sections, locale }: { sections: Section[]; locale: string }) {
  const [open, setOpen] = useState<string | null>(null)
  return (
    <div className="space-y-2">
      {sections.map(s => {
        const isOpen = open === s.id
        const body = locale === 'es' ? s.es : s.en
        return (
          <div key={s.id} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <button onClick={() => setOpen(isOpen ? null : s.id)}
              className="w-full flex items-center justify-between px-4 py-3 text-left">
              <span className="text-sm font-semibold text-white">{locale === 'es' ? s.titleEs : s.titleEn}</span>
              {isOpen ? <ChevronUp size={16} className="text-zinc-500" /> : <ChevronDown size={16} className="text-zinc-500" />}
            </button>
            {isOpen && (
              <div className="px-4 pb-4 space-y-1.5 border-t border-zinc-800 pt-3">
                {body.map((line, i) => line.startsWith('•') ? (
                  <p key={i} className="text-sm text-zinc-400 pl-2">{line}</p>
                ) : (
                  <p key={i} className="text-sm text-zinc-400">{line}</p>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function AyudaPage() {
  const locale = useLocale()
  const lbl = (es: string, en: string) => locale === 'es' ? es : en
  const [tab, setTab] = useState<'jugador' | 'organizador'>('jugador')

  return (
    <div className="min-h-screen pb-12">
      <header className="bg-zinc-900/95 border-b border-zinc-800 backdrop-blur-md px-4 py-3 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto flex items-center gap-2">
          <Link href={`/${locale}/dashboard`} className="text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={18} />
          </Link>
          <HelpCircle size={18} className="text-emerald-400" />
          <span className="font-bold text-white text-sm">{lbl('Ayuda', 'Help')}</span>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 pt-4">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
            <Flag size={15} className="text-white" />
          </div>
          <div>
            <h1 className="font-bold text-white">GolfBook<span className="text-emerald-400">VIP</span></h1>
            <p className="text-xs text-zinc-500">{lbl('Guía de uso', 'How-to guide')}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          <button onClick={() => setTab('jugador')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold border transition-colors ${
              tab === 'jugador' ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300' : 'bg-zinc-900 border-zinc-800 text-zinc-400'
            }`}>
            <User size={15} /> {lbl('Para jugar', 'For players')}
          </button>
          <button onClick={() => setTab('organizador')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold border transition-colors ${
              tab === 'organizador' ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300' : 'bg-zinc-900 border-zinc-800 text-zinc-400'
            }`}>
            <Trophy size={15} /> {lbl('Organizar torneos', 'Run tournaments')}
          </button>
        </div>

        <Accordion sections={tab === 'jugador' ? PLAYER : ORGANIZER} locale={locale} />

        <p className="text-center text-xs text-zinc-600 mt-6">
          {lbl('¿Dudas que no resuelve esta guía? Pregúntale a CaddyAI desde cualquier pantalla.',
               "Questions this guide doesn't cover? Ask CaddyAI from any screen.")}
        </p>
      </div>
    </div>
  )
}
