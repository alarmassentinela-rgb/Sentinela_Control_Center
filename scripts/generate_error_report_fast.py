import csv
import xmlrpc.client

URL = "http://192.168.3.2:8070"
DB = "Sentinela_V18"
USERNAME = "api_user"
PASSWORD = "admin"

INPUT_FILE = 'plantilla_importacion_alarmas.csv'
OUTPUT_FILE = 'errores_importacion.csv'

def main():
    print("=== Generando Reporte (Optimizado) ===")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USERNAME, PASSWORD, [])
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        
        # Traer TODOS los nombres de partners de una vez
        print("Descargando base de datos de clientes...")
        partners = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search_read', [[], ['name']])
        # Fix: Manejar nombres False/None
        partner_names = {str(p['name'] or '').strip().upper() for p in partners} 
        print(f"✅ {len(partner_names)} clientes en Odoo.")
        
    except Exception as e:
        print(f"Error conectando a Odoo: {e}")
        return

    failed_rows = []
    
    try:
        # Leer CSV
        try:
            f = open(INPUT_FILE, mode='r', encoding='utf-8-sig')
            reader = csv.DictReader(f)
            rows = list(reader)
        except:
            f = open(INPUT_FILE, mode='r', encoding='latin-1')
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"Analizando {len(rows)} registros del CSV...")

        for row in rows:
            p_name = row['partner_id'].strip().upper()
            
            if p_name not in partner_names:
                # Intento fuzzy (opcional, por si acaso)
                failed_rows.append(row)

    except Exception as e:
        print(f"Error leyendo archivo: {e}")
        return

    if failed_rows:
        keys = failed_rows[0].keys()
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(failed_rows)
        print(f"\n🚨 Se encontraron {len(failed_rows)} registros faltantes.")
        print(f"📄 Archivo generado: {OUTPUT_FILE}")
        
        # Mover a descargas si es posible (en entorno local del usuario)
        print(f"Copia este archivo a tus descargas con: cp {OUTPUT_FILE} /mnt/c/Users/dell/Downloads/")
    else:
        print("\n✨ ¡Felicidades! Todos los clientes están en Odoo.")

if __name__ == '__main__':
    main()
