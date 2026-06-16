from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class MonitoringContact(models.Model):
    _name = 'sentinela.monitoring.contact'
    _description = 'Contacto de Emergencia de Monitoreo'
    _order = 'sequence, id'

    device_id = fields.Many2one('sentinela.monitoring.device', string='Dispositivo / Panel', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Prioridad de Llamada', default=10)
    
    name = fields.Char(string='Nombre Completo', required=True)
    user_number = fields.Integer(string='Número de Usuario/Panel', help="El ID que reporta el panel (Ej. 1, 2, 99)")
    is_emergency_contact = fields.Boolean(string='Es Contacto de Emergencia', default=True, help="Si se marca, aparecerá en la lista de llamadas del operador.")
    phone = fields.Char(string='Teléfono / Móvil', required=True)
    email = fields.Char(string='Correo Electrónico')
    
    relation = fields.Char(string='Relación / Puesto', help="Ej. Propietario, Gerente, Esposa")
    
    notes = fields.Text(string='Notas / Horario')
    
    # Campos para auditoría y portal futuro
    is_active = fields.Boolean(string='Activo', default=True)
    last_update = fields.Datetime(string='Última Actualización', readonly=True, default=fields.Datetime.now)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['last_update'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        vals['last_update'] = fields.Datetime.now()
        return super().write(vals)

    def action_call_contact(self):
        """ Inicia la llamada a este contacto desde el conmutador.
        SIEMPRE devuelve una notificación (toast) para NO cerrar el modal
        de atención desde el que se dispara. """
        self.ensure_one()
        def _toast(msg, kind='success'):
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Telefonía', 'message': msg, 'type': kind, 'sticky': False},
            }
        if self.phone:
            # Intentar encontrar un evento de alarma activo en el contexto para registrar la nota
            event_id = self.env.context.get('active_alarm_event_id')
            if event_id:
                event = self.env['sentinela.alarm.event'].browse(event_id)
                event.action_click_to_call(self.phone)
                return _toast("Marcando a %s (%s) — descuelga tu extensión." % (self.name, self.phone))
            else:
                # Llamada directa sin evento
                operator_extension = self.env.user.sip_extension
                if not operator_extension:
                    return _toast("No tienes extensión SIP configurada en tu perfil.", 'danger')

                target_number = "".join(filter(str.isdigit, str(self.phone)))
                # Credenciales UCM/CDR desde ir.config_parameter (sembradas en el server, NO en el repo)
                icp = self.env['ir.config_parameter'].sudo()
                ucm_ip = icp.get_param('sentinela_monitoring.ucm_host') or "192.168.3.5:8089"
                api_user = icp.get_param('sentinela_monitoring.ucm_user') or "odoo_api"
                api_pass = icp.get_param('sentinela_monitoring.ucm_password')
                if not api_pass:
                    _logger.warning("UCM no configurado (sentinela_monitoring.ucm_password vacío); no se marca")
                    return _toast("Telefonía no configurada (falta ucm_password).", 'warning')

                import requests
                try:
                    login_url = f"https://{ucm_ip}/cgi?action=login&username={api_user}&password={api_pass}"
                    session = requests.Session()
                    login_res = session.get(login_url, timeout=5, verify=False)
                    if login_res.ok:
                        dial_url = f"https://{ucm_ip}/cgi?action=dial&extension={operator_extension}&number={target_number}"
                        session.get(dial_url, timeout=5, verify=False)
                    return _toast("Marcando a %s (%s)…" % (self.name, self.phone))
                except Exception as e:
                    _logger.warning("UCM dial falló para %s: %s", self.name, e)
                    return _toast("No se pudo contactar la central: %s" % e, 'danger')
        return _toast("Este contacto no tiene teléfono.", 'warning')
