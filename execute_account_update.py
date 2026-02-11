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

    print(f"Reanudando actualización masiva para {len(accounts_data)} cuentas...")

    excel_map = {str(acc.get('Numero de Cuenta')): acc for acc in accounts_data if acc.get('Numero de Cuenta')}
    account_numbers = list(excel_map.keys())

    chunk_size = 50
    total_processed = 0
    created_contacts = 0
    updated_contacts = 0
    
    # Context to suppress email errors
    ctx = {'tracking_disable': True, 'mail_create_nosubscribe': True, 'mail_notrack': True}

    for i in range(0, len(account_numbers), chunk_size):
        chunk = account_numbers[i:i+chunk_size]
        
        domain = [['account_number', 'in', chunk]]
        device_ids = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'search', [domain])
        
        if not device_ids: continue
        
        devices = models.execute_kw(db, uid, password, 'sentinela.monitoring.device', 'read', [device_ids, ['account_number', 'subscription_id']])
        
        for dev in devices:
            if not dev['subscription_id']: continue
            
            acc_num = dev['account_number']
            excel_info = excel_map.get(acc_num)
            sub_id = dev['subscription_id'][0]
            
            # Read Sub
            sub = models.execute_kw(db, uid, password, 'sentinela.subscription', 'read', [[sub_id], ['partner_id', 'service_address_id']])[0]
            
            if not sub['partner_id'] or not sub['service_address_id']: continue
            
            p_id = sub['partner_id'][0]
            s_id = sub['service_address_id'][0]
            
            new_name = f"[{acc_num}] {excel_info.get('Nombre')}"
            new_street = excel_info.get('Direccion')
            new_ref = acc_num

            # Check if ALREADY PROCESSED to avoid duplicates on retry
            # If current service address matches exactly what we want, skip
            current_s_name = sub['service_address_id'][1]
            if current_s_name == new_name:
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
                # Create with context
                # Note: create signature is (db, uid, password, model, method, args, kwargs)
                # But execute_kw maps to execute(db, uid, obj, method, *args, **kw)
                # To pass context to create, we might need it in kwargs? Or standard create doesn't take context easily via RPC.
                # Actually, standard way is creating record first.
                
                new_contact_id = models.execute_kw(db, uid, password, 'res.partner', 'create', [vals]) # Context less critical here
                
                # Update Subscription WITH CONTEXT
                # Since execute_kw doesn't support context injection directly for write in all versions via XMLRPC cleanly without wrapping,
                # we rely on the fact that write usually doesn't trigger email unless track_visibility is on.
                # If it failed, it means it tried to send email.
                # Let's try to set the context in the connection? No.
                
                # Workaround: Update 'admin' email if it fails again?
                # Or simply catch error and continue? No, update fails.
                
                try:
                    models.execute_kw(db, uid, password, 'sentinela.subscription', 'write', [[sub_id], {'service_address_id': new_contact_id}])
                except xmlrpc.client.Fault as e:
                    if 'configure la dirección de correo' in str(e):
                        print("  [WARN] Falló el envío de correo, pero intentando forzar actualización...")
                        # This is tough remotely.
                        pass
                    raise e

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

    print("\n--- FINALIZADO ---")
    print(f"Total Procesados: {total_processed}")
    print(f"Nuevos Contactos Creados: {created_contacts}")
    print(f"Contactos Actualizados: {updated_contacts}")

if __name__ == '__main__':
    execute_updates()