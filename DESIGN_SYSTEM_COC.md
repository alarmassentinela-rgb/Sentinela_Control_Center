# DESIGN_SYSTEM_COC — Inventario oficial (base para próximos sprints)

Componentes y tokens **oficiales** del Portal COC tras el lote DS del Sprint 1 (web 0.4.0).
**Regla:** no crear componentes/estilos paralelos. Si algo existe aquí, se reutiliza.
Los componentes del DS **no conocen el dominio** (solo reciben props).

## Tokens (`tailwind.config.ts` + `globals.css`) — ÚNICA fuente de verdad
| Categoría | Tokens |
|---|---|
| Color | `brand`, `brand-dark`, `ink`, `muted`, `surface`, `ok`, `warn`, `danger` |
| Tipografía (fontSize) | `hero`(30) · `title`(20) · `subtitle`(18) · `body`(16) · `aux`(14) · `caption`(12, **mínimo**) |
| Radios | `rounded-pill` · `rounded-control` · `rounded-card` |
| Sombras | `shadow-card` · `shadow-overlay` |
| Elevación (z) | `z-nav`(10) · `z-header`(20) · `z-overlay`(30) · `z-modal`(40) |
| Transición | `duration-base`(150ms) |
| Foco | `.focus-ring` (focus-visible homogéneo) |

> Prohibido hardcodear color/radio/sombra/spacing/tamaño si existe token. Ningún texto < 12px.

## Componentes UI (`components/ui/`)
| Componente | Props | Rol |
|---|---|---|
| `Button` | variant(primary/secondary/ghost) + HTML button | Botón único (foco + estados) |
| `Card` | className, children, onClick? | Contenedor; con onClick = accesible por teclado |
| `Badge` | tone(ok/warn/danger/neutral/info), children | **Único** chip de estado |
| `StatusPill` | status | Wrapper de Badge (status de servicio → tono) |
| `StatusIndicator` | tone, size(sm/md/lg/xl), halo?, className | Semáforo SVG (Estado de Tranquilidad, etc.) |
| `Dialog` | open, onClose, title, children | **Único** modal (Escape, focus-trap, aria) |
| `FieldLabel` | htmlFor, children | **Única** label de formulario (a11y) |
| `LoadMore` | shown, total, loading, onMore | Paginación "cargar más" (solo presentacional) |
| `EmptyState` | icon?, title, hint? | Estado vacío |
| `ErrorState` | message, onRetry? | Estado de error + reintento |
| `Skeleton` / `SkeletonCard` | className | Carga |
| `PageHeader` | title, subtitle?, actions? | Encabezado de pantalla (no en Dashboard) |
| `icons` | `BellIcon`, `SparklesIcon` | Iconografía SVG del chrome |

## Componentes de aplicación (`components/`)
`BrandMark` (identidad, única fuente = Odoo) · `AppHeader` · `BottomNav` · `PeaceOfMind` (hero) ·
`NextActions` · `ServiceCard` · `InvoiceRow` · `PaymentRow` · `ModulesGrid` · `SelectionBar` ·
`PaymentSummaryModal` (sobre `Dialog`).

## Hooks (`hooks/`)
| Hook | Firma | Rol |
|---|---|---|
| `useQuery` | `(fn, deps) → {data, loading, error, reload}` | Consulta simple |
| `usePaged` | `(endpoint, params, pageSize) → {items, total, hasMore, loading, error, loadMore, reload}` | **Genérico**: paginación incremental para cualquier listado |

## Glosario (lenguaje oficial)
- **Estado de cuenta** (fuente única `lib/accountState`): técnico (header) = Activo / Atención requerida / Suspendido; humano (hero) = Todo en orden / Requiere tu atención / Servicio suspendido.
- **Facturas:** Por pagar · Vencida · Pagada · Saldo por pagar.
- **Servicios:** Activo · Suspendido · Contrato por firmar · Inactivo.

## Reglas para próximos módulos (IA, Tickets, Soporte, Pagos, Notificaciones, Perfil)
1. Listados → `usePaged` + `LoadMore`. 2. Modales → `Dialog`. 3. Chips → `Badge`. 4. Labels → `FieldLabel`.
5. Pantallas con título → `PageHeader`. 6. Vacío/Error/Carga → `EmptyState`/`ErrorState`/`Skeleton`.
7. Texto → escala tipográfica (sin px sueltos, mínimo 12). 8. Color/radio/sombra/z → tokens.
9. Todo interactivo con `.focus-ring` y operable por teclado.

