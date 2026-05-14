from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

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
        return self._reload_view()

    @api.model
    def fetch_traffic_stats(self, wizard_id):
        try:
            wiz = self.browse(wizard_id)
            if not wiz.exists():
                 return {'rx': 0, 'tx': 0, 'ip': 'N/A', 'status': 'Cerrado'}

            sub = wiz.subscription_id
            if not sub or not sub.router_id:
                return {'rx': 0, 'tx': 0, 'ip': 'N/A', 'status': 'Falta Config'}

            import routeros_api
            connection = None
            result = {'rx': 0, 'tx': 0, 'ip': sub.ip_address or 'N/A', 'status': 'Conectando...'}

            try:
                connection = routeros_api.RouterOsApiPool(
                    sub.router_id.ip_address,
                    username=sub.router_id.api_user,
                    password=sub.router_id.api_password or '',
                    port=sub.router_id.api_port,
                    plaintext_login=True
                )
                api = connection.get_api()
                
                # MODO PPPOE
                if sub.internet_mgmt_mode == 'pppoe':
                    active_res = api.get_resource('/ppp/active')
                    conns = active_res.get(name=sub.pppoe_user)
                    if conns:
                        result['ip'] = conns[0].get('address', 'N/A')
                        iface = conns[0].get('interface') or f"<pppoe-{sub.pppoe_user}>"
                        resource = api.get_resource('/interface')
                        stats = resource.call('monitor-traffic', {'interface': iface, 'once': 'true'})
                        if stats:
                            result['rx'] = round(int(stats[0].get('rx-bits-per-second', 0)) / 1000000.0, 2)
                            result['tx'] = round(int(stats[0].get('tx-bits-per-second', 0)) / 1000000.0, 2)
                            result['status'] = "Online (PPP)"
                    else:
                        result['status'] = "Offline"
                
                # MODO ESTÁTICO (Simple Queues)
                else:
                    resource = api.get_resource('/queue/simple')
                    # Intentar buscar por nombre primero
                    q_name = f"Q-{sub.name}"
                    queue = resource.get(name=q_name)
                    
                    # Si no la halla por nombre, buscar por IP (Target)
                    if not queue and sub.ip_address:
                        all_queues = resource.get()
                        for q in all_queues:
                            if sub.ip_address in q.get('target', ''):
                                queue = [q]
                                break
                    
                    if queue:
                        q_real_name = queue[0].get('name')
                        try:
                            stats = resource.call('monitor-traffic', {'interface': q_real_name, 'once': 'true'})
                            if stats:
                                result['rx'] = round(int(stats[0].get('rx-bits-per-second', 0)) / 1000000.0, 2)
                                result['tx'] = round(int(stats[0].get('tx-bits-per-second', 0)) / 1000000.0, 2)
                                result['status'] = f"Online ({q_real_name})"
                            else:
                                rate_str = queue[0].get('rate', '0/0')
                                parts = rate_str.split('/')
                                result['tx'] = round(int(parts[0]) / 1000000.0, 2)
                                result['rx'] = round(int(parts[1]) / 1000000.0, 2)
                                result['status'] = "Online (Rate Mode)"
                        except:
                            rate_str = queue[0].get('rate', '0/0')
                            parts = rate_str.split('/')
                            result['tx'] = round(int(parts[0]) / 1000000.0, 2)
                            result['rx'] = round(int(parts[1]) / 1000000.0, 2)
                            result['status'] = "Online (Fallback)"
                    else:
                        result['status'] = f"Sin Cola para {sub.ip_address or 'IP'}"
                
                connection.disconnect()
            except Exception as e:
                result['status'] = f"Error MikroTik: {str(e)}"
                if connection:
                    try: connection.disconnect()
                    except: pass
            
            return result
        except Exception as e:
            return {'rx': 0, 'tx': 0, 'ip': 'ERR', 'status': str(e)}

    def _reload_view(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sentinela.mikrotik.traffic',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context
        }
