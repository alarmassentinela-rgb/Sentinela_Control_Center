#!/usr/bin/env python3
"""
Crea/actualiza la PAGINA PRINCIPAL (/) del sitio SentiCar (website id=5) en Odoo prod.

Problema que resuelve: senticar.com/ hace 303 -> /shop porque el website SentiCar
NO tiene su propia pagina '/' (solo cae en la generica vacia). Los otros 4 sitios
corporativos (sentinela.mx, aleasystems.io, etc.) si tienen su page '/' propia y
renderizan 200. Este script replica ese patron para SentiCar:
  1. Crea (o reusa) una vista QWeb primary key='website.homepage' website_id=5.
  2. Crea (o reusa) website.page url='/' website_id=5 -> esa vista, publicada.
  3. Escribe el arch con la landing profesional.

Idempotente: re-ejecutar solo reescribe el arch / re-publica.
Objetivo de la pagina: posicionar la PLATAFORMA (CTA dominante = acceder/rastrear),
con embudo secundario a la tienda (/shop) y a WhatsApp.
"""
import xmlrpc.client

URL = 'http://192.168.3.2:8070'
DB = 'Sentinela_V18'
USER = 'api_user'
PWD = 'SentinelaBot2026!'
WEBSITE_ID = 5

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USER, PWD, {})
assert uid, "Auth fallida"
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')


def ex(model, method, args, kw=None):
    return models.execute_kw(DB, uid, PWD, model, method, args, kw or {})


