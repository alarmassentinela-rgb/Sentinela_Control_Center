import requests
import logging
from odoo import api, SUPERUSER_ID

def run_sync(env):
    print("--- INICIANDO RESCATE DE PRECIOS EN CERO (SYSCOM) ---")
    
    # 1. Configuración
    client_id = 'AE2U6oagC6BZVCSjASwFBUIGkj8M4Hjg'
    client_secret = 'ERWZPV4vYQfWwDt5QGcYqyZb6Zmzc4p2b7iO4Ld5'
    tc = 17.26
    margin = 1.30
    
    # 2. Obtener Token
    try:
        token_url = 'https://developers.syscom.mx/oauth/token'
        res_token = requests.post(token_url, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }, timeout=15)
        token = res_token.json().get('access_token')
        if not token:
            print("Error: No se pudo obtener el token de Syscom.")
            return
    except Exception as e:
        print(f"Error de conexión: {str(e)}")
        return

    headers = {'Authorization': f'Bearer {token}'}
    
    # 3. Buscar productos en Odoo con precio <= 0
    products = env['product.template'].search([
        ('active', '=', True),
        ('list_price', '<=', 0),
        ('default_code', '!=', False)
    ])
    
    print(f"Detectados {len(products)} productos para procesar.")
    
    updated_count = 0
    failed_count = 0
    
    for p in products:
        try:
            # Intentar primero por ID si lo tiene, si no por modelo (default_code)
            if p.syscom_product_id:
                url = f'https://developers.syscom.mx/api/v1/productos/{p.syscom_product_id}'
            else:
                url = f'https://developers.syscom.mx/api/v1/productos?modelo={p.default_code}'
            
            res = requests.get(url, headers=headers, timeout=10).json()
            
            # Si buscamos por modelo, el resultado es una lista o un objeto con resultados
            product_data = {}
            if isinstance(res, list) and len(res) > 0:
                product_data = res[0]
            elif isinstance(res, dict):
                if 'productos' in res and len(res['productos']) > 0:
                    product_data = res['productos'][0]
                elif 'producto_id' in res: # Respuesta directa de ID
                    product_data = res
            
            if product_data and 'precio_lista' in product_data:
                costo_usd = float(product_data.get('precio_lista', 0))
                if costo_usd > 0:
                    new_price = costo_usd * tc * margin
                    p.write({
                        'standard_price': costo_usd * tc,
                        'list_price': new_price,
                        'syscom_product_id': product_data.get('producto_id'),
                        'syscom_model': product_data.get('modelo')
                    })
                    print(f"✅ [{p.default_code}] Actualizado: ${new_price:.2f}")
                    updated_count += 1
                else:
                    print(f"⚠️ [{p.default_code}] Encontrado en Syscom pero sin precio de lista.")
                    failed_count += 1
            else:
                print(f"❌ [{p.default_code}] No encontrado en el catálogo de Syscom.")
                failed_count += 1
                
        except Exception as e:
            print(f"🚨 [{p.default_code}] Error procesando: {str(e)}")
            failed_count += 1

    env.cr.commit()
    print(f"
--- RESUMEN ---")
    print(f"Actualizados con éxito: {updated_count}")
    print(f"No encontrados/sin precio: {failed_count}")
    print("--- FIN DEL PROCESO ---")

if __name__ == "__main__":
    run_sync(env)
