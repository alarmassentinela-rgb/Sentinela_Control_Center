# FASE 2B — JWT httpOnly (refresh) + access en memoria + silent-refresh + WS sin token en URL

> Contrato para Codex. Cierra el último crítico de seguridad de la auditoría (C1/C2/C3/C4 del frontend).
> Cross-cutting FE+BE. El Arquitecto verifica: backend con curl+cliente WS real; frontend con build+review.
> NO tocar dinero ni migraciones de esquema. NO tocar producción.

## Estrategia (respétala — es de bajo riesgo y sin CSRF)
- **Refresh token → cookie httpOnly, Secure, SameSite=Lax** (credencial larga, inalcanzable por JS/XSS).
- **Access token → en MEMORIA del cliente (variable JS), enviado como `Authorization: Bearer`** (corto).
  Por eso `get_current_user` (Bearer header) NO cambia y NO hay superficie CSRF (la API se autentica por header).
- **Silent-refresh**: al cargar la app y ante un 401, el cliente llama `POST /auth/refresh` (con la cookie)
  para obtener un nuevo access token en memoria.
- **WebSocket**: autenticación por PRIMER MENSAJE tras `onopen`, nunca en la query string.
- Hoy el frontend guarda `access_token` en localStorage (riesgo XSS) y NO tiene refresh flow. Lo eliminamos.

## BACKEND

### 1. Config (`app/core/config.py`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: cambia el default de 1440 a **30**.
- Agrega: `REFRESH_COOKIE_NAME: str = "gbv_refresh"`, `COOKIE_SECURE: bool = True`,
  `COOKIE_DOMAIN: str = ""` (vacío = host-only; en prod se setea `.golfbookvip.com` por env),
  `COOKIE_SAMESITE: str = "lax"`.

### 2. `app/api/v1/auth.py`
Helper local `_set_refresh_cookie(response, token)` y `_clear_refresh_cookie(response)` usando
`response.set_cookie(key=settings.REFRESH_COOKIE_NAME, value=token, httponly=True,
secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE, domain=(settings.COOKIE_DOMAIN or None),
path="/api/v1/auth", max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS*86400)`.
- `login` y `register`: agrega `response: Response` param; tras generar tokens, **setea la cookie de refresh**
  y devuelve el access token en el body como hoy. Deja `refresh_token` en el body por compat (el frontend
  dejará de usarlo), pero la fuente de verdad del refresh es la cookie.
- `refresh_token` endpoint: lee el refresh token de la **cookie** (`request.cookies.get(REFRESH_COOKIE_NAME)`),
  con fallback al body `data.refresh_token` por compat. Valida `type==refresh`, ROTA (nuevo access + nuevo
  refresh), setea la nueva cookie y devuelve el nuevo access en el body. Agrega `request: Request` y
  `response: Response`. Si no hay refresh ni en cookie ni en body → 401.
- Nuevo endpoint `POST /auth/logout`: limpia la cookie de refresh y responde `{"message":"ok"}`.
- Mantén el rate-limit de Fase 2A.
- NO cambies `get_current_user` (`deps.py`) — sigue siendo Bearer header.

### 3. WebSocket (`app/api/v1/scores_ws.py`)
- Quita `token: str = Query(...)`. Tras `await ws.accept()` (llámalo explícito), espera el PRIMER mensaje
  con timeout corto (p.ej. 10s vía `asyncio.wait_for(ws.receive_text(), 10)`); parsea JSON y toma
  `{"action":"auth","token":"<access>"}`. Autentica con `_authenticate(token)`. Si falta/invalid/timeout →
  `await ws.close(code=4001)` y return. El resto del flujo (rol, espectador, loop) queda igual.
  Nota: `manager.connect` hace el `accept`; muévelo o haz el `accept` manual antes de recibir el auth y ajusta
  `manager.connect` para no re-aceptar (revisa `ws_manager.py`).
- Actualiza el docstring (ya no hay `?token=`).

## FRONTEND

