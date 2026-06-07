# -*- coding: utf-8 -*-
"""Monta regla de prueba: SOLO 192.168.3.90 -> to_ISP3, antes del pin de oficina."""
import routeros_api

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()
MG = api.get_resource('/ip/firewall/mangle')

# 1. localizar el primer pin de oficina (Servidores Wan2 o Wan1) para insertar ANTES
anchor = None
for m in MG.get():
    if (m.get('chain') == 'prerouting' and 'ether7' in (m.get('in-interface') or '')
            and 'Servidores' in (m.get('src-address-list') or '')):
        anchor = m['id']
        break
print("ancla (1er pin oficina) id =", anchor)

# 2. ¿ya existe la regla de prueba? (idempotencia)
exists = [m['id'] for m in MG.get() if (m.get('comment') or '') == 'TEST PCC ether3 (192.168.3.90)']
for e in exists:
    MG.remove(id=e)
    print("  (removida regla de prueba previa)")

# 3. agregar la regla de prueba -> to_ISP3
MG.add(chain='prerouting', **{'in-interface': 'ether7_LAN',
                              'src-address': '192.168.3.90',
                              'action': 'mark-routing',
                              'new-routing-mark': 'to_ISP3',
                              'passthrough': 'no',
                              'comment': 'TEST PCC ether3 (192.168.3.90)',
                              'place-before': anchor})
print("  + regla: 192.168.3.90 -> to_ISP3 (passthrough=no), antes del pin")

# 4. flush conexiones de 192.168.3.90 (que arranque fresca por la nueva ruta)
CN = api.get_resource('/ip/firewall/connection')
n = 0
for c in CN.get():
    if (c.get('src-address', '') or '').startswith('192.168.3.90') or \
       (c.get('dst-address', '') or '').startswith('192.168.3.90'):
        try: CN.remove(id=c['id']); n += 1
        except Exception: pass
print(f"  conexiones de 192.168.3.90 limpiadas: {n}")

# 5. confirmar estado de la ruta to_ISP3 que usará
print("\n  Ruta to_ISP3 ACTIVA ahora:")
for r in api.get_resource('/ip/route').get():
    if r.get('routing-mark') == 'to_ISP3' and r.get('active') == 'true':
        tipo = 'DIRECTA' if '%ether' in (r.get('gateway') or '') else 'recursiva'
        print(f"    [{tipo}] gw={r.get('gateway')}")

pool.disconnect()
print("\nListo. La PC 192.168.3.90 ahora sale por to_ISP3.")
