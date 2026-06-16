import requests
import logging
import secrets
from datetime import datetime, timedelta, timezone
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
        # Vincular el equipo a TODOS los administradores (Enrique, su hijo, etc.) para que la
        # central vea toda la flota sin ligar manualmente. Si no se puede leer la lista de
        # usuarios, cae al param sentinela.senticar_admin_user_id (acepta lista "1,5").
        admin_ids = []
        ru = self._req('GET', '/api/users')
        if ru is not None and ru.status_code == 200:
            try:
                admin_ids = [u['id'] for u in ru.json() if u.get('administrator')]
            except Exception:
                admin_ids = []
        if not admin_ids:
            p = self.env['ir.config_parameter'].sudo().get_param('sentinela.senticar_admin_user_id') or ''
            admin_ids = [int(x) for x in str(p).split(',') if x.strip().isdigit()]
        for au in admin_ids:
            if au != (user_id or 0):
                self._req('POST', '/api/permissions', json={'userId': au, 'deviceId': did})
        return did

    @api.model
    def update_user_email(self, user_id, new_email):
        """Actualiza el email (= login) de un usuario Traccar. Para sincronizar cuando cambia
        el email del cliente en Odoo (si no, el cliente acabaría logueando con un correo viejo)."""
        if not user_id or not new_email:
            return False
        r = self._req('GET', '/api/users')
        if r is None or r.status_code != 200:
            return False
        u = next((x for x in r.json() if x.get('id') == user_id), None)
        if not u:
            return False
        u['email'] = new_email
        r2 = self._req('PUT', f'/api/users/{user_id}', json=u)
        return r2 is not None and r2.status_code == 200

    @api.model
    def cleanup_expired_temp_users(self):
        """Borra de Traccar los usuarios temporales (de links de rastreo) ya vencidos, para que
        no se acumulen. Devuelve cuántos borró."""
        r = self._req('GET', '/api/users')
        if r is None or r.status_code != 200:
            return 0
        now = datetime.now(timezone.utc)
        n = 0
        for u in r.json():
            if not u.get('temporary'):
                continue
            exp = u.get('expirationTime')
            if not exp:
                continue
            try:
                dt = datetime.strptime(str(exp)[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if dt < now:
                d = self._req('DELETE', f"/api/users/{u['id']}")
                if d is not None and d.status_code in (200, 204):
                    n += 1
        return n

    @api.model
    def list_devices(self):
        """Devuelve la lista cruda de TODOS los devices de Traccar (o None si no se pudo leer).
        Para reconciliación: una sola llamada y comparar en Python."""
        r = self._req('GET', '/api/devices', params={'all': 'true'})
        if r is None or r.status_code != 200:
            return None
        try:
            return r.json()
        except Exception:
            return None

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

    @api.model
    def create_share_link(self, device_id, hours=24, label='Rastreo temporal'):
        """Genera un link PÚBLICO y TEMPORAL para rastrear UNA sola unidad, sin cuenta, que
        EXPIRA en `hours` horas. Crea un usuario temporal (readonly, deviceLimit=1) ligado al
        equipo, genera su token y arma el link con la URL pública de SentiCar.
        Devuelve {ok, link, expira} o {ok:False, detail}."""
        if not device_id:
            return {'ok': False, 'detail': 'El equipo no está registrado en SentiCar (sin ID).'}
        conn = self._conn()
        if not conn:
            return {'ok': False, 'detail': 'Faltan parámetros de API de SentiCar.'}
        base, auth = conn
        try:
            hours = int(hours) or 24
        except (ValueError, TypeError):
            hours = 24
        # Tope de duración para que un link no quede vivo indefinidamente (abuso).
        try:
            max_h = int(self.env['ir.config_parameter'].sudo().get_param('sentinela.senticar_share_max_hours', '168') or 168)
        except (ValueError, TypeError):
            max_h = 168
        hours = max(1, min(hours, max_h))
        exp = (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        pw = 'Sh' + secrets.token_hex(8)
        email = f'share-{secrets.token_hex(6)}@senticar.com'
        try:
            r = requests.post(base + '/api/users', auth=auth, timeout=20, json={
                'name': f'{label} ({hours}h)', 'email': email, 'password': pw,
                'expirationTime': exp, 'deviceLimit': 1, 'temporary': True, 'readonly': True})
            if r.status_code not in (200, 201):
                return {'ok': False, 'detail': f'No se pudo crear el acceso temporal: HTTP {r.status_code} {r.text[:150]}'}
            uid = r.json()['id']
            requests.post(base + '/api/permissions', auth=auth, timeout=20,
                          json={'userId': uid, 'deviceId': device_id})
            # login como el usuario temporal y generar su token
            s = requests.Session()
            s.post(base + '/api/session', data={'email': email, 'password': pw}, timeout=20)
            tr = s.post(base + '/api/session/token', data={'expiration': exp}, timeout=20)
            if tr.status_code != 200 or 'Exception' in tr.text:
                return {'ok': False, 'detail': 'No se pudo generar el token de rastreo.'}
            token = tr.text.strip().strip('"')
        except Exception as e:
            _logger.error("SENTICAR share error: %s", e)
            return {'ok': False, 'detail': f'Excepción: {e}'}
        public = (self.env['ir.config_parameter'].sudo().get_param('sentinela.senticar_public_url')
                  or 'https://radar.senticar.com').rstrip('/')
        return {'ok': True, 'link': f'{public}/?token={token}', 'expira': exp}
