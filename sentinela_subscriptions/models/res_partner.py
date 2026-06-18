import secrets
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- SentiCar / Traccar (usuario del cliente en la plataforma propia) ---
    senticar_user_id = fields.Integer(string='ID Usuario SentiCar', copy=False,
        help="Identificador del usuario de este cliente en SentiCar/Traccar. Se crea al dar de alta su primer GPS.")
    senticar_user_email = fields.Char(string='Usuario SentiCar (email)', copy=False)
    senticar_user_password = fields.Char(string='Contraseña SentiCar', copy=False,
        help="Contraseña generada para que el cliente acceda a SentiCar a ver sus equipos.")
    senticar_portal_token = fields.Char(string='Token Portal Transportista', copy=False, index=True,
        help="Token del link personal del transportista para generar links de rastreo de sus unidades.")
    senticar_group_id = fields.Integer(string='ID Grupo SentiCar', copy=False,
        help="Grupo del cliente en SentiCar/Traccar. Sus equipos se meten a este grupo y la "
             "visibilidad se hereda (en vez de ligar equipo por equipo). Se crea al dar de alta su primer GPS.")
    senticar_distributor_id = fields.Many2one('res.partner', string='Distribuidor SentiCar (cuelga de)',
        help="Distribuidor/gestor del que depende este cliente en SentiCar. Si se define, el grupo del "
             "cliente se anida bajo el del distribuidor y el distribuidor ve los equipos del cliente "
             "(automático). Sin distribuidor, cuelga del grupo raíz.")

    @api.constrains('senticar_distributor_id')
    def _check_senticar_distributor_no_cycle(self):
        for p in self:
            d = p.senticar_distributor_id
            seen = {p.id}
            while d:
                if d.id in seen:
                    raise ValidationError(_("El distribuidor SentiCar no puede formar un ciclo (un cliente no puede colgar de sí mismo, directa o indirectamente)."))
                seen.add(d.id)
                d = d.senticar_distributor_id

    def ensure_senticar_portal_token(self):
        for p in self:
            if not p.senticar_portal_token:
                p.senticar_portal_token = secrets.token_urlsafe(16)
        return self.senticar_portal_token

    def rotate_senticar_portal_token(self):
        """Regenera el token del portal del transportista → el enlace anterior deja de servir."""
        for p in self:
            p.senticar_portal_token = secrets.token_urlsafe(16)
        return self.senticar_portal_token

    def revoke_senticar_portal_token(self):
        """Revoca el enlace del portal del transportista (lo deja sin acceso)."""
        for p in self:
            p.senticar_portal_token = False

    def write(self, vals):
        res = super().write(vals)
        # Si cambia el email del cliente y ya tiene usuario en SentiCar, sincronizar el login
        # (si no, el cliente acabaría logueando con un correo viejo). Side-effect externo: no truena.
        if 'email' in vals:
            svc = self.env['sentinela.senticar.service']
            for p in self:
                if p.senticar_user_id and p.email and p.email != p.senticar_user_email:
                    try:
                        if svc.update_user_email(p.senticar_user_id, p.email):
                            p.senticar_user_email = p.email
                            _logger.info("SENTICAR: email del usuario %s sincronizado a %s", p.senticar_user_id, p.email)
                    except Exception as e:
                        _logger.error("SENTICAR update_user_email %s: %s", p.senticar_user_id, e)
        return res

    invoice_grouping_method = fields.Selection([
        ('individual', 'Una factura por servicio detallado'),
        ('by_branch', 'Agrupar por sucursal'),
        ('global', 'Una factura global todo junto')
    ], string='Preferencia de Facturación', default='individual',
    help="Define cómo prefiere el cliente recibir sus facturas de suscripción.")

    invoice_cc_partner_ids = fields.Many2many(
        'res.partner',
        'res_partner_invoice_cc_rel',
        'partner_id', 'contact_id',
        string='Correos adicionales de facturación (CC)',
        help="Contactos que reciben COPIA (CC) de TODAS las facturas/remisiones de este "
             "cliente, sin importar la agrupación. Ideal para facturación global o por "
             "sucursal: se configura UNA sola vez aquí en vez de en cada suscripción. "
             "Se combina con los CC definidos a nivel de cada suscripción. Solo se usan "
             "los contactos que tengan correo cargado.")

    # --- Condiciones de Venta para Facturación Automática ---
    invoice_payment_condition = fields.Selection([
        ('contado', 'Contado'),
        ('credito', 'Crédito'),
        ('otro', 'Otro')
    ], string='Condición de Pago', default='contado')
    invoice_payment_condition_text = fields.Char(string='Especifique Condición')

    invoice_payment_form = fields.Selection([
        ('01', '01 - Efectivo'),
        ('02', '02 - Cheque nominativo'),
        ('03', '03 - Transferencia electrónica de fondos'),
        ('04', '04 - Tarjeta de crédito'),
        ('05', '05 - Monedero electrónico'),
        ('06', '06 - Dinero electrónico'),
        ('08', '08 - Vales de despensa'),
        ('12', '12 - Dación en pago'),
        ('13', '13 - Pago por subrogación'),
        ('14', '14 - Pago por consignación'),
        ('15', '15 - Condonación'),
        ('17', '17 - Compensación'),
        ('23', '23 - Novación'),
        ('24', '24 - Confusión'),
        ('25', '25 - Remisión de deuda'),
        ('26', '26 - Prescripción o caducidad'),
        ('27', '27 - A satisfacción del acreedor'),
        ('28', '28 - Tarjeta de débito'),
        ('29', '29 - Tarjeta de servicios'),
        ('30', '30 - Aplicación de anticipos'),
        ('31', '31 - Intermediario pagos'),
        ('99', '99 - Por definir')
    ], string='Forma de Pago', default='99')

    invoice_bank_account = fields.Char(string='Número de Cuenta (4 dígitos)', size=4)
    
    invoice_payment_method = fields.Selection([
        ('PUE', 'PUE - Pago en una sola exhibición'),
        ('PPD', 'PPD - Pago en parcialidades o diferido')
    ], string='Método de Pago', default='PUE')

    invoice_zip = fields.Char(string='Lugar de Expedición', default='87350')

    # --- Facturación CFDI vs Remisión ---
    requiere_factura = fields.Boolean(
        string='Requiere Factura CFDI',
        default=False,
        help="Activar si el cliente requiere comprobante fiscal timbrado (CFDI). "
             "Si no está activado, se emite remisión (documento interno sin timbre SAT). "
             "Ambos documentos aplican para cobranza y generan saldo pendiente."
    )

    subscription_count = fields.Integer(compute='_compute_subscription_count', string='# Subscriptions')
    
    def _compute_subscription_count(self):
        for partner in self:
            partner.subscription_count = self.env['sentinela.subscription'].search_count([('partner_id', '=', partner.id)])

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscriptions',
            'view_mode': 'kanban,list,form',
            'res_model': 'sentinela.subscription',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    @api.depends('name', 'parent_id.name')
    def _compute_display_name(self):
        if self._context.get('show_only_name'):
            for partner in self:
                partner.display_name = partner.name
        else:
            super()._compute_display_name()
