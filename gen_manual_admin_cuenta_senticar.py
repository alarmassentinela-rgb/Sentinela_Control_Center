# -*- coding: utf-8 -*-
"""Manual del Administrador de Cuenta (cliente) de SentiCar — PDF con logo + capturas reales.
Dirigido a clientes tipo KAWAC: administran SU propia cuenta (manager), no son super-admin."""
import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, ListFlowable, ListItem, Image, HRFlowable)
from PIL import Image as PILImage

ROOT = "/mnt/c/Users/dell/DellCli"
OUT = os.path.join(ROOT, "MANUAL_ADMIN_CUENTA_SENTICAR.pdf")
LOGO_NAVY = os.path.join(ROOT, "logo_senticar_pro.png")
LOGO_WHITE = os.path.join(ROOT, "logo_senticar_pro_inverted.png")

NAVY  = colors.HexColor("#1a237e")
GREEN = colors.HexColor("#2e9e5b")
GREY  = colors.HexColor("#555555")
LIGHT = colors.HexColor("#eef0fa")
OKG   = colors.HexColor("#e8f5e9")
WARN  = colors.HexColor("#fff8e1")
REDBG = colors.HexColor("#fdecea")

ss = getSampleStyleSheet()
st = {
 'cover_t': ParagraphStyle('ct', parent=ss['Title'], fontName='Helvetica-Bold', fontSize=28,
                           textColor=colors.white, alignment=TA_CENTER, leading=32),
 'cover_s': ParagraphStyle('cs', parent=ss['Normal'], fontSize=14, textColor=colors.HexColor("#c5cae9"),
                           alignment=TA_CENTER, leading=20),
 'h1': ParagraphStyle('h1', parent=ss['Heading1'], fontName='Helvetica-Bold', fontSize=17,
                      textColor=NAVY, spaceBefore=14, spaceAfter=7, leading=21),
 'h2': ParagraphStyle('h2', parent=ss['Heading2'], fontName='Helvetica-Bold', fontSize=12.5,
                      textColor=GREEN, spaceBefore=9, spaceAfter=3, leading=16),
 'body': ParagraphStyle('body', parent=ss['Normal'], fontSize=10.5, leading=15.5,
                        alignment=TA_JUSTIFY, spaceAfter=5),
 'bullet': ParagraphStyle('bu', parent=ss['Normal'], fontSize=10.5, leading=14.5),
 'cap': ParagraphStyle('cap', parent=ss['Normal'], fontSize=8.5, textColor=GREY,
                       alignment=TA_CENTER, leading=11, spaceBefore=3),
 'cell': ParagraphStyle('cell', parent=ss['Normal'], fontSize=9.5, leading=13),
 'cellb': ParagraphStyle('cellb', parent=ss['Normal'], fontSize=9.5, leading=13, fontName='Helvetica-Bold'),
 'toc': ParagraphStyle('toc', parent=ss['Normal'], fontSize=11.5, leading=20, textColor=NAVY),
 'small': ParagraphStyle('sm', parent=ss['Normal'], fontSize=8.5, textColor=GREY, leading=11, alignment=TA_CENTER),
}

F = []
def S(h=6): F.append(Spacer(1, h))
def P(t, s='body'): F.append(Paragraph(t, st[s]))
def H1(t): F.append(Paragraph(t, st['h1']))
def H2(t): F.append(Paragraph(t, st['h2']))
def bullets(items, sym='•'):
    F.append(ListFlowable([ListItem(Paragraph(i, st['bullet']), leftIndent=10) for i in items],
                          bulletType='bullet', start=sym, leftIndent=16, bulletColor=NAVY))
    F.append(S(4))

