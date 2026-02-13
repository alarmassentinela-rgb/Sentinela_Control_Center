import requests
import logging
import time
from odoo import models, fields, api

def mass_sync_dynamic():
    # 1. Credenciales
    client_id = 'AE2U6oagC6BZVCSjASwFBUIGkj8M4Hjg'
    client_secret = 'ERWZPV4vYQfWwDt5QGcYqyZb6Zmzc4p2b7iO4Ld5'
    token_url = "https://developers.syscom.mx/oauth/token"
    api_url = 'https://developers.syscom.mx/api/v1'

    print("--- INICIANDO ACTUALIZACIÓN DINÁMICA SYSCOM (TC REAL) ---")
    
    # 2. Obtener Token
    try:
        res = requests.post(token_url, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }, timeout=20)
        token = res.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        print("✅ Conexión establecida con Syscom.")
    except Exception as e:
        print(f"❌ Error crítico de conexión: {e}")
        return

    # 3. Obtener TIPO DE CAMBIO REAL
    try:
        res_tc = requests.get(f"{api_url}/tipocambio", headers=headers, timeout=10)
        tc_data = res_tc.json()
        tc = float(tc_data.get('normal', 17.26))
        print(f"💹 Tipo de Cambio obtenido: ${tc} MXN/USD")
    except Exception as e:
        tc = 17.26
        print(f"⚠️ No se pudo obtener TC dinámico, usando preventivo: ${tc}")

    # 4. Buscar productos para procesar
    products = env['product.template'].search([
        ('default_code', '!=', False),
        ('detailed_type', 'in', ['product', 'consu'])
    ])

    total = len(products)
    print(f"📦 Total de productos a procesar: {total}")

    count = 0
    success = 0
    errors = 0

    for prod in products:
        count += 1
        model = prod.default_code
        
        try:
            sys_id = prod.syscom_id
            
            # Si no tiene ID, buscarlo por modelo
            if not sys_id:
                search_res = requests.get(f"{api_url}/productos?busqueda={model}", headers=headers, timeout=10)
                if search_res.status_code == 200:
                    results = search_res.json().get('productos', [])
                    if results:
                        sys_id = str(results[0].get('producto_id'))
                    else:
                        errors += 1
                        continue
                else:
                    errors += 1
                    continue

            # Obtener detalle y precio real
            detail_res = requests.get(f"{api_url}/productos/{sys_id}", headers=headers, timeout=10)
            if detail_res.status_code == 200:
                detail = detail_res.json()
                precios = detail.get('precios', {})
                cost_usd = float(precios.get('precio_descuento') or precios.get('precio_1') or 0.0)
                
                # Actualizar en Odoo
                prod.write({
                    'syscom_id': sys_id,
                    'syscom_price_usd': cost_usd,
                    'standard_price': cost_usd * tc,
                    'syscom_last_update': fields.Datetime.now()
                })
                success += 1
            
            # Reportar progreso cada 50
            if count % 50 == 0:
                print(f"⏳ Progreso: {count}/{total} | TC: {tc} | Éxitos: {success}")
                env.cr.commit() 
                time.sleep(0.5)

        except Exception as e:
            errors += 1
            continue

    env.cr.commit()
    print(f"
✅ ACTUALIZACIÓN FINALIZADA CON TC ${tc} ✅")
    print(f"Resumen: Total: {total} | Éxitos: {success} | Errores: {errors}")

mass_sync_dynamic()
