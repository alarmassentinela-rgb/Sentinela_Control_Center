import xmlrpc.client

# Configuración basada en scripts previos
url = 'http://localhost:8069'
db = 'Sentinela_V18'
username = 'admin'
password = 'admin'

def check_subs():
    print(f"Conectando a {url} (DB: {db})...")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("Error de autenticación.")
            return
        
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        sub_names = ['SUB-0144', 'SUB-0145']
        subs = models.execute_kw(db, uid, password, 'sentinela.subscription', 'search_read',
                                [[('name', 'in', sub_names)]],
                                {'fields': ['name', 'state', 'next_billing_date', 'partner_id', 'service_type']})
        
        if not subs:
            print("No se encontraron las suscripciones SUB-0144 o SUB-0145.")
            return

        for sub in subs:
            print(f"--- {sub['name']} ---")
            print(f"Estado: {sub['state']}")
            print(f"Próxima Factura: {sub['next_billing_date']}")
            print(f"Cliente ID: {sub['partner_id']}")
            
            partner = models.execute_kw(db, uid, password, 'res.partner', 'read',
                                       [sub['partner_id'][0]],
                                       {'fields': ['name', 'invoice_grouping_method']})
            print(f"Método de Agrupación del Cliente: {partner[0].get('invoice_grouping_method')}")
            
            # Buscar cotizaciones relacionadas
            so_ids = models.execute_kw(db, uid, password, 'sale.order', 'search',
                                      [['|', ('origin', 'like', sub['name']), ('subscription_id', '=', sub['id'])]])
            if so_ids:
                sos = models.execute_kw(db, uid, password, 'sale.order', 'read', [so_ids], {'fields': ['name', 'state', 'date_order', 'origin']})
                print(f"Cotizaciones encontradas: {sos}")
            else:
                print("No se encontraron cotizaciones.")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_subs()
