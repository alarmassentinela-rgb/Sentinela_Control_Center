import xmlrpc.client

url = "http://192.168.3.2:8070"
db = "Sentinela_V18"
username = "api_user"
password = "admin"

def check_data():
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, [])
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # Buscar una suscripción que sepamos que procesamos
    subs = models.execute_kw(db, uid, password, 'sentinela.subscription', 'search_read', 
        [[['monitoring_account_number', '!=', False]]], 
        {'fields': ['name', 'monitoring_account_number', 'service_type'], 'limit': 5}
    )
    
    if subs:
        print("--- Suscripciones con Cuenta Detectada ---")
        for s in subs:
            print(f"Sub: {s['name']} | Cuenta: {s['monitoring_account_number']} | Tipo: {s['service_type']}")
    else:
        print("ALERTA: No se encontró ninguna suscripción con el campo 'monitoring_account_number' lleno.")

if __name__ == '__main__':
    check_data()
