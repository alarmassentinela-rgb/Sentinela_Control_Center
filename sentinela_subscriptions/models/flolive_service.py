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
    def _extract_msisdn(self, content):
        """Saca el MSISDN activo de la SIM desde subscriberIdentifiers.imsiMsisdnPairs."""
        si = (content or {}).get('subscriberIdentifiers') or {}
        pairs = si.get('imsiMsisdnPairs') or []
        for p in pairs:
            if p.get('isLastActive'):
                return p.get('msisdn')
        return pairs[0].get('msisdn') if pairs else None

    @api.model
    def send_sms_command(self, iccid, message, encoding='GSM-7'):
        """Envía un SMS (comando) a la SIM vía floLIVE/Connecta usando la mutation GraphQL
        `sendSmsToSim` (el mismo mecanismo que el portal web). Requiere {encoding, message,
        iccid, accountId, msisdn, accountName}; los 3 últimos se obtienen del detalle de la SIM.
        encoding: 'GSM-7' (default, texto normal) o 'UCS2' (acentos/unicode).
        Devuelve {ok, detail, process_id}. Kill-switch: param sentinela.flolive_sms_enabled."""
        if not iccid or not message:
            return {'ok': False, 'detail': 'Falta ICCID o mensaje.'}
        cfg = self.env['ir.config_parameter'].sudo()
        if cfg.get_param('sentinela.flolive_sms_enabled', 'True') in ('False', '0', 'false'):
            return {'ok': False, 'detail': 'Envío de SMS deshabilitado (param sentinela.flolive_sms_enabled).'}
        token = self._get_auth_token()
        if not token:
            return {'ok': False, 'detail': 'No se pudo autenticar con floLIVE.'}
        raw = self.get_sim_details(iccid)
        c = raw.get('content') if raw else None
        if isinstance(c, list) and c:
            c = c[0]
        if not isinstance(c, dict):
            return {'ok': False, 'detail': 'No se pudo obtener el detalle de la SIM en floLIVE.'}
        msisdn = self._extract_msisdn(c)
        account_id = c.get('customerId')
        account_name = c.get('customerName')
        if not (msisdn and account_id and account_name):
            return {'ok': False, 'detail': 'La SIM no tiene MSISDN/cuenta completos en floLIVE.'}
        mutation = ('mutation($sendSmsInfo: SendSmsInfoInput!){ '
                    'processId: sendSmsToSim(sendSmsInfo: $sendSmsInfo) }')
        variables = {'sendSmsInfo': {
            'encoding': encoding or 'GSM-7',
            'message': message,
            'iccid': iccid,
            'accountId': account_id,
            'msisdn': msisdn,
            'accountName': account_name,
        }}
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
        try:
            r = requests.post("https://floportal.flolive.net/graphql", headers=headers,
                              json={'query': mutation, 'variables': variables}, timeout=30)
            j = r.json() if r.content else {}
            pid = (j.get('data') or {}).get('processId')
            if r.status_code == 200 and pid:
                _logger.info(f"FLOLIVE SMS enviado a {iccid} ({encoding}): {message} [processId {pid}]")
                return {'ok': True, 'detail': f'SMS enviado ({encoding}). processId {pid}', 'process_id': pid}
            err = (j.get('errors') or [{}])[0].get('message') if isinstance(j, dict) else None
            return {'ok': False, 'detail': f'floLIVE: {err or ("HTTP %s: %s" % (r.status_code, r.text[:200]))}'}
        except Exception as e:
            _logger.error(f"FLOLIVE SMS SEND EXCEPTION: {str(e)}")
            return {'ok': False, 'detail': f'Excepción: {e}'}
