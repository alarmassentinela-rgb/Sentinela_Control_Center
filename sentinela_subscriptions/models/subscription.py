from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
import logging
import base64

_logger = logging.getLogger(__name__)

class SentinelaSubscription(models.Model):
    _name = 'sentinela.subscription'
    _description = 'Subscription Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mail.render.mixin']
    _order = 'id desc'

    # --- Digital Contracts ---
    contract_content = fields.Html(string='Contenido del Contrato', copy=False, help="Contenido HTML renderizado del contrato específico para este cliente.")
    sign_document_ids = fields.One2many('sentinela.sign.document', 'res_id', string='Documentos de Firma', domain=[('res_model', '=', 'sentinela.subscription')])
    
    last_contract_pdf = fields.Binary(compute='_compute_last_contract', string='Último Contrato')
    last_contract_name = fields.Char()

    @api.depends('sign_document_ids.file', 'sign_document_ids.file_signed')
    def _compute_last_contract(self):
        for sub in self:
            last_doc = sub.sign_document_ids.sorted('create_date', reverse=True)[:1]
            if last_doc:
                sub.last_contract_pdf = last_doc.file_signed or last_doc.file
                sub.last_contract_name = last_doc.filename_signed or last_doc.filename
            else:
                sub.last_contract_pdf = False
                sub.last_contract_name = False

    def action_reset_contract_template(self):
        """ Fuerza la recarga de la plantilla desde el producto, borrando cambios manuales """
        self.ensure_one()
        if not self.product_id.contract_template_id:
             raise UserError(_("El producto seleccionado no tiene una plantilla vinculada."))
        
        try:
            rendered_content = self.env['mail.render.mixin']._render_template(
                self.product_id.contract_template_id.content,
                'sentinela.subscription',
                self.ids
            )[self.id]
        except Exception as e:
            # En lugar de lanzar UserError que bloquea la pantalla, mostramos el error en el campo
            # para que el usuario pueda ver qué falló y corregirlo en la plantilla.
            error_msg = f'''
                <div style="border: 5px solid red; padding: 20px; color: red; background: #fff0f0;">
                    <h3>⚠️ Error al cargar la plantilla maestra</h3>
                    <p>No se pudo procesar el diseño original debido a un error en el texto o las variables.</p>
                    <p><b>Detalle técnico:</b> {str(e)}</p>
                    <hr/>
                    <p><b>Acción sugerida:</b> Revise que los códigos entre llaves en la configuración de la plantilla sean correctos.</p>
                </div>
            '''
            self.contract_content = error_msg
            return False

        # Inyectar Logo de la Compañía (Base64 para evitar timeouts de wkhtmltopdf)
            logo = self.env.company.logo
            if logo:
                logo_b64 = logo.decode('utf-8')
                logo_html = f'<div style="text-align: center; margin-bottom: 5px;"><img src="data:image/png;base64,{logo_b64}" style="max-height: 80px;"/></div>'
                # Insertar al inicio del contenido
                rendered_content = logo_html + rendered_content

        except Exception as e:
            raise UserError(f"Error al renderizar la plantilla: {str(e)}")

        self.contract_content = rendered_content
        
        # Inyectar salto de página automático antes de las cláusulas de responsabilidad
        if self.contract_content:
            target_text = 'CLAUSULAS DE LIMITACION DE RESPONSABILIDAD'
            if target_text in self.contract_content:
                break_html = '<div class="page-break-before"></div>'
                self.contract_content = self.contract_content.replace(target_text, break_html + target_text)

    def action_generate_contract(self):
        self.ensure_one()
        
        # Auto-fix sequence if missing
        if self.name == 'New':
            self.name = self.env['ir.sequence'].next_by_code('sentinela.subscription') or 'SUB-0000'

        # Si el contenido está vacío, cargarlo primero
        if not self.contract_content:
            self.action_reset_contract_template()

        if 'Error al cargar la plantilla maestra' in (self.contract_content or ''):
            raise UserError("No se puede generar el contrato porque el diseño actual tiene errores. Por favor corrija la plantilla o el contenido primero.")

        # 2. Generar PDF usando el reporte QWeb (usará self.contract_content actual)
        pdf_content, dummy = self.env['ir.actions.report']._render_qweb_pdf(
            'sentinela_subscriptions.action_report_subscription_contract', 
            [self.id]
        )

        # 3. Crear Documento de Firma
        filename = f"Contrato_{self.name}_{self.partner_id.name}.pdf".replace('/', '_')
        sign_doc = self.env['sentinela.sign.document'].create({
            'name': f"Contrato {self.name}",
            'partner_id': self.partner_id.id,
            'file': base64.b64encode(pdf_content),
            'filename': filename,
            'res_model': 'sentinela.subscription',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Documento Generado',
            'res_model': 'sentinela.sign.document',
            'res_id': sign_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    
    def _compute_display_name(self):
        for sub in self:
            address = sub.service_address_id.street or sub.service_address_id.name or 'Sin Dirección'
            product = sub.product_id.name or 'Sin Plan'
            # Format: "Reference - Product (Address)" or just "Product (Address)" if Reference is New
            if sub.name and sub.name != 'New':
                sub.display_name = f"{sub.name} - {product} ({address})"
            else:
                sub.display_name = f"{product} ({address})"

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    invoice_grouping_method = fields.Selection(related='partner_id.invoice_grouping_method', string='Invoice Grouping', readonly=True)
    service_address_id = fields.Many2one('res.partner', string='Service Address (Branch)', 
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]",
        help="Physical location where service is provided. Can be the customer's main address or a specific branch.")
    
    # Address Details (Readonly)
    address_street = fields.Char(related='service_address_id.street', string='Street', readonly=True)
    address_street2 = fields.Char(related='service_address_id.street2', string='Street 2', readonly=True)
    address_city = fields.Char(related='service_address_id.city', string='City', readonly=True)
    address_state_id = fields.Many2one(related='service_address_id.state_id', string='State', readonly=True)
    address_zip = fields.Char(related='service_address_id.zip', string='ZIP', readonly=True)
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            if not self.service_address_id:
                self.service_address_id = self.partner_id
            return {'domain': {'service_address_id': ['|', ('id', '=', self.partner_id.id), ('parent_id', '=', self.partner_id.id)]}}
        else:
            self.service_address_id = False
            return {'domain': {'service_address_id': []}}
    
    # --- Service Details ---
    product_id = fields.Many2one('product.product', string='Service Plan', required=True, domain="[('is_subscription', '=', True)]")
    price_unit = fields.Float(string='Monthly Fee (Excl. Tax)', required=True, tracking=True)
    price_total = fields.Float(string='Total Mensual (Neto)', compute='_compute_price_total', store=True)
    
    @api.depends('price_unit', 'product_id')
    def _compute_price_total(self):
        for sub in self:
            taxes = sub.product_id.taxes_id
            if taxes:
                tax_res = taxes.compute_all(sub.price_unit, quantity=1, currency=sub.currency_id, product=sub.product_id, partner=sub.partner_id)
                sub.price_total = tax_res['total_included']
            else:
                sub.price_total = sub.price_unit

    service_type = fields.Selection([
        ('internet', 'Internet WISP'),
        ('alarm', 'Monitoreo de Alarma'),
        ('gps', 'Rastreo GPS'),
        ('maintenance', 'Póliza de Mantenimiento')
    ], string='Tipo de Servicio', required=True)
    
    ip_address = fields.Char(string='Dirección IP', help="IP estática para integración MikroTik")

    # --- Alarm / Equipment Details ---
    equipment_brand = fields.Char(string='Marca del Equipo')
    equipment_model = fields.Char(string='Modelo del Equipo')
    equipment_serial = fields.Char(string='Número de Serie')
    monitoring_account_number = fields.Char(string='Número de Cuenta (Monitoreo)', help="Código de cuenta para la Central de Monitoreo")
    
    # --- Nuevo Motor de Cobranza Flexible ---
    current_period_start = fields.Date(string='Inicio del Periodo', help="Fecha de inicio del periodo actual de servicio")
    current_period_end = fields.Date(string='Fin del Periodo', help="Fecha de fin del periodo actual de servicio")

    invoice_gen_type = fields.Selection([
        (str(i), f'{i} días antes' if i > 0 else 'Inicio del periodo') for i in range(31)
    ], string='Crear Factura', default='5', help="Días de anticipación para generar la factura antes del inicio del periodo")

    payment_due_type = fields.Selection([
        (str(i), f'{i} días después' if i > 0 else 'Mismo día') for i in range(16)
    ], string='Fecha de Pago', default='0', help="Días de gracia después del fin del periodo para realizar el pago")

    service_cut_type = fields.Selection([
        (str(i), f'{i} días después' if i > 0 else 'Mismo día') for i in range(16)
    ], string='Corte del Servicio', default='3', help="Días después del vencimiento del pago para suspender el servicio")

    # --- Billing Cycle (Mantenemos next_billing_date como la fecha en que DEBE iniciar el siguiente ciclo) ---
    start_date = fields.Date(string='Fecha de Contratación', default=fields.Date.today, required=True)
    next_billing_date = fields.Date(string='Próximo Inicio de Periodo', required=True, tracking=True)
    recurring_interval = fields.Selection([
        ('1', 'Mensual'),
        ('2', 'Bimestral'),
        ('3', 'Trimestral'),
        ('6', 'Semestral'),
        ('12', 'Anual')
    ], string='Ciclo de Facturación', default='1', required=True)
    
    # --- Contract & Equipment ---
    is_forced_contract = fields.Boolean(string='Forced Contract Term?', default=False)
    commitment_period = fields.Integer(string='Commitment (Months)', default=12, help="Forced contract duration.")
    commitment_end_date = fields.Date(string='Commitment End', compute='_compute_commitment_end', store=True)
    penalty_amount = fields.Float(string='Penalización por Cancelación Anticipada', help="Monto a cobrar si se cancela antes del fin del contrato.")
    equipment_replacement_cost = fields.Float(string='Costo de Reposición de Equipo', default=2500.0, help="Monto a cobrar si el equipo no es devuelto o se daña.")
    
    equipment_ownership = fields.Selection([
        ('company', 'Propiedad de la Empresa (Comodato)'),
        ('customer', 'Propiedad del Cliente'),
        ('leasing', 'Arrendamiento (Renta con opción a compra)')
    ], string='Propiedad del Equipo', default='company')
    
    plan_after_leasing_id = fields.Many2one('product.product', string='Plan al terminar renta', 
        domain="[('is_subscription', '=', True)]",
        help="Plan al que cambiará automáticamente la suscripción cuando termine el plazo forzoso.")

    is_contract_locked = fields.Boolean(compute='_compute_is_contract_locked', string='UI Locked')
    can_edit_plan = fields.Boolean(compute='_compute_can_edit_plan', string='Puede Editar Plan')

    def _compute_can_edit_plan(self):
        is_admin = self.env.user.has_group('base.group_system')
        for sub in self:
            sub.can_edit_plan = is_admin

    @api.depends('equipment_ownership')
    def _compute_is_contract_locked(self):
        is_admin = self.env.user.has_group('base.group_system')
        for sub in self:
            if sub.equipment_ownership == 'company' and not is_admin:
                sub.is_contract_locked = True
            else:
                sub.is_contract_locked = False

    serial_number_id = fields.Many2one('stock.lot', string='Equipment Serial', domain="[('product_id', '=', product_id)]")
    
    # --- Status ---
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], string='Contract Status', default='draft', tracking=True)
    
    technical_state = fields.Selection([
        ('active', 'Activo / En Línea'),
        ('suspended', 'Suspendido (Falta de Pago)'),
        ('cut', 'Corte Definitivo / Retirado')
    ], string='Technical Status', default='active', tracking=True)
    
    technical_state_date = fields.Datetime(string='Estado Técnico Desde', default=fields.Datetime.now, readonly=True)
    extension_end_date = fields.Datetime(string='Fin de Prórroga', readonly=True, help="Fecha y hora en que termina la prórroga temporal.")

    description = fields.Html(string='Internal Notes')
    
    # --- Technical Location ---
    location_notes = fields.Text(string='Location References (Croquis)', help="Notes on how to find the exact installation point.")
    latitude = fields.Char(string='Latitude')
    longitude = fields.Char(string='Longitude')
    
    # --- Internet WISP (PPPoE & Router) ---
    router_id = fields.Many2one('sentinela.router', string='Mikrotik Router', help="Router that manages this connection.")
    pppoe_user = fields.Char(string='PPPoE User', help="Username for authentication (e.g. cta1234)")
    pppoe_password = fields.Char(string='PPPoE Password')
    
    edit_pppoe_locked = fields.Boolean(default=True, string='Lock PPPoE Fields') # Control UI
    edit_plan_locked = fields.Boolean(default=True, string='Lock Plan Fields') # Control UI
    
    is_new_record = fields.Boolean(compute='_compute_is_new_record')

    @api.depends('name') # Algún campo que cambie
    def _compute_is_new_record(self):
        for rec in self:
            # En Odoo 18, rec.id puede ser un NewId. 
            # La forma mas segura es checar si existe en la DB (_origin)
            rec.is_new_record = not rec._origin.id
    
    # --- Monitoring Devices (Alarm) ---

    # --- Automations ---
    def action_recalculate_dates(self):
        """ Re-calcula periodos y fechas de gracia para registros migrados """
        for sub in self:
            if not sub.next_billing_date:
                continue
            
            interval = int(sub.recurring_interval or 1)
            # Si no hay fin de periodo, es el dia antes de la proxima factura
            if not sub.current_period_end:
                sub.current_period_end = sub.next_billing_date - timedelta(days=1)
            
            # Si no hay inicio de periodo, es el fin menos el intervalo
            if not sub.current_period_start:
                sub.current_period_start = sub.current_period_end - relativedelta(months=interval) + timedelta(days=1)
            
            # Forzar el calculo de fechas de gracia
            sub._compute_flexible_dates()
            sub.message_post(body="AUDITORÍA: Fechas de periodo y cobranza sincronizadas automáticamente.")

    def toggle_pppoe_lock(self):
        for rec in self:
            rec.edit_pppoe_locked = not rec.edit_pppoe_locked

    def toggle_plan_lock(self):
        for rec in self:
            rec.edit_plan_locked = not rec.edit_plan_locked

    @api.onchange('router_id')
    def _onchange_router_id(self):
        if self.router_id and not self.pppoe_user:
            seq = self.router_id.next_pppoe_sequence
            prefix = self.router_id.pppoe_prefix or 'cta'
            self.pppoe_user = f"{prefix}{seq}"
            self.pppoe_password = f".{prefix}{seq}"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sentinela.subscription') or 'New'
            
            # Inicializar periodos si no vienen (Importante para Miriam y nuevos registros)
            if vals.get('next_billing_date') and vals.get('recurring_interval'):
                next_date = fields.Date.from_string(vals['next_billing_date'])
                interval = int(vals['recurring_interval'])
                if not vals.get('current_period_end'):
                    vals['current_period_end'] = next_date - timedelta(days=1)
                if not vals.get('current_period_start'):
                    vals['current_period_start'] = vals['current_period_end'] - relativedelta(months=interval) + timedelta(days=1)

            if vals.get('router_id') and vals.get('pppoe_user'):
                router = self.env['sentinela.router'].browse(vals['router_id'])
                expected_user = f"{router.pppoe_prefix}{router.next_pppoe_sequence}"
                if vals['pppoe_user'] == expected_user:
                    router.write({'next_pppoe_sequence': router.next_pppoe_sequence + 1})
        return super().create(vals_list)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price
            if hasattr(self.product_id, 'default_recurring_interval') and self.product_id.default_recurring_interval:
                self.recurring_interval = self.product_id.default_recurring_interval

    def write(self, vals):
        # Campos críticos que invalidan el contrato
        critical_fields = ['product_id', 'price_unit', 'start_date', 'service_address_id', 'recurring_interval']
        if any(field in vals for field in critical_fields):
            for sub in self:
                # 1. Limpiar visualización actual
                vals['contract_content'] = False
                
                # 2. Gestionar documentos existentes
                docs = sub.sign_document_ids
                draft_docs = docs.filtered(lambda d: d.state in ['draft', 'sent'])
                signed_docs = docs.filtered(lambda d: d.state == 'signed')
                
                # Cancelar borradores obsoletos
                if draft_docs:
                    draft_docs.write({'state': 'cancel'})
                    sub.message_post(body=_("El contrato borrador ha sido cancelado automáticamente debido a cambios en las condiciones del servicio."))
                
                # Advertir si hay firmados
                if signed_docs:
                    sub.message_post(body=_("⚠️ ATENCIÓN: Se han modificado condiciones críticas (Plan/Precio) pero existe un contrato firmado vigente. Se recomienda generar un nuevo contrato y solicitar firma."))

        return super(SentinelaSubscription, self).write(vals)

    @api.onchange('pppoe_user')
    def _onchange_pppoe_user(self):
        if self.pppoe_user and not self.pppoe_password:
            self.pppoe_password = f".{self.pppoe_user}"

    @api.onchange('equipment_ownership')
    def _onchange_equipment_ownership(self):
        if self.equipment_ownership == 'company':
            self.is_forced_contract = True
            if self.commitment_period < 12:
                self.commitment_period = 12
        elif self.equipment_ownership == 'leasing':
            self.is_forced_contract = True
        else:
            pass

    def action_monitor_traffic(self):
        self.ensure_one()
        if not self.pppoe_user:
            raise UserError("No hay usuario PPPoE asignado.")
        wizard = self.env['sentinela.mikrotik.traffic'].create({
            'user': self.pppoe_user,
            'subscription_id': self.id,
            'status': 'Consultando...',
            'current_ip': '...',
            'rx_speed': '...',
            'tx_speed': '...'
        })
        return wizard.action_refresh()

    # --- Financials ---
    invoice_ids = fields.One2many('account.move', 'subscription_id', string='Invoices')
    sale_order_ids = fields.One2many('sale.order', 'subscription_id', string='Cotizaciones / Ordenes')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # --- Computed Fields ---
    payment_due_date = fields.Date(string='Fecha Límite de Pago', compute='_compute_flexible_dates', store=True)
    service_cut_date = fields.Date(string='Fecha de Corte', compute='_compute_flexible_dates', store=True)

    @api.depends('current_period_end', 'payment_due_type', 'service_cut_type')
    def _compute_flexible_dates(self):
        for sub in self:
            if sub.current_period_end:
                # Fecha de Pago: X días después del FIN del periodo
                due_days = int(sub.payment_due_type or 0)
                sub.payment_due_date = sub.current_period_end + timedelta(days=due_days)
                
                # Fecha de Corte: X días después de la Fecha de Pago
                cut_days = int(sub.service_cut_type or 0)
                sub.service_cut_date = sub.payment_due_date + timedelta(days=cut_days)
            else:
                sub.payment_due_date = False
                sub.service_cut_date = False

    @api.onchange('start_date', 'next_billing_date', 'recurring_interval')
    def _onchange_billing_dates(self):
        if self.next_billing_date and self.recurring_interval:
            interval = int(self.recurring_interval)
            # El periodo actual termina un día antes del siguiente inicio de facturación
            self.current_period_end = self.next_billing_date - timedelta(days=1)
            # El inicio del periodo actual es el fin menos el intervalo (aprox)
            self.current_period_start = self.current_period_end - relativedelta(months=interval) + timedelta(days=1)

    @api.depends('start_date', 'commitment_period', 'is_forced_contract')
    def _compute_commitment_end(self):
        for sub in self:
            if sub.is_forced_contract and sub.start_date and sub.commitment_period:
                sub.commitment_end_date = sub.start_date + relativedelta(months=sub.commitment_period)
            else:
                sub.commitment_end_date = False

    def action_open_google_maps(self):
        self.ensure_one()
        if self.latitude and self.longitude:
            url = f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }
        else:
            raise UserError(_("No GPS coordinates set for this subscription."))

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cotizaciones de Suscripción',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id, 'default_partner_id': self.partner_id.id}
        }

    def action_quote_reconnection(self):
        """ Revives a cancelled sub by creating a Reconnection Quote (Admin Only) """
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise UserError("Solo un administrador puede reactivar contratos cancelados.")
            
        SaleOrder = self.env['sale.order']
        # Find Reconnection Product
        reconnection_product = self.env.ref('sentinela_subscriptions.product_service_reconnection', raise_if_not_found=False)
        
        today = fields.Date.today()
        so_vals = {
            'partner_id': self.partner_id.id,
            'subscription_id': self.id,
            'origin': f"Reactivación de {self.name}",
            'require_signature': False, # Skip signature to speed up
            'require_payment': True,    # Force payment button
            'order_line': []
        }
        
        # Line 1: Reconnection Fee
        if reconnection_product:
            so_vals['order_line'].append((0, 0, {
                'product_id': reconnection_product.id,
                'name': reconnection_product.name,
                'product_uom_qty': 1,
                'price_unit': reconnection_product.list_price,
            }))
            
        # Line 2: First Month of Service
        so_vals['order_line'].append((0, 0, {
            'product_id': self.product_id.id,
            'name': f"Reactivación: {self.product_id.name} (Mes Adelantado)",
            'product_uom_qty': 1,
            'price_unit': self.price_unit,
        }))
        
        so = SaleOrder.create(so_vals)
        
        # Reset Subscription to Draft so it can be 'activated' again
        self.write({
            'state': 'draft',
            'technical_state_date': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cotización de Reconexión',
            'res_model': 'sale.order',
            'res_id': so.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_request_transfer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Solicitar Cambio de Domicilio',
            'res_model': 'sentinela.subscription.transfer',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id}
        }

    def action_suspend_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmar Motivo de Suspensión',
            'res_model': 'sentinela.subscription.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_action_type': 'suspend'
            }
        }

    def action_cancel_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmar Motivo de Cancelación',
            'res_model': 'sentinela.subscription.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_action_type': 'cancel'
            }
        }

    def action_activate(self):
        self.write({
            'state': 'active', 
            'technical_state': 'active',
            'technical_state_date': fields.Datetime.now()
        })
        # 1. Internet (MikroTik)
        self.action_provision_mikrotik_enable()
        # 2. Alarm (Monitoring Device)
        #     _logger.info(f"MONITORING: Activated device {device.name} for subscription {self.name}")

    def action_suspend(self):
        self.write({
            'technical_state': 'suspended',
            'technical_state_date': fields.Datetime.now()
        })
        # 1. Internet (MikroTik)
        self.action_provision_mikrotik_disable()
        # 2. Alarm (Monitoring Device)
        #     # We treat suspension as inactivation for the monitoring station logic
        #     _logger.info(f"MONITORING: Suspended device {device.name} for subscription {self.name}")

    def action_cancel(self):
        for sub in self:
            if sub.commitment_end_date and sub.commitment_end_date > fields.Date.today():
                message = _("Warning: Cancelling before commitment end date (%s). Check for penalties.") % sub.commitment_end_date
                sub.message_post(body=message)
        self.write({
            'state': 'cancelled', 
            'technical_state': 'cut',
            'technical_state_date': fields.Datetime.now()
        })
        # 1. Internet (MikroTik)
        self.action_provision_mikrotik_disable()
        # 2. Alarm (Monitoring Device)
        #     _logger.info(f"MONITORING: Cancelled device {device.name} for subscription {sub.name}")

    def _get_mikrotik_api(self):
        self.ensure_one()
        if not self.router_id:
            return None
        import routeros_api
        connection = routeros_api.RouterOsApiPool(
            self.router_id.ip_address,
            username=self.router_id.api_user,
            password=self.router_id.api_password or '',
            port=self.router_id.api_port,
            plaintext_login=True
        )
        return connection

    def action_provision_mikrotik_enable(self):
        for sub in self:
            if sub.service_type != 'internet' or not sub.router_id or not sub.pppoe_user:
                continue
            
            # Master Switch Check
            if not sub.router_id.sync_active:
                _logger.info(f"MIKROTIK: Skipping sync for {sub.name} (Router sync disabled)")
                continue

            pool = sub._get_mikrotik_api()
            try:
                api = pool.get_api()
                profile_record = sub.product_id.mikrotik_profile_id
                profile_name = profile_record.name or 'default'
                if profile_record:
                    rate_limit_str = f"{profile_record.upload_speed}M/{profile_record.download_speed}M"
                    prof_resource = api.get_resource('/ppp/profile')
                    existing_prof = prof_resource.get(name=profile_name)
                    prof_params = {
                        'name': profile_name,
                        'rate-limit': rate_limit_str,
                        'comment': f"Synced by Odoo: {sub.product_id.name}"
                    }
                    if profile_record.local_address: prof_params['local-address'] = profile_record.local_address
                    if profile_record.remote_address: prof_params['remote-address'] = profile_record.remote_address
                    if existing_prof: prof_resource.set(id=existing_prof[0]['id'], **prof_params)
                    else: prof_resource.add(**prof_params)

                resource = api.get_resource('/ppp/secret')
                existing = resource.get(name=sub.pppoe_user)
                params = {
                    'name': sub.pppoe_user,
                    'password': sub.pppoe_password or '',
                    'service': 'pppoe',
                    'profile': profile_name,
                    'comment': f"Odoo Sub: {sub.name}",
                    'disabled': 'no'
                }
                if existing:
                    resource.set(id=existing[0]['id'], **params)
                    _logger.info(f"MIKROTIK: Updated secret {sub.pppoe_user}")
                else:
                    resource.add(**params)
                    _logger.info(f"MIKROTIK: Created new secret {sub.pppoe_user}")
                
                active_resource = api.get_resource('/ppp/active')
                active_conn = active_resource.get(name=sub.pppoe_user)
                if active_conn:
                    active_resource.remove(id=active_conn[0]['id'])
                    _logger.info(f"MIKROTIK: Kicked user {sub.pppoe_user} to apply profile.")
                pool.disconnect()
            except Exception as e:
                raise UserError(f"Error Mikrotik: {str(e)}")

    def action_provision_mikrotik_disable(self):
        for sub in self:
            if sub.service_type != 'internet' or not sub.router_id or not sub.pppoe_user:
                continue
            
            # Master Switch Check
            if not sub.router_id.sync_active:
                _logger.info(f"MIKROTIK: Skipping sync disable for {sub.name} (Router sync disabled)")
                continue

            pool = sub._get_mikrotik_api()
            try:
                api = pool.get_api()
                resource = api.get_resource('/ppp/secret')
                existing = resource.get(name=sub.pppoe_user)
                if existing:
                    resource.set(id=existing[0]['id'], profile='profile-corte', disabled='no')
                    _logger.info(f"MIKROTIK: Suspended user {sub.pppoe_user} (Moved to profile-corte)")
                
                active_resource = api.get_resource('/ppp/active')
                active_conn = active_resource.get(name=sub.pppoe_user)
                if active_conn:
                    active_resource.remove(id=active_conn[0]['id'])
                    _logger.info(f"MIKROTIK: Terminated active session for {sub.pppoe_user} to apply suspension.")
                pool.disconnect()
            except Exception as e:
                _logger.error(f"MIKROTIK ERROR: {str(e)}")

    def action_renew_service(self):
        for sub in self:
            today = fields.Date.today()
            interval = int(sub.recurring_interval)
            
            # Limpiar prórroga si existe (ya pagó o renovó)
            if sub.extension_end_date:
                sub.extension_end_date = False
                
            if sub.next_billing_date and sub.next_billing_date >= today:
                new_date = sub.next_billing_date + relativedelta(months=interval)
                sub.message_post(body=f"Renovación Anticipada/Puntual: Vencimiento extendido de {sub.next_billing_date} a {new_date}")
                sub.next_billing_date = new_date
            else:
                new_date = today + relativedelta(months=interval)
                sub.message_post(body=f"Renovación Tardía: Ciclo reiniciado. Nuevo vencimiento: {new_date}")
                sub.next_billing_date = new_date
            
            # Allow reactivation from both 'suspended' and 'cut' states
            if sub.technical_state in ['suspended', 'cut']:
                sub.action_activate()
                sub.message_post(body="Servicio reactivado automáticamente por renovación.")

    def apply_extension(self, days, reason):
        """ Otorga servicio temporal sin mover fechas de cobro """
        self.ensure_one()
        
        if self.service_type != 'internet':
            raise UserError(_("La prórroga solo está disponible para servicios de Internet."))
            
        if self.extension_end_date:
            raise UserError(_("Este contrato ya tiene una prórroga activa. Debe esperar a que venza o se pague."))

        end_date = fields.Datetime.now() + timedelta(days=days)
        self.write({
            'extension_end_date': end_date,
            'technical_state': 'active', # Reactivar visualmente
            'technical_state_date': fields.Datetime.now()
        })
        # Reactivar en MikroTik
        self.action_provision_mikrotik_enable()
        
        # Enviar Notificación por Correo
        template = self.env.ref('sentinela_subscriptions.mail_template_subscription_extension', raise_if_not_found=False)
        if template:
            self.message_post_with_source(
                template,
                email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
            )
        else:
            self.message_post(body=f"PRÓRROGA OTORGADA: {days} días. Vence: {end_date}. Motivo: {reason} (No se envió correo: Plantilla no encontrada)")

    def _cron_check_expired_extensions(self):
        """ Busca prórrogas vencidas y suspende el servicio """
        now = fields.Datetime.now()
        expired_subs = self.search([
            ('technical_state', '=', 'active'),
            ('extension_end_date', '!=', False),
            ('extension_end_date', '<', now)
        ])
        for sub in expired_subs:
            _logger.info(f"EXTENSION EXPIRED: Suspending {sub.name}")
            sub.action_suspend()
            sub.message_post(body="PRÓRROGA VENCIDA: Servicio suspendido automáticamente.")
            sub.write({'extension_end_date': False}) # Limpiar para evitar re-procesamiento infinito

    # --- Cron 1: Pre-Generate Sale Orders (5 days before) ---
    def _cron_generate_pre_invoices(self):
        """ Genera cotizaciones basadas en la configuración personalizada de cada suscripción """
        today = fields.Date.today()
        
        # 1. Buscar todas las suscripciones activas (Ya no filtramos por fecha fija aquí)
        active_subs = self.search([('state', '=', 'active')])
        
        subs_to_bill = []
        for sub in active_subs:
            if not sub.next_billing_date:
                continue
                
            # Calcular cuándo le toca factura a esta suscripción específica (Basado en el PRÓXIMO inicio)
            lead_days = int(sub.invoice_gen_type or 0)
            gen_date = sub.next_billing_date - timedelta(days=lead_days)
            
            # Si hoy es el día de generación o ya pasó
            if today >= gen_date:
                # Verificar si ya existe una SO para el periodo que vamos a facturar
                # (Para evitar duplicados si el cron corre varias veces)
                period_desc = f"Periodo: {sub.next_billing_date}"
                existing = sub.sale_order_ids.filtered(
                    lambda s: s.state in ['draft', 'sent'] and period_desc in (s.order_line.mapped('name')[0] if s.order_line else '')
                )
                if not existing:
                    subs_to_bill.append(sub)
        
        if not subs_to_bill:
            return

        SaleOrder = self.env['sale.order']
        grouped_subs = {}
        
        # 2. Agrupación según preferencia del cliente
        for sub in subs_to_bill:
            method = sub.partner_id.invoice_grouping_method or 'individual'
            if method == 'global':
                key = (sub.partner_id.id, 'global') 
            elif method == 'by_branch':
                addr_id = sub.service_address_id.id if sub.service_address_id else False
                key = (sub.partner_id.id, addr_id)
            else:
                key = (sub.partner_id.id, sub.id)
            
            if key not in grouped_subs:
                grouped_subs[key] = []
            grouped_subs[key].append(sub)
            
        # 3. Generación de las Órdenes
        for key, subs_list in grouped_subs.items():
            try:
                partner_id = key[0]
                first_sub = subs_list[0]
                
                origin_names = ", ".join([s.name for s in subs_list])
                so_vals = {
                    'partner_id': partner_id,
                    'origin': f"Renovación: {origin_names}",
                    'order_line': []
                }
                
                if first_sub.partner_id.invoice_grouping_method == 'by_branch' and first_sub.service_address_id:
                    so_vals['partner_shipping_id'] = first_sub.service_address_id.id
                
                for sub in subs_list:
                    # Usamos las fechas reales del periodo configurado
                    desc = f"Servicio: {sub.product_id.name} | Contrato: {sub.name} | Periodo: {sub.current_period_start} al {sub.current_period_end}"
                    if sub.service_address_id and sub.partner_id.invoice_grouping_method == 'global':
                         desc += f" | Sucursal: {sub.service_address_id.name}"

                    so_vals['order_line'].append((0, 0, {
                        'product_id': sub.product_id.id,
                        'name': desc,
                        'product_uom_qty': 1,
                        'price_unit': sub.price_unit,
                    }))
                
                so = SaleOrder.create(so_vals)
                for sub in subs_list:
                    sub.write({'sale_order_ids': [(4, so.id)]})
                
                # Intentar enviar correo si hay plantilla
                template = self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)
                if template:
                    so.message_post_with_source(template, email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature')
                    so.state = 'sent'
                
                _logger.info(f"FLEX-BILLING: Generada {so.name} para {len(subs_list)} suscripciones")
            except Exception as e:
                _logger.error(f"Error en facturación flexible para {key}: {str(e)}")

    # --- Cron 2: Process Leasing Expiration ---
    def _cron_process_leasing_expiration(self):
        """ Auto-switches plan when Leasing ends """
        today = fields.Date.today()
        # Find active leasing subs where commitment ends TODAY (or past due and not yet switched)
        subs_leasing = self.search([
            ('state', '=', 'active'),
            ('equipment_ownership', '=', 'leasing'),
            ('commitment_end_date', '<=', today),
            ('plan_after_leasing_id', '!=', False) # Must have a target plan
        ])
        
        for sub in subs_leasing:
            try:
                old_plan = sub.product_id.name
                new_plan = sub.plan_after_leasing_id
                
                # Perform the switch
                sub.write({
                    'product_id': new_plan.id,
                    'price_unit': new_plan.list_price,
                    'equipment_ownership': 'customer',
                    'is_forced_contract': False,
                    # We don't clear commitment_period for historical record, but it no longer applies
                })
                
                # Notify
                sub.message_post(body=f"LEASING FINALIZADO: El equipo pasó a propiedad del cliente. Plan cambiado de '{old_plan}' a '{new_plan.name}'.")
                _logger.info(f"LEASING: Switched {sub.name} to customer owned and new plan.")
                
            except Exception as e:
                _logger.error(f"Failed to process leasing expiration for {sub.name}: {str(e)}")

    # --- Cron 3: Gestión de Suspensión Automática ---
    def _cron_generate_recurring_invoices(self):
        """ Revisa suscripciones vencidas para suspender el servicio según sus días de gracia """
        today = fields.Date.today()
        # Buscamos activas que ya pasaron su fecha de corte
        subs_to_suspend = self.search([
            ('state', '=', 'active'),
            ('technical_state', '=', 'active'),
            ('service_cut_date', '<', today)
        ])
        for sub in subs_to_suspend:
            # Solo suspender si NO hay pagos o prórrogas activas
            # (La lógica de prórroga ya limpia extension_end_date al vencer)
            sub.action_suspend()
            sub.message_post(body="SUSPENSIÓN AUTOMÁTICA: Se alcanzó la fecha límite de corte sin detectar pago.")

    def action_renew_service(self):
        for sub in self:
            today = fields.Date.today()
            interval = int(sub.recurring_interval)
            
            # Limpiar prórroga si existe
            if sub.extension_end_date:
                sub.extension_end_date = False
                
            # Calcular Nuevo Periodo
            # Si el next_billing_date es futuro, sumamos a ese. Si es pasado, sumamos a hoy.
            base_date = sub.next_billing_date if sub.next_billing_date and sub.next_billing_date >= today else today
            
            new_next_billing = base_date + relativedelta(months=interval)
            
            sub.write({
                'current_period_start': base_date,
                'current_period_end': new_next_billing - timedelta(days=1),
                'next_billing_date': new_next_billing
            })
            
            sub.message_post(body=f"SERVICIO RENOVADO: Nuevo periodo del {sub.current_period_start} al {sub.current_period_end}")
            
            # Reactivación si estaba suspendido
            if sub.technical_state in ['suspended', 'cut']:
                sub.action_activate()
                sub.message_post(body="Servicio reactivado automáticamente por renovación.")

    def _create_recurring_invoice(self):
        # Legacy method
        self.ensure_one()
        Invoice = self.env['account.move']
        period_start = self.next_billing_date
        period_end = period_start + relativedelta(months=int(self.recurring_interval)) - timedelta(days=1)
        description = f"{self.product_id.name} - Period: {period_start} to {period_end}"
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.service_address_id.id if self.service_address_id else self.partner_id.id,
            'invoice_date': self.next_billing_date,
            'subscription_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'name': description,
                'quantity': 1,
                'price_unit': self.price_unit,
            })]
        }
        return Invoice.create(invoice_vals)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    subscription_id = fields.Many2one('sentinela.subscription', string='Main Subscription (Legacy)')
    
    # Compute or Relation to find all subs linked to this order
    related_subscription_ids = fields.Many2many('sentinela.subscription', string='Related Subscriptions', compute='_compute_related_subs')

    def _compute_related_subs(self):
        for order in self:
            # Find subs that have this order in their sale_order_ids
            subs = self.env['sentinela.subscription'].search([('sale_order_ids', 'in', order.id)])
            order.related_subscription_ids = subs

    is_renewal_processed = fields.Boolean(default=False, copy=False)
    target_transfer_address_id = fields.Many2one('res.partner', string='Target Transfer Address', copy=False)
    
    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        for order in self:
            # Renew ALL linked subscriptions
            # Fallback to legacy field if no related_subs found (for older orders)
            subs_to_renew = order.related_subscription_ids or order.subscription_id
            
            if subs_to_renew and not order.is_renewal_processed:
                for sub in subs_to_renew:
                    # 1. Renewal
                    sub.action_renew_service()
                    _logger.info(f"SUBSCRIPTION: Auto-renewed {sub.name} via Global Order {order.name}")
                    
                    # 2. Address Transfer (Only applies if single sub usually, or apply to all if logical)
                    if order.target_transfer_address_id:
                        old_addr = sub.service_address_id.contact_address
                        new_addr = order.target_transfer_address_id.contact_address
                        sub.write({
                            'service_address_id': order.target_transfer_address_id.id,
                            'description': (sub.description or '') + f"<br/>[System] Traslado de Domicilio completado el {fields.Date.today()}"
                        })
                        sub.message_post(body=f"DOMICILIO ACTUALIZADO: Servicio trasladado a {new_addr}")

                order.is_renewal_processed = True
        return res
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super(SaleOrder, self)._create_invoices(grouped=grouped, final=final, date=date)
        # Propagate subscription_id to invoices
        for move in moves:
            # Find which subscription this invoice came from (via sale orders)
            # A move can be related to multiple orders, but usually one sub per order
            orders = move.line_ids.sale_line_ids.order_id
            for order in orders:
                if order.subscription_id:
                    move.subscription_id = order.subscription_id
                    # If SO already triggered renewal, mark Invoice as processed to avoid double renewal
                    if order.is_renewal_processed:
                        move.is_renewal_processed = True 
                    break 
        return moves

class AccountMove(models.Model):
    _inherit = 'account.move'
    subscription_id = fields.Many2one('sentinela.subscription', string='Related Subscription')
    is_renewal_processed = fields.Boolean(default=False, copy=False, help="Technical flag to prevent double renewal processing.")

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        self._check_subscription_renewal()
        return res

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if 'payment_state' in vals:
            self._check_subscription_renewal()
        return res

    def _check_subscription_renewal(self):
        for move in self:
            if move.subscription_id and move.payment_state in ['paid', 'in_payment'] and not move.is_renewal_processed:
                move.subscription_id.action_renew_service()
                move.is_renewal_processed = True
                _logger.info(f"SUBSCRIPTION: Auto-renewed {move.subscription_id.name} via Invoice {move.name}")

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        payments = super().action_create_payments()
        
        # Trigger renewal check for related invoices immediately after manual payment
        invoices = self.line_ids.move_id
        for invoice in invoices:
            if invoice.subscription_id:
                _logger.info(f"PAYMENT REGISTER: Checking renewal for invoice {invoice.name}")
                invoice._check_subscription_renewal()
                
        return payments