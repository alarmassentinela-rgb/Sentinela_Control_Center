import requests
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class FloliveService(models.AbstractModel):
    _name = 'sentinela.flolive.service'
    _description = 'Servicio de Integración floLIVE'

    @api.model
    def _get_auth_token(self):
        """Obtiene un Bearer Token de floLIVE usando las credenciales configuradas."""
        config = self.env['ir.config_parameter'].sudo()
        username = config.get_param('sentinela.connecta_client_id')
        password = config.get_param('sentinela.connecta_access_token')

        if not username or not password:
            _logger.error("FLOLIVE: Credenciales no configuradas en ir.config_parameter")
            return None

        url = "https://floportal.flolive.net/api/v2/auth/token"
        payload = {
            "username": username,
            "password": password
        }

        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                # La estructura observada es: {'content': [{'token': '...', ...}]}
                content = data.get('content')
                if content and isinstance(content, list) and len(content) > 0:
                    return content[0].get('token')
            _logger.error(f"FLOLIVE AUTH FAIL: {response.status_code} - {response.text}")
        except Exception as e:
            _logger.error(f"FLOLIVE AUTH EXCEPTION: {str(e)}")
        
        return None

    @api.model
    def update_sim_status(self, iccid, new_status):
        """
        Cambia el estado de una SIM en floLIVE.
        new_status: 'ACTIVE' o 'SUSPENDED'
        """
        if not iccid:
            return False

        token = self._get_auth_token()
        if not token:
            return False

        url = f"https://floportal.flolive.net/api/v2/subscriber/iccid/{iccid}/status"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "status": new_status
        }

        try:
            # Según documentación y Swagger, el cambio de status suele ser PUT
            response = requests.put(url, json=payload, headers=headers, timeout=15)
            if response.status_code in [200, 204]:
                _logger.info(f"FLOLIVE: SIM {iccid} cambiada a {new_status} exitosamente.")
                return True
            _logger.error(f"FLOLIVE STATUS FAIL: {response.status_code} - {response.text}")
        except Exception as e:
            _logger.error(f"FLOLIVE STATUS EXCEPTION: {str(e)}")

        return False

    @api.model
    def get_sim_details(self, iccid):
        """Obtiene detalles de la SIM para verificar su estado actual."""
        if not iccid:
            return None

        token = self._get_auth_token()
        if not token:
            return None

        url = f"https://floportal.flolive.net/api/v2/subscriber/iccid/{iccid}"
        headers = {
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            _logger.error(f"FLOLIVE GET DETAILS EXCEPTION: {str(e)}")
        
        return None
