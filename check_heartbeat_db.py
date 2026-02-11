import xmlrpc.client

url = "http://192.168.3.2:8070"
db = "Sentinela_V18"
username = "api_user"
password = "admin"

def check():
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, [])
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    recs = models.execute_kw(db, uid, password, 'sentinela.receiver.status', 'search_read', [[]], {'limit': 1})
    if recs:
        print(f"Ultimo Latido (DB): {recs[0]['last_heartbeat']}")
        print(f"Estado (DB): {recs[0]['status']}")
    else:
        print("No hay registro de estado.")

if __name__ == '__main__':
    check()
