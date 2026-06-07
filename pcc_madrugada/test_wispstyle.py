# -*- coding: utf-8 -*-
"""Prueba marcado ESTILO WISP en 192.168.3.90: mark-connection ISP3_conn
   (lo enruta la regla #45 cm=ISP3_conn->to_ISP3, igual que a los clientes)."""
import routeros_api

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()
MG = api.get_resource('/ip/firewall/mangle')

# quitar la regla de prueba anterior (mark-routing directo)
for m in MG.get():
    if (m.get('comment') or '') in ('TEST PCC ether3 (192.168.3.90)',
                                    'TEST WISP-style (192.168.3.90)'):
        MG.remove(id=m['id'])

# ancla: primer pin de oficina
anchor = next(m['id'] for m in MG.get()
              if m.get('chain') == 'prerouting'
              and 'ether7' in (m.get('in-interface') or '')
              and 'Servidores' in (m.get('src-address-list') or ''))

# marcar la CONEXIÓN como ISP3_conn (como el PCC a los clientes); que la #45 la enrute
MG.add(chain='prerouting', **{'in-interface': 'ether7_LAN',
                              'src-address': '192.168.3.90',
                              'connection-mark': 'no-mark',
                              'action': 'mark-connection',
                              'new-connection-mark': 'ISP3_conn',
                              'passthrough': 'yes',
                              'comment': 'TEST WISP-style (192.168.3.90)',
                              'place-before': anchor})
print("regla cambiada: 192.168.3.90 -> mark-connection ISP3_conn (estilo WISP)")

# flush conexiones de 3.90
CN = api.get_resource('/ip/firewall/connection')
n = 0
for c in CN.get():
    if (c.get('src-address', '') or '').startswith('192.168.3.90'):
        try: CN.remove(id=c['id']); n += 1
        except Exception: pass
print(f"conexiones de 192.168.3.90 limpiadas: {n}")
print("Ruta to_ISP3 que usará la #45:")
for r in api.get_resource('/ip/route').get():
    if r.get('routing-mark') == 'to_ISP3' and r.get('active') == 'true':
        print("   gw=", r.get('gateway'))
pool.disconnect()
print("Listo. Navega de nuevo en la PC.")
