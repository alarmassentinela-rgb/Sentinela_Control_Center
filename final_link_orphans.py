import json

with open('/tmp/cuentas_huerfanas_listas.json', 'r') as f:
    data = json.load(f)

print("--- INICIANDO VINCULACION FINAL DE HUERFANOS ---")
linked = 0
failed = []

for item in data:
    acc_num = str(item.get('Cuenta'))
    odoo_name = item.get('Nombre en Odoo (RELLENAR)')
    central_name = item.get('Nombre en Central')
    
    if not odoo_name:
        continue # Si dejaste la celda vacía, saltar
        
    # Buscar al Cliente en Odoo
    partner = env['res.partner'].search([('name', '=', odoo_name)], limit=1)
    
    if partner:
        # 1. Crear Direccion de Servicio
        # Buscamos si ya existe para no duplicar
        child = env['res.partner'].search([
            ('parent_id', '=', partner.id),
            ('name', '=', f"[{acc_num}] {central_name}")
        ], limit=1)
        
        if not child:
            child = env['res.partner'].create({
                'parent_id': partner.id,
                'type': 'other',
                'name': f"[{acc_num}] {central_name}",
                'ref': acc_num,
                'comment': 'Vinculado manualmente desde Excel de Huerfanos.'
            })
        
        # 2. Crear/Actualizar Dispositivo
        device = env['sentinela.monitoring.device'].search([('account_number', '=', acc_num)], limit=1)
        if not device:
            env['sentinela.monitoring.device'].create({
                'name': f"{acc_num} - {central_name}",
                'device_id': acc_num,
                'account_number': acc_num,
                'partner_id': partner.id,
                'status': 'active',
                'protocol': 'contact_id',
                'device_type': 'control_panel'
            })
        else:
            device.write({'partner_id': partner.id})
            
        print(f"[EXITO] Cta {acc_num} vinculada a {partner.name}")
        linked += 1
    else:
        failed.append(f"Cta: {acc_num} | Motivo: El nombre '{odoo_name}' no existe en Odoo exactamente asi.")

env.cr.commit()
print(f"\n--- RESUMEN ---")
print(f"Cuentas vinculadas con exito: {linked}")
print(f"Cuentas fallidas: {len(failed)}")
for f in failed:
    print(f)
