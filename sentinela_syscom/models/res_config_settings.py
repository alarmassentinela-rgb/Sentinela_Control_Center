from odoo import models, fields, api
import requests
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    syscom_client_id = fields.Char(string='Client ID', config_parameter='sentinela_syscom.client_id')
    syscom_client_secret = fields.Char(string='Client Secret', config_parameter='sentinela_syscom.client_secret')
    syscom_api_url = fields.Char(string='API URL', default='https://developers.syscom.mx/api/v1', config_parameter='sentinela_syscom.api_url')

    def action_test_syscom_connection(self):
        """ Tests the connection to Syscom API using the provided credentials """
        self.ensure_one()
        url = "https://developers.syscom.mx/oauth/token"
        data = {
            'client_id': self.syscom_client_id,
            'client_secret': self.syscom_client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                token = response.json().get('access_token')
                # Try a simple GET to verify full access
                api_url = self.syscom_api_url or 'https://developers.syscom.mx/api/v1'
                headers = {'Authorization': f'Bearer {token}'}
                # Check categories as a lightweight test
                test_res = requests.get(f'{api_url}/categorias', headers=headers)
                
                if test_res.status_code == 200:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Connection Successful',
                            'message': 'Successfully connected to Syscom API!',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
            
            raise UserError(f"Connection Failed: {response.text}")
            
        except Exception as e:
            raise UserError(f"Error connecting to Syscom: {str(e)}")
