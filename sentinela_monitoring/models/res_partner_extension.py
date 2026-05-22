from odoo import models, fields
import base64
import logging
import re

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_patrol = fields.Boolean(string='Es Patrulla', default=False)
    traccar_device_id = fields.Char(string='ID Dispositivo Traccar')
    last_gps_lat = fields.Float(string='Última Latitud', digits=(10, 7))
    last_gps_lng = fields.Float(string='Última Longitud', digits=(10, 7))
    last_gps_update = fields.Datetime(string='Última Actualización GPS')
    manual_geolocation = fields.Boolean(string='Geolocalización Manual', default=False)
    telegram_chat_id = fields.Char(string='Telegram Chat ID', help="ID de chat para notificaciones automáticas")

    # F3 — Canal de notificación del cliente
    notification_channel = fields.Selection([
        ('both', 'Telegram + WhatsApp'),
        ('telegram', 'Solo Telegram'),
        ('whatsapp', 'Solo WhatsApp'),
        ('none', 'Sin notificaciones automáticas'),
    ], string='Canal de notificación', default='both',
       help='Por dónde el sistema envía alertas (camino patrulla, autorizaciones, reporte cierre, etc).')
    whatsapp_number = fields.Char(string='WhatsApp (opcional)',
        help='Si está vacío, se usa mobile/phone. Formato libre — el sistema normaliza a E.164.')

    def _get_telegram_token(self):
        params = self.env['ir.config_parameter'].sudo()
        return params.get_param('sentinela_syscom.telegram_token') or "8373567654:AAGyLpZttCUaHh-LymQwEHRBOqwtVNXYN10"

    def send_telegram_message(self, message):
        """ Envía un mensaje de Telegram a este contacto """
        self.ensure_one()
        if not self.telegram_chat_id:
            return False

        import requests
        try:
            url = f"https://api.telegram.org/bot{self._get_telegram_token()}/sendMessage"
            res = requests.post(url, data={'chat_id': self.telegram_chat_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
            return res.ok
        except:
            return False

    # ---------------- F3 WhatsApp vía EvoApi ----------------

    def _get_evoapi_config(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'url': params.get_param('sentinela_monitoring.evoapi_url') or 'http://192.168.3.2:8080',
            'key': params.get_param('sentinela_monitoring.evoapi_key') or '61EBE23C75A5787BAD62C9D20D7CE5CA',
            'instance': params.get_param('sentinela_monitoring.evoapi_instance') or 'SentinelaWA',
        }

    def _whatsapp_number(self):
        """Normaliza el número del partner a formato E.164 sin '+' para EvoApi.
        Mexicano default: agrega '521' si parece nacional 10 dígitos.
        Returns string o None si no hay número."""
        self.ensure_one()
        raw = self.whatsapp_number or self.mobile or self.phone
        if not raw:
            return None
        digits = re.sub(r'\D', '', raw)
        if not digits:
            return None
        # Mexicano: 10 dígitos → agregar 521 (México móvil con prefijo histórico)
        if len(digits) == 10:
            return f"521{digits}"
        # Ya tiene país (52 + 10): asegurar 521 + 10 para móviles
        if len(digits) == 12 and digits.startswith('52') and not digits.startswith('521'):
            return f"521{digits[2:]}"
        return digits

    def send_whatsapp_message(self, message):
        """F3.1 — Envía mensaje texto al cliente vía EvoApi/WhatsApp.
        Best-effort: devuelve True/False sin lanzar."""
        self.ensure_one()
        number = self._whatsapp_number()
        if not number:
            return False
        cfg = self._get_evoapi_config()
        import requests
        try:
            res = requests.post(
                f"{cfg['url']}/message/sendText/{cfg['instance']}",
                headers={'apikey': cfg['key'], 'Content-Type': 'application/json'},
                json={'number': number, 'text': message},
                timeout=15,
            )
            return res.ok
        except Exception as e:
            _logger.warning("WhatsApp sendText failed for %s: %s", self.name, e)
            return False

    def send_whatsapp_document(self, filename, content_bytes, caption=None):
        """F3.1 — Envía PDF/documento al cliente vía EvoApi. Returns bool."""
        self.ensure_one()
        number = self._whatsapp_number()
        if not number:
            return False
        cfg = self._get_evoapi_config()
        import requests
        media_b64 = base64.b64encode(content_bytes).decode('utf-8')
        payload = {
            'number': number,
            'mediatype': 'document',
            'mimetype': 'application/pdf',
            'media': media_b64,
            'fileName': filename,
        }
        if caption:
            payload['caption'] = caption[:1024]
        try:
            res = requests.post(
                f"{cfg['url']}/message/sendMedia/{cfg['instance']}",
                headers={'apikey': cfg['key'], 'Content-Type': 'application/json'},
                json=payload,
                timeout=30,
            )
            return res.ok
        except Exception as e:
            _logger.warning("WhatsApp sendMedia failed for %s: %s", self.name, e)
            return False

    # ---------------- F3 Wrapper de notificación ----------------

    def notify(self, message, document=None, filename=None, caption=None):
        """F3 — Notifica al partner usando el canal preferido en notification_channel.
        Args:
            message: texto del mensaje (sirve también como caption del documento).
            document: bytes del PDF/imagen (opcional). Si presente, se envía como adjunto.
            filename: nombre del archivo (requerido si document presente).
            caption: caption diferente al message (override). Si None, usa message.

        Returns: dict {'telegram': bool|None, 'whatsapp': bool|None}
            None = canal no usado por preferencia
            True/False = resultado del envío"""
        self.ensure_one()
        ch = self.notification_channel or 'both'
        result = {'telegram': None, 'whatsapp': None}
        cap = caption if caption is not None else message

        if ch in ('telegram', 'both'):
            if document:
                result['telegram'] = self.send_telegram_document(filename, document, caption=cap)
            else:
                result['telegram'] = self.send_telegram_message(message)

        if ch in ('whatsapp', 'both'):
            if document:
                result['whatsapp'] = self.send_whatsapp_document(filename, document, caption=cap)
            else:
                result['whatsapp'] = self.send_whatsapp_message(message)

        return result

    def send_telegram_document(self, filename, content_bytes, caption=None):
        """F2.7.3 — Envía un archivo PDF (u otro binary) al cliente vía Telegram.
        Args:
            filename: nombre que verá el usuario (ej. 'Reporte_Evento_E-123.pdf').
            content_bytes: bytes del documento.
            caption: texto opcional acompañante (max 1024 chars, Markdown).
        Returns: True si el send fue ok, False en cualquier fallo (sin lanzar).
        """
        self.ensure_one()
        if not self.telegram_chat_id:
            return False
        import requests
        try:
            url = f"https://api.telegram.org/bot{self._get_telegram_token()}/sendDocument"
            files = {'document': (filename, content_bytes, 'application/pdf')}
            data = {'chat_id': self.telegram_chat_id}
            if caption:
                data['caption'] = caption[:1024]
                data['parse_mode'] = 'Markdown'
            res = requests.post(url, data=data, files=files, timeout=30)
            return res.ok
        except Exception:
            return False

    def write(self, vals):
        # Si se están escribiendo coordenadas manualmente, marcar como manual
        if 'partner_latitude' in vals or 'partner_longitude' in vals:
            vals['manual_geolocation'] = True
        return super(ResPartner, self).write(vals)

    def geo_localize(self):
        """ Sobreescribir para evitar que Odoo borre o mueva las coordenadas manuales """
        # Si está marcado como manual, no hacer nada
        if self.manual_geolocation:
            return True
        # Si no es manual, permitir el comportamiento estándar (si es necesario)
        return super(ResPartner, self).geo_localize()

    def action_open_google_maps(self):
        self.ensure_one()
        if self.partner_latitude and self.partner_longitude:
            url = f"https://www.google.com/maps/search/?api=1&query={self.partner_latitude},{self.partner_longitude}"
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }
        return True

    def action_dial_ucm_ami(self):
        """
        Inicia una llamada a este contacto usando el Grandstream UCM6204 vía AMI.
        """
        self.ensure_one()
        if not self.phone and not self.mobile:
            return False

        operator_extension = self.env.user.sip_extension
        if not operator_extension:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error de Telefonía',
                    'message': 'No tienes una Extensión SIP configurada en tu perfil.',
                    'type': 'danger',
                    'sticky': False,
                }
            }

        # Limpiar número: Solo dígitos
        raw_number = "".join(filter(str.isdigit, str(self.mobile or self.phone)))
        
        # Lógica de prefijo '1': 
        # Si el número empieza con 52 (México), lo quitamos para poner el 1 de salida
        if raw_number.startswith('52') and len(raw_number) > 10:
            target_number = '1' + raw_number[2:]
        elif not raw_number.startswith('1'):
            target_number = '1' + raw_number
        else:
            target_number = raw_number

        # CONFIGURACION AMI
        host = "192.168.3.5"
        port = 7777
        user = "admin_ami"
        pw = "Sentinela"

        import socket
        import time
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((host, port))
            s.recv(1024)
            
            s.send(("Action: Login\r\nUsername: " + user + "\r\nSecret: " + pw + "\r\n\r\n").encode())
            time.sleep(1.0) # Aumentado a 1 segundo
            s.recv(1024)
            
            # Comando ultra-simple
            dial_cmd = "Action: Originate\r\n"
            dial_cmd += "Channel: Local/" + target_number + "@from-internal\r\n"
            dial_cmd += "Exten: " + str(operator_extension) + "\r\n"
            dial_cmd += "Context: from-internal\r\n"
            dial_cmd += "Priority: 1\r\n"
            dial_cmd += "Async: yes\r\n\r\n"
            
            print("Enviando comando AMI: " + dial_cmd)
            s.send(dial_cmd.encode())
            time.sleep(1.0) # Aumentado a 1 segundo
            s.send(b"Action: Logoff\r\n\r\n")
            time.sleep(0.5)
            s.close()

            self.message_post(body=f"📞 <b>Llamada:</b> Marcando al {target_number} para conectar con Ext. {operator_extension}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Llamada Iniciada',
                    'message': f'Marcando al {target_number}... Descuelga tu extensión {operator_extension}.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error de Conexión AMI',
                    'message': f'No se pudo contactar al AMI (Puerto 7777): {str(e)}',
                    'type': 'danger',
                    'sticky': False,
                }
            }
        return True
