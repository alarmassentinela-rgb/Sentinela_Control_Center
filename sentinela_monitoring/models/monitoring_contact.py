from odoo import models, fields, api

class MonitoringContact(models.Model):
    _name = 'sentinela.monitoring.contact'
    _description = 'Contacto de Emergencia de Monitoreo'
    _order = 'sequence, id'

    device_id = fields.Many2one('sentinela.monitoring.device', string='Dispositivo / Panel', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Prioridad de Llamada', default=10)
    
    name = fields.Char(string='Nombre Completo', required=True)
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
