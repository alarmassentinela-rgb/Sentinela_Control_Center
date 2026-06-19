from odoo import models, fields, api
import base64
import logging
import re
import secrets

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_patrol = fields.Boolean(string='Es Patrulla', default=False)
    traccar_device_id = fields.Char(string='ID Dispositivo Traccar')
    default_patrol_unit_id = fields.Many2one('sentinela.patrol.unit',
        string='Unidad por defecto',
        domain="[('available', '=', True)]",
        help='Unidad (celular o vehículo) que este patrullero usa normalmente. '
             'Se preselecciona al despacharlo; el operador puede cambiarla por un vehículo del catálogo.')
    last_gps_lat = fields.Float(string='Última Latitud', digits=(10, 7))
    last_gps_lng = fields.Float(string='Última Longitud', digits=(10, 7))
    last_gps_update = fields.Datetime(string='Última Actualización GPS')
    manual_geolocation = fields.Boolean(string='Geolocalización Manual', default=False)
    telegram_chat_id = fields.Char(string='Telegram Chat ID', help="ID de chat para notificaciones automáticas")
    # Vinculación por Telegram: token de un solo sentido que va en la liga t.me/<bot>?start=<token>.
    # El cliente abre la liga, da /start, comparte su contacto y el cron escribe telegram_chat_id solo.
    telegram_link_token = fields.Char(string='Token de Vinculación Telegram', copy=False, readonly=True, index=True)
    telegram_link_url = fields.Char(string='Liga de Telegram', compute='_compute_telegram_link_url')
    # Consentimiento (opt-in): fecha del primer /start del cliente al Bot Clientes.
    telegram_opt_in_date = fields.Datetime(string='Aceptó Telegram (opt-in)', readonly=True, copy=False,
        help="Fecha/hora en que el cliente aceptó recibir avisos por Telegram (su primer /start).")
    # Qué BOT capturó el chat_id (= el mismo que puede enviarle). Lo sella el cron al vincular.
    telegram_bot = fields.Selection([
        ('client', 'Clientes (SentiBot)'),
        ('internal', 'Interno (Sentinela)'),
    ], string='Bot de Telegram', readonly=True, copy=False,
       help="Bot por el que está vinculado este contacto. El chat_id solo sirve para enviar "
            "desde este mismo bot. Lo determina el cron según por cuál bot dio /start.")

    @api.model_create_multi
    def create(self, vals_list):
        # Cada partner nace con su token de vinculación (como FSM con tracking_token):
        # así factura/portal pueden pintar el QR personal sin escribir en tiempo de render.
        for vals in vals_list:
            if not vals.get('telegram_link_token'):
                vals['telegram_link_token'] = secrets.token_urlsafe(24)
        return super().create(vals_list)

    def _is_internal_staff(self):
        """True si el partner corresponde a un usuario interno de Odoo (no portal/cliente)."""
        self.ensure_one()
        return bool(self.user_ids.filtered(lambda u: not u.share))

    def _telegram_bot_kind(self):
        """Qué bot le toca a este partner para INVITAR: interno si es personal de Odoo,
        si no, clientes."""
        self.ensure_one()
        return 'internal' if self._is_internal_staff() else 'client'

    def _telegram_bot_username(self, kind='client'):
        ICP = self.env['ir.config_parameter'].sudo()
        key = ('sentinela_monitoring.telegram_internal_bot_username' if kind == 'internal'
               else 'sentinela_monitoring.telegram_client_bot_username')
        return (ICP.get_param(key) or '').lstrip('@')

    def _telegram_invite_url(self):
        """Asegura el token y devuelve la liga t.me del bot que le toca (interno/cliente),
        o False si ese bot no está configurado."""
        self.ensure_one()
        username = self._telegram_bot_username(self._telegram_bot_kind())
        if not username:
            return False
        if not self.telegram_link_token:
            self.sudo().telegram_link_token = secrets.token_urlsafe(24)
        return f"https://t.me/{username}?start={self.telegram_link_token}"

    def _telegram_qr_for_report(self):
        """QR (PNG base64) de la liga de invitación, para embeber en factura/portal.
        Devuelve False si el cliente YA está vinculado (no lo molestamos), si no hay
        bot configurado, o si falla la generación. Sin lanzar."""
        self.ensure_one()
        if self.telegram_chat_id:
            return False  # ya vinculado → no invitar
        url = self._telegram_invite_url()
        if not url:
            return False
        try:
            import qrcode, io, base64
            buf = io.BytesIO()
            qrcode.make(url).save(buf, format='PNG')
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return False

    @api.depends('telegram_link_token', 'user_ids.share')
    def _compute_telegram_link_url(self):
        for partner in self:
            username = partner._telegram_bot_username(partner._telegram_bot_kind())
            if partner.telegram_link_token and username:
                partner.telegram_link_url = f"https://t.me/{username}?start={partner.telegram_link_token}"
            else:
                partner.telegram_link_url = False

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
        # El token vive en ir.config_parameter (sembrado en el server, NO en el repo).
        # IMPORTANTE: el chat_id es POR BOT → el bot que CAPTURÓ el chat_id es el único que
        # le puede enviar. Por eso ruteamos por el bot del partner (telegram_bot):
        #   - 'internal' → bot Sentinela (personal de Odoo)
        #   - 'client'/None → Bot Clientes (SentiBot), con fallback al token histórico.
        p = self.env['ir.config_parameter'].sudo()
        if self and self.telegram_bot == 'internal':
            return (p.get_param('sentinela_monitoring.telegram_internal_bot_token')
                    or p.get_param('sentinela_syscom.telegram_token'))
        return (p.get_param('sentinela_monitoring.telegram_client_bot_token')
                or p.get_param('sentinela_syscom.telegram_token'))

    def send_telegram_message(self, message):
        """ Envía un mensaje de Telegram a este contacto """
        self.ensure_one()
        if not self.telegram_chat_id:
            return False
        token = self._get_telegram_token()
        if not token:
            _logger.warning("Telegram no configurado (sentinela_syscom.telegram_token vacío)")
            return False

        import requests
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            res = requests.post(url, data={'chat_id': self.telegram_chat_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
            return res.ok
        except:
            return False

    # ---------------- Vinculación de cliente por Telegram ----------------

    def action_generate_telegram_link(self):
        """Genera (o reusa) el token de vinculación y devuelve la liga t.me para
        mandársela al cliente. El cliente abre la liga → /start → comparte contacto →
        el cron _cron_telegram_poll_updates escribe su telegram_chat_id."""
        self.ensure_one()
        url = self._telegram_invite_url()
        if not url:
            kind = self._telegram_bot_kind()
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {
                    'title': 'Falta configurar el bot',
                    'message': f"Define el usuario del bot ({kind}) en Parámetros del sistema "
                               f"(sentinela_monitoring.telegram_{'internal' if kind=='internal' else 'client'}_bot_username).",
                    'type': 'danger', 'sticky': True,
                },
            }
        destino = 'personal interno (bot Sentinela)' if self._is_internal_staff() else 'cliente (SentiBot)'
        self.message_post(body=f"🔗 Liga de vinculación Telegram [{destino}]:<br/><a href='{url}'>{url}</a>")
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': 'Liga generada',
                'message': f"Liga para {destino}:\n{url}\n(quedó también en la bitácora).",
                'type': 'success', 'sticky': True,
            },
        }

    @api.model
    def _telegram_api(self, method, payload, token, files=None, timeout=20):
        """Llamada cruda al Bot API usando el token EXPLÍCITO del bot dado. JSON o None."""
        if not token:
            return None
        import requests
        try:
            url = f"https://api.telegram.org/bot{token}/{method}"
            res = requests.post(url, data=payload, files=files, timeout=timeout)
            return res.json()
        except Exception as e:
            _logger.warning("Telegram %s falló: %s", method, e)
            return None

    @api.model
    def _cron_telegram_poll_updates(self):
        """Cron de vinculación. Sondea AMBOS bots con offsets separados y etiqueta cada
        chat_id con el bot que lo capturó (telegram_bot):
          - Bot Clientes (SentiBot)  → telegram_bot='client'
          - Bot Sentinela (interno)  → telegram_bot='internal'
        Cada bot tiene su propio getUpdates (sin conflicto entre sí). Ninguno debe tener
        webhook (si lo tiene, getUpdates da 409 y se ignora ese bot)."""
        ICP = self.env['ir.config_parameter'].sudo()
        bots = [
            ('client',
             ICP.get_param('sentinela_monitoring.telegram_client_bot_token'),
             'sentinela_monitoring.telegram_getupdates_offset'),
            ('internal',
             ICP.get_param('sentinela_monitoring.telegram_internal_bot_token')
             or ICP.get_param('sentinela_syscom.telegram_token'),
             'sentinela_monitoring.telegram_internal_getupdates_offset'),
        ]
        for kind, token, offset_key in bots:
            if token:
                self._telegram_poll_one_bot(kind, token, offset_key)

    @api.model
    def _telegram_poll_one_bot(self, bot_kind, token, offset_key):
        """Procesa los updates de UN bot. Best-effort: si falla, no toca el offset."""
        ICP = self.env['ir.config_parameter'].sudo()
        offset = int(ICP.get_param(offset_key) or 0)
        import requests
        try:
            res = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={'offset': offset, 'timeout': 0, 'allowed_updates': '["message"]'},
                timeout=20,
            )
            data = res.json()
        except Exception as e:
            _logger.warning("Telegram getUpdates (%s) falló: %s", bot_kind, e)
            return
        if not data.get('ok'):
            _logger.warning("Telegram getUpdates (%s) no-ok: %s", bot_kind, data.get('description'))
            return

        max_update_id = offset
        for upd in data.get('result', []):
            max_update_id = max(max_update_id, upd['update_id'] + 1)
            msg = upd.get('message') or {}
            chat = msg.get('chat') or {}
            chat_id = chat.get('id')
            if not chat_id:
                continue
            chat_id = str(chat_id)
            text = (msg.get('text') or '').strip()
            contact = msg.get('contact')

            # 1) /start <token> → vincula el chat_id al partner del token, etiquetando el bot
            if text.startswith('/start'):
                parts = text.split(maxsplit=1)
                link_token = parts[1].strip() if len(parts) > 1 else ''
                partner = self.search([('telegram_link_token', '=', link_token)], limit=1) if link_token else False
                if partner:
                    vals = {'telegram_chat_id': chat_id, 'telegram_bot': bot_kind}
                    if not partner.telegram_opt_in_date:
                        vals['telegram_opt_in_date'] = fields.Datetime.now()
                    partner.write(vals)
                    quien = 'el cliente' if bot_kind == 'client' else 'personal interno'
                    partner.message_post(body=f"✅ Telegram vinculado por {quien} (chat_id {chat_id}, bot {bot_kind}).")
                    self._telegram_api('sendMessage', {
                        'chat_id': chat_id,
                        'text': f"¡Hola {partner.name}! Quedaste vinculado a Sentinela ✅\n"
                                "Por favor comparte tu número para confirmar tu cuenta.",
                        'reply_markup': '{"keyboard":[[{"text":"📱 Compartir mi número","request_contact":true}]],'
                                        '"resize_keyboard":true,"one_time_keyboard":true}',
                    }, token)
                else:
                    self._telegram_api('sendMessage', {
                        'chat_id': chat_id,
                        'text': "No reconozco esta liga. Pídele a Sentinela tu liga de vinculación personal.",
                    }, token)
                continue

            # 2) Contacto compartido → guarda el teléfono en el partner de ESTE bot
            if contact and contact.get('phone_number'):
                partner = self.search([('telegram_chat_id', '=', chat_id),
                                       ('telegram_bot', '=', bot_kind)], limit=1)
                if partner:
                    if not partner.whatsapp_number:
                        partner.whatsapp_number = contact['phone_number']
                    partner.message_post(body=f"📱 Teléfono confirmado por Telegram: {contact['phone_number']}")
                    self._telegram_api('sendMessage', {
                        'chat_id': chat_id,
                        'text': "Listo, ya recibirás tus avisos por aquí. 🛡️",
                        'reply_markup': '{"remove_keyboard":true}',
                    }, token)

        if max_update_id != offset:
            ICP.set_param(offset_key, str(max_update_id))

    # ---------------- F3 WhatsApp vía EvoApi ----------------

    def _get_evoapi_config(self):
        params = self.env['ir.config_parameter'].sudo()
        # url/instance no son secretos → default razonable. key SÍ es secreto → sin default (se siembra en el server).
        return {
            'url': params.get_param('sentinela_monitoring.evoapi_url') or 'http://192.168.3.2:8080',
            'key': params.get_param('sentinela_monitoring.evoapi_key') or '',
            'instance': params.get_param('sentinela_monitoring.evoapi_instance') or 'SentinelaWA',
        }

    def _get_ami_config(self):
        """Config del AMI del conmutador Grandstream UCM. host/port/user con
        default (no secretos); la password vive en ir.config_parameter, sembrada
        en el server (NO en el repo). Returns dict o None si falta la password."""
        params = self.env['ir.config_parameter'].sudo()
        pw = params.get_param('sentinela_monitoring.ami_password')
        if not pw:
            _logger.warning("AMI no configurado (sentinela_monitoring.ami_password vacío)")
            return None
        return {
            'host': params.get_param('sentinela_monitoring.ami_host') or '192.168.3.5',
            'port': int(params.get_param('sentinela_monitoring.ami_port') or 7777),
            'user': params.get_param('sentinela_monitoring.ami_user') or 'admin_ami',
            'password': pw,
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

        # CONFIGURACION AMI (desde ir.config_parameter)
        ami = self._get_ami_config()
        if not ami:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Telefonía no configurada',
                    'message': 'Falta la contraseña del AMI (sentinela_monitoring.ami_password) en Parámetros del sistema.',
                    'type': 'danger',
                    'sticky': False,
                }
            }

        import socket
        import time
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((ami['host'], ami['port']))
            s.recv(1024)

            s.send(("Action: Login\r\nUsername: " + ami['user'] + "\r\nSecret: " + ami['password'] + "\r\n\r\n").encode())
            time.sleep(1.0)
            s.recv(1024)

            # Primero suena el operador, al descolgar marca afuera
            dial_cmd = "Action: Originate\r\n"
            dial_cmd += "Channel: Local/" + str(operator_extension) + "@from-internal\r\n"
            dial_cmd += "Exten: " + target_number + "\r\n"
            dial_cmd += "Context: from-internal\r\n"
            dial_cmd += "Priority: 1\r\n"
            dial_cmd += "CallerID: Sentinela <" + str(operator_extension) + ">\r\n"
            dial_cmd += "Async: yes\r\n\r\n"

            s.send(dial_cmd.encode())
            time.sleep(1.0)
            s.send(b"Action: Logoff\r\n\r\n")
            s.close()

            self.message_post(body=f"📞 <b>Llamada:</b> Conectando Ext. {operator_extension} con el número {target_number}")
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
