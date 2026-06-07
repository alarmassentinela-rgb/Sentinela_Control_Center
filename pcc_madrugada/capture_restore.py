# -*- coding: utf-8 -*-
"""Captura estado EXACTO antes de restaurar diseño Argus (para rollback)."""
import routeros_api, json

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()
snap = {'routes': [], 'ether2': None, 'nat_iface': [], 'foisps': None}

for r in api.get_resource('/ip/route').get():
    if r.get('routing-mark') in ('to_ISP1', 'to_ISP2', 'to_ISP3'):
        gw = r.get('gateway', '')
        snap['routes'].append({'id': r['id'], 'mark': r.get('routing-mark'),
                               'gw': gw, 'dist': r.get('distance'),
                               'disabled': r.get('disabled'),
                               'tipo': 'directa' if '%ether' in gw else 'recursiva'})

for x in api.get_resource('/interface').get():
    if x.get('name') == 'ether2_WAN':
        snap['ether2'] = {'id': x['id'], 'disabled': x.get('disabled')}

for n in api.get_resource('/ip/firewall/nat').get():
    if 'NAT por interfaz' in (n.get('comment', '') or ''):
        snap['nat_iface'].append({'id': n['id'], 'out': n.get('out-interface')})

for s in api.get_resource('/system/script').get():
    if s.get('name') == 'failoverConfig':
        for ln in (s.get('source', '') or '').splitlines():
            if 'foIsps {' in ln:
                snap['foisps'] = ln.strip()

pool.disconnect()
print(json.dumps(snap, indent=1, ensure_ascii=False))
open('/tmp/restore_snapshot.json', 'w').write(json.dumps(snap, indent=1, ensure_ascii=False))
print("\nGuardado en /tmp/restore_snapshot.json")
