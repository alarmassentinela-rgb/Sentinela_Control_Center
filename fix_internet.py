import routeros_api
import sys

HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = ''

def fix_internet():
    try:
        connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
        
        print("--- CONFIGURANDO INTERNET (DHCP CLIENT) ---")
        
        # 1. Check if DHCP Client exists
        dhcp_res = api.get_resource('/ip/dhcp-client')
        clients = dhcp_res.get(interface='ether1')
        
        if clients:
            print("El cliente DHCP ya existe, asegurando que esté habilitado...")
            dhcp_res.set(id=clients[0]['id'], disabled='no')
        else:
            print("Creando nuevo Cliente DHCP en ether1...")
            # add-default-route=yes es CRUCIAL para tener internet
            dhcp_res.add(interface='ether1', disabled='no', add_default_route='yes', use_peer_dns='yes', use_peer_ntp='yes')
            
        print("Esperando asignación de IP...")
        # No podemos esperar indefinidamente aquí, pero al menos la config ya está.
        
        connection.disconnect()
        print("LISTO. El router ahora debería pedir IP al módem.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    fix_internet()