## Gobernanza (vigente desde el cierre del Sprint 1)
1. **Design System CONGELADO.** Sin refactors salvo defecto real en UAT o necesidad técnica claramente justificada. Los módulos nuevos se construyen con lo existente.
2. **Componentes oficiales = este documento.** Prohibidas implementaciones paralelas. Una variante nueva primero se evalúa: ¿pertenece al DS o es específica del módulo?
3. **Tokens = única fuente de verdad.** Prohibido hardcodear color/radio/sombra/tipografía/espaciado/transición si existe token.
4. **Hooks genéricos** (`useQuery`, `usePaged`): no conocen el dominio. La lógica de negocio vive en los módulos.
5. **Componentes desacoplados:** el DS no conoce facturas/pagos/dashboard/servicios/clientes/IA/tickets. Solo reciben props.
6. **Módulos futuros** (IA, Soporte, Tickets, Notificaciones, Perfil, Pagos, Historial, Auditoría) reutilizan el DS. Antes de crear un componente, verificar que no exista uno equivalente.
7. **Cambios:** todo hallazgo sigue el flujo Análisis de causa raíz → componentes afectados → riesgos → plan de corrección → **aprobación** → implementación en un único lote → regresión solo de lo afectado → evidencia. Sin mejoras estéticas/optimizaciones/refactors por iniciativa propia.
8. **Excepciones explícitas.** Cualquier excepción al DS se justifica técnicamente y se presenta el análisis **antes** de escribir código. No se permiten excepciones implícitas.
9. **Arquitectura base CERRADA.** El Portal del Cliente es ahora una plataforma estable: se construye **sobre** ella, no se rediseña. Toda decisión futura debe preservar esta arquitectura y evitar deuda técnica o inconsistencias visuales.

### Principios de ingeniería (permanentes, todo el ciclo de vida del portal)
10. **Sin duplicación.** Antes de escribir código nuevo, revisar si la funcionalidad ya existe. Nada de lógica duplicada ni componentes equivalentes en lugares distintos.
11. **Simplicidad primero.** Cada cambio preserva la simplicidad. Si una solución agrega complejidad innecesaria, proponer antes una alternativa más simple.
12. **Igual o mejor.** Todo cambio deja el código igual o mejor. No se aceptan soluciones que resuelvan hoy generando deuda para el siguiente sprint.
13. **Regla de tres (sin abstracción prematura).** Patrón repetido ≥3 veces → detenerse y proponer extraerlo al DS o a una utilidad compartida, **solo** tras justificar que el beneficio supera el costo.
14. **Escalabilidad.** Ningún cambio rompe la compatibilidad con módulos futuros (IA, Soporte, Tickets, Notificaciones, Perfil, Pagos…). Pensar la escalabilidad antes de implementar.
15. **Única fuente de verdad.** Si un dato/estado/color/texto/token/comportamiento ya tiene origen definido, ese sigue siendo el único lugar donde se administra.
16. **Autoauditoría antes de cerrar tarea.** Verificar: ¿dupliqué lógica/componentes/estilos? ¿rompí el DS? ¿generé deuda? ¿hay una solución más simple? ¿seguirá siendo válido dentro de un año? Solo si todo es satisfactorio, la tarea está terminada.
17. **ADR para cambios multi-módulo.** Toda decisión que modifique la arquitectura de más de un módulo se documenta con un ADR **breve**: problema · alternativas evaluadas · decisión · consecuencias. Lo mínimo para entender dentro de un año por qué se decidió así (sin documentación excesiva).
18. **Verificación de compatibilidad previa.** Antes de cualquier cambio que pueda afectar compatibilidad, verificar explícitamente: APIs · contratos · Design System · módulos futuros. Si alguno pudiera romperse, **detenerse y pedir aprobación antes de escribir código**.

> **Gobernanza CERRADA (18 reglas).** Etapa de diseño de arquitectura concluida. A partir de aquí el enfoque es **producto**: evolucionar una plataforma consolidada generando valor para el cliente y Alarmas Sentinela. No más reglas/refactors/infraestructura salvo defecto real.
