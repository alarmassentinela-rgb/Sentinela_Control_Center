from odoo import models, fields, api

class AlarmPriority(models.Model):
    _name = 'sentinela.alarm.priority'
    _description = 'Prioridad de Alarma Personalizable'
    _order = 'level asc'

    active = fields.Boolean(string='Activa', default=True)
    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(string='Código Interno', required=True, help="Ej. P1, P2, CRITICA")
    level = fields.Integer(string='Nivel', default=1, required=True,
                           help="1 = la más importante (sirena); el número sube = menos importante.")
    
    color_hex = fields.Char(string='Color Hex', default='#FFFFFF', help="Color de fondo para el Dashboard (Ej. #FF0000)")
    text_color_hex = fields.Char(string='Color Texto', default='#000000')
    
    # Sonido Personalizado (MP3/WAV)
    priority_sound = fields.Binary(string='Archivo de Sonido (MP3/WAV)', help="Cargue un archivo MP3 o WAV para esta prioridad.")
    priority_sound_filename = fields.Char(string='Nombre del Archivo Audio')
    
    is_reminder = fields.Boolean(string='Es Sonido de Recordatorio', default=False, help="Marque esto para usar este sonido como recordatorio suave cada 30 segundos.")
    blink = fields.Boolean(string='Parpadear en Dashboard', default=False)

    # F2.3 — SLA por prioridad (minutos hasta que operador debe reconocer)
    sla_response_minutes = fields.Integer(
        string='SLA Reconocimiento (min)',
        default=0,
        help='Minutos máximos para que un operador reconozca un evento de esta '
             'prioridad. 0 = sin SLA. Los eventos sin reconocer pasan a estado '
             "'overdue' al cumplirse el plazo.")
    
    _sql_constraints = [
        ('level_uniq', 'unique(level)', 'Ya existe una prioridad con este nivel.'),
        ('code_uniq', 'unique(code)', 'El código debe ser único.')
    ]