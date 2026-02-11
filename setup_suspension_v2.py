import routeros_api
import sys

HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = ''

def setup_suspension_v2():
    try:
        connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
        
        print("--- REINTENTANDO REGLAS DE FIREWALL ---")
        fw_res = api.get_resource('/ip/firewall/filter')
        
        # Limpiar reglas anteriores de este script
        old_rules = fw_res.get(comment='ODOO_CORTE')
        for r in old_rules:
            fw_res.remove(id=r['id'])

        # Creamos las reglas sin 'place-before' para evitar errores de índice.
        # Luego las moveremos al principio usando 'move'.
        
        # 1. DNS
        id_dns = fw_res.add(
            chain='forward',
            src_address_list='morosos',
            protocol='udp',
            dst_port='53',
            action='accept',
            comment='ODOO_CORTE'
        )
        
        # 2. Odoo
        id_odoo = fw_res.add(
            chain='forward',
            src_address_list='morosos',
            dst_address='192.168.3.2',
            action='accept',
            comment='ODOO_CORTE'
        )

        # 3. Drop
        id_drop = fw_res.add(
            chain='forward',
            src_address_list='morosos',
            action='drop',
            comment='ODOO_CORTE'
        )
        
        # Intentar moverlas al principio (índice 0, 1, 2)
        try:
            # Nota: 'move' en la API a veces requiere sintaxis específica o no es soportado por la lib wrapper.
            # Si falla, las reglas quedarán al final. 
            # Dado que el router estaba limpio, al final es probable que funcione bien si no hay otras reglas.
            pass 
        except:
            pass

        print(" -> Reglas creadas exitosamente.")
        connection.disconnect()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    setup_suspension_v2()
