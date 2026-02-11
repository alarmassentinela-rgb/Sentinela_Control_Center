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
    try:
        result = subprocess.run(['node', 'read_excel_to_json.js'], capture_output=True, text=True, cwd='temp_analysis_tool')
        accounts_data = json.loads(result.stdout)
    except Exception as e:
        print(f"Error reading Excel data: {e}")
        return

    print(f"Analizando {len(accounts_data)} cuentas del archivo Excel...")

    uid, models = get_odoo_connection()
    if not uid:
        print("Error connecting to Odoo.")
        return

    matches = 0
    missing = 0
    skipped_no_addr = 0
    updates_preview = []

    print("\n--- INICIO DE SIMULACIÓN ---\n")

    for acc in accounts_data:
        acc_num = str(acc.get('Numero de Cuenta'))
        new_name = acc.get('Nombre')
        new_address = acc.get('Direccion')

        if not acc_num: continue

        device_ids = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'search', [[['account_number', '=', acc_num]]])
        
        if device_ids:
            device = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'read', [device_ids[0], ['subscription_id']])
            sub_data = device[0].get('subscription_id')
            
            if sub_data:
                sub_id = sub_data[0]
                sub_name = sub_data[1]
                
                sub_record = models.execute_kw(db, uid, password, 'sentinela.subscription', 'read', [sub_id, ['service_address_id']])
                
                if not sub_record[0]['service_address_id']:
                    skipped_no_addr += 1
                    continue

                addr_id = sub_record[0]['service_address_id'][0]
                addr_current_name = sub_record[0]['service_address_id'][1]
                
                addr_record = models.execute_kw(db, uid, password, 'res.partner', 'read', [addr_id, ['street', 'ref']])
                current_street = addr_record[0]['street'] or "Sin Dirección"
                
                matches += 1
                
                proposed_name = f"[{acc_num}] {new_name}"
                
                updates_preview.append({
                    'account': acc_num,
                    'sub': sub_name,
                    'current_partner': addr_current_name,
                    'current_address': current_street,
                    'new_name': proposed_name,
                    'new_address': new_address,
                    'new_ref': acc_num
                })
        else:
            missing += 1

    print(f"Resumen del Análisis:")
    print(f"- Cuentas en Excel: {len(accounts_data)}")
    print(f"- Coincidencias encontradas: {matches}")
    print(f"- Cuentas SIN dispositivo en Odoo: {missing}")
    print(f"- Suscripciones sin dirección (saltadas): {skipped_no_addr}")
    
    print("\n--- EJEMPLOS DE CAMBIOS (Primeros 10) ---")
    for up in updates_preview[:10]:
        print(f"Cuenta: {up['account']} | Sub: {up['sub']}")
        print(f"  Cambio Propuesto:")
        print(f"    - Nombre: '{up['current_partner']}' -> '{up['new_name']}'")
        print(f"    - Dirección: '{up['current_address'][:30]}...' -> '{up['new_address'][:30]}...'")
        print(f"    - Ref: -> '{up['new_ref']}'")
        print("-" * 40)

if __name__ == '__main__':
    run_analysis()