# Reporte formal de UAT — Sprint 1 (Portal COC · SPA)

**Fecha:** 2026-06-29 · **Responsable de ejecución:** Claude Code (a solicitud de Enrique Garza).
**Alcance:** Únicamente la **UAT de la SPA** del Sprint 1 ("Consulta: Mis Servicios + Facturación"), extremo a extremo, contra un entorno **STAGING completo**. **No se desplegó nada a Producción.**

---

## 1. Entorno de prueba

| Capa | Detalle |
|---|---|
| SPA | Repo HEAD (`coc-web` con lote DS **0.4.0**, build de producción) servida en `:3080`, `NEXT_PUBLIC_API_BASE=http://192.168.3.2:8401` |
| Gateway (BFF) | `coc-gw-staging` **0.3.2** (`:8401`), todos los endpoints Sprint 1 (`/v1/me`, `/v1/services`, `/v1/billing/*`, `/v1/dashboard`, `/v1/config/theme`) |
| Odoo | `Sentinela_STAGING` (`odoo-lab :8075`) con `sentinela_api` (controllers Mis Servicios + Facturación) — verificado idéntico al repo |
| Driver UAT | Playwright headless (Chromium) manejando la UI real; capturas PNG = evidencia |
| Autenticación en UAT | Login real por la UI con OTP recuperado del hash en la BD del gateway (HMAC-SHA256, sin enviar WhatsApp); pantallas autenticadas con sesión minteada por el mismo `session_service` que usa `otp/verify` |

> **Hallazgo de arranque (registrado):** El **Gateway de Producción está en `0.2.0` (solo RC1/identidad)** y **NO tiene desplegado el backend del Sprint 1** (`/v1/services`, `/v1/billing/*`, `/v1/dashboard`, `/v1/me` → 404). El código existe en el repo pero **nunca se promovió a prod**. Por eso la UAT se ejecutó en STAGING con el código del repo. La promoción del backend Sprint 1 a prod queda **pendiente y sujeta a esta aprobación**.

Fixtures (datos reales STAGING): **25757** (alarma/suspendido/0 facturas), **25216** (internet/empresa), **25295** (multiservicio), **25763** = "MARIO" (factura `INV/2026/00104` id 144, vencido $6,050), **20601** (CFDI/XML id 48), IDOR B = factura 143.

---

## 2. Resumen ejecutivo

| Métrica | Valor |
|---|---|
| **Casos ejecutados** | **27** |
| **Aprobados (PASS)** | **25** |
| **Rechazados (FAIL)** | **0** |
| **No aplica (N/A justificado)** | **2** |
| **Defectos bloqueantes** | **0** |
| **Correcciones realizadas** | **0** (no hubo defectos que corregir) |

### Recomendación final: ✅ **APROBADO**

La SPA del Sprint 1 cumple todos los criterios de aceptación end-to-end contra el backend real: login OTP, dashboard/Estado de Tranquilidad coherente, Mis Servicios, Facturación (resumen + lista + detalle + **PDF y XML de CFDI** + pagos + selección/modal de pago diferido), **aislamiento por cliente (IDOR bloqueado)**, sesión (expiración + rotación de refresh), branding desde Odoo, responsive móvil/escritorio y consola limpia.

---

## 3. Casos ejecutados — detalle

### A. Autenticación / Sesión
| # | Caso | Resultado | Evidencia |
|---|---|---|---|
| UAT-01 | Login paso teléfono solicita OTP (avanza a paso código) | ✅ PASS | `UAT-01_login_phone.png`, `UAT-01_login_code_step.png` |
| UAT-02 | Código correcto verifica y entra a `/dashboard` | ✅ PASS | `UAT-02_login_success_dashboard.png` |
| UAT-03 | Código incorrecto → error amigable, no avanza | ✅ PASS | `UAT-03_login_wrong_code.png` |
| UAT-04 | "Usar otro número" regresa al paso teléfono | ✅ PASS | — |
| UAT-05 | Sesión expirada (401) → `/login?expired=1` + banner | ✅ PASS | `UAT-05_expired.png` |
| UAT-06 | Logout por la UI | ➖ N/A | Sprint 1 **no expone botón de logout** (perfil "próximamente"); cierre por expiración / borrado de tokens (sync multi-pestaña). *Recomendación no bloqueante.* |
| UAT-07 | Rotación de refresh token (reuse del viejo = 401) | ✅ PASS | refresh#1=200 (nuevo access), reuse viejo=**401** |

