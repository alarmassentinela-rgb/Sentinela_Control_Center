from odoo import models, fields

class SentinelaRouter(models.Model):
    _name = 'sentinela.router'
    _description = 'Mikrotik Router'

    name = fields.Char(string='Router Name', required=True, help="Ej: Torre Norte RB1100")
    ip_address = fields.Char(string='IP Address', required=True)
    api_user = fields.Char(string='API User', default='admin')
    api_password = fields.Char(string='API Password')
    api_port = fields.Integer(string='API Port', default=8728)
    
    # PPPoE Automation
    pppoe_prefix = fields.Char(string='User Prefix', default='cta', help="Prefix for PPPoE users (e.g. cta)")
    next_pppoe_sequence = fields.Integer(string='Next Sequence', default=1000, help="Next number for PPPoE user generation")
    
    sync_active = fields.Boolean(string='Sincronización Activa', default=True, help="Si está desactivado, Odoo no intentará conectar al Mikrotik (útil para importaciones masivas).")
    active = fields.Boolean(default=True)

    def action_test_connection(self):
        """ Tests the API connection to Mikrotik """
        self.ensure_one()
        import routeros_api
        try:
            connection = routeros_api.RouterOsApiPool(
                self.ip_address,
                username=self.api_user,
                password=self.api_password or '',
                port=self.api_port,
                plaintext_login=True
            )
            api = connection.get_api()
            # Try to get system identity as a test
            system_resource = api.get_resource('/system/identity')
            identity = system_resource.get()
            connection.disconnect()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Conexión Exitosa',
                    'message': f'Conectado al Router: {identity[0]["name"]}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error de Conexión',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

