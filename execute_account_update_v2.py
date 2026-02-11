import sys
import json
import xmlrpc.client
import subprocess
import time

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

def execute_updates():
    try:
        result = subprocess.run(['node', 'read_excel_to_json.js'], capture_output=True, text=True, cwd='temp_analysis_tool')
        accounts_data = json.loads(result.stdout)
    except Exception as e:
        print(f"Error reading Excel data: {e}")
        return

    uid, models = get_odoo_connection()
    if not uid: return

    print(f"Reanudando actualización masiva para {len(accounts_data)} cuentas (Modo Lento)...")

    excel_map = {str(acc.get('Numero de Cuenta')): acc for acc in accounts_data if acc.get('Numero de Cuenta')}
    account_numbers = list(excel_map.keys())

    chunk_size = 10 # Smaller chunks
    total_processed = 0
    created_contacts = 0
    updated_contacts = 0
    errors = 0

    for i in range(0, len(account_numbers), chunk_size):
        chunk = account_numbers[i:i+chunk_size]
        
        try:
            domain = [['account_number', 'in', chunk]]
            device_ids = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'search', [domain])
            
            if not device_ids: continue
            
            devices = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'read', [device_ids, ['account_number', 'subscription_id']])
            
            for dev in devices:
                try:
                    if not dev['subscription_id']: continue
                    
                    acc_num = dev['account_number']
                    excel_info = excel_map.get(acc_num)
                    sub_id = dev['subscription_id'][0]
                    
                    sub = models.execute_kw(db, uid, password, 'sentinela.subscription', 'read', [[sub_id], ['partner_id', 'service_address_id']])[0]
                    
                    if not sub['partner_id'] or not sub['service_address_id']: continue
                    
                    p_id = sub['partner_id'][0]
                    s_id = sub['service_address_id'][0]
                    
                    # Clean up data
                    raw_name = excel_info.get('Nombre') or "Sin Nombre"
                    raw_street = excel_info.get('Direccion') or ""
                    
                    # Ensure name isn't already prefixed
                    if raw_name.startswith(f"[{acc_num}]"):
                        new_name = raw_name
                    else:
                        new_name = f"[{acc_num}] {raw_name}"
                        
                    new_street = raw_street
                    new_ref = acc_num

                    current_s_name = sub['service_address_id'][1]
                    if current_s_name == new_name and sub['service_address_id'][0] != sub['partner_id'][0]:
                        print(f"[SKIP] Sub {sub_id}: Ya actualizada.")
                        continue

                    if p_id == s_id:
                        print(f"[CREAR] Sub {sub_id} (Cta: {acc_num}): Creando dir. servicio separada...")
                        vals = {
                            'parent_id': p_id,
                            'type': 'other',
                            'name': new_name,
                            'street': new_street,
                            'ref': new_ref,
                            'comment': 'Dirección de Monitoreo creada automáticamente desde Excel.'
                        }
                        new_contact_id = models.execute_kw(db, uid, password, 'res.partner', 'create', [vals])
                        models.execute_kw(db, uid, password, 'sentinela.subscription', 'write', [[sub_id], {'service_address_id': new_contact_id}])
                        created_contacts += 1
                    else:
                        print(f"[ACTUALIZAR] Sub {sub_id} (Cta: {acc_num}): Actualizando dir. existente...")
                        vals = {
                            'name': new_name,
                            'street': new_street,
                            'ref': new_ref
                        }
                        models.execute_kw(db, uid, password, 'res.partner', 'write', [[s_id], vals])
                        updated_contacts += 1
                    
                    total_processed += 1
                    time.sleep(0.1) # Brief pause per record

                except Exception as inner_e:
                    print(f"Error procesando dispositivo {dev.get('id')}: {inner_e}")
                    errors += 1
            
            time.sleep(1) # Pause between chunks to let server breathe

        except Exception as e:
            print(f"Error en bloque {i}: {e}")
            errors += 1

    print("\n--- FINALIZADO ---")
    print(f"Total Procesados Exitosamente: {total_processed}")
    print(f"Nuevos Contactos Creados: {created_contacts}")
    print(f"Contactos Actualizados: {updated_contacts}")
    print(f"Errores: {errors}")

if __name__ == '__main__':
    execute_updates()
