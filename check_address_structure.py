import sys
import xmlrpc.client

url = "http://192.168.3.2:8070"
db = "Sentinela_V18"
username = "api_user"
password = "admin"

def check_address_types():
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, [])
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    # Get all subs with monitoring devices
    # Correct syntax: args list contains the domain, kwargs dict contains fields
    subs = models.execute_kw(db, uid, password, 'sentinela.subscription', 'search_read', 
        [[['monitoring_device_ids', '!=', False]]], 
        {'fields': ['name', 'partner_id', 'service_address_id'], 'limit': 20}
    )

    same_address = 0
    different_address = 0

    print("--- Análisis de Direcciones ---")
    for sub in subs:
        if not sub['partner_id'] or not sub['service_address_id']:
            continue
            
        p_id = sub['partner_id'][0]
        s_id = sub['service_address_id'][0]
        
        status = "SEPARADA (OK)" if p_id != s_id else "IGUAL (RIESGO)"
        if p_id == s_id:
            same_address += 1
        else:
            different_address += 1
            
        print(f"Sub: {sub['name']} | Cliente: {p_id} | Servicio: {s_id} -> {status}")

    print("-" * 30)
    print(f"Total Muestra: {len(subs)}")
    print(f"Misma Dirección (Riesgo Fiscal): {same_address}")
    print(f"Dirección Separada (Segura): {different_address}")

if __name__ == '__main__':
    check_address_types()