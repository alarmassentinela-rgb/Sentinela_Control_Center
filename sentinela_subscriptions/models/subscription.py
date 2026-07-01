from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
import calendar
import base64
import json
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
        ('maintenance', 'Mantenimiento / Póliza'),
        ('domain', 'Nombre de Dominio')
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
    invoice_notes = fields.Text(
        string='Notas para Factura',
        help='Texto que aparece en el recuadro "Notas" de la factura/remisión PDF del cliente. '
             'A diferencia de las Notas Internas, ESTE sí lo ve el cliente.')

    # --- Ubicación Técnica (Categoría 1: dirección de INSTALACIÓN, fija) ---
    # NO confundir con gps_sim_lat/lon (Categoría 2: ubicación móvil del rastreador GPS/SIM).
    location_notes = fields.Text(string='Referencias de Ubicación')
    latitude = fields.Char(string='Latitud')
    longitude = fields.Char(string='Longitud')
    coords_status = fields.Selection([
        ('none', 'Sin ubicación'),
        ('estimada', 'Estimada (por dirección)'),
        ('verificada', 'Verificada en sitio'),
    ], string='Estado de coordenadas', default='none', tracking=True,
       help="Estimada = capturada por dirección/geocode. Verificada = confirmada en la "
            "instalación con GPS + firma del cliente (queda bloqueada salvo supervisor).")
    coords_map_html = fields.Html(string='Mapa de ubicación', compute='_compute_coords_map_html', sanitize=False)

    @api.depends('latitude', 'longitude')
    def _compute_coords_map_html(self):
        for s in self:
            if s.latitude and s.longitude:
                s.coords_map_html = (
                    '<div style="width:320px;max-width:100%;margin:0">'
                    '<div style="position:relative;padding-bottom:75%;height:0;overflow:hidden;border-radius:8px">'
                    '<iframe style="position:absolute;top:0;left:0;width:100%;height:100%;border:0" '
                    'loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
                    f'src="https://maps.google.com/maps?q={s.latitude},{s.longitude}&amp;t=&amp;z=17&amp;ie=UTF8&amp;iwloc=&amp;output=embed"></iframe>'
                    '</div></div>'
                )
            else:
                s.coords_map_html = '<div class="text-muted">Sin coordenadas. Captura la dirección y pulsa "Obtener coordenadas".</div>'

    def action_unlock_coords(self):
        """Desbloquea las coordenadas verificadas para corrección (solo manager)."""
        self.ensure_one()
        if not self.env.user.has_group('sentinela_subscriptions.group_subscription_manager'):
            raise UserError(_("Solo un supervisor puede desbloquear coordenadas verificadas."))
        self.coords_status = 'estimada'
        return True

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
        vals = {'latitude': str(lat), 'longitude': str(lng)}
        # Geocodificar marca la coordenada como ESTIMADA (salvo que esté verificada en sitio)
        if self.coords_status != 'verificada':
            vals['coords_status'] = 'estimada'
        self.write(vals)
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
    gps_platform = fields.Selection([
        ('tracksolid', 'Tracksolid Pro'),
        ('smake', 'Smake'),
        ('senticar', 'SentiCar'),
    ], string='Plataforma de Rastreo')
    gps_platform_device_id = fields.Char(string='ID / Usuario en Plataforma',
        help="Identificador del equipo en la plataforma de rastreo (Tracksolid Pro / Smake / SentiCar).")
    # --- GPS multi-equipo: 1 suscripción = N equipos (renglones) ---
    gps_mode = fields.Selection(related='product_id.gps_mode', store=True,
        string='Modo GPS', readonly=True,
        help="Lo define el plan: 'GPS Vehículo' (SIM nuestra, se corta al suspender) o 'Rastreo Móvil' (SIM del cliente, nunca se corta).")
    gps_device_ids = fields.One2many('sentinela.subscription.gps.device', 'subscription_id', string='Equipos GPS')
    gps_device_count = fields.Integer(string='Nº de Equipos', compute='_compute_gps_device_count', store=True)
    senticar_portal_url = fields.Char(string='Portal del Transportista', compute='_compute_senticar_portal_url',
        help="Link personal del cliente para generar links de rastreo de sus unidades. Genéralo con el botón.")
    senticar_distributor_id = fields.Many2one(related='partner_id.senticar_distributor_id', readonly=False,
        string='Distribuidor SentiCar',
        help="Si el cliente cuelga de un distribuidor, su grupo se anida bajo el del distribuidor y "
             "el distribuidor ve sus equipos. Se aplica en la próxima alta/reconciliación.")

    @api.depends('partner_id.senticar_portal_token')
    def _compute_senticar_portal_url(self):
        # El portal vive en Odoo (mismo backend que senticar.com). Dominio configurable.
        web = (self.env['ir.config_parameter'].sudo().get_param('sentinela.senticar_portal_base')
               or 'https://senticar.com').rstrip('/')
        for s in self:
            tok = s.partner_id.senticar_portal_token
            s.senticar_portal_url = (web + '/senticar/t/' + tok) if tok else False

    def action_make_portal_link(self):
        """Genera (si falta) el token del portal del transportista y muestra su link."""
        self.ensure_one()
        self.partner_id.ensure_senticar_portal_token()
        self.message_post(body=_("🔗 <b>Portal del transportista</b> (mándaselo al cliente): %s") % self.senticar_portal_url)

    @api.depends('gps_device_ids')
    def _compute_gps_device_count(self):
        for s in self:
            s.gps_device_count = len(s.gps_device_ids)

    # --- Diagnóstico GPS (datos de la SIM en floLIVE/Connecta, solo lectura) ---
    gps_sim_status = fields.Char(string='Estado SIM', readonly=True)
    gps_sim_online = fields.Boolean(string='En sesión de datos', readonly=True)
    gps_sim_lat = fields.Char(string='Latitud', readonly=True)
    gps_sim_lon = fields.Char(string='Longitud', readonly=True)
    gps_sim_map_url = fields.Char(string='Mapa', compute='_compute_gps_sim_map_url')
    gps_sim_network = fields.Char(string='Red conectada', readonly=True)
    gps_sim_last_session = fields.Char(string='Última sesión de datos', readonly=True)
    gps_sim_checked = fields.Datetime(string='Diagnóstico actualizado', readonly=True)
    # --- Enlace con SentiCar (device de esta suscripción en la plataforma propia) ---
    senticar_device_id = fields.Integer(string='ID Equipo en SentiCar', copy=False, readonly=True,
        help="Identificador del equipo de esta suscripción en SentiCar/Traccar. Se crea al registrarlo.")

    # --- Comandos SMS al GPS (vía Connecta) ---
    gps_sms_command = fields.Char(string='Comando SMS a enviar')
    gps_sms_encoding = fields.Selection([
        ('GSM-7', 'GSM-7 (texto normal)'),
        ('UCS2', 'UCS2 (acentos / unicode)'),
    ], string='Codificación', default='GSM-7')
    gps_sms_log = fields.Text(string='Bitácora de comandos SMS', readonly=True)

    @api.depends('gps_sim_lat', 'gps_sim_lon')
    def _compute_gps_sim_map_url(self):
        for s in self:
            if s.gps_sim_lat and s.gps_sim_lon:
                s.gps_sim_map_url = f"https://www.google.com/maps?q={s.gps_sim_lat},{s.gps_sim_lon}"
            else:
                s.gps_sim_map_url = False
    equipment_brand = fields.Char(string='Marca')
    equipment_model = fields.Char(string='Modelo')
    equipment_serial = fields.Char(string='Número de Serie (Manual)')

    # --- Vehículo (GPS / Rastreo) ---
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
    # Diagnóstico REAL de navegación (no solo "conectado al router")
    nav_status = fields.Char(string='Diagnóstico de Navegación', readonly=True)
    nav_status_date = fields.Datetime(string='Validado el', readonly=True)
    # Señal de la antena CPE (airOS, vía SSH mca-status)
    antenna_signal_dbm = fields.Char(string='Señal', readonly=True)
    antenna_snr = fields.Char(string='SNR', readonly=True)
    antenna_signal_quality = fields.Char(string='Calidad de Señal', readonly=True)
    antenna_link_rate = fields.Char(string='Enlace TX/RX', readonly=True)
    antenna_distance = fields.Char(string='Distancia', readonly=True)
    antenna_signal_updated = fields.Datetime(string='Señal actualizada', readonly=True)
    # Estado de conexión en vivo (lo refresca el cron _cron_refresh_antenna_signal)
    conn_online = fields.Boolean(string='En línea', readonly=True)
    conn_live_ip = fields.Char(string='IP en vivo', readonly=True)
    conn_checked = fields.Datetime(string='Conexión revisada', readonly=True)
    conn_status_display = fields.Char(string='Estado', compute='_compute_conn_status_display')
    ping_result = fields.Text(string='Resultado del Ping', readonly=True)

    @api.depends('conn_online', 'conn_checked')
    def _compute_conn_status_display(self):
        for s in self:
            if not s.conn_checked:
                s.conn_status_display = '⚪ Sin revisar'
            elif s.conn_online:
                s.conn_status_display = '🟢 CONECTADA'
            else:
                s.conn_status_display = '🔴 DESCONECTADA'

    # --- Internet WISP (PPPoE & Router) ---
    router_id = fields.Many2one('sentinela.router', string='Mikrotik Router')
    internet_mgmt_mode = fields.Selection([
        ('pppoe', 'PPPoE'),
        ('static', 'IP Estática'),
        ('dhcp', 'DHCP'),
    ], string='Modo de Conexión', default='pppoe')
    connection_equipment = fields.Selection([
        ('antenna_airos', 'Antena airOS (Ubiquiti)'),
        ('modem_direct', 'Módem directo'),
        ('other', 'Otro / N/A'),
    ], string='Equipo de Conexión', default='antenna_airos',
       help="Antena airOS: permite leer la señal por SSH (botón 'Señal Antena'). "
            "Módem directo / Otro: no hay antena airOS — la lectura de señal no aplica y el botón se oculta.")
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
    contract_gps_platform = fields.Char(
        string='Plataforma de Rastreo (Contrato)', compute='_compute_contract_fields', store=False)
    contract_equipment_clause = fields.Html(
        string='Cláusula de Equipo (Contrato)', compute='_compute_contract_fields', store=False, sanitize=False)

    @api.depends('antenna_brand', 'antenna_model', 'router_id', 'router_id.ip_address',
                 'router_id.pppoe_server_name', 'service_address_id', 'address_street',
                 'address_street2', 'address_city', 'address_zip', 'monitoring_account_number',
                 'gps_platform', 'equipment_ownership', 'commitment_period', 'is_forced_contract',
                 'early_termination_fee', 'penalty_amount')
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
            plat_map = dict(rec._fields['gps_platform'].selection or [])
            rec.contract_gps_platform = plat_map.get(rec.gps_platform) or 'la plataforma de rastreo contratada'
            rec.contract_equipment_clause = rec._build_equipment_clause()

    def _build_equipment_clause(self):
        """Construye la cláusula TERCERA (EQUIPO) del contrato según el régimen del equipo."""
        self.ensure_one()
        from markupsafe import Markup
        money = lambda v: '${:,.2f} MXN'.format(v or 0.0)
        meses = self.commitment_period or 0
        fee = money(self.early_termination_fee or self.penalty_amount or 0.0)
        if self.equipment_ownership == 'customer':
            html = (
                '<p><strong>TERCERA. EQUIPO.</strong> El dispositivo de rastreo (GPS) y la SIM son propiedad de '
                'EL SUSCRIPTOR. EL PROVEEDOR presta únicamente el servicio de localización a través de la plataforma '
                'contratada; no se entrega equipo en comodato ni en arrendamiento, ni existe plazo forzoso por concepto '
                'de equipo.</p>'
            )
        elif self.equipment_ownership == 'leasing':
            extra = (' El plazo forzoso es de <strong>%s meses</strong>; la cancelación anticipada antes de cumplirlo '
                     'generará una penalización de <strong>%s</strong>.' % (meses, fee)) if meses else ''
            html = (
                '<p><strong>TERCERA. EQUIPO (ARRENDAMIENTO CON OPCIÓN A COMPRA).</strong> El dispositivo de rastreo '
                '(GPS) y la SIM se entregan en arrendamiento con opción a compra. Durante el plazo forzoso, la renta '
                'mensual incluye el costo del equipo. Al concluir dicho plazo y estando EL SUSCRIPTOR al corriente en '
                'sus pagos, el equipo pasará a ser de su <strong>propiedad</strong>.' + extra + '</p>'
            )
        else:  # company / comodato (default)
            extra = (' El contrato tiene un plazo forzoso de <strong>%s meses</strong> por el equipo en comodato; la '
                     'cancelación anticipada generará una penalización de <strong>%s</strong>.' % (meses, fee)) if (self.is_forced_contract and meses) else ''
            html = (
                '<p><strong>TERCERA. EQUIPO (COMODATO).</strong> Para la prestación del servicio, EL PROVEEDOR instala '
                'en el vehículo un dispositivo de rastreo (GPS) y una SIM entregados en comodato, que son y seguirán '
                'siendo propiedad de EL PROVEEDOR. EL SUSCRIPTOR se obliga a conservarlos en buen estado y a devolverlos '
                'al término del contrato. En caso de daño por negligencia, manipulación indebida, retiro no autorizado o '
                'no devolución, cubrirá el costo de reposición vigente.' + extra + '</p>'
            )
        return Markup(html)

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
    auto_invoice = fields.Boolean(
        string='Generar Factura (No Remisión)',
        related='partner_id.requiere_factura', store=True, readonly=True,
        help="Se DERIVA del cliente ('Requiere Factura CFDI'). Si está activo, la factura del "
             "ciclo nace como 'Pendiente de Timbrado'; si no, queda como remisión. "
             "Para cambiarlo, edita 'Requiere Factura CFDI' en el cliente.")
    auto_send_mail = fields.Boolean(string='Enviar automáticamente por Correo', default=False)
    extra_invoice_partner_ids = fields.Many2many(
        'res.partner',
        'sentinela_sub_extra_invoice_partner_rel',
        'subscription_id', 'partner_id',
        string='Correos adicionales (CC)',
        help="Contactos del cliente que recibirán COPIA (CC) de la factura/remisión del "
             "ciclo, además del correo principal. Útil cuando la empresa quiere que el "
             "documento también llegue al gerente, contabilidad, etc. Solo se usan los "
             "contactos que tengan correo cargado.")
    billing_mode = fields.Selection([
        ('normal', 'Normal'),
        ('courtesy', 'Cortesía'),
    ], string='Tipo de Facturación', default='normal', required=True, tracking=True,
       help="Normal: se factura y entra a cobranza/suspensión. "
            "Cortesía: el servicio queda activo pero NO se le genera factura/remisión, "
            "NO entra a cobranza, recordatorios ni auto-suspensión. "
            "Solo un administrador (Gestor de Suscripciones) puede cambiarlo.")
    can_edit_billing_mode = fields.Boolean(
        compute='_compute_can_edit_billing_mode',
        help="True si el usuario actual es Gestor de Suscripciones (puede editar el Tipo de Facturación).")

    @api.depends_context('uid')
    def _compute_can_edit_billing_mode(self):
        is_mgr = self.env.user.has_group('sentinela_subscriptions.group_subscription_manager')
        for rec in self:
            rec.can_edit_billing_mode = is_mgr

    can_edit_router = fields.Boolean(
        compute='_compute_can_edit_router',
        help="True si el usuario es Gestor de Suscripciones (puede cambiar el Router MikroTik).")

    @api.depends_context('uid')
    def _compute_can_edit_router(self):
        is_mgr = self.env.user.has_group('sentinela_subscriptions.group_subscription_manager')
        for rec in self:
            rec.can_edit_router = is_mgr
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

    def action_cobro_adelantado(self):
        """ Abre el wizard para generar una factura borrador de N meses por adelantado.
        Al publicar esa factura, el ciclo (next_billing_date) avanza esos N meses. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cobro de Meses por Adelantado'),
            'res_model': 'sentinela.subscription.advance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id},
        }

    def action_cobro_adelantado_global(self):
        """ Abre el wizard de cobro adelantado GLOBAL del cliente (todas sus suscripciones activas),
        con preview por suscripción de la fecha de cobro antes/después. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cobro Adelantado Global del Cliente'),
            'res_model': 'sentinela.subscription.advance.global.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.partner_id.id},
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
            ('billing_mode', '!=', 'courtesy'),
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
                    ('billing_mode', '!=', 'courtesy'),
                ])
            elif method == 'by_branch':
                group = self.search([
                    ('state', '=', 'active'),
                    ('partner_id', '=', sub.partner_id.id),
                    ('service_address_id', '=', sub.service_address_id.id if sub.service_address_id else False),
                    ('next_billing_date', '<=', end_of_month),
                    ('billing_mode', '!=', 'courtesy'),
                ])
            else:
                group = sub
            grouped_subs[key] = group

        for key, group in grouped_subs.items():
            try:
                self._billing_generate_invoice(group)
            except Exception as e:
                _logger.error(f"BILLING: Falló la generación para grupo {key}: {str(e)}")

    def _billing_period_label(self, n_ciclos=1):
        """Etiqueta del periodo para la línea de factura: 'CORRESPONDIENTE AL MES DE <MES> <AÑO>'
        (o rango de meses si el ciclo es multi-mes). La usan la descripción de la línea Y el
        candado anti-duplicado, así que AMBOS deben llamar a este mismo método para no desincronizar.

        `n_ciclos` (default 1) = nº de ciclos que cubre el documento. El cron y el candado lo
        llaman sin argumento (1 ciclo natural); el cobro adelantado global lo llama con N para
        que la etiqueta abarque los N×intervalo meses prepagados. Con n_ciclos=1 el resultado es
        idéntico al histórico."""
        self.ensure_one()
        meses = ['', 'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO',
                 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
        nb = self.next_billing_date
        months = int(self.recurring_interval or 1) * int(n_ciclos or 1)
        if months <= 1:
            return "CORRESPONDIENTE AL MES DE %s %s" % (meses[nb.month], nb.year)
        period_end = nb + relativedelta(months=months) - timedelta(days=1)
        return "CORRESPONDIENTE DE %s %s A %s %s" % (meses[nb.month], nb.year, meses[period_end.month], period_end.year)

    def _billing_line_qty(self, n_ciclos=1):
        """ Cantidad a facturar de UNA suscripción para n_ciclos ciclos. Fuente ÚNICA usada por
        el cron, el cobro adelantado global y el preview del wizard (decisión #7, sin duplicar).
        CONVENCIÓN (Opción B, 1-jul-2026): `price_unit` SIEMPRE es el precio del PERIODO COMPLETO
        del ciclo (no mensual), para TODOS los tipos (alarma/dominio/internet/GPS/mantenimiento).
        Por eso la cantidad NO se multiplica por los meses del intervalo: qty = 1 por ciclo — el
        único multiplicador legítimo es el nº de equipos (GPS), que sí son unidades contables.
        El periodo queda reflejado en la etiqueta y el avance de next_billing, NO en la cantidad.
        Todo × n_ciclos (cobro adelantado global). """
        self.ensure_one()
        q = 1
        if self.service_type == 'gps':
            n_dev = max(1, len(self.gps_device_ids.filtered(lambda d: d.device_state != 'suspended')))
            q = n_dev
        return q * n_ciclos

    def _build_group_lines(self, subs_list, n_ciclos=1):
        """ Fuente ÚNICA de verdad de las LÍNEAS de una factura de grupo. La comparten:
          - el cron de facturación recurrente (`_billing_generate_invoice`, n_ciclos=1),
          - el cobro adelantado global (n_ciclos=N).
        Devuelve la lista de comandos (0,0,{...}) para `invoice_line_ids`.

        Cantidad por sub = qty de UN ciclo × n_ciclos. El avance de `next_billing_date` y el
        conteo de ciclos NO se infieren de estas líneas: viven explícitos en el account.move
        (`advance_periods`), para no tener que reconstruir el contexto leyendo la factura.
        Con n_ciclos=1 produce exactamente las mismas líneas que el cron histórico. """
        partner = subs_list[0].partner_id
        method = partner.invoice_grouping_method or 'individual'

        # Cantidad por sub = _billing_line_qty (fuente única compartida con el wizard de adelanto).
        # Periodo: si TODAS las subs comparten el mismo, va UNA sola vez (renglón de nota al final)
        # y NO se repite en cada línea. Si hubiera periodos distintos (raro), se deja por línea.
        period_labels = {s._billing_period_label(n_ciclos) for s in subs_list}
        single_period = list(period_labels)[0] if len(period_labels) == 1 else None
        # Toggle por cliente: detallar nombres de sucursales en la factura global o solo el conteo.
        show_branches = getattr(partner, 'invoice_show_branches', True)

        line_cmds = []
        if method == 'global' and len(subs_list) > 1:
            # FACTURACIÓN GLOBAL CONSOLIDADA: una línea por (producto, precio, periodo); la cantidad
            # es el nº de servicios del grupo. Sucursales según el toggle del cliente.
            groups, order = {}, []
            for sub in subs_list:
                key = (sub.product_id.id, round(sub.price_unit, 2), sub._billing_period_label(n_ciclos))
                if key not in groups:
                    groups[key] = []
                    order.append(key)
                groups[key].append(sub)
            for key in order:
                gsubs = groups[key]
                prod = gsubs[0].product_id
                if show_branches:
                    suc_txt = " | Sucursales: %s" % ", ".join((s.service_address_id.name or s.name) for s in gsubs)
                else:
                    suc_txt = ""
                per_txt = "" if single_period else (" - %s" % gsubs[0]._billing_period_label(n_ciclos))
                desc = "Servicio: %s%s%s" % (prod.name, per_txt, suc_txt)
                line_cmds.append((0, 0, {
                    # `product_id` de la sub es product.template → la línea de factura exige la
                    # VARIANTE (product.product). Usar .id de la plantilla solo "funciona" cuando
                    # coinciden los ids (migración legacy); con productos nuevos falla → factura en
                    # ceros. Resolver siempre a la variante principal.
                    'product_id': prod.product_variant_id.id,
                    'name': desc,
                    'quantity': sum(s._billing_line_qty(n_ciclos) for s in gsubs),
                    'price_unit': gsubs[0].price_unit,
                }))
        else:
            for sub in subs_list:
                dev_suffix = ""
                if sub.service_type == 'gps':
                    n_dev = max(1, len(sub.gps_device_ids.filtered(lambda d: d.device_state != 'suspended')))
                    dev_suffix = f" - {n_dev} equipo(s)"
                per_txt = "" if single_period else (" - %s" % sub._billing_period_label(n_ciclos))
                desc = f"Servicio: {sub.product_id.name} - Contrato: {sub.name}{dev_suffix}{per_txt}"
                line_cmds.append((0, 0, {
                    # Ver nota arriba: resolver la plantilla a su variante (product.product).
                    'product_id': sub.product_id.product_variant_id.id,
                    'name': desc,
                    'quantity': sub._billing_line_qty(n_ciclos),
                    'price_unit': sub.price_unit,
                }))
        # Renglón de NOTA con el periodo (una sola vez). Mantiene el periodo visible y permite que
        # el candado anti-duplicado lo siga encontrando (busca _billing_period_label en las líneas).
        if single_period:
            line_cmds.append((0, 0, {'display_type': 'line_note', 'name': "Periodo facturado: %s" % single_period}))
        return line_cmds

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
        # 🔒 CANDADO ANTI-DUPLICADO: no re-facturar una suscripción cuyo periodo actual
        # (next_billing_date) ya tenga una factura NO cancelada. Evita facturas dobles del
        # mismo periodo aunque el cron corra de más, se traslape, o se llame este método dos veces.
        billables = self.env['sentinela.subscription']
        omitidas = []
        for sub in subs_list:
            dup = Move.search_count([
                ('move_type', '=', 'out_invoice'),
                ('state', '!=', 'cancel'),
                '|', ('subscription_ids', 'in', sub.id), ('subscription_id', '=', sub.id),
                ('invoice_line_ids.name', 'ilike', sub._billing_period_label()),
            ])
            if dup:
                omitidas.append(sub.name)
            else:
                billables |= sub
        if omitidas:
            _logger.warning("BILLING anti-duplicado: omitidas (ya facturadas este periodo): %s", omitidas)
        if not billables:
            return
        subs_list = billables
        partner = subs_list[0].partner_id
        first_sub = subs_list[0]
        method = partner.invoice_grouping_method or 'individual'

        # Líneas de la factura: fuente ÚNICA de verdad, compartida con el cobro adelantado global
        # (refactor D1). n_ciclos=1 = ciclo natural del cron. El avance de next_billing_date y el
        # conteo de ciclos NO se infieren de estas líneas: viven explícitos en el account.move.
        line_cmds = self._build_group_lines(subs_list, n_ciclos=1)
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
            # Gating timbrado vs remisión (según preferencia fiscal del CLIENTE):
            # - requiere_factura=True  -> 'pending' (Pendiente de Timbrado): queda en la
            #   lista de trabajo de facturas por timbrar. El timbrado NO es automático:
            #   sigue siendo el botón manual action_cfdi_stamp_prodigia (a Prodigia).
            # - requiere_factura=False -> 'draft': remisión definitiva, nunca se timbra.
            # Mientras no tenga cfdi_uuid, el reporte la imprime como REMISIÓN en ambos casos.
            'cfdi_status': 'pending' if partner.requiere_factura else 'draft',
        }
        if method == 'by_branch' and first_sub.service_address_id:
            move_vals['partner_shipping_id'] = first_sub.service_address_id.id
        move = Move.create(move_vals)
        move.action_post()  # genera el saldo por cobrar

        # Envío de correo al GENERAR: SOLO remisiones (cliente NO requiere factura).
        # Los clientes que requieren FACTURA se envían DESPUÉS de timbrar (con el CFDI
        # pegado), vía account.move._cfdi_send_invoice_email() que dispara el cron de
        # auto-timbrado. Así el cliente nunca recibe el PDF sin timbre.
        # Se usa el MISMO método branded (logo + datos bancarios + QR Telegram + PDF) para
        # que remisión y factura se vean igual; el método ya maneja el CC interno.
        if any(s.auto_send_mail for s in subs_list) and partner.email and not partner.requiere_factura:
            try:
                move._cfdi_send_invoice_email()
            except Exception as e:
                _logger.warning("BILLING: remisión %s no se pudo enviar por correo: %s", move.name, e)

        for sub in subs_list:
            sub.next_billing_date = sub.next_billing_date + relativedelta(months=int(sub.recurring_interval))

        stamp_note = " (REQUIERE TIMBRADO → cfdi_status=pending)" if partner.requiere_factura else " (REMISIÓN, sin timbrar)"
        _logger.info(f"BILLING: Documento {move.name} publicado para {len(subs_list)} suscripción(es){stamp_note}")
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
        active_subs = self.search([('state', '=', 'active'), ('billing_mode', '!=', 'courtesy')])
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
        active_subs = self.search([('state', '=', 'active'), ('billing_mode', '!=', 'courtesy')])
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
        self._provision_flolive_enable()
        self._provision_senticar_enable()
        self.action_provision_mikrotik_enable()

    def action_suspend(self):
        self.write({
            'state': 'suspension',
            'technical_state': 'suspended',
            'technical_state_date': fields.Datetime.now()
        })
        self._provision_flolive_disable()
        self._provision_senticar_disable()
        self.action_provision_mikrotik_disable()

    def action_cancel(self):
        self.write({
            'state': 'cancelled',
            'technical_state': 'cut',
            'technical_state_date': fields.Datetime.now()
        })
        self._provision_flolive_disable()
        self._provision_senticar_disable()
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
        self._provision_flolive_enable()
        self._provision_senticar_enable()
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
        self.write({'ping_result': _('Ping a %s\n%s/%s recibidos · pérdida %s%%\nlatencia avg %s · max %s\n(%s)') % (
            target_ip, recv, sent, loss, avg, max_rtt, fields.Datetime.now())})
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Ping a %s') % target_ip,
                           'message': _('%s/%s recibidos · pérdida %s%% · latencia %s (max %s)') % (recv, sent, loss, avg, max_rtt),
                           'type': tipo, 'sticky': False}}

    def _nav_notif(self, msg, tipo):
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Diagnóstico de Navegación'), 'message': msg, 'type': tipo, 'sticky': True}}

    def action_validar_navegacion(self):
        """Diagnóstico REAL: ¿el cliente NAVEGA o solo está conectado al router?
        'Conectada' (sesión PPPoE) NO garantiza internet: un suspendido sigue conectado
        pero en walled-garden. Esto distingue de verdad leyendo el perfil del secret +
        el conntrack (conexiones a Internet CON datos de vuelta)."""
        self.ensure_one()
        if not self.router_id:
            raise UserError(_('Se requiere un router asignado.'))
        # Dedicada/empresarial (IP fija sobre el Balanceador, SIN PPPoE): se diagnostica
        # por IP fija leyendo el conntrack del router (solo lectura, no toca el enlace).
        if self.internet_mgmt_mode == 'static':
            return self._validar_navegacion_static()
        SUSPENDED_PROFILE = 'argusblack_servicio_suspendido'
        if not self.pppoe_user:
            raise UserError(_('Se requiere usuario PPPoE.'))
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            self.router_id.ip_address, username=self.router_id.api_user or 'gemini_api',
            password=self.router_id.api_password or '', port=int(self.router_id.api_port or 8728),
            plaintext_login=True)
        try:
            api = conn.get_api()
            # 1. ¿hay sesión PPPoE? (conectado al router)
            sess = api.get_resource('/ppp/active').get(name=self.pppoe_user)
            if not sess:
                verdict, tipo = '⚫ DESCONECTADO — sin sesión PPPoE en el router.', 'danger'
                conn.disconnect()
                self.write({'nav_status': verdict, 'nav_status_date': fields.Datetime.now()})
                self.message_post(body=_('🔎 <b>Validación de navegación:</b> %s') % verdict)
                return self._nav_notif(verdict, tipo)
            client_ip = sess[0].get('address', self.ip_address)
            # 2. ¿el secret está en perfil suspendido? (walled-garden = conecta pero NO navega)
            sec = api.get_resource('/ppp/secret').get(name=self.pppoe_user)
            profile = sec[0].get('profile') if sec else ''
            if profile == SUSPENDED_PROFILE:
                verdict = _('🔴 SUSPENDIDO — conectado al router pero en walled-garden (SIN internet). IP %s') % client_ip
                conn.disconnect()
                self.write({'nav_status': verdict, 'nav_status_date': fields.Datetime.now()})
                self.message_post(body=_('🔎 <b>Validación de navegación:</b> %s') % verdict)
                return self._nav_notif(verdict, 'warning')
            # 2.5 ¿la IP sigue en el address-list de bloqueo? El perfil del secret puede decir
            # "plan" pero la sesión viva o una entrada dinámica residual dejar la IP amurallada
            # por el firewall (el conntrack contaría las respuestas del propio walled-garden como
            # "datos de vuelta" → 🟢 falso). Verificamos el bloqueo REAL, no el perfil que debería.
            cip_only = str(client_ip).split(':')[0]
            blocked = api.get_resource('/ip/firewall/address-list').get(
                **{'list': SUSPENDED_PROFILE, 'address': cip_only})
            if not blocked:
                blocked = [e for e in api.get_resource('/ip/firewall/address-list').get(
                    **{'list': SUSPENDED_PROFILE}) if e.get('comment') == self.pppoe_user]
            if blocked:
                verdict = _('🔴 SUSPENDIDO — IP %s aún bloqueada en el firewall (walled-garden), pese al perfil. Reactiva el servicio para liberarla.') % client_ip
                conn.disconnect()
                self.write({'nav_status': verdict, 'nav_status_date': fields.Datetime.now()})
                self.message_post(body=_('🔎 <b>Validación de navegación:</b> %s') % verdict)
                return self._nav_notif(verdict, 'warning')
            # 3. conntrack: ¿tiene conexiones a Internet CON respuesta?
            def es_publica(ip):
                ip = (ip or '').split(':')[0]
                if not ip:
                    return False
                return not (ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('127.')
                            or any(ip.startswith('172.%d.' % n) for n in range(16, 32)))
            inet = con_datos = 0
            cip = str(client_ip)
            for c in api.get_resource('/ip/firewall/connection').get():
                src = c.get('src-address', '') or ''
                if src == cip or src.startswith(cip + ':'):
                    if es_publica(c.get('dst-address', '')):
                        inet += 1
                        if int(c.get('repl-bytes', 0) or 0) > 200:
                            con_datos += 1
            conn.disconnect()
            if con_datos > 0:
                verdict = _('🟢 NAVEGANDO — %d conexiones a Internet con datos de vuelta. IP %s') % (con_datos, client_ip)
                tipo = 'success'
            elif inet > 0:
                verdict = _('🟠 SOSPECHOSO — %d conexiones a Internet pero SIN respuesta (¿enlace caído / bloqueo?). IP %s') % (inet, client_ip)
                tipo = 'warning'
            else:
                verdict = _('🟡 CONECTADO, sin tráfico ahora — activo y NO bloqueado, pero no usa internet en este momento. IP %s') % client_ip
                tipo = 'info'
            self.write({'nav_status': verdict, 'nav_status_date': fields.Datetime.now()})
            self.message_post(body=_('🔎 <b>Validación de navegación:</b> %s') % verdict)
            return self._nav_notif(verdict, tipo)
        except UserError:
            try: conn.disconnect()
            except Exception: pass
            raise
        except Exception as e:
            try: conn.disconnect()
            except Exception: pass
            raise UserError(_('Error al validar navegación: %s') % e)

    def _validar_navegacion_static(self):
        """Diagnóstico para conexión DEDICADA/estática (IP fija sobre el Balanceador,
        sin PPPoE). No hay sesión PPPoE ni walled-garden: se lee la SIMPLE QUEUE de la
        IP fija (tabla chica, con tasa en vivo) para saber si el servicio está habilitado
        y si hay tráfico ahora. 100% lectura — no modifica NAT, queue ni nada del enlace.
        Además refresca el panel de tráfico en vivo con la tasa real de la queue."""
        self.ensure_one()
        if not self.ip_address:
            raise UserError(_('La suscripción dedicada no tiene IP fija asignada.'))
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            self.router_id.ip_address, username=self.router_id.api_user or 'gemini_api',
            password=self.router_id.api_password or '', port=int(self.router_id.api_port or 8728),
            plaintext_login=True)
        cip = str(self.ip_address)

        def mbps(v):
            try:
                return round(int(v) / 1000000.0, 2)
            except Exception:
                return 0.0
        try:
            api = conn.get_api()
            q = None
            for item in api.get_resource('/queue/simple').get():
                tgt = item.get('target', '') or ''
                if cip == tgt.split('/')[0] or cip in tgt:
                    q = item
                    break
            conn.disconnect()
            if not q:
                verdict = _('⚪ Sin queue dedicada para la IP %s en el Balanceador — no se puede diagnosticar por tasa.') % cip
                self.write({'nav_status': verdict, 'nav_status_date': fields.Datetime.now()})
                self.message_post(body=_('🔎 <b>Validación de navegación (dedicada):</b> %s') % verdict)
                return self._nav_notif(verdict, 'warning')
            # tasa en vivo de la queue: "subida/bajada" en bps
            rate = q.get('rate', '0/0') or '0/0'
            parts = (rate.split('/') + ['0', '0'])[:2]
            up, down = mbps(parts[0]), mbps(parts[1])
            qname = q.get('name', '') or '?'
            if (q.get('disabled') or 'false') == 'true':
                verdict = _('🔴 SUSPENDIDO — la queue dedicada «%s» está DESHABILITADA en el Balanceador (sin servicio). IP %s') % (qname, cip)
                tipo = 'warning'
                status_live = '🔴 Suspendido'
            elif down > 0 or up > 0:
                verdict = _('🟢 NAVEGANDO — tráfico en vivo ⬇ %s Mbps / ⬆ %s Mbps (queue «%s»). IP dedicada %s') % (down, up, qname, cip)
                tipo = 'success'
                status_live = '🟢 En línea'
            else:
                verdict = _('🟡 ENLACE ACTIVO, sin tráfico ahora — queue «%s» habilitada pero 0 Mbps en este instante. IP %s') % (qname, cip)
                tipo = 'info'
                status_live = '🟡 Sin tráfico'
            self.write({
                'nav_status': verdict, 'nav_status_date': fields.Datetime.now(),
                'live_traffic_status': status_live, 'live_traffic_ip': cip,
                'live_traffic_rx': '%s Mbps' % down, 'live_traffic_tx': '%s Mbps' % up,
                'live_traffic_updated': fields.Datetime.now(),
            })
            self.message_post(body=_('🔎 <b>Validación de navegación (dedicada):</b> %s') % verdict)
            return self._nav_notif(verdict, tipo)
        except UserError:
            try: conn.disconnect()
            except Exception: pass
            raise
        except Exception as e:
            try: conn.disconnect()
            except Exception: pass
            raise UserError(_('Error al validar navegación (dedicada): %s') % e)

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
        if self.connection_equipment != 'antenna_airos':
            label = dict(self._fields['connection_equipment'].selection).get(self.connection_equipment, 'este equipo')
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {
                    'title': _('Sin antena airOS'),
                    'message': _('Este servicio usa "%s": no tiene antena airOS para leer señal.') % label,
                    'type': 'warning', 'sticky': False,
                }
            }
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
        ok, sig, quality = self._apply_antenna_signal(ip, timeout=12, post=True)
        if not ok:
            raise UserError(_('No se pudo leer la antena %s: %s') % (ip, quality))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Señal: %s') % quality,
                           'message': _('%s dBm · %s') % (sig, quality),
                           'type': 'success' if (sig and sig >= -75) else 'warning', 'sticky': False}}

    def _apply_antenna_signal(self, ip, timeout=12, post=True):
        """SSH a la antena airOS en `ip`, lee mca-status y guarda los campos de señal.
        NO lanza: devuelve (ok, sig, quality_o_error). Reusado por el botón y el cron."""
        self.ensure_one()
        import paramiko, re
        airos_user = self.env['ir.config_parameter'].sudo().get_param('sentinela.airos_user', 'sentinela')
        airos_pwd = self.env['ir.config_parameter'].sudo().get_param('sentinela.airos_password', 'SentinelaW1sp')
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            cli.connect(ip, port=22, username=airos_user, password=airos_pwd, look_for_keys=False,
                        allow_agent=False, timeout=timeout,
                        disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']})
            _in, out, _err = cli.exec_command('mca-status')
            data = out.read().decode('utf-8', 'ignore')
            cli.close()
        except Exception as ex:
            try: cli.close()
            except Exception: pass
            return (False, 0, str(ex)[:120])
        d = {k: v.strip() for k, v in re.findall(r'(\w+)=([^,\r\n]+)', data)}
        try: sig = int(d.get('signal', 0) or 0)
        except Exception: sig = 0
        try: noise = int(d.get('noise', 0) or 0)
        except Exception: noise = 0
        snr = (sig - noise) if (sig and noise) else 0
        if sig == 0: quality = '❓ Sin datos'
        elif sig >= -65: quality = '🟢 Excelente'
        elif sig >= -75: quality = '🟢 Buena'
        elif sig >= -82: quality = '🟡 Regular'
        else: quality = '🔴 Mala (revisar antena)'
        self.write({
            'antenna_signal_dbm': '%s dBm' % sig,
            'antenna_snr': '%s dB' % snr,
            'antenna_signal_quality': quality,
            'antenna_link_rate': '%s / %s Mbps' % (d.get('wlanTxRate', '?'), d.get('wlanRxRate', '?')),
            'antenna_distance': '%s m' % d.get('distance', '?'),
            'antenna_signal_updated': fields.Datetime.now(),
        })
        if post:
            plat = d.get('platform', 'CPE')
            self.message_post(body=_('📡 <b>Señal de antena (%s):</b> %s dBm · SNR %s dB · %s · enlace %s/%s Mbps · %sm') % (
                plat, sig, snr, quality, d.get('wlanTxRate', '?'), d.get('wlanRxRate', '?'), d.get('distance', '?')))
        return (True, sig, quality)

    @api.model
    def _cron_refresh_antenna_signal(self):
        """Opción C: en segundo plano refresca el estado de conexión (online/IP) de los
        clientes de internet y la señal de antena airOS de los que estén en línea.
        Conexión = barato (1 consulta /ppp/active por router). Señal = SSH, en lotes
        (los más desactualizados primero) para no saturar."""
        import routeros_api
        BATCH_SSH = 25
        subs = self.search([('service_type', '=', 'internet'), ('state', '=', 'active'),
                            ('pppoe_user', '!=', False), ('router_id', '!=', False)])
        if not subs:
            return True
        live = {}
        for router in subs.mapped('router_id'):
            try:
                conn = routeros_api.RouterOsApiPool(
                    router.ip_address, username=router.api_user, password=router.api_password or '',
                    port=int(router.api_port or 8728), plaintext_login=True)
                api = conn.get_api()
                for a in api.get_resource('/ppp/active').get():
                    live[(router.id, a.get('name'))] = a.get('address')
                conn.disconnect()
            except Exception as e:
                _logger.warning("cron señal: no pude leer /ppp/active de %s: %s", router.ip_address, e)
        now = fields.Datetime.now()
        for s in subs:
            ip = live.get((s.router_id.id, s.pppoe_user))
            s.write({'conn_online': bool(ip), 'conn_live_ip': ip or False, 'conn_checked': now})
        self.env.cr.commit()  # transacción corta: persiste el estado de conexión antes del SSH lento
        ant = subs.filtered(lambda x: x.conn_online and x.connection_equipment == 'antenna_airos')
        ant = ant.sorted(lambda x: x.antenna_signal_updated or fields.Datetime.to_datetime('2000-01-01'))[:BATCH_SSH]
        done = 0
        for s in ant:
            ip = live.get((s.router_id.id, s.pppoe_user))
            if ip and s._apply_antenna_signal(ip, timeout=7, post=False)[0]:
                done += 1
                self.env.cr.commit()  # persiste cada lectura (no perder todo por un conflicto tardío)
        _logger.info("cron señal: %s subs conexión actualizada, %s señales leídas.", len(subs), done)
        return True

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
                    # NO reescribir el password de un secret existente: es lo que
                    # autentica el CPE en campo y puede no coincidir con el valor
                    # guardado en Odoo (datos heredados de la migración Argus, p.ej.
                    # cta0002 quedó '.cta0002' sin el punto final). Pisarlo aquí
                    # tumbaba al cliente al reactivarse (la sesión se reinicia abajo).
                    # La reactivación solo debe tocar perfil/estado.
                    secrets.set(
                        id=existing[0]['id'],
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

                # IP(s) de la(s) sesión(es) activas: las entradas del walled-garden son
                # DINÁMICAS y sin comment (las pone el perfil suspendido por dirección),
                # así que hay que limpiarlas por address, no solo por comment.
                active = api.get_resource('/ppp/active')
                active_sessions = active.get(name=sub.pppoe_user)
                active_ips = {s.get('address') for s in active_sessions if s.get('address')}

                # Quitar de address-list suspendidos: por comment Y por dirección (dinámicas)
                addr_list = api.get_resource('/ip/firewall/address-list')
                seen = set()
                entries = addr_list.get(**{'list': 'argusblack_servicio_suspendido', 'comment': sub.pppoe_user})
                for ip in active_ips:
                    entries += addr_list.get(**{'list': 'argusblack_servicio_suspendido', 'address': ip})
                for entry in entries:
                    if entry['id'] in seen:
                        continue
                    seen.add(entry['id'])
                    try:
                        addr_list.remove(id=entry['id'])
                    except Exception as ex:
                        _logger.warning("No se pudo quitar %s de suspendidos (sub %s): %s", entry.get('address'), sub.name, ex)

                # Cortar la sesión activa para que reconecte YA con el perfil del plan.
                # El perfil del secret solo se aplica al conectar; sin esto el cliente sigue
                # navegando sobre la sesión vieja con el perfil suspendido (walled-garden).
                for session in active_sessions:
                    try:
                        active.remove(id=session['id'])
                    except Exception as ex:
                        _logger.warning("No se pudo cortar sesión PPPoE %s (sub %s): %s", sub.pppoe_user, sub.name, ex)

                conn.disconnect()
                sub.message_post(body=f"<b>MikroTik:</b> Secret PPPoE <b>{sub.pppoe_user}</b> activado con perfil <b>{profile_name}</b> (sesión reiniciada para aplicar el perfil).")
            except Exception as e:
                try:
                    conn.disconnect()
                except Exception:
                    pass
                _logger.error("MikroTik enable error sub %s: %s", sub.name, e)
                sub.message_post(body=f"<b>MikroTik ERROR al activar:</b> {e}")

    def action_provision_mikrotik_disable(self):
        """Suspende SIN cortar la conexión: deja el secret PPPoE HABILITADO pero le cambia
        el perfil a 'argusblack_servicio_suspendido' (walled-garden). Así el CPE se conecta
        pero NO navega (el firewall lo bloquea y el NAT lo manda a la página de pago) y DEJA
        de golpear auth en bucle. Reactivar con action_provision_mikrotik_enable (vuelve al
        perfil del plan). Para borrar/cortar de raíz el equipo, hacerlo aparte."""
        SUSPENDED_PROFILE = 'argusblack_servicio_suspendido'
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

                # HABILITADO + perfil suspendido (walled-garden). NO se deshabilita: el CPE
                # conecta y deja de reintentar; el perfil suspendido etiqueta su IP en el
                # address-list 'argusblack_servicio_suspendido' que el firewall bloquea.
                secrets = api.get_resource('/ppp/secret')
                existing = secrets.get(name=sub.pppoe_user)
                if existing:
                    secrets.set(id=existing[0]['id'], disabled='false', profile=SUSPENDED_PROFILE)

                # Cortar la sesión activa para que reconecte ya con el perfil suspendido
                active = api.get_resource('/ppp/active')
                for session in active.get(name=sub.pppoe_user):
                    active.remove(id=session['id'])

                conn.disconnect()
                sub.message_post(body=f"<b>MikroTik:</b> Secret PPPoE <b>{sub.pppoe_user}</b> suspendido (perfil <b>{SUSPENDED_PROFILE}</b>): conecta pero no navega.")
            except Exception as e:
                try:
                    conn.disconnect()
                except Exception:
                    pass
                _logger.error("MikroTik disable error sub %s: %s", sub.name, e)
                sub.message_post(body=f"<b>MikroTik ERROR al suspender:</b> {e}")

    def _senticar_register_device(self, dev):
        """Registra UN equipo (renglón) en SentiCar y lo vincula a la cuenta del cliente.
        Idempotente. Reusa el usuario del cliente. Guarda dev.senticar_device_id."""
        sub = self
        svc = self.env['sentinela.senticar.service']
        if sub.gps_platform != 'senticar':
            raise UserError(_("La plataforma de la suscripción no es SentiCar (es %s).") % (sub.gps_platform or 'sin plataforma'))
        if not dev.gps_imei:
            raise UserError(_("El equipo '%s' no tiene IMEI / Device-ID.") % (dev.name or '?'))
        uid, pw = svc.ensure_client_user(sub.partner_id)
        name = f"{sub.partner_id.name} - {dev.name or dev.gps_imei}"
        did = svc.ensure_device(name, dev.gps_imei, user_id=uid)
        if did:
            dev.senticar_device_id = did
            svc.set_device_disabled(did, False)
            # Grupo del cliente: crear/recuperar, meter el equipo y compartir el grupo con el cliente.
            try:
                gid = svc.ensure_client_group(sub.partner_id)
                if gid:
                    svc.assign_device_to_group(did, gid)
                    if uid:
                        svc.share_group(uid, gid)
            except Exception as e:
                _logger.error("SENTICAR grupo (alta) sub %s dev %s: %s", sub.name, dev.id, e)
            dev.write({'senticar_state': 'registered', 'senticar_sync_msg': 'Registrado y activo',
                       'senticar_sync_date': fields.Datetime.now()})
            msg = f"<b>SentiCar:</b> equipo <b>{dev.name or dev.gps_imei}</b> ({dev.gps_imei}) registrado y activo (device #{did})."
            if pw:
                msg += f"<br/>👤 Usuario cliente creado: <b>{sub.partner_id.senticar_user_email}</b> / <b>{pw}</b>"
            sub.message_post(body=msg)
        else:
            dev.write({'senticar_state': 'error', 'senticar_sync_msg': 'No se pudo registrar en SentiCar',
                       'senticar_sync_date': fields.Datetime.now()})
            sub.message_post(body=f"<b>SentiCar ERROR:</b> no se pudo registrar el equipo {dev.gps_imei}.")

    def _provision_senticar_enable(self):
        """Registra/activa TODOS los equipos de la sub en SentiCar (recorre los renglones).
        Solo gps_platform='senticar'. Tracksolid/Smake (cerradas) se gestionan en su portal."""
        for sub in self:
            if sub.service_type != 'gps' or sub.gps_platform != 'senticar':
                continue
            for dev in sub.gps_device_ids:
                try:
                    sub._senticar_register_device(dev)
                except Exception as e:
                    _logger.error("SENTICAR enable sub %s dev %s: %s", sub.name, dev.id, e)
                    sub.message_post(body=f"<b>SentiCar ERROR</b> ({dev.name or dev.gps_imei}): {e}")

    def _provision_senticar_disable(self):
        """Deshabilita TODOS los equipos de la sub en SentiCar (suspensión/baja)."""
        svc = self.env['sentinela.senticar.service']
        for sub in self:
            if sub.service_type != 'gps' or sub.gps_platform != 'senticar':
                continue
            n = 0
            for dev in sub.gps_device_ids.filtered('senticar_device_id'):
                if svc.set_device_disabled(dev.senticar_device_id, True):
                    n += 1
                    dev.write({'senticar_state': 'disabled', 'senticar_sync_msg': 'Deshabilitado por suspensión/baja',
                               'senticar_sync_date': fields.Datetime.now()})
            if sub.gps_device_ids:
                sub.message_post(body=f"<b>SentiCar:</b> {n} equipo(s) deshabilitado(s) por suspensión.")

    # ---- Reconciliación Odoo ↔ SentiCar (P1 #6) ----
    def _senticar_reconcile_devices(self, devices):
        """Compara los equipos `devices` (gps platform=senticar) contra Traccar y deja el estado
        consistente. Detecta: equipos que faltan en SentiCar (→ error) y desajustes del flag
        'disabled' (Odoo activo ↔ SentiCar deshabilitado, o viceversa). Si el auto-arreglo está
        activo (param sentinela.senticar_reconcile_autoheal, default True), corrige el flag en
        SentiCar (reversible, no toca SIM ni borra nada; Odoo = fuente de verdad). Devuelve un
        resumen {checked, healed, drift, error}."""
        svc = self.env['sentinela.senticar.service']
        traccar = svc.list_devices()
        if traccar is None:
            _logger.warning("SENTICAR reconcile: no se pudo leer Traccar; abortado.")
            return None
        by_id = {d.get('id'): d for d in traccar}
        by_imei = {str(d.get('uniqueId')): d for d in traccar}
        autoheal = self.env['ir.config_parameter'].sudo().get_param(
            'sentinela.senticar_reconcile_autoheal', 'True') not in ('False', '0', 'false')
        now = fields.Datetime.now()
        res = {'checked': 0, 'healed': 0, 'drift': 0, 'error': 0, 'grouped': 0, 'matched_ids': set()}
        group_cache = {}     # partner_id -> group_id (evita recrear/leer por cada equipo)
        subtree_cache = {}   # group_id -> {grupo + sub-grupos} (para respetar la organización del cliente)
        for dev in devices:
            if dev.gps_platform != 'senticar':
                continue
            res['checked'] += 1
            sub = dev.subscription_id
            # Estado esperado en SentiCar: deshabilitado si la sub no está activa o el equipo
            # está suspendido temporalmente. Activo solo si todo está en marcha.
            expected_disabled = (sub.state != 'active') or (dev.device_state == 'suspended')
            tdev = by_id.get(dev.senticar_device_id) if dev.senticar_device_id else by_imei.get(str(dev.gps_imei or ''))
            if not tdev:
                # Solo es problema si esperábamos que estuviera (ya registrado o sub activa).
                if dev.senticar_device_id or sub.state == 'active':
                    dev.write({'senticar_state': 'error',
                               'senticar_sync_msg': 'No existe en SentiCar (re-registrar)',
                               'senticar_sync_date': now})
                    res['error'] += 1
                continue
            res['matched_ids'].add(tdev['id'])
            if dev.senticar_device_id != tdev['id']:
                dev.senticar_device_id = tdev['id']
            actual_disabled = bool(tdev.get('disabled'))
            if actual_disabled != expected_disabled:
                if autoheal and svc.set_device_disabled(tdev['id'], expected_disabled):
                    dev.write({'senticar_state': 'disabled' if expected_disabled else 'registered',
                               'senticar_sync_msg': 'Auto-corregido a %s' % ('deshabilitado' if expected_disabled else 'activo'),
                               'senticar_sync_date': now})
                    res['healed'] += 1
                else:
                    dev.write({'senticar_state': 'drift',
                               'senticar_sync_msg': 'SentiCar=%s, Odoo espera %s' % (
                                   'deshabilitado' if actual_disabled else 'activo',
                                   'deshabilitado' if expected_disabled else 'activo'),
                               'senticar_sync_date': now})
                    res['drift'] += 1
            else:
                dev.write({'senticar_state': 'disabled' if actual_disabled else 'registered',
                           'senticar_sync_msg': 'OK', 'senticar_sync_date': now})
            # Pertenencia al GRUPO del cliente (Fase 1). Solo si auto-arreglo activo: asegura el
            # grupo del cliente (caché por cliente), mete el equipo si no está, y comparte el grupo.
            if autoheal:
                pid = sub.partner_id.id
                if pid not in group_cache:
                    group_cache[pid] = svc.ensure_client_group(sub.partner_id) or 0
                gid = group_cache[pid]
                if gid:
                    # RESPETAR sub-grupos del cliente: solo re-agrupar si el equipo se salió del
                    # ÁRBOL del cliente (su grupo o cualquier sub-grupo anidado). Así el cliente
                    # puede organizar su flota en sub-grupos (Bombas, Trailers, Pipas…) y la
                    # reconciliación NO los aplana; solo jala equipos que quedaron fuera del árbol.
                    if gid not in subtree_cache:
                        subtree_cache[gid] = svc.group_descendants(gid)
                    if tdev.get('groupId') not in subtree_cache[gid]:
                        if svc.assign_device_to_group(tdev['id'], gid):
                            if sub.partner_id.senticar_user_id:
                                svc.share_group(sub.partner_id.senticar_user_id, gid)
                            res['grouped'] += 1
        return res

    def action_rotate_portal_link(self):
        """Botón: regenera el enlace del portal del transportista (invalida el anterior)."""
        self.ensure_one()
        self.partner_id.rotate_senticar_portal_token()
        self.message_post(body=_(
            "♻️ <b>Enlace del portal regenerado.</b> El anterior ya no sirve. Nuevo: %s"
        ) % (self.senticar_portal_url or '—'))

    def action_revoke_portal_link(self):
        """Botón: revoca el enlace del portal del transportista (lo deja sin acceso)."""
        self.ensure_one()
        self.partner_id.revoke_senticar_portal_token()
        self.message_post(body=_("🚫 <b>Enlace del portal revocado.</b> El link ya no da acceso."))

    def _cron_senticar_cleanup_shares(self):
        """Cron: borra de SentiCar los usuarios temporales (links de rastreo) ya vencidos."""
        n = self.env['sentinela.senticar.service'].cleanup_expired_temp_users()
        _logger.info("SENTICAR cleanup: %s usuario(s) temporal(es) de link de rastreo vencido(s) borrado(s).", n)

    def _cron_senticar_reconcile(self):
        """Cron: reconcilia TODOS los equipos GPS de SentiCar contra Traccar. Reporta huérfanos
        (devices en Traccar no ligados a ninguna sub: flota/demo/manuales) solo en el log."""
        devices = self.env['sentinela.subscription.gps.device'].search([('gps_platform', '=', 'senticar')])
        res = self._senticar_reconcile_devices(devices)
        if res is None:
            return
        traccar = self.env['sentinela.senticar.service'].list_devices() or []
        orphans = [d for d in traccar if d.get('id') not in res['matched_ids']]
        _logger.info("SENTICAR reconcile: %s revisados, %s auto-corregidos, %s agrupados, %s desincronizados, "
                     "%s error, %s en Traccar sin sub (flota/demo/manual).",
                     res['checked'], res['healed'], res['grouped'], res['drift'], res['error'], len(orphans))

    def action_reconcile_senticar(self):
        """Botón: reconcilia los equipos de ESTA suscripción contra SentiCar y reporta al chatter."""
        self.ensure_one()
        if self.service_type != 'gps' or self.gps_platform != 'senticar':
            raise UserError(_("Esta acción es solo para suscripciones GPS en SentiCar."))
        res = self._senticar_reconcile_devices(self.gps_device_ids)
        if res is None:
            raise UserError(_("No se pudo conectar con SentiCar para reconciliar. Revisa los parámetros de la API."))
        self.message_post(body=_(
            "🔄 <b>Reconciliación SentiCar:</b> %s revisados · %s auto-corregidos · %s agrupados · %s desincronizados · %s con error."
        ) % (res['checked'], res['healed'], res['grouped'], res['drift'], res['error']))

    def action_create_senticar_client_account(self):
        """Botón: crea SOLO la cuenta (usuario Traccar) del cliente en SentiCar, SIN equipos.
        Útil cuando los GPS todavía están en otra plataforma: deja la cuenta lista y los
        dispositivos se registran después (al activar la sub o con el botón de registro).
        Idempotente: si el cliente ya tiene cuenta (por senticar_user_id o por email), la reusa
        sin duplicar."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("La suscripción no tiene cliente."))
        if not self.partner_id.email:
            raise UserError(_("El cliente no tiene email. El email es el usuario de acceso a "
                              "SentiCar; captúralo primero en el contacto."))
        svc = self.env['sentinela.senticar.service']
        uid, pw = svc.ensure_client_user(self.partner_id)
        if not uid:
            raise UserError(_("No se pudo crear la cuenta en SentiCar (revisa la conexión y los "
                              "parámetros sentinela.traccar_api_url/user/password)."))
        portal = (self.env['ir.config_parameter'].sudo().get_param('sentinela.senticar_public_url')
                  or 'https://radar.senticar.com')
        if pw:
            self.message_post(body=_(
                "👤 <b>Cuenta SentiCar creada</b> para %s<br/>"
                "Usuario: <b>%s</b> · Contraseña: <b>%s</b><br/>Acceso: %s<br/>"
                "<i>Los equipos se registrarán después (siguen en otra plataforma).</i>"
            ) % (self.partner_id.name, self.partner_id.senticar_user_email, pw, portal))
        else:
            self.message_post(body=_(
                "👤 <b>Cuenta SentiCar</b>: %s ya tenía cuenta (usuario <b>%s</b>, id %s). Reusada.")
                % (self.partner_id.name, self.partner_id.senticar_user_email or self.partner_id.email, uid))
        return True

    def action_provision_senticar(self):
        """Botón: registra/activa en SentiCar TODOS los equipos de la suscripción (alta)."""
        self.ensure_one()
        if self.service_type != 'gps':
            raise UserError(_("Esta acción es solo para servicios GPS."))
        if self.gps_platform != 'senticar':
            raise UserError(_("La suscripción no está en SentiCar (es %s). El alta automática solo aplica a SentiCar.") % (self.gps_platform or 'sin plataforma'))
        if not self.gps_device_ids:
            raise UserError(_("Agrega al menos un equipo (renglón) en la pestaña GPS antes de registrar."))
        self._provision_senticar_enable()

    def _flolive_set_all(self, status):
        """Cambia el estado de las SIMs floLIVE que SÍ gestionamos:
        - alarm: la SIM de la sub (sub.sim_iccid).
        - gps modo VEHÍCULO: la SIM de cada equipo (renglón). El modo MÓVIL usa SIM del
          cliente → NUNCA se toca."""
        flo = self.env['sentinela.flolive.service']
        verb = 'suspendida' if status == 'SUSPENDED' else 're-activada'
        for sub in self:
            iccids = []
            if sub.service_type == 'alarm' and sub.sim_iccid:
                iccids = [sub.sim_iccid]
            elif sub.service_type == 'gps' and sub.gps_mode == 'vehiculo':
                iccids = [d.sim_iccid for d in sub.gps_device_ids if d.sim_iccid]
            for iccid in iccids:
                if flo.update_sim_status(iccid, status):
                    sub.message_post(body=f"<b>floLIVE:</b> SIM {iccid} {verb}.")
                else:
                    sub.message_post(body=f"<b>floLIVE ERROR:</b> SIM {iccid} no se pudo cambiar a {status}.")

    def _provision_flolive_disable(self):
        self._flolive_set_all('SUSPENDED')

    def _provision_flolive_enable(self):
        self._flolive_set_all('ACTIVE')

    def action_refresh_gps_diag(self):
        """Refresca el diagnóstico de la SIM del GPS desde floLIVE (solo lectura):
        estado, sesión de datos, última ubicación, red. Botón de la pestaña Diagnóstico GPS."""
        self.ensure_one()
        if self.service_type != 'gps':
            raise UserError(_("Esta acción es solo para servicios GPS."))
        if not self.sim_iccid:
            raise UserError(_("La suscripción no tiene ICCID de SIM capturado."))
        diag = self.env['sentinela.flolive.service'].get_sim_diagnostics(self.sim_iccid)
        if not diag.get('ok'):
            raise UserError(_("No se pudo obtener el diagnóstico de floLIVE. Revisa el ICCID y las credenciales API de Connecta."))
        self.write({
            'gps_sim_status': diag.get('status'),
            'gps_sim_online': diag.get('online'),
            'gps_sim_lat': str(diag['lat']) if diag.get('lat') is not None else False,
            'gps_sim_lon': str(diag['lon']) if diag.get('lon') is not None else False,
            'gps_sim_network': diag.get('network'),
            'gps_sim_last_session': diag.get('last_session'),
            'gps_sim_checked': fields.Datetime.now(),
        })
        self.message_post(body=_("📡 <b>Diagnóstico GPS actualizado:</b> SIM %s · %s · última ubicación %s, %s") % (
            diag.get('status'), 'en línea' if diag.get('online') else 'sin sesión',
            diag.get('lat'), diag.get('lon')))

    def action_send_gps_sms(self):
        """Envía el comando SMS capturado a la SIM del GPS vía Connecta/floLIVE.
        Andamiaje listo: si Connecta aún no habilita SMS, avisa claramente sin romper."""
        self.ensure_one()
        if self.service_type != 'gps':
            raise UserError(_("Esta acción es solo para servicios GPS."))
        if not self.sim_iccid:
            raise UserError(_("La suscripción no tiene ICCID de SIM capturado."))
        if not self.gps_sms_command:
            raise UserError(_("Escribe el comando SMS a enviar."))
        res = self.env['sentinela.flolive.service'].send_sms_command(
            self.sim_iccid, self.gps_sms_command, encoding=self.gps_sms_encoding or 'GSM-7')
        ts = fields.Datetime.now()
        mark = '✅' if res.get('ok') else '⚠️'
        line = f"[{ts}] {mark} ENVIAR «{self.gps_sms_command}» ({self.gps_sms_encoding or 'GSM-7'}) → {res.get('detail')}"
        self.gps_sms_log = (line + "\n" + (self.gps_sms_log or "")).strip()
        self.message_post(body=_("📨 <b>Comando SMS</b> «%s»: %s") % (self.gps_sms_command, res.get('detail')))
        if not res.get('ok'):
            # No truena: deja el aviso en bitácora/chatter (típico mientras Connecta no habilita SMS).
            return
        self.gps_sms_command = False

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
            # Al cambiar de Plan, la Tarifa Mensual se actualiza SIEMPRE al precio del nuevo plan.
            # (El usuario puede ajustarla manualmente después; si vuelve a cambiar de plan, se retoma la del plan.)
            sub.price_unit = sub.product_id.list_price
            if sub.product_id.default_recurring_interval and not sub.recurring_interval:
                sub.recurring_interval = sub.product_id.default_recurring_interval
            if sub.product_id.service_type and not sub.service_type:
                sub.service_type = sub.product_id.service_type
            # Prellenar Servicios Incluidos desde la matriz del plan.
            # Agrega SOLO los servicios faltantes (no sobreescribe), de modo que
            # al cambiar de plan en una sub existente aparezcan los nuevos servicios
            # del plan sin borrar los que ya tenía. Evita que el constraint
            # _check_service_inclusions_complete bloquee el guardado.
            matrix = self.env['sentinela.product.service.inclusion'].sudo().search([
                ('product_id', '=', sub.product_id.id),
            ])
            if matrix:
                existing_ids = set(sub.service_inclusion_ids.mapped('service_id.id'))
                SubInc = self.env['sentinela.subscription.service.inclusion']
                for row in matrix:
                    if row.service_id.id in existing_ids:
                        continue
                    sub.service_inclusion_ids += SubInc.new({
                        'service_id': row.service_id.id,
                        'is_included': row.is_included,
                        'extra_price': row.extra_price,
                    })

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

    def _assert_billing_mode_manager(self):
        """Candado: solo el Gestor de Suscripciones (o el sistema) cambia el Tipo de Facturación."""
        if self.env.su or self.env.user.has_group('sentinela_subscriptions.group_subscription_manager'):
            return
        raise AccessError(_(
            "Solo un administrador (Gestor de Suscripciones) puede cambiar el Tipo de Facturación "
            "(Normal / Cortesía)."))

    def write(self, vals):
        if 'billing_mode' in vals and any(rec.billing_mode != vals['billing_mode'] for rec in self):
            self._assert_billing_mode_manager()
        # Al cambiar de plan, deriva los servicios faltantes del NUEVO plan ANTES de
        # super().write(): el constraint _check_service_inclusions_complete se valida
        # dentro del write, así que agregarlos después llega tarde y bloquea el guardado.
        # Solo aplica si el caller no trae ya su propia lista de servicios.
        new_plan = vals.get('product_id')
        if new_plan and 'service_inclusion_ids' not in vals:
            rows = self.env['sentinela.product.service.inclusion'].sudo().search([
                ('product_id', '=', new_plan),
            ])
            if rows:
                SubInc = self.env['sentinela.subscription.service.inclusion'].sudo()
                for rec in self:
                    existing_ids = set(rec.service_inclusion_ids.mapped('service_id.id'))
                    for row in rows:
                        if row.service_id.id in existing_ids:
                            continue
                        SubInc.create({
                            'subscription_id': rec.id,
                            'service_id': row.service_id.id,
                            'is_included': row.is_included,
                            'extra_price': row.extra_price,
                        })
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        Matrix = self.env['sentinela.product.service.inclusion'].sudo()
        for vals in vals_list:
            if vals.get('billing_mode', 'normal') != 'normal':
                self._assert_billing_mode_manager()
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sentinela.subscription') or 'New'
            # Pre-derivar la matriz del plan EN vals (antes de super().create) para que
            # el constraint _check_service_inclusions_complete encuentre los services al
            # evaluarse. Si el caller ya pasó service_inclusion_ids, no se sobrescribe.
            product_id = vals.get('product_id')
            if product_id and not vals.get('service_inclusion_ids'):
                rows = Matrix.search([('product_id', '=', product_id)])
                if rows:
                    vals['service_inclusion_ids'] = [(0, 0, {
                        'service_id': row.service_id.id,
                        'is_included': row.is_included,
                        'extra_price': row.extra_price,
                    }) for row in rows]
        subs = super().create(vals_list)
        # Pase idempotente: garantiza inclusion records si algún caller inyectó
        # service_inclusion_ids parciales o si el plan se cambió en write posterior.
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
    is_advance_payment = fields.Boolean(
        string='Cobro Adelantado', default=False, copy=False,
        help="Marca esta factura como pago de meses por adelantado de una suscripción. "
             "Al publicarla, empuja la próxima fecha de cobro (next_billing_date) de la suscripción "
             "por el número de meses facturados. Funciona desde el botón de la suscripción o capturando "
             "la factura manualmente en Ventas (ligar la suscripción + facturar el producto del plan).")
    advance_months_applied = fields.Integer(
        string='Meses adelantados aplicados', default=0, copy=False, readonly=True,
        help="Meses por los que ya se empujó el ciclo (camino LEGACY mono-suscripción). "
             "Se usa para revertir exactamente si la factura se cancela.")
    # --- Cobro adelantado GLOBAL (metadatos explícitos; el avance NUNCA se lee de las líneas) ---
    advance_periods = fields.Integer(
        string='Ciclos adelantados', default=0, copy=False, readonly=True,
        help="Nº de CICLOS de cobro que adelanta esta factura (cobro adelantado global). Cada "
             "suscripción avanza advance_periods × su propio intervalo. Es la ÚNICA fuente del "
             "avance: el ciclo no se recalcula leyendo las líneas. >0 marca el adelanto global.")
    advance_detail = fields.Text(
        string='Detalle de adelanto (snapshot)', copy=False, readonly=True,
        help="JSON escrito al publicar: por cada suscripción {sub_id, sub, interval, periods, "
             "months, old_date, new_date}. Permite REVERTIR y AUDITAR la operación exactamente, "
             "sin reconstruirla desde las líneas de factura.")
    advance_executed_on = fields.Datetime(
        string='Adelanto ejecutado el', copy=False, readonly=True,
        help="Fecha/hora en que se aplicó el avance de ciclo (al publicar la factura).")
    advance_executed_by = fields.Many2one(
        'res.users', string='Adelanto ejecutado por', copy=False, readonly=True,
        help="Usuario que publicó la factura y disparó el avance de ciclo.")

    def _is_global_advance(self):
        """ True si este movimiento es un cobro adelantado GLOBAL del modelo nuevo, identificado
        por metadatos explícitos (advance_periods > 0), por oposición al adelanto LEGACY
        mono-suscripción que calcula meses leyendo las líneas. """
        self.ensure_one()
        return bool(self.is_advance_payment and self.advance_periods > 0)

    @api.model
    def _check_no_concurrent_global_advance(self, partner, subs):
        """ Bloqueo de negocio (decisión #5): impide cobros adelantados globales CONCURRENTES sobre
        las mismas suscripciones de un cliente. Bloquea si ya existe un adelanto global que comparte
        alguna sub y sigue EN CURSO, es decir:
          - en borrador (draft, aún sin publicar), o
          - publicado pero NO liquidado (payment_state ∉ paid/in_payment) → adeudo abierto, pendiente
            de cobrar o de revertir.
        Un adelanto ya pagado NO bloquea: el ciclo quedó en la nueva fecha y encadenar otro es válido.
        Las canceladas se ignoran (state != 'cancel'). """
        if not subs:
            return
        candidates = self.search([
            ('is_advance_payment', '=', True),
            ('advance_periods', '>', 0),
            ('partner_id', '=', partner.id),
            ('state', 'in', ('draft', 'posted')),
            ('subscription_ids', 'in', subs.ids),
        ])
        blockers = candidates.filtered(
            lambda m: m.state == 'draft' or m.payment_state not in ('paid', 'in_payment'))
        if blockers:
            overlap = (blockers.subscription_ids & subs).mapped('name')
            raise UserError(_(
                "Ya hay un cobro adelantado global EN CURSO para %s: %s.\n\n"
                "Comparte suscripciones con esta operación (%s) y aún no está liquidado. "
                "No se permiten dos adelantos concurrentes sobre las mismas suscripciones: "
                "cobra, cancela o revierte el adelanto existente antes de crear otro."
            ) % (partner.display_name,
                 ", ".join(blockers.mapped(lambda m: m.name or 'BORRADOR')),
                 ", ".join(overlap)))

    def _advance_subscription(self):
        """ Suscripción cuyo ciclo afecta este movimiento:
        - Factura de adelanto (out_invoice): su propia subscription_id.
        - Nota de crédito (out_refund) que revierte una factura de adelanto: la sub de la
          factura ORIGINAL (vía reversed_entry_id). Si es nota de crédito manual marcada
          como adelanto: su propia subscription_id. """
        self.ensure_one()
        if self.move_type == 'out_refund' and self.reversed_entry_id and self.reversed_entry_id.is_advance_payment:
            return self.reversed_entry_id.subscription_id
        return self.subscription_id

    def _advance_subscriptions(self):
        """ Recordset de TODAS las suscripciones cuyo ciclo afecta este movimiento (M2M
        `subscription_ids` ∪ Many2one `subscription_id` legacy). Para una nota de crédito que
        revierte un adelanto, las subs de la factura ORIGINAL. Generaliza `_advance_subscription`
        (singular) sin romper su contrato. """
        self.ensure_one()
        if self.move_type == 'out_refund' and self.reversed_entry_id and self.reversed_entry_id.is_advance_payment:
            orig = self.reversed_entry_id
            return orig.subscription_ids | orig.subscription_id
        return self.subscription_ids | self.subscription_id

    def _advance_direction(self):
        """ +1 = empuja el ciclo (factura de adelanto), -1 = lo regresa (nota de crédito de un
        adelanto legacy), 0 = este movimiento no afecta el ciclo. Considera tanto el M2M
        `subscription_ids` (global) como el Many2one `subscription_id` (legacy). """
        self.ensure_one()
        has_sub = bool(self.subscription_id or self.subscription_ids)
        if self.move_type == 'out_invoice' and self.is_advance_payment and has_sub:
            return 1
        if self.move_type == 'out_refund':
            orig = self.reversed_entry_id
            if orig and orig.is_advance_payment and (orig.subscription_id or orig.subscription_ids):
                return -1
            if self.is_advance_payment and has_sub:
                return -1
        return 0

    def _advance_plan_months(self, sub):
        """ Meses (suma de cantidades de las líneas del producto-plan de la sub) en ESTE move.
        Cobro adelantado de 6 meses → línea del plan con cantidad=6 → devuelve 6. En una nota
        de crédito total/parcial, devuelve los meses efectivamente acreditados. """
        self.ensure_one()
        if not sub:
            return 0
        plan_tmpl_id = sub.product_id.id
        months = 0
        for line in self.invoice_line_ids:
            if line.product_id and line.product_id.product_tmpl_id.id == plan_tmpl_id:
                months += int(round(line.quantity))
        return months

    def _advance_on_post(self):
        """ Al publicar empuja el ciclo de las suscripciones. Dos caminos:
        - GLOBAL (advance_periods > 0): cada sub avanza advance_periods × su intervalo. El cuánto
          sale de METADATOS explícitos, NUNCA de las líneas; se persiste un snapshot (advance_detail)
          para revertir/auditar sin reconstruir desde la factura.
        - LEGACY (mono-suscripción): conserva el cálculo histórico por líneas (incluye notas de
          crédito parciales/múltiples sobre adelantos legacy).
        Idempotente vía is_renewal_processed: una factura jamás adelanta dos veces aunque
        action_post se dispare de nuevo. Reversa PARCIAL sobre un adelanto global: PROHIBIDA en V1
        (la reversa de un global es total = cancelar la factura completa). """
        for move in self:
            direction = move._advance_direction()
            if not direction or move.is_renewal_processed:
                continue

            # 🚫 V1: ninguna nota de crédito (parcial o total) sobre un adelanto GLOBAL. La reversa
            # de un global es total y se hace cancelando la factura de adelanto completa.
            if direction < 0:
                orig = move.reversed_entry_id
                if orig and orig._is_global_advance():
                    raise UserError(_(
                        "Reversa parcial no soportada en esta versión.\n\n"
                        "La factura %s es un COBRO ADELANTADO GLOBAL. Para revertirlo, cancela la "
                        "factura de adelanto COMPLETA (Restablecer a borrador / Cancelar): eso "
                        "regresa el ciclo de TODAS sus suscripciones. Las notas de crédito sobre "
                        "adelantos globales no están permitidas en V1."
                    ) % (orig.name or orig.display_name))

            # --- Camino GLOBAL: avance por metadatos explícitos + snapshot ---
            if direction > 0 and move._is_global_advance():
                subs = move._advance_subscriptions()
                if not subs:
                    continue
                detail = []
                for sub in subs:
                    months = move.advance_periods * int(sub.recurring_interval or 1)
                    if months <= 0:
                        continue
                    old_date = sub.next_billing_date or fields.Date.today()
                    new_date = old_date + relativedelta(months=months)
                    sub.next_billing_date = new_date
                    detail.append({
                        'sub_id': sub.id, 'sub': sub.name,
                        'interval': int(sub.recurring_interval or 1),
                        'periods': move.advance_periods, 'months': months,
                        'old_date': str(old_date), 'new_date': str(new_date),
                    })
                    sub.message_post(body=_(
                        "💰 <b>Cobro adelantado global:</b> %s ciclo(s) (%s mes(es)) en %s. "
                        "Próxima renovación de <b>%s</b> a <b>%s</b>."
                    ) % (move.advance_periods, months, move.name or 'borrador', old_date, new_date))
                move.advance_detail = json.dumps(detail, ensure_ascii=False)
                move.advance_executed_on = fields.Datetime.now()
                move.advance_executed_by = move.env.user.id
                move.is_renewal_processed = True
                continue

            # --- Camino LEGACY (mono-suscripción, basado en líneas) ---
            sub = move._advance_subscription()
            if not sub:
                continue
            months = move._advance_plan_months(sub)
            original = move.reversed_entry_id if (direction < 0 and move.reversed_entry_id and move.reversed_entry_id.is_advance_payment) else False
            if direction < 0 and original:
                months = min(months, original.advance_months_applied)
            if months <= 0:
                continue
            old_date = sub.next_billing_date or fields.Date.today()
            sub.next_billing_date = old_date + relativedelta(months=direction * months)
            move.advance_months_applied = months
            move.advance_executed_on = fields.Datetime.now()
            move.advance_executed_by = move.env.user.id
            move.is_renewal_processed = True
            if direction < 0 and original:
                original.advance_months_applied -= months
            if direction > 0:
                sub.message_post(body=_(
                    "💰 <b>Cobro adelantado:</b> %s mes(es) facturados en %s. "
                    "Próxima renovación movida de <b>%s</b> a <b>%s</b>."
                ) % (months, move.name or 'borrador', old_date, sub.next_billing_date))
            else:
                sub.message_post(body=_(
                    "↩️ <b>Nota de crédito:</b> %s mes(es) acreditados en %s. "
                    "Próxima renovación regresa de <b>%s</b> a <b>%s</b>."
                ) % (months, move.name or 'borrador', old_date, sub.next_billing_date))

    def _advance_on_unpost(self):
        """ Al cancelar / regresar a borrador deshace EXACTAMENTE lo que este move aplicó:
        - GLOBAL: lee el snapshot (advance_detail) y regresa cada sub los meses que registró.
          Reversa TOTAL (todas las subs del snapshot), nunca recalcula desde las líneas ni
          depende del M2M actual (robusto si el grupo cambió después).
        - LEGACY: regresa el ciclo los meses de advance_months_applied (y, si es nota de crédito,
          le devuelve los meses a la factura original).
        Idempotente: solo actúa si is_renewal_processed; lo apaga al terminar, así una segunda
        cancelación/draft no vuelve a revertir. """
        for move in self:
            if not move.is_renewal_processed:
                continue

            # --- Camino GLOBAL: revertir desde el snapshot (reversa TOTAL) ---
            if move._is_global_advance():
                try:
                    detail = json.loads(move.advance_detail or '[]')
                except (ValueError, TypeError):
                    detail = []
                for entry in detail:
                    sub = move.env['sentinela.subscription'].browse(entry.get('sub_id')).exists()
                    months = int(entry.get('months') or 0)
                    if not sub or months <= 0:
                        continue
                    old_date = sub.next_billing_date or fields.Date.today()
                    sub.next_billing_date = old_date - relativedelta(months=months)
                    sub.message_post(body=_(
                        "🔄 <b>Adelanto global revertido</b> (%s cancelada/en borrador): se regresan "
                        "%s mes(es); próxima renovación ahora <b>%s</b>."
                    ) % (move.name or 'borrador', months, sub.next_billing_date))
                # Se conservan advance_detail/executed_* como bitácora de auditoría.
                move.is_renewal_processed = False
                continue

            # --- Camino LEGACY ---
            direction = move._advance_direction()
            if not direction:
                move.is_renewal_processed = False
                continue
            months = move.advance_months_applied
            if months <= 0:
                move.is_renewal_processed = False
                continue
            sub = move._advance_subscription()
            if not sub:
                continue
            old_date = sub.next_billing_date or fields.Date.today()
            # Deshacer = aplicar el signo contrario al que este move había usado.
            sub.next_billing_date = old_date - relativedelta(months=direction * months)
            if direction < 0 and move.reversed_entry_id and move.reversed_entry_id.is_advance_payment:
                move.reversed_entry_id.advance_months_applied += months
            move.advance_months_applied = 0
            move.is_renewal_processed = False
            sub.message_post(body=_(
                "🔄 <b>Ajuste de ciclo revertido</b> (%s cancelada/en borrador): "
                "próxima renovación ahora <b>%s</b>."
            ) % (move.name or 'borrador', sub.next_billing_date))

    def action_post(self):
        res = super().action_post()
        self._advance_on_post()
        return res

    def button_draft(self):
        self._advance_on_unpost()
        return super().button_draft()

    def button_cancel(self):
        self._advance_on_unpost()
        return super().button_cancel()

    def _compute_payment_state(self):
        """ Reactivación automática al pagar: cuando una factura de cliente ligada a una
        suscripción suspendida queda PAGADA (o en proceso de pago), reconecta el servicio
        solo (action_reactivate → perfil del plan en el router + sale de walled-garden).
        Idempotente: solo toca subs en technical_state='suspended', así que una vez
        reactivada las siguientes corridas del cómputo la ignoran. Cubre factura individual
        (subscription_id) y agrupada (subscription_ids). """
        res = super()._compute_payment_state()
        for move in self:
            if move.move_type != 'out_invoice' or move.payment_state not in ('paid', 'in_payment'):
                continue
            subs = (move.subscription_id | move.subscription_ids).filtered(
                lambda s: s.technical_state == 'suspended'
            )
            if subs:
                subs.action_reactivate()
                state_label = dict(move._fields['payment_state'].selection).get(move.payment_state)
                for sub in subs:
                    sub.message_post(body=_(
                        "💸 <b>Pago aplicado:</b> factura <b>%s</b> (%s) → servicio reconectado automáticamente."
                    ) % (move.name or 'borrador', state_label))
        return res
