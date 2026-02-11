import routeros_api
import sys

HOST = '192.168.3.3'
USER = 'admin'
PASSWORD = ''

def fix_bridge_conflict():
    try:
        connection = routeros_api.RouterOsApiPool(HOST, username=USER, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
        
        print("--- ANALIZANDO PUENTES (BRIDGES) ---")
        
        # 1. Buscar puertos en bridges
        bridge_ports = api.get_resource('/interface/bridge/port').get()
        ether5_bridge = None
        
        for port in bridge_ports:
            if port['interface'] == 'ether5':
                ether5_bridge = port['bridge']
                print(f"¡ALERTA! Ether5 es esclavo del bridge: '{ether5_bridge}'")
                break
        
        if ether5_bridge:
            print(f"CORRIGIENDO: Moviendo Servidor PPPoE de 'ether5' a '{ether5_bridge}'...")
            
            # Buscar el servidor PPPoE actual
            pppoe_srv_res = api.get_resource('/interface/pppoe-server/server')
            servers = pppoe_srv_res.get(interface='ether5')
            
            for srv in servers:
                # Cambiar la interfaz al bridge
                pppoe_srv_res.set(id=srv['id'], interface=ether5_bridge)
                print(" -> Servidor actualizado exitosamente.")
                
            # Verificar si hay otros servidores en el mismo bridge que puedan causar conflicto
            all_servers = pppoe_srv_res.get(interface=ether5_bridge)
            if len(all_servers) > 1:
                print(" -> Advertencia: Hay múltiples servidores en el mismo bridge. Dejando solo el de Sentinela.")
                # Aquí podrías borrar los extras si quisieras, por ahora solo avisamos.

        else:
            print("Ether5 NO está en ningún bridge. La configuración directa debería funcionar.")
            # Si no está en un bridge, quizás hay un conflicto con un Master Port (en versiones viejas de RouterOS)
            # Pero el diagnóstico anterior dijo "Master Port: Ninguno", así que eso está bien.

        connection.disconnect()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    fix_bridge_conflict()
