# -*- coding: utf-8 -*-
"""REVISIÓN (solo lectura): cómo tenía Argus el PCC/routing vs el rediseño."""
import routeros_api

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()


def res(p):
    return api.get_resource(p).get()


print("===== RUTAS to_ISP1/2/3: DIRECTAS (Argus) vs RECURSIVAS (rediseño) =====")
for mark in ('to_ISP1', 'to_ISP2', 'to_ISP3'):
    print(f"\n  --- {mark} ---")
    for r in res('/ip/route'):
        if r.get('routing-mark') == mark:
            gw = r.get('gateway', '')
            tipo = 'DIRECTA(ether)' if '%ether' in gw else 'recursiva(DNS)'
            print(f"    [{tipo:14}] gw={gw:26} dist={r.get('distance')} "
                  f"active={r.get('active')} disabled={r.get('disabled')}")

print("\n===== DEFAULT principal (main) =====")
for r in res('/ip/route'):
    if r.get('dst-address') == '0.0.0.0/0' and (r.get('routing-mark', '') in ('', 'main')):
        gw = r.get('gateway', '')
        tipo = 'DIRECTA' if '%ether' in gw else ('recursiva' if not gw[0].isdigit() or '.' in gw else 'x')
        print(f"    gw={gw:26} dist={r.get('distance')} active={r.get('active')} disabled={r.get('disabled')}")

print("\n===== NAT srcnat masquerade/src-nat: ¿por interfaz (Argus) o catch-all? =====")
i = 0
for n in res('/ip/firewall/nat'):
    if n.get('chain') == 'srcnat' and n.get('action') in ('masquerade', 'src-nat', 'accept'):
        i += 1
        oi = n.get('out-interface', '') or n.get('out-interface-list', '') or '(cualquiera)'
        print(f"    #{i} {n.get('action'):11} out={oi:16} to={n.get('to-addresses') or '-'} "
              f"disabled={n.get('disabled')} cmt={(n.get('comment') or '')[:22]}")

print("\n===== ¿Existe el .rsc original de Argus? =====")
for f in res('/file'):
    nm = f.get('name', '')
    if 'pre_pcc' in nm or 'rsc' in nm.lower():
        print(f"    {nm}  ({f.get('size')} bytes, {f.get('creation-time')})")

pool.disconnect()
