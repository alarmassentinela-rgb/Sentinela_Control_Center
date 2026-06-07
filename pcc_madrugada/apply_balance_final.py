# -*- coding: utf-8 -*-
"""Aplica balance 2:1:2 + flush conntrack WISP + monitor + auto-rollback."""
import routeros_api, time, re

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()
SC = api.get_resource('/system/script')
IF = api.get_resource('/interface')
CN = api.get_resource('/ip/firewall/connection')


def run(n):
    try: api.get_binary_resource('/system/script').call('run', {'number': n.encode()})
    except Exception: pass


def set_foisps(lit):
    cfg = [s for s in SC.get() if s.get('name') == 'failoverConfig'][0]
    SC.set(id=cfg['id'], source=re.sub(r':global foIsps \{.*?\};',
           ':global foIsps ' + lit + ';', cfg.get('source')))
    run('failoverConfig'); time.sleep(0.5); run('failoverActualizadorCapacidadesISPs')


def wan_dl(secs=6):
    def rb():
        return {i['name']: int(i.get('rx-byte', 0)) for i in IF.get()
                if i.get('name') in ('ether1_WAN', 'ether2_WAN', 'ether3_WAN')}
    a = rb(); time.sleep(secs); b = rb()
    return {k: round((b[k] - a[k]) * 8 / secs / 1e6, 1) for k in a}


def flush_wisp():
    n = 0
    for c in CN.get():
        if (c.get('src-address', '') or '').startswith('192.168.10.50'):
            try: CN.remove(id=c['id']); n += 1
            except Exception: pass
    return n


def rollback():
    set_foisps('{{1;1} }')
    IF.set(id='*3', disabled='yes')
    flush_wisp()


try:
    print(">>> Baseline (antes):", wan_dl(5), "Mbps")
    base = sum(wan_dl(2).values()) or 1

    print(">>> Aplicando foIsps = 2:1:2 ...")
    set_foisps('{{1;2};{2;1};{3;2} }')
    time.sleep(2)

    print(">>> Flush conntrack WISP (192.168.10.50) ...")
    f = flush_wisp()
    print(f"    conexiones WISP vaciadas: {f}")
    time.sleep(12)

    print("\n>>> MONITOREO (3 muestras):")
    for k in range(3):
        r = wan_dl(5)
        tot = sum(r.values())
        print(f"   m{k+1}: ether1={r['ether1_WAN']:6}  ether2={r['ether2_WAN']:6}  "
              f"ether3={r['ether3_WAN']:6}  | TOTAL={tot:.0f} Mbps")

    # conntrack: correctitud por ISP
    nat = {'ISP1_conn': '192.168.1', 'ISP2_conn': '192.168.2', 'ISP3_conn': '192.168.0'}
    st = {k: {'tot': 0, 'ok': 0, 'rep': 0} for k in nat}
    conns = []
    for _ in range(4):
        try: conns = CN.get(); break
        except Exception: time.sleep(0.4)
    for c in conns:
        cm = c.get('connection-mark', '')
        if cm in st:
            st[cm]['tot'] += 1
            if (c.get('reply-dst-address', '') or '').startswith(nat[cm]): st[cm]['ok'] += 1
            if int(c.get('repl-bytes', 0) or 0) > 500: st[cm]['rep'] += 1
    print("\n>>> Conntrack por ISP (NAT correcto / con vuelta):")
    for k in nat:
        print(f"   {k}: total={st[k]['tot']:5}  NAT-ok={st[k]['ok']:5}  con-vuelta={st[k]['rep']:5}")

    final = wan_dl(4)
    tot = sum(final.values())
    ok = (tot >= base * 0.6 and final['ether3_WAN'] > 5 and final['ether2_WAN'] > 2)
    if ok:
        print(f"\n>>> ✅ BALANCE OK — 3 WAN repartiendo, total {tot:.0f} Mbps. DEJO ENCENDIDO.")
        keep = True
    else:
        print(f"\n>>> ❌ algo no cuadra (total {tot:.0f} vs base {base:.0f}) — AUTO-ROLLBACK.")
        rollback(); keep = False
except Exception as e:
    print(">>> EXCEPCIÓN:", str(e)[:120], "-> ROLLBACK")
    rollback(); keep = False

print("\nESTADO:", "BALANCE 2:1:2 ACTIVO" if keep else "REVERTIDO (ISP1)")
pool.disconnect()
