from odoo import models, fields, api

class AlarmPriority(models.Model):
    _name = 'sentinela.alarm.priority'
    _description = 'Prioridad de Alarma Personalizable'
    _order = 'level desc'

    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(string='Código Interno', required=True, help="Ej. P1, P2, CRITICA")
    level = fields.Integer(string='Nivel (1-10)', default=1, required=True, help="10 es la más alta.")
    
    color_hex = fields.Char(string='Color Hex', default='#FFFFFF', help="Color de fondo para el Dashboard (Ej. #FF0000)")
    text_color_hex = fields.Char(string='Color Texto', default='#000000')
    
    # Sonido Personalizado (MP3)
    priority_sound = fields.Binary(string='Archivo de Sonido (MP3)', help="Cargue un archivo MP3 para esta prioridad.")
    priority_sound_filename = fields.Char(string='Nombre del Archivo Audio')
    
    is_reminder = fields.Boolean(string='Es Sonido de Recordatorio', default=False, help="Marque esto para usar este sonido como recordatorio suave cada 30 segundos.")
    blink = fields.Boolean(string='Parpadear en Dashboard', default=False)
    
    _sql_constraints = [
        ('level_uniq', 'unique(level)', 'Ya existe una prioridad con este nivel.'),
        ('code_uniq', 'unique(code)', 'El código debe ser único.')
    ]