from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SubscriptionGpsDevice(models.Model):
    """Un equipo GPS dentro de una suscripción. Una suscripción GPS = N equipos (renglones).
    Todos los equipos de una sub son del MISMO modo (lo define el plan): 'vehiculo' (SIM nuestra,
    se corta al suspender) o 'movil' (SIM del cliente, NUNCA se corta)."""
    _name = 'sentinela.subscription.gps.device'
    _description = 'Equipo GPS de Suscripción'

    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción',
                                      required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Alias / Unidad', required=True,
                       help="Ej.: Unidad 1, Camioneta Ventas, Celular Juan.")
    gps_imei = fields.Char(string='IMEI / Device-ID',
                           help="IMEI del rastreador (vehículo) o el identificador del equipo en la app (móvil).")
    sim_iccid = fields.Char(string='ICCID SIM',
                            help="Solo aplica a GPS de vehículo (SIM nuestra). En rastreo móvil la SIM es del cliente: dejar vacío.")
    # Modo y plataforma vienen de la suscripción (uniformes por sub)
    gps_mode = fields.Selection(related='subscription_id.gps_mode', store=True, string='Modo')
    gps_platform = fields.Selection(related='subscription_id.gps_platform', store=True, string='Plataforma')

    # Suspensión TEMPORAL por equipo (a petición del cliente). Distinto de eliminar:
    # es reversible, conserva el registro, deja de rastrear (SIM cortada) y NO se factura.
    device_state = fields.Selection([
        ('active', 'Activo'),
        ('suspended', 'Suspendido'),
    ], string='Estado', default='active', required=True, copy=False,
       help="Suspendido = pausa temporal: corta la SIM (deja de rastrear) y NO se factura "
            "mientras esté suspendido. Reactivar lo restaura. Para baja definitiva, elimínalo.")

    # Vehículo / equipo
    vehicle_plate = fields.Char(string='Placa')
    vehicle_brand = fields.Char(string='Marca Vehículo')
    vehicle_model = fields.Char(string='Modelo Vehículo')
    equipment_brand = fields.Char(string='Marca Equipo')
    equipment_model = fields.Char(string='Modelo Equipo')
    equipment_serial = fields.Char(string='No. Serie')

    # Enlace SentiCar
    senticar_device_id = fields.Integer(string='ID en SentiCar', readonly=True, copy=False)
    senticar_state = fields.Selection([
        ('pending', 'Pendiente'),
        ('registered', 'Registrado'),
        ('disabled', 'Deshabilitado'),
        ('error', 'Error'),
        ('drift', 'Desincronizado'),
    ], string='Estado SentiCar', default='pending', readonly=True, copy=False,
       help="Sincronización del equipo en SentiCar/Traccar. 'Error' = no se pudo registrar/no existe; "
            "'Desincronizado' = el estado en SentiCar no coincide con lo que dice Odoo (lo detecta y, si "
            "está activo el auto-arreglo, lo corrige el cron de reconciliación).")
    senticar_sync_msg = fields.Char(string='Detalle SentiCar', readonly=True, copy=False)
    senticar_sync_date = fields.Datetime(string='Verificado en SentiCar', readonly=True, copy=False)

    # Diagnóstico SIM (solo lectura, floLIVE) — útil para modo vehículo
    gps_sim_status = fields.Char(string='Estado SIM', readonly=True)
    gps_sim_online = fields.Boolean(string='En datos', readonly=True)
    gps_sim_lat = fields.Char(string='Latitud', readonly=True)
    gps_sim_lon = fields.Char(string='Longitud', readonly=True)
    gps_sim_checked = fields.Datetime(string='Diag. actualizado', readonly=True)

    # Link de rastreo temporal (compartir con el dueño de la carga, etc.)
    gps_share_hours = fields.Integer(string='Horas del link', default=24,
        help="Cuántas horas será válido el link de rastreo compartido.")
    gps_share_link = fields.Char(string='Link de rastreo', readonly=True, copy=False,
        help="Link público temporal para rastrear SOLO esta unidad (sin cuenta). Cópialo y compártelo (WhatsApp).")

    # Comandos SMS (solo vehículo / SIM nuestra)
    gps_password = fields.Char(string='Contraseña equipo', default='666666',
        help="Contraseña del rastreador para comandos SMS (rellena {pwd} en las plantillas). "
             "Default de fábrica típico = 666666 (GT06/Coban).")
    gps_command_template_id = fields.Many2one('sentinela.gps.command.template',
        string='Plantilla de comando', copy=False,
        help="Elige una plantilla y el comando se arma solo abajo (lo revisas antes de enviar).")
    gps_sms_command = fields.Char(string='Comando SMS')
    gps_sms_encoding = fields.Selection([('GSM-7', 'GSM-7'), ('UCS2', 'UCS2')], default='GSM-7', string='Codif.')
    gps_sms_log = fields.Text(string='Bitácora SMS', readonly=True)

    @api.onchange('gps_command_template_id')
    def _onchange_gps_command_template(self):
        """Al elegir una plantilla, arma el comando (con placeholders resueltos) en el campo
        editable para que el operador lo revise antes de enviarlo."""
        if self.gps_command_template_id:
            command, encoding = self.gps_command_template_id.render_for_device(self)
            self.gps_sms_command = command
            self.gps_sms_encoding = encoding

    # ---- Acciones por equipo ----
    def action_register_senticar(self):
        for dev in self:
            dev.subscription_id._senticar_register_device(dev)

    def action_generate_share_link(self):
        """Genera el link público temporal para rastrear SOLO esta unidad (X horas)."""
        self.ensure_one()
        if not self.senticar_device_id:
            raise UserError(_("Primero registra el equipo en SentiCar (botón 📲 Registrar)."))
        res = self.env['sentinela.senticar.service'].create_share_link(
            self.senticar_device_id, hours=self.gps_share_hours or 24,
            label=self.name or 'Rastreo')
        if not res.get('ok'):
            raise UserError(_("No se pudo generar el link: %s") % res.get('detail'))
        self.gps_share_link = res['link']
        self.subscription_id.message_post(body=_(
            "📍 <b>Link de rastreo</b> generado para <b>%s</b> (válido %sh): %s"
        ) % (self.name, self.gps_share_hours or 24, res['link']))

    def action_refresh_diag(self):
        self.ensure_one()
        if not self.sim_iccid:
            raise UserError(_("Este equipo no tiene ICCID (SIM nuestra) para diagnosticar."))
        diag = self.env['sentinela.flolive.service'].get_sim_diagnostics(self.sim_iccid)
        if not diag.get('ok'):
            raise UserError(_("No se pudo obtener el diagnóstico de floLIVE."))
        self.write({
            'gps_sim_status': diag.get('status'),
            'gps_sim_online': diag.get('online'),
            'gps_sim_lat': str(diag['lat']) if diag.get('lat') is not None else False,
            'gps_sim_lon': str(diag['lon']) if diag.get('lon') is not None else False,
            'gps_sim_checked': fields.Datetime.now(),
        })

    def action_send_sms(self):
        self.ensure_one()
        if self.gps_mode == 'movil':
            raise UserError(_("El rastreo móvil usa la SIM del cliente: no enviamos SMS."))
        if not self.sim_iccid:
            raise UserError(_("Falta el ICCID de la SIM."))
        if not self.gps_sms_command:
            raise UserError(_("Escribe el comando SMS."))
        res = self.env['sentinela.flolive.service'].send_sms_command(
            self.sim_iccid, self.gps_sms_command, encoding=self.gps_sms_encoding or 'GSM-7')
        ts = fields.Datetime.now()
        mark = '✅' if res.get('ok') else '⚠️'
        self.gps_sms_log = (f"[{ts}] {mark} «{self.gps_sms_command}» → {res.get('detail')}\n" + (self.gps_sms_log or "")).strip()
        if res.get('ok'):
            self.gps_sms_command = False
            self.gps_command_template_id = False

    # ---- Suspensión temporal por equipo ----
    def action_suspend_device(self):
        """Suspensión TEMPORAL del equipo (a petición del cliente): corta su SIM floLIVE
        (modo vehículo), lo deshabilita en SentiCar si aplica, y lo marca Suspendido para que
        NO se facture. Reversible con action_reactivate_device. NO borra el registro."""
        flo = self.env['sentinela.flolive.service']
        svc = self.env['sentinela.senticar.service']
        for dev in self:
            if dev.device_state == 'suspended':
                continue
            if dev.gps_mode == 'vehiculo' and dev.sim_iccid:
                try:
                    if flo.update_sim_status(dev.sim_iccid, 'SUSPENDED'):
                        dev.gps_sim_status = 'SUSPENDED'
                    else:
                        dev.subscription_id.message_post(body=_(
                            "⚠️ floLIVE: no se pudo cortar la SIM %s de «%s»; revisar manualmente.")
                            % (dev.sim_iccid, dev.name))
                except Exception as e:
                    _logger.error("floLIVE suspend %s: %s", dev.sim_iccid, e)
            if dev.senticar_device_id:
                try:
                    svc.set_device_disabled(dev.senticar_device_id, True)
                    dev.write({'senticar_state': 'disabled', 'senticar_sync_msg': 'Deshabilitado (suspensión temporal)',
                               'senticar_sync_date': fields.Datetime.now()})
                except Exception as e:
                    _logger.error("SENTICAR suspend device %s: %s", dev.senticar_device_id, e)
            dev.device_state = 'suspended'
            dev.subscription_id.message_post(body=_(
                "⏸️ Equipo <b>%s</b> (IMEI %s) SUSPENDIDO temporalmente: deja de rastrear y "
                "NO se factura mientras esté suspendido.") % (dev.name, dev.gps_imei or '—'))

    def action_reactivate_device(self):
        """Reactiva un equipo suspendido: restaura su SIM floLIVE, lo re-habilita en SentiCar
        si aplica, y vuelve a contar para la facturación."""
        flo = self.env['sentinela.flolive.service']
        svc = self.env['sentinela.senticar.service']
        for dev in self:
            if dev.device_state != 'suspended':
                continue
            if dev.gps_mode == 'vehiculo' and dev.sim_iccid:
                try:
                    if flo.update_sim_status(dev.sim_iccid, 'ACTIVE'):
                        dev.gps_sim_status = 'ACTIVE'
                    else:
                        dev.subscription_id.message_post(body=_(
                            "⚠️ floLIVE: no se pudo reactivar la SIM %s de «%s»; revisar manualmente.")
                            % (dev.sim_iccid, dev.name))
                except Exception as e:
                    _logger.error("floLIVE reactivate %s: %s", dev.sim_iccid, e)
            if dev.senticar_device_id:
                try:
                    svc.set_device_disabled(dev.senticar_device_id, False)
                    dev.write({'senticar_state': 'registered', 'senticar_sync_msg': 'Reactivado',
                               'senticar_sync_date': fields.Datetime.now()})
                except Exception as e:
                    _logger.error("SENTICAR reactivate device %s: %s", dev.senticar_device_id, e)
            dev.device_state = 'active'
            dev.subscription_id.message_post(body=_(
                "▶️ Equipo <b>%s</b> (IMEI %s) REACTIVADO: vuelve a rastrear y a facturarse.")
                % (dev.name, dev.gps_imei or '—'))

    def unlink(self):
        # Al quitar el equipo de la suscripción, deshabilitarlo en SentiCar (no borrar histórico).
        svc = self.env['sentinela.senticar.service']
        for dev in self:
            if dev.senticar_device_id:
                try:
                    svc.set_device_disabled(dev.senticar_device_id, True)
                except Exception as e:
                    _logger.error("SENTICAR unlink device %s: %s", dev.senticar_device_id, e)
        return super().unlink()
