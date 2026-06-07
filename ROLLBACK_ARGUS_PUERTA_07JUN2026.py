# -*- coding: utf-8 -*-
"""
ROLLBACK — Reabre la "puerta" de Argus en CCRsentinela (192.168.10.50).

Revierte EXACTAMENTE los cambios hechos el 7-jun-2026 por el cierre de Argus:
  1. Re-habilita el scheduler argusblack_monitorinterfaz (el que reactiva el túnel).
  2. Re-habilita la interfaz OVPN argusblack (el túnel vuelve a subir).
  3. Restaura 10.231.71.0/24 en las IPs permitidas de los usuarios sentinela y gemini_api.

Estado ANTES del cierre (snapshot 7-jun-2026 ~13:1x):
  - scheduler argusblack_monitorinterfaz (id *E): disabled=false
  - interface ovpn argusblack (id *D): disabled=false, running=true
  - user sentinela (id *2) address: 192.168.3.0/24,192.168.10.0/24,172.19.0.0/16,172.16.50.0/24,10.231.71.0/24
  - user gemini_api (id *7) address: 192.168.3.0/24,192.168.10.0/24,172.19.0.0/16,172.16.50.0/24,10.231.71.0/24

Uso:  python3 ROLLBACK_ARGUS_PUERTA_07JUN2026.py
"""
import routeros_api

HOST, USER, PASS = '192.168.10.50', 'gemini_api', 'gemini_api2113'
ORIG_ADDR = '192.168.3.0/24,192.168.10.0/24,172.19.0.0/16,172.16.50.0/24,10.231.71.0/24'

pool = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASS, plaintext_login=True)
api = pool.get_api()

# 1. Re-habilitar usuarios (restaurar la subred de Argus) PRIMERO
for u in api.get_resource('/user').get():
    if u.get('name') in ('sentinela', 'gemini_api'):
        api.get_resource('/user').set(id=u['id'], address=ORIG_ADDR)
        print(f"  user {u['name']}: address restaurada -> {ORIG_ADDR}")

# 2. Re-habilitar el scheduler monitor (volverá a levantar el túnel)
for s in api.get_resource('/system/scheduler').get():
    if s.get('name') == 'argusblack_monitorinterfaz':
        api.get_resource('/system/scheduler').set(id=s['id'], disabled='no')
        print("  scheduler argusblack_monitorinterfaz: ENABLED")

# 3. Re-habilitar la interfaz OVPN
for i in api.get_resource('/interface/ovpn-client').get():
    if i.get('name') == 'argusblack':
        api.get_resource('/interface/ovpn-client').set(id=i['id'], disabled='no')
        print("  interface argusblack: ENABLED (el túnel volverá a subir)")

pool.disconnect()
print("\nROLLBACK aplicado. Argus vuelve a tener acceso al CCR.")
