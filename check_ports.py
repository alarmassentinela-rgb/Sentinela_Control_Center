import routeros_api
import sys

HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = ''

try:
    connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
    api = connection.get_api()
    
    print("--- ESTADO DE LOS PUERTOS ---")
    interfaces = api.get_resource('/interface').get()
    for iface in interfaces:
        # Solo nos interesan los puertos físicos ether
        if 'ether' in iface['name']:
            print(f"Puerto: {iface['name']}")
            print(f"  - Activado: {'SI' if iface['disabled'] == 'false' else 'NO (DISABLED)'}")
            print(f"  - Enlace (Running): {'SI (Cable conectado)' if iface['running'] == 'true' else 'NO (Cable desconectado)'}")
            print(f"  - Master Port: {iface.get('master-port', 'Ninguno')}")
            print("------------------------------------------------")

    connection.disconnect()

except Exception as e:
    print(f"Error conectando: {e}")
