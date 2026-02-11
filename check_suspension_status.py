import routeros_api
import sys

HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = ''

def check_status():
    try:
        connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
        
        print("--- ESTADO ACTUAL ---")
        
        # 1. Check User Secret
        secrets = api.get_resource('/ppp/secret').get(name='test_odoo')
        if secrets:
            s = secrets[0]
            print(f"Usuario: {s['name']}")
            print(f"  - Profile: {s.get('profile')}")
            print(f"  - Disabled: {s.get('disabled')}")
        else:
            print("Usuario 'test_odoo' NO ENCONTRADO.")

        # 2. Check Profile
        profs = api.get_resource('/ppp/profile').get(name='profile-corte')
        if profs:
            p = profs[0]
            print(f"Perfil 'profile-corte': EXISTS")
            print(f"  - Address List: {p.get('address-list')}")
        else:
            print("Perfil 'profile-corte' NO EXISTE.")

        # 3. Check Active Connections
        active = api.get_resource('/ppp/active').get(name='test_odoo')
        if active:
            print("Sesión Activa: SI")
        else:
            print("Sesión Activa: NO")

        connection.disconnect()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_status()
