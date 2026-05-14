from odoo import models, fields, api

class SentinelaServiceDefinition(models.Model):
    _name = 'sentinela.service.definition'
    _description = 'Definición de Conceptos de Servicio'

    name = fields.Char(string='Concepto de Servicio', required=True)
    code = fields.Selection([
        ('patrol', 'Patrullaje por Evento'),
        ('maintenance', 'Mantenimiento Preventivo'),
        ('night_unit', 'Unidad de Patrullaje (Base Nocturna)'),
        ('other', 'Otro Servicio')
    ], string='Código Técnico', required=True)
    
    default_price = fields.Float(string='Precio Base (Sin IVA)', default=0.0)
    active = fields.Boolean(default=True)

class SentinelaProductServiceInclusion(models.Model):
    _name = 'sentinela.product.service.inclusion'
    _description = 'Matriz de Inclusión de Servicios por Plan'

    product_id = fields.Many2one('product.template', string='Plan / Membresía', ondelete='cascade')
    service_id = fields.Many2one('sentinela.service.definition', string='Servicio', required=True)
    
    is_included = fields.Boolean(string='Incluido en Plan', default=False)
    extra_price = fields.Float(string='Precio si es Extra', help="Precio a cobrar si no está incluido.")

class SentinelaSubscriptionServiceInclusion(models.Model):
    _name = 'sentinela.subscription.service.inclusion'
    _description = 'Derechos de Servicio del Contrato'

    subscription_id = fields.Many2one('sentinela.subscription', string='Contrato', ondelete='cascade')
    service_id = fields.Many2one('sentinela.service.definition', string='Servicio')
    
    service_code = fields.Selection(related='service_id.code', store=True)
    is_included = fields.Boolean(string='Incluido', default=False)
    extra_price = fields.Float(string='Precio Extra')
