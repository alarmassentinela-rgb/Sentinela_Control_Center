import sys
import json
import xmlrpc.client
import subprocess

url = "http://192.168.3.2:8070"
db = "Sentinela_V18"
username = "api_user"
password = "admin"

def get_odoo_connection():
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, [])
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        return uid, models
    except:
        return None, None

def run_analysis():
    # 1. Get Data from Excel
    try:
        result = subprocess.run(['node', 'read_excel_to_json.js'], capture_output=True, text=True, cwd='temp_analysis_tool')
        accounts_data = json.loads(result.stdout)
    except Exception as e:
        print(f"Error reading Excel data: {e}")
        return

    print(f"Analizando {len(accounts_data)} cuentas (Verificación Fiscal)...")

    uid, models = get_odoo_connection()
    if not uid: return

    # 2. Extract account numbers
    excel_map = {str(acc.get('Numero de Cuenta')): acc for acc in accounts_data if acc.get('Numero de Cuenta')}
    account_numbers = list(excel_map.keys())

    # 3. Batch Search Devices
    domain = [['account_number', 'in', account_numbers]]
    device_ids = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'search', [domain])
    
    # 4. Batch Read Devices
    devices = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'read', [device_ids, ['account_number', 'subscription_id']])
    
    # 5. Map Subscriptions
    sub_ids = [d['subscription_id'][0] for d in devices if d['subscription_id']]
    
    # 6. Read Subscriptions (Get Partner AND Service Address)
    subs = models.execute_kw(db, uid, password, 'sentinela.subscription', 'read', [sub_ids, ['name', 'partner_id', 'service_address_id']])
    
    # 7. Analyze Impact
    action_create_child = 0
    action_update_existing = 0
    
    print("\n--- EJEMPLO DE ACCIONES A TOMAR ---")
    
    count = 0
    for sub in subs:
        if not sub['partner_id'] or not sub['service_address_id']: continue
        
        p_id = sub['partner_id'][0]
        s_id = sub['service_address_id'][0]
        s_name = sub['service_address_id'][1]
        
        # Find the account number for this sub
        # (Inefficient lookup here but fine for reporting)
        acc_num = None
        for dev in devices:
            if dev['subscription_id'] and dev['subscription_id'][0] == sub['id']:
                acc_num = dev['account_number']
                break
        
        if not acc_num: continue
        excel_info = excel_map.get(acc_num)
        new_name_fmt = f"[{acc_num}] {excel_info.get('Nombre')}"

        action = ""
        if p_id == s_id:
            action_create_child += 1
            action = "CREAR HIJO (Proteger Fiscal)"
        else:
            action_update_existing += 1
            action = "ACTUALIZAR EXISTENTE"

        if count < 10:
            print(f"Sub: {sub['name']} | Cuenta: {acc_num}")
            print(f"  Estado Actual: Cliente ID {p_id} == Dir. Servicio ID {s_id} ? -> {p_id == s_id}")
            print(f"  Acción: {action}")
            print(f"  Nuevo Nombre: {new_name_fmt}")
            print("-" * 40)
            count += 1

    print("\n--- RESUMEN DE IMPACTO ---")
    print(f"Total de Suscripciones a procesar: {len(subs)}")
    print(f"Casos Seguros (Actualizar dir existente): {action_update_existing}")
    print(f"Casos Riesgosos (Requieren crear dir hija): {action_create_child}")
    print("--------------------------")
    print("Si procedes, el sistema creará automáticamente las direcciones hijas")
    print("para los casos riesgosos, asegurando que NO se toque la facturación.")

if __name__ == '__main__':
    run_analysis()
