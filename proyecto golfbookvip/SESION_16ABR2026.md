# GolfBookVIP — Sesión 16 Abr 2026
## Resumen de cambios implementados

---

## 1. FORMATO FLORIDA

### Backend
- `app/schemas/round.py` → `RoundOut` incluye `team_size: int = 1`
- `app/schemas/round.py` → `RoundUpdate` incluye `team_size: Optional[int]`
- El campo `team_size` ya existía en `Round` model y `RoundCreate`

### Frontend — `rounds/new/page.tsx`
- Agregado `florida` al array `FORMATS`
- `form.team_size: 2` en estado inicial
- UI: al seleccionar Florida aparece selector 2/3/4 jugadores por equipo
- Se envía `team_size` al API solo si `game_format === 'florida'`
- `FORMAT_SHORT['florida']` con descripción y ejemplo

### Frontend — `rounds/[id]/page.tsx`
- `Round` interface: campo `team_size: number`
- `FORMAT_LABELS` incluye `florida` y `skins`
- `FORMATS` array incluye `florida`
- `FORMAT_INFO['florida']` con reglas y ejemplo de cálculo
- Chip "2 jug/equipo" azul visible cuando `game_format === 'florida'`
- Edit form: selector de team_size cuando formato es florida
- `editForm` y `saveEdit()` envían `team_size`

---

## 2. IMAGEN DE FONDO

### `frontend/src/app/globals.css`
```css
body {
  background-color: #09090b;
  background-image:
    linear-gradient(overlay 55%/40%/55%),
    url('/golf-bg.jpg');
  background-attachment: fixed;
}
.min-h-screen.bg-zinc-950 { background-color: transparent !important; }
header.bg-zinc-900 { backdrop-filter: blur(8px); }
.bg-zinc-900.border.border-zinc-800.rounded-2xl { backdrop-filter: blur(6px); }
```

### `frontend/public/golf-bg.jpg`
- Descargada en el servidor con `curl` desde Unsplash (351KB, foto aérea de campo)
- Path: `/opt/golfbookvip/frontend/public/golf-bg.jpg`

### `frontend/src/app/[locale]/layout.tsx`
- Removido `bg-zinc-950` del body (el fondo lo maneja globals.css)

---

## 3. MODAL DE INFORMACIÓN DE FORMATOS

### `rounds/[id]/page.tsx` y `rounds/new/page.tsx`
- Componente `FormatInfoModal` con descripción, tabla de puntos y ejemplo práctico
- Icono `ⓘ` junto al chip del formato actual → abre modal del formato activo
- En formulario de edición: link "¿Cómo funciona cada formato?" → modal del formato seleccionado
- Cubre los 6 formatos: stroke, stableford, stableford_modified, match, skins, florida

---

## 4. PERMISOS — SOLO EL CREADOR PUEDE MODIFICAR

### Frontend — `rounds/[id]/page.tsx`
| Elemento | Antes | Después |
|----------|-------|---------|
| Botón "Iniciar ronda" | Todos | Solo `amCreator` |
| Botón "Copiar enlace" / QR | Todos | Solo `amCreator` |
| Inputs de apuestas | Todos (habilitados) | Solo `amCreator` (disabled para invitados) |
| Botón "Guardar apuestas" | Todos | Solo `amCreator` |
| Sección apuestas visible | Siempre | `amCreator` OR `betCfg != null` |
| Mensaje explicativo | — | Invitados ven "Solo el organizador puede modificar" |
| Editar ronda | Solo `amCreator` ✓ | Sin cambio |
| Eliminar ronda | Solo `amCreator` ✓ | Sin cambio |

### Backend (ya estaba protegido)
- `POST /{round_id}/start` → verifica `Round.created_by == current_user.id`
- `PATCH /{round_id}` → verifica `created_by + status == scheduled`
- `DELETE /{round_id}` → verifica `created_by + status == scheduled`
- `POST /{round_id}/bet-config` → verifica `created_by`

---

## 5. FLUJO DE INVITACIÓN — REGISTRO CON HÁNDICAP

### Problema encontrado
- `POST /auth/register` retornaba 422 (error visible en logs API)
- Redirect post-registro usaba `infoRes.data.id` (de un segundo GET) en vez del `round_id` directo del POST join → causaba `/rounds/undefined`

