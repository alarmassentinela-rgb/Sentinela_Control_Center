# -*- coding: utf-8 -*-
"""¿La salida por ether3 se enmascara? Reglas srcnat en ORDEN + interface-lists."""
import routeros_api

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()


def res(p):
    return api.get_resource(p).get()


print("===== TODAS las reglas srcnat EN ORDEN =====")
i = 0
for n in res('/ip/firewall/nat'):
    if n.get('chain') != 'srcnat':
        continue
    i += 1
    oi = n.get('out-interface', '') or ''
    oil = n.get('out-interface-list', '') or ''
    print(f"  #{i:2} {n.get('action'):11} out-int={oi or '-':12} out-list={oil or '-':6} "
          f"cm={n.get('connection-mark') or '-':10} src={n.get('src-address') or '-':16} "
          f"to={n.get('to-addresses') or '-'} disabled={n.get('disabled')}")

print("\n===== Miembros de interface-list WAN =====")
for il in res('/interface/list/member'):
    if il.get('list') == 'WAN':
        print(f"   {il.get('interface')}")

print("\n===== ¿ether3_WAN tiene IP/gateway? (sanidad del enlace) =====")
for a in res('/ip/address'):
    if 'ether3' in (a.get('interface', '') or ''):
        print(f"   addr={a.get('address')} iface={a.get('interface')} disabled={a.get('disabled')}")
for r in res('/ip/route'):
    if (r.get('dst-address') == '0.0.0.0/0') and 'ether3' in (str(r.get('gateway')) or ''):
        print(f"   ruta default ether3: gw={r.get('gateway')} active={r.get('active')} disabled={r.get('disabled')}")

pool.disconnect()
