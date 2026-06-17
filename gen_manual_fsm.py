# -*- coding: utf-8 -*-
"""Genera el Manual de Usuario del módulo sentinela_fsm (Gestión de Servicios) en PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    ListFlowable, ListItem, HRFlowable, KeepTogether, Image
)

OUT = "/mnt/c/Users/dell/DellCli/MANUAL_USUARIO_FSM_GESTION_SERVICIOS.pdf"
LOGO = "/mnt/c/Users/dell/DellCli/logo_sentinela_master.jpg"

NAVY = colors.HexColor("#1a237e")
BLUE = colors.HexColor("#1565c0")
LIGHT = colors.HexColor("#e8eaf6")
GREY = colors.HexColor("#555555")
GREENC = colors.HexColor("#2e7d32")
ORANGE = colors.HexColor("#e65100")

styles = getSampleStyleSheet()

def S(name, **kw):
    styles.add(ParagraphStyle(name=name, **kw))

S("Cover", fontName="Helvetica-Bold", fontSize=30, textColor=NAVY, alignment=TA_CENTER, leading=36)
S("CoverSub", fontName="Helvetica", fontSize=15, textColor=GREY, alignment=TA_CENTER, leading=22)
S("CoverSmall", fontName="Helvetica", fontSize=10, textColor=GREY, alignment=TA_CENTER, leading=16)
S("H1", fontName="Helvetica-Bold", fontSize=17, textColor=NAVY, spaceBefore=14, spaceAfter=8, leading=21)
S("H2", fontName="Helvetica-Bold", fontSize=13, textColor=BLUE, spaceBefore=10, spaceAfter=5, leading=16)
S("H3", fontName="Helvetica-Bold", fontSize=11, textColor=colors.black, spaceBefore=7, spaceAfter=3, leading=14)
S("Body", fontName="Helvetica", fontSize=10, textColor=colors.black, alignment=TA_JUSTIFY, leading=15, spaceAfter=5)
S("BulletX", fontName="Helvetica", fontSize=10, textColor=colors.black, leading=14)
S("Note", fontName="Helvetica-Oblique", fontSize=9.5, textColor=GREY, leading=13, spaceAfter=4)
S("Cell", fontName="Helvetica", fontSize=9, textColor=colors.black, leading=12)
S("CellB", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, leading=12)
S("CellBd", fontName="Helvetica-Bold", fontSize=9, textColor=colors.black, leading=12)
S("TOC", fontName="Helvetica", fontSize=11, textColor=colors.black, leading=20)

E = []

def h1(t): E.append(Paragraph(t, styles["H1"]))
def h2(t): E.append(Paragraph(t, styles["H2"]))
def h3(t): E.append(Paragraph(t, styles["H3"]))
def p(t): E.append(Paragraph(t, styles["Body"]))
def note(t): E.append(Paragraph("ℹ️ " + t, styles["Note"]))
def sp(h=6): E.append(Spacer(1, h))
def rule(): E.append(HRFlowable(width="100%", thickness=0.6, color=LIGHT, spaceBefore=6, spaceAfter=6))

def bullets(items, st="BulletX"):
    li = [ListItem(Paragraph(x, styles[st]), leftIndent=6, value=None) for x in items]
    E.append(ListFlowable(li, bulletType="bullet", bulletColor=BLUE, leftIndent=14, bulletFontSize=8))

def table(header, rows, widths):
    data = [[Paragraph(c, styles["CellB"]) for c in header]]
    for r in rows:
        data.append([Paragraph(c, styles["Cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fb")]),
    ]
    t.setStyle(TableStyle(ts))
    E.append(t)
    sp(6)

# ============ PORTADA ============
E.append(Spacer(1, 55))
_logo = Image(LOGO, width=95*mm, height=95*mm*512/1440)  # proporción 1440x512
_logo.hAlign = "CENTER"
E.append(_logo)
E.append(Spacer(1, 28))
E.append(Paragraph("Gestión de Servicios", styles["Cover"]))
E.append(Spacer(1, 18))
E.append(HRFlowable(width="55%", thickness=2, color=BLUE, hAlign="CENTER"))
E.append(Spacer(1, 18))
E.append(Paragraph("Manual de Usuario", styles["CoverSub"]))
E.append(Spacer(1, 4))
E.append(Paragraph("Módulo de Órdenes de Servicio en Campo (FSM)", styles["CoverSub"]))
E.append(Spacer(1, 60))
E.append(Paragraph("Instalación &bull; Reparación &bull; Mantenimiento &bull; Traslado &bull; Retiro &bull; Patrullaje", styles["CoverSmall"]))
E.append(Spacer(1, 40))
E.append(Paragraph("Versión del módulo 18.0.1.8.9 &nbsp;|&nbsp; Odoo 18 Community", styles["CoverSmall"]))
E.append(Paragraph("Junio 2026", styles["CoverSmall"]))
E.append(PageBreak())

# ============ ÍNDICE ============
h1("Contenido")
toc = [
    "1.  ¿Qué es Gestión de Servicios?",
    "2.  Conceptos básicos",
    "3.  Tipos de orden y prioridades",
    "4.  El ciclo de vida de una orden",
    "5.  La pantalla de la orden (oficina / central)",
    "6.  Crear una orden manualmente",
    "7.  El portal del técnico (celular)",
    "8.  Patrullaje y respuesta a emergencias",
    "9.  Rastreo en vivo para el cliente (SentiCar)",
    "10. El portal del cliente",
    "11. Checklist, evidencias y equipos",
    "12. Cómo se generan órdenes automáticamente",
    "13. Mantenimiento preventivo automático",
    "14. Flujo de cotización (apoyo de Ventas)",
    "15. Reporte de servicio al cliente",
    "16. Integración con otros módulos",
    "17. Preguntas frecuentes",
]
for t in toc:
    E.append(Paragraph(t, styles["TOC"]))
E.append(PageBreak())

# ============ 1 ============
h1("1. ¿Qué es Gestión de Servicios?")
p("<b>Gestión de Servicios</b> (módulo <font face='Helvetica-Bold'>sentinela_fsm</font>) es el sistema que coordina "
  "todo el trabajo de campo de Sentinela: las visitas de los técnicos y patrulleros al domicilio del cliente. "
  "Sustituye a las herramientas anteriores (2Worker / Auvo) e integra el trabajo de campo con las ventas, "
  "los contratos (suscripciones) y la central de monitoreo.")
p("Una <b>orden de servicio</b> es el documento central: representa una visita o un trabajo concreto "
  "(instalar una alarma, reparar el internet, hacer mantenimiento a un GPS, responder a una alarma con una patrulla, etc.). "
  "Cada orden viaja por una serie de etapas, desde que se crea hasta que se cierra y se le envía el reporte al cliente.")
p("El módulo trabaja en <b>tres frentes</b> a la vez:")
bullets([
    "<b>La oficina / central:</b> crea, asigna y supervisa las órdenes desde la computadora (Odoo backend).",
    "<b>El técnico / patrullero:</b> trabaja desde su celular con un portal simplificado, registra lo que hizo, toma fotos y captura la firma del cliente.",
    "<b>El cliente:</b> levanta reportes desde su portal y puede ver en un mapa, en vivo, cómo llega la patrulla o el técnico a su domicilio.",
])

h1("2. Conceptos básicos")
table(
    ["Concepto", "Qué significa"],
    [
        ["Orden de servicio", "El trabajo a realizar. Tiene un folio único (ej. OS-0001), un cliente, una dirección, un tipo y un técnico responsable."],
        ["Etapa / Estado", "En qué punto va la orden: Nuevo, Asignado, En Proceso, Pausado, Finalizado o Cancelado."],
        ["Tipo de servicio", "Qué clase de trabajo es: instalación, reparación, mantenimiento, traslado, retiro o patrullaje."],
        ["Técnico / Patrullero", "La persona que ejecuta la orden en campo. Entra al sistema desde su celular."],
        ["Unidad de patrulla", "El dispositivo que se rastrea por GPS (un celular compartido o un vehículo). No es lo mismo que el patrullero (la persona)."],
        ["Suscripción / Contrato", "El servicio contratado por el cliente (alarma, GPS, internet). La orden se enlaza a él para heredar y actualizar sus datos."],
        ["Token de rastreo", "Una clave secreta única de cada orden que permite al cliente ver el mapa en vivo sin necesidad de contraseña."],
    ],
    [42*mm, 128*mm],
)
note("Una misma orden puede mostrar campos distintos según su tipo: una de internet pide datos de antena y router; "
     "una de alarma pide marca de panel y zonas; una de patrullaje pide el dictamen de la situación.")

# ============ 3 ============
h1("3. Tipos de orden y prioridades")
h2("Tipos de servicio")
table(
    ["Tipo", "Para qué se usa"],
    [
        ["Instalación", "Alta nueva: instalar físicamente el equipo (alarma, GPS, antena de internet) en el domicilio."],
        ["Reparación / Falla", "Atender una falla o avería reportada por el cliente. La reactivación tras pago entra aquí, como urgente."],
        ["Mantenimiento", "Mantenimiento preventivo programado. Se genera solo, según la frecuencia del contrato."],
        ["Traslado", "Mover el equipo del cliente a un domicilio nuevo."],
        ["Retiro / Desinstalación", "Retirar el equipo. Al finalizar, cierra el contrato del cliente automáticamente."],
        ["Patrullaje / Respuesta", "Despachar una patrulla al domicilio (típicamente tras una alarma). Incluye rastreo en vivo y dictamen."],
        ["Otro", "Cualquier servicio que no encaje en los anteriores."],
    ],
    [48*mm, 122*mm],
)
h2("Prioridades")
p("Cada orden tiene una prioridad que ayuda a ordenar el trabajo del día: "
  "<b>Normal</b>, <b>Alta</b>, <b>Urgente</b> y <b>Crítica</b>. "
  "Las órdenes urgentes y críticas aparecen primero en la agenda del técnico.")

# ============ 4 ============
h1("4. El ciclo de vida de una orden")
p("Toda orden recorre las mismas etapas. La barra de estado, arriba del formulario, muestra en qué punto va:")
p("<b>Nuevo &nbsp;→&nbsp; Asignado &nbsp;→&nbsp; En Proceso &nbsp;→&nbsp; (Llegada) &nbsp;→&nbsp; Finalizado</b>", )
p("Con dos desvíos posibles: <b>Pausado</b> (se retoma después) y <b>Cancelado</b>.")
sp()
table(
    ["Etapa", "Qué pasa y qué se dispara automáticamente"],
    [
        ["Nuevo", "La orden recién creada. El sistema le pone folio, genera el token de rastreo y arma el checklist según el tipo de servicio y la tecnología."],
        ["Asignado", "La oficina elige técnico y fecha. Al asignar se avisa al técnico (correo + notificación). Sin técnico y sin fecha no se puede asignar."],
        ["En Proceso", "El técnico hace 'Iniciar Trabajo' (check-in): se guarda la hora y su ubicación, y se le avisa al cliente que el técnico va en camino (con link de rastreo si es patrulla)."],
        ["Llegada al sitio", "El técnico/patrullero confirma que llegó. Se guarda hora y coordenadas; en patrullaje se valida la geocerca (debe estar a menos de ~150 m del domicilio)."],
        ["Pausado", "El trabajo se detiene con una causa y notas (falta refacción, requiere cotización, etc.). Si la causa es 'cotización', se avisa al vendedor."],
        ["Finalizado", "El técnico cierra con firma del cliente. Se descuenta el inventario usado, se vuelcan los datos técnicos al contrato, se reprograma el mantenimiento y se avisa a la central."],
        ["Cancelado", "La orden se anula. No toca inventario ni contrato."],
    ],
    [34*mm, 136*mm],
)
note("La firma del cliente es OBLIGATORIA para finalizar. Sin firma, el sistema no deja cerrar la orden.")

# ============ 5 ============
h1("5. La pantalla de la orden (oficina / central)")
p("Desde la computadora, en el menú <b>Gestión de Servicios</b>, el personal de oficina ve y administra las órdenes. "
  "El menú se organiza así:")
bullets([
    "<b>Nuevo Reporte</b> — abre el asistente para crear una orden a mano.",
    "<b>Mis Órdenes</b> / <b>Mi Ruta del Día</b> — las órdenes propias del usuario, sin las ya terminadas.",
    "<b>Tablero</b> — la vista general de todas las órdenes (lista, kanban y agenda/calendario).",
    "<b>Operaciones &rarr; Todas las Órdenes</b> y <b>Rutas Optimizadas</b> (gestores).",
    "<b>Reportes y Análisis &rarr; Análisis de Desempeño</b> — métricas por técnico (gestores).",
    "<b>Configuración &rarr; Causas de Pausa</b> — catálogo de motivos de pausa (gestores).",
])
h2("Botones de la barra superior")
p("Aparecen según la etapa de la orden:")
table(
    ["Botón", "Aparece cuando…", "Qué hace"],
    [
        ["Navegar (Maps)", "Siempre", "Abre Google Maps en la dirección del cliente."],
        ["Programar / Asignar", "Estado Nuevo", "Asigna técnico y fecha; avisa al técnico."],
        ["Iniciar Trabajo", "Estado Asignado", "Check-in: arranca el cronómetro y avisa al cliente."],
        ["Pausar", "Estado En Proceso", "Abre el asistente para justificar la pausa."],
        ["Reanudar", "Estado Pausado", "Continúa la orden."],
        ["Finalizar", "Estado En Proceso", "Check-out: cierra la orden y dispara los efectos finales."],
    ],
    [42*mm, 46*mm, 82*mm],
)
h2("Pestañas del formulario")
bullets([
    "<b>Evidencias (Fotos):</b> galería de fotos tomadas en el sitio.",
    "<b>Checklist:</b> lista de tareas a verificar; se llena sola según el tipo de servicio.",
    "<b>Instalación / Unidad:</b> datos técnicos (ubicación real, datos de vehículo GPS, panel de alarma, antena/router de internet).",
    "<b>Resolución:</b> check-in/out, duración, notas del trabajo, firma y calificación del cliente.",
    "<b>Equipos y Materiales:</b> productos usados; se descuentan del almacén al finalizar.",
    "<b>Localización:</b> coordenadas de check-in/out y distancia recorrida.",
    "<b>Comunicación:</b> historial de mensajes con el cliente (botón 'Enviar Mensaje').",
])
h2("Vistas disponibles")
p("Las órdenes se pueden ver como <b>Lista</b> (con colores por estado), <b>Kanban</b> (columnas por etapa), "
  "<b>Agenda del Equipo</b> (calendario por fecha programada) y, en análisis, como tabla dinámica y gráfica. "
  "Hay filtros rápidos: Pendientes, Sin asignar, En proceso, Pausados, Programadas hoy, Patrullaje, Mis órdenes, etc.")

# ============ 6 ============
h1("6. Crear una orden manualmente")
p("En <b>Gestión de Servicios &rarr; Nuevo Reporte</b> se abre un asistente. Se llenan:")
bullets([
    "<b>Cliente</b> (obligatorio) y, opcionalmente, su <b>Dirección de Servicio</b> y la <b>Suscripción</b> afectada.",
    "<b>Tipo de Servicio</b> y <b>Prioridad</b>.",
    "<b>Técnico / Patrullero</b> (si se deja vacío, la orden queda en 'Nuevo' sin asignar).",
    "<b>Fecha Programada</b> y la <b>Descripción del Trabajo</b>.",
])
p("Al presionar <b>Crear Orden</b> se genera la orden lista para trabajar. La mayoría de las órdenes, sin embargo, "
  "se crean solas (ver sección 12).")

# ============ 7 ============
h1("7. El portal del técnico (celular)")
p("El técnico de campo <b>no usa el Odoo normal</b>: al iniciar sesión, el sistema lo lleva automáticamente a su "
  "portal móvil simplificado (<font face='Helvetica'>/tech/dashboard</font>), pensado para el celular. "
  "Arriba aparece el encabezado <b>SENTINELA TECH</b> con su nombre y el botón <b>Salir</b>.")
h2("Mi Agenda")
p("La pantalla principal es <b>Mi Agenda</b>: muestra en tarjetas las órdenes asignadas que aún no terminan, "
  "ordenadas por prioridad y hora. Cada tarjeta indica el folio, la hora de la cita (en rojo si va retrasada), "
  "el cliente, la ubicación y unas etiquetas de color con el tipo (Instalación, Reparación, Patrullaje…) y el estado. "
  "Si no hay pendientes, aparece <i>'¡Todo listo! No tienes órdenes pendientes.'</i>")
h2("Trabajar una orden, paso a paso")
bullets([
    "<b>Abrir la orden:</b> muestra los datos del cliente y dos botones grandes — <b>Cómo llegar (Google Maps)</b> y <b>Cómo llegar (Waze)</b> — además del teléfono para llamar con un toque.",
    "<b>Iniciar:</b> con la orden 'Asignada', el técnico toca <b>▶ INICIAR TRABAJO</b>. La orden pasa a 'En Proceso'.",
    "<b>Llenar el reporte</b> en tres pestañas: <b>Resolución</b> (qué se hizo, nombre de quien recibe, firma en pantalla, fotos), <b>Checklist</b> (las tareas del protocolo) y <b>Datos Técnicos</b> (según sea alarma, GPS, CCTV o internet).",
    "<b>Subir fotos:</b> botón <b>📷 SUBIR FOTOS</b> usando la cámara del celular.",
    "<b>Firma:</b> el cliente firma con el dedo en la pantalla; hay opción de <b>Borrar Firma</b> y rehacerla.",
    "<b>Guardar avance:</b> <b>💾 Guardar avance</b> conserva lo capturado sin cerrar la orden.",
    "<b>Finalizar:</b> <b>✓ FINALIZAR SERVICIO</b> cierra la orden (exige firma). Avisa: <i>'al finalizar, la orden se cierra y se avisa a Central. No se puede reabrir desde la app.'</i>",
    "<b>Pausar / Reanudar:</b> botón <b>⏸ PAUSAR</b> (pide motivo y notas) y, si está pausada, <b>▶ REANUDAR TRABAJO</b>.",
    "<b>Requisición a Ventas:</b> si el cliente pide algo extra, el técnico lo escribe en 'Requisición Adicional' y lo envía a Ventas para que cotice.",
])
note("Los datos técnicos cambian según la tecnología: Alarma (panel, cuenta de monitoreo, zonas), GPS (placas, marca, "
     "ICCID/IMEI de la SIM), CCTV (grabador, número de cámaras, disco, acceso remoto) e Internet (antena/MAC, señal en dBm, PPPoE).")

# ============ 8 ============
h1("8. Patrullaje y respuesta a emergencias")
p("El patrullaje es un tipo de orden especial para responder a una alarma o llamada del cliente, con seguimiento en vivo.")
h2("Unidad vs. patrullero")
bullets([
    "El <b>patrullero</b> es la persona (un usuario del sistema).",
    "La <b>unidad de patrulla</b> es lo que se rastrea por GPS: un celular compartido o un vehículo. Se elige al despachar; si no, se usa la unidad por defecto.",
])
h2("Cómo funciona el despacho")
bullets([
    "Se crea la orden de patrullaje (normalmente desde la central de monitoreo al atender una alarma), con prioridad alta y respuesta inmediata.",
    "El patrullero <b>inicia</b> la orden; el sistema empieza a leer su posición desde SentiCar/Traccar y avisa al cliente con el link de rastreo.",
    "Cada <b>3 minutos</b>, el sistema recalcula el tiempo estimado de llegada (ETA) y le avisa al cliente si cambió (hasta un máximo de avisos, para no saturar).",
    "Al llegar, el técnico toca <b>📍 LLEGADA AL SITIO</b>; el sistema valida que esté dentro de la <b>geocerca</b> (~150 m del domicilio) antes de aceptar la llegada.",
])
h2("Modo emergencia")
p("En patrullaje, el portal del técnico muestra una tarjeta roja de <b>Emergencia Activa</b> con la información crítica del sitio: "
  "número de cuenta, <b>zonas activas</b>, <b>contactos de emergencia</b> (con botón para llamar), las <b>palabras clave</b> "
  "de seguridad y un botón para <b>solicitar apoyo / policía</b>.")
h2("Dictamen de la patrulla")
p("Al cerrar, el patrullero registra el <b>dictamen</b>: Sin Novedad, Falsa Alarma, Falla Técnica, Actividad Sospechosa, "
  "Intento de Intrusión, Intrusión Confirmada / Robo, Emergencia Médica o Incendio; y marca si hubo señales de "
  "intrusión forzada y si se avisó a la policía / 911.")

# ============ 9 ============
h1("9. Rastreo en vivo para el cliente (SentiCar)")
p("Cuando el técnico o la patrulla van en camino, el cliente recibe un <b>enlace de rastreo</b> "
  "(/SentiCar/rastreo/&lt;token&gt;) que abre un mapa en vivo, sin necesidad de contraseña ni de instalar nada.")
bullets([
    "El mapa muestra el domicilio destino y la posición de la unidad, que se actualiza cada pocos segundos.",
    "Una tarjeta indica el nombre del técnico/oficial y el estatus ('En camino por SentiCar' o, en emergencia, 'Respuesta de Emergencia').",
    "El enlace deja de funcionar cuando la orden se finaliza o se cancela: aparece <i>'Servicio Completado'</i>.",
    "Es seguro: la clave del enlace es única por orden, así que el cliente solo ve su propio servicio.",
])

# ============ 10 ============
h1("10. El portal del cliente")
p("El cliente puede levantar y dar seguimiento a sus reportes desde su portal:")
bullets([
    "<b>Mis Solicitudes de Soporte</b> (/my/services): lista sus tickets con folio, fecha, problema y estado (Recibido, Asignado, Resuelto).",
    "<b>Levantar Nuevo Ticket</b> (/my/services/new): elige el contrato afectado, describe el problema y marca si es urgente ('¡URGENTE! Sitio sin servicio').",
    "<b>Reporte sin cuenta</b> (/reportar): para quien no tiene portal, ofrece reportar por <b>WhatsApp</b> (la vía más rápida) o entrar al portal si ya tiene cuenta.",
])

# ============ 11 ============
h1("11. Checklist, evidencias y equipos")
h2("Checklist automático")
p("Al crear la orden, el sistema copia las <b>tareas de protocolo</b> que correspondan al tipo de servicio y a la "
  "tecnología del contrato. Así, una instalación de alarma trae sus tareas (instalar panel, probar zonas, instruir al cliente) "
  "y un patrullaje las suyas (revisar perímetro, documentar daños, obtener firma).")
h2("Evidencias fotográficas")
p("El técnico adjunta fotos clasificadas (antes, durante, resultado final, documentos). Quedan guardadas en la orden "
  "como respaldo para auditoría, garantías o incidentes de seguridad.")
h2("Equipos y materiales")
p("Cada producto instalado o consumido se registra con su cantidad y precio. Al <b>finalizar</b> la orden, "
  "esos equipos se <b>descuentan del almacén</b> automáticamente y su costo se suma para medir la rentabilidad del servicio.")

# ============ 12 ============
h1("12. Cómo se generan órdenes automáticamente")
p("La mayoría de las órdenes no se crean a mano: nacen al <b>confirmar una venta</b>. Según el caso:")
table(
    ["Situación en la venta", "Orden que se crea"],
    [
        ["Plan/suscripción nueva (alarma, GPS, internet)", "Instalación inicial, enlazada al contrato. (No se crea si el cliente ya tiene ese servicio activo: es renovación.)"],
        ["La venta indica una dirección destino de traslado", "Traslado de domicilio."],
        ["El origen de la venta contiene 'Reactivación'", "Reparación urgente (reconexión)."],
        ["Producto marcado para generar orden de servicio", "El tipo de orden que ese producto define (ej. mantenimiento puntual)."],
    ],
    [80*mm, 90*mm],
)
note("Hay un control anti-duplicados: si la misma venta ya generó una orden en los últimos minutos (doble clic), no se crea otra.")

# ============ 13 ============
h1("13. Mantenimiento preventivo automático")
p("Cada contrato puede tener una <b>frecuencia de mantenimiento</b> (mensual, trimestral, semestral, anual). "
  "Un proceso automático corre <b>cada día</b> y, para cada contrato activo cuyo próximo mantenimiento ya venció:")
bullets([
    "Crea una orden de <b>Mantenimiento Preventivo</b> (si no hay ya una abierta para ese contrato).",
    "Avanza la fecha del próximo mantenimiento según la frecuencia, para no regenerar la orden todos los días.",
])
p("Cuando el técnico finaliza el mantenimiento, el siguiente se reprograma a partir de la fecha real del servicio.")

# ============ 14 ============
h1("14. Flujo de cotización (apoyo de Ventas)")
p("Si en el sitio el técnico detecta que se necesita un equipo adicional, <b>pausa</b> la orden con la causa "
  "'requiere cotización' (o usa la 'Requisición Adicional' del portal). El sistema entonces:")
bullets([
    "Crea una <b>tarea/actividad para el vendedor</b>, con los datos técnicos del sitio para que elija equipos compatibles.",
    "Notifica al vendedor para que arme la cotización y la comunique al cliente.",
    "Si el cliente acepta, la nueva venta genera una orden complementaria; si no, la orden queda pausada o se cancela.",
])

# ============ 15 ============
h1("15. Reporte de servicio al cliente")
p("Tras finalizar, el flujo de entrega del reporte es:")
bullets([
    "<b>Autorizar Reporte:</b> un supervisor de central revisa la orden y la autoriza, evitando enviar reportes incompletos.",
    "<b>Enviar Reporte al Cliente:</b> el sistema arma un PDF con folio, fechas, técnico, fotos antes/después, firma, dictamen (si es patrullaje) y notas, y lo envía por el canal que el cliente prefiera (WhatsApp, correo, etc.).",
])

# ============ 16 ============
h1("16. Integración con otros módulos")
table(
    ["Módulo", "Cómo se relaciona con Gestión de Servicios"],
    [
        ["Ventas (sale)", "Confirmar una venta crea órdenes FSM automáticamente (instalación, traslado, reparación)."],
        ["Suscripciones", "La orden se enlaza al contrato del cliente: hereda su tecnología y, al finalizar, le vuelca los datos técnicos y reprograma su mantenimiento. El retiro cierra el contrato."],
        ["Monitoreo (alarmas)", "Al atender una alarma, la central despacha una orden de patrullaje con la info del evento (cuenta, zonas, contactos)."],
        ["SentiCar / Traccar", "Provee la posición GPS en vivo de la unidad para el ETA y el mapa de rastreo del cliente."],
        ["Inventario (stock)", "Al finalizar, descuenta del almacén los equipos y materiales usados en la orden."],
        ["Mensajería / chatter", "Cada orden lleva su bitácora de seguimiento, actividades y mensajes con el cliente."],
    ],
    [40*mm, 130*mm],
)

# ============ 17 ============
h1("17. Preguntas frecuentes")
h3("No puedo finalizar la orden, ¿por qué?")
p("Falta la <b>firma del cliente</b>. Es obligatoria para cerrar cualquier orden.")
h3("El técnico dice que no lo deja confirmar la llegada en un patrullaje.")
p("Debe estar <b>físicamente cerca</b> del domicilio (dentro de ~150 m) y tener la <b>ubicación del celular activada</b>. "
  "El sistema valida la geocerca antes de aceptar la llegada.")
h3("El cliente abre el link de rastreo y dice 'Servicio Completado'.")
p("Es normal: el rastreo deja de estar disponible en cuanto la orden se <b>finaliza o cancela</b>.")
h3("Confirmé una venta y no se creó la orden de instalación.")
p("Si el cliente ya tenía ese servicio activo, el sistema lo trata como <b>renovación</b> y no crea instalación. "
  "Para una visita en ese caso, crea la orden a mano desde 'Nuevo Reporte'.")
h3("¿Quién ve cada cosa?")
p("Los <b>técnicos</b> ven solo su portal móvil y sus órdenes; los <b>gestores</b> ven todas las órdenes, rutas, "
  "análisis y configuración desde la oficina.")

sp(14)
E.append(HRFlowable(width="100%", thickness=1, color=NAVY))
sp(6)
E.append(Paragraph("Sentinela &mdash; Manual de Usuario · Gestión de Servicios (sentinela_fsm v18.0.1.8.9). "
                   "Documento operativo interno. Junio 2026.", styles["Note"]))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(20*mm, 12*mm, "Sentinela · Gestión de Servicios")
    canvas.drawRightString(190*mm, 12*mm, "Pág. %d" % doc.page)
    canvas.setStrokeColor(LIGHT)
    canvas.line(20*mm, 15*mm, 190*mm, 15*mm)
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4,
                        leftMargin=20*mm, rightMargin=20*mm,
                        topMargin=18*mm, bottomMargin=20*mm,
                        title="Manual de Usuario - Gestión de Servicios (FSM)",
                        author="Sentinela")
doc.build(E, onFirstPage=lambda c, d: None, onLaterPages=footer)
print("PDF generado:", OUT)