### 4. `src/lib/api.ts` (choke point)
- `axios.create({..., withCredentials: true})` para que la cookie de refresh viaje a `/auth/refresh`.
- Access token EN MEMORIA: `let accessToken: string | null = null`. Exporta:
  - `setAuth(token: string)`: `accessToken = token; localStorage.setItem('gbv_authed','1')` (flag NO sensible).
  - `clearAuth()`: `accessToken = null; localStorage.removeItem('gbv_authed')`.
  - `isAuthed(): boolean`: `typeof window!=='undefined' && !!localStorage.getItem('gbv_authed')`.
  - `getAccessToken()`, y `refreshAccessToken(): Promise<boolean>` que hace `POST /auth/refresh` (withCredentials),
    si 200 → `setAuth(res.data.access_token); return true`, si no → `clearAuth(); return false`.
- Request interceptor: usa `accessToken` (memoria), no localStorage.
- Response interceptor 401: intenta `refreshAccessToken()` UNA vez; si true, reintenta la request original;
  si false, `clearAuth()` + redirige a `/{locale}/auth/login`. (Evita loop en el propio `/auth/refresh`.)
- Elimina toda lectura/escritura de `localStorage 'access_token'`.

### 5. Bootstrap de sesión
- Crea `src/components/AuthBootstrap.tsx` (client component) que en `useEffect` al montar llama
  `refreshAccessToken()` una vez (repuebla el access token en memoria desde la cookie tras un reload).
  Móntalo en `src/app/[locale]/layout.tsx` dentro de los providers.

### 6. login / register / logout
- `auth/login/page.tsx` y `auth/register/page.tsx`: reemplaza `localStorage.setItem('access_token', ...)`
  por `setAuth(res.data.access_token)` (import desde `@/lib/api`).
- `dashboard/page.tsx` `logout()`: llama `await api.post('/auth/logout').catch(()=>{})`, luego `clearAuth()` y
  redirige. Reemplaza el `localStorage.removeItem('access_token')`.

### 7. Guards de ruta dispersos
- Reemplaza TODAS las ocurrencias de `if (!localStorage.getItem('access_token')) { router.push(... login) }`
  por `if (!isAuthed()) { router.push(... login) }` (import `isAuthed` de `@/lib/api`). Son ~15 archivos
  (admin/*, club/[id]/*, etc.). Búscalas con grep y cámbialas todas.

### 8. WebSocket (frontend)
- `rounds/[id]/play/page.tsx` y `rounds/[id]/spectate/page.tsx`: quita `?token=${token}` de la URL del
  `new WebSocket(...)`. En el handler `onopen`, envía `ws.send(JSON.stringify({action:'auth', token:
  getAccessToken()}))`. Usa el access token en memoria.

### 9. Middleware (`src/middleware.ts`)
- Además del redirect de locale, para rutas protegidas (todo salvo `/{locale}` raíz, `/auth/*`, `/join*`,
  `/live/*`, assets), si NO existe la cookie `gbv_refresh` en `request.cookies`, redirige a
  `/{locale}/auth/login`. Mantén el comportamiento de locale. Sé conservador: ante duda, no bloquees
  (la protección real es del backend). Documenta qué prefijos consideraste protegidos.

## Verificación que el Arquitecto correrá (no la simules)
- Backend: login setea Set-Cookie httpOnly; Bearer access → 200; `/auth/refresh` con cookie rota y responde
  nuevo access; `/auth/logout` limpia; WS con primer mensaje de auth → `connected`, WS sin auth → cerrado.
- Frontend: `next build` (typecheck/lint) verde + revisión de diff.

## Reglas
- Archivos backend: `config.py`, `auth.py`, `scores_ws.py`, `ws_manager.py` (si hace falta ajustar accept).
  Frontend: `lib/api.ts`, `middleware.ts`, `components/AuthBootstrap.tsx`, `layout.tsx`, login/register/dashboard,
  los ~15 guards, y los 2 archivos de WS. Nada de dinero, modelos ni migraciones.
- Entrega: diffs resumidos por archivo, lista de guards reemplazados, y prefijos protegidos del middleware.
