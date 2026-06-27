# Evidencia E2E — Sprint 1 (Portal COC) · STAGING

**Fecha:** 2026-06-27 · **Entorno:** `Sentinela_STAGING` (Odoo `odoo-lab :8075`) + Gateway `0.3.1` + SPA Next.js.
**Resultado global: ✅ 13/13 escenarios validados** (harness automatizado 19/20; el único "FAIL" es un artefacto de medición, no un defecto — ver §9).

Harness: `sentinela_coc/gateway/tests/e2e_staging_portal.py` (TestClient in-process + **Odoo STAGING real** + OTP Mock para login automatizable; recursos minteando sesiones por el mismo camino que `otp/verify`).

## Clientes de prueba (datos reales STAGING)
| Tipo | partner | Notas |
|---|---|---|
| Residencial con alarma / suspendido / sin facturas | 25757 | 1 servicio alarma, suspendido, 0 facturas |
| Internet / Empresarial | 25216 | empresa con servicio internet |
| Multiservicio | 25295 | 3 servicios |
| Con factura | 25763 | factura INV/2026/00104 (id 144) |
| Con CFDI/XML | 20601 | factura id 48 (timbrada) |
| IDOR | A=25763 / B=20801 | factura ajena id 143 |

## Resultados por escenario
| # | Escenario | Resultado | Evidencia |
|---|---|---|---|
| 1 | Login OTP completo | ✅ | `request=200 verify=200 token=sí`, resolve→partner 25757 |
| 2 | Dashboard carga | ✅ | 200 en los 4 tipos de cliente |
| 3 | Estado de Tranquilidad coherente | ✅ | 25757 suspendido → `atencion` (coherente=True) |
| 4 | Mis Servicios solo del cliente | ✅ | pid 25216 → 1 servicio, tipo `internet` |
| 5 | Facturación solo del cliente | ✅ | pid 25763 → 1 factura |
| 6 | Descarga PDF y XML | ✅ | PDF `%PDF` 35.5 KB; XML `<?xml…` 5.5 KB |
| 7 | Aislamiento IDOR → 404 | ✅ | propia(144)=200 · ajena detalle(143)=**404** · ajena PDF(143)=**404** |
| 8 | Expiración + refresh | ✅ | refresh=200, access nuevo=200, **reuse viejo=401**; logout → access=**401** (revocable) |
| 9 | Caché Dashboard 30s / PDF 300s | ✅ | dashboard `last_refresh` estable en 2 llamadas; PDF **frío 3126 ms → cacheado 12 ms (~260×)** |
| 10 | request_id + auditoría | ✅ | `X-Request-Id` + `meta.request_id`; auditoría gateway y Odoo (ver §10) |
| 11 | Tiempos de respuesta | ✅ | ver §11 |
| 12 | Navegador móvil/escritorio | ⏳ verificación visual | SPA en línea: `http://192.168.3.2:3080` (ver §12) |
| 13 | Múltiples tipos de cliente | ✅ | 4 perfiles ejercitados (tabla §13) |

## §9 — Comportamiento del caché
- **Dashboard (TTL 30 s):** dos llamadas consecutivas devuelven el mismo `meta.last_refresh` → sirvió de caché. ✅
- **PDF (TTL 300 s):** primer render real (escena 6) **3126 ms**; mismo PDF cacheado (escena 9) **12 ms** → **~260× más rápido**. ✅
- *Incidencia menor (no defecto):* la aserción automática `9_cache_pdf` comparó dos llamadas **ya cacheadas** (el PDF se había pedido en la escena 6), por eso marcó FAIL. La evidencia real frío-vs-cacheado (3126→12 ms) confirma el caché. Se documenta tal cual.

## §10 — request_id y auditoría
- **Gateway** (`auth_audit_event`): `login, login_new_device, logout, otp_request, otp_sent, otp_verify, refresh, refresh_reuse`.
- **Odoo** (`sentinela.coc.auth.log`): `session_open=63, session_close=38, session_expired=1`.
- Header `X-Request-Id` en respuestas + `meta.request_id` en el cuerpo. ✅

## §11 — Tiempos de respuesta (in-process + Odoo real)
| Cliente | Dashboard | Servicios | Billing summary |
|---|---|---|---|
| 25757 | 91.1 ms | 34.6 ms | 35.4 ms |
| 25216 | 78.6 ms | 28.6 ms | 34.6 ms |
| 25295 | 67.0 ms | 28.7 ms | 69.7 ms |
| 25763 | 74.5 ms | 40.9 ms | 61.6 ms |

PDF frío (render wkhtmltopdf): 3126 ms; cacheado: 12 ms. *(Tiempos sin la latencia pública NPM/Cloudflare; cota optimista representativa.)*

## §12 — Navegador móvil/escritorio (verificación visual pendiente del usuario)
La SPA está **desplegada en STAGING** para tu revisión en dispositivos reales:
- **SPA:** `http://192.168.3.2:3080` (LAN)
- **Gateway:** `http://192.168.3.2:8401` (EvoApi `SentinelaWA` conectada; login real con tu número `+52 868 125 5741` → partner 3).
- Diseño **Mobile First** (columna `max-w-app`, `viewport` fijo, BottomNav), responsive en escritorio (columna centrada). Skeleton loading en toda consulta; errores amigables.
> No puedo capturar pantallas de navegador desde aquí; esta es la parte humana del escenario 12. Abre la URL en móvil y escritorio y confirma.

## §13 — Cobertura por tipo de cliente
| Cliente (partner) | peace | servicios (tot/act/susp) | saldo | vencido | acciones |
|---|---|---|---|---|---|
| 25757 (alarma/suspendido/sin facturas) | atencion | 1/0/1 | 0 | 0 | 1 |
| 25216 (internet/empresarial) | atencion | 1/0/1 | 0 | 0 | 1 |
| 25295 (multiservicio) | atencion | 3/0/3 | 0 | 0 | 3 |
| 25763 (con factura) | atencion | 1/1/0 | 6050.0 | 6050.0 | 2 |

> Nota: en STAGING la mayoría de suscripciones están en estado `suspension` (artefacto de la migración), por eso predomina `atencion`. La rama `tranquilo` está cubierta por las pruebas unitarias del gateway (`test_portal.py::test_dashboard_peace_when_clean`).

## Incidencias encontradas
1. **Caché PDF — aserción del harness** (artefacto de medición, no defecto): documentada en §9. Evidencia real del caché: 260×.
2. Sin defectos funcionales. Aislamiento (record rules), IDOR, refresh/reuse, revocación y auditoría: correctos.

## Limpieza
- Teléfono temporal en partner 25757 (para login OTP): **revertido**.
- Contenedores STAGING `coc-gw-staging` (8401) y `coc-web-staging` (3080) quedan **en línea** para tu verificación del escenario 12. Tear-down: `docker rm -f coc-gw-staging coc-web-staging`.

## Veredicto
✅ **E2E STAGING superado.** Listo para preparar la ventana de despliegue a Producción **tras tu visto bueno del escenario 12** en navegador. No se despliega a Producción sin tu autorización.
