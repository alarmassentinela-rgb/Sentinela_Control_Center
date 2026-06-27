import pytz
from datetime import timedelta

from odoo import models, fields, api

class SentinelaSubscriptionSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    connecta_client_id = fields.Char(
        string='Connecta Client ID (Correo)',
        config_parameter='sentinela.connecta_client_id',
        help="El correo electrónico usado para entrar al portal de Connecta/floLIVE."
    )
    connecta_access_token = fields.Char(
        string='Connecta Access Token (Contraseña)',
        config_parameter='sentinela.connecta_access_token',
        help="La contraseña usada para entrar al portal de Connecta/floLIVE."
    )
    # --- Comandos SMS GPS (placeholders de las plantillas) ---
    gps_apn = fields.Char(
        string='APN de las SIM GPS',
        config_parameter='sentinela.gps_apn',
        default='gigsky-02',
        help="APN que se inyecta en {apn} de las plantillas de comando. Fijo para las SIM floLIVE = gigsky-02."
    )
    gps_server_senticar = fields.Char(
        string='Servidor GPS — SentiCar',
        config_parameter='sentinela.gps_server_senticar',
        default='gps.senticar.com',
        help="Host al que marcan los rastreadores de SentiCar (rellena {server}). Usar el DOMINIO "
             "(gps.senticar.com, DNS-only → IP fija) y NO la IP cruda: si cambia la IP fija solo se "
             "actualiza el registro A, sin reconfigurar los GPS. ⚠️ Con dominio, el comando GT06 usa "
             "modo 1 (SERVER,1,...); con IP cruda sería modo 0."
    )
    gps_server_tracksolid = fields.Char(
        string='Servidor GPS — Tracksolid',
        config_parameter='sentinela.gps_server_tracksolid',
        help="Host/IP del servidor para equipos en Tracksolid Pro (rellena {server})."
    )
    gps_server_smake = fields.Char(
        string='Servidor GPS — Smake',
        config_parameter='sentinela.gps_server_smake',
        help="Host/IP del servidor para equipos en Smake (rellena {server})."
    )
    # --- SentiCar / Traccar (API + portal) ---
    traccar_api_url = fields.Char(
        string='SentiCar — URL de la API', config_parameter='sentinela.traccar_api_url',
        default='http://192.168.3.2:8082',
        help="URL interna de la API de SentiCar/Traccar (LAN). Ej.: http://192.168.3.2:8082")
    traccar_api_user = fields.Char(
        string='SentiCar — Usuario API', config_parameter='sentinela.traccar_api_user',
        help="Cuenta de servicio admin de Traccar que usa la integración (Basic Auth).")
    traccar_api_password = fields.Char(
        string='SentiCar — Contraseña API', config_parameter='sentinela.traccar_api_password',
        help="Contraseña de la cuenta de servicio de Traccar.")
    senticar_public_url = fields.Char(
        string='SentiCar — URL pública (panel)', config_parameter='sentinela.senticar_public_url',
        default='https://radar.senticar.com',
        help="URL pública del panel (para los links de rastreo). Ej.: https://radar.senticar.com")
    senticar_portal_base = fields.Char(
        string='SentiCar — Base portal transportista', config_parameter='sentinela.senticar_portal_base',
        default='https://senticar.com',
        help="Dominio base para armar el enlace del portal del transportista (/senticar/t/<token>).")
    senticar_admin_user_id = fields.Char(
        string='SentiCar — IDs de admins', config_parameter='sentinela.senticar_admin_user_id',
        help="IDs de usuarios admin de Traccar que deben ver toda la flota (lista, ej.: 1,5).")
    senticar_reconcile_autoheal = fields.Boolean(
        string='Auto-corregir desajustes (reconciliación)', config_parameter='sentinela.senticar_reconcile_autoheal',
        default=True,
        help="Si está activo, el cron de reconciliación corrige en SentiCar el estado habilitado/"
             "deshabilitado para que coincida con Odoo (no toca SIM ni borra nada).")
    senticar_share_max_hours = fields.Integer(
        string='Máx. horas de link de rastreo', config_parameter='sentinela.senticar_share_max_hours',
        default=168,
        help="Tope de duración de un link de rastreo temporal (por defecto 168 = 7 días).")
    senticar_root_group = fields.Char(
        string='Grupo raíz SentiCar', config_parameter='sentinela.senticar_root_group',
        default='SentiCar',
        help="Nombre del grupo 'paraguas' bajo el que cuelgan los clientes sin distribuidor. "
             "Vacío = sin grupo raíz (clientes al nivel superior).")

    # =========================================================================
    # Automatización de facturación/cobranza — panel de crones.
    # Capa 1: encender/apagar (ir.cron.active) + estado.
    # Capa 2: hora de ejecución (diarios) e intervalo, + control MASTER.
    # =========================================================================
    _BILLING_CRONS = {
        'auto_cron_generate':  'sentinela_subscriptions.ir_cron_generate_invoices',
        'auto_cron_stamp':     'sentinela_cfdi_prodigia.ir_cron_auto_stamp_prodigia',
        'auto_cron_suspend':   'sentinela_subscriptions.ir_cron_auto_suspend_overdue',
        'auto_cron_reminders': 'sentinela_subscriptions.ir_cron_send_payment_reminders',
        'auto_cron_leasing':   'sentinela_subscriptions.ir_cron_check_leasing_end',
    }
    # Crones por intervalo de HORAS (no tienen "hora de ejecución" fija del día).
    _BILLING_CRONS_HOURLY = {'auto_cron_stamp'}
    _CRON_INTERVAL_TYPES = [
        ('minutes', 'Minutos'), ('hours', 'Horas'), ('days', 'Días'),
        ('weeks', 'Semanas'), ('months', 'Meses'),
    ]

    # Control MASTER (enciende/apaga todos a la vez vía onchange).
    auto_cron_master = fields.Boolean(string='Facturación automática (encender/apagar TODO)')

    # Capa 1: toggles
    auto_cron_generate = fields.Boolean(string='Generar pre-facturas automáticamente')
    auto_cron_stamp = fields.Boolean(string='Timbrar facturas automáticamente (Prodigia)')
    auto_cron_suspend = fields.Boolean(string='Auto-suspender por facturas vencidas')
    auto_cron_reminders = fields.Boolean(string='Enviar recordatorios de cobranza')
    auto_cron_leasing = fields.Boolean(string='Revisar fin de leasing')

    # Capa 2: hora de ejecución (solo diarios) — Float HH:MM (widget float_time)
    auto_cron_generate_hour = fields.Float(string='Hora')
    auto_cron_suspend_hour = fields.Float(string='Hora')
    auto_cron_reminders_hour = fields.Float(string='Hora')
    auto_cron_leasing_hour = fields.Float(string='Hora')

    # Capa 2: intervalo (todos)
    auto_cron_generate_interval_number = fields.Integer(string='Cada')
    auto_cron_generate_interval_type = fields.Selection(_CRON_INTERVAL_TYPES, string='Unidad')
    auto_cron_stamp_interval_number = fields.Integer(string='Cada')
    auto_cron_stamp_interval_type = fields.Selection(_CRON_INTERVAL_TYPES, string='Unidad')
    auto_cron_suspend_interval_number = fields.Integer(string='Cada')
    auto_cron_suspend_interval_type = fields.Selection(_CRON_INTERVAL_TYPES, string='Unidad')
    auto_cron_reminders_interval_number = fields.Integer(string='Cada')
    auto_cron_reminders_interval_type = fields.Selection(_CRON_INTERVAL_TYPES, string='Unidad')
    auto_cron_leasing_interval_number = fields.Integer(string='Cada')
    auto_cron_leasing_interval_type = fields.Selection(_CRON_INTERVAL_TYPES, string='Unidad')

    # Estado (solo lectura)
    auto_cron_generate_info = fields.Char(compute='_compute_billing_cron_info')
    auto_cron_stamp_info = fields.Char(compute='_compute_billing_cron_info')
    auto_cron_suspend_info = fields.Char(compute='_compute_billing_cron_info')
    auto_cron_reminders_info = fields.Char(compute='_compute_billing_cron_info')
    auto_cron_leasing_info = fields.Char(compute='_compute_billing_cron_info')

    def _bc_cron(self, xmlid):
        return self.env.ref(xmlid, raise_if_not_found=False)

    def _bc_tz(self):
        return pytz.timezone(self.env.user.tz or self.env.company.partner_id.tz or 'America/Mexico_City')

    def _next_run_at_local_hour(self, hour_float):
        """Devuelve nextcall (UTC naïve) = próxima ocurrencia de esa hora local."""
        tz = self._bc_tz()
        now_local = pytz.utc.localize(fields.Datetime.now()).astimezone(tz)
        h = int(hour_float or 0)
        m = int(round(((hour_float or 0) - h) * 60))
        if m >= 60:
            h, m = h + 1, 0
        target = now_local.replace(hour=min(h, 23), minute=min(m, 59), second=0, microsecond=0)
        if target <= now_local:
            target += timedelta(days=1)
        return target.astimezone(pytz.utc).replace(tzinfo=None)

    def _compute_billing_cron_info(self):
        def fmt(rec, dt):
            return fields.Datetime.context_timestamp(rec, dt).strftime('%d/%m/%Y %H:%M') if dt else '—'
        for s in self:
            for fld, xmlid in self._BILLING_CRONS.items():
                c = self._bc_cron(xmlid)
                if not c:
                    s[fld + '_info'] = 'No encontrado'
                    continue
                estado = '🟢 Activo' if c.active else '🔴 Apagado'
                s[fld + '_info'] = '%s · cada %s %s · última: %s · próxima: %s' % (
                    estado, c.interval_number, c.interval_type, fmt(s, c.lastcall), fmt(s, c.nextcall))

    @api.onchange('auto_cron_master')
    def _onchange_auto_cron_master(self):
        for fld in self._BILLING_CRONS:
            self[fld] = self.auto_cron_master

    @api.model
    def get_values(self):
        res = super().get_values()
        all_on = True
        for fld, xmlid in self._BILLING_CRONS.items():
            c = self._bc_cron(xmlid)
            res[fld] = bool(c and c.active)
            all_on = all_on and bool(c and c.active)
            if c:
                res[fld + '_interval_number'] = c.interval_number
                res[fld + '_interval_type'] = c.interval_type
                if fld not in self._BILLING_CRONS_HOURLY and c.nextcall:
                    loc = pytz.utc.localize(c.nextcall).astimezone(self._bc_tz())
                    res[fld + '_hour'] = loc.hour + loc.minute / 60.0
        res['auto_cron_master'] = all_on
        return res

    def set_values(self):
        super().set_values()
        for fld, xmlid in self._BILLING_CRONS.items():
            c = self._bc_cron(xmlid)
            if not c:
                continue
            vals = {}
            if c.active != bool(self[fld]):
                vals['active'] = bool(self[fld])
            inum = self[fld + '_interval_number']
            itype = self[fld + '_interval_type']
            if inum and c.interval_number != inum:
                vals['interval_number'] = inum
            if itype and c.interval_type != itype:
                vals['interval_type'] = itype
            hfield = fld + '_hour'
            if hfield in self._fields:
                new_h = self[hfield] or 0.0
                cur = pytz.utc.localize(c.nextcall).astimezone(self._bc_tz()) if c.nextcall else None
                cur_h = (cur.hour + cur.minute / 60.0) if cur else None
                if cur_h is None or abs(new_h - cur_h) > 0.0084:  # ~30s de tolerancia
                    vals['nextcall'] = self._next_run_at_local_hour(new_h)
            if vals:
                c.sudo().write(vals)
        # El auto-timbrado tiene doble candado: además del cron, el parámetro auto_stamp_enabled.
        self.env['ir.config_parameter'].sudo().set_param(
            'sentinela_cfdi_prodigia.auto_stamp_enabled', '1' if self.auto_cron_stamp else '0')