# ---------------------------------------------------------------------------
# La landing. Arch QWeb: t-call website.layout (header/footer/menu del sitio).
# CSS propio con prefijo .sc- (el website SentiCar no tiene tema instalado).
# ---------------------------------------------------------------------------
ARCH = """<t name="Home" t-name="website.homepage">
  <t t-call="website.layout">
    <t t-set="pageName" t-value="'homepage'"/>
    <div id="wrap" class="oe_structure">
      <style>
        .sc-wrap{font-family:inherit;color:#0a2540}
        .sc-sec{padding:84px 0}
        .sc-sec-sm{padding:56px 0}
        .sc-container{max-width:1140px;margin:0 auto;padding:0 18px}
        .sc-btn{display:inline-block;border-radius:50px;padding:14px 34px;font-weight:700;text-decoration:none;margin:6px 8px 6px 0;transition:.2s;border:2px solid transparent}
        .sc-btn-primary{background:#00c3ff;color:#06243a}
        .sc-btn-primary:hover{background:#00a6d6;color:#06243a;text-decoration:none}
        .sc-btn-light{background:#fff;color:#0a2540}
        .sc-btn-light:hover{background:#eef6ff;color:#0a2540;text-decoration:none}
        .sc-btn-outline{border-color:rgba(255,255,255,.85);color:#fff}
        .sc-btn-outline:hover{background:#fff;color:#0a2540;text-decoration:none}
        .sc-btn-wa{background:#25D366;color:#fff}
        .sc-btn-wa:hover{background:#1ebe5b;color:#fff;text-decoration:none}
        .sc-hero{background:linear-gradient(135deg,#0a2540 0%,#0066cc 58%,#00a6d6 100%);color:#fff;padding:96px 0 88px}
        .sc-hero h1{font-size:3.3rem;font-weight:900;line-height:1.05;margin:0 0 14px}
        .sc-hero .sc-lead{font-size:1.25rem;opacity:.95;max-width:620px;margin:0 0 28px}
        .sc-kicker{display:inline-block;background:rgba(255,255,255,.15);color:#fff;border-radius:50px;padding:6px 16px;font-weight:600;font-size:.85rem;letter-spacing:.04em;margin-bottom:18px}
        .sc-strip{background:#0a2540;color:#fff}
        .sc-strip .sc-num{font-size:1.6rem;font-weight:800;color:#00c3ff}
        .sc-strip .sc-lbl{opacity:.8;font-size:.95rem}
        .sc-h2{font-size:2.1rem;font-weight:800;margin:0 0 10px}
        .sc-tag{color:#0066cc;font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:.82rem}
        .sc-card{background:#fff;border:1px solid #e8eef5;border-radius:16px;padding:30px;height:100%;transition:.25s}
        .sc-card:hover{transform:translateY(-6px);box-shadow:0 18px 40px rgba(10,37,64,.12)}
        .sc-ico{width:58px;height:58px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0066cc,#00c3ff);color:#fff;font-size:1.5rem;margin-bottom:16px}
        .sc-step-n{width:46px;height:46px;border-radius:50%;background:#00c3ff;color:#06243a;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:1.2rem;margin:0 auto 14px}
        .sc-bg-soft{background:#f4f8fc}
        .sc-plan{background:#fff;border:1px solid #e8eef5;border-radius:18px;padding:32px;height:100%;text-align:center}
        .sc-plan-top{border-color:#00c3ff;box-shadow:0 14px 36px rgba(0,102,204,.14)}
        .sc-faq{max-width:820px;margin:0 auto}
        .sc-faq details{background:#fff;border:1px solid #e8eef5;border-radius:12px;padding:16px 20px;margin-bottom:12px}
        .sc-faq summary{font-weight:700;cursor:pointer;list-style:none}
        .sc-faq summary::-webkit-details-marker{display:none}
        .sc-faq p{margin:12px 0 0;color:#48586b}
        .sc-cta{background:linear-gradient(135deg,#0066cc,#00a6d6);color:#fff;border-radius:22px;padding:48px;text-align:center}
        .sc-muted{color:#5a6b7d}
        @media(max-width:768px){.sc-hero h1{font-size:2.3rem}.sc-sec{padding:54px 0}}
      </style>

      <div class="sc-wrap">

        <!-- ======================= HERO ======================= -->
        <section class="sc-hero">
          <div class="sc-container">
            <div class="row align-items-center">
              <div class="col-lg-7">
                <span class="sc-kicker">RASTREO GPS PROFESIONAL</span>
                <h1>Cuida lo que mueve tu negocio, en tiempo real.</h1>
                <p class="sc-lead">SentiCar es la plataforma de rastreo GPS de Sentinela: ubica tus vehiculos y activos al instante, recibe alertas y apaga el motor de forma remota &#8212; desde tu celular o la web.</p>
                <div>
                  <a href="https://radar.senticar.com" class="sc-btn sc-btn-primary"><i class="fa fa-map-marker"/> Acceder a la plataforma</a>
                  <a href="/shop" class="sc-btn sc-btn-light">Contratar GPS</a>
                  <a href="https://wa.me/528688225875" class="sc-btn sc-btn-outline"><i class="fa fa-whatsapp"/> WhatsApp</a>
                </div>
              </div>
              <div class="col-lg-5 d-none d-lg-block text-center">
                <i class="fa fa-map-o" style="font-size:13rem;opacity:.18"/>
              </div>
            </div>
          </div>
        </section>

        <!-- ======================= STRIP ======================= -->
        <section class="sc-strip sc-sec-sm">
          <div class="sc-container">
            <div class="row text-center">
              <div class="col-6 col-md-3 mb-3 mb-md-0"><div class="sc-num">24/7</div><div class="sc-lbl">Monitoreo continuo</div></div>
              <div class="col-6 col-md-3 mb-3 mb-md-0"><div class="sc-num">Tiempo real</div><div class="sc-lbl">Posicion al instante</div></div>
              <div class="col-6 col-md-3"><div class="sc-num">App movil</div><div class="sc-lbl">Android y web</div></div>
              <div class="col-6 col-md-3"><div class="sc-num">Sentinela</div><div class="sc-lbl">Respaldo de seguridad</div></div>
            </div>
          </div>
        </section>

        <!-- ======================= FEATURES ======================= -->
        <section class="sc-sec">
          <div class="sc-container">
            <div class="text-center" style="margin-bottom:46px">
              <span class="sc-tag">Por que SentiCar</span>
              <h2 class="sc-h2">Todo el control de tu flota en una sola plataforma</h2>
            </div>
            <div class="row g-4">
              <div class="col-md-6 col-lg-4 mb-4"><div class="sc-card"><div class="sc-ico"><i class="fa fa-map-marker"/></div><h4>Radar en vivo</h4><p class="sc-muted">Ubicacion exacta de cada unidad con actualizacion en tiempo real sobre el mapa.</p></div></div>
              <div class="col-md-6 col-lg-4 mb-4"><div class="sc-card"><div class="sc-ico"><i class="fa fa-power-off"/></div><h4>Paro de motor</h4><p class="sc-muted">Bloquea el motor de forma remota desde la app en caso de robo. Seguridad total.</p></div></div>
              <div class="col-md-6 col-lg-4 mb-4"><div class="sc-card"><div class="sc-ico"><i class="fa fa-bell"/></div><h4>Alertas y geocercas</h4><p class="sc-muted">Avisos por exceso de velocidad, salida de zona, encendido o desconexion.</p></div></div>
              <div class="col-md-6 col-lg-4 mb-4"><div class="sc-card"><div class="sc-ico"><i class="fa fa-road"/></div><h4>Historial de rutas</h4><p class="sc-muted">Reconstruye el recorrido de cualquier dia: paradas, tiempos y kilometraje.</p></div></div>
              <div class="col-md-6 col-lg-4 mb-4"><div class="sc-card"><div class="sc-ico"><i class="fa fa-mobile"/></div><h4>App SentiCar</h4><p class="sc-muted">Lleva el rastreo en tu bolsillo. Disponible para Android y desde cualquier navegador.</p></div></div>
              <div class="col-md-6 col-lg-4 mb-4"><div class="sc-card"><div class="sc-ico"><i class="fa fa-line-chart"/></div><h4>Reportes y telemetria</h4><p class="sc-muted">Informes de uso, distancia y comportamiento para decidir con datos reales.</p></div></div>
            </div>
          </div>
        </section>

        <!-- ======================= COMO FUNCIONA ======================= -->
        <section class="sc-sec sc-bg-soft">
          <div class="sc-container">
            <div class="text-center" style="margin-bottom:46px">
              <span class="sc-tag">Como funciona</span>
              <h2 class="sc-h2">Empieza a rastrear en 3 pasos</h2>
            </div>
            <div class="row text-center">
              <div class="col-md-4 mb-4"><div class="sc-step-n">1</div><h5>Contratas</h5><p class="sc-muted">Eliges el equipo y el plan que necesitas en nuestra tienda en linea.</p></div>
              <div class="col-md-4 mb-4"><div class="sc-step-n">2</div><h5>Instalamos</h5><p class="sc-muted">Nuestro equipo tecnico instala y activa el GPS en tu vehiculo o activo.</p></div>
              <div class="col-md-4 mb-4"><div class="sc-step-n">3</div><h5>Rastreas</h5><p class="sc-muted">Accedes a la plataforma desde tu celular o la web y tomas el control.</p></div>
            </div>
          </div>
        </section>

        <!-- ======================= PLANES / EQUIPOS ======================= -->
        <section class="sc-sec">
          <div class="sc-container">
            <div class="text-center" style="margin-bottom:46px">
              <span class="sc-tag">Soluciones</span>
              <h2 class="sc-h2">Un plan para cada necesidad</h2>
              <p class="sc-muted">Equipos y planes disponibles en nuestra tienda en linea.</p>
            </div>
            <div class="row g-4">
              <div class="col-md-4 mb-4"><div class="sc-plan"><i class="fa fa-car fa-2x" style="color:#0066cc"/><h4 class="mt-3">Vehiculo particular</h4><p class="sc-muted">Protege tu auto: ubicacion, paro de motor y alertas antirrobo.</p><a href="/shop" class="sc-btn sc-btn-primary">Ver en la tienda</a></div></div>
              <div class="col-md-4 mb-4"><div class="sc-plan sc-plan-top"><i class="fa fa-truck fa-2x" style="color:#0066cc"/><h4 class="mt-3">Flotillas</h4><p class="sc-muted">Administra multiples unidades, conductores y rutas desde un solo tablero.</p><a href="/shop" class="sc-btn sc-btn-primary">Ver en la tienda</a></div></div>
              <div class="col-md-4 mb-4"><div class="sc-plan"><i class="fa fa-cubes fa-2x" style="color:#0066cc"/><h4 class="mt-3">Activos y carga</h4><p class="sc-muted">Rastrea maquinaria, remolques y mercancia de alto valor en movimiento.</p><a href="/shop" class="sc-btn sc-btn-primary">Ver en la tienda</a></div></div>
            </div>
          </div>
        </section>

        <!-- ======================= APP ======================= -->
        <section class="sc-sec sc-bg-soft">
          <div class="sc-container">
            <div class="row align-items-center">
              <div class="col-lg-6 mb-4">
                <span class="sc-tag">App SentiCar</span>
                <h2 class="sc-h2">Tu rastreo, en tu bolsillo</h2>
                <p class="sc-muted">Descarga la app SentiCar para Android y monitorea tus unidades donde estes. Tambien puedes entrar desde cualquier navegador en la plataforma web.</p>
                <a href="/web/content/17577/SentiCar.apk" class="sc-btn sc-btn-primary"><i class="fa fa-android"/> Descargar para Android</a>
                <a href="https://radar.senticar.com" class="sc-btn sc-btn-light">Abrir version web</a>
              </div>
              <div class="col-lg-6 text-center">
                <i class="fa fa-mobile" style="font-size:11rem;color:#0066cc;opacity:.85"/>
              </div>
            </div>
          </div>
        </section>

        <!-- ======================= RESPALDO ======================= -->
        <section class="sc-sec">
          <div class="sc-container text-center">
            <span class="sc-tag">Confianza</span>
            <h2 class="sc-h2">Respaldado por Sentinela</h2>
            <p class="sc-muted" style="max-width:760px;margin:0 auto">SentiCar es la plataforma de rastreo de <strong>Sentinela</strong>, empresa de seguridad electronica y monitoreo. Detras de cada GPS hay un centro de monitoreo y soporte tecnico que responde cuando mas lo necesitas. Tecnologia desarrollada por <strong>Alea Systems</strong>.</p>
          </div>
        </section>

        <!-- ======================= FAQ ======================= -->
        <section class="sc-sec sc-bg-soft">
          <div class="sc-container">
            <div class="text-center" style="margin-bottom:36px">
              <span class="sc-tag">Preguntas frecuentes</span>
              <h2 class="sc-h2">Resolvemos tus dudas</h2>
            </div>
            <div class="sc-faq">
              <details><summary>Que necesito para empezar?</summary><p>Solo contratar el equipo y el plan en la tienda. Nosotros instalamos el GPS y activamos tu cuenta en la plataforma.</p></details>
              <details><summary>Puedo apagar el motor de mi vehiculo?</summary><p>Si. Los equipos con corte de motor permiten bloquear el encendido de forma remota desde la app, ideal en caso de robo.</p></details>
              <details><summary>Funciona en toda la republica?</summary><p>Si. Los equipos operan sobre red celular de cobertura nacional, asi que rastreas tus unidades donde tengan senal.</p></details>
              <details><summary>Necesito instalar algo en mi celular?</summary><p>Puedes usar la app SentiCar para Android o simplemente entrar desde el navegador a la plataforma web. Ambas muestran lo mismo en tiempo real.</p></details>
              <details><summary>Que pasa si tengo varios vehiculos?</summary><p>Administras todas tus unidades desde una sola cuenta, con vistas, alertas y reportes por vehiculo o por flotilla.</p></details>
            </div>
          </div>
        </section>

        <!-- ======================= CTA FINAL ======================= -->
        <section class="sc-sec">
          <div class="sc-container">
            <div class="sc-cta">
              <h2 style="font-weight:800;margin:0 0 10px">Listo para tomar el control?</h2>
              <p style="opacity:.95;margin:0 0 22px">Contrata hoy o habla con un asesor. Te ayudamos a elegir el equipo ideal.</p>
              <a href="/shop" class="sc-btn sc-btn-light">Contratar ahora</a>
              <a href="https://wa.me/528688225875" class="sc-btn sc-btn-wa"><i class="fa fa-whatsapp"/> Escribir por WhatsApp</a>
              <a href="https://radar.senticar.com" class="sc-btn sc-btn-outline">Acceder a la plataforma</a>
              <div style="margin-top:18px;opacity:.9"><i class="fa fa-envelope"/> gps@senticar.com &#160;&#160; <i class="fa fa-phone"/> 868 822 5875</div>
            </div>
          </div>
        </section>

      </div>
    </div>
  </t>
</t>"""


