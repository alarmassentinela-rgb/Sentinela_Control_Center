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

    @api.model
    def get_sim_diagnostics(self, iccid):
        """Devuelve un dict normalizado para la pestaña Diagnóstico GPS, de SOLO LECTURA:
        {ok, status, online, lat, lon, network, last_session}. Toma el detalle de la SIM
        (subsStatus, isInDataSession, lastKnownLocation, lastConnectedNetwork, lastDataSession)."""
        raw = self.get_sim_details(iccid)
        if not raw:
            return {'ok': False}
        c = raw.get('content')
        if isinstance(c, list) and c:
            c = c[0]
        if not isinstance(c, dict):
            return {'ok': False}
        loc = c.get('lastKnownLocation') or {}
        net = c.get('lastConnectedNetwork') or {}
        network = f"MCC {net.get('mcc')} / MNC {net.get('mnc')}" if net else None
        return {
            'ok': True,
            'status': c.get('subsStatus') or c.get('status'),
            'online': bool(c.get('isInDataSession')),
            'lat': loc.get('latitude'),
            'lon': loc.get('longitude'),
            'network': network,
            'last_session': c.get('lastDataSession'),
        }

    @api.model
    def get_sms_history(self, iccid):
        """Lee el historial de SMS de la SIM (GET, disponible). Devuelve lista o []."""
        if not iccid:
            return []
        token = self._get_auth_token()
        if not token:
            return []
        url = f"https://floportal.flolive.net/api/v2/subscriber/iccid/{iccid}/sms/history"
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
            if r.status_code == 200:
                return r.json().get('content') or []
        except Exception as e:
            _logger.error(f"FLOLIVE SMS HISTORY EXCEPTION: {str(e)}")
        return []

    @api.model
    def send_sms_command(self, iccid, message):
        """Envía un SMS (comando) a la SIM vía Connecta/floLIVE. ANDAMIAJE LISTO pero el envío
        depende de que Connecta habilite el servicio SMS y nos dé el endpoint real (hoy la API
        del portal NO expone envío MT para nuestra cuenta; el plan es solo datos).

        Configurable por parámetros del sistema (sin tocar código) para activarlo cuando
        Connecta confirme:
          - sentinela.flolive_sms_enabled  (bool, default False)
          - sentinela.flolive_sms_endpoint (plantilla con {iccid})
          - sentinela.flolive_sms_method   ('POST' por defecto)
          - sentinela.flolive_sms_msg_key  (clave del cuerpo, 'message' por defecto)

        Devuelve {ok, detail}. Mientras esté deshabilitado, ok=False con detalle explicativo."""
        cfg = self.env['ir.config_parameter'].sudo()
        if cfg.get_param('sentinela.flolive_sms_enabled', 'False') not in ('True', '1', 'true'):
            return {'ok': False, 'detail': 'SMS no habilitado. Falta que Connecta active el servicio SMS '
                                           'en las SIMs y configurar el endpoint (parámetros sentinela.flolive_sms_*).'}
        if not iccid or not message:
            return {'ok': False, 'detail': 'Falta ICCID o mensaje.'}
        token = self._get_auth_token()
        if not token:
            return {'ok': False, 'detail': 'No se pudo autenticar con floLIVE.'}
        tmpl = cfg.get_param('sentinela.flolive_sms_endpoint', '/api/v2/subscriber/iccid/{iccid}/sms')
        method = (cfg.get_param('sentinela.flolive_sms_method', 'POST') or 'POST').upper()
        msg_key = cfg.get_param('sentinela.flolive_sms_msg_key', 'message') or 'message'
        url = "https://floportal.flolive.net" + tmpl.format(iccid=iccid)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            r = requests.request(method, url, headers=headers, json={msg_key: message}, timeout=20)
            if r.status_code in (200, 201, 202, 204):
                _logger.info(f"FLOLIVE SMS enviado a {iccid}: {message}")
                return {'ok': True, 'detail': f'SMS enviado (HTTP {r.status_code}).'}
            return {'ok': False, 'detail': f'floLIVE respondió HTTP {r.status_code}: {r.text[:200]}'}
        except Exception as e:
            _logger.error(f"FLOLIVE SMS SEND EXCEPTION: {str(e)}")
            return {'ok': False, 'detail': f'Excepción: {e}'}
