import requests
import logging
import secrets
from odoo import models, api

_logger = logging.getLogger(__name__)


class SenticarService(models.AbstractModel):
    """Integración con SentiCar (instancia Traccar propia) vía su API REST con Basic Auth.
    Registra equipos GPS en la cuenta del cliente y los habilita/deshabilita según el ciclo
    de cobranza (alta/suspensión/reactivación). Solo aplica a suscripciones con
    gps_platform='senticar' (Tracksolid/Smake son plataformas cerradas: la suspensión de esas
    se hace cortando la SIM en floLIVE, no por aquí)."""
    _name = 'sentinela.senticar.service'
    _description = 'Servicio de Integración SentiCar / Traccar'

    @api.model
    def _conn(self):
        cfg = self.env['ir.config_parameter'].sudo()
        url = cfg.get_param('sentinela.traccar_api_url')
        user = cfg.get_param('sentinela.traccar_api_user')
        pw = cfg.get_param('sentinela.traccar_api_password')
        if not (url and user and pw):
            _logger.warning("SENTICAR: faltan parámetros sentinela.traccar_api_url/user/password")
            return None
        return url.rstrip('/'), (user, pw)

    @api.model
    def _req(self, method, path, **kw):
        conn = self._conn()
        if not conn:
            return None
        base, auth = conn
        try:
            return requests.request(method, base + path, auth=auth, timeout=20, **kw)
        except Exception as e:
            _logger.error("SENTICAR %s %s: %s", method, path, e)
            return None

    @api.model
    def ensure_client_user(self, partner):
        """Crea/recupera el usuario Traccar del cliente. Devuelve (user_id, password_nueva_o_None)."""
        partner = partner.sudo()
        if partner.senticar_user_id:
            return partner.senticar_user_id, None
        email = partner.email or f"cliente{partner.id}@senticar.local"
        r = self._req('GET', '/api/users')
        if r is not None and r.status_code == 200:
            for u in r.json():
                if (u.get('email') or '').lower() == email.lower():
                    partner.senticar_user_id = u['id']
                    partner.senticar_user_email = email
                    return u['id'], None
        pw = 'Sc' + secrets.token_hex(5)
        r = self._req('POST', '/api/users',
                      json={'name': partner.name or email, 'email': email, 'password': pw})
        if r is not None and r.status_code in (200, 201):
            uid = r.json()['id']
            partner.write({'senticar_user_id': uid, 'senticar_user_email': email, 'senticar_user_password': pw})
            return uid, pw
        _logger.error("SENTICAR crear usuario falló: %s", r.text[:200] if r is not None else 'sin conexión')
        return None, None

    @api.model
    def ensure_device(self, name, imei, user_id=None):
        """Crea/recupera el device por uniqueId=IMEI y (opcional) lo vincula al usuario.
        Devuelve device_id o None."""
        if not imei:
            return None
        # Traccar no combina bien all=true con uniqueId → traer todos y filtrar en Python.
        r = self._req('GET', '/api/devices', params={'all': 'true'})
        dev = None
        if r is not None and r.status_code == 200:
            dev = next((d for d in r.json() if str(d.get('uniqueId')) == str(imei)), None)
        if not dev:
            r = self._req('POST', '/api/devices', json={'name': name or imei, 'uniqueId': imei})
            if r is not None and r.status_code in (200, 201):
                dev = r.json()
        if not dev:
            _logger.error("SENTICAR crear device falló: %s", r.text[:200] if r is not None else 'sin conexión')
            return None
        did = dev['id']
        if user_id:
            self._req('POST', '/api/permissions', json={'userId': user_id, 'deviceId': did})
        # Vincular también a la cuenta de monitoreo/admin (Enrique/central) para que vean TODA
        # la flota, no solo la cuenta del cliente. Configurable: sentinela.senticar_admin_user_id.
        admin_uid = self.env['ir.config_parameter'].sudo().get_param('sentinela.senticar_admin_user_id')
        if admin_uid:
            try:
                au = int(admin_uid)
                if au != (user_id or 0):
                    self._req('POST', '/api/permissions', json={'userId': au, 'deviceId': did})
            except (ValueError, TypeError):
                pass
        return did

    @api.model
    def set_device_disabled(self, device_id, disabled):
        """Habilita/deshabilita un device (Traccar PUT requiere el objeto completo)."""
        if not device_id:
            return False
        r = self._req('GET', '/api/devices', params={'all': 'true'})
        if r is None or r.status_code != 200:
            return False
        dev = next((d for d in r.json() if d.get('id') == device_id), None)
        if not dev:
            return False
        dev['disabled'] = bool(disabled)
        r2 = self._req('PUT', f'/api/devices/{device_id}', json=dev)
        return r2 is not None and r2.status_code == 200