### Fix — `auth/register/page.tsx`
- **Campo nuevo:** "Hándicap índice" (0.0–54.0, step 0.1) con tooltip explicativo
- Se envía `initial_handicap` al backend (el schema ya lo aceptaba)
- Post-registro: usa `joinRes.data.round_id` directamente del POST `/rounds/join/{code}`
- Errores de join visibles en pantalla en vez de silenciados

### Fix — `auth/login/page.tsx`
- Mismo fix: usa `joinRes.data.round_id` en vez de hacer un GET adicional

### Backend — `app/schemas/auth.py` (sin cambios)
- `RegisterRequest.initial_handicap: float | None = None` ya existía
- `app/api/v1/auth.py` ya guardaba `initial_handicap` y `handicap_index`

---

## 6. ENDPOINT DELETE ROUND (nuevo)

### `app/api/v1/rounds.py`
```python
@router.delete("/{round_id}", status_code=204)
async def delete_round(round_id, current_user, db):
    # Solo creador + status == scheduled
    # Borra: RoundPlayer, RoundBetConfig, RoundPlayerBalance, Round
```

### `rounds/[id]/page.tsx`
- Botón "Eliminar" (rojo) junto a "Editar" — visible solo para creador en ronda scheduled
- Modal de confirmación con descripción del impacto
- Estados: `confirmDelete`, `deleting`
- Post-delete: redirect a `/rounds`

---

## BUGS CORREGIDOS

| Bug | Causa | Fix |
|-----|-------|-----|
| `/es/rounds` en blanco | rsync anterior sobreescribió `rounds/page.tsx` con contenido de `[id]/page.tsx` | Re-rsync del archivo correcto |
| Skines no visible en crear ronda | rsync usaba timestamps, el servidor tenía archivo más nuevo con versión vieja | Usar `--checksum` en rsync |
| `/rounds/undefined` en logs | join redirect usaba `infoRes.data.id` de un segundo GET que podía fallar | Usar `round_id` del POST response directamente |
| Build Docker falla con UTF-8 | `favicon.ico` binario causa error en BuildKit gRPC | Usar `DOCKER_BUILDKIT=0` |
| `app/layout.tsx` sobreescrito | rsync de múltiples archivos a directorio puso `[locale]/layout.tsx` en raíz | Restaurar manualmente + rsync con path explícito |

---

## ARCHIVOS MODIFICADOS EN ESTA SESIÓN

```
app/
├── api/v1/rounds.py          → DELETE endpoint, permisos start protegidos
└── schemas/round.py          → RoundOut.team_size, RoundUpdate.team_size

frontend/src/app/
├── globals.css               → Fondo golf + glassmorphism
├── [locale]/layout.tsx       → Sin bg-zinc-950 en body
└── [locale]/
    ├── auth/register/page.tsx → Campo handicap + fix redirect invite
    ├── auth/login/page.tsx    → Fix redirect invite
    ├── rounds/new/page.tsx    → Florida + FormatInfoModal
    └── rounds/[id]/page.tsx   → Florida + DELETE + permisos + FormatInfoModal

frontend/public/golf-bg.jpg   → Foto campo de golf (solo en servidor)
```

---

## ESTADO DE CONTENEDORES AL CIERRE

```
golfbookvip_api       Up, healthy
golfbookvip_frontend  Up (Next.js 16.2.3, Ready)
golfbookvip_db        Up, healthy (postgres:16)
golfbookvip_redis     Up
```

---

## LO QUE FALTA (PRIORIZADO)

### 🔴 Alta prioridad (siguiente sesión)
1. **Scoring Florida** — lógica de mejor net score por equipo en `scoring.py`
2. **Asignación de equipos** — UI para que el creador asigne jugadores a equipos
3. **Finalizar ronda** — botón + endpoint para cerrar y calcular resultado final
4. **Cálculo HCP post-ronda** — score differential + actualizar handicap_index del usuario
5. **Notificación cuando un jugador se une** — broadcast WS o polling

### 🟡 Media prioridad
6. **Feed social** — timeline de actividad con amigos/grupo
7. **Sistema de amigos** — buscar usuarios, seguir, grupos
8. **Modo espectador** — ver scoring sin estar en la ronda
9. **Estadísticas avanzadas** — fairways, GIR, putts, tendencia HCP

### 🟢 Baja prioridad / polish
10. **Email SMTP** — confirmación de registro, invitaciones
11. **Notificaciones in-app** — bell icon
12. **Admin de canchas** — desde la app
13. **Stripe LIVE** — pagos reales de entry fees
14. **PWA** — instalable en móvil
