import routeros_api
import sys

# Configuración (según logs anteriores)
HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = '' # Intentaremos sin password primero, como es común en defaults

try:
    connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
    api = connection.get_api()
except Exception as e:
    print(f"Error de conexión: {e}")
    sys.exit(1)

print("--- 1. INTERFACES (Puertos) ---")
interfaces = api.get_resource('/interface').get()
for iface in interfaces:
    print(f"Name: {iface.get('name')}, Type: {iface.get('type')}, Running: {iface.get('running')}")

print("\n--- 2. PPPoE SERVERS (Servidores Activos) ---")
servers = api.get_resource('/interface/pppoe-server/server').get()
if not servers:
    print("NO HAY SERVIDORES PPPoE CONFIGURADOS.")
else:
    for srv in servers:
        print(f"Service Name: {srv.get('service-name')}, Interface: {srv.get('interface')}, Disabled: {srv.get('disabled')}")

print("\n--- 3. IP POOLS (Rangos de IP) ---")
pools = api.get_resource('/ip/pool').get()
for pool in pools:
    print(f"Name: {pool.get('name')}, Ranges: {pool.get('ranges')}")

print("\n--- 4. PPP PROFILES (Perfiles de Velocidad/Config) ---")
profiles = api.get_resource('/ppp/profile').get()
for prof in profiles:
    print(f"Name: {prof.get('name')}, Local Address: {prof.get('local-address')}, Remote Address: {prof.get('remote-address')}")

connection.disconnect()
