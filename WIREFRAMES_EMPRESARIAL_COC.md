# Wireframes — Flujo Empresarial · COC Sentinela

> Formato: Markdown/ASCII, versionable. Base para diseño visual (Figma) tras aprobación.
> Alcance: **cliente empresarial** — múltiples sucursales, múltiples usuarios/roles, múltiples servicios.
> Orientación: **operación diaria + toma de decisiones**. Desktop-first (con adaptación móvil).
> Cada pantalla indica su **Fase** del roadmap (PRD §10). Estado: borrador para revisión.

## Convenciones (específicas del empresarial)

- **Layout:** escritorio con **navegación lateral** + cabecera; móvil colapsa a barra inferior + menú. Densidad de información alta.
- **Cabecera global:** `[Org]` + **🏢 selector de sucursal** (Todas / sitio) + 📞 Emergencia + 🔔 Notificaciones + 💬 Asistente (→WhatsApp v1) + 👤 Usuario·Rol.
- **Navegación lateral:** 🏠 Tablero · 🛡️ Seguridad · 🌐 Internet · 📍 Flotilla · 📹 CCTV* · 🚪 Accesos* · 🧾 Facturación · 🛠️ Soporte · 📊 Reportes · ⚙️ Administración. (*placeholder v1.)
- **UI por rol:** la navegación y las acciones se filtran según el rol del usuario (ver matriz abajo). Un Contador solo ve Facturación/Reportes; un Operador-flotilla solo Flotilla.
- **Selector de sucursal:** transversal. "Todas" = vista agregada para decisión; un sitio = vista operativa de detalle.
- **Estados universales:** Cargando (skeleton) · Vacío (con propósito) · Error (reintentar) · Sin conexión (última info conocida).
- **Exportación:** las vistas de datos (facturas, reportes, flotilla, eventos) ofrecen exportar (CSV/PDF) — clave para el contador/gerente.
- **Regla de 3 interacciones:** toda acción importante a ≤3 taps/clics desde el Tablero (verificación al final).

## Matriz de roles (v1 propuesta)

| Capacidad | Titular/Admin | Operador-Flotilla | Contador | Lectura |
|---|:--:|:--:|:--:|:--:|
| Tablero (según sus módulos) | ✅ | ✅ (flotilla) | ✅ (finanzas) | ✅ |
| Seguridad / eventos | ✅ | — | — | 👁️ |
| Internet | ✅ | — | — | 👁️ |
| Flotilla (mapa, compartir, reportes) | ✅ | ✅ | — | 👁️ |
| Facturación / CFDI / estado de cuenta | ✅ | — | ✅ | 👁️ |
| Soporte (crear/seguir tickets) | ✅ | ✅ (sus servicios) | — | 👁️ |
| Reportes / exportar | ✅ | ✅ (flotilla) | ✅ (finanzas) | 👁️ |
| Administración (usuarios, sucursales) | ✅ | — | — | — |
| Autorizar servicios/firmar | ✅ | — | — | — |

> 👁️ = solo lectura. Roles = scopes en el JWT (gateway). **Confirmado v1:** Titular (Admin General), Operador de Flotilla, Contabilidad, Solo Lectura. La arquitectura debe permitir **agregar roles nuevos a futuro sin modificar la lógica principal** (roles/scopes data-driven, no hardcodeados). Permisos **limitables por sucursal, servicio y módulo**.

---

# 1. Acceso y contexto organizacional  [Fase 0]

> La autenticación es la misma del flujo residencial (OTP WhatsApp / contraseña / biométrico, ver `WIREFRAMES_RESIDENCIAL_COC.md` §2). Aquí solo el contexto empresarial posterior al login.

### EA-1 · Selección de organización / rol (si aplica)
```
┌───────────────────────────────────────────┐
│  Hola, Ing. Ramírez 👋                      │
│  Entras como:                               │
│  ╭─────────────────────────────────────╮   │
│  │ ● Transportes del Norte · Admin      │   │
│  │ ○ Comercializadora RG · Contador     │   │
│  ╰─────────────────────────────────────╯   │
│  [ Entrar ]                                 │
└───────────────────────────────────────────┘
```
- **Muestra:** solo si el usuario pertenece a >1 organización o tiene >1 rol. Si tiene uno solo, se omite → Tablero directo.
- **Acciones:** elegir contexto → aplica rol/scopes → Tablero.
- **Origen:** 🆕 identidad/roles en gateway (JWT con org + rol).

