import xmlrpc.client

url = "http://192.168.3.2:8070"
db = "Sentinela_V18"
username = "api_user"
password = "admin"

def find_updated_example():
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, [])
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # Buscar suscripciones donde el nombre de la direccion de servicio tenga el formato [XXXX]
    # Usamos un domain que busque '[' en el nombre del contacto de servicio
    subs = models.execute_kw(db, uid, password, 'sentinela.subscription', 'search_read', 
        [[('service_address_id.name', 'like', '[')]], 
        {'fields': ['name', 'partner_id', 'service_address_id', 'monitoring_account_number'], 'limit': 5}
    )
    
    if subs:
        print("--- EJEMPLOS DE SUSCRIPCIONES ACTUALIZADAS ---")
        for s in subs:
            # Obtener detalles de la direccion
            addr_id = s['service_address_id'][0]
            addr_data = models.execute_kw(db, uid, password, 'res.partner', 'read', [addr_id, ['name', 'street', 'parent_id']])
            
            print(f"Suscripción: {s['name']}")
            print(f"  Cuenta (Campo): {s['monitoring_account_number']}")
            print(f"  Cliente Fiscal: {s['partner_id'][1]}")
            print(f"  Contacto de Servicio: {addr_data[0]['name']}")
            print(f"  Dirección en Odoo: {addr_data[0]['street']}")
            print("-" * 40)
    else:
        print("No se encontraron ejemplos actualizados.")

if __name__ == '__main__':
    find_updated_example()
