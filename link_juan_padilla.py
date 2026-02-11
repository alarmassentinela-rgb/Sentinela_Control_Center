# Buscar a Juan Padilla sin filtros de 'Cliente'
partner = env['res.partner'].search([('name', 'ilike', 'Juan Padilla')], limit=1)

if partner:
    acc_num = '1223'
    central_name = 'Juan Padilla '
    
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
    print(f"[RESCATADO] Cta {acc_num} vinculada al EMPLEADO/CONTACTO: {partner.name}")
    env.cr.commit()
else:
    print("[FALLA] Ni siquiera como contacto interno se encontro a 'Juan Padilla'")
