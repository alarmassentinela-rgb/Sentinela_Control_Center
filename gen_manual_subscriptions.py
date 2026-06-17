# -*- coding: utf-8 -*-
"""Manual de Usuario del módulo sentinela_subscriptions (Suscripciones) en PDF.
Lleva versión del módulo + fecha de publicación + control de versiones del manual."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    ListFlowable, ListItem, HRFlowable, Image
)

OUT = "/mnt/c/Users/dell/DellCli/MANUAL_USUARIO_SUSCRIPCIONES.pdf"
LOGO = "/mnt/c/Users/dell/DellCli/logo_sentinela_master.jpg"

MODULO_VER = "18.0.1.3.99"
FECHA_PUB = "17 de junio de 2026"

NAVY = colors.HexColor("#1a237e")
BLUE = colors.HexColor("#1565c0")
LIGHT = colors.HexColor("#e8eaf6")
GREY = colors.HexColor("#555555")

styles = getSampleStyleSheet()
def S(name, **kw): styles.add(ParagraphStyle(name=name, **kw))

S("MCover", fontName="Helvetica-Bold", fontSize=30, textColor=NAVY, alignment=TA_CENTER, leading=36)
S("MCoverSub", fontName="Helvetica", fontSize=15, textColor=GREY, alignment=TA_CENTER, leading=22)
S("MCoverSmall", fontName="Helvetica", fontSize=10, textColor=GREY, alignment=TA_CENTER, leading=16)
S("MVerBox", fontName="Helvetica-Bold", fontSize=11, textColor=NAVY, alignment=TA_CENTER, leading=16)
S("MH1", fontName="Helvetica-Bold", fontSize=16, textColor=NAVY, spaceBefore=14, spaceAfter=7, leading=20)
S("MH2", fontName="Helvetica-Bold", fontSize=12.5, textColor=BLUE, spaceBefore=9, spaceAfter=4, leading=15)
S("MH3", fontName="Helvetica-Bold", fontSize=10.5, textColor=colors.black, spaceBefore=6, spaceAfter=2, leading=13)
S("MBody", fontName="Helvetica", fontSize=10, textColor=colors.black, alignment=TA_JUSTIFY, leading=14.5, spaceAfter=5)
S("MBul", fontName="Helvetica", fontSize=10, textColor=colors.black, leading=14)
S("MNote", fontName="Helvetica-Oblique", fontSize=9.5, textColor=GREY, leading=13, spaceAfter=4)
S("MCell", fontName="Helvetica", fontSize=8.8, textColor=colors.black, leading=11.5)
S("MCellH", fontName="Helvetica-Bold", fontSize=8.8, textColor=colors.white, leading=11.5)
S("MTOC", fontName="Helvetica", fontSize=10.5, textColor=colors.black, leading=18)

E = []
def h1(t): E.append(Paragraph(t, styles["MH1"]))
def h2(t): E.append(Paragraph(t, styles["MH2"]))
def h3(t): E.append(Paragraph(t, styles["MH3"]))
def p(t): E.append(Paragraph(t, styles["MBody"]))
def note(t): E.append(Paragraph("ℹ️ " + t, styles["MNote"]))
def sp(h=6): E.append(Spacer(1, h))
def bullets(items):
    li = [ListItem(Paragraph(x, styles["MBul"]), leftIndent=6) for x in items]
    E.append(ListFlowable(li, bulletType="bullet", bulletColor=BLUE, leftIndent=14, bulletFontSize=7))
def table(header, rows, widths):
    data = [[Paragraph(c, styles["MCellH"]) for c in header]]
    for r in rows:
        data.append([Paragraph(c, styles["MCell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#cccccc")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),3.5),("BOTTOMPADDING",(0,0),(-1,-1),3.5),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f4f6fb")]),
    ]))
    E.append(t); sp(6)

# ===== PORTADA =====
E.append(Spacer(1, 50))
_logo = Image(LOGO, width=95*mm, height=95*mm*512/1440); _logo.hAlign="CENTER"
E.append(_logo)
E.append(Spacer(1, 26))
E.append(Paragraph("Suscripciones", styles["MCover"]))
E.append(Spacer(1, 14))
E.append(HRFlowable(width="55%", thickness=2, color=BLUE, hAlign="CENTER"))
E.append(Spacer(1, 16))
E.append(Paragraph("Manual de Usuario", styles["MCoverSub"]))
E.append(Paragraph("Facturación recurrente y aprovisionamiento de servicios", styles["MCoverSub"]))
E.append(Spacer(1, 40))
E.append(Paragraph("Internet WISP &bull; Monitoreo de Alarmas &bull; Rastreo GPS", styles["MCoverSmall"]))
E.append(Spacer(1, 36))
_vt = Table([[Paragraph(f"Versión del módulo: {MODULO_VER}", styles["MVerBox"])],
             [Paragraph(f"Fecha de publicación: {FECHA_PUB}", styles["MVerBox"])]],
            colWidths=[110*mm])
_vt.setStyle(TableStyle([("BOX",(0,0),(-1,-1),1,NAVY),("BACKGROUND",(0,0),(-1,-1),LIGHT),
                         ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
                         ("ALIGN",(0,0),(-1,-1),"CENTER")]))
_wrap = Table([[_vt]], colWidths=[170*mm]); _wrap.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER")]))
E.append(_wrap)
E.append(Spacer(1, 8))
E.append(Paragraph("Odoo 18 Community &middot; Sentinela", styles["MCoverSmall"]))
E.append(Paragraph("Consulte la última página (Control de versiones) para confirmar si maneja la edición vigente.",
                   styles["MCoverSmall"]))
E.append(PageBreak())

# ===== ÍNDICE =====
h1("Contenido")
for t in [
    "1.  ¿Qué es el módulo de Suscripciones?",
    "2.  Conceptos básicos",
    "3.  Los dos estados: comercial y técnico",
    "4.  Tipos de servicio y cómo se cobra cada uno",
    "5.  Ciclo de vida de una suscripción",
    "6.  La pantalla de la suscripción",
    "7.  El contrato digital",
    "8.  Aprovisionamiento (Internet, GPS, Alarma)",
    "9.  Matriz de servicios del plan",
    "10. Facturación recurrente",
    "11. Cobro adelantado",
    "12. Cobranza automática",
    "13. Modo cortesía",
    "14. Plazo forzoso y leasing de equipo",
    "15. Asistentes (wizards)",
    "16. Ajustes del módulo",
    "17. Integraciones externas",
    "18. Control de versiones de este manual",
]:
    E.append(Paragraph(t, styles["MTOC"]))
E.append(PageBreak())

# ===== 1 =====
h1("1. ¿Qué es el módulo de Suscripciones?")
p("<b>Suscripciones</b> (módulo <font face='Helvetica-Bold'>sentinela_subscriptions</font>) es el <b>corazón</b> del sistema "
  "de Sentinela. Reemplaza a MASadmin y Argus, y une en un solo lugar dos cosas que antes estaban separadas:")
bullets([
    "<b>La facturación recurrente:</b> genera las cuentas de cada cliente, mes con mes, de forma automática.",
    "<b>El aprovisionamiento técnico:</b> activa, suspende o corta el servicio real del cliente en los equipos "
    "(router de internet, SIM de la alarma, plataforma del GPS) según su estado de pago.",
])
p("Cada cliente tiene una <b>suscripción</b> (también llamada <b>contrato</b>): un registro que concentra su plan, su precio, "
  "su ciclo de cobro, sus datos técnicos, su contrato firmado y el estado del servicio. Cuando una suscripción se suspende "
  "por falta de pago, el módulo corta el servicio en el equipo; cuando el cliente paga, lo reactiva solo.")

h1("2. Conceptos básicos")
table(["Concepto", "Qué significa"],
      [["Suscripción / Contrato", "El registro central de un cliente: plan, precio, ciclo, datos técnicos y estado. Folio tipo SUB-####."],
       ["Plan de servicio", "El producto contratado (ej. 'Internet 10 Mbps', 'Monitoreo Básico', 'Rastreo Vehículo'). Define precio, ciclo y qué servicios incluye."],
       ["Tipo de servicio", "Alarma (monitoreo), Internet (WISP) o GPS (rastreo). Determina qué pestañas y qué aprovisionamiento aplican."],
       ["Ciclo de facturación", "Cada cuánto se cobra: mensual, bimestral, trimestral, semestral o anual."],
       ["Estado comercial", "En qué punto va el contrato: Borrador, Confirmado, Activo, Suspensión, Cancelado, Cerrado."],
       ["Estado técnico", "Si el servicio funciona AHORA en el equipo: Activo, Suspendido (falta de pago) o Corte definitivo."],
       ["Aprovisionamiento", "La acción de activar/suspender/cortar el servicio real en el router, la SIM o la plataforma GPS."]],
      [44*mm, 126*mm])

# ===== 3 =====
h1("3. Los dos estados: comercial y técnico")
p("Una suscripción tiene <b>dos estados que corren en paralelo</b>. Entenderlos evita confusiones:")
h2("Estado comercial (del contrato)")
table(["Estado", "Significado"],
      [["Borrador", "Suscripción nueva, en preparación. No cobra ni provisiona."],
       ["Pendiente de Firma", "El contrato está redactado y enviado; falta que el cliente lo firme."],
       ["Confirmado", "Contrato firmado (digital o en papel). Listo para activar el servicio."],
       ["Activo", "El servicio funciona y se factura cada ciclo automáticamente."],
       ["Suspensión", "Pausado (por falta de pago o decisión del operador). Sigue siendo cliente."],
       ["Cancelado / Cerrado", "Baja definitiva del contrato."]],
      [40*mm, 130*mm])
h2("Estado técnico (del servicio en el equipo)")
table(["Estado técnico", "Qué pasa en el equipo del cliente"],
      [["Activo / En línea", "El servicio funciona con normalidad (navega, la alarma reporta, el GPS rastrea)."],
       ["Suspendido (falta de pago)", "Internet: el cliente se conecta pero queda en 'walled-garden' (solo ve la página de pago). Alarma/GPS: la SIM se corta y deja de reportar."],
       ["Corte definitivo", "El servicio se eliminó por completo (retiro). El cliente ya no puede ni conectarse."]],
      [44*mm, 126*mm])
note("Pueden no coincidir a propósito: si el operador otorga una <b>prórroga</b>, el contrato puede estar en 'Suspensión' "
     "pero el servicio seguir técnicamente 'Activo' hasta que venza la prórroga.")

# ===== 4 =====
h1("4. Tipos de servicio y cómo se cobra cada uno")
p("El módulo maneja tres tipos de servicio y cada uno se cobra de forma distinta. Esta diferencia es importante al revisar "
  "una factura:")
table(["Servicio", "Cómo se fija el precio", "Cantidad en la factura", "Aprovisionamiento"],
      [["Alarma", "El precio ya es el del <b>periodo completo</b> (planes de 3/6/12 meses).",
        "Cantidad = 1 (el precio del periodo ya está dentro).", "SIM floLIVE: se corta al suspender, se reactiva al pagar."],
       ["Internet (WISP)", "El precio es la <b>tarifa mensual</b>.",
        "Cantidad = nº de meses del ciclo (ej. semestral = 6).", "Router MikroTik: secret PPPoE + perfil; suspensión = walled-garden."],
       ["GPS", "Tarifa <b>mensual por equipo</b> (una sub puede tener varios equipos).",
        "Cantidad = meses × equipos activos (los suspendidos no se cobran).", "SentiCar/Traccar + SIM floLIVE (modo vehículo)."]],
      [24*mm, 52*mm, 52*mm, 42*mm])

# ===== 5 =====
h1("5. Ciclo de vida de una suscripción")
p("El recorrido típico de un alta, paso a paso:")
bullets([
    "<b>1. Alta (Borrador):</b> se crea la suscripción, se elige el cliente y el plan; el sistema deriva sus servicios y datos.",
    "<b>2. Contrato:</b> se redacta el contrato y se envía a firma (digital) o se marca como firmado en papel → <b>Confirmado</b>.",
    "<b>3. Activación:</b> se activa el servicio → el módulo da de alta al cliente en el equipo (router/SIM/plataforma) y queda <b>Activo</b>.",
    "<b>4. Facturación:</b> cada ciclo se genera la factura/remisión automáticamente y se adelanta la próxima fecha de cobro.",
    "<b>5. Cobranza:</b> si no paga, recibe recordatorios y, pasados los días configurados, se <b>suspende</b> solo; al pagar, se <b>reactiva</b> solo.",
    "<b>6. Baja:</b> por fin de contrato o retiro, se cierra/cancela y se corta el servicio definitivamente.",
])

# ===== 6 =====
h1("6. La pantalla de la suscripción")
p("Se llega desde el menú <b>Suscripciones &rarr; Operaciones &rarr; Contratos</b>. El menú de <b>Configuración</b> contiene "
  "Planes de Servicio, Routers MikroTik, Perfiles MikroTik y Plantillas de Contratos.")
h2("Barra de estado y botones de acción")
p("Arriba se ve la barra de estado (Borrador → Confirmado → Activo → Suspensión…) y los botones cambian según la etapa. "
  "Los principales:")
table(["Botón", "Aparece / sirve para"],
      [["Confirmar Contrato / Enviar a Firmar", "Avanza de Borrador a Confirmado (o manda el contrato a firma electrónica)."],
       ["Activar Servicio", "Activa el servicio en el equipo y pone la sub en Activo."],
       ["Suspender", "Suspende el servicio (walled-garden o corte de SIM)."],
       ["Reconexión / Re-Activar", "Reactiva el servicio tras un pago o suspensión."],
       ["Cobro Adelantado", "Abre el asistente para cobrar varios meses por adelantado."],
       ["Otorgar Prórroga", "Da días de gracia sin cortar el servicio."],
       ["Baja Definitiva / Cancelar", "Termina el contrato y corta el servicio."],
       ["Redactar / Descargar / Enviar Contrato", "Genera, descarga o manda a firmar el contrato digital."]],
      [54*mm, 116*mm])
h2("Pestañas del formulario")
bullets([
    "<b>Monitoreo / Alarma:</b> número de cuenta, clave de seguridad, clave maestra, estado técnico.",
    "<b>GPS:</b> equipos (IMEI, placa, modelo), plataforma, registro en SentiCar, portal del transportista, comandos SMS y diagnóstico de SIM.",
    "<b>Internet / MikroTik:</b> router, perfil, modo (PPPoE/estático/DHCP), IP, usuario y contraseña PPPoE, antena y router del cliente.",
    "<b>Diagnóstico (internet):</b> validar navegación, ping, señal de la antena y tráfico en vivo.",
    "<b>Facturación y Plazos:</b> modo de facturación, fechas, ciclo, días para suspender, contrato forzoso.",
    "<b>Instalación:</b> dirección, coordenadas (geocodificadas o verificadas) y mapa del sitio.",
    "<b>Contrato Digital:</b> estado de firma, vista previa y acciones del contrato.",
    "<b>Notas:</b> descripción interna.",
])
note("Hay un botón <b>Facturas</b> (arriba a la derecha) que lleva a todas las facturas de esa suscripción. "
     "El formulario bloquea la edición de datos sensibles una vez que el contrato está activo (los desbloquea un supervisor).")

# ===== 7 =====
h1("7. El contrato digital")
p("Cada plan usa una <b>plantilla de contrato</b> (HTML) que el sistema rellena con los datos del cliente y de la suscripción. "
  "El flujo es:")
bullets([
    "<b>Redactar / Actualizar Contrato:</b> genera el documento con los datos actuales y permite previsualizarlo.",
    "<b>Descargar PDF:</b> obtiene el contrato en PDF con el logo y el folio.",
    "<b>Enviar para Firma Electrónica:</b> manda al cliente un enlace para firmar en línea; el estado pasa a 'Pendiente de Firma' y luego a 'Firmado'.",
    "<b>Marcar como Firmado en Papel:</b> alternativa cuando el cliente firma físicamente.",
])
note("Las plantillas usan solo marcadores tipo <font face='Courier'>{{ }}</font>; no admiten condicionales <font face='Courier'>{% %}</font>. "
     "Las partes variables (como la cláusula del equipo) las arma el sistema automáticamente.")

# ===== 8 =====
h1("8. Aprovisionamiento (Internet, GPS, Alarma)")
h2("Internet WISP")
p("Al <b>activar</b> internet, el módulo crea/actualiza el usuario PPPoE (secret) en el router MikroTik y le asigna el perfil del "
  "plan (que define la velocidad). Al <b>suspender</b>, NO desconecta al cliente: lo deja conectado pero le cambia el perfil a uno "
  "suspendido (<b>walled-garden</b>), de modo que solo ve la página de pago. Al pagar, vuelve al perfil de su plan.")
bullets([
    "<b>Router:</b> el MikroTik físico (CCR) destino del aprovisionamiento, con su IP, credenciales y servidor PPPoE.",
    "<b>Perfil MikroTik:</b> define la velocidad de subida/bajada del plan.",
])
h2("GPS")
p("Una suscripción GPS puede tener <b>varios equipos</b>. El módulo permite:")
bullets([
    "<b>Registrar en SentiCar:</b> crea la cuenta del cliente en SentiCar/Traccar y da de alta cada IMEI.",
    "<b>Cortar/activar la SIM (floLIVE):</b> en modo vehículo, la SIM de datos se corta al suspender y se reactiva al pagar (la SIM del cliente, en modo móvil, no se toca).",
    "<b>Enviar comandos SMS al GPS:</b> con plantillas por familia de equipo (servidor, APN, ubicar, intervalo), el operador elige y se arma solo.",
    "<b>Diagnóstico de SIM y link de rastreo temporal:</b> consulta estado/ubicación de la SIM y genera enlaces de rastreo para terceros (con vigencia configurable).",
])
h2("Alarma / Monitoreo")
p("La suscripción de alarma guarda el número de cuenta, la clave de seguridad (voz) y la clave maestra del panel, y se enlaza a "
  "la SIM floLIVE por la que el panel reporta al centro de monitoreo. Suspender corta la SIM; reactivar la restaura.")

# ===== 9 =====
h1("9. Matriz de servicios del plan")
p("Cada plan define, mediante una <b>matriz de servicios</b>, qué prestaciones incluye (por ejemplo: patrullaje por evento, "
  "mantenimiento preventivo) y cuáles son extra con su precio. Al crear la suscripción o cambiarle el plan, esos servicios se "
  "<b>derivan automáticamente</b> a la suscripción y aparecen en el contrato (incluido / no incluido / precio por evento).")

# ===== 10 =====
h1("10. Facturación recurrente")
p("Un proceso automático diario genera las <b>pre-facturas</b> de los clientes cuya fecha de próxima renovación llegó. Al publicar "
  "la factura, el sistema <b>adelanta la próxima fecha de cobro</b> un ciclo completo, de modo que no se regenera dos veces.")
bullets([
    "<b>Ciclo multi-mes:</b> en planes trimestrales/semestrales/anuales se cobra el bloque completo de meses en una sola factura.",
    "<b>Factura o remisión:</b> los clientes que timbran reciben factura CFDI; los que no, reciben una remisión. El cobro y la cobranza funcionan igual en ambos casos.",
])

# ===== 11 =====
h1("11. Cobro adelantado")
p("Con el botón <b>Cobro Adelantado</b> se cobran varios meses de una sola vez:")
bullets([
    "Se indica cuántos meses y el sistema calcula el total; se genera una factura en borrador.",
    "Al <b>publicar</b> esa factura, la próxima fecha de cobro se empuja hacia adelante esos meses.",
    "Si la factura se cancela o se le hace nota de crédito, la fecha de cobro <b>se revierte</b> proporcionalmente.",
])

# ===== 12 =====
h1("12. Cobranza automática")
p("El módulo gestiona la cobranza de principio a fin, sin intervención manual:")
bullets([
    "<b>Recordatorios de pago:</b> se envían avisos al cliente conforme se acerca y pasa la fecha de vencimiento.",
    "<b>Auto-suspensión por mora:</b> pasados los <b>días para suspender</b> configurados en la suscripción, el servicio se suspende solo.",
    "<b>Prórroga:</b> el operador puede otorgar días de gracia; mientras esté vigente, no se envían recordatorios ni se suspende.",
    "<b>Reactivación al pagar:</b> cuando se registra el pago de la factura, el servicio se reconecta automáticamente y se avisa al cliente.",
])
note("Los <b>días para suspender</b> son configurables por suscripción (por ejemplo, más días para un cliente VIP). "
     "El modo cortesía queda excluido de toda la cobranza (ver siguiente sección).")

# ===== 13 =====
h1("13. Modo cortesía")
p("El <b>modo cortesía</b> mantiene el servicio activo y funcionando, pero <b>no factura, no cobra, no envía recordatorios y no "
  "suspende</b>. Sirve para periodos de prueba, promociones o clientes especiales. Solo un <b>gestor</b> puede activarlo. "
  "Mientras la suscripción esté en cortesía, queda fuera de todo el ciclo de facturación y cobranza.")

# ===== 14 =====
h1("14. Plazo forzoso y leasing de equipo")
h2("Plazo forzoso (permanencia)")
p("Una suscripción puede marcarse como <b>contrato forzoso</b> con un periodo de compromiso (en meses) y una <b>penalización</b> "
  "por cancelación anticipada. El sistema calcula la fecha de fin del compromiso y, si el cliente se da de baja antes, aplica la penalización.")
h2("Leasing de equipo")
p("Algunos equipos (sobre todo GPS) se ofrecen en <b>arrendamiento</b>: el cliente paga un plazo y al terminar el equipo pasa a ser "
  "suyo. Un proceso automático avisa antes del fin del leasing y, al cumplirse el plazo, cambia la suscripción al <b>plan posterior "
  "al leasing</b> y marca el equipo como propiedad del cliente.")

# ===== 15 =====
h1("15. Asistentes (wizards)")
table(["Asistente", "Para qué sirve"],
      [["Cerrar / Suspender", "Suspende o cancela la suscripción con un motivo; si hay plazo forzoso, calcula y factura la penalización."],
       ["Prórroga / Extensión", "Otorga días de gracia (fecha límite + motivo) sin cortar el servicio."],
       ["Traslado", "Cambio de domicilio del cliente; genera la cotización del servicio de traslado."],
       ["Cobro Adelantado", "Cobra varios meses por adelantado y adelanta la fecha de renovación."],
       ["Generar / Confirmar contrato", "Genera el contrato y avisa antes de sobrescribir uno existente."],
       ["Selección de equipo", "Vincula el equipo comprado en una venta a la suscripción (marca, modelo, serie/IMEI)."],
       ["Tráfico MikroTik", "Muestra en vivo IP y velocidad de subida/bajada del cliente de internet."]],
      [48*mm, 122*mm])

# ===== 16 =====
h1("16. Ajustes del módulo")
p("En <b>Ajustes</b> se configuran las credenciales e integraciones:")
bullets([
    "<b>floLIVE / Connecta:</b> usuario (correo) y token para administrar las SIM de datos.",
    "<b>SentiCar / Traccar:</b> URL de la API (LAN), usuario/contraseña, URL pública del panel, base del portal del transportista e IDs de administradores.",
    "<b>Reconciliación y enlaces:</b> auto-corregir desajustes, máximo de horas de los links de rastreo y grupo raíz en SentiCar.",
])

# ===== 17 =====
h1("17. Integraciones externas")
table(["Integración", "Para qué"],
      [["MikroTik (routers)", "Alta/suspensión de internet (secret PPPoE, perfiles, walled-garden) y lectura de tráfico."],
       ["floLIVE (Connecta)", "Activar/cortar SIM de datos (alarma y GPS), diagnóstico y envío de SMS."],
       ["SentiCar / Traccar", "Plataforma de rastreo GPS: alta de equipos, grupos por cliente y links de rastreo."],
       ["Firma digital", "Envío del contrato a firma electrónica desde el portal del cliente."],
       ["CFDI / Prodigia", "Timbrado de facturas; los clientes que no timbran reciben remisión."]],
      [42*mm, 128*mm])

# ===== 18 =====
h1("18. Control de versiones de este manual")
p("Este manual corresponde a una versión concreta del módulo. Si el módulo se actualiza, actualice también este documento y "
  "agregue un renglón a la tabla.")
table(["Fecha", "Versión módulo", "Cambios de esta edición"],
      [[FECHA_PUB, MODULO_VER, "Edición inicial del manual de usuario: facturación recurrente, aprovisionamiento (internet/alarma/GPS), contrato digital, cobranza, cobro adelantado, cortesía, plazo forzoso/leasing y asistentes."]],
      [38*mm, 30*mm, 102*mm])
sp(10)
E.append(HRFlowable(width="100%", thickness=1, color=NAVY))
sp(4)
E.append(Paragraph(f"Sentinela &mdash; Manual de Usuario · Suscripciones (sentinela_subscriptions v{MODULO_VER}). "
                   f"Publicado el {FECHA_PUB}. Documento operativo interno.", styles["MNote"]))

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8); canvas.setFillColor(GREY)
    canvas.drawString(20*mm, 12*mm, f"Sentinela · Suscripciones · v{MODULO_VER} · {FECHA_PUB}")
    canvas.drawRightString(190*mm, 12*mm, "Pág. %d" % doc.page)
    canvas.setStrokeColor(LIGHT); canvas.line(20*mm, 15*mm, 190*mm, 15*mm)
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                        topMargin=18*mm, bottomMargin=20*mm,
                        title=f"Manual de Usuario - Suscripciones (v{MODULO_VER})", author="Sentinela")
doc.build(E, onLaterPages=footer)
print("PDF:", OUT)
