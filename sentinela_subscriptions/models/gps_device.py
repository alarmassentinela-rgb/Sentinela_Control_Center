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

    # Vehículo / equipo
    vehicle_plate = fields.Char(string='Placa')
    vehicle_brand = fields.Char(string='Marca Vehículo')
    vehicle_model = fields.Char(string='Modelo Vehículo')
    equipment_brand = fields.Char(string='Marca Equipo')
    equipment_model = fields.Char(string='Modelo Equipo')
    equipment_serial = fields.Char(string='No. Serie')

    # Enlace SentiCar
    senticar_device_id = fields.Integer(string='ID en SentiCar', readonly=True, copy=False)

    # Diagnóstico SIM (solo lectura, floLIVE) — útil para modo vehículo
    gps_sim_status = fields.Char(string='Estado SIM', readonly=True)
    gps_sim_online = fields.Boolean(string='En datos', readonly=True)
    gps_sim_lat = fields.Char(string='Latitud', readonly=True)
    gps_sim_lon = fields.Char(string='Longitud', readonly=True)
    gps_sim_checked = fields.Datetime(string='Diag. actualizado', readonly=True)

    # Comandos SMS (solo vehículo / SIM nuestra)
    gps_sms_command = fields.Char(string='Comando SMS')
    gps_sms_encoding = fields.Selection([('GSM-7', 'GSM-7'), ('UCS2', 'UCS2')], default='GSM-7', string='Codif.')
    gps_sms_log = fields.Text(string='Bitácora SMS', readonly=True)

    # ---- Acciones por equipo ----
    def action_register_senticar(self):
        for dev in self:
            dev.subscription_id._senticar_register_device(dev)

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
