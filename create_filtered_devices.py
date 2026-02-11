import json

with open('/tmp/cuentas_data.json', 'r') as f:
    data = json.load(f)

print("--- INICIANDO CREACION FILTRADA DE DISPOSITIVOS FALTANTES ---")
created = 0
orphans = []

for item in data:
    acc_num = str(item.get('Numero de Cuenta'))
    full_name = item.get('Nombre')
    address = item.get('Direccion')
    
    if not acc_num or acc_num == 'None': continue
    
    # 1. Verificar si ya existe (por si acaso)
    device = env['sentinela.monitoring.device'].search([('account_number', '=', acc_num)], limit=1)
    if device: continue # Ya procesado anteriormente
    
    # 2. Buscar al Cliente por el nombre que viene en el Excel
    # Intentamos busqueda exacta o parcial
    partner = env['res.partner'].search(['|', ('name', '=', full_name), ('name', 'ilike', full_name)], limit=1)
    
    if partner:
        # CLIENTE ENCONTRADO -> Crear Dispositivo y Direccion
        print(f"[RESCATADO] Cta {acc_num} vinculada a Cliente: {partner.name}")
        
        # Crear direccion hija de servicio
        child = env['res.partner'].create({
            'parent_id': partner.id,
            'type': 'other',
            'name': f"[{acc_num}] {full_name}",
            'street': address,
            'ref': acc_num,
            'comment': 'Creado automaticamente desde Excel (Dispositivo faltante)'
        })
        
        # Crear el dispositivo
        env['sentinela.monitoring.device'].create({
            'name': f"{acc_num} - {full_name}",
            'device_id': acc_num,
            'account_number': acc_num,
            'partner_id': partner.id,
            'status': 'active',
            'device_type': 'control_panel',
            'protocol': 'contact_id'
        })
        created += 1
    else:
        # CLIENTE NO ENCONTRADO -> Huérfano
        orphans.append(f"Cta: {acc_num} | Nombre en Excel: {full_name}")

env.cr.commit()

print(f"\n--- RESULTADO FINAL ---")
print(f"Dispositivos rescatados y creados: {created}")
print(f"Cuentas sin cliente registrado (NO creadas): {len(orphans)}")
for o in orphans:
    print(o)
