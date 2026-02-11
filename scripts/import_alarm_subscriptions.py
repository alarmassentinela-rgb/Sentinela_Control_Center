import csv
import xmlrpc.client
import sys
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
URL = "http://192.168.3.2:8070"
DB = "Sentinela_V18"
USERNAME = "api_user"
PASSWORD = "admin"

# Ruta del archivo a importar
INPUT_FILE = 'errores_importacion.csv'

def parse_date(date_str):
    if not date_str: return False
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except:
            return False

def main():
    print("=== Iniciando Importación Optimizada ===")
    
    # 1. Establecer conexión única
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        # Intentar login simplificado
        uid = common.authenticate(DB, USERNAME, PASSWORD, {})
        if not uid:
            print("❌ Error de login.")
            return
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        print(f"✅ Conectado como UID: {uid}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        # Si falla, intentar sin el diccionario vacio
        try:
            uid = common.authenticate(DB, USERNAME, PASSWORD, [])
            models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
            print(f"✅ Conectado (fallback) UID: {uid}")
        except:
            return

    # 2. Cargar CSV
    rows = []
    try:
        with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
    except:
        with open(INPUT_FILE, mode='r', encoding='latin-1') as f:
            rows = list(csv.DictReader(f))

    print(f"Procesando {len(rows)} registros...")
    
    success = 0
    errors = 0

    for i, row in enumerate(rows, 1):
        try:
            p_name = row['partner_id'].strip()
            p_code = row['product_id'].strip()
            
            print(f"[{i}/{len(rows)}] {p_name}...", end=" ", flush=True)

            # A. Obtener Partner
            res = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', '=', p_name]]])
            if res:
                partner_id = res[0]
            else:
                partner_id = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'create', [{'name': p_name}])
            
            # B. Obtener Producto
            res = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'search', [[['default_code', '=', p_code]]])
            if res:
                product_id = res[0]
            else:
                # Crear producto si no existe
                product_id = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'create', [{
                    'name': f"Servicio {p_code}",
                    'default_code': p_code,
                    'type': 'service',
                    'is_subscription': True,
                    'list_price': float(row.get('price_unit') or 0)
                }])

            # C. Crear Suscripción
            sub_vals = {
                'partner_id': partner_id,
                'product_id': product_id,
                'price_unit': float(row.get('price_unit') or 0),
                'start_date': parse_date(row.get('start_date')) or datetime.now().strftime("%Y-%m-%d"),
                'next_billing_date': parse_date(row.get('next_billing_date')) or datetime.now().strftime("%Y-%m-%d"),
                'service_type': 'alarm',
                'recurring_interval': row.get('recurring_interval', '1'),
                'state': 'active'
            }
            sub_id = models.execute_kw(DB, uid, PASSWORD, 'sentinela.subscription', 'create', [sub_vals])

            # D. Crear Dispositivo
            acc = row.get('account_number')
            if acc:
                # Verificar si ya existe el dispositivo
                exists = models.execute_kw(DB, uid, PASSWORD, 'sentinela.monitoring.device', 'search', [[['account_number', '=', acc]]])
                if not exists:
                    models.execute_kw(DB, uid, PASSWORD, 'sentinela.monitoring.device', 'create', [{
                        'name': f"Panel {acc} - {p_name}",
                        'account_number': acc,
                        'device_id': acc,
                        'partner_id': partner_id,
                        'subscription_id': sub_id,
                        'device_type': 'control_panel',
                        'protocol': 'contact_id'
                    }])
            
            print("✅ OK")
            success += 1
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            errors += 1
            # Pausa pequeña en caso de error para no saturar
            time.sleep(0.5)

    print(f"\nFIN: {success} exitosos, {errors} errores.")

if __name__ == '__main__':
    main()
