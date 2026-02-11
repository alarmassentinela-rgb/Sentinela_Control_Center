import json

# Cargar datos desde el JSON que ya subimos
with open('/tmp/cuentas_data.json', 'r') as f:
    data = json.load(f)

print(f"Iniciando actualizacion de {len(data)} registros...")
count = 0

for item in data:
    acc_num = str(item.get('Numero de Cuenta'))
    new_name = item.get('Nombre')
    new_address = item.get('Direccion')
    
    if not acc_num or acc_num == 'None':
        continue
    
    # Buscar dispositivo por numero de cuenta
    device = env['sentinela.monitoring.device'].search([('account_number', '=', acc_num)], limit=1)
    
    if device and device.subscription_id:
        sub = device.subscription_id
        
        # 1. Actualizar el nuevo campo de cuenta en la suscripcion
        sub.write({'monitoring_account_number': acc_num})
        
        # 2. Gestionar direccion de servicio (Separada de la fiscal)
        p_id = sub.partner_id
        s_id = sub.service_address_id
        name_fmt = f"[{acc_num}] {new_name}"
        
        if p_id == s_id:
            # Caso Riesgo: Crear contacto hijo nuevo
            child = env['res.partner'].create({
                'parent_id': p_id.id,
                'type': 'other',
                'name': name_fmt,
                'street': new_address,
                'ref': acc_num,
                'comment': 'Creado automaticamente desde importacion masiva.'
            })
            sub.write({'service_address_id': child.id})
        else:
            # Caso Seguro: Actualizar el contacto existente
            s_id.write({
                'name': name_fmt,
                'street': new_address,
                'ref': acc_num
            })
        count += 1

# Guardar cambios
env.cr.commit()
print(f"EXITO: Se procesaron {count} suscripciones correctamente.")
