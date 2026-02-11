import routeros_api
import sys

HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = ''

def setup_suspension():
    try:
        connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
        
        print("--- CONFIGURANDO SISTEMA DE CORTE (WALLED GARDEN) ---")
        
        # 1. Crear Perfil de Corte
        print("1. Creando perfil 'profile-corte'...")
        prof_res = api.get_resource('/ppp/profile')
        if not prof_res.get(name='profile-corte'):
            prof_res.add(
                name='profile-corte',
                local_address='192.168.3.3',
                remote_address='pppoe-pool', # Usamos el mismo pool para que sigan teniendo IP
                address_list='morosos',      # <--- LA CLAVE: Los mete a esta lista
                dns_server='8.8.8.8,1.1.1.1',
                rate_limit='64k/64k',        # Velocidad mínima solo para cargar aviso de corte
                comment='Perfil para clientes suspendidos (Odoo)'
            )
            print(" -> Perfil creado.")
        else:
            print(" -> El perfil ya existe.")

        # 2. Reglas de Firewall (Bloqueo)
        print("2. Configurando Firewall para 'morosos'...")
        fw_res = api.get_resource('/ip/firewall/filter')
        
        # Limpiar reglas viejas de morosos para evitar duplicados
        old_rules = fw_res.get(comment='ODOO_CORTE')
        for r in old_rules:
            fw_res.remove(id=r['id'])

        # Regla 1: Permitir DNS (Vital para redireccionamiento futuro)
        fw_res.add(
            chain='forward',
            src_address_list='morosos',
            protocol='udp',
            dst_port='53',
            action='accept',
            comment='ODOO_CORTE: Permitir DNS',
            place_before='0' # Intentar poner al principio
        )
        
        # Regla 2: Permitir Acceso al Servidor Odoo (Para ver facturas/pagar)
        fw_res.add(
            chain='forward',
            src_address_list='morosos',
            dst_address='192.168.3.2', # IP de Odoo
            action='accept',
            comment='ODOO_CORTE: Permitir Odoo',
            place_before='1'
        )

        # Regla 3: BLOQUEAR TODO LO DEMAS
        fw_res.add(
            chain='forward',
            src_address_list='morosos',
            action='drop',
            comment='ODOO_CORTE: Bloquear Internet',
            place_before='2'
        )
        
        print(" -> Reglas de Firewall aplicadas.")
        
        connection.disconnect()
        print("CONFIGURACION EXITOSA.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    setup_suspension()
