import requests
import logging
from odoo import models, fields, api

def test_sync():
    # 1. Credenciales
    client_id = 'AE2U6oagC6BZVCSjASwFBUIGkj8M4Hjg'
    client_secret = 'ERWZPV4vYQfWwDt5QGcYqyZb6Zmzc4p2b7iO4Ld5'
    token_url = "https://developers.syscom.mx/oauth/token"
    api_url = 'https://developers.syscom.mx/api/v1'

    print("--- INICIANDO PRUEBA DE SINCRONIZACIÓN SYSCOM ---")
    
    # 2. Obtener Token
    try:
        res = requests.post(token_url, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        })
        token = res.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        print("✅ Token obtenido con éxito.")
    except Exception as e:
        print(f"❌ Error al obtener token: {e}")
        return

    # 3. Buscar 5 productos en Odoo que no tengan syscom_id
    products = env['product.template'].search([
        ('syscom_id', '=', False),
        ('default_code', '!=', False),
        ('detailed_type', 'in', ['product', 'consu'])
    ], limit=5)

    print(f"🔍 Procesando {len(products)} productos para vinculación...")

    for prod in products:
        model = prod.default_code
        print(f"
Buscando modelo: {model}")
        
        try:
            # Buscar en Syscom por modelo
            search_res = requests.get(f"{api_url}/productos?busqueda={model}", headers=headers, timeout=10)
            if search_res.status_code == 200:
                results = search_res.json().get('productos', [])
                if results:
                    # Tomar el primer resultado exacto
                    sys_prod = results[0]
                    syscom_id = str(sys_prod.get('producto_id'))
                    
                    # Obtener detalle completo para tener el precio real
                    detail_res = requests.get(f"{api_url}/productos/{syscom_id}", headers=headers, timeout=10)
                    detail = detail_res.json()
                    
                    precios = detail.get('precios', {})
                    cost_usd = float(precios.get('precio_descuento') or precios.get('precio_1') or 0.0)
                    
                    # Guardar en Odoo
                    prod.write({
                        'syscom_id': syscom_id,
                        'syscom_price_usd': cost_usd,
                        'standard_price': cost_usd * 20.0, # Asumiendo un TC de 20 para la prueba
                        'syscom_last_update': fields.Datetime.now()
                    })
                    print(f"✅ Vinculado: {model} -> ID Syscom: {syscom_id} | Costo USD: {cost_usd}")
                else:
                    print(f"⚠️ No se encontró el modelo {model} en Syscom.")
            else:
                print(f"❌ Error API Syscom ({search_res.status_code}) para {model}")
        except Exception as e:
            print(f"❌ Error procesando {model}: {e}")

    env.cr.commit()
    print("
--- PRUEBA FINALIZADA ---")

test_sync()
