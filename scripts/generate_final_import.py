import csv
import os

# Rutas
BASE_DIR = '/mnt/c/Users/dell/Downloads/argus'
REPORT_FILE = '/mnt/c/Users/dell/DellCli/sentinela_subscriptions/reporte_coincidencias_clientes.csv'
OUTPUT_FILE = '/mnt/c/Users/dell/DellCli/sentinela_subscriptions/importacion_final_odoo.csv'

def read_csv(path):
    try:
        f = open(path, mode='r', encoding='utf-8-sig')
        return list(csv.DictReader(f))
    except UnicodeDecodeError:
        f = open(path, mode='r', encoding='latin-1')
        return list(csv.DictReader(f))

def main():
    print("Cargando mapeo de clientes...")
    client_map = {} # { Argus Name : Odoo Name }
    
    try:
        report = read_csv(REPORT_FILE)
        for row in report:
            argus_name = row.get('Nombre Argus')
            odoo_name = row.get('Nombre Odoo')
            if argus_name and odoo_name:
                client_map[argus_name] = odoo_name
    except Exception as e:
        print(f"Advertencia: No se pudo leer el reporte de coincidencias ({e}). Se usaran nombres originales.")

    print("Leyendo datos de Argus...")
    try:
        clientes = {c['Nombre Completo']: c for c in read_csv(os.path.join(BASE_DIR, 'clientes.csv'))}
        cpes_list = read_csv(os.path.join(BASE_DIR, 'cpes.csv'))
        contratos = read_csv(os.path.join(BASE_DIR, 'contratos.csv'))
    except Exception as e:
        print(f"Error leyendo archivos Argus: {e}")
        return

    # Indexar CPEs
    cpes_by_contrato = {}
    for cpe in cpes_list:
        if cpe.get('Contrato'):
            cpes_by_contrato[cpe['Contrato']] = cpe

    print(f"Procesando {len(contratos)} contratos...")
    output_rows = []

    for con in contratos:
        contrato_id = con.get('Contrato')
        cliente_nombre_argus = con.get('Cliente')
        
        # Mapeo de Nombre (Clave del éxito)
        final_partner_name = client_map.get(cliente_nombre_argus, cliente_nombre_argus).upper()
        
        cpe = cpes_by_contrato.get(contrato_id, {})
        cliente_data = clientes.get(cliente_nombre_argus, {})
        
        # Estado
        is_cancelled = con.get('Cancelado') == '1'
        state = 'cancelled' if is_cancelled else 'active'
        technical_state = 'cut' if is_cancelled else 'active'
        
        # Fechas
        start_date = con.get('Inicio de periodo') or con.get('Fecha instalacion')
        next_billing_date = con.get('Fin de periodo')
        
        # Producto
        product_name = con.get('Servicio', 'Servicio Genérico')
        
        row = {
            'partner_id': final_partner_name,
            'product_id': product_name,
            'price_unit': con.get('precio_servicio', '0.00'),
            'start_date': start_date,
            'next_billing_date': next_billing_date,
            'service_type': 'internet',
            'pppoe_user': cpe.get('Usuario PPPoE', ''),
            'pppoe_password': cpe.get('Clave PPPoE', ''),
            'ip_address': cpe.get('IP LAN', ''),
            'latitude': con.get('Latitud', ''),
            'longitude': con.get('Longitud', ''),
            'state': state,
            'technical_state': technical_state,
            'equipment_ownership': 'company',
            'description': f"Migrado de Argus. Contrato #{contrato_id}."
        }
        output_rows.append(row)

    # Escribir
    headers = [
        'partner_id', 'product_id', 'price_unit', 
        'start_date', 'next_billing_date', 'service_type', 
        'pppoe_user', 'pppoe_password', 'ip_address',
        'latitude', 'longitude', 'state', 'technical_state', 
        'equipment_ownership', 'description'
    ]
    
    with open(OUTPUT_FILE, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"¡Listo! Archivo final generado en: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
