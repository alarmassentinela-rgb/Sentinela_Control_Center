import xmlrpc.client
import requests
import json
import logging
from datetime import datetime

# CONFIGURACION ODOO
URL = 'http://localhost:8069'
DB = 'Sentinela_V18'
USER = 'admin'  # Cambiar por tu usuario
PASS = 'admin'  # Cambiar por tu contraseña

# CONFIGURACION SYSCOM
CLIENT_ID = 'tu_client_id' # Se obtendrá de Odoo automáticamente
CLIENT_SECRET = 'tu_client_secret'

def get_syscom_token(client_id, client_secret):
    url = "https://developers.syscom.mx/oauth/token"
    res = requests.post(url, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    })
    return res.json().get('access_token')

def run_update():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

    print(f"[*] Autenticado en Odoo (UID: {uid})")

    # 1. Obtener credenciales de Syscom desde Odoo
    params = models.execute_kw(DB, uid, PASS, 'ir.config_parameter', 'search_read', 
        [[['key', 'in', ['sentinela_syscom.client_id', 'sentinela_syscom.client_secret']]]], 
        {'fields': ['key', 'value']})
    
    config = {p['key']: p['value'] for p in params}
    c_id = config.get('sentinela_syscom.client_id')
    c_secret = config.get('sentinela_syscom.client_secret')

    if not c_id or not c_secret:
        print("[!] Error: No hay credenciales de Syscom en Odoo.")
        return

    token = get_syscom_token(c_id, c_secret)
    headers = {'Authorization': f'Bearer {token}'}
    print("[*] Token de Syscom obtenido.")

    # 2. Buscar productos de Syscom sin Clave SAT
    product_ids = models.execute_kw(DB, uid, PASS, 'product.template', 'search', 
        [[['syscom_id', '!=', False], ['l10n_mx_edi_code_sat', '=', False]]])
    
    print(f"[*] Encontrados {len(product_ids)} productos para actualizar.")

    for pid in product_ids:
        prod = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [pid], {'fields': ['syscom_id', 'name']})[0]
        sys_id = prod['syscom_id']
        
        try:
            print(f"    > Consultando {prod['name']} (ID: {sys_id})...")
            res = requests.get(f"https://developers.syscom.mx/api/v1/productos/{sys_id}", headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                sat_key = data.get('sat_key')
                if sat_key:
                    models.execute_kw(DB, uid, PASS, 'product.template', 'write', [[pid], {'l10n_mx_edi_code_sat': sat_key}])
                    print(f"    [OK] Actualizado con clave: {sat_key}")
                else:
                    print(f"    [!] No tiene sat_key en Syscom.")
            else:
                print(f"    [!] Error API Syscom: {res.status_code}")
        except Exception as e:
            print(f"    [!] Error en producto {pid}: {e}")

    print("[*] Proceso finalizado.")

if __name__ == "__main__":
    run_update()
