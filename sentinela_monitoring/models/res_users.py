from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    sip_extension = fields.Char(string='Extensión SIP', help="Número de extensión del operador en el Grandstream UCM (Ej. 101)")
