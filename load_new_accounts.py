# Script para ejecutar dentro de odoo shell
import csv
from datetime import datetime, timedelta

correcciones = {
    '1167': {'NAME': 'MANUFACTURAS Y ENSAMBLE DE LA FRONTERA', 'ADDR': 'PRIVADA TERRACOTA S/N  LA CANTERA  LOS ARADOS  87560'},
    '1168': {'NAME': 'MANUFACTURAS Y ENSAMBLE DE LA FRONTERA', 'ADDR': 'PRIVADA TERRACOTA S/N  LA CANTERA  LOS ARADOS  87560'},
    '1169': {'NAME': 'MANUFACTURAS Y ENSAMBLE DE LA FRONTERA', 'ADDR': 'PRIVADA TERRACOTA S/N  LA CANTERA  LOS ARADOS  87560'},
    '1297': {'NAME': 'RUBEN RODRIGUEZ ALVARADO', 'ADDR': 'CALLE 11 ESQUINA CON RIO PANUCO'}
}
cuentas_validas = ['785', '1167', '1168', '1169', '1185', '1223', '1271', '1297', '2031', '2035']

st_data = {}
with open('/tmp/securithor_consolidado_maestro.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        st_data[row['CUENTA']] = row

today = datetime.now().date()
next_month = today + timedelta(days=30)

for acc in cuentas_validas:
    if acc not in st_data: continue
    data = st_data[acc]
    name = correcciones.get(acc, {}).get('NAME', data['NOMBRE_CLIENTE'])
    addr = correcciones.get(acc, {}).get('ADDR', data['DIRECCION'])
    
    print(f"Procesando {acc}: {name}")
    
    partner = env['res.partner'].search([('name', '=', name)], limit=1)
    if not partner:
        partner = env['res.partner'].create({
            'name': name,
            'street': addr,
            'customer_rank': 1
        })
    
    # CORREGIDO: recurring_interval es un STRING '1'
    sub = env['sentinela.subscription'].create({
        'name': f'SUB-ST-{acc}',
        'partner_id': partner.id,
        'product_id': 2015,
        'service_type': 'alarm',
        'state': 'active',
        'start_date': today,
        'next_billing_date': next_month,
        'recurring_interval': '1',
        'price_unit': 0.0
    })
    
    device = env['sentinela.monitoring.device'].create({
        'device_id': f'ST-{acc}',
        'account_number': acc,
        'partner_id': partner.id,
        'subscription_id': sub.id,
        'device_type': 'control_panel'
    })
    
    zones_list = data['DETALLE_ZONAS'].split(' | ')
    for z in zones_list:
        if ':' in z:
            try:
                z_parts = z.split(':')
                z_num = int(z_parts[0].replace('Z', '').strip())
                z_name = z_parts[1].strip()
                env['sentinela.monitoring.zone'].create({
                    'device_id': device.id,
                    'zone_number': z_num,
                    'name': z_name,
                    'zone_type': 'perimeter'
                })
            except: continue

    contacts_list = data['CONTACTOS'].split(' | ')
    for seq, c in enumerate(contacts_list):
        if ':' in c:
            try:
                c_parts = c.split(':')
                c_name_rel = c_parts[0].strip()
                c_phone = c_parts[1].strip()
                c_name = c_name_rel.split('(')[0].strip()
                c_rel = c_name_rel.split('(')[1].replace(')', '').strip() if '(' in c_name_rel else ''
                env['sentinela.monitoring.contact'].create({
                    'device_id': device.id,
                    'name': c_name,
                    'phone': c_phone,
                    'relation': c_rel,
                    'sequence': (seq + 1) * 10
                })
            except: continue

env.cr.commit()
print("¡CARGA FINALIZADA CON EXITO!")
