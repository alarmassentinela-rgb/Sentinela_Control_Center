# -*- coding: utf-8 -*-
"""
ROLLBACK del re-encendido del PCC (Balanceador 192.168.10.254) — 7-jun-2026.

Revierte EXACTAMENTE al estado previo (PCC apagado, todo por ether1, ether2 off):
  mangle *58 -> pcc both-addresses:1/0, disabled=yes
  mangle *13 -> pcc both-addresses:2/3, disabled=yes
  route  *29 (to_ISP1->208.67.220.220) -> distance=2
  route  *2F (to_ISP3->208.67.220.220) -> distance=2
  route  *B  (default ->192.168.2.254%ether2) -> distance=1
  iface  *3  ether2_WAN -> disabled=yes

Uso:  python3 ROLLBACK_PCC_07JUN2026.py
"""
import routeros_api

pool = routeros_api.RouterOsApiPool('192.168.10.254', username='gemini_api',
                                    password='gemini_api2113', plaintext_login=True)
api = pool.get_api()

api.get_resource('/ip/firewall/mangle').set(id='*58', **{'per-connection-classifier': 'both-addresses:1/0', 'disabled': 'yes'})
api.get_resource('/ip/firewall/mangle').set(id='*13', **{'per-connection-classifier': 'both-addresses:2/3', 'disabled': 'yes'})
api.get_resource('/ip/route').set(id='*29', distance='2')
api.get_resource('/ip/route').set(id='*2F', distance='2')
api.get_resource('/ip/route').set(id='*B', distance='1')
api.get_resource('/interface').set(id='*3', disabled='yes')

pool.disconnect()
print("ROLLBACK aplicado: PCC apagado, ether2 off, todo vuelve a ether1.")
