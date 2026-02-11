import csv
import xmlrpc.client

URL = "http://192.168.3.2:8070"
DB = "Sentinela_V18"
USERNAME = "api_user"
PASSWORD = "admin"

INPUT_FILE = 'plantilla_importacion_alarmas.csv'
OUTPUT_FILE = 'errores_importacion.csv'

def main():
    print("=== Generando Reporte de Errores ===")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        # Fix: Usar lista vacía en lugar de dict vacío para compatibilidad
        uid = common.authenticate(DB, USERNAME, PASSWORD, [])
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    except Exception as e:
        print(f"Error conectando a Odoo: {e}")
        return

    failed_rows = []
    
    try:
        try:
            f = open(INPUT_FILE, mode='r', encoding='utf-8-sig')
            reader = csv.DictReader(f)
            rows = list(reader)
        except:
            f = open(INPUT_FILE, mode='r', encoding='latin-1')
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"Verificando {len(rows)} registros...")

        for row in rows:
            p_name = row['partner_id'].strip()
            
            # Verificar si existe el Partner
            exists = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search_count', [[['name', '=', p_name]]])
            
            if not exists:
                print(f"❌ Faltante: {p_name}")
                failed_rows.append(row)
            # else:
            #     print(f"✅ Existe: {p_name}")

    except Exception as e:
        print(f"Error leyendo archivo: {e}")
        return

    # Escribir archivo de errores
    if failed_rows:
        keys = failed_rows[0].keys()
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(failed_rows)
        print(f"\n¡Listo! Se encontraron {len(failed_rows)} registros faltantes.")
        print(f"Archivo generado: {OUTPUT_FILE}")
    else:
        print("\n¡Felicidades! No se encontraron registros faltantes. Todo se importó.")

if __name__ == '__main__':
    main()