---

# 2. Tablero / Centro de operación  [Fase 1]

### ED-1 · Tablero — Todas las sucursales (vista de decisión)
```
┌──────────────────────────────────────────────────────────────────────┐
│ Transportes del Norte   🏢 Todas ▾    📞  🔔  💬   👤 Admin            │
├──────────────────────────────────────────────────────────────────────┤
│ Estado general:   ● 11 OK    ⚠ 2 atención    🔴 1 crítico              │
│                                                                        │
│ Servicios por sucursal                                    (tap = ver)  │
│ ┌──────────────┬───────┬───────┬───────┬───────┬───────┐              │
│ │ Sucursal     │🌐 Int │🛡️ Ala │📍 GPS │📹 CCTV│🚪 Acc │              │
│ ├──────────────┼───────┼───────┼───────┼───────┼───────┤              │
│ │ Matriz (HQ)  │   ●   │   ●   │ 18/18 │   ●   │   ●   │              │
│ │ Sucursal Sur │   ⚠   │   ●   │ 12/12 │   ●   │   —   │              │
│ │ Bodega Norte │   ●   │  🔴   │  8/10 │   ⚠   │   —   │              │
│ └──────────────┴───────┴───────┴───────┴───────┴───────┘              │
│                                                                        │
│ Indicadores            Alertas en vivo              Pendientes         │
│ • Adeudo:    $0        🔴 Bodega: intrusión 14:32   • 3 tickets        │
│ • Próx. vto: 1-jul     ⚠ Sur: internet lento        • 1 contrato firma │
│ • SLA mes:   99.8%     ⚠ 2 unidades sin señal >2h    • Factura jun     │
│ • Flotilla:  38/40     [ Ver todas → ]               [ Ver → ]         │
│                                                                        │
│ [🗺️ Mapa flotilla] [📊 Reportes] [🧾 Estado de cuenta] [+ Reportar]    │
└──────────────────────────────────────────────────────────────────────┘
```
- **Muestra:** veredicto agregado; **matriz servicios×sucursal** (corazón operativo — un golpe de vista de todo el negocio); indicadores de decisión (adeudo, SLA, uptime, flotilla); **feed de alertas en vivo** priorizado; pendientes accionables; accesos rápidos.
- **Acciones:** tap celda de matriz → drill al servicio en esa sucursal (ED-2 / módulo); ver alertas (ED-3); mapa flotilla (EF-1); reportes (ER-1); estado de cuenta (EB-1); reportar (ESU-2).
- **Indicadores de valor:** servicios OK/atención/crítico, SLA del mes, unidades reportando, adeudo, próximo vencimiento.
- **Estados:** todo OK → matriz verde; cualquier 🔴 escala arriba el feed de alertas.
- **Origen:** agregación multi-sitio en gateway (estados subs + health + eventos + flotilla + account.move).

### ED-2 · Tablero — Vista por sucursal (operación de detalle)
```
┌──────────────────────────────────────────────────────────────────────┐
│ 🏢 Bodega Norte ▾                                  📞 🔔 💬 👤 Admin   │
├──────────────────────────────────────────────────────────────────────┤
│ 🔴 Atención requerida: alarma de intrusión activa (14:32)  [Ver → ]    │
│                                                                        │
│ 🌐 Internet ●   🛡️ Alarma 🔴   📍 GPS 8/10   📹 CCTV ⚠                  │
│ Estable 6d      Intrusión      2 sin señal    1 cámara                 │
│                 en curso                      desconectada             │
│                                                                        │
│ Eventos hoy            Tickets abiertos        Equipos                 │
│ • 14:32 Intrusión      • OS-0192 internet      • 6 paneles · 24 cám.   │
│ • 09:10 Apertura       (técnico en camino)     [ Ver equipos ]         │
│                                                                        │
│ [🗺️ Ver flotilla del sitio] [📄 Reporte del sitio]                     │
└──────────────────────────────────────────────────────────────────────┘
```
- **Muestra:** todo lo de **una** sucursal: estado por servicio, evento crítico arriba, eventos del día, tickets, equipos del sitio.
- **Acciones:** drill a cada módulo filtrado por el sitio; reporte del sitio.
- **Origen:** ♻️ scoped por `service_address_id` / sitio.

