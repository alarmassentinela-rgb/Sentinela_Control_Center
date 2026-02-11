import csv
import os

# Rutas
ARGUS_FILE = '/mnt/c/Users/dell/Downloads/argus/clientes.csv'
ODOO_FILE = 'odoo_partners.txt'
REPORT_FILE = '/mnt/c/Users/dell/DellCli/sentinela_subscriptions/reporte_coincidencias_clientes.csv'

def normalize(name):
    """ Quita espacios extra y convierte a minúsculas para comparar """
    if not name: return ""
    return " ".join(name.strip().lower().split())

def main():
    print("Cargando clientes de Odoo...")
    odoo_partners = {} # { normalized_name: real_name }
    
    try:
        with open(ODOO_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                raw_name = line.strip()
                if not raw_name or '---' in raw_name or 'name' in raw_name: continue
                odoo_partners[normalize(raw_name)] = raw_name
    except Exception as e:
        print(f"Error leyendo Odoo partners: {e}")
        return

    print(f"Clientes en Odoo: {len(odoo_partners)}")

    print("Analizando clientes de Argus...")
    report_rows = []
    
    try:
        with open(ARGUS_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                argus_name = row.get('Nombre Completo') or row.get('Cliente', 'Sin Nombre')
                norm_argus = normalize(argus_name)
                
                odoo_match = odoo_partners.get(norm_argus, "")
                
                status = "Coincidencia" if odoo_match else "NO ENCONTRADO"
                
                report_rows.append({
                    'Nombre Argus': argus_name,
                    'Nombre Odoo': odoo_match,
                    'Estado': status
                })
    except Exception as e:
        print(f"Error leyendo Argus: {e}")
        return

    # Escribir reporte
    with open(REPORT_FILE, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Nombre Argus', 'Nombre Odoo', 'Estado'])
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"Reporte generado en: {REPORT_FILE}")

if __name__ == '__main__':
    main()
