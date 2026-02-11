from odoo import models, fields, api

class FsmEvidence(models.Model):
    _name = 'sentinela.fsm.evidence'
    _description = 'Evidencia Fotográfica FSM'
    _order = 'create_date desc'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', required=True, ondelete='cascade')
    name = fields.Char(string='Descripción', required=True, default='Evidencia')
    evidence_type = fields.Selection([
        ('before', 'Antes del Trabajo'),
        ('during', 'Durante el Trabajo'),
        ('after', 'Resultado Final (Después)'),
        ('docs', 'Documentos / Otros')
    ], string='Tipo', default='after', required=True)
    
    image = fields.Image(string='Fotografía', required=True, max_width=1024, max_height=1024)
