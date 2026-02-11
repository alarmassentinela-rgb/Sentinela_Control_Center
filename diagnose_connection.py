import routeros_api
import sys

HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = ''

def diagnose():
    try:
        connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
        
        print("--- 1. ULTIMOS LOGS (Buscando intentos PPPoE) ---")
        # Get last 15 logs related to ppp, pppoe, or info
        logs = api.get_resource('/log').get()
        # Sort by id (implicitly chronologically mostly, but let's just take last 20)
        # Mikrotik API returns list.
        last_logs = logs[-20:] 
        for log in last_logs:
            if 'ppp' in log.get('topics', '') or 'info' in log.get('topics', ''):
                 print(f"Time: {log.get('time')} - {log.get('message')}")

        print("\n--- 2. ESTADO DE WAN (Ether1) ---")
        # Check if ether1 has IP
        addresses = api.get_resource('/ip/address').get(interface='ether1')
        if addresses:
            for addr in addresses:
                print(f"Ether1 IP: {addr.get('address')}")
        else:
            print("¡ALERTA! Ether1 NO tiene dirección IP. El DHCP Client podría estar fallando.")
            
        # Check DHCP Client status on ether1
        dhcp_clients = api.get_resource('/ip/dhcp-client').get()
        found_client = False
        for client in dhcp_clients:
            if client['interface'] == 'ether1':
                found_client = True
                print(f"DHCP Client en ether1: Status={client.get('status')}, Address={client.get('address')}")
        
        if not found_client:
            print("¡ALERTA! No hay DHCP Client configurado en ether1. El router no está pidiendo IP al módem.")

        print("\n--- 3. RUTAS (Internet Gateway) ---")
        routes = api.get_resource('/ip/route').get(dst_address='0.0.0.0/0')
        if routes:
            for r in routes:
                 print(f"Default Route: Gateway={r.get('gateway')}, Active={r.get('active')}")
        else:
            print("¡ALERTA! No hay ruta por defecto (0.0.0.0/0). No hay salida a internet.")

        connection.disconnect()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    diagnose()
