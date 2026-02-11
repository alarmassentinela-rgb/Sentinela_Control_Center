import xmlrpc.client
import os

# Configuración
url = 'http://localhost:8069'
db = 'Sentinela_V18'
username = 'admin'
password = 'admin'

def update_module():
    print(f"Conectando para actualizar módulos...")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print("Error de autenticación.")
            return
        
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # 1. Buscar el módulo
        module_ids = models.execute_kw(db, uid, password, 'ir.module.module', 'search', [[('name', '=', 'sentinela_subscriptions')]])
        if module_ids:
            print(f"Actualizando módulo sentinela_subscriptions (ID: {module_ids[0]})...")
            # 2. Marcar para actualización
            models.execute_kw(db, uid, password, 'ir.module.module', 'button_immediate_upgrade', [module_ids])
            print("¡ÉXITO! El módulo se ha mandado a actualizar. Recarga tu navegador en un momento.")
        else:
            print("No se encontró el módulo sentinela_subscriptions.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_module()
