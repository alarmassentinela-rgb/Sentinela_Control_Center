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
    # Automatización de facturación/cobranza — encender/apagar crones (Capa 1).
    # Toggle = ir.cron.active. Solo ON/OFF + estado; la hora/intervalo NO se edita aquí.
    # =========================================================================
    _BILLING_CRONS = {
        'auto_cron_generate':  'sentinela_subscriptions.ir_cron_generate_invoices',
        'auto_cron_stamp':     'sentinela_cfdi_prodigia.ir_cron_auto_stamp_prodigia',
        'auto_cron_suspend':   'sentinela_subscriptions.ir_cron_auto_suspend_overdue',
        'auto_cron_reminders': 'sentinela_subscriptions.ir_cron_send_payment_reminders',
        'auto_cron_leasing':   'sentinela_subscriptions.ir_cron_check_leasing_end',
    }

    auto_cron_generate = fields.Boolean(string='Generar pre-facturas automáticamente')
    auto_cron_stamp = fields.Boolean(string='Timbrar facturas automáticamente (Prodigia)')
    auto_cron_suspend = fields.Boolean(string='Auto-suspender por facturas vencidas')
    auto_cron_reminders = fields.Boolean(string='Enviar recordatorios de cobranza')
    auto_cron_leasing = fields.Boolean(string='Revisar fin de leasing')

    auto_cron_generate_info = fields.Char(compute='_compute_billing_cron_info')
    auto_cron_stamp_info = fields.Char(compute='_compute_billing_cron_info')
    auto_cron_suspend_info = fields.Char(compute='_compute_billing_cron_info')
    auto_cron_reminders_info = fields.Char(compute='_compute_billing_cron_info')
    auto_cron_leasing_info = fields.Char(compute='_compute_billing_cron_info')

    def _bc_cron(self, xmlid):
        return self.env.ref(xmlid, raise_if_not_found=False)

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

    @api.model
    def get_values(self):
        res = super().get_values()
        for fld, xmlid in self._BILLING_CRONS.items():
            c = self._bc_cron(xmlid)
            res[fld] = bool(c and c.active)
        return res

    def set_values(self):
        super().set_values()
        for fld, xmlid in self._BILLING_CRONS.items():
            c = self._bc_cron(xmlid)
            val = bool(self[fld])
            if c and c.active != val:
                c.sudo().active = val
        # El auto-timbrado tiene doble candado: además del cron, el parámetro auto_stamp_enabled.
        self.env['ir.config_parameter'].sudo().set_param(
            'sentinela_cfdi_prodigia.auto_stamp_enabled', '1' if self.auto_cron_stamp else '0')
