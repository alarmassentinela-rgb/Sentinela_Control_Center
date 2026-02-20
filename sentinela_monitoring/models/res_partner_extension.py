from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_patrol = fields.Boolean(string='Es Patrulla', default=False)
    traccar_device_id = fields.Char(string='ID Dispositivo Traccar')
    last_gps_lat = fields.Float(string='Última Latitud', digits=(10, 7))
    last_gps_lng = fields.Float(string='Última Longitud', digits=(10, 7))
    last_gps_update = fields.Datetime(string='Última Actualización GPS')