### ED-3 · Feed de alertas (triage)
```
┌───────────────────────────────────────────────────────┐
│ ←  Alertas en vivo         Filtrar: [Sitio▾][Tipo▾]    │
│ 🔴 14:32 Bodega · Intrusión · Cocina      [Atender →]  │
│ ⚠ 13:50 Sur · Internet lento (>40% pérdida) [Ver →]   │
│ ⚠ 12:10 Flotilla · Unid.12 sin señal 2h    [Ver →]    │
│ ⚠ 11:05 Bodega · Cámara entrada offline    [Ver →]    │
│ ● 09:10 Bodega · Apertura (normal)                     │
└───────────────────────────────────────────────────────┘
```
- **Muestra:** todas las alertas del negocio, ordenadas por severidad, con sitio y tipo; filtros.
- **Acciones:** atender/ver → pantalla destino (deep-link).
- **Origen:** agregación de eventos de alarma + salud internet/flotilla/CCTV.

---

# 3. Seguridad / Alarma (multi-sucursal)  [eventos Fase 1–2 · núcleo Fase 2]

### ES-1 · Seguridad — panorama por sucursal
```
┌───────────────────────────────────────────────────────┐
│ ←  Seguridad      🏢 Todas ▾                            │
│ Paneles por sucursal                                   │
│ ┌──────────────┬─────────┬───────┬──────┬───────────┐ │
│ │ Sucursal     │ Estado  │ CA    │ Bat. │ Últ.señal │ │
│ ├──────────────┼─────────┼───────┼──────┼───────────┤ │
│ │ Matriz       │ ● línea │ ⚡ CA  │ 92%  │ 3 min     │ │
│ │ Sur          │ ● línea │ ⚡ CA  │ 88%  │ 5 min     │ │
│ │ Bodega Norte │ 🔴 evento│ ⚡ CA │ 80%  │ ahora     │ │
│ └──────────────┴─────────┴───────┴──────┴───────────┘ │
│ [ Eventos (todas) ]  [ Contactos por sitio ]          │
└───────────────────────────────────────────────────────┘
```
- **Muestra:** salud de cada panel (comunicación, **CA/energía**, **batería**, última señal) por sucursal; medio de comunicación en detalle.
- **Acciones:** tap fila → detalle del panel/sitio; eventos (ES-2); contactos por sitio.
- **Origen:** ♻️ `monitoring.device` por sitio · 🆕 `get_health_status`.

### ES-2 · Eventos (todas las sucursales)
```
┌───────────────────────────────────────────────────────┐
│ ←  Eventos      [Sitio▾][Tipo▾][Estado▾]   [Exportar] │
│ 🔴 14:32 Bodega · Intrusión · Atendiendo    [Ver]     │
│ ● 09:10 Bodega · Apertura · Normal                    │
│ ● 08:55 Matriz · Apertura · Normal                    │
│ ● 03-jun Sur · Prueba · Normal                        │
└───────────────────────────────────────────────────────┘
```
- **Muestra:** timeline consolidado con sucursal; filtros por sitio/tipo/estado; **exportar**.
- **Acciones:** ver detalle (ES-3 = reusa S-3 residencial: detalle + patrulla + reporte PDF).
- **Origen:** ♻️ `alarm.event` (record rule + scope multi-sitio del cliente).

### ES-3 · Detalle de evento + patrulla + reporte PDF
- Igual a **S-3/S-4 del flujo residencial** (detalle, operador que atendió, patrulla en mapa, descargar reporte PDF), con etiqueta de **sucursal**. Autorizar patrulla = magic link (rol Titular/Admin).

---

# 4. Internet (multi-sucursal)  [estado Fase 1–2 · consumo/SLA Fase 2]

### EI-1 · Internet — enlaces por sucursal
```
┌───────────────────────────────────────────────────────┐
│ ←  Internet     🏢 Todas ▾                  [Exportar] │
│ ┌──────────────┬─────────┬──────┬──────┬────────────┐ │
│ │ Sucursal     │ Enlace  │ Plan │ Señal│ Uptime mes │ │
│ ├──────────────┼─────────┼──────┼──────┼────────────┤ │
│ │ Matriz       │ ● OK    │100M  │ buena│ 99.9%      │ │
│ │ Sur          │ ⚠ lento │ 50M  │ regul│ 98.2%      │ │
│ │ Bodega Norte │ ● OK    │ 50M  │ buena│ 99.7%      │ │
│ └──────────────┴─────────┴──────┴──────┴────────────┘ │
│ SLA del periodo: 99.3%        [ Reportar falla ]      │
└───────────────────────────────────────────────────────┘
```
- **Muestra:** estado de cada enlace, plan, señal, **uptime/SLA** por sucursal y agregado.
- **Acciones:** tap sitio → detalle/consumo (EI-2); reportar falla (→ ESU-2).
- **Origen:** ♻️ `subscription.conn_online/antenna_signal_dbm` · 🔧 uptime/consumo (netwatch TSDB, Fase 2).

