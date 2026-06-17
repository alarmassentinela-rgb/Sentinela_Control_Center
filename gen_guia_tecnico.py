# -*- coding: utf-8 -*-
"""Guía Rápida del Técnico (celular) — sentinela_fsm. 1-2 páginas."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    ListFlowable, ListItem, HRFlowable, Image
)

OUT = "/mnt/c/Users/dell/DellCli/GUIA_RAPIDA_TECNICO_FSM.pdf"
LOGO = "/mnt/c/Users/dell/DellCli/logo_sentinela_master.jpg"

NAVY = colors.HexColor("#1a237e")
BLUE = colors.HexColor("#1565c0")
LIGHT = colors.HexColor("#e8eaf6")
GREY = colors.HexColor("#555555")
GREEN = colors.HexColor("#2e7d32")
RED = colors.HexColor("#c62828")
AMBER = colors.HexColor("#ff8f00")
AMBERBG = colors.HexColor("#fff8e1")
REDBG = colors.HexColor("#ffebee")

st = getSampleStyleSheet()
def S(n, **k): st.add(ParagraphStyle(name=n, **k))

S("GTitle", fontName="Helvetica-Bold", fontSize=18, textColor=NAVY, leading=21)
S("GSub", fontName="Helvetica", fontSize=10, textColor=GREY, leading=13)
S("H", fontName="Helvetica-Bold", fontSize=11.5, textColor=BLUE, spaceBefore=7, spaceAfter=3, leading=14)
S("B", fontName="Helvetica", fontSize=9.3, textColor=colors.black, leading=12.5, alignment=TA_JUSTIFY)
S("Li", fontName="Helvetica", fontSize=9.3, textColor=colors.black, leading=12.5)
S("Box", fontName="Helvetica", fontSize=9, textColor=colors.black, leading=12.5)
S("BoxB", fontName="Helvetica-Bold", fontSize=9.3, textColor=colors.black, leading=12.5)
S("StepN", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white, alignment=1, leading=13)
S("StepT", fontName="Helvetica-Bold", fontSize=9.8, textColor=NAVY, leading=12)
S("StepB", fontName="Helvetica", fontSize=8.8, textColor=colors.black, leading=11.5)

E = []

def steps(items):
    """items = list of (title, body) -> numbered step boxes."""
    rows = []
    for i, (t, b) in enumerate(items, 1):
        num = Table([[Paragraph(str(i), st["StepN"])]], colWidths=[8*mm], rowHeights=[8*mm])
        num.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),BLUE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                 ("ROUNDEDCORNERS",[4,4,4,4])]))
        txt = [Paragraph(t, st["StepT"]), Paragraph(b, st["StepB"])]
        rows.append([num, txt])
    tb = Table(rows, colWidths=[10*mm, 160*mm])
    tb.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),
                            ("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(1,0),(1,-1),5)]))
    E.append(tb)

def callout(title, lines, bg, border):
    body = [Paragraph("<b>%s</b>" % title, st["BoxB"])]
    for l in lines:
        body.append(Paragraph("• " + l, st["Box"]))
    t = Table([[body]], colWidths=[170*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),("BOX",(0,0),(-1,-1),0.8,border),
                           ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
                           ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    E.append(t)
    E.append(Spacer(1, 5))

# ---- Encabezado (logo Sentinela + título) ----
logo = Image(LOGO, width=56*mm, height=56*mm*512/1440)  # conserva proporción 1440x512
logo.hAlign = "LEFT"
hd = Table([[logo,
             Paragraph("Guía Rápida del Técnico<br/><font size=12 color='#1a237e'><b>Gestión de Servicios</b></font>"
                       "<br/>App de campo (celular)", st["GSub"])]],
           colWidths=[90*mm, 80*mm])
hd.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,0),(1,0),"RIGHT")]))
E.append(hd)
E.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceBefore=4, spaceAfter=8))

E.append(Paragraph("Entras a <b>sentinela.mx</b> con tu usuario y la app te lleva sola a <b>Mi Agenda</b>. Ahí ves tus órdenes del día "
                   "(las urgentes primero; la hora en <font color='#c62828'>rojo</font> = vas retrasado). "
                   "Toca una orden para trabajarla.", st["B"]))
E.append(Spacer(1, 4))

E.append(Paragraph("PASO A PASO EN CADA ORDEN", st["H"]))
steps([
    ("Llegar al domicilio",
     "Usa <b>Cómo llegar (Google Maps)</b> o <b>(Waze)</b>. El botón verde de teléfono llama al cliente con un toque."),
    ("Iniciar el trabajo (Check-in)",
     "Con la orden en 'Asignado', toca <b>▶ INICIAR TRABAJO</b>. Se registra tu hora y ubicación, y al cliente le avisa que vas en camino."),
    ("Llenar el reporte (3 pestañas)",
     "<b>Resolución:</b> qué hiciste, nombre de quien recibe y su parentesco. &nbsp; "
     "<b>Checklist:</b> palomea cada tarea del protocolo. &nbsp; "
     "<b>Datos Técnicos:</b> según el servicio (panel/zonas, placas/IMEI, antena/señal, DVR/cámaras)."),
    ("Subir fotos",
     "Botón <b>📷 SUBIR FOTOS</b>. Toma evidencia del antes, durante y el resultado final."),
    ("Firma del cliente",
     "El cliente firma con el dedo en la pantalla. Si quedó mal, usa <b>Borrar Firma</b> y rehaz. <b>Sin firma NO se puede finalizar.</b>"),
    ("Guardar o Finalizar",
     "<b>💾 Guardar avance</b> conserva todo sin cerrar. &nbsp; <b>✓ FINALIZAR SERVICIO</b> cierra la orden y avisa a Central "
     "(ya no se puede reabrir desde la app)."),
])

E.append(Paragraph("SI TIENES QUE PARAR", st["H"]))
callout("⏸ PAUSAR la orden", [
    "Toca <b>⏸ PAUSAR</b>, elige el motivo y escribe notas.",
    "Para retomarla: <b>▶ REANUDAR TRABAJO</b>.",
    "¿El cliente pidió algo extra? Escríbelo en <b>Requisición Adicional</b> y mándalo a Ventas para que cotice.",
], AMBERBG, AMBER)

E.append(Paragraph("SI ES PATRULLAJE / EMERGENCIA", st["H"]))
callout("🚨 Respuesta de emergencia", [
    "Verás la tarjeta roja <b>Emergencia Activa</b> con cuenta, <b>zonas</b>, <b>contactos</b> (botón LLAMAR) y <b>palabras clave</b>.",
    "Al llegar toca <b>📍 LLEGADA AL SITIO</b>: tu celular debe tener <b>ubicación activada</b> y estar a menos de ~150 m del domicilio.",
    "Cierra con el <b>Dictamen</b> (Sin Novedad, Falsa Alarma, Intrusión, etc.) y marca si hubo intrusión forzada y si se avisó a Policía/911.",
    "El cliente ve tu llegada en vivo en el mapa SentiCar mientras la orden esté abierta.",
], REDBG, RED)

E.append(Paragraph("REGLAS DE ORO", st["H"]))
E.append(ListFlowable([
    ListItem(Paragraph("<b>Sin firma no cierras.</b> Es obligatoria para finalizar.", st["Li"]), value=None),
    ListItem(Paragraph("<b>Activa el GPS del celular</b> al iniciar y al confirmar llegada.", st["Li"]), value=None),
    ListItem(Paragraph("<b>Captura los datos técnicos reales</b> (panel, IMEI, señal…): se copian al contrato del cliente.", st["Li"]), value=None),
    ListItem(Paragraph("<b>Toma fotos siempre.</b> Son tu respaldo ante cualquier reclamo.", st["Li"]), value=None),
    ListItem(Paragraph("Finalizar = definitivo. Si dudas, usa <b>Guardar avance</b>.", st["Li"]), value=None),
], bulletType="bullet", bulletColor=GREEN, leftIndent=14, bulletFontSize=8))

E.append(Spacer(1, 8))
E.append(HRFlowable(width="100%", thickness=1, color=NAVY))
E.append(Spacer(1, 3))
E.append(Paragraph("Sentinela · Gestión de Servicios (sentinela_fsm v18.0.1.8.9) — Guía rápida de campo. Junio 2026.",
                   st["GSub"]))

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                        topMargin=15*mm, bottomMargin=15*mm,
                        title="Guía Rápida del Técnico - Gestión de Servicios", author="Sentinela")
doc.build(E)
print("PDF:", OUT)
