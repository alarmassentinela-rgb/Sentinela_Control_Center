# -*- coding: utf-8 -*-
"""ROLLBACK del restore del diseño Argus (Balanceador) — 7-jun-2026.
Devuelve al estado previo: rutas recursivas activas, directas off, ether2 off,
foIsps={{1;1}} (todo ISP1), quita NAT ether1."""
import routeros_api

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()
RT = api.get_resource('/ip/route')

# directas -> deshabilitar
for rid in ('*1', '*14', '*15', '*2', '*3'):
    try: RT.set(id=rid, disabled='yes')
    except Exception as e: print('rt', rid, e)
# recursivas -> habilitar
for rid in ('*27', '*28', '*29', '*2A', '*2B', '*2C', '*2D', '*2E', '*2F'):
    try: RT.set(id=rid, disabled='no')
    except Exception as e: print('rt', rid, e)
# ether2 -> apagar
api.get_resource('/interface').set(id='*3', disabled='yes')
# NAT ether1 -> quitar (por comentario)
for n in api.get_resource('/ip/firewall/nat').get():
    if (n.get('comment') or '') == 'PCC: NAT por interfaz ether1':
        api.get_resource('/ip/firewall/nat').remove(id=n['id'])
# foIsps -> solo ISP1
SC = api.get_resource('/system/script')
cfg = [s for s in SC.get() if s.get('name') == 'failoverConfig'][0]
import re
src = re.sub(r':global foIsps \{.*?\};', ':global foIsps {{1;1} };', cfg.get('source'))
SC.set(id=cfg['id'], source=src)
try:
    api.get_binary_resource('/system/script').call('run', {'number': b'failoverConfig'})
    api.get_binary_resource('/system/script').call('run', {'number': b'failoverActualizadorCapacidadesISPs'})
except Exception: pass
pool.disconnect()
print("ROLLBACK aplicado: vuelta al estado previo (recursivas, todo ISP1).")
