from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MikrotikTrafficWizard(models.TransientModel):
    _name = 'sentinela.mikrotik.traffic'
    _description = 'Live Traffic Monitor'

    user = fields.Char(string='Usuario')
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', required=True)
    current_ip = fields.Char(string='IP Asignada', readonly=True)
    tx_speed = fields.Char(string='Subida (Tx)', readonly=True)
    rx_speed = fields.Char(string='Bajada (Rx)', readonly=True)
    status = fields.Char(string='Estado', readonly=True)
    graph_data = fields.Text(string='Gráfica en Vivo', compute='_compute_graph_data') # Dummy field for widget

    def _compute_graph_data(self):
        for rec in self:
            rec.graph_data = "Graph Placeholder"

    def action_refresh(self):
        return self._get_traffic_data()

    @api.model
    def fetch_traffic_stats(self, wizard_id):
        """ JSON API for the JS Widget """
        wiz = self.browse(wizard_id)
        if not wiz.exists():
             return {'rx': 0, 'tx': 0, 'ip': 'N/A', 'status': 'Wizard cerrado'}

        wiz.ensure_one()
        sub = wiz.subscription_id
        
        if not sub or not sub.router_id or not sub.pppoe_user:
            return {'rx': 0, 'tx': 0, 'ip': 'N/A', 'status': 'Error Config'}

        import routeros_api
        connection = None
        result = {'rx': 0, 'tx': 0, 'ip': 'N/A', 'status': 'Desconectado'}

        try:
            connection = routeros_api.RouterOsApiPool(
                sub.router_id.ip_address,
                username=sub.router_id.api_user,
                password=sub.router_id.api_password or '',
                port=sub.router_id.api_port,
                plaintext_login=True
            )
            api = connection.get_api()
            
            active_resource = api.get_resource('/ppp/active')
            active_conns = active_resource.get(name=sub.pppoe_user)
            
            if active_conns:
                result['ip'] = active_conns[0].get('address', 'N/A')
                interface_name = active_conns[0].get('interface')
                if not interface_name:
                    interface_name = f"<pppoe-{sub.pppoe_user}>"
                
                resource = api.get_resource('/interface')
                stats = resource.call('monitor-traffic', {'interface': interface_name, 'once': 'true'})
                
                if stats:
                    rx_bps = int(stats[0].get('rx-bits-per-second', 0))
                    tx_bps = int(stats[0].get('tx-bits-per-second', 0))
                    result['rx'] = round(rx_bps / 1000000.0, 2)
                    result['tx'] = round(tx_bps / 1000000.0, 2)
                    result['status'] = "Conectado"
            
            connection.disconnect()

        except Exception as e:
            # Capture full traceback for debugging if needed, but return clear message
            error_msg = str(e)
            if "login failure" in error_msg.lower():
                result['status'] = "Error: Login falló (Usuario/Pass API)"
            elif "timed out" in error_msg.lower():
                result['status'] = "Error: Tiempo de espera agotado"
            elif "refused" in error_msg.lower():
                result['status'] = "Error: Conexión rechazada (Puerto API)"
            else:
                result['status'] = f"Error: {error_msg}"
            
            if connection:
                try: connection.disconnect()
                except: pass
        
        return result

    def _get_traffic_data(self):
        self.ensure_one()
        sub = self.subscription_id
        
        if not sub or not sub.router_id or not sub.pppoe_user:
            self.status = "Error: Configuración incompleta (Falta router o usuario)"
            return self._reload_view()

        import routeros_api
        connection = None
        try:
            connection = routeros_api.RouterOsApiPool(
                sub.router_id.ip_address,
                username=sub.router_id.api_user,
                password=sub.router_id.api_password or '',
                port=sub.router_id.api_port,
                plaintext_login=True
            )
            api = connection.get_api()
            
            # Step 1: Check active connections
            active_resource = api.get_resource('/ppp/active')
            active_conns = active_resource.get(name=sub.pppoe_user)
            
            if not active_conns:
                self.status = "Usuario Desconectado (No aparece en /ppp/active)"
                self.current_ip = "N/A"
                self.tx_speed = "0 Mbps"
                self.rx_speed = "0 Mbps"
                connection.disconnect()
                return self._reload_view()
            
            # Step 2: Determine Interface Name & IP
            # active_conns[0] is a dictionary like {'name': 'user', 'service': 'pppoe', 'caller-id': '...', 'address': '192.168.10.5', ...}
            self.current_ip = active_conns[0].get('address', 'Desconocida')
            
            interface_name = active_conns[0].get('interface')
            if not interface_name:
                interface_name = f"<pppoe-{sub.pppoe_user}>"
            
            # Step 3: Monitor Traffic
            resource = api.get_resource('/interface')
            
            try:
                stats = resource.call('monitor-traffic', {'interface': interface_name, 'once': 'true'})
            except Exception as e:
                self.status = f"Error monitoreando interface '{interface_name}': {e}"
                stats = []

            if stats:
                try:
                    rx = int(stats[0].get('rx-bits-per-second', 0))
                    tx = int(stats[0].get('tx-bits-per-second', 0))
                    
                    self.rx_speed = f"{rx / 1000000:.2f} Mbps"
                    self.tx_speed = f"{tx / 1000000:.2f} Mbps"
                    self.status = f"Conectado ({interface_name})"
                except Exception as e:
                     self.status = f"Error procesando datos: {e}"
            else:
                if not self.status.startswith("Error"):
                    self.status = f"Conectado ({interface_name}) - Sin datos"
            
            connection.disconnect()

        except Exception as e:
            self.status = f"Error de Conexión: {str(e)}"
            if connection:
                try:
                    connection.disconnect()
                except:
                    pass
            
        return self._reload_view()

    def _reload_view(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sentinela.mikrotik.traffic',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context
        }
