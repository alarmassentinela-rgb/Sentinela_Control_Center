import xmlrpc.client

# Configuración Odoo
url = 'http://localhost:8069' # Puerto interno del contenedor
db = 'Sentinela_V18'
username = 'admin' # Asumo admin, si cambiaste la pass dimelo
password = 'admin'

# Lista de Productos
products = [
    "PLAN INTERNET 10MB/3MB",
    "PLAN INTERNET 15MB/5MB",
    "PLAN INTERNET 20MB/7MB",
    "PLAN INTERNET 25MB/10MB",
    "PLAN INTERNET 30MB/15MB",
    "PLAN INTERNET 5MB/1MB",
    "Plan Intercambio 10mb",
    "Plan Intercambio 15mb",
    "Plan Intercambio 30MB/10MB",
    "Plan Renta Simetrico 15",
    "Renta 10mb/3mb",
    "Renta 15mb/5mb",
    "Renta 20mb/7mb",
    "Renta 25mb/10mb",
    "Renta 30mb/15mb",
    "Renta 5mb/1mb"
]

def main():
    print("Conectando a Odoo...")
    # Autenticación
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Error de autenticación. Verifica usuario/pass.")
        return

    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    print(f"Creando {len(products)} productos...")
    
    for prod_name in products:
        # Verificar si existe
        existing = models.execute_kw(db, uid, password, 'product.product', 'search', [[['name', '=', prod_name]]])
        
        if existing:
            print(f"[Existe] {prod_name}")
            # Opcional: Actualizar para asegurar que sea servicio
            models.execute_kw(db, uid, password, 'product.product', 'write', [existing, {
                'type': 'service',
                'is_subscription': True,
                'service_type': 'internet'
            }])
        else:
            # Crear
            prod_id = models.execute_kw(db, uid, password, 'product.product', 'create', [{
                'name': prod_name,
                'type': 'service',
                'is_subscription': True,
                'service_type': 'internet',
                'list_price': 0.0, # Se actualizará con el contrato
                'taxes_id': [], # Sin impuestos por defecto, o definir IVA
            }])
            print(f"[Creado] {prod_name} (ID: {prod_id})")

    print("Proceso terminado.")

if __name__ == '__main__':
    main()
