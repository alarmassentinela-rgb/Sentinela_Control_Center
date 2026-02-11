import csv
import os

csv_file = '/mnt/extra-addons/sentinela_subscriptions/importacion_final_odoo.csv'

def main():
    print("Leyendo CSV...")
    try:
        with open(csv_file, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)[:5] # 5 primeros
    except FileNotFoundError:
        print(f"Error: No encuentro {csv_file}. Asegurate de subirlo a addons.")
        return

    print(f"Probando importación de {len(rows)} registros...")

    for i, row in enumerate(rows):
        print(f"\n--- Registro {i+1}: {row['partner_id']} ---")
        
        # 1. Buscar Partner
        partner = env['res.partner'].search([('name', '=', row['partner_id'])], limit=1)
        if not partner:
            print(f"  > Cliente no existe, creando: {row['partner_id']}")
            partner = env['res.partner'].create({'name': row['partner_id']})
        
        # 2. Buscar Producto
        product = env['product.product'].search([('name', '=', row['product_id'])], limit=1)
        if not product:
            print(f"  > ERROR: Producto no encontrado: {row['product_id']}")
            continue

        # 3. Datos
        vals = {
            'partner_id': partner.id,
            'product_id': product.id,
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

        # 4. Crear
        try:
            sub = env['sentinela.subscription'].create(vals)
            print(f"  > ÉXITO: Suscripción creada: {sub.name}")
            # env.cr.commit() # Descomentar para guardar cambios reales
        except Exception as e:
            print(f"  > FALLO: {e}")
            env.cr.rollback()

if __name__ == '__main__':
    main()
