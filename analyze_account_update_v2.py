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

    print(f"Analizando {len(accounts_data)} cuentas (Modo Optimizado)...")

    uid, models = get_odoo_connection()
    if not uid:
        print("Error connecting to Odoo.")
        return

    # 2. Extract all account numbers from Excel
    excel_map = {str(acc.get('Numero de Cuenta')): acc for acc in accounts_data if acc.get('Numero de Cuenta')}
    account_numbers = list(excel_map.keys())

    # 3. Batch Search in Odoo
    # Search all devices that have one of these account numbers
    domain = [['account_number', 'in', account_numbers]]
    device_ids = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'search', [domain])
    
    # 4. Batch Read Devices
    devices = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'read', [device_ids, ['account_number', 'subscription_id']])
    
    # 5. Collect Subscription IDs
    sub_ids = []
    device_by_sub = {} # Map sub_id -> device info
    
    for dev in devices:
        if dev['subscription_id']:
            s_id = dev['subscription_id'][0]
            sub_ids.append(s_id)
            device_by_sub[s_id] = dev

    # 6. Batch Read Subscriptions (to get service address ID)
    subs = models.execute_kw(db, uid, password, 'sentinela.subscription', 'read', [sub_ids, ['service_address_id', 'name']])
    
    # 7. Collect Address IDs
    addr_ids = []
    sub_by_addr = {} # Map addr_id -> sub info
    
    for sub in subs:
        if sub['service_address_id']:
            a_id = sub['service_address_id'][0]
            addr_ids.append(a_id)
            sub_by_addr[a_id] = sub

    # 8. Batch Read Partners (Addresses)
    partners = models.execute_kw(db, uid, password, 'res.partner', 'read', [addr_ids, ['name', 'street', 'ref']])
    partner_map = {p['id']: p for p in partners}

    # 9. Build Report
    matches = 0
    missing = len(account_numbers) - len(device_ids)
    updates_preview = []

    for sub in subs:
        s_id = sub['id']
        dev = device_by_sub.get(s_id)
        if not dev: continue
        
        acc_num = dev['account_number']
        excel_info = excel_map.get(acc_num)
        
        addr_id = sub['service_address_id'][0] if sub['service_address_id'] else None
        if not addr_id: continue
        
        partner = partner_map.get(addr_id)
        if not partner: continue

        matches += 1
        
        current_name = partner['name']
        current_street = partner['street'] or "Sin Dirección"
        current_ref = partner['ref'] or ""
        
        new_name = f"[{acc_num}] {excel_info.get('Nombre')}"
        new_address = excel_info.get('Direccion')
        
        # Only show if there is a change
        if current_ref != acc_num or new_name != current_name:
            updates_preview.append({
                'account': acc_num,
                'sub': sub['name'],
                'current_partner': current_name,
                'current_address': current_street,
                'new_name': new_name,
                'new_address': new_address,
                'new_ref': acc_num
            })

    print(f"Resumen del Análisis:")
    print(f"- Cuentas en Excel: {len(account_numbers)}")
    print(f"- Dispositivos encontrados en Odoo: {len(devices)}")
    print(f"- Suscripciones vinculadas: {len(subs)}")
    
    print("\n--- EJEMPLOS DE CAMBIOS (Primeros 10) ---")
    for up in updates_preview[:10]:
        print(f"Cuenta: {up['account']} | Sub: {up['sub']}")
        print(f"  Cambio Propuesto:")
        print(f"    - Nombre: '{up['current_partner']}' -> '{up['new_name']}'")
        print(f"    - Dirección: '{up['current_address'][:30]}...' -> '{up['new_address'][:30]}...'")
        print(f"    - Ref: '{up['new_ref']}'")
        print("-" * 40)

if __name__ == '__main__':
    run_analysis()
