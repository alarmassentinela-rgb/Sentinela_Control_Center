# -*- coding: utf-8 -*-
"""Account Administrator Manual (client) for SentiCar — EN. PDF with logo + real screenshots."""
import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, ListFlowable, ListItem, Image)
from PIL import Image as PILImage

ROOT = "/mnt/c/Users/dell/DellCli"
OUT = os.path.join(ROOT, "SENTICAR_ACCOUNT_ADMIN_MANUAL_EN.pdf")
LOGO_NAVY = os.path.join(ROOT, "logo_senticar_pro.png")
LOGO_WHITE = os.path.join(ROOT, "logo_senticar_pro_inverted.png")

NAVY=colors.HexColor("#1a237e"); GREEN=colors.HexColor("#2e9e5b"); GREY=colors.HexColor("#555555")
LIGHT=colors.HexColor("#eef0fa"); OKG=colors.HexColor("#e8f5e9"); WARN=colors.HexColor("#fff8e1")

ss=getSampleStyleSheet()
st={
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
}
F=[]
def S(h=6): F.append(Spacer(1,h))
def P(t,s='body'): F.append(Paragraph(t, st[s]))
def H1(t): F.append(Paragraph(t, st['h1']))
def H2(t): F.append(Paragraph(t, st['h2']))
def bullets(items, sym='•'):
    F.append(ListFlowable([ListItem(Paragraph(i, st['bullet']), leftIndent=10) for i in items],
                          bulletType='bullet', start=sym, leftIndent=16, bulletColor=NAVY)); F.append(S(4))
