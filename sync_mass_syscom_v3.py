import requests
import time
from odoo import fields

def mass_sync_dynamic():
    client_id = 'AE2U6oagC6BZVCSjASwFBUIGkj8M4Hjg'
    client_secret = 'ERWZPV4vYQfWwDt5QGcYqyZb6Zmzc4p2b7iO4Ld5'
    token_url = "https://developers.syscom.mx/oauth/token"
    api_url = 'https://developers.syscom.mx/api/v1'

    print("--- INICIANDO ACTUALIZACIÓN DINÁMICA SYSCOM (TC REAL) ---")
    
    try:
        res = requests.post(token_url, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }, timeout=20)
        token = res.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        print("✅ Conexión establecida.")
    except Exception as e:
        print(f"❌ Error token: {e}")
        return

    try:
        res_tc = requests.get(f"{api_url}/tipocambio", headers=headers, timeout=10)
        tc = float(res_tc.json().get('normal', 17.26))
        print(f"💹 Tipo de Cambio: ${tc}")
    except:
        tc = 17.26
        print(f"⚠️ Usando TC preventivo: ${tc}")

    products = env['product.template'].search([
        ('default_code', '!=', False),
        ('detailed_type', 'in', ['product', 'consu'])
    ])

    total = len(products)
    print(f"📦 Procesando: {total}")

    count = 0
    success = 0

    for prod in products:
        count += 1
        try:
            sys_id = prod.syscom_id
            if not sys_id:
                search = requests.get(f"{api_url}/productos?busqueda={prod.default_code}", headers=headers, timeout=5).json()
                results = search.get('productos', [])
                if results:
                    sys_id = str(results[0].get('producto_id'))
                else:
                    continue

            detail = requests.get(f"{api_url}/productos/{sys_id}", headers=headers, timeout=5).json()
            cost_usd = float(detail.get('precios', {}).get('precio_descuento') or 0.0)
            
            prod.write({
                'syscom_id': sys_id,
                'syscom_price_usd': cost_usd,
                'standard_price': cost_usd * tc,
                'syscom_last_update': fields.Datetime.now()
            })
            success += 1
            
            if count % 50 == 0:
                print(f"Progreso: {count}/{total} | Exitos: {success}")
                env.cr.commit()
        except:
            continue

    env.cr.commit()
    print("DONE")

mass_sync_dynamic()
