# -*- coding: utf-8 -*-
"""Prueba ether2 (TotalPlay) con 192.168.3.90 -> to_ISP2."""
import routeros_api, time

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()
MG = api.get_resource('/ip/firewall/mangle')

# 1. encender ether2_WAN
api.get_resource('/interface').set(id='*3', disabled='no')
print("ether2_WAN encendido")
time.sleep(3)
ip2 = next((a.get('address') for a in api.get_resource('/ip/address').get()
            if 'ether2' in (a.get('interface') or '')), '?')
print("  ether2 IP:", ip2)

# 2. quitar reglas de prueba previas y agregar 3.90 -> to_ISP2
for m in MG.get():
    if 'TEST PCC' in (m.get('comment') or '') or 'TEST WISP' in (m.get('comment') or ''):
        MG.remove(id=m['id'])
anchor = next(m['id'] for m in MG.get()
              if m.get('chain') == 'prerouting'
              and 'ether7' in (m.get('in-interface') or '')
              and 'Servidores' in (m.get('src-address-list') or ''))
MG.add(chain='prerouting', **{'in-interface': 'ether7_LAN', 'src-address': '192.168.3.90',
                              'action': 'mark-routing', 'new-routing-mark': 'to_ISP2',
                              'passthrough': 'no',
                              'comment': 'TEST PCC ether2 (192.168.3.90)',
                              'place-before': anchor})
print("regla: 192.168.3.90 -> to_ISP2 (ether2)")

# 3. flush conexiones de 3.90
CN = api.get_resource('/ip/firewall/connection')
n = 0
for c in CN.get():
    if (c.get('src-address', '') or '').startswith('192.168.3.90'):
        try: CN.remove(id=c['id']); n += 1
        except Exception: pass
print("conexiones 3.90 limpiadas:", n)

# 4. verificar ruta to_ISP2 activa (debe ser por ether2 ahora)
print("\nRuta to_ISP2 ACTIVA:")
for r in api.get_resource('/ip/route').get():
    if r.get('routing-mark') == 'to_ISP2' and r.get('active') == 'true':
        gw = r.get('gateway', '')
        print(f"  gw={gw}  ({r.get('gateway-status')})")
pool.disconnect()
print("\nListo. Navega en la PC.")
