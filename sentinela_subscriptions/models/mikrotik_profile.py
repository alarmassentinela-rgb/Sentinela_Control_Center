from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SentinelaMikrotikProfile(models.Model):
    _name = 'sentinela.mikrotik.profile'
    _description = 'Mikrotik PPPoE Profile'

    name = fields.Char(string='Profile Name', required=True, help="Name as it will appear in Mikrotik")
    upload_speed = fields.Integer(string='Upload Speed (Mbps)', required=True, default=5)
    download_speed = fields.Integer(string='Download Speed (Mbps)', required=True, default=20)
    
    local_address = fields.Char(string='Local Address', help="IP of the gateway (optional)")
    remote_address = fields.Char(string='Remote Address Pool', help="Name of the IP Pool in Mikrotik")
    
    router_ids = fields.Many2many('sentinela.router', string='Sync with Routers')

    def action_sync_to_routers(self):
        """ Creates or Updates this profile in all selected routers """
        self.ensure_one()
        import routeros_api
        
        errors = []
        success_count = 0
        
        # Rate Limit Format: rx/tx (Upload/Download from client perspective is Tx/Rx, 
        # but Mikrotik Rate Limit is: rx-rate/tx-rate 
        # Rx = Upload (Client -> Router), Tx = Download (Router -> Client)
        # So: 5M/20M
        rate_limit = f"{self.upload_speed}M/{self.download_speed}M"

        for router in self.router_ids:
            try:
                connection = routeros_api.RouterOsApiPool(
                    router.ip_address,
                    username=router.api_user,
                    password=router.api_password or '',
                    port=router.api_port,
                    plaintext_login=True
                )
                api = connection.get_api()
                resource = api.get_resource('/ppp/profile')
                
                # Check if exists
                existing = resource.get(name=self.name)
                
                params = {
                    'name': self.name,
                    'rate-limit': rate_limit,
                    'comment': 'Managed by Odoo'
                }
                
                if self.local_address:
                    params['local-address'] = self.local_address
                if self.remote_address:
                    params['remote-address'] = self.remote_address

                if existing:
                    resource.set(id=existing[0]['id'], **params)
                else:
                    resource.add(**params)
                
                connection.disconnect()
                success_count += 1
                
            except Exception as e:
                errors.append(f"{router.name}: {str(e)}")
        
        if errors:
            raise UserError(f"Sync Errors:\n" + "\n".join(errors))
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Successful',
                'message': f'Profile updated on {success_count} routers.',
                'type': 'success',
            }
        }
