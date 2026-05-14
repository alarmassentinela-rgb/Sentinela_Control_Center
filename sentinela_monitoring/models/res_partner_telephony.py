from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_patrol = fields.Boolean(string='Es Patrulla', default=False)
    traccar_device_id = fields.Char(string='ID Dispositivo Traccar')
    last_gps_lat = fields.Float(string='Última Latitud', digits=(10, 7))
    last_gps_lng = fields.Float(string='Última Longitud', digits=(10, 7))
    last_gps_update = fields.Datetime(string='Última Actualización GPS')
    manual_geolocation = fields.Boolean(string='Geolocalización Manual', default=False)
    telegram_chat_id = fields.Char(string='Telegram Chat ID', help="ID de chat para notificaciones automáticas")

    def send_telegram_message(self, message):
        """ Envía un mensaje de Telegram a este contacto """
        self.ensure_one()
        if not self.telegram_chat_id:
            return False
        
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('sentinela_syscom.telegram_token') or "8373567654:AAGyLpZttCUaHh-LymQwEHRBOqwtVNXYN10"
        
        import requests
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            res = requests.post(url, data={'chat_id': self.telegram_chat_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
            return res.ok
        except:
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
            time.sleep(1.0)
            s.recv(1024)
            
            # VARIANTE 1: Primero suena el operador, al descolgar marca afuera
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
