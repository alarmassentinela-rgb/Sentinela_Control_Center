from odoo import models, fields, api

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
        """ Inicia la llamada a este contacto desde el conmutador """
        self.ensure_one()
        if self.phone:
            # Intentar encontrar un evento de alarma activo en el contexto para registrar la nota
            event_id = self.env.context.get('active_alarm_event_id')
            if event_id:
                event = self.env['sentinela.alarm.event'].browse(event_id)
                event.action_click_to_call(self.phone)
            else:
                # Llamada directa sin evento
                operator_extension = self.env.user.sip_extension
                if not operator_extension:
                    return False
                
                target_number = "".join(filter(str.isdigit, str(self.phone)))
                ucm_ip = "192.168.3.5:8089"
                api_user = "sentinela"
                api_pass = "cdrapi123"
                
                import requests
                try:
                    login_url = f"https://{ucm_ip}/cgi?action=login&username={api_user}&password={api_pass}"
                    session = requests.Session()
                    login_res = session.get(login_url, timeout=5, verify=False)
                    if login_res.ok:
                        dial_url = f"https://{ucm_ip}/cgi?action=dial&extension={operator_extension}&number={target_number}"
                        session.get(dial_url, timeout=5, verify=False)
                except: pass
        return True