# ---------------------------------------------------------------------------
# 1. Vista QWeb propia del website 5 (key website.homepage, primary, COW-style)
# ---------------------------------------------------------------------------
view_ids = ex('ir.ui.view', 'search',
              [[['key', '=', 'website.homepage'], ['website_id', '=', WEBSITE_ID]]])
if view_ids:
    view_id = view_ids[0]
    ex('ir.ui.view', 'write', [[view_id], {'arch_db': ARCH, 'active': True}])
    print(f"[=] Vista existente actualizada: {view_id}")
else:
    view_id = ex('ir.ui.view', 'create', [{
        'name': 'Home',
        'type': 'qweb',
        'key': 'website.homepage',
        'mode': 'primary',
        'website_id': WEBSITE_ID,
        'arch_db': ARCH,
        'active': True,
    }])
    print(f"[+] Vista creada: {view_id}")

# ---------------------------------------------------------------------------
# 2. website.page '/' propia del website 5 -> esa vista
# ---------------------------------------------------------------------------
page_ids = ex('website.page', 'search',
              [[['url', '=', '/'], ['website_id', '=', WEBSITE_ID]]])
if page_ids:
    page_id = page_ids[0]
    ex('website.page', 'write', [[page_id], {
        'view_id': view_id, 'is_published': True, 'website_indexed': True,
        'website_meta_title': 'SentiCar | Rastreo GPS profesional',
        'website_meta_description': 'Plataforma de rastreo GPS de Sentinela: ubicacion en tiempo real, paro de motor, alertas y app movil.',
    }])
    print(f"[=] Pagina '/' existente actualizada: {page_id}")
else:
    page_id = ex('website.page', 'create', [{
        'name': 'Home',
        'url': '/',
        'website_id': WEBSITE_ID,
        'view_id': view_id,
        'is_published': True,
        'website_indexed': True,
        'website_meta_title': 'SentiCar | Rastreo GPS profesional',
        'website_meta_description': 'Plataforma de rastreo GPS de Sentinela: ubicacion en tiempo real, paro de motor, alertas y app movil.',
    }])
    print(f"[+] Pagina '/' creada: {page_id}")

print("OK. Landing principal de SentiCar desplegada (website 5).")