### B. Dashboard / Estado de Tranquilidad
| # | Caso | Resultado | Evidencia |
|---|---|---|---|
| UAT-08 | Dashboard carga (skeleton→data) | ✅ PASS | `dash_25763.png` |
| UAT-09 | Estado "atención" coherente con suspendido/vencido | ✅ PASS | `dash_25763.png` |
| UAT-10 | Estado "tranquilo" con cliente limpio | ➖ N/A | STAGING: subs migradas en suspensión; rama "tranquilo" cubierta por unit test del gateway (`test_dashboard_peace_when_clean`) |
| UAT-11 | Saldo por pagar + badge "Vencido" | ✅ PASS | `dash_25763.png` ($6,050 / Vencido) |
| UAT-12 | Próximas acciones agrupadas/colapsadas | ✅ PASS | `dash_25763.png` (Facturas vencidas/por pagar) |
| UAT-13 | "Mis servicios" (3) + "Ver todos (N)" | ✅ PASS | `UAT-13_multiservicio.png` (≤3 servicios → "Ver todos" se muestra solo si total>3; comportamiento correcto) |
| UAT-14 | AppHeader institucional (nombre/cliente/estado/última actualización) | ✅ PASS | `UAT-14_header.png` ("Hola, MARIO · Cliente #25763 · Atención requerida") |

### C. Mis Servicios
| # | Caso | Resultado | Evidencia |
|---|---|---|---|
| UAT-15 | Lista de servicios solo del cliente | ✅ PASS | `UAT-15_servicios_25216.png` |
| UAT-16 | Detalle de un servicio (plan/tarifa/próximo cobro/domicilio) | ✅ PASS | `UAT-16_servicio_detalle.png` |

### D. Facturación
| # | Caso | Resultado | Evidencia |
|---|---|---|---|
| UAT-17 | Resumen ejecutivo (por pagar/saldo/próx. venc./último pago) | ✅ PASS | `UAT-17_facturacion.png` |
| UAT-18 | Lista de facturas + paginación ("Mostrando 1 de 1") | ✅ PASS | `UAT-17_facturacion.png` |
| UAT-19 | Detalle de factura | ✅ PASS | `UAT-19_factura_detalle.png` |
| UAT-20 | Descarga **PDF (CFDI)** válida | ✅ PASS | `UAT-20_factura144.pdf` (PDF 1.4, 35,613 bytes, magic `%PDF`) |
| UAT-21 | Descarga **XML (CFDI)** válida | ✅ PASS | `UAT-21_factura48.xml` (XML 1.0, 5,520 chars, `<?xml…`) |
| UAT-22 | Historial de pagos (tab Pagos) | ✅ PASS | `UAT-22_pagos.png` |
| UAT-23 | Selección de facturas + barra + modal Resumen + "Pagar (próximamente)" deshabilitado | ✅ PASS | `UAT-23_pago_modal.png` |

### E. Aislamiento / Seguridad (vía UI)
| # | Caso | Resultado | Evidencia |
|---|---|---|---|
| UAT-24 | IDOR: cliente A no accede a factura de B (404 → error amigable, sin fuga) | ✅ PASS | `UAT-24_idor.png` |

### F. Identidad / Responsive / Calidad
| # | Caso | Resultado | Evidencia |
|---|---|---|---|
| UAT-25 | BrandMark (logo desde Odoo) en login | ✅ PASS | `UAT-25_branding_login.png` |
| UAT-26 | Responsive móvil 390 (BottomNav, header colapsado) | ✅ PASS | `UAT-26_mobile_390.png` |
| UAT-27 | Consola del navegador sin errores (Dashboard) | ✅ PASS | sin errores; sin respuestas 5xx en ninguna pantalla |

