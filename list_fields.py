import xmlrpc.client

url = "http://192.168.3.2:8070"
db = "Sentinela_V18"
username = "api_user"
password = "admin"

def list_all_fields():
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, [])
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    fields = models.execute_kw(db, uid, password, 'sentinela.subscription', 'fields_get', [], {'attributes': ['string']})
    
    print("--- Campos disponibles en sentinela.subscription ---")
    for f in sorted(fields.keys()):
        print(f)

if __name__ == '__main__':
    list_all_fields()