def shot(fname, caption, w_cm=14.5):
    path = os.path.join(ROOT, fname)
    iw, ih = PILImage.open(path).size
    w = w_cm * cm
    h = w * ih / iw
    img = Image(path, width=w, height=h); img.hAlign = 'CENTER'
    box = Table([[img]], colWidths=[w])
    box.setStyle(TableStyle([('BOX',(0,0),(-1,-1),0.8,colors.HexColor("#cfd2e0")),
                             ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
                             ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
    box.hAlign = 'CENTER'
    F.append(S(4)); F.append(box)
    F.append(Paragraph(caption, st['cap'])); F.append(S(8))

def callout(title, txt, bg=OKG, bc=GREEN):
    inner = [Paragraph("<b>"+title+"</b>", st['cellb']), Paragraph(txt, st['cell'])]
    t = Table([[inner]], colWidths=[16*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('BOX',(0,0),(-1,-1),0.6,bc),
                           ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
                           ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    F.append(t); F.append(S(8))

# ---------------- PORTADA ----------------
def cover_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, LETTER[0], LETTER[1], fill=1, stroke=0)
    # banda verde inferior
    canvas.setFillColor(GREEN)
    canvas.rect(0, 0, LETTER[0], 0.5*cm, fill=1, stroke=0)
    canvas.restoreState()

iw, ih = PILImage.open(LOGO_WHITE).size
lw = 9.5*cm; lh = lw*ih/iw
logo = Image(LOGO_WHITE, width=lw, height=lh); logo.hAlign='CENTER'
F.append(Spacer(1, 5.2*cm))
F.append(logo)
F.append(Spacer(1, 1.4*cm))
F.append(Paragraph("Manual del Administrador de Cuenta", st['cover_t']))
F.append(Spacer(1, 0.5*cm))
F.append(Paragraph("Guía completa para administrar tu cuenta, equipos y usuarios<br/>"
                   "en la plataforma de rastreo GPS SentiCar", st['cover_s']))
F.append(Spacer(1, 3.0*cm))
F.append(Paragraph("radar.senticar.com&nbsp;&nbsp;·&nbsp;&nbsp;App SentiCar (Android)", st['cover_s']))
F.append(Spacer(1, 0.3*cm))
F.append(Paragraph("Rastreo Inteligente GPS — Un servicio de Sentinela", st['cover_s']))
F.append(PageBreak())

# ---------------- ÍNDICE ----------------
H1("Contenido")
toc = ["1.  Tu rol: Administrador de tu cuenta",
       "2.  Cómo entrar (web y app)",
       "3.  El mapa y tu lista de equipos",
       "4.  Ver un equipo en detalle",
       "5.  Seguir un equipo en el mapa",
       "6.  Compartir la ubicación (enlace temporal)",
       "7.  Reportes (recorridos, resumen, viajes)",
       "8.  Geo-Zonas y notificaciones",
       "9.  Administrar los usuarios de tu cuenta",
       "10. Editar un equipo",
       "11. Tu cuenta: cambiar y recuperar contraseña",
       "12. Lo que tu rol no incluye (y por qué)",
       "13. Soporte y contacto"]
for t in toc:
    F.append(Paragraph(t, st['toc']))
F.append(PageBreak())

# ---------------- 1. ROL ----------------
H1("1. Tu rol: Administrador de tu cuenta")
P("Bienvenido a <b>SentiCar</b>, tu plataforma de rastreo GPS. Tu usuario tiene perfil de "
  "<b>Administrador de tu propia cuenta</b>. Esto significa que mandas sobre todo lo tuyo, "
  "pero solo sobre lo tuyo:")
bullets([
 "<b>Ves y gestionas únicamente tus equipos</b> y los de las cuentas que cuelgan de ti.",
 "<b>Puedes crear usuarios</b> dentro de tu cuenta (choferes, supervisores, socios) y decidir qué ven.",
 "<b>No ves a otros clientes</b> de SentiCar, ni ellos te ven a ti. Tu información es privada.",
 "<b>No eres «super administrador»</b> de la plataforma: ese rol es exclusivo de Sentinela, que opera el servidor.",
])
callout("En pocas palabras",
        "Eres el dueño de tu cuenta: administras tus equipos y a tu propia gente (cuenta padre e hijos), "
        "sin tocar ni ver lo de nadie más. Es tu espacio privado y seguro dentro de SentiCar.")

# ---------------- 2. ENTRAR ----------------
H1("2. Cómo entrar")
H2("Desde la computadora (recomendado para administrar)")
bullets([
 "Abre tu navegador y entra a <b>radar.senticar.com</b>.",
 "Escribe tu <b>correo</b> (es tu usuario) y tu <b>contraseña</b>.",
 "Presiona <b>INICIAR SESIÓN</b>.",
])
H2("Desde el celular")
P("Instala la app <b>SentiCar</b> (Android) o entra desde el navegador del teléfono a la misma dirección. "
  "La pantalla es la misma, adaptada a tu pantalla.")
shot("man_shot_login.png", "Pantalla de inicio de sesión de SentiCar. Si olvidaste tu contraseña, usa «Reiniciar contraseña» (ver sección 11).")

# ---------------- 3. MAPA ----------------
H1("3. El mapa y tu lista de equipos")
P("Al entrar verás el <b>mapa</b> y, a la izquierda, la <b>lista de tus equipos</b>. Abajo está el menú "
  "principal: <b>Mapa</b>, <b>Reportes</b>, <b>Ajustes</b> y <b>Cuenta</b>.")
bullets([
 "<b>En línea</b> (verde): el equipo está reportando ahora mismo.",
 "<b>Hace X días/horas</b> (rojo): es la última vez que reportó (apagado, sin señal o sin batería).",
 "El ícono de <b>batería</b> a la derecha indica la carga del equipo (en celulares/rastreadores que la reportan).",
 "Usa <b>«Buscar Dispositivos»</b> arriba para filtrar cuando tengas muchos equipos.",
])
shot("man_shot_mapa.png", "Vista principal: lista de equipos a la izquierda, mapa a la derecha y menú inferior.")

# ---------------- 4. DETALLE ----------------
H1("4. Ver un equipo en detalle")
P("Haz clic (o toca) un equipo en la lista o en el mapa. Se abre una <b>tarjeta</b> con su información:")
bullets([
 "<b>Hora ajustada:</b> fecha y hora del último reporte.",
 "<b>Dirección / Calle:</b> toca «Mostrar calle» para ver la dirección.",
 "<b>Velocidad</b> y <b>Distancia total</b> recorrida.",
])
P("En la parte baja de la tarjeta hay <b>botones de acción</b> (de izquierda a derecha): más detalles, "
  "<b>recorrido</b>, <b>Compartir</b> (ícono de avión), <b>editar</b> y eliminar.")
shot("man_shot_equipo.png", "Tarjeta del equipo. El ícono de avión (✈) es «Compartir» — genera un enlace temporal (sección 6).")

# ---------------- 5. SEGUIR ----------------
H1("5. Seguir un equipo en el mapa")
P("Para que el mapa <b>siga solo</b> a un equipo en movimiento (sin que tengas que recentrar a mano), "
  "ve a <b>Ajustes &gt; Preferencias</b> y activa la casilla <b>«Seguir»</b>. También puedes elegir qué "
  "datos aparecen en la tarjeta (Información popup) y agrupar marcadores cuando tienes muchos equipos juntos.")
shot("man_shot_preferencias.png", "Ajustes > Preferencias. Activa «Seguir» para que el mapa siga al equipo seleccionado.")

# ---------------- 6. COMPARTIR ----------------
H1("6. Compartir la ubicación (enlace temporal)")
P("Puedes compartir la ubicación en vivo de <b>un</b> equipo con quien quieras, <b>sin darle una cuenta</b> "
  "y por un <b>tiempo limitado</b> (ideal para que el dueño de una carga siga a su unidad).")
bullets([
 "Selecciona el equipo para abrir su tarjeta.",
 "Toca el botón <b>Compartir</b> (ícono de avión ✈).",
 "Elige <b>cuánto tiempo</b> estará activo el enlace.",
 "Copia el enlace y envíalo por WhatsApp, correo, etc.",
])
callout("Privacidad",
        "El enlace muestra SOLO ese equipo y deja de funcionar cuando vence el tiempo. Quien lo abre no ve "
        "el resto de tu flota ni necesita usuario ni contraseña.", bg=LIGHT, bc=NAVY)

# ---------------- 7. REPORTES ----------------
H1("7. Reportes")
P("En el menú <b>Reportes</b> obtienes el historial de tus equipos. Tipos disponibles:")
bullets([
 "<b>Recorrido / Repetición de ruta:</b> el trayecto sobre el mapa.",
 "<b>Resumen:</b> distancia, velocidad máxima/promedio y horas de motor por día.",
 "<b>Viajes</b> y <b>Paradas:</b> dónde y cuánto tiempo se detuvo.",
 "<b>Eventos</b> y <b>Geo-Zonas:</b> entradas/salidas y alertas.",
])
H2("Cómo generar un reporte")
bullets([
 "Elige el o los <b>Dispositivos</b> (o un Grupo).",
 "Elige el <b>Período</b> (Hoy, ayer, esta semana o un rango de fechas).",
 "Presiona <b>MOSTRAR</b>. Puedes <b>exportar a Excel</b> el resultado.",
])
shot("man_shot_reportes.png", "Menú de Reportes: elige dispositivo, período y presiona MOSTRAR.")

# ---------------- 8. GEOZONAS ----------------
H1("8. Geo-Zonas y notificaciones")
P("Una <b>Geo-Zona</b> es un área en el mapa (por ejemplo, tu base o el domicilio de un cliente). "
  "Puedes recibir un <b>aviso</b> cuando un equipo entra o sale de ella.")
bullets([
 "<b>Ajustes &gt; Geo-Zonas:</b> dibuja la zona sobre el mapa y ponle nombre.",
 "<b>Ajustes &gt; Notificaciones:</b> elige qué eventos te avisan y por qué medio (en la app, correo, etc.).",
])

# ---------------- 9. USUARIOS ----------------
H1("9. Administrar los usuarios de tu cuenta")
P("Como administrador de tu cuenta puedes crear <b>usuarios propios</b> (choferes, supervisores, un socio) "
  "y decidir qué equipos ve cada uno. Esos usuarios cuelgan de ti y <b>nunca ven otras cuentas</b>.")
H2("Crear un usuario")
bullets([
 "Ve a <b>Ajustes &gt; Usuarios</b>.",
 "Toca el botón <b>+</b> (abajo a la derecha).",
 "Escribe <b>nombre</b>, <b>correo</b> (será su usuario) y una <b>contraseña</b>.",
 "Guarda. Luego, en el usuario, vincula los <b>equipos o grupos</b> que quieres que vea.",
])
callout("Importante",
        "Deja la casilla <b>«Administrador»</b> SIEMPRE apagada para los usuarios que crees. Tus usuarios "
        "deben ser de tu cuenta, no administradores de la plataforma.", bg=WARN, bc=colors.HexColor("#f9a825"))
shot("man_shot_usuarios.png", "Ajustes > Usuarios. El botón + (abajo a la derecha) crea un nuevo usuario de tu cuenta.")

# ---------------- 10. EDITAR EQUIPO ----------------
H1("10. Editar un equipo")
P("Puedes cambiar el <b>nombre</b> de un equipo para reconocerlo fácil (por ejemplo «Camioneta Ventas» "
  "en lugar de un número). Ve a <b>Ajustes &gt; Dispositivos</b>, elige el equipo y edita el campo "
  "<b>Nombre</b>. El <b>Identificador</b> (IMEI o ID del aparato) no se cambia: lo configura Sentinela.")
shot("man_shot_editar_equipo.png", "Edición de un equipo: cambia el Nombre; el Identificador lo gestiona Sentinela.")

# ---------------- 11. CONTRASEÑA ----------------
H1("11. Tu cuenta: cambiar y recuperar contraseña")
H2("Cambiar tu contraseña (estando dentro)")
bullets([
 "Ve a <b>Cuenta</b> (o Ajustes &gt; Cuenta).",
 "Escribe la nueva contraseña en el campo <b>Contraseña</b>.",
 "Presiona <b>GUARDAR</b>.",
])
shot("senticar_shot_cuenta.png", "Ajustes > Cuenta: escribe la nueva contraseña y GUARDAR.")
H2("Olvidé mi contraseña")
bullets([
 "En la pantalla de inicio, toca <b>«Reiniciar contraseña»</b>.",
 "Escribe tu <b>correo</b> (el mismo de tu usuario) y envía.",
 "Te llegará un correo de <b>SentiCar</b> con un enlace para crear una contraseña nueva.",
])
callout("Nota",
        "El correo de recuperación llega desde una dirección automática (no-reply): no respondas a ese "
        "mensaje. Para cualquier duda usa los contactos de soporte (sección 13).", bg=LIGHT, bc=NAVY)

# ---------------- 12. LIMITES ----------------
H1("12. Lo que tu rol no incluye (y por qué)")
P("Para proteger tu seguridad y la de la plataforma, tu cuenta tiene algunos límites:")
bullets([
 "<b>No envías comandos directos al hardware</b> del GPS (por ejemplo, corte de motor). Si necesitas un "
 "comando especial, Sentinela lo realiza por ti.",
 "<b>No ves ni administras otras cuentas</b> de clientes; solo la tuya y la de tus usuarios.",
 "<b>No administras el servidor</b> ni la configuración global de SentiCar.",
])
callout("Esto te protege",
        "Estos límites evitan errores costosos y garantizan que nadie ajeno vea tus unidades. Tú mandas en "
        "tu cuenta; Sentinela cuida la infraestructura.")

# ---------------- 13. SOPORTE ----------------
H1("13. Soporte y contacto")
sup = [[Paragraph("<b>Plataforma web</b>", st['cellb']), Paragraph("radar.senticar.com", st['cell'])],
       [Paragraph("<b>App móvil</b>", st['cellb']), Paragraph("SentiCar (Android)", st['cell'])],
       [Paragraph("<b>WhatsApp / Soporte</b>", st['cellb']), Paragraph("+52 868 822 5875", st['cell'])],
       [Paragraph("<b>Correo</b>", st['cellb']), Paragraph("gps@senticar.com (automático, no-reply)", st['cell'])]]
t = Table(sup, colWidths=[5*cm, 11*cm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),LIGHT),('BOX',(0,0),(-1,-1),0.6,colors.HexColor("#cfd2e0")),
                       ('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor("#dfe2ee")),
                       ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                       ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                       ('LEFTPADDING',(0,0),(-1,-1),10)]))
F.append(t); S(10)
P("Gracias por confiar en <b>SentiCar — Rastreo Inteligente GPS</b>, un servicio de Sentinela.")

# ---------------- PIE / NUMERACION ----------------
def later(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GREY)
    canvas.drawString(2*cm, 1.1*cm, "SentiCar — Manual del Administrador de Cuenta")
    canvas.drawRightString(LETTER[0]-2*cm, 1.1*cm, "Página %d" % (doc.page-1))
    canvas.setStrokeColor(colors.HexColor("#dfe2ee"))
    canvas.line(2*cm, 1.5*cm, LETTER[0]-2*cm, 1.5*cm)
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=LETTER, topMargin=1.8*cm, bottomMargin=2*cm,
                        leftMargin=2*cm, rightMargin=2*cm, title="Manual del Administrador de Cuenta — SentiCar",
                        author="Sentinela")
doc.build(F, onFirstPage=cover_bg, onLaterPages=later)
print("PDF generado:", OUT, os.path.getsize(OUT), "bytes")
