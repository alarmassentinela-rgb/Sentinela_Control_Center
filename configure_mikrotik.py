import routeros_api
import sys

HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = ''

def run_config():
    try:
        connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
    except Exception as e:
        print(f"FAILED TO CONNECT: {e}")
        return

    print("Connected to Mikrotik. Starting reconfiguration...")

    # 1. IP Configuration (Ensure 192.168.3.3 is on ether5)
    print("Configuring IP on ether5...")
    ip_res = api.get_resource('/ip/address')
    # Find if IP exists anywhere
    existing_ip = ip_res.get(address='192.168.3.3/24')
    if existing_ip:
        # Move it to ether5 if not already there
        if existing_ip[0].get('interface') != 'ether5':
             ip_res.set(id=existing_ip[0]['id'], interface='ether5')
             print("Moved 192.168.3.3 to ether5")
    else:
        try:
            ip_res.add(address='192.168.3.3/24', interface='ether5')
            print("Added 192.168.3.3 to ether5")
        except Exception as e:
            print(f"IP Add Warning: {e}")

    # 2. IP Pool
    print("Configuring IP Pool...")
    pool_res = api.get_resource('/ip/pool')
    if not pool_res.get(name='pppoe-pool'):
        pool_res.add(name='pppoe-pool', ranges='192.168.20.10-192.168.20.200')
        print("Created IP Pool: pppoe-pool")

    # 3. PPP Profile
    print("Configuring PPP Profile...")
    profile_res = api.get_resource('/ppp/profile')
    if not profile_res.get(name='sentinela-profile'):
        profile_res.add(name='sentinela-profile', 
                        local_address='192.168.3.3', 
                        remote_address='pppoe-pool', 
                        dns_server='8.8.8.8,1.1.1.1')
        print("Created Profile: sentinela-profile")

    # 4. PPPoE Server (The critical fix for Error 651)
    print("Configuring PPPoE Server on ether5...")
    server_res = api.get_resource('/interface/pppoe-server/server')
    # Remove existing ones to clean up conflicts
    for srv in server_res.get():
        server_res.remove(id=srv['id'])
    
    server_res.add(service_name='service-sentinela',
                   interface='ether5',
                   disabled='no',
                   default_profile='sentinela-profile',
                   authentication='pap,chap,mschap1,mschap2',
                   one_session_per_host='yes')
    print("Created PPPoE Server on ether5")

    # 5. NAT (Internet Access)
    print("Configuring NAT...")
    nat_res = api.get_resource('/ip/firewall/nat')
    # Check if masquerade exists
    nats = nat_res.get(action='masquerade', chain='srcnat')
    if not nats:
        nat_res.add(chain='srcnat', action='masquerade', out_interface='ether1')
        print("Added Masquerade NAT on ether1")

    # 6. Ensure Test User Exists
    print("Verifying test_odoo user...")
    secret_res = api.get_resource('/ppp/secret')
    user = secret_res.get(name='test_odoo')
    if user:
        secret_res.set(id=user[0]['id'], password='.test', profile='sentinela-profile', service='pppoe', disabled='no')
        print("Updated test_odoo user")
    else:
        secret_res.add(name='test_odoo', password='.test', profile='sentinela-profile', service='pppoe')
        print("Created test_odoo user")

    connection.disconnect()
    print("CONFIGURATION COMPLETE.")

if __name__ == '__main__':
    run_config()
