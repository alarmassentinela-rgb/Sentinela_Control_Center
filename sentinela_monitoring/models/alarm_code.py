from odoo import models, fields, api

class AlarmCode(models.Model):
    _name = 'sentinela.alarm.code'
    _description = 'Código de Alarma (Contact ID / SIA)'
    _rec_name = 'code'
    _order = 'code asc'

    code = fields.Char(string='Código (Event Code)', required=True, size=4, help="Ej. 130, 110")
    name = fields.Char(string='Descripción', required=True, translate=True, help="Ej. Robo, Fuego, Pánico")
    
    protocol_type = fields.Selection([
        ('contact_id', 'Contact ID (Ademco)'),
        ('sia', 'SIA DCS'),
        ('4_2', '4+2 Pulse'),
    ], string='Protocolo', default='contact_id', required=True)

    event_category = fields.Selection([
        ('alarm', 'Alarma (Emergencia)'),
        ('restore', 'Restauración'),
        ('status', 'Estado / Informativo'),
        ('trouble', 'Falla Técnica'),
        ('test', 'Prueba / Test'),
        ('open_close', 'Apertura / Cierre')
    ], string='Categoría de Evento', required=True, default='alarm')

    priority_id = fields.Many2one('sentinela.alarm.priority', string='Nivel de Prioridad')
    
    # --- NUEVOS CAMPOS DE INTELIGENCIA ---
    requires_attention = fields.Boolean(string='Mostrar en Dashboard', default=True, 
        help="Si se desmarca, la señal se archiva automáticamente sin alertar al operador.")
    
    play_sound = fields.Boolean(string='Activar Sirena', default=False,
        help="Si se marca, el dashboard emitirá un sonido de alarma al recibir este código.")
    
    color_hex = fields.Char(string='Color Visual', default='#FFFFFF', 
        help="Color de fondo para la tarjeta en el dashboard.")
    # -------------------------------------

    is_billable = fields.Boolean(string='Generable Cobro?', help="Si es True, este evento podría generar un cargo por evento.")

    _sql_constraints = [
        ('code_protocol_uniq', 'unique(code, protocol_type)', 'El código debe ser único por protocolo.')
    ]