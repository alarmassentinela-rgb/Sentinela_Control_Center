from odoo import models, fields

class SentinelaSatPaymentMethod(models.Model):
    _name = 'sentinela.sat.payment.method'
    _description = 'Metodos de Pago SAT'
    _order = 'code asc'

    code = fields.Char(string='Código SAT', required=True)
    name = fields.Char(string='Descripción', required=True)

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, f"{rec.code} - {rec.name}"))
        return result
