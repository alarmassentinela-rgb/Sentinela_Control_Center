from odoo import models, fields, api, _


class GpsCommandTemplate(models.Model):
    """Catálogo de comandos SMS de configuración de rastreadores GPS.

    Cada registro es una plantilla por familia de equipo (Concox/GT06/Jimi, Coban, etc.)
    y acción (Set APN / Set Server / Status / Locate / ...). El texto del comando lleva
    placeholders que se sustituyen al momento de armarlo para un equipo concreto:
        {apn}    -> param sentinela.gps_apn (gigsky-02 por defecto)
        {server} -> host de la plataforma de la suscripción (params sentinela.gps_server_*)
        {port}   -> puerto del protocolo (campo default_port de la plantilla)
        {pwd}    -> contraseña del equipo (gps_password del renglón, 666666 por defecto)
        {imei}   -> IMEI del equipo
    Así el operador NO teclea el comando: elige la plantilla y se arma solo (lo revisa
    antes de enviarlo con el botón existente 'Enviar SMS')."""
    _name = 'sentinela.gps.command.template'
    _description = 'Plantilla de Comando SMS GPS'
    _order = 'brand, sequence, id'

    name = fields.Char(string='Nombre', required=True,
                       help="Etiqueta visible en el selector. Ej.: 'N01K / GT06 — Configurar servidor'.")
    brand = fields.Selection([
        ('concox_gt06', 'Concox / Jimi / GT06 (N01K, etc.)'),
        ('coban', 'Coban (TK103 / TK303)'),
        ('teltonika', 'Teltonika'),
        ('generic', 'Genérico / Otro'),
    ], string='Familia de equipo', required=True, default='concox_gt06',
       help="Familia/marca a la que aplica la sintaxis del comando.")
    action_type = fields.Selection([
        ('set_apn', 'Configurar APN'),
        ('set_server', 'Configurar Servidor'),
        ('status', 'Estado / Status'),
        ('locate', 'Ubicar ahora'),
        ('interval', 'Intervalo de reporte'),
        ('reset', 'Reiniciar'),
        ('factory', 'Restaurar de fábrica'),
        ('relay', 'Corte de motor (relay)'),
        ('other', 'Otro'),
    ], string='Acción', required=True, default='status')
    command_template = fields.Char(string='Comando (plantilla)', required=True,
        help="Texto del SMS con placeholders: {apn} {server} {port} {pwd} {imei}. "
             "Ej. GT06: SERVER,0,{server},{port},0#  ·  Coban: adminip{pwd} {server} {port}")
    default_port = fields.Integer(string='Puerto del protocolo',
        help="Puerto del protocolo del equipo en el servidor (rellena {port}). Ej. GT06 ≈ 5023.")
    encoding = fields.Selection([('GSM-7', 'GSM-7'), ('UCS2', 'UCS2')],
                                default='GSM-7', string='Codificación', required=True)
    sequence = fields.Integer(string='Orden', default=10)
    note = fields.Char(string='Nota / ayuda')
    active = fields.Boolean(string='Activo', default=True)

    def render_for_device(self, device):
        """Devuelve (comando, encoding) con los placeholders resueltos para `device`
        (sentinela.subscription.gps.device)."""
        self.ensure_one()
        cfg = self.env['ir.config_parameter'].sudo()
        apn = cfg.get_param('sentinela.gps_apn') or 'gigsky-02'
        platform = device.gps_platform or 'senticar'
        server = (cfg.get_param('sentinela.gps_server_%s' % platform)
                  or cfg.get_param('sentinela.gps_server_senticar') or '')
        values = {
            'apn': apn,
            'server': server,
            'port': self.default_port or '',
            'pwd': device.gps_password or '666666',
            'imei': device.gps_imei or '',
        }
        try:
            command = self.command_template.format(**values)
        except (KeyError, IndexError):
            # placeholder desconocido: no truena, regresa la plantilla cruda
            command = self.command_template
        return command, self.encoding
