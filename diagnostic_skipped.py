import json

with open('/tmp/cuentas_data.json', 'r') as f:
    data = json.load(f)

print("--- REPORTE DE CUENTAS NO PROCESADAS ---")
skipped = []

for item in data:
    acc_num = str(item.get('Numero de Cuenta'))
    name = item.get('Nombre')
    
    if not acc_num or acc_num == 'None':
        continue
    
    device = env['sentinela.monitoring.device'].search([('account_number', '=', acc_num)], limit=1)
    
    if not device:
        skipped.append(f"Cta: {acc_num} | Motivo: Dispositivo no encontrado en Odoo | Nombre: {name}")
    elif not device.subscription_id:
        skipped.append(f"Cta: {acc_num} | Motivo: Dispositivo existe pero NO tiene suscripcion vinculada | Nombre: {name}")

for s in skipped:
    print(s)

print(f"\nTotal no procesadas: {len(skipped)}")