def shot(fname, caption, w_cm=14.5):
    path=os.path.join(ROOT, fname); iw,ih=PILImage.open(path).size; w=w_cm*cm; h=w*ih/iw
    img=Image(path, width=w, height=h); img.hAlign='CENTER'
    box=Table([[img]], colWidths=[w])
    box.setStyle(TableStyle([('BOX',(0,0),(-1,-1),0.8,colors.HexColor("#cfd2e0")),
                             ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
                             ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
    box.hAlign='CENTER'; F.append(S(4)); F.append(box); F.append(Paragraph(caption, st['cap'])); F.append(S(8))
def callout(title, txt, bg=OKG, bc=GREEN):
    inner=[Paragraph("<b>"+title+"</b>", st['cellb']), Paragraph(txt, st['cell'])]
    t=Table([[inner]], colWidths=[16*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('BOX',(0,0),(-1,-1),0.6,bc),
                           ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
                           ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    F.append(t); F.append(S(8))

# COVER
def cover_bg(c, d):
    c.saveState(); c.setFillColor(NAVY); c.rect(0,0,LETTER[0],LETTER[1], fill=1, stroke=0)
    c.setFillColor(GREEN); c.rect(0,0,LETTER[0],0.5*cm, fill=1, stroke=0); c.restoreState()
iw,ih=PILImage.open(LOGO_WHITE).size; lw=9.5*cm; lh=lw*ih/iw
logo=Image(LOGO_WHITE, width=lw, height=lh); logo.hAlign='CENTER'
F.append(Spacer(1,5.2*cm)); F.append(logo); F.append(Spacer(1,1.4*cm))
F.append(Paragraph("Account Administrator Manual", st['cover_t'])); F.append(Spacer(1,0.5*cm))
F.append(Paragraph("A complete guide to managing your account, devices and users<br/>"
                   "on the SentiCar GPS tracking platform", st['cover_s']))
F.append(Spacer(1,3.0*cm))
F.append(Paragraph("radar.senticar.com&nbsp;&nbsp;·&nbsp;&nbsp;SentiCar app (Android)", st['cover_s']))
F.append(Spacer(1,0.3*cm))
F.append(Paragraph("Smart GPS Tracking — A Sentinela service", st['cover_s']))
F.append(PageBreak())

# TOC
H1("Contents")
for t in ["1.  Your role: Administrator of your account",
          "2.  How to sign in (web and app)",
          "3.  The map and your device list",
          "4.  Viewing a device in detail",
          "5.  Following a device on the map",
          "6.  Sharing a location (temporary link)",
          "7.  Reports (routes, summary, trips)",
          "8.  Geofences and notifications",
          "9.  Managing the users of your account",
          "10. Editing a device",
          "11. Your account: changing and recovering your password",
          "12. What your role does not include (and why)",
          "13. Support and contact"]:
    F.append(Paragraph(t, st['toc']))
F.append(PageBreak())

# 1
H1("1. Your role: Administrator of your account")
P("Welcome to <b>SentiCar</b>, your GPS tracking platform. Your user has the role of "
  "<b>Administrator of your own account</b>. This means you are in charge of everything that is yours, "
  "but only of what is yours:")
bullets([
 "<b>You see and manage only your devices</b> and those of the accounts that hang below yours.",
 "<b>You can create users</b> within your account (drivers, supervisors, partners) and decide what each one sees.",
 "<b>You do not see other SentiCar customers</b>, and they do not see you. Your information is private.",
 "<b>You are not a “super administrator”</b> of the platform: that role belongs only to Sentinela, which operates the server.",
])
callout("In short",
        "You own your account: you manage your devices and your own people (parent account and children), "
        "without touching or seeing anyone else’s. It is your private, secure space inside SentiCar.")

# 2
H1("2. How to sign in")
H2("From a computer (recommended for management)")
bullets(["Open your browser and go to <b>radar.senticar.com</b>.",
         "Enter your <b>email</b> (this is your username) and your <b>password</b>.",
         "Press <b>LOGIN</b>."])
H2("From your phone")
P("Install the <b>SentiCar</b> app (Android) or open the same address in your phone’s browser. "
  "The screen is the same, adapted to your display.")
shot("en_shot_login.png", "SentiCar sign-in screen. If you forgot your password, use “Reset Password” (see section 11).")

# 3
H1("3. The map and your device list")
P("After signing in you will see the <b>map</b> and, on the left, the <b>list of your devices</b>. "
  "At the bottom is the main menu: <b>Map</b>, <b>Reports</b>, <b>Settings</b> and <b>Account</b>.")
bullets(["<b>Online</b> (green): the device is reporting right now.",
         "<b>X days/hours ago</b> (red): the last time it reported (off, no signal or no battery).",
         "The <b>battery</b> icon on the right shows the device charge (on units that report it).",
         "Use <b>“Search Devices”</b> at the top to filter when you have many units."])
shot("en_shot_mapa.png", "Main view: device list on the left, map on the right, menu at the bottom.")

# 4
H1("4. Viewing a device in detail")
P("Click (or tap) a device in the list or on the map. A <b>card</b> opens with its information:")
bullets(["<b>Fix Time:</b> date and time of the last report.",
         "<b>Address:</b> tap “Show Address” to see the street.",
         "<b>Speed</b> and <b>Total Distance</b> traveled."])
P("At the bottom of the card there are <b>action buttons</b> (left to right): more details, "
  "<b>route/replay</b>, <b>Share</b> (paper-plane icon), <b>edit</b> and delete.")
shot("en_shot_equipo.png", "Device card. The paper-plane icon (✈) is “Share” — it creates a temporary link (section 6).")

# 5
H1("5. Following a device on the map")
P("To make the map <b>follow</b> a moving device on its own (so you don’t have to re-center it), go to "
  "<b>Settings &gt; Preferences</b> and turn on the <b>“Follow”</b> checkbox. You can also choose which "
  "data appears on the card (popup info) and group markers when many devices are close together.")
shot("en_shot_preferencias.png", "Settings > Preferences. Turn on “Follow” so the map follows the selected device.")

# 6
H1("6. Sharing a location (temporary link)")
P("You can share the live location of <b>one</b> device with anyone, <b>without giving them an account</b> "
  "and for a <b>limited time</b> (ideal so a cargo owner can follow their unit).")
bullets(["Select the device to open its card.",
         "Tap the <b>Share</b> button (paper-plane icon ✈).",
         "Choose <b>how long</b> the link will stay active.",
         "Copy the link and send it via WhatsApp, email, etc."])
callout("Privacy",
        "The link shows ONLY that device and stops working when the time expires. Whoever opens it cannot "
        "see the rest of your fleet and does not need a username or password.", bg=LIGHT, bc=NAVY)

# 7
H1("7. Reports")
P("In the <b>Reports</b> menu you get the history of your devices. Available types:")
bullets(["<b>Route / Route replay:</b> the path drawn on the map.",
         "<b>Summary:</b> distance, max/average speed and engine hours per day.",
         "<b>Trips</b> and <b>Stops:</b> where and how long it stopped.",
         "<b>Events</b> and <b>Geofences:</b> entries/exits and alerts."])
H2("How to generate a report")
bullets(["Choose the <b>Device(s)</b> (or a Group).",
         "Choose the <b>Period</b> (Today, yesterday, this week or a date range).",
         "Press <b>SHOW</b>. You can <b>export the result to Excel</b>."])
shot("en_shot_reportes.png", "Reports menu: choose device, period and press SHOW.")

# 8
H1("8. Geofences and notifications")
P("A <b>Geofence</b> is an area on the map (for example, your base or a customer’s address). "
  "You can receive an <b>alert</b> when a device enters or leaves it.")
bullets(["<b>Settings &gt; Geofences:</b> draw the area on the map and name it.",
         "<b>Settings &gt; Notifications:</b> choose which events alert you and through which channel (in-app, email, etc.)."])

# 9
H1("9. Managing the users of your account")
P("As the administrator of your account you can create <b>your own users</b> (drivers, supervisors, a partner) "
  "and decide which devices each one sees. Those users hang below you and <b>never see other accounts</b>.")
H2("Create a user")
bullets(["Go to <b>Settings &gt; Users</b>.",
         "Tap the <b>+</b> button (bottom right).",
         "Enter a <b>name</b>, <b>email</b> (it will be their username) and a <b>password</b>.",
         "Save. Then, on the user, link the <b>devices or groups</b> you want them to see."])
callout("Important",
        "Always leave the <b>“Admin”</b> checkbox OFF for the users you create. Your users should belong to "
        "your account, not be administrators of the platform.", bg=WARN, bc=colors.HexColor("#f9a825"))
shot("en_shot_usuarios.png", "Settings > Users. The + button (bottom right) creates a new user of your account.")

# 10
H1("10. Editing a device")
P("You can change a device’s <b>name</b> so you recognize it easily (for example, “Sales Van” instead of a "
  "number). Go to <b>Settings &gt; Devices</b>, choose the device and edit the <b>Name</b> field. The "
  "<b>Identifier</b> (the unit’s IMEI or ID) is not changed: Sentinela sets it.")
shot("en_shot_editar_equipo.png", "Editing a device: change the Name; the Identifier is managed by Sentinela.")

# 11
H1("11. Your account: changing and recovering your password")
H2("Change your password (while signed in)")
bullets(["Go to <b>Account</b> (or Settings &gt; Account).",
         "Type the new password in the <b>Password</b> field.",
         "Press <b>SAVE</b>."])
shot("en_shot_cuenta.png", "Settings > Account: type the new password and SAVE.")
H2("Forgot my password")
bullets(["On the sign-in screen, tap <b>“Reset Password”</b>.",
         "Enter your <b>email</b> (the same as your username) and submit.",
         "You will receive an email from <b>SentiCar</b> with a link to create a new password."])
callout("Note",
        "The recovery email comes from an automated address (no-reply): do not reply to that message. "
        "For any questions use the support contacts (section 13).", bg=LIGHT, bc=NAVY)

# 12
H1("12. What your role does not include (and why)")
P("To protect your security and the platform’s, your account has a few limits:")
bullets(["<b>You do not send direct commands to the GPS hardware</b> (for example, engine cut-off). If you "
         "need a special command, Sentinela performs it for you.",
         "<b>You do not see or manage other customer accounts</b>; only yours and your users’.",
         "<b>You do not administer the server</b> or SentiCar’s global configuration."])
callout("This protects you",
        "These limits prevent costly mistakes and ensure no outsider sees your units. You are in charge of "
        "your account; Sentinela takes care of the infrastructure.")

# 13
H1("13. Support and contact")
sup=[[Paragraph("<b>Web platform</b>", st['cellb']), Paragraph("radar.senticar.com", st['cell'])],
     [Paragraph("<b>Mobile app</b>", st['cellb']), Paragraph("SentiCar (Android)", st['cell'])],
     [Paragraph("<b>WhatsApp / Support</b>", st['cellb']), Paragraph("+52 868 822 5875", st['cell'])],
     [Paragraph("<b>Email</b>", st['cellb']), Paragraph("gps@senticar.com (automated, no-reply)", st['cell'])]]
t=Table(sup, colWidths=[5*cm,11*cm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),LIGHT),('BOX',(0,0),(-1,-1),0.6,colors.HexColor("#cfd2e0")),
                       ('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor("#dfe2ee")),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                       ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LEFTPADDING',(0,0),(-1,-1),10)]))
F.append(t); S(10)
P("Thank you for trusting <b>SentiCar — Smart GPS Tracking</b>, a Sentinela service.")

def later(c, d):
    c.saveState(); c.setFont('Helvetica',8); c.setFillColor(GREY)
    c.drawString(2*cm,1.1*cm,"SentiCar — Account Administrator Manual")
    c.drawRightString(LETTER[0]-2*cm,1.1*cm,"Page %d"%(d.page-1))
    c.setStrokeColor(colors.HexColor("#dfe2ee")); c.line(2*cm,1.5*cm,LETTER[0]-2*cm,1.5*cm); c.restoreState()

doc=SimpleDocTemplate(OUT, pagesize=LETTER, topMargin=1.8*cm, bottomMargin=2*cm, leftMargin=2*cm,
                      rightMargin=2*cm, title="SentiCar — Account Administrator Manual", author="Sentinela")
doc.build(F, onFirstPage=cover_bg, onLaterPages=later)
print("PDF:", OUT, os.path.getsize(OUT), "bytes")
