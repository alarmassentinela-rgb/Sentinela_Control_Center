import xmlrpc.client

url = "http://192.168.3.2:8070"
db = "Sentinela_V18"
username = "api_user"
password = "admin"

def verify_field():
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, [])
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        fields = models.execute_kw(db, uid, password, 'sentinela.subscription', 'fields_get', [], {'attributes': ['string', 'help']})
        
        if 'monitoring_account_number' in fields:
            print("EXITO: El campo 'monitoring_account_number' EXISTE en la base de datos.")
            print(f"Detalles: {fields['monitoring_account_number']}")
            return True
        else:
            print("PENDIENTE: El campo 'monitoring_account_number' NO existe aún.")
            return False
            
    except Exception as e:
        print(f"Error conexión: {e}")
        return False

if __name__ == '__main__':
    verify_field()
