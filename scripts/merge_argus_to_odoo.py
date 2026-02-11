import csv
import os

# Configuración de Rutas
BASE_DIR = '/mnt/c/Users/dell/Downloads/argus'
OUTPUT_FILE = '/mnt/c/Users/dell/DellCli/sentinela_subscriptions/importacion_final_odoo.csv'

def read_csv(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, mode='r', encoding='utf-8-sig') as f: # utf-8-sig to handle BOM if any
        reader = csv.DictReader(f)
        return list(reader)

def main():
    print("Leyendo archivos de Argus...")
    try:
        clientes = {c['Nombre Completo']: c for c in read_csv('clientes.csv')}
        cpes_list = read_csv('cpes.csv')
        contratos = read_csv('contratos.csv')
    except Exception as e:
        print(f"Error leyendo archivos: {e}")
        return

    # Indexar CPEs por Contrato ID para búsqueda rápida
    cpes_by_contrato = {}
    for cpe in cpes_list:
        contrato_id = cpe.get('Contrato')
        if contrato_id:
            cpes_by_contrato[contrato_id] = cpe

    print(f"Procesando {len(contratos)} contratos...")

    output_rows = []
    
    for con in contratos:
        contrato_id = con.get('Contrato')
        cliente_nombre = con.get('Cliente')
        
        # Datos del CPE asociado
        cpe = cpes_by_contrato.get(contrato_id, {})
        
        # Datos del Cliente
        cliente_data = clientes.get(cliente_nombre, {})
        
        # Mapeo de Estado
        is_cancelled = con.get('Cancelado') == '1'
        state = 'cancelled' if is_cancelled else 'active'
        technical_state = 'cut' if is_cancelled else 'active'
        
        # Mapeo de Fechas
        start_date = con.get('Inicio de periodo') or con.get('Fecha instalacion')
        next_billing_date = con.get('Fin de periodo')
        
        # Mapeo de Dirección (Prioridad: Contrato > Cliente)
        street = con.get('Calle', '')
        # Concatenar numero si existe
        if con.get('Numero exterior'):
            street += f" #{con.get('Numero exterior')}"
        
        # Mapeo de Producto
        product_name = con.get('Servicio', 'Servicio Genérico')
        
        row = {
            'partner_id': cliente_nombre,
            'email': cliente_data.get('Correo', ''),
            'phone': cliente_data.get('Telefono', ''), # Si existe en clientes
            'product_id': product_name,
            'price_unit': con.get('precio_servicio', '0.00'),
            'start_date': start_date,
            'next_billing_date': next_billing_date,
            'service_type': 'internet', # Asumimos internet para Argus
            'pppoe_user': cpe.get('Usuario PPPoE', ''),
            'pppoe_password': cpe.get('Clave PPPoE', ''),
            'ip_address': cpe.get('IP LAN', ''),
            'mac_address': cpe.get('MAC LAN', ''),
            'latitude': con.get('Latitud', ''),
            'longitude': con.get('Longitud', ''),
            'state': state,
            'technical_state': technical_state,
            'equipment_ownership': 'company', # Default comompany, ajustar si hay campo
            'description': f"Migrado de Argus. Contrato #{contrato_id}. CPE: {cpe.get('Modelo','')}"
        }
        
        output_rows.append(row)

    # Escribir CSV final
    headers = [
        'partner_id', 'email', 'phone', 'product_id', 'price_unit', 
        'start_date', 'next_billing_date', 'service_type', 
        'pppoe_user', 'pppoe_password', 'ip_address', 'mac_address',
        'latitude', 'longitude', 'state', 'technical_state', 
        'equipment_ownership', 'description'
    ]
    
    with open(OUTPUT_FILE, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"¡Éxito! Archivo generado en: {OUTPUT_FILE}")
    print(f"Total registros: {len(output_rows)}")

if __name__ == '__main__':
    main()
