import csv
import xmlrpc.client
import time

# Configuración
url = 'http://localhost:8069'
db = 'Sentinela_V18'
username = 'admin' # Asumo admin
password = 'admin' 
csv_file = '/mnt/c/Users/dell/DellCli/sentinela_subscriptions/importacion_final_odoo.csv'

def main():
    print("Conectando a Odoo...")
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    # Intentar autenticar (esto valida si la pass es admin, si no, fallará y me dirás)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Error de autenticación. Verifica credenciales.")
        return

    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    print("Leyendo CSV...")
    with open(csv_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)[:5] # Solo 5 primeros

    print(f"Probando importación de {len(rows)} registros...")

    for i, row in enumerate(rows):
        print(f"\n--- Registro {i+1}: {row['partner_id']} ---")
        
        # 1. Buscar Partner
        partner_id = models.execute_kw(db, uid, password, 'res.partner', 'search', [[['name', '=', row['partner_id']]]])
        if not partner_id:
            # Si no existe, lo creamos para la prueba (simulando importación real)
            print(f"  > Cliente no existe, creando: {row['partner_id']}")
            partner_id = [models.execute_kw(db, uid, password, 'res.partner', 'create', [{'name': row['partner_id']}] )]
        
        # 2. Buscar Producto
        product_id = models.execute_kw(db, uid, password, 'product.product', 'search', [[['name', '=', row['product_id']]]])
        if not product_id:
            print(f"  > ERROR: Producto no encontrado: {row['product_id']}")
            continue

        # 3. Preparar Datos
        vals = {
            'partner_id': partner_id[0],
            'product_id': product_id[0],
            'service_type': row['service_type'],
            'price_unit': float(row['price_unit'] or 0),
            'start_date': row['start_date'],
            'next_billing_date': row['next_billing_date'],
            'pppoe_user': row['pppoe_user'],
            'pppoe_password': row['pppoe_password'],
            'equipment_ownership': row['equipment_ownership'],
            'technical_state': row['technical_state'],
            'state': row['state'],
            'description': row['description']
        }

        # 4. Intentar Crear
        try:
            sub_id = models.execute_kw(db, uid, password, 'sentinela.subscription', 'create', [vals])
            print(f"  > ÉXITO: Suscripción creada con ID {sub_id}")
            
            # Borrar para limpiar
            # models.execute_kw(db, uid, password, 'sentinela.subscription', 'unlink', [[sub_id]])
            # print("  > (Borrada para limpieza)")
            
        except Exception as e:
            print(f"  > FALLO: {e}")

if __name__ == '__main__':
    main()