### EI-2 · Detalle de enlace / consumo (por sitio)
```
┌───────────────────────────────────────────────────────┐
│ ←  Sur · Internet 50M                                  │
│ ● Conectado · señal regular · estable 2d              │
│ Consumo (mes)*  ▁▂▄▆█▅▃  820 GB / —    *Fase 2        │
│ Incidencias:                                          │
│ • 20-may Corte 35 min · energía CFE                   │
│ • 13-may Lentitud · resuelto                          │
│ [ Diagnóstico ] [ Reportar falla ] [ Exportar ]       │
└───────────────────────────────────────────────────────┘
```
- **Muestra:** estado, consumo (Fase 2), historial de incidencias con causa.
- **Nota:** autodiagnóstico "¿soy yo o la red?" + status por zona = **Fase 2** (PRD §8).

---

# 5. Flotilla / GPS  [Fase 2–3]  ← núcleo operativo diario del empresarial

### EF-1 · Mapa de flotilla en vivo
```
┌──────────────────────────────────────────────────────────────────────┐
│ ←  Flotilla   🏢 Todas ▾   [Buscar unidad…]      38/40 en línea  📊    │
│ ╭──────────────────────────────────────────────────────────────────╮ │
│ │                       [ mapa con unidades ]                         │ │
│ │     🚚12   🚚07          🚚22(⚠ detenido)      🚚31                 │ │
│ ╰──────────────────────────────────────────────────────────────────╯ │
│ Alertas: ⚠ 2 sin señal · ⚠ 1 exceso velocidad · ⚠ 1 fuera geocerca   │
│ Unidades                                          [Exportar][Reportes] │
│ • 🚚12 En movimiento · 62 km/h · Blvd … · hace 8s   [Ver][Compartir]  │
│ • 🚚22 Detenido 45 min · Bodega · hace 20s          [Ver][Compartir]  │
│ • 🚚05 Sin señal 2h · última: Carr.57 · 12:10       [Ver]             │
└──────────────────────────────────────────────────────────────────────┘
```
- **Muestra:** mapa en vivo de todas las unidades; contador reportando/total; **alertas de flotilla** (sin señal, velocidad, geocerca); lista con estado/posición/hora.
- **Acciones:** ver recorrido/detalle (EF-2); **compartir ubicación temporal** (link que expira); buscar unidad; exportar; reportes (EF-5). Inmovilizar = **Fase 2–3**.
- **Indicadores:** unidades en línea, alertas activas, km, velocidad.
- **Origen:** ♻️ `senticar.service` / Traccar, `create_share_link`, `get_last_location`.

### EF-2 · Detalle de unidad / recorrido
```
┌───────────────────────────────────────────────────────┐
│ ←  🚚12 · Volvo FH (Placa ABC-12-34)                   │
│ ● En movimiento · 62 km/h · hace 8s                    │
│ [ Mapa en vivo ]   [ Recorrido: Hoy ▾ ]               │
│ Hoy: 142 km · 3 paradas · 1 exceso velocidad          │
│ Geocercas: dentro de "Ruta Norte"                     │
│ [ Compartir ubicación ] [ Inmovilizar* ] [ Reporte ]   │  *Fase 2-3
└───────────────────────────────────────────────────────┘
```
- **Muestra:** estado, recorrido histórico, paradas, alertas, geocercas, datos de unidad.
- **Acciones:** ver recorrido por fecha; compartir; reporte de la unidad; (Fase 2–3) inmovilizar/comandos.

### EF-3 · Alertas de flotilla
```
┌───────────────────────────────────────────────────────┐
│ ←  Alertas de flotilla     [Tipo▾][Unidad▾][Exportar] │
│ ⚠ 12:10 🚚05 Sin señal > 2h                            │
│ ⚠ 11:40 🚚31 Exceso de velocidad (98 km/h)             │
│ ⚠ 10:05 🚚22 Salida de geocerca "Ruta Norte"          │
└───────────────────────────────────────────────────────┘
```
- **Muestra/Acciones:** alertas por tipo/unidad; tap → unidad; exportar.