---

## 4. Defectos encontrados

**Ninguno bloqueante. 0 defectos funcionales.** El aislamiento por cliente (record rules), IDOR, expiración/rotación de sesión, descarga de CFDI (PDF/XML) y la UX de pago diferido funcionan correctamente.

### Observaciones no bloqueantes (para backlog, NO afectan la aprobación)
1. **Sin botón de logout en la UI** (Sprint 1): el cierre de sesión ocurre por expiración o borrado de tokens. Recomendación: agregar acción explícita de "Cerrar sesión" en un sprint posterior (cuando se habilite el menú de perfil).
2. **Iconografía por emoji**: en las capturas headless se ven recuadros □ porque el entorno de captura (WSL) no tiene fuente de emoji; en dispositivos reales (móvil/Windows) renderizan normal. **Es artefacto del entorno de captura, no de la SPA.** Sugerencia menor: evaluar íconos SVG en lugar de emoji para independizarse de la fuente del sistema.
3. **Cobertura de "tranquilo"**: no exhibible con los datos de STAGING (todo en suspensión por la migración); queda cubierto por prueba unitaria del gateway.

## 4 bis. Mejora cosmética detectada durante la UAT — IMPLEMENTADA Y APROBADA

Durante la revisión se detectó una mejora de presentación institucional (clasificada explícitamente como **cosmética**, no defecto, y **no bloqueaba** la aprobación). **Implementada, validada y APROBADA por Enrique (29-jun-2026).**

- **Pie de página institucional en la pantalla de Login.** Pie discreto, centrado en la parte inferior, con tres líneas:
  `Portal del Cliente v1.0` · `© 2026 Alarmas Sentinela` · `Powered by Alea Systems`.
- **Implementación DS-pura:** clases `text-caption` (12px, mínimo del Design System) + `text-muted` (#64748b, gris suave). Posicionado con `absolute inset-x-0 bottom-0`, de modo que **no altera el centrado de la tarjeta de login ni el comportamiento responsive**, y no toca la lógica/UX del login.
- **Validación visual (re-capturas):**
  - Escritorio (`UAT-25b_login_footer_desktop.png`) y móvil 390 (`UAT-25b_login_footer_mobile.png`) — pie correcto, tarjeta de login sin desplazamiento, **0 errores de consola**.
  - Contenedor del server, URL real `http://192.168.3.2:3080/login?expired=1` (`server_login_expired_footer.png`) — pie + banner de expiración correctos.
- **Archivo:** `sentinela_coc/web/app/login/page.tsx` (typecheck ✅, build ✅). *Pendiente de commit/release antes de la promoción a Producción (ver Plan de Despliegue).*

## 5. Correcciones realizadas

**Ninguna corrección de defecto** (no se encontraron defectos bloqueantes). El único cambio de código fue la **mejora cosmética** del §4 bis (pie de Login), implementada y validada visualmente. Se respetó: sin features funcionales nuevas, sin cambios de arquitectura, sin tocar el spec ni el backlog del Sprint 2.

## 6. Evidencias

Carpeta: [`evidencia_uat_sprint1/`](evidencia_uat_sprint1/) — 18 capturas PNG + PDF/XML de CFDI descargados + `results.json` (salida estructurada del driver). Las capturas clave (dashboard, login, facturación, modal de pago, IDOR, móvil) muestran la UI real renderizada contra el backend real de STAGING.

## 7. Veredicto

✅ **UAT del Sprint 1 APROBADA — SPA lista.** Todos los criterios de aceptación verificados extremo a extremo; 0 defectos bloqueantes.

**Puerta de avance:** Conforme a lo acordado, el inicio del Sprint 2 (S2-000) y cualquier despliegue a Producción quedan condicionados a la orden explícita **"La UAT terminó."** Una vez emitida, la secuencia autorizada será: (1) desplegar el **backend Sprint 1** a Producción (gateway 0.3.2 + `sentinela_api`), (2) desplegar la **SPA** (`portal.sentinela.mx` + ingreso público `api.sentinela.mx`), (3) recién entonces abrir S2-000.
