import xmlrpc.client

url = "http://192.168.3.2:8070"
db = "Sentinela_V18"
username = "api_user"
password = "admin"

def fix_admin():
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, [])
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # Update Admin (ID 2 usually, or current uid if admin)
    # Since api_user might not be ID 2, we update ID 2 explicitly (Administrator)
    try:
        models.execute_kw(db, uid, password, 'res.users', 'write', [[2], {'email': 'admin@localhost.com'}])
        print("Admin email updated.")
        
        # Also update current user just in case
        if uid != 2:
            models.execute_kw(db, uid, password, 'res.users', 'write', [[uid], {'email': 'api@localhost.com'}])
            print("API User email updated.")
            
    except Exception as e:
        print(f"Error updating email: {e}")

if __name__ == '__main__':
    fix_admin()
