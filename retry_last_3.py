import json

# Datos de las 3 cuentas fallidas
retry_data = [
    {'Cuenta': '1223', 'Nombre en Odoo': 'JUAN PADILLA', 'Nombre en Central': 'Juan Padilla '},
    {'Cuenta': '1243', 'Nombre en Odoo': 'DIVISAS FRONTERA LONGORIA', 'Nombre en Central': 'Centro Cambiario Divisas Frontera Suc Sexta / PLAN BASICO'},
    {'Cuenta': '1296', 'Nombre en Odoo': 'VIVIANA LIRA', 'Nombre en Central': 'Viviana Lira    / PLAN ESTANDAR'}
]

print("--- REINTENTANDO VINCULACION FLEXIBLE (3 CUENTAS) ---")

for item in retry_data:
    acc_num = item['Cuenta']
    odoo_name = item['Nombre en Odoo'].strip()
    central_name = item['Nombre en Central']
    
    # Busqueda flexible (ilike)
    partner = env['res.partner'].search([('name', 'ilike', odoo_name)], limit=1)
    
    if partner:
        # Crear Direccion de Servicio
        child = env['res.partner'].create({
            'parent_id': partner.id,
            'type': 'other',
            'name': f"[{acc_num}] {central_name}",
            'ref': acc_num
        })
        
        # Crear Dispositivo
        env['sentinela.monitoring.device'].create({
            'name': f"{acc_num} - {central_name}",
            'device_id': acc_num,
            'account_number': acc_num,
            'partner_id': partner.id,
            'status': 'active',
            'protocol': 'contact_id',
            'device_type': 'control_panel'
        })
        print(f"[RESCATADO] Cta {acc_num} vinculada a {partner.name}")
    else:
        print(f"[FALLA] Cta {acc_num}: No se encontro nada parecido a '{odoo_name}'")

env.cr.commit()
