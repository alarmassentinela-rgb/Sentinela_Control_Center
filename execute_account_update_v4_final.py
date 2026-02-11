import sys
import json
import xmlrpc.client
import subprocess
import time
import socket

# Timeout global
socket.setdefaulttimeout(60)

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
    except Exception as e:
        print(f"Error conexión: {e}")
        return None, None

def execute_updates():
    try:
        result = subprocess.run(['node', 'read_excel_to_json.js'], capture_output=True, text=True, cwd='temp_analysis_tool')
        accounts_data = json.loads(result.stdout)
    except Exception as e:
        print(f"Error reading Excel data: {e}")
        return

    print(f"Iniciando actualización FINAL para {len(accounts_data)} cuentas...")
    print("Asegúrate de haber actualizado el módulo 'sentinela_subscriptions' antes de correr esto.")

    excel_map = {str(acc.get('Numero de Cuenta')): acc for acc in accounts_data if acc.get('Numero de Cuenta')}
    account_numbers = list(excel_map.keys())

    chunk_size = 20 
    total_processed = 0
    errors = 0

    for i in range(0, len(account_numbers), chunk_size):
        chunk = account_numbers[i:i+chunk_size]
        print(f"Procesando chunk {i//chunk_size + 1}: {chunk}")
        
        uid, models = get_odoo_connection()
        if not uid:
            print("Reconectando...")
            time.sleep(5)
            uid, models = get_odoo_connection()
            if not uid: continue

        try:
            # Search Devices
            domain = [['account_number', 'in', chunk]]
            device_ids = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'search', [domain])
            
            if not device_ids: 
                print(f"No se encontraron dispositivos para el chunk {i//chunk_size + 1}")
                continue
            
            print(f"Encontrados {len(device_ids)} dispositivos en el chunk")
            
            devices = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'read', [device_ids, ['account_number', 'subscription_id']])
            
            for dev in devices:
                try:
                    acc_num = dev['account_number']
                    if not dev['subscription_id']: 
                        print(f"Dispositivo {acc_num} sin suscripción")
                        continue
                    excel_info = excel_map.get(acc_num)
                    sub_id = dev['subscription_id'][0]
                    
                    # 1. Update Subscription Field (The NEW field)
                    # We do this regardless of contact status to ensure all subs get the account number field filled
                    models.execute_kw(db, uid, password, 'sentinela.subscription', 'write', [[sub_id], {
                        'monitoring_account_number': acc_num
                    }])
                    
                    # 2. Handle Contact Logic (Create Child vs Update)
                    sub = models.execute_kw(db, uid, password, 'sentinela.subscription', 'read', [[sub_id], ['partner_id', 'service_address_id']])[0]
                    
                    if not sub['partner_id']: continue
                    
                    p_id = sub['partner_id'][0]
                    s_id = sub['service_address_id'][0] if sub['service_address_id'] else p_id
                    
                    raw_name = excel_info.get('Nombre') or "Sin Nombre"
                    raw_street = excel_info.get('Direccion') or ""
                    
                    if raw_name.startswith(f"[{acc_num}]"):
                        new_name = raw_name
                    else:
                        new_name = f"[{acc_num}] {raw_name}"
                    
                    # Check if contact needs update
                    # Optimization: Read current name first?
                    # We just write to ensure consistency.
                    
                    if p_id == s_id:
                        print(f"[CREAR+CAMPO] Sub {sub_id}: Nuevo contacto + Campo '{acc_num}'")
                        vals = {
                            'parent_id': p_id,
                            'type': 'other',
                            'name': new_name,
                            'street': raw_street,
                            'ref': acc_num,
                            'comment': 'Auto-created from Excel'
                        }
                        new_contact_id = models.execute_kw(db, uid, password, 'res.partner', 'create', [vals])
                        models.execute_kw(db, uid, password, 'sentinela.subscription', 'write', [[sub_id], {'service_address_id': new_contact_id}])
                    else:
                        print(f"[ACTUALIZAR+CAMPO] Sub {sub_id}: Contacto Existente + Campo '{acc_num}'")
                        vals = {
                            'name': new_name,
                            'street': raw_street,
                            'ref': acc_num
                        }
                        models.execute_kw(db, uid, password, 'res.partner', 'write', [[s_id], vals])
                    
                    total_processed += 1

                except Exception as inner_e:
                    print(f"Error en Sub {sub_id}: {inner_e}")
                    errors += 1
            
            time.sleep(0.5)

        except Exception as e:
            print(f"Error bloque: {e}")
            errors += 1

    print(f"Finalizado. Procesados: {total_processed}. Errores: {errors}")

if __name__ == '__main__':
    execute_updates()