### EF-4 · Compartir unidad (link temporal)
- Igual al patrón residencial GPS: genera link que expira y se comparte por WhatsApp. ♻️ `create_share_link`. Permiso: Titular/Operador-flotilla.

### EF-5 · Reportes de flotilla
```
┌───────────────────────────────────────────────────────┐
│ ←  Reportes de flotilla                                │
│ Tipo: ( ) Recorridos ( ) Velocidades ( ) Paradas      │
│       ( ) Geocercas  ( ) Uso por unidad               │
│ Rango: [ 01-jun ] a [ 25-jun ]   Unidad/Todas ▾       │
│ [ Generar ]   [ Exportar PDF/CSV ]                    │
└───────────────────────────────────────────────────────┘
```
- **Muestra/Acciones:** generar reportes operativos exportables (decisión: uso, eficiencia, cumplimiento de rutas).

---

# 6. CCTV y Control de acceso  [placeholders v1]
- Secciones visibles si el cliente tiene el servicio, con estado "Próximamente". CCTV: lista de cámaras + estado (vista preliminar). Accesos: puntos + log (preliminar). Telemetría/operación completas = fase posterior (requiere definir fuente NVR/controladora).

---

# 7. Facturación empresarial  [Fase 1 · solo consulta]

### EB-1 · Estado de cuenta consolidado
```
┌──────────────────────────────────────────────────────────────────────┐
│ ←  Facturación   🏢 Todas ▾                              [Exportar]    │
│ ╭──────────────────────────────────────────────────────────────────╮ │
│ │ Adeudo total: $0      Próximo vencimiento: 1-jul   Crédito: al día│ │
│ ╰──────────────────────────────────────────────────────────────────╯ │
│ Por sucursal                                                          │
│ • Matriz       $0     al día                                         │
│ • Sur          $0     al día                                         │
│ • Bodega Norte $0     al día                                         │
│ Facturas recientes                          [ Ver todas ][ CFDI masivo]│
│ • Jun · Global · $12,450 · por timbrar                               │
│ • May · Global · $12,450 · Pagada                                    │
└──────────────────────────────────────────────────────────────────────┘
```
- **Muestra:** adeudo **consolidado** + desglose por sucursal; facturas; estado de crédito.
- **Acciones:** ver facturas (EB-2); **descarga masiva de CFDI** (EB-3); exportar estado de cuenta. (Pagar = Fase 2.)
- **Origen:** ♻️ `account.move` + grouping (`invoice_grouping_method`) + `om_account_followup`; composición en gateway.

### EB-2 · Facturas (filtrable)
```
┌───────────────────────────────────────────────────────┐
│ ←  Facturas  [Sitio▾][Estado▾][Año▾]      [Exportar]  │
│ • Jun A-1240 Global $12,450 ⚠ Pendiente   [Ver]       │
│ • May A-1180 Global $12,450 ● Pagada      [Ver]       │
│ • Abr A-1120 Global $12,450 ● Pagada      [Ver]       │
└───────────────────────────────────────────────────────┘
```
- **Acciones:** filtrar; tap → detalle (reusa F-3 residencial: PDF + XML, etiqueta FACTURA/REMISIÓN, UUID).

### EB-3 · Descarga masiva de CFDI (regalo del contador)
```
┌───────────────────────────────────────────────────────┐
│ ←  Descargar CFDI                                      │
│ Periodo: [ ene-2026 ] a [ jun-2026 ]                  │
│ Sucursal: Todas ▾    Tipo: Facturas ▾                 │
│ [ Descargar ZIP (PDF + XML) ]                         │
└───────────────────────────────────────────────────────┘
```
- **Muestra/Acciones:** seleccionar periodo/sitio/tipo → descargar paquete PDF+XML. Rol Contador/Titular.
- **Origen:** ♻️ render CFDI + XML (solo lectura); empaquetado en gateway.

---

# 8. Soporte (multi-sucursal)  [Fase 1–2]

### ESU-1 · Soporte — tickets del negocio
```
┌───────────────────────────────────────────────────────┐
│ ←  Soporte   🏢 Todas ▾        [+ Reportar][Exportar] │
│ Abiertos                                              │
│ • OS-0192 Bodega · Internet · 🚚 en camino · SLA 2h  │
│ • OS-0188 Sur · CCTV · Asignado · SLA 4h             │
│ Recientes                                             │
│ • OS-0181 Matriz · Mantenimiento · ● Resuelto        │
└───────────────────────────────────────────────────────┘
```
- **Muestra:** tickets de todas las sucursales con sitio, servicio, estado y **SLA**; filtros; exportar.
- **Acciones:** reportar (ESU-2); tap → detalle/tracking (ESU-3 = reusa SP-3/SP-4 residencial).
- **Origen:** ♻️ `fsm.order` multi-sitio.

### ESU-2 · Reportar (con sucursal y servicio)
```
┌───────────────────────────────────────────────────────┐
│ ←  Reportar incidencia                                │
│ Sucursal: Bodega Norte ▾                              │
│ Servicio: ( )Internet ( )Alarma ( )CCTV ( )GPS       │
│ Descripción: ( ___________________ )  [📎]           │
│ Prioridad: ( )Normal ( )Alta ( )Crítica              │
│ [ Enviar ]                                            │
└───────────────────────────────────────────────────────┘
```
- **Diferencia vs residencial:** incluye **sucursal** y **prioridad** (operación empresarial).
- **Origen:** 🔧 creación de orden a método de modelo; ♻️ `fsm.order`.

### ESU-3 · Detalle / tracking
- Reusa **SP-3 (stepper + chat)** y **SP-4 (mapa técnico + ETA)** del flujo residencial, con etiqueta de sucursal y SLA.

---

# 9. Reportes y analítica  [Fase 1 (básico) → 2/3 (avanzado)]

### ER-1 · Centro de reportes (decisión)
```
┌───────────────────────────────────────────────────────┐
│ ←  Reportes                                           │
│ Operación        Finanzas         Flotilla            │
│ • Eventos por    • Estado de      • Recorridos        │
│   sucursal         cuenta         • Velocidades       │
│ • SLA servicios  • Facturas/CFDI  • Uso por unidad    │
│ • Tickets/tiempos• Pagos          • Geocercas         │
│ Rango: [ … ]  Sucursal: Todas ▾   [ Generar ][Export] │
└───────────────────────────────────────────────────────┘
```
- **Muestra:** catálogo de reportes para **toma de decisiones**: operación (eventos, SLA, tickets), finanzas (estado de cuenta, CFDI, pagos), flotilla (uso, eficiencia).
- **Acciones:** generar por rango/sucursal; exportar PDF/CSV.
- **Nota:** v1 = reportes básicos (listados/exportes); analítica avanzada (tendencias, tableros) = Fase 2–3. **Centro de Mando/wallboard** = Fase 3 (PRD §8).

---

# 10. Administración  [Fase 1–2]  (rol Titular/Admin)

### EAD-1 · Usuarios y roles
```
┌───────────────────────────────────────────────────────┐
│ ←  Usuarios y roles               [ + Invitar usuario ]│
│ • Ing. Ramírez · Admin · todas las sucursales         │
│ • Laura M. · Contador · todas                         │
│ • Pedro S. · Operador-Flotilla · Bodega+Sur           │
│ • Recepción · Lectura · Matriz                        │
│   [ editar rol ] [ alcance sucursales ] [ desactivar ]│
└───────────────────────────────────────────────────────┘
```
- **Muestra:** usuarios de la organización con rol y **alcance por sucursal**.
- **Acciones:** invitar (por WhatsApp/correo), editar rol, limitar a sucursales, desactivar.
- **Origen:** 🆕 gestión de identidad/roles en gateway (scopes en JWT).

### EAD-2 · Sucursales / ubicaciones
```
┌───────────────────────────────────────────────────────┐
│ ←  Sucursales                                         │
│ • Matriz (HQ) · Calle … · 4 servicios                 │
│ • Sucursal Sur · Av … · 3 servicios                   │
│ • Bodega Norte · Carr … · 3 servicios                 │
│   [ ver detalle / contactos del sitio ]               │
└───────────────────────────────────────────────────────┘
```
- **Muestra:** ubicaciones de servicio, servicios por sitio, contactos del sitio.
- **Origen:** ♻️ `res.partner` (child_of) / `service_address_id`.

### EAD-3 · Contratos y documentos
- Lista de contratos por sucursal/servicio (firmados / por firmar) + documentos descargables. **Firmar** = magic link (rol Titular). Reusa flujo de firma (MC-3 residencial).

### EAD-4 · Notificaciones (ruteo por rol)
```
┌───────────────────────────────────────────────────────┐
│ ←  Notificaciones del equipo                          │
│ ¿Quién recibe qué?                                    │
│ • Eventos de alarma → Admin + Lectura(Matriz)         │
│ • Alertas de flotilla → Operador-Flotilla             │
│ • Vencimiento de factura → Contador + Admin           │
│ • Tickets/SLA → Admin                                 │
│ Canales: WhatsApp / Push / Correo                     │
└───────────────────────────────────────────────────────┘
```
- **Muestra/Acciones:** **ruteo de notificaciones por rol** (cada quién recibe lo suyo) + canales. Diferenciador operativo clave.
- **Origen:** ♻️ `partner.notify()` + 🆕 reglas de ruteo por rol en gateway.

---

# 11. Centro de notificaciones (org)  [Fase 1]
- Igual a **N-1 residencial**, pero con etiqueta de sucursal y filtrado por rol (cada usuario ve las notificaciones de su alcance).

---

## Mapa de navegación (flujo empresarial)

```
Login(compartido)→[EA-1 org/rol si aplica]→Tablero(ED-1 Todas)
Tablero ─┬─ matriz/celda → ED-2 (sitio) / módulo del servicio
         ├─ 🔔 → Notif(org) · 📞 Emergencia · 💬 WhatsApp
         ├─ Seguridad(ES-1)→Eventos(ES-2)→Detalle/PDF(ES-3)
         ├─ Internet(EI-1)→Detalle/Consumo(EI-2)
         ├─ Flotilla(EF-1)→Unidad(EF-2)·Alertas(EF-3)·Compartir(EF-4)·Reportes(EF-5)
         ├─ Facturación(EB-1)→Facturas(EB-2)→Detalle CFDI · CFDI masivo(EB-3)
         ├─ Soporte(ESU-1)→Reportar(ESU-2)·Ticket/Tracking(ESU-3)
         ├─ Reportes(ER-1)→generar/exportar
         └─ Administración(EAD-1 usuarios·EAD-2 sucursales·EAD-3 contratos·EAD-4 notif)
Externos (magic link): Autorizar patrulla · Firmar contrato
```

## Verificación de la regla de las 3 interacciones (desde Tablero)

| Acción | Ruta | Taps |
|---|---|---|
| Ver estado de un servicio en una sucursal | Tablero→celda matriz | 1 |
| Atender alerta crítica | Tablero→Alerta(ED-3)→Atender | 2 |
| Ver mapa de flotilla | Tablero→[🗺️ Mapa] | 1 |
| Compartir una unidad | Tablero→Flotilla→Unidad→Compartir | 3 |
| Estado de cuenta consolidado | Tablero→[🧾] | 1 |
| Descargar CFDI masivo | Tablero→Facturación→CFDI masivo | 2 |
| Reportar incidencia (sitio+servicio) | Tablero→[+ Reportar]→Enviar | 2 |
| Rastrear técnico | Tablero→Soporte→Ticket→Mapa | 3 |
| Generar/exportar reporte | Tablero→[📊 Reportes]→Generar | 2 |
| Gestionar usuarios/roles | Tablero→Administración→Usuarios | 2 |
| Ver eventos de seguridad (todas) | Tablero→Seguridad→Eventos | 2 |

✅ Todas las acciones importantes ≤ 3 interacciones.

## Decisiones tomadas (flujo empresarial APROBADO)
- ✅ **Roles v1:** Titular (Admin General), Operador de Flotilla, Contabilidad, Solo Lectura. Arquitectura **extensible** (agregar roles sin tocar lógica principal — roles/scopes data-driven).
- ✅ **Permisos por sucursal/servicio/módulo:** un usuario puede limitarse a determinadas sucursales, servicios o módulos según su rol.
- ✅ **Centro de Mando (Wallboard):** planificado para **Fase 3**, fuera del alcance v1.
- ✅ **CCTV / Control de Acceso:** placeholder **discreto** "Próximamente" en v1 (sin generar expectativas exageradas).

> Flujo empresarial aprobado por Enrique el 25-jun-2026. Base para diseño visual (Figma).
