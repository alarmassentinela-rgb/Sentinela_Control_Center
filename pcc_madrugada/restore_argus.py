# -*- coding: utf-8 -*-
"""Restaura diseño Argus (rutas directas + NAT por interfaz) + foIsps=2:1:2.
   Prueba con conntrack; si falla, AUTO-ROLLBACK."""
import routeros_api, time, re

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()
RT = api.get_resource('/ip/route')
NAT = api.get_resource('/ip/firewall/nat')
SC = api.get_resource('/system/script')
IF = api.get_resource('/interface')

DIRECTAS = ('*1', '*14', '*15', '*2', '*3')
RECURSIVAS = ('*27', '*28', '*29', '*2A', '*2B', '*2C', '*2D', '*2E', '*2F')


def run(n):
    try: api.get_binary_resource('/system/script').call('run', {'number': n.encode()})
    except Exception: pass


def set_foisps(lit):
    cfg = [s for s in SC.get() if s.get('name') == 'failoverConfig'][0]
    SC.set(id=cfg['id'], source=re.sub(r':global foIsps \{.*?\};',
           ':global foIsps ' + lit + ';', cfg.get('source')))
    run('failoverConfig'); time.sleep(0.5); run('failoverActualizadorCapacidadesISPs')


def rollback():
    for rid in DIRECTAS:
        try: RT.set(id=rid, disabled='yes')
        except Exception: pass
    for rid in RECURSIVAS:
        try: RT.set(id=rid, disabled='no')
        except Exception: pass
    IF.set(id='*3', disabled='yes')
    for n in NAT.get():
        if (n.get('comment') or '') == 'PCC: NAT por interfaz ether1':
            NAT.remove(id=n['id'])
    set_foisps('{{1;1} }')


try:
    print(">>> 1. NAT por interfaz ether1 (ether2/3 ya existen)")
    have1 = any((n.get('comment') or '') == 'PCC: NAT por interfaz ether1' for n in NAT.get())
    if not have1:
        rule8 = next(n['id'] for n in NAT.get() if n.get('chain') == 'srcnat'
                     and n.get('action') == 'masquerade'
                     and not (n.get('out-interface') or n.get('out-interface-list')
                              or n.get('src-address') or n.get('connection-mark'))
                     and n.get('disabled') != 'true')
        NAT.add(chain='srcnat', action='masquerade',
                **{'out-interface': 'ether1_WAN',
                   'comment': 'PCC: NAT por interfaz ether1', 'place-before': rule8})

    print(">>> 2. Encender ether2_WAN")
    IF.set(id='*3', disabled='no'); time.sleep(2)
    ip2 = next((a.get('address') for a in api.get_resource('/ip/address').get()
                if 'ether2' in (a.get('interface') or '')), '?')
    print("    ether2 IP:", ip2)

    print(">>> 3. Habilitar rutas DIRECTAS, deshabilitar RECURSIVAS")
    for rid in DIRECTAS: RT.set(id=rid, disabled='no')
    for rid in RECURSIVAS: RT.set(id=rid, disabled='yes')

    print(">>> 4. foIsps = 2:1:2 (ISP1=2, ISP2=1, ISP3=2)")
    set_foisps('{{1;2};{2;1};{3;2} }')
    time.sleep(30)

    print("\n>>> PRUEBA conntrack por ISP (NAT-src correcto + vuelta>0):")
    expect = {'ISP1_conn': '192.168.1', 'ISP2_conn': '192.168.2', 'ISP3_conn': '192.168.0'}
    stats = {k: {'tot': 0, 'reply': 0, 'natok': 0} for k in expect}
    conns = []
    for _ in range(4):
        try: conns = api.get_resource('/ip/firewall/connection').get(); break
        except Exception: time.sleep(0.5)
    for c in conns:
        cm = c.get('connection-mark', '')
        if cm in stats:
            stats[cm]['tot'] += 1
            if int(c.get('repl-bytes', 0) or 0) > 200: stats[cm]['reply'] += 1
            if (c.get('reply-dst-address', '') or '').startswith(expect[cm]): stats[cm]['natok'] += 1
    for k in expect:
        s = stats[k]
        print(f"   {k}: total={s['tot']:4} vuelta>0={s['reply']:4} NAT-src-ok({expect[k]}.x)={s['natok']:4}")

    # cruce: ISP3 con NAT correcto Y respuesta
    isp3_ok=0
    for c in conns:
        if c.get('connection-mark')=='ISP3_conn' and (c.get('reply-dst-address','') or '').startswith('192.168.0') and int(c.get('repl-bytes',0) or 0)>200:
            isp3_ok+=1
    print(f"   >>> ISP3 con NAT-ok(192.168.0.x) Y vuelta>0: {isp3_ok}")
    def rb():
        return {i['name']: int(i.get('rx-byte', 0)) for i in IF.get()
                if i.get('name') in ('ether1_WAN','ether2_WAN','ether3_WAN')}
    a=rb(); time.sleep(8); b=rb()
    r={k:(b[k]-a[k])*8/8/1e6 for k in a}
    print("\n>>> Tráfico:", {k: f"{v:.0f}Mbps" for k, v in r.items()})
    ok = (r['ether3_WAN'] > 5 and r['ether2_WAN'] > 1 and isp3_ok >= 3)
    if ok:
        print("\n>>> ✅ FUNCIONA — los 3 WAN reparten, ISP3 baja datos, NAT correcto. DEJO ENCENDIDO.")
        keep = True
    else:
        print("\n>>> ❌ Algo falla — AUTO-ROLLBACK.")
        rollback(); keep = False
except Exception as e:
    print(">>> EXCEPCIÓN:", str(e)[:120], "-> ROLLBACK")
    rollback(); keep = False

time.sleep(2)
print("\nESTADO:", "RESTAURADO ARGUS 2:1:2" if keep else "REVERTIDO (ISP1)")
pool.disconnect()
