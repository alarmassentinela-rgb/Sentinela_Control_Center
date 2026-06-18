#!/usr/bin/env python3
"""
Publica un set CURADO de productos GPS SentiCar en el /shop (website id=5).

- Crea categoria eCommerce "Rastreo GPS".
- Crea/actualiza 4 productos limpios (idempotente por default_code).
- Scoped a website_id=5 -> solo aparecen en la tienda SentiCar, no en los otros sitios.
- Reusa la FOTO real de los productos Syscom de referencia (no inventa imagenes);
  el plan (servicio) usa el logo SentiCar.

Prices y seleccion confirmados por Enrique (17-jun-2026).
"""
import xmlrpc.client, base64, os

URL='http://192.168.3.2:8070'; DB='Sentinela_V18'; USER='api_user'; PWD='SentinelaBot2026!'
WEBSITE_ID=5

common=xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common'); uid=common.authenticate(DB,USER,PWD,{})
assert uid,"auth"
models=xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
def ex(model,meth,args,kw=None): return models.execute_kw(DB,uid,PWD,model,meth,args,kw or {})

def img_of(pid):
    try:
        r=ex('product.template','read',[[pid],['image_1920']])
        return r[0].get('image_1920') or False
    except Exception:
        return False

logo_b64=False
lp='/mnt/c/Users/dell/DellCli/logo_senticar_real.png'
if os.path.exists(lp):
    with open(lp,'rb') as f: logo_b64=base64.b64encode(f.read()).decode()

# --- categoria eCommerce ---
cat=ex('product.public.category','search',[[['name','=','Rastreo GPS']]])
if cat:
    cat_id=cat[0]
else:
    cat_id=ex('product.public.category','create',[{'name':'Rastreo GPS','sequence':1}])
print("categoria Rastreo GPS:",cat_id)

PRODUCTS=[
 {
  'code':'SENTICAR-GPS-VEH','name':'GPS Vehicular SentiCar con Paro de Motor',
  'price':1499.0,'type':'consu','img_from':712,
  'sale':'Rastreador 4G LTE con apagado/encendido de motor remoto. Carcasa IP66.',
  'web':"""<p>El <strong>GPS Vehicular SentiCar</strong> es la proteccion ideal para tu auto particular. Rastreo en tiempo real, alertas y la tranquilidad de poder <strong>apagar el motor de forma remota</strong> en caso de robo, directo desde la app.</p>
<ul>
<li>Conectividad 4G LTE con respaldo 2G &#8212; cobertura nacional.</li>
<li>Apagado y encendido de motor remoto desde la app SentiCar.</li>
<li>Ubicacion en tiempo real, geocercas y alertas instantaneas.</li>
<li>Carcasa robusta IP66 y proteccion de bateria.</li>
<li>Incluye alta en la plataforma SentiCar (radar.senticar.com).</li>
</ul>
<p><em>Requiere plan de rastreo mensual para el servicio de plataforma.</em></p>""",
 },
 {
  'code':'SENTICAR-PLAN','name':'Plan de Rastreo SentiCar (mensual)',
  'price':349.0,'type':'service','img_from':None,
  'sale':'Servicio mensual de la plataforma SentiCar: app, web, alertas y soporte.',
  'web':"""<p>El <strong>Plan de Rastreo SentiCar</strong> activa tu equipo en nuestra plataforma de monitoreo, con todo lo que necesitas para tener el control:</p>
<ul>
<li>Acceso a la plataforma web <strong>radar.senticar.com</strong> y a la app Android.</li>
<li>Ubicacion en tiempo real, historial de rutas y reportes.</li>
<li>Alertas por velocidad, geocerca, encendido y desconexion.</li>
<li>Respaldo del centro de monitoreo Sentinela.</li>
</ul>
<p><strong>$349 MXN / mes por equipo.</strong> Sin plazo forzoso.</p>""",
 },
 {
  'code':'SENTICAR-GPS-FLEET','name':'GPS SentiCar para Flotillas (Avanzado)',
  'price':2890.0,'type':'consu','img_from':719,
  'sale':'Rastreador avanzado 4G: identificacion de conductor, bloqueo remoto, doble SIM y CAN bus.',
  'web':"""<p>El <strong>GPS SentiCar para Flotillas</strong> es la solucion para empresas que administran varias unidades. Telemetria avanzada y control total desde un solo tablero.</p>
<ul>
<li>4G LTE Cat 1 con doble SIM para maxima disponibilidad.</li>
<li>Identificacion de conductor y bloqueo remoto del vehiculo.</li>
<li>Lectura CAN bus, multiples entradas/salidas y deteccion de jammer.</li>
<li>Sensores Bluetooth (temperatura, combustible) compatibles.</li>
<li>Administracion de toda la flota desde la plataforma SentiCar.</li>
</ul>
<p><em>Requiere plan de rastreo mensual por unidad.</em></p>""",
 },
 {
  'code':'SENTICAR-GPS-ASSET','name':'GPS SentiCar para Activos y Carga (Solar IP67)',
  'price':4990.0,'type':'consu','img_from':6256,
  'sale':'Rastreador de activos con bateria solar recargable, IP67, para maquinaria, remolques y carga.',
  'web':"""<p>El <strong>GPS SentiCar para Activos</strong> rastrea lo que no tiene bateria propia: remolques, maquinaria, contenedores y mercancia de alto valor.</p>
<ul>
<li>Bateria recargable de larga duracion con <strong>panel solar</strong> integrado.</li>
<li>Proteccion IP67 para intemperie y condiciones extremas.</li>
<li>Conectividad LTE Cat-M1 / NB-IoT de bajo consumo.</li>
<li>Alarma de movimiento y de bateria baja.</li>
<li>Seguimiento desde la plataforma SentiCar.</li>
</ul>
<p><em>Requiere plan de rastreo mensual por equipo.</em></p>""",
 },
]

for pdef in PRODUCTS:
    img = logo_b64
    if pdef['img_from']:
        ri=img_of(pdef['img_from'])
        if ri: img=ri
    vals={
        'name':pdef['name'],
        'list_price':pdef['price'],
        'type':pdef['type'],
        'sale_ok':True,
        'purchase_ok':False,
        'default_code':pdef['code'],
        'description_sale':pdef['sale'],
        'website_description':pdef['web'],
        'is_published':True,
        'website_id':WEBSITE_ID,
        'public_categ_ids':[(6,0,[cat_id])],
    }
    if img: vals['image_1920']=img
    found=ex('product.template','search',[[['default_code','=',pdef['code']]]])
    if found:
        pid=found[0]; ex('product.template','write',[[pid],vals]); print(f"[=] actualizado {pdef['code']} -> {pid}")
    else:
        pid=ex('product.template','create',[vals]); print(f"[+] creado {pdef['code']} -> {pid}")

print("OK. Productos GPS SentiCar publicados en /shop (website 5).")
