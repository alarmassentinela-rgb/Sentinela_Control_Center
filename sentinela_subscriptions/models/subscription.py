from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
import calendar
import base64
import logging

_logger = logging.getLogger(__name__)

class SentinelaSubscription(models.Model):
    _name = 'sentinela.subscription'
    _description = 'Subscription Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_billing_date asc, name desc'

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, tracking=True)
    # Nota v18.0.1.3.0: el string label se sobreescribe en la vista PRO para usar
    # "Fecha de Alta del Servicio" / "Próxima Renovación" / "Días de Crédito" / "Frecuencia de Cobro"

    service_address_id = fields.Many2one('res.partner', string='Dirección de Servicio',
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]",
        help="Ubicación física donde se presta el servicio.")

    # --- Dirección (solo lectura) ---
    address_street = fields.Char(related='service_address_id.street', string='Calle', readonly=True)
    address_street2 = fields.Char(related='service_address_id.street2', string='Colonia', readonly=True)
    address_city = fields.Char(related='service_address_id.city', string='Ciudad', readonly=True)
    address_state_id = fields.Many2one(related='service_address_id.state_id', string='Estado', readonly=True)
    address_zip = fields.Char(related='service_address_id.zip', string='C.P.', readonly=True)

    # --- Detalles del Servicio ---
    product_id = fields.Many2one('product.template', string='Plan de Servicio', required=True, domain="[('is_subscription', '=', True)]")
    price_unit = fields.Float(string='Tarifa Mensual (Sin IVA)', required=True, tracking=True)
    price_total = fields.Float(string='Total Mensual (Neto)', compute='_compute_price_total', store=True)
    
    @api.depends('price_unit', 'product_id')
    def _compute_price_total(self):
        for sub in self:
            sub.price_total = sub.price_unit * 1.16 # IVA 16% Hardcoded for now based on previous logic

    service_type = fields.Selection([
        ('internet', 'Internet WISP'),
        ('alarm', 'Monitoreo de Alarmas'),
        ('gps', 'GPS / Rastreo'),
        ('maintenance', 'Mantenimiento / Póliza')
    ], string='Tipo de Servicio', required=True)

    ip_address = fields.Char(string='Dirección IP')

    # --- Ciclo de Facturación ---
    start_date = fields.Date(string='Fecha de Inicio', default=fields.Date.today, required=True)
    next_billing_date = fields.Date(string='Próximo Cobro', required=True, tracking=True)
    recurring_interval = fields.Selection([
        ('1', 'Mensual'),
        ('2', 'Bimestral'),
        ('3', 'Trimestral'),
        ('6', 'Semestral'),
        ('12', 'Anual')
    ], string='Ciclo de Facturación', default='1', required=True)

    # --- Contrato y Equipo ---
    is_forced_contract = fields.Boolean(string='¿Plazo Forzoso?', default=False)
    commitment_period = fields.Integer(string='Plazo (Meses)', default=12)
    commitment_end_date = fields.Date(string='Fin de Plazo', compute='_compute_commitment_end', store=True)
    # DEPRECATED v18.0.1.3.0 — duplicado de early_termination_fee. Quedarse con early_termination_fee.
    penalty_amount = fields.Float(string='Penalización Anticipada (legacy)')
    
    equipment_ownership = fields.Selection([
        ('company', 'Propiedad de la Empresa (Comodato)'),
        ('customer', 'Propiedad del Cliente'),
        ('leasing', 'Arrendamiento (Renta con opción a compra)')
    ], string='Propiedad del Equipo', default='company')
    
    plan_after_leasing_id = fields.Many2one('product.template', string='Plan al terminar renta', 
        domain="[('is_subscription', '=', True)]")

    is_contract_locked = fields.Boolean(string='Contrato Sellado', default=False, tracking=True)
    # DEPRECATED v18.0.1.3.0 — redundante con recurring_interval. Mantenido para compatibilidad
    # con plantillas de contrato que lo referencian. NO editar desde UI.
    contract_mode = fields.Selection([
        ('monthly', 'Mensual'),
        ('annual', 'Anual'),
        ('biannual', 'Semestral'),
        ('custom', 'Personalizado'),
    ], string='Modalidad de Contrato (legacy)', default='monthly')
    early_termination_fee = fields.Monetary(string='Penalización por Cancelar Antes de Plazo', currency_field='currency_id')
    contract_signed = fields.Boolean(string='Contrato Firmado', default=False, tracking=True)
    contract_date = fields.Date(string='Fecha del Contrato', tracking=True,
        help='Fecha de celebración del contrato. Se llena automáticamente al generar el contrato por primera vez.')
    contract_date_human = fields.Char(string='Fecha del Contrato (texto)', compute='_compute_contract_date_human')

    @api.depends('contract_date')
    def _compute_contract_date_human(self):
        meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                 'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
        for rec in self:
            if rec.contract_date:
                rec.contract_date_human = f'{rec.contract_date.day} de {meses[rec.contract_date.month-1]} de {rec.contract_date.year}'
            else:
                rec.contract_date_human = '—'
    contract_body_html = fields.Html(string='Contrato (HTML)', compute='_compute_contract_body_html',
                                     store=False, sanitize=False, sanitize_attributes=False, sanitize_style=False)
    # DEPRECATED v18.0.1.3.0 — duplicado de commitment_period. Eliminado de la vista.
    # commitment_months = fields.Integer(related='commitment_period', string='Plazo (meses)', readonly=True)
    # DEPRECATED v18.0.1.3.0 — decorativo, no respetaba lógica. Eliminado de la vista.
    # Mantenido en modelo para compatibilidad con plantillas (referencia {{ object.payment_day }}).
    payment_day = fields.Integer(string='Día de Pago (legacy)', default=5)

    edit_plan_locked = fields.Boolean(string='Plan Bloqueado', default=True)
    edit_pppoe_locked = fields.Boolean(string='PPPoE Bloqueado', default=True)
    pppoe_user_locked = fields.Boolean(string='Usuario PPPoE Bloqueado', default=True)
    pppoe_password_locked = fields.Boolean(string='Contraseña PPPoE Bloqueada', default=True)

    serial_number_id = fields.Many2one('stock.lot', string='Serie del Equipo', domain="[('product_id', '=', product_id)]")

    # --- Estado ---
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending_signature', 'Pendiente de Firma'),
        ('confirmed', 'Confirmado'),
        ('active', 'Activo'),
        ('suspension', 'En Suspensión'),
        ('closed', 'Cerrado'),
        ('cancelled', 'Cancelado')
    ], string='Estado del Contrato', default='draft', tracking=True)

    technical_state = fields.Selection([
        ('active', 'Activo / En Línea'),
        ('suspended', 'Suspendido (Falta de Pago)'),
        ('cut', 'Corte Definitivo / Retirado')
    ], string='Estado Técnico', default='active', tracking=True)

    technical_state_date = fields.Datetime(string='Estado Técnico Desde', default=fields.Datetime.now, readonly=True)
    days_suspended = fields.Integer(
        string='Días en Suspensión',
        compute='_compute_days_suspended',
        search='_search_days_suspended',
        help='Días que lleva la suscripción en estado Suspensión, contados desde la fecha del último cambio de estado técnico.',
    )

    @api.depends('state', 'technical_state_date')
    def _compute_days_suspended(self):
        today = fields.Date.today()
        for sub in self:
            if sub.state == 'suspension' and sub.technical_state_date:
                sub.days_suspended = (today - sub.technical_state_date.date()).days
            else:
                sub.days_suspended = 0

    def _search_days_suspended(self, operator, value):
        """Permite filtrar por días en suspensión usando dominios SQL sobre technical_state_date."""
        if operator not in ('=', '!=', '>', '>=', '<', '<='):
            return []
        today = fields.Date.today()
        cutoff_date = today - timedelta(days=int(value))
        # 'days_suspended > 30' ↔ 'technical_state_date < hoy - 30 días'
        op_map = {'>': '<', '>=': '<=', '<': '>', '<=': '>=', '=': '=', '!=': '!='}
        return [('state', '=', 'suspension'), ('technical_state_date', op_map[operator], cutoff_date)]

    description = fields.Html(string='Notas Internas')

    # --- Ubicación Técnica ---
    location_notes = fields.Text(string='Referencias de Ubicación')
    latitude = fields.Char(string='Latitud')
    longitude = fields.Char(string='Longitud')
    def action_open_map(self):
        """Abre Google Maps en una nueva pestaña centrado en las coordenadas."""
        self.ensure_one()
        if not self.latitude or not self.longitude:
            raise UserError(_('No hay coordenadas guardadas. Usa "Obtener Coordenadas" primero.'))
        return {
            'type': 'ir.actions.act_url',
            'url': f'https://www.google.com/maps?q={self.latitude},{self.longitude}&z=17',
            'target': 'new',
        }

    def action_geocode_address(self):
        """Geocodifica la dirección del servicio usando base_geolocalize.
        Estrategia de fallback en cascada:
          1. Dirección completa (street + street2 + zip + ciudad + estado)
          2. Calle limpia (sin "#NNN ENTRE X y Y") + zip + ciudad + estado
          3. Solo zip + ciudad + estado (precisión a nivel CP)
        """
        self.ensure_one()
        import re
        Geocoder = self.env['base.geocoder']
        state_name = self.address_state_id.name if self.address_state_id else None
        if not (self.address_street or self.address_zip or self.address_city):
            raise UserError(_('Se requiere al menos calle/CP/ciudad en la dirección del servicio antes de geocodificar.'))

        def try_query(parts, precision_label):
            q = ', '.join(filter(None, parts))
            if not q:
                return None, None
            try:
                r = Geocoder.geo_find(q)
            except Exception:
                r = None
            return (r, precision_label) if r else (None, None)

        # Intento 1 — dirección completa
        result, precision = try_query(
            [self.address_street, self.address_street2, self.address_zip,
             self.address_city, state_name, 'México'],
            'exacta')

        # Intento 2 — limpiar números/anotaciones de la calle
        if not result and self.address_street:
            clean = re.sub(r'#\s*\d+\S*|ENTRE\s+\S+\s+y\s+\S+|N[oº]\s*\d+', '',
                           self.address_street, flags=re.IGNORECASE).strip(' ,')
            if clean and clean.lower() != self.address_street.lower():
                result, precision = try_query(
                    [clean, self.address_zip, self.address_city, state_name, 'México'],
                    'media (sin número)')

        # Intento 3 — solo CP + ciudad + estado
        if not result:
            result, precision = try_query(
                [self.address_zip, self.address_city, state_name, 'México'],
                'aproximada (código postal)')

        if not result:
            raise UserError(_(
                'No se encontraron coordenadas para esta dirección.\n'
                'Verifica que el CP, ciudad y estado estén correctos, o ingresa las coordenadas manualmente.'
            ))
        lat, lng = result[0], result[1]
        self.write({'latitude': str(lat), 'longitude': str(lng)})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Coordenadas obtenidas (precisión: %s)') % precision,
                'message': _('Lat: %.6f, Lng: %.6f\nAjusta manualmente si no es exacto.') % (lat, lng),
                'type': 'success' if precision == 'exacta' else 'warning',
                'sticky': False,
            }
        }
    
    # --- Extensions ---
    extension_due_date = fields.Date(string='Vencimiento de Prórroga', tracking=True)

    # --- Contract Body ---
    contract_template_id = fields.Many2one('sentinela.contract.template', string='Plantilla de Contrato',
        related='product_id.contract_template_id', readonly=True)
    contract_body = fields.Html(string='Contenido del Contrato')

    # --- Technical identifiers ---
    monitoring_account_number = fields.Char(string='Número de Cuenta')
    security_code = fields.Char(string='Clave de Seguridad (Voz)')
    master_password = fields.Char(string='Clave Maestra (Panel)')
    gps_imei = fields.Char(string='IMEI del Equipo')
    sim_iccid = fields.Char(string='ICCID de la SIM')
    # gps_platform_id = fields.Char(string='ID en Plataforma')
    equipment_brand = fields.Char(string='Marca')
    equipment_model = fields.Char(string='Modelo')
    equipment_serial = fields.Char(string='Número de Serie (Manual)')

    # --- Vehículo (GPS / SentiCar) ---
    vehicle_brand = fields.Char(string='Marca Vehículo')
    vehicle_model = fields.Char(string='Modelo Vehículo')
    vehicle_year = fields.Integer(string='Año Vehículo')
    vehicle_color = fields.Char(string='Color Vehículo')
    vehicle_plate = fields.Char(string='Placa')
    vehicle_vin = fields.Char(string='VIN / NIV')

    # --- Internet WISP — Antena CPE exterior (Ubiquiti/MikroTik) ---
    antenna_product_id = fields.Many2one('product.template', string='Antena (catálogo)',
        domain="[('syscom_brand','in',['UBIQUITI','MIKROTIK'])]",
        help="Selecciona la antena del catálogo (Ubiquiti/MikroTik). Marca y modelo se llenan solos. Si es de otra marca no catalogada, déjalo vacío y captura manual.")
    antenna_brand = fields.Char(string='Marca Antena')
    antenna_model = fields.Char(string='Modelo Antena')
    antenna_serial = fields.Char(string='Número de Serie Antena')
    # Router/Módem WiFi interior (cualquier marca: TP-Link, Hikvision, etc.)
    router_product_id = fields.Many2one('product.template', string='Router/Módem (catálogo)',
        help="Selecciona el router/módem del catálogo (cualquier marca). Marca y modelo se llenan solos. Si no está catalogado, déjalo vacío y captura manual.")
    # Panel de tráfico en vivo (embebido, se llena con el botón Actualizar Tráfico)
    live_traffic_status = fields.Char(string='Estado', readonly=True)
    live_traffic_ip = fields.Char(string='IP en línea', readonly=True)
    live_traffic_rx = fields.Char(string='⬇ Bajada (RX)', readonly=True)
    live_traffic_tx = fields.Char(string='⬆ Subida (TX)', readonly=True)
    live_traffic_updated = fields.Datetime(string='Última lectura', readonly=True)
    live_traffic_graph = fields.Char(string='Gráfica', readonly=True)  # dummy para el widget OWL
    # Señal de la antena CPE (airOS, vía SSH mca-status)
    antenna_signal_dbm = fields.Char(string='Señal', readonly=True)
    antenna_snr = fields.Char(string='SNR', readonly=True)
    antenna_signal_quality = fields.Char(string='Calidad de Señal', readonly=True)
    antenna_link_rate = fields.Char(string='Enlace TX/RX', readonly=True)
    antenna_distance = fields.Char(string='Distancia', readonly=True)
    antenna_signal_updated = fields.Datetime(string='Señal actualizada', readonly=True)

    # --- Internet WISP (PPPoE & Router) ---
    router_id = fields.Many2one('sentinela.router', string='Mikrotik Router')
    internet_mgmt_mode = fields.Selection([
        ('pppoe', 'PPPoE'),
        ('static', 'IP Estática'),
        ('dhcp', 'DHCP'),
    ], string='Modo de Conexión', default='pppoe')
    pppoe_user = fields.Char(string='PPPoE User')
    pppoe_password = fields.Char(string='PPPoE Password')
    pppoe_pass = fields.Char(string='PPPoE Password (Legacy)')
    pppoe_server_name = fields.Char(related='router_id.pppoe_server_name', string='Servidor PPPoE', readonly=True)
    gateway_address = fields.Char(string='Gateway')
    subnet_mask = fields.Char(string='Máscara de Subred')
    vlan_id = fields.Char(string='VLAN ID')
    mikrotik_profile_id = fields.Many2one('sentinela.mikrotik.profile', string='Perfil MikroTik',
        compute='_compute_mikrotik_profile_id', store=True, readonly=False,
        help="Se hereda automáticamente del perfil del plan. Si el plan no tiene perfil, se puede elegir manualmente.")
    product_mikrotik_profile_id = fields.Many2one(
        'sentinela.mikrotik.profile',
        related='product_id.mikrotik_profile_id',
        string='Perfil del Plan',
        readonly=True,
    )
    modem_user = fields.Char(string='Usuario Módem')
    modem_password = fields.Char(string='Contraseña Módem')

    # --- Campos computados para plantillas de contrato ---
    contract_antena_marca = fields.Char(
        string='Marca Antena (Contrato)', compute='_compute_contract_fields', store=False)
    contract_antena_modelo = fields.Char(
        string='Modelo Antena (Contrato)', compute='_compute_contract_fields', store=False)
    contract_router_nombre = fields.Char(
        string='Router Nombre (Contrato)', compute='_compute_contract_fields', store=False)
    contract_router_ip = fields.Char(
        string='Router IP (Contrato)', compute='_compute_contract_fields', store=False)
    contract_pppoe_servidor = fields.Char(
        string='Servidor PPPoE (Contrato)', compute='_compute_contract_fields', store=False)
    contract_domicilio_servicio = fields.Char(
        string='Domicilio de Servicio (Contrato)', compute='_compute_contract_fields', store=False)
    contract_cuenta_monitoreo = fields.Char(
        string='Cuenta Monitoreo (Contrato)', compute='_compute_contract_fields', store=False)

    @api.depends('antenna_brand', 'antenna_model', 'router_id', 'router_id.ip_address',
                 'router_id.pppoe_server_name', 'service_address_id', 'address_street',
                 'address_street2', 'address_city', 'address_zip', 'monitoring_account_number')
    def _compute_contract_fields(self):
        for rec in self:
            rec.contract_antena_marca = rec.antenna_brand or ''
            rec.contract_antena_modelo = rec.antenna_model or ''
            rec.contract_router_nombre = rec.router_id.name if rec.router_id else ''
            rec.contract_router_ip = rec.router_id.ip_address if rec.router_id else ''
            rec.contract_pppoe_servidor = rec.router_id.pppoe_server_name if rec.router_id else ''
            parts = filter(None, [
                rec.address_street,
                rec.address_street2,
                rec.address_city,
                rec.address_state_id.name if rec.address_state_id else '',
                rec.address_zip,
            ])
            rec.contract_domicilio_servicio = ', '.join(parts)
            rec.contract_cuenta_monitoreo = rec.monitoring_account_number or ''

    @api.depends('contract_body')
    def _compute_contract_body_html(self):
        """Renderiza el cuerpo del contrato con estilo de documento + logo de la compañía."""
        company = self.env.company
        logo_url = f'/web/image/res.company/{company.id}/logo'
        company_name = company.name or 'Sentinela'
        company_vat = company.vat or ''
        css = (
            '<style>'
            '.sentinela-contract { background:#fff; max-width:850px; margin:0 auto; '
            'padding:40px 60px; font-family: Georgia, "Times New Roman", serif; '
            'color:#222; line-height:1.55; box-shadow:0 0 8px rgba(0,0,0,0.08); '
            'border:1px solid #ddd; }'
            '.sentinela-contract .sc-header { border-bottom:2px solid #1f4e79; '
            'padding-bottom:10px; margin-bottom:25px; }'
            '.sentinela-contract .sc-header h2 { margin:6px 0 2px 0; color:#1f4e79; font-size:18px; }'
            '.sentinela-contract .sc-header small { color:#666; font-size:12px; }'
            '.sentinela-contract h1, .sentinela-contract h2, .sentinela-contract h3 { color:#1f4e79; }'
            '.sentinela-contract p { text-align:justify; margin: 0.6em 0; }'
            '.sentinela-contract .sc-empty { padding:30px; background:#f8f8f8; '
            'border:1px dashed #ccc; text-align:center; color:#888; font-style:italic; }'
            '</style>'
        )
        # Construir header con folio + fecha a la derecha
        # se completa por suscripción dentro del for de abajo
        header_template = (
            '<div class="sc-header" style="display:flex; justify-content:space-between; align-items:center;">'
            '<div>'
            f'<img src="{logo_url}" alt="{company_name}" '
            'style="height:50px; width:auto; max-width:180px; vertical-align:middle; margin-right:14px;"/>'
            '<span style="font-size:18px; color:#1f4e79; font-weight:bold; vertical-align:middle;">CONTRATO DE SERVICIO</span>'
            '</div>'
            '<div style="text-align:right; font-size:12px; color:#444;">'
            'Folio: <b>{folio}</b><br/>'
            'Fecha: <b>{fecha}</b>'
            '</div>'
            '</div>'
        )
        for rec in self:
            header_html = header_template.format(folio=rec.name or '—', fecha=rec.contract_date_human)
            if rec.contract_body and rec.contract_body.strip():
                body = rec.contract_body
            else:
                body = (
                    '<div class="sc-empty">Aún no se ha redactado el contrato. '
                    'Usa el botón <b>"Redactar / Actualizar Contrato"</b> arriba para generarlo a partir de la plantilla.</div>'
                )
            rec.contract_body_html = (
                f'{css}<div class="sentinela-contract">{header_html}{body}</div>'
            )

    # --- Financials ---
    invoice_ids = fields.One2many('account.move', 'subscription_id', string='Invoices')
    sale_order_ids = fields.One2many('sale.order', 'subscription_id', string='Cotizaciones')
    service_inclusion_ids = fields.One2many('sentinela.subscription.service.inclusion', 'subscription_id', string='Servicios Incluidos')
    invoice_count = fields.Integer(default=0)
    
    # --- Digital Signature Integration ---
    sign_document_id = fields.Many2one('sentinela.sign.document', string='Documento de Firma', readonly=True)
    sign_state = fields.Selection(related='sign_document_id.state', string='Estado de Firma', readonly=True)
    contract_status_label = fields.Char(string='Estado del Contrato', compute='_compute_contract_status_label')

    @api.depends('contract_body', 'sign_document_id', 'sign_state', 'contract_signed')
    def _compute_contract_status_label(self):
        for rec in self:
            if rec.contract_signed and (not rec.sign_state or rec.sign_state != 'signed'):
                rec.contract_status_label = '📝 Firmado en papel'
            elif rec.sign_state == 'signed':
                rec.contract_status_label = '✅ Firmado digitalmente'
            elif rec.sign_state == 'sent':
                rec.contract_status_label = '📤 Enviado al cliente, esperando firma'
            elif rec.sign_state == 'cancel':
                rec.contract_status_label = '⛔ Solicitud de firma cancelada'
            elif rec.contract_body and rec.contract_body.strip():
                rec.contract_status_label = '🟡 Redactado, pendiente enviar'
            else:
                rec.contract_status_label = '🔴 Sin contrato redactado'

    def action_print_contract(self):
        """Descarga el contrato como PDF usando el report Qweb."""
        self.ensure_one()
        if not self.contract_body or not self.contract_body.strip():
            raise UserError(_('Redacta el contrato primero (botón "Redactar Contrato").'))
        return self.env.ref('sentinela_subscriptions.action_report_subscription_contract').report_action(self)

    def action_send_contract_for_signature(self):
        """Genera (si no existe) el sign_document y lo envía por email al cliente."""
        self.ensure_one()
        if not self.contract_body or not self.contract_body.strip():
            raise UserError(_('Redacta el contrato primero (botón "Redactar Contrato" en la cabecera).'))
        if not self.partner_id.email:
            raise UserError(_('El cliente %s no tiene email configurado. Agrega un email en su ficha.') % self.partner_id.name)
        # Crear sign_document si no existe (o si está cancelado/firmado anterior, crear uno nuevo)
        if not self.sign_document_id or self.sign_document_id.state in ('signed', 'cancel'):
            sign_doc = self.env['sentinela.sign.document'].create({
                'partner_id': self.partner_id.id,
                'res_model': self._name,
                'res_id': self.id,
                'filename': f"Contrato_{self.name}.pdf",
                'file': base64.b64encode((self.contract_body or '').encode('utf-8')),
            })
            self.sign_document_id = sign_doc.id
        # Enviar email (cambia estado a 'sent')
        self.sign_document_id.action_send_email()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Contrato enviado'),
                'message': _('Se envió el contrato a %s (%s) para firma electrónica.') % (
                    self.partner_id.name, self.partner_id.email),
                'type': 'success',
                'sticky': False,
            }
        }

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    payment_term_id = fields.Many2one('account.payment.term', string='Plazos de Pago')
    auto_invoice = fields.Boolean(string='Generar Factura (No Remisión)', default=False)
    auto_send_mail = fields.Boolean(string='Enviar automáticamente por Correo', default=False)
    days_to_suspend = fields.Integer(
        string='Días para Auto-Suspensión',
        default=5,
        help='Días después del vencimiento de una factura tras los cuales el sistema suspende automáticamente el servicio. Default: 5 días. Editable por suscripción para casos especiales (VIPs, clientes morosos crónicos, etc).'
    )

    # --- Methods ---
    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facturas',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_move_type': 'out_invoice', 'default_subscription_id': self.id}
        }

    def action_view_fsm_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes Técnicas (FSM)',
            'res_model': 'sentinela.fsm.order',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id, 'default_partner_id': self.partner_id.id}
        }

    def action_request_signature(self):
        self.ensure_one()
        if not self.contract_body:
            raise UserError("Debe redactar el contrato antes de solicitar la firma.")
        
        # 1. Generar PDF (Usando el reporte base de Odoo para el contrato si existe, o HTML a PDF básico)
        # Por ahora crearemos el registro de firma con el contenido redactado
        # Para pruebas de laboratorio, creamos el documento de firma:
        sign_vals = {
            'partner_id': self.partner_id.id,
            'res_model': self._name,
            'res_id': self.id,
            'filename': f"Contrato_{self.name}.pdf",
            'file': base64.b64encode(self.contract_body.encode('utf-8')) # Dummy PDF, en Odoo real usaríamos ir.actions.report
        }
        
        sign_doc = self.env['sentinela.sign.document'].create(sign_vals)
        self.sign_document_id = sign_doc.id
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sentinela.sign.document',
            'res_id': sign_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_sign_document(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sentinela.sign.document',
            'res_id': self.sign_document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def toggle_plan_lock(self):
        for rec in self:
            rec.edit_plan_locked = not rec.edit_plan_locked

    def toggle_pppoe_lock(self):
        for rec in self:
            rec.edit_pppoe_locked = not rec.edit_pppoe_locked

    def toggle_pppoe_user_lock(self):
        for rec in self:
            rec.pppoe_user_locked = not rec.pppoe_user_locked

    def toggle_pppoe_password_lock(self):
        for rec in self:
            rec.pppoe_password_locked = not rec.pppoe_password_locked

    def action_alta_router_pppoe(self):
        """Cliente NUEVO: asigna el siguiente ctaNNNN libre del router y crea su secret PPPoE.
        Acción explícita del usuario — ignora sync_active. Si el usuario ya existe, NO lo
        sobreescribe (protege a Argus): lanza error."""
        self.ensure_one()
        if self.service_type != 'internet' or self.internet_mgmt_mode != 'pppoe':
            raise UserError(_('Esta acción es solo para suscripciones de Internet por PPPoE.'))
        if not self.router_id:
            raise UserError(_('Asigna primero el Router MikroTik.'))
        if not self.mikrotik_profile_id:
            raise UserError(_('Asigna primero el Perfil MikroTik (se hereda del plan).'))
        import routeros_api, re
        conn = routeros_api.RouterOsApiPool(
            self.router_id.ip_address, username=self.router_id.api_user,
            password=self.router_id.api_password or '', port=self.router_id.api_port,
            plaintext_login=True)
        try:
            api = conn.get_api()
            secrets = api.get_resource('/ppp/secret')
            all_secrets = secrets.get()
            # Si no tiene usuario asignado, calcular el siguiente ctaNNNN libre
            if not self.pppoe_user:
                nums = [int(m.group(1)) for s in all_secrets
                        for m in [re.match(r'cta(\d+)$', s.get('name', '') or '')] if m]
                nxt = (max(nums) + 1) if nums else 1
                self.pppoe_user = 'cta%04d' % nxt
            # Protección: no sobreescribir un secret existente (p.ej. de Argus)
            if any(s.get('name') == self.pppoe_user for s in all_secrets):
                raise UserError(_('El usuario %s ya existe en el router. No se sobreescribe. '
                                  'Revisa o deja el campo vacío para asignar uno nuevo.') % self.pppoe_user)
            # Password por defecto patrón Argus (.ctaNNNN.) si el usuario no capturó uno
            if not self.pppoe_password:
                self.pppoe_password = '.%s.' % self.pppoe_user
            secrets.add(
                name=self.pppoe_user, password=self.pppoe_password, service='pppoe',
                profile=self.mikrotik_profile_id.name, comment='Odoo SUB/%s' % self.name)
            conn.disconnect()
        except UserError:
            try: conn.disconnect()
            except Exception: pass
            raise
        except Exception as e:
            try: conn.disconnect()
            except Exception: pass
            raise UserError(_('Error al dar de alta en el router: %s') % e)
        self.message_post(body=_('✅ <b>Alta en router:</b> secret PPPoE <b>%s</b> creado con perfil <b>%s</b>. El CPE ya puede autenticar.') % (self.pppoe_user, self.mikrotik_profile_id.name))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Alta en router exitosa'),
                           'message': _('Usuario %s creado en el MikroTik.') % self.pppoe_user,
                           'type': 'success', 'sticky': False}}

    # --- Billing Automation ---
    def _cron_generate_pre_invoices(self):
        """ Genera FACTURAS (account.move) para las suscripciones cuyo cobro vence hoy o antes.
        La factura publicada genera el saldo por cobrar; sirve como "remisión" (sin timbrar) o
        como factura fiscal (cuando se implemente el timbrado CFDI real). Sin anticipo: se genera
        el día exacto de next_billing_date (<= hoy también recupera atrasadas).

        Agrupación según preferencia del cliente (res.partner.invoice_grouping_method):
        - individual: 1 factura por suscripción.
        - by_branch: 1 factura por (cliente, dirección de servicio). Cuando la primera sub del
          grupo vence en el mes, jala todas las del mismo grupo cuya next_billing_date caiga
          dentro del MISMO MES CALENDARIO (de hoy hasta fin de mes). Las del mes siguiente
          esperan a su propio mes.
        - global: igual que by_branch, pero el grupo es solo (cliente,*).
        El avance de next_billing_date evita duplicados (cada sub mantiene su ciclo natural). """
        today = fields.Date.today()
        subs_due = self.search([
            ('state', '=', 'active'),
            ('next_billing_date', '<=', today),
        ])
        if not subs_due:
            return

        end_of_month = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        grouped_subs = {}
        for sub in subs_due:
            method = sub.partner_id.invoice_grouping_method or 'individual'
            if method == 'global':
                key = (sub.partner_id.id, 'global')
            elif method == 'by_branch':
                addr_id = sub.service_address_id.id if sub.service_address_id else False
                key = (sub.partner_id.id, addr_id)
            else:
                key = (sub.partner_id.id, sub.id)
            if key in grouped_subs:
                continue  # Grupo ya expandido por otra sub vencida del mismo grupo
            if method == 'global':
                group = self.search([
                    ('state', '=', 'active'),
                    ('partner_id', '=', sub.partner_id.id),
                    ('next_billing_date', '<=', end_of_month),
                ])
            elif method == 'by_branch':
                group = self.search([
                    ('state', '=', 'active'),
                    ('partner_id', '=', sub.partner_id.id),
                    ('service_address_id', '=', sub.service_address_id.id if sub.service_address_id else False),
                    ('next_billing_date', '<=', end_of_month),
                ])
            else:
                group = sub
            grouped_subs[key] = group

        for key, group in grouped_subs.items():
            try:
                self._billing_generate_invoice(group)
            except Exception as e:
                _logger.error(f"BILLING: Falló la generación para grupo {key}: {str(e)}")

    def _billing_generate_invoice(self, subs_list):
        """ Crea y publica UNA factura (account.move) para el grupo de suscripciones dado,
        envía por correo si alguna tiene auto_send_mail, y avanza su next_billing_date al
        siguiente ciclo. El impuesto sale del producto (16%) y la posición fiscal del cliente
        lo ajusta (8% frontera). El timbrado CFDI queda pendiente del módulo Prodigia real:
        las marcadas con auto_invoice quedan publicadas listas para timbrar.

        Asocia la factura a TODAS las subs del grupo vía M2M (`subscription_ids`), y además
        mantiene el Many2one `subscription_id` cuando solo hay una (compatibilidad con vistas
        y One2many.invoice_ids existentes). Para modo by_branch, fija `partner_shipping_id`
        a la dirección de servicio para que la factura muestre la sucursal correspondiente. """
        Move = self.env['account.move']
        partner = subs_list[0].partner_id
        first_sub = subs_list[0]
        method = partner.invoice_grouping_method or 'individual'
        line_cmds = []
        for sub in subs_list:
            period_end = sub.next_billing_date + relativedelta(months=int(sub.recurring_interval)) - timedelta(days=1)
            desc = f"Servicio: {sub.product_id.name} - Contrato: {sub.name} - Periodo: {sub.next_billing_date} al {period_end}"
            line_cmds.append((0, 0, {
                'product_id': sub.product_id.id,
                'name': desc,
                'quantity': 1,
                'price_unit': sub.price_unit,
            }))
        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'fiscal_position_id': partner.property_account_position_id.id or False,
            'invoice_payment_term_id': first_sub.payment_term_id.id or False,
            'invoice_origin': f"Renovación: {', '.join(s.name for s in subs_list)}",
            'subscription_id': first_sub.id if len(subs_list) == 1 else False,
            'subscription_ids': [(6, 0, subs_list.ids)],
            'invoice_line_ids': line_cmds,
        }
        if method == 'by_branch' and first_sub.service_address_id:
            move_vals['partner_shipping_id'] = first_sub.service_address_id.id
        move = Move.create(move_vals)
        move.action_post()  # genera el saldo por cobrar

        if any(s.auto_send_mail for s in subs_list) and partner.email:
            template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
            if template:
                template.send_mail(move.id, force_send=True)

        for sub in subs_list:
            sub.next_billing_date = sub.next_billing_date + relativedelta(months=int(sub.recurring_interval))

        stamp_note = " (marcada para timbrar CFDI)" if any(s.auto_invoice for s in subs_list) else ""
        _logger.info(f"BILLING: Factura {move.name} publicada para {len(subs_list)} suscripción(es){stamp_note}")
        return move

    # --- Extensions & Suspensions ---
    def apply_extension(self, days, reason):
        self.ensure_one()
        new_date = fields.Date.today() + timedelta(days=days)
        self.write({
            'extension_due_date': new_date,
            'technical_state': 'active' if self.technical_state == 'suspended' else self.technical_state
        })
        self.message_post(body=f"✅ <b>Prórroga Otorgada:</b> Vence el {new_date}.<br/>Motivo: {reason}")
        if self.technical_state == 'active':
            self.action_provision_mikrotik_enable()

    def _cron_check_expired_extensions(self):
        """ Suspends service if extension expired and no payment recorded """
        today = fields.Date.today()
        expired_subs = self.search([
            ('extension_due_date', '<', today),
            ('technical_state', '!=', 'suspended'),
            ('state', '=', 'active')
        ])
        for sub in expired_subs:
            sub.message_post(body="⚠️ <b>Prórroga Vencida:</b> Suspendiendo servicio automáticamente.")
            sub.action_suspend()
            sub.extension_due_date = False

    def _cron_auto_suspend_overdue(self):
        """ Suspende automáticamente suscripciones con facturas vencidas más allá
        de su umbral configurado (days_to_suspend, default 5 días). """
        today = fields.Date.today()
        active_subs = self.search([('state', '=', 'active')])
        suspended_count = 0
        tpl_suspended = self.env.ref(
            'sentinela_subscriptions.mail_template_subscription_suspended',
            raise_if_not_found=False,
        )
        for sub in active_subs:
            if sub.extension_due_date and sub.extension_due_date >= today:
                continue
            days_threshold = sub.days_to_suspend or 5
            cutoff = today - timedelta(days=days_threshold)
            overdue_invoices = sub.invoice_ids.filtered(
                lambda i: i.move_type == 'out_invoice'
                and i.state == 'posted'
                and i.payment_state in ('not_paid', 'partial')
                and i.invoice_date_due
                and i.invoice_date_due <= cutoff
            )
            if overdue_invoices:
                names = ', '.join(overdue_invoices.mapped('name'))
                sub.message_post(
                    body=f"⚠️ <b>Auto-Suspensión por Mora:</b> Facturas vencidas hace más de {days_threshold} días: {names}"
                )
                sub.action_suspend()
                suspended_count += 1
                if tpl_suspended and sub.partner_id.email:
                    try:
                        tpl_suspended.send_mail(sub.id, force_send=True)
                    except Exception as e:
                        _logger.error(f"Failed to send suspended mail for sub {sub.name}: {e}")
        _logger.info(f"AUTO-SUSPEND: {suspended_count} suscripciones suspendidas por facturas vencidas.")
        return suspended_count

    def _cron_check_leasing_end(self):
        """Punto 7: gestión automática del fin de leasing.
        - 30 días antes del Fin de Plazo: notifica al cliente y crea activity para Cobranza.
        - Al cumplirse Fin de Plazo: cambia product_id a plan_after_leasing_id, ajusta price_unit,
          cambia equipment_ownership='customer', limpia plan_after_leasing_id, manda mail al cliente.
        """
        today = fields.Date.today()
        in_30_days = today + timedelta(days=30)
        tpl_notice = self.env.ref(
            'sentinela_subscriptions.mail_template_subscription_leasing_30_days',
            raise_if_not_found=False,
        )
        tpl_done = self.env.ref(
            'sentinela_subscriptions.mail_template_subscription_leasing_completed',
            raise_if_not_found=False,
        )
        # Buscar leasings activos con plan post-leasing configurado
        leasing_subs = self.search([
            ('state', '=', 'active'),
            ('equipment_ownership', '=', 'leasing'),
            ('plan_after_leasing_id', '!=', False),
            ('commitment_end_date', '!=', False),
        ])
        notices_sent = 0
        switches_done = 0
        for sub in leasing_subs:
            # Notice 30 days before
            if sub.commitment_end_date == in_30_days and tpl_notice:
                ctx = {
                    'new_plan_name': sub.plan_after_leasing_id.name,
                    'new_plan_price': sub.plan_after_leasing_id.list_price,
                }
                try:
                    tpl_notice.with_context(**ctx).send_mail(sub.id, force_send=True)
                    sub.message_post(
                        body=(f"📅 <b>Aviso de Fin de Leasing (30 días):</b> "
                              f"El {sub.commitment_end_date} cambia automáticamente al plan "
                              f"<b>{sub.plan_after_leasing_id.name}</b> "
                              f"(${sub.plan_after_leasing_id.list_price:,.2f}).")
                    )
                    sub.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=sub.commitment_end_date,
                        summary=f'Fin de leasing — cambio de plan automático {sub.name}',
                        note=(f'Cambio programado: {sub.product_id.name} → '
                              f'{sub.plan_after_leasing_id.name}'),
                    )
                    notices_sent += 1
                except Exception as e:
                    _logger.error(f"Leasing notice failed for {sub.name}: {e}")
            # Auto-switch on or after the end date
            if sub.commitment_end_date <= today:
                new_plan = sub.plan_after_leasing_id
                old_plan_name = sub.product_id.name
                sub.write({
                    'product_id': new_plan.id,
                    'price_unit': new_plan.list_price,
                    'equipment_ownership': 'customer',
                    'plan_after_leasing_id': False,
                })
                sub.message_post(
                    body=(f"✅ <b>Leasing completado:</b> Plan cambiado de "
                          f"<b>{old_plan_name}</b> a <b>{new_plan.name}</b> "
                          f"(${new_plan.list_price:,.2f}). Equipo ahora propiedad del cliente.")
                )
                if tpl_done:
                    try:
                        tpl_done.send_mail(sub.id, force_send=True)
                    except Exception as e:
                        _logger.error(f"Leasing completion mail failed for {sub.name}: {e}")
                switches_done += 1
        _logger.info(f"LEASING: notices={notices_sent} switches={switches_done}")
        return {'notices': notices_sent, 'switches': switches_done}

    def _cron_send_payment_reminders(self):
        """Recordatorios de cobranza al cliente (siempre se mandan, no respetan auto_send_mail):
        - Día +1 vencida la factura  → recordatorio SUAVE
        - Día -1 de auto-suspensión → recordatorio URGENTE
        El día de suspensión envía el cron _cron_auto_suspend_overdue.
        """
        today = fields.Date.today()
        tpl_soft = self.env.ref(
            'sentinela_subscriptions.mail_template_subscription_overdue_soft',
            raise_if_not_found=False,
        )
        tpl_urgent = self.env.ref(
            'sentinela_subscriptions.mail_template_subscription_pre_suspend',
            raise_if_not_found=False,
        )
        active_subs = self.search([('state', '=', 'active')])
        soft_count = 0
        urgent_count = 0
        for sub in active_subs:
            if sub.extension_due_date and sub.extension_due_date >= today:
                continue
            if not sub.partner_id.email:
                continue
            days_threshold = sub.days_to_suspend or 5
            for inv in sub.invoice_ids.filtered(
                lambda i: i.move_type == 'out_invoice'
                and i.state == 'posted'
                and i.payment_state in ('not_paid', 'partial')
                and i.invoice_date_due
            ):
                days_overdue = (today - inv.invoice_date_due).days
                days_until_suspend = days_threshold - days_overdue
                ctx = {
                    'invoice_name': inv.name,
                    'invoice_amount': inv.amount_total,
                    'invoice_date_due': inv.invoice_date_due.strftime('%d/%m/%Y'),
                    'days_until_suspend': days_until_suspend,
                }
                # Día +1 vencida — recordatorio SUAVE (1ª vez)
                if days_overdue == 1 and tpl_soft:
                    try:
                        tpl_soft.with_context(**ctx).send_mail(sub.id, force_send=True)
                        sub.message_post(body=f"📧 Recordatorio SUAVE enviado por factura {inv.name} vencida ayer.")
                        soft_count += 1
                    except Exception as e:
                        _logger.error(f"Failed to send soft reminder sub {sub.name}: {e}")
                # Día -1 de auto-suspensión — recordatorio URGENTE
                elif days_until_suspend == 1 and tpl_urgent:
                    try:
                        tpl_urgent.with_context(**ctx).send_mail(sub.id, force_send=True)
                        sub.message_post(body=f"📧 Recordatorio URGENTE enviado — mañana se suspende por factura {inv.name}.")
                        urgent_count += 1
                    except Exception as e:
                        _logger.error(f"Failed to send urgent reminder sub {sub.name}: {e}")
        _logger.info(f"REMINDERS: soft={soft_count} urgent={urgent_count}")
        return {'soft': soft_count, 'urgent': urgent_count}

    def action_monitor_traffic(self):
        self.ensure_one()
        # Method placeholder
        return True

    def action_generate_contract(self):
        self.ensure_one()
        if not self.contract_template_id:
            raise UserError("No hay una plantilla de contrato definida para este plan.")

        # Setea fecha del contrato la primera vez = fecha de alta del servicio (no la sobrescribe si ya existe)
        if not self.contract_date:
            self.contract_date = self.start_date

        # Render the template using mail.render.mixin logic from template
        rendered_content = self.contract_template_id._render_template(
            self.contract_template_id.content,
            'sentinela.subscription',
            [self.id]
        )[self.id]

        self.contract_body = rendered_content
        self.message_post(body="📄 <b>Contrato Generado:</b> Se ha actualizado el contenido del contrato digital.")

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_activate(self):
        self.write({
            'state': 'active', 
            'technical_state': 'active',
            'technical_state_date': fields.Datetime.now()
        })
        # Integración floLIVE
        for sub in self:
            if sub.sim_iccid and sub.service_type in ['gps', 'alarm']:
                success = self.env['sentinela.flolive.service'].update_sim_status(sub.sim_iccid, 'ACTIVE')
                if success:
                    sub.message_post(body=f"<b>floLIVE:</b> SIM {sub.sim_iccid} activada exitosamente.")
        
        self.action_provision_mikrotik_enable()

    def action_suspend(self):
        self.write({
            'state': 'suspension',
            'technical_state': 'suspended',
            'technical_state_date': fields.Datetime.now()
        })
        # Integración floLIVE
        for sub in self:
            if sub.sim_iccid and sub.service_type in ['gps', 'alarm']:
                success = self.env['sentinela.flolive.service'].update_sim_status(sub.sim_iccid, 'SUSPENDED')
                if success:
                    sub.message_post(body=f"<b>floLIVE:</b> SIM {sub.sim_iccid} suspendida (CORTE) exitosamente.")
        
        self.action_provision_mikrotik_disable()

    def action_cancel(self):
        self.write({
            'state': 'cancelled', 
            'technical_state': 'cut',
            'technical_state_date': fields.Datetime.now()
        })
        self.action_provision_mikrotik_disable()

    def action_renew_service(self):
        for sub in self:
            today = fields.Date.today()
            interval = int(sub.recurring_interval)
            if sub.next_billing_date and sub.next_billing_date >= today:
                new_date = sub.next_billing_date + relativedelta(months=interval)
                sub.next_billing_date = new_date
            else:
                new_date = today + relativedelta(months=interval)
                sub.next_billing_date = new_date
            
            if sub.technical_state in ['suspended', 'cut']:
                sub.action_activate()
                sub.message_post(body="Servicio reactivado automáticamente por renovación.")

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_mark_contract_signed(self):
        """Firma manual en papel — pasa a estado Confirmado."""
        self.write({'state': 'confirmed'})
        self.message_post(body="✅ <b>Contrato firmado en papel.</b> Estado actualizado a Confirmado.")

    def action_reactivate(self):
        """Reconecta un servicio suspendido."""
        self.write({
            'state': 'active',
            'technical_state': 'active',
            'technical_state_date': fields.Datetime.now(),
            'extension_due_date': False,
        })
        self.action_provision_mikrotik_enable()
        self.message_post(body="🔄 <b>Servicio reconectado.</b>")

    def action_open_extension_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Otorgar Prórroga',
            'res_model': 'sentinela.subscription.extension.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id},
        }

    def action_open_close_wizard(self):
        """Abre el wizard de Baja Definitiva. Si el contrato está dentro del plazo
        forzoso, el wizard muestra la opción de facturar penalización."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Baja Definitiva',
            'res_model': 'sentinela.subscription.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_action_type': 'cancel',
            },
        }

    def action_check_connection(self):
        """Verifica estado PPPoE en MikroTik y actualiza IP."""
        self.ensure_one()
        if not self.router_id or not self.pppoe_user:
            raise UserError("Se requiere un router y usuario PPPoE para verificar la conexión.")
        try:
            import routeros_api
            conn = routeros_api.RouterOsApiPool(
                self.router_id.ip_address,
                username=self.router_id.api_user or 'gemini_api',
                password=self.router_id.api_password or 'gemini_api2113',
                port=int(self.router_id.api_port or 8728),
                plaintext_login=True,
            )
            api = conn.get_api()
            sessions = api.get_resource('/ppp/active').get(name=self.pppoe_user)
            if sessions:
                s = sessions[0]
                self.write({'ip_address': s.get('address', self.ip_address)})
                conn.disconnect()
                return {'type': 'ir.actions.client', 'tag': 'display_notification',
                        'params': {'title': 'En Línea', 'message': f"IP: {s.get('address', '?')}", 'type': 'success'}}
            else:
                conn.disconnect()
                return {'type': 'ir.actions.client', 'tag': 'display_notification',
                        'params': {'title': 'Sin Línea', 'message': 'No hay sesión PPPoE activa.', 'type': 'warning'}}
        except Exception as e:
            raise UserError(f"Error al consultar MikroTik: {e}")

    def action_open_ping_wizard(self):
        """Ping ICMP real desde el router hacia la IP del cliente (latencia + % pérdida)."""
        self.ensure_one()
        if not self.router_id:
            raise UserError(_('Asigna primero el Router MikroTik.'))
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            self.router_id.ip_address, username=self.router_id.api_user,
            password=self.router_id.api_password or '', port=int(self.router_id.api_port or 8728),
            plaintext_login=True)
        try:
            api = conn.get_api()
            target_ip = self.ip_address
            # En PPPoE, tomar la IP de la sesión activa (más confiable)
            if self.internet_mgmt_mode == 'pppoe' and self.pppoe_user:
                sess = api.get_resource('/ppp/active').get(name=self.pppoe_user)
                if not sess:
                    conn.disconnect()
                    raise UserError(_('El cliente no tiene sesión PPPoE activa (offline). No se puede hacer ping.'))
                target_ip = sess[0].get('address', target_ip)
            if not target_ip:
                conn.disconnect()
                raise UserError(_('No hay IP asignada para hacer ping. Verifica la conexión primero.'))
            res = api.get_resource('/').call('ping', {'address': target_ip, 'count': '5'})
            conn.disconnect()
        except UserError:
            try: conn.disconnect()
            except Exception: pass
            raise
        except Exception as e:
            try: conn.disconnect()
            except Exception: pass
            raise UserError(_('Error al hacer ping desde el router: %s') % e)
        last = res[-1] if res else {}
        sent = last.get('sent', '5'); recv = last.get('received', '0')
        loss = last.get('packet-loss', '?'); avg = last.get('avg-rtt', '?')
        max_rtt = last.get('max-rtt', '?')
        try:
            ploss = int(loss)
            tipo = 'success' if ploss == 0 else ('warning' if ploss < 100 else 'danger')
        except Exception:
            tipo = 'warning'
        self.message_post(body=_('📡 <b>Ping a %s:</b> %s/%s recibidos, pérdida %s%%, latencia avg %s / max %s.') % (
            target_ip, recv, sent, loss, avg, max_rtt))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Ping a %s') % target_ip,
                           'message': _('%s/%s recibidos · pérdida %s%% · latencia %s (max %s)') % (recv, sent, loss, avg, max_rtt),
                           'type': tipo, 'sticky': False}}

    def action_view_traffic(self):
        """Actualiza el panel de tráfico en vivo EMBEBIDO en el formulario (sin popup)."""
        self.ensure_one()
        if not self.router_id:
            raise UserError(_('Asigna primero el Router MikroTik.'))
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            self.router_id.ip_address, username=self.router_id.api_user,
            password=self.router_id.api_password or '', port=int(self.router_id.api_port or 8728),
            plaintext_login=True)
        ip = self.ip_address or '—'; rx = tx = 0.0; status = 'Sin datos'
        try:
            api = conn.get_api()
            if self.internet_mgmt_mode == 'pppoe' and self.pppoe_user:
                sess = api.get_resource('/ppp/active').get(name=self.pppoe_user)
                if sess:
                    ip = sess[0].get('address', ip)
                    iface = sess[0].get('interface') or ('<pppoe-%s>' % self.pppoe_user)
                    stats = api.get_resource('/interface').call('monitor-traffic', {'interface': iface, 'once': 'true'})
                    if stats:
                        rx = round(int(stats[0].get('rx-bits-per-second', 0)) / 1000000.0, 2)
                        tx = round(int(stats[0].get('tx-bits-per-second', 0)) / 1000000.0, 2)
                        status = '🟢 En línea'
                else:
                    status = '🔴 Desconectado'
            conn.disconnect()
        except Exception as e:
            try: conn.disconnect()
            except Exception: pass
            raise UserError(_('Error al consultar tráfico: %s') % e)
        self.write({
            'live_traffic_status': status, 'live_traffic_ip': ip,
            'live_traffic_rx': '%s Mbps' % rx, 'live_traffic_tx': '%s Mbps' % tx,
            'live_traffic_updated': fields.Datetime.now(),
        })
        return True

    def action_signal_antenna(self):
        """Lee la señal/calidad del enlace de la antena CPE (Ubiquiti airOS) vía SSH mca-status."""
        self.ensure_one()
        if self.service_type != 'internet':
            raise UserError(_('Esta acción es solo para suscripciones de Internet.'))
        # IP del CPE: de la sesión PPPoE activa (la real)
        ip = self.ip_address
        if self.router_id and self.internet_mgmt_mode == 'pppoe' and self.pppoe_user:
            import routeros_api
            try:
                rconn = routeros_api.RouterOsApiPool(
                    self.router_id.ip_address, username=self.router_id.api_user,
                    password=self.router_id.api_password or '', port=int(self.router_id.api_port or 8728),
                    plaintext_login=True)
                rapi = rconn.get_api()
                sess = rapi.get_resource('/ppp/active').get(name=self.pppoe_user)
                if sess:
                    ip = sess[0].get('address', ip)
                rconn.disconnect()
            except Exception:
                pass
        if not ip:
            raise UserError(_('No hay IP del cliente. Usa "Verificar Conexión" primero (debe estar en línea).'))
        # SSH a la antena airOS
        import paramiko, re
        airos_user = self.env['ir.config_parameter'].sudo().get_param('sentinela.airos_user', 'sentinela')
        airos_pwd = self.env['ir.config_parameter'].sudo().get_param('sentinela.airos_password', 'SentinelaW1sp')
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            cli.connect(ip, port=22, username=airos_user, password=airos_pwd, look_for_keys=False,
                        allow_agent=False, timeout=12,
                        disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
            _in, out, _err = cli.exec_command('mca-status')
            data = out.read().decode('utf-8', 'ignore')
            cli.close()
        except Exception as ex:
            try: cli.close()
            except Exception: pass
            raise UserError(_('No se pudo leer la antena %s: %s') % (ip, str(ex)[:120]))
        d = {k: v.strip() for k, v in re.findall(r'(\w+)=([^,\r\n]+)', data)}
        try:
            sig = int(d.get('signal', 0) or 0)
        except Exception:
            sig = 0
        try:
            noise = int(d.get('noise', 0) or 0)
        except Exception:
            noise = 0
        snr = (sig - noise) if (sig and noise) else 0
        if sig == 0:
            quality = '❓ Sin datos'
        elif sig >= -65:
            quality = '🟢 Excelente'
        elif sig >= -75:
            quality = '🟢 Buena'
        elif sig >= -82:
            quality = '🟡 Regular'
        else:
            quality = '🔴 Mala (revisar antena)'
        self.write({
            'antenna_signal_dbm': '%s dBm' % sig,
            'antenna_snr': '%s dB' % snr,
            'antenna_signal_quality': quality,
            'antenna_link_rate': '%s / %s Mbps' % (d.get('wlanTxRate', '?'), d.get('wlanRxRate', '?')),
            'antenna_distance': '%s m' % d.get('distance', '?'),
            'antenna_signal_updated': fields.Datetime.now(),
        })
        plat = d.get('platform', 'CPE')
        self.message_post(body=_('📡 <b>Señal de antena (%s):</b> %s dBm · SNR %s dB · %s · enlace %s/%s Mbps · %sm') % (
            plat, sig, snr, quality, d.get('wlanTxRate', '?'), d.get('wlanRxRate', '?'), d.get('distance', '?')))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Señal: %s') % quality,
                           'message': _('%s dBm · SNR %s dB · enlace %s/%s Mbps · %s') % (
                               sig, snr, d.get('wlanTxRate', '?'), d.get('wlanRxRate', '?'), plat),
                           'type': 'success' if sig >= -75 and sig != 0 else 'warning', 'sticky': False}}

    def get_live_traffic(self):
        """Devuelve el tráfico actual (dict) para la gráfica animada OWL. Solo lectura."""
        self.ensure_one()
        res = {'rx': 0, 'tx': 0, 'ip': self.ip_address or '—', 'status': 'Sin datos'}
        if not self.router_id:
            res['status'] = 'Sin router'
            return res
        import routeros_api
        conn = None
        try:
            conn = routeros_api.RouterOsApiPool(
                self.router_id.ip_address, username=self.router_id.api_user,
                password=self.router_id.api_password or '', port=int(self.router_id.api_port or 8728),
                plaintext_login=True)
            api = conn.get_api()
            if self.internet_mgmt_mode == 'pppoe' and self.pppoe_user:
                sess = api.get_resource('/ppp/active').get(name=self.pppoe_user)
                if sess:
                    res['ip'] = sess[0].get('address', res['ip'])
                    iface = sess[0].get('interface') or ('<pppoe-%s>' % self.pppoe_user)
                    stats = api.get_resource('/interface').call('monitor-traffic', {'interface': iface, 'once': 'true'})
                    if stats:
                        res['rx'] = round(int(stats[0].get('rx-bits-per-second', 0)) / 1000000.0, 2)
                        res['tx'] = round(int(stats[0].get('tx-bits-per-second', 0)) / 1000000.0, 2)
                        res['status'] = 'En línea'
                else:
                    res['status'] = 'Desconectado'
            conn.disconnect()
        except Exception as e:
            if conn:
                try: conn.disconnect()
                except Exception: pass
            res['status'] = 'Error: %s' % str(e)[:40]
        return res

    def action_request_pppoe_credentials(self):
        self.ensure_one()
        self.message_post(body="🔑 <b>Solicitud de Credenciales PPPoE</b> enviada al equipo técnico.")
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Solicitud enviada', 'message': 'El equipo técnico generará las credenciales.', 'type': 'info'}}

    def _get_mikrotik_api(self):
        """Abre y devuelve la conexión API al router de esta suscripción."""
        self.ensure_one()
        if not self.router_id:
            raise UserError("Esta suscripción no tiene un router asignado.")
        if not self.router_id.sync_active:
            return None
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            self.router_id.ip_address,
            username=self.router_id.api_user,
            password=self.router_id.api_password or '',
            port=self.router_id.api_port,
            plaintext_login=True
        )
        return conn

    def action_provision_mikrotik_enable(self):
        """Crea o habilita el secret PPPoE y lo saca de la lista de suspendidos."""
        for sub in self:
            if sub.service_type != 'internet' or sub.internet_mgmt_mode != 'pppoe':
                continue
            if not sub.pppoe_user or not sub.router_id:
                continue
            conn = sub._get_mikrotik_api()
            if not conn:
                continue
            try:
                api = conn.get_api()
                secrets = api.get_resource('/ppp/secret')
                profile_name = sub.mikrotik_profile_id.name if sub.mikrotik_profile_id else 'default'

                existing = secrets.get(name=sub.pppoe_user)
                if existing:
                    secrets.set(
                        id=existing[0]['id'],
                        password=sub.pppoe_password or '',
                        profile=profile_name,
                        disabled='false',
                        comment=f'Odoo SUB/{sub.name}'
                    )
                else:
                    secrets.add(
                        name=sub.pppoe_user,
                        password=sub.pppoe_password or '',
                        service='pppoe',
                        profile=profile_name,
                        comment=f'Odoo SUB/{sub.name}'
                    )

                # Quitar de address-list suspendidos si estaba ahí
                addr_list = api.get_resource('/ip/firewall/address-list')
                suspended_entries = addr_list.get(**{'list': 'argusblack_servicio_suspendido', 'comment': sub.pppoe_user})
                for entry in suspended_entries:
                    addr_list.remove(id=entry['id'])

                conn.disconnect()
                sub.message_post(body=f"<b>MikroTik:</b> Secret PPPoE <b>{sub.pppoe_user}</b> activado con perfil <b>{profile_name}</b>.")
            except Exception as e:
                try:
                    conn.disconnect()
                except Exception:
                    pass
                _logger.error("MikroTik enable error sub %s: %s", sub.name, e)
                sub.message_post(body=f"<b>MikroTik ERROR al activar:</b> {e}")

    def action_provision_mikrotik_disable(self):
        """Deshabilita el secret PPPoE y agrega al cliente a la lista de suspendidos."""
        for sub in self:
            if sub.service_type != 'internet' or sub.internet_mgmt_mode != 'pppoe':
                continue
            if not sub.pppoe_user or not sub.router_id:
                continue
            conn = sub._get_mikrotik_api()
            if not conn:
                continue
            try:
                api = conn.get_api()

                # Deshabilitar secret PPPoE
                secrets = api.get_resource('/ppp/secret')
                existing = secrets.get(name=sub.pppoe_user)
                if existing:
                    secrets.set(id=existing[0]['id'], disabled='true')

                # Desconectar sesión activa si existe
                active = api.get_resource('/ppp/active')
                sessions = active.get(name=sub.pppoe_user)
                for session in sessions:
                    active.remove(id=session['id'])

                # Agregar a address-list de suspendidos (si no está ya)
                addr_list = api.get_resource('/ip/firewall/address-list')
                existing_entry = addr_list.get(**{'list': 'argusblack_servicio_suspendido', 'comment': sub.pppoe_user})
                if not existing_entry and sub.ip_address:
                    addr_list.add(**{
                        'list': 'argusblack_servicio_suspendido',
                        'address': sub.ip_address,
                        'comment': sub.pppoe_user
                    })

                conn.disconnect()
                sub.message_post(body=f"<b>MikroTik:</b> Secret PPPoE <b>{sub.pppoe_user}</b> deshabilitado y agregado a lista de suspendidos.")
            except Exception as e:
                try:
                    conn.disconnect()
                except Exception:
                    pass
                _logger.error("MikroTik disable error sub %s: %s", sub.name, e)
                sub.message_post(body=f"<b>MikroTik ERROR al suspender:</b> {e}")

    @api.depends('start_date', 'commitment_period', 'is_forced_contract')
    def _compute_commitment_end(self):
        for sub in self:
            if sub.is_forced_contract and sub.start_date and sub.commitment_period:
                sub.commitment_end_date = sub.start_date + relativedelta(months=sub.commitment_period)
            else:
                sub.commitment_end_date = False

    @api.depends('product_id')
    def _compute_mikrotik_profile_id(self):
        """Hereda el perfil MikroTik del plan de forma confiable (no depende del onchange UI).
        Si el plan no tiene perfil, conserva el valor manual existente."""
        for sub in self:
            prof = sub.product_id.mikrotik_profile_id
            if prof:
                sub.mikrotik_profile_id = prof
            elif not sub.mikrotik_profile_id:
                sub.mikrotik_profile_id = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for sub in self:
            if not sub.product_id:
                continue
            if not sub.price_unit:
                sub.price_unit = sub.product_id.list_price
            if sub.product_id.default_recurring_interval and not sub.recurring_interval:
                sub.recurring_interval = sub.product_id.default_recurring_interval
            if sub.product_id.service_type and not sub.service_type:
                sub.service_type = sub.product_id.service_type

    @api.onchange('antenna_product_id')
    def _onchange_antenna_product_id(self):
        for sub in self:
            if sub.antenna_product_id:
                sub.antenna_brand = sub.antenna_product_id.syscom_brand or sub.antenna_brand
                sub.antenna_model = sub.antenna_product_id.name

    @api.onchange('router_product_id')
    def _onchange_router_product_id(self):
        for sub in self:
            if sub.router_product_id:
                sub.equipment_brand = sub.router_product_id.syscom_brand or sub.equipment_brand
                sub.equipment_model = sub.router_product_id.name

    @api.onchange('start_date', 'recurring_interval')
    def _onchange_start_date(self):
        for sub in self:
            if sub.start_date and sub.recurring_interval and not sub.next_billing_date:
                sub.next_billing_date = sub.start_date + relativedelta(months=int(sub.recurring_interval))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sentinela.subscription') or 'New'
        subs = super().create(vals_list)
        # Auto-derivar inclusion records desde la matriz del plan
        for sub in subs:
            sub._derive_service_inclusions()
        return subs

    def _derive_service_inclusions(self):
        """Copia la matriz product.service.inclusion del plan a la suscripción.
        No sobreescribe — solo crea registros para servicios que aún no existen
        en la suscripción (idempotente y seguro para re-llamar)."""
        for sub in self:
            if not sub.product_id:
                continue
            template = sub.product_id
            existing_service_ids = set(sub.service_inclusion_ids.mapped('service_id.id'))
            matrix = self.env['sentinela.product.service.inclusion'].sudo().search([
                ('product_id', '=', template.id),
            ])
            for row in matrix:
                if row.service_id.id in existing_service_ids:
                    continue
                self.env['sentinela.subscription.service.inclusion'].sudo().create({
                    'subscription_id': sub.id,
                    'service_id': row.service_id.id,
                    'is_included': row.is_included,
                    'extra_price': row.extra_price,
                })

    @api.constrains('service_inclusion_ids', 'product_id')
    def _check_service_inclusions_complete(self):
        """Si el plan tiene matriz definida en product.service.inclusion,
        la suscripción debe tener todos los inclusion records derivados.
        Permite legacy plans (sin matriz) y no-monitoreo (TK-Renta, R*MB, etc.)."""
        for sub in self:
            if not sub.product_id:
                continue
            template = sub.product_id
            plan_services = self.env['sentinela.product.service.inclusion'].sudo().search([
                ('product_id', '=', template.id),
            ])
            if not plan_services:
                continue  # plan legacy / no-monitoreo: se perdona
            plan_service_ids = set(plan_services.mapped('service_id.id'))
            sub_service_ids = set(sub.service_inclusion_ids.mapped('service_id.id'))
            missing = plan_service_ids - sub_service_ids
            if missing:
                names = self.env['sentinela.service.definition'].sudo().browse(list(missing)).mapped('name')
                raise ValidationError(_(
                    "La suscripción '%s' (plan %s) no tiene definidos todos los servicios. "
                    "Faltan: %s. Edita la sección 'Servicios Incluidos' antes de guardar."
                ) % (sub.name, template.default_code or template.name, ', '.join(names)))

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción / Contrato')
    is_renewal_processed = fields.Boolean(default=False, copy=False)
    target_transfer_address_id = fields.Many2one('res.partner', string='Dirección Destino (Traslado)')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción')

class AccountMove(models.Model):
    _inherit = 'account.move'
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción / Contrato')
    subscription_ids = fields.Many2many(
        'sentinela.subscription',
        'account_move_subscription_rel',
        'move_id', 'subscription_id',
        string='Suscripciones agrupadas',
        help='Todas las suscripciones que aporta esta factura. Usado para clientes con preferencia de facturación global o por sucursal.')
    is_renewal_processed = fields.Boolean(default=False, copy=False)
