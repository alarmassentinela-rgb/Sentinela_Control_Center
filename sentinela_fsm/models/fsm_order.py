from odoo import models, fields, api, _

class FsmOrder(models.Model):
    _name = 'sentinela.fsm.order'
    _description = 'Field Service Order'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, scheduled_date asc'

    name = fields.Char(string='Folio', required=True, copy=False, readonly=True, default='Nuevo')
    
    # Customer Info
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, tracking=True)
    service_address_id = fields.Many2one('res.partner', string='Dirección de Servicio',
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    phone = fields.Char(related='partner_id.phone', string='Teléfono')

    # Location Tracking
    check_in_lat = fields.Float(string='Latitud Check-In', digits=(10, 7))
    check_in_lon = fields.Float(string='Longitud Check-In', digits=(10, 7))
    check_out_lat = fields.Float(string='Latitud Check-Out', digits=(10, 7))
    check_out_lon = fields.Float(string='Longitud Check-Out', digits=(10, 7))
    distance_traveled = fields.Float(string='Distancia Recorrida (km)', help='Distancia aproximada entre check-in y check-out')
    
    # Context
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción Relacionada',
        domain="[('partner_id', '=', partner_id)]") # Domain in python definition works for standard views
    description = fields.Html(string='Descripción del Problema/Solicitud', required=True)

    # Monitoring Integration
    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento de Alarma Relacionado')
    
    # Scheduling
    technician_id = fields.Many2one('res.users', string='Técnico Asignado', tracking=True)
    scheduled_date = fields.Datetime(string='Fecha Programada', tracking=True)
    duration_expected = fields.Float(string='Duración Estimada (Horas)', default=1.0)
    
    # Status
    stage = fields.Selection([
        ('new', 'Nuevo'),
        ('assigned', 'Asignado'),
        ('in_progress', 'En Proceso'),
        ('paused', 'Pausado'),
        ('done', 'Finalizado'),
        ('cancel', 'Cancelado')
    ], string='Etapa', default='new', tracking=True)
    pause_reason_id = fields.Many2one('sentinela.fsm.pause.reason', string='Última Causa de Pausa', readonly=True, tracking=True)
    pause_notes = fields.Text(string='Notas de Pausa', readonly=True, tracking=True)
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Alta'),
        ('2', 'Urgente'),
        ('3', 'Crítica')
    ], string='Prioridad', default='0')
    
    service_type = fields.Selection([
        ('install', 'Instalación'),
        ('repair', 'Reparación'),
        ('transfer', 'Traslado'),
        ('patrol', 'Patrullaje / Respuesta'),
        ('other', 'Otro')
    ], string='Tipo de Servicio', default='other')

    # Checklist & Evidence
    checklist_ids = fields.One2many('sentinela.fsm.order.line', 'order_id', string='Checklist de Tareas')
    evidence_ids = fields.One2many('sentinela.fsm.evidence', 'order_id', string='Evidencias')
    equipment_ids = fields.One2many('sentinela.fsm.equipment', 'order_id', string='Equipos/Materiales Usados')
    equipment_cost = fields.Float(string='Costo de Equipos', compute='_compute_equipment_cost', store=True)

    # Communication
    chat_message_ids = fields.One2many('sentinela.fsm.chat.message', 'order_id', string='Mensajes de Chat')
    chat_message_count = fields.Integer(string='Número de Mensajes', compute='_compute_chat_message_count')

    # Execution
    check_in_date = fields.Datetime(string='Check-In (Inicio)')
    check_out_date = fields.Datetime(string='Check-Out (Fin)')

    # Time Tracking
    actual_start_time = fields.Datetime(string='Inicio Real del Trabajo')
    actual_end_time = fields.Datetime(string='Fin Real del Trabajo')
    planned_duration = fields.Float(string='Duración Planificada (Horas)', default=1.0)
    actual_duration = fields.Float(string='Duración Real (Horas)', compute='_compute_actual_duration', store=True)
    travel_time = fields.Float(string='Tiempo de Viaje (Horas)')
    work_time = fields.Float(string='Tiempo de Trabajo (Horas)', compute='_compute_work_time', store=True)

    # Resolution
    resolution_notes = fields.Text(string='Notas de Resolución')
    customer_signature = fields.Binary(string='Firma del Cliente')
    customer_rating = fields.Integer(string='Calificación del Cliente', help='Calificación del 1 al 5', default=0)
    customer_feedback = fields.Text(string='Comentarios del Cliente')

    # Report Authorization
    is_authorized_by_operator = fields.Boolean(string='Reporte Autorizado por Central', default=False, tracking=True)
    report_sent_date = fields.Datetime(string='Fecha de Envío a Cliente', readonly=True)

    is_fsm_manager = fields.Boolean(string="Is FSM Manager", compute='_compute_is_fsm_manager')

    def _compute_is_fsm_manager(self):
        for order in self:
            order.is_fsm_manager = self.env.user.has_group('sentinela_fsm.group_fsm_manager')

    def send_push_notification(self, title, message, recipient_user=None, notification_type='update'):
        """
        Método para enviar notificaciones push al técnico asignado o usuario específico
        """
        if not recipient_user:
            recipient_user = self.technician_id

        if recipient_user:
            # Crear notificación interna
            notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'type': 'info',
                    'sticky': False,
                }
            }

            # Enviar mensaje al usuario
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.users', recipient_user.id),
                {'type': 'simple_notification', 'payload': notification['params']}
            )

            # También crear un mensaje en el chatter
            self.message_post(
                body=message,
                subtype_xmlid='mail.mt_note',
                message_type='notification'
            )

            # Registrar la notificación en el modelo de notificaciones
            self.env['sentinela.fsm.notification'].create({
                'order_id': self.id,
                'title': title,
                'message': message,
                'recipient_user_id': recipient_user.id,
                'notification_type': notification_type
            })

        return True

    def action_assign(self):
        self.stage = 'assigned'
        # Send Notification Email
        template = self.env.ref('sentinela_fsm.mail_template_fsm_assigned', raise_if_not_found=False)
        if template:
            self.message_post_with_source(
                template,
                email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
            )

        # Enviar notificación push al técnico
        if self.technician_id:
            self.send_push_notification(
                title="Nueva Orden Asignada",
                message=f"Se te ha asignado la orden {self.name}. Fecha programada: {self.scheduled_date}",
                recipient_user=self.technician_id,
                notification_type='assignment'
            )

    def action_start(self):
        self.stage = 'in_progress'
        self.check_in_date = fields.Datetime.now()
        # Aquí se podría obtener la ubicación real del técnico si se integra con GPS
        # Por ahora, se puede usar la ubicación del cliente como referencia
        if self.service_address_id:
            self.check_in_lat = self.service_address_id.partner_latitude
            self.check_in_lon = self.service_address_id.partner_longitude

        # Enviar notificación al técnico
        if self.technician_id:
            self.send_push_notification(
                title="Orden Iniciada",
                message=f"Has iniciado la orden {self.name}. Recuerda tomar evidencias del trabajo realizado.",
                recipient_user=self.technician_id,
                notification_type='start'
            )

    def action_finish(self):
        # Generar movimientos de inventario antes de cerrar
        if self.equipment_ids:
            self._create_stock_moves()

        self.stage = 'done'
        self.check_out_date = fields.Datetime.now()
        # Registrar la ubicación de salida si está disponible
        if self.service_address_id:
            self.check_out_lat = self.service_address_id.partner_latitude
            self.check_out_lon = self.service_address_id.partner_longitude
            # Calcular distancia aproximada si ambas ubicaciones están disponibles
            if self.check_in_lat and self.check_in_lon and self.check_out_lat and self.check_out_lon:
                from math import radians, cos, sin, asin, sqrt
                lat1, lon1, lat2, lon2 = map(radians, [self.check_in_lat, self.check_in_lon, self.check_out_lat, self.check_out_lon])

                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                r = 6371  # Radio de la Tierra en kilómetros

                self.distance_traveled = round(c * r, 2)

        # Enviar notificación al coordinador o cliente
        manager_group = self.env.ref('sentinela_fsm.group_fsm_manager')
        managers = self.env['res.users'].search([('groups_id', 'in', manager_group.id)])

        for manager in managers:
            self.send_push_notification(
                title="Orden Finalizada",
                message=f"La orden {self.name} ha sido completada por {self.technician_id.name}.",
                recipient_user=manager,
                notification_type='finish'
            )

    def _create_stock_moves(self):
        """ Creates and validates a Stock Picking for used materials """
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        
        # 1. Get Warehouse Config (Default to main warehouse)
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        if not warehouse:
            return

        picking_type = warehouse.out_type_id
        src_location = picking_type.default_location_src_id
        dest_location = self.env.ref('stock.stock_location_customers')

        # TODO: Future improvement - Use Technician's mobile location if configured
        
        # 2. Create Picking
        picking = Picking.create({
            'picking_type_id': picking_type.id,
            'location_id': src_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.name,
            'partner_id': self.partner_id.id,
        })

        # 3. Create Moves
        for line in self.equipment_ids:
            if line.product_id.type == 'service':
                continue
                
            Move.create({
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': src_location.id,
                'location_dest_id': dest_location.id,
            })

        # 4. Confirm and Validate
        if picking.move_ids:
            picking.action_confirm()
            picking.action_assign()
            
            # Auto-validate (Assume technician used what they said)
            # Create immediate transfer wizard logic or just set quantity_done
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                
            picking.button_validate()
            
            self.message_post(body=f"Inventario descontado: <a href='#' data-oe-model='stock.picking' data-oe-id='{picking.id}'>{picking.name}</a>")

    @api.depends('actual_start_time', 'actual_end_time')
    def _compute_actual_duration(self):
        for order in self:
            if order.actual_start_time and order.actual_end_time:
                duration = order.actual_end_time - order.actual_start_time
                order.actual_duration = duration.total_seconds() / 3600
            else:
                order.actual_duration = 0.0

    @api.depends('actual_start_time', 'actual_end_time', 'travel_time')
    def _compute_work_time(self):
        for order in self:
            if order.actual_duration:
                order.work_time = order.actual_duration - order.travel_time
            else:
                order.work_time = 0.0

    @api.depends('equipment_ids.total_price')
    def _compute_equipment_cost(self):
        for order in self:
            order.equipment_cost = sum(equipment.total_price for equipment in order.equipment_ids)

    @api.depends('chat_message_ids')
    def _compute_chat_message_count(self):
        for order in self:
            order.chat_message_count = len(order.chat_message_ids)
    
    
    def action_open_map(self):
        """ Opens Google Maps with coordinates or address """
        self.ensure_one()
        url = "https://www.google.com/maps/search/?api=1&query="
        
        # Priority: 1. Subscription Lat/Long, 2. Partner Lat/Long, 3. Address Text
        if self.subscription_id and self.subscription_id.latitude and self.subscription_id.longitude:
            url += f"{self.subscription_id.latitude},{self.subscription_id.longitude}"
        elif self.partner_id.partner_latitude and self.partner_id.partner_longitude:
            url += f"{self.partner_id.partner_latitude},{self.partner_id.partner_longitude}"
        else:
            # Fallback to address string
            addr = self.service_address_id.contact_address or self.partner_id.contact_address
            import urllib.parse
            url += urllib.parse.quote(addr.replace('\n', ' '))
            
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('sentinela.fsm.order') or 'OS-0000'
        
        orders = super().create(vals_list)
        
        # Auto-populate checklist if templates exist
        for order in orders:
            order._populate_checklist()
            
        return orders

    def _populate_checklist(self):
        """ Copies templates to order lines based on service type """
        templates = self.env['sentinela.fsm.task.template'].search([
            '|', ('service_type', '=', 'all'), ('service_type', '=', self.service_type)
        ])
        lines = []
        for t in templates:
            lines.append((0, 0, {
                'name': t.name,
                'is_done': False
            }))
        if lines:
            self.write({'checklist_ids': lines})

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return ['new', 'assigned', 'in_progress', 'paused', 'done', 'cancel']

    def action_assign(self):
        self.stage = 'assigned'
        # Send Notification Email
        template = self.env.ref('sentinela_fsm.mail_template_fsm_assigned', raise_if_not_found=False)
        if template:
            self.message_post_with_source(
                template,
                email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
            )

    def action_start(self):
        self.stage = 'in_progress'
        self.check_in_date = fields.Datetime.now()
        # Aquí se podría obtener la ubicación real del técnico si se integra con GPS
        # Por ahora, se puede usar la ubicación del cliente como referencia
        if self.service_address_id:
            self.check_in_lat = self.service_address_id.partner_latitude
            self.check_in_lon = self.service_address_id.partner_longitude

    def action_finish(self):
        self.stage = 'done'
        self.check_out_date = fields.Datetime.now()
        # Registrar la ubicación de salida si está disponible
        if self.service_address_id:
            self.check_out_lat = self.service_address_id.partner_latitude
            self.check_out_lon = self.service_address_id.partner_longitude
            # Calcular distancia aproximada si ambas ubicaciones están disponibles
            if self.check_in_lat and self.check_in_lon and self.check_out_lat and self.check_out_lon:
                from math import radians, cos, sin, asin, sqrt
                lat1, lon1, lat2, lon2 = map(radians, [self.check_in_lat, self.check_in_lon, self.check_out_lat, self.check_out_lon])

                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                r = 6371  # Radio de la Tierra en kilómetros

                self.distance_traveled = round(c * r, 2)

    def action_resume(self):
        self.ensure_one()
        self.write({
            'stage': 'in_progress',
            'pause_reason_id': False,
            'pause_notes': False,
        })
        self.message_post(body=_("Order resumed by %s.") % self.env.user.name)

    def notify_salesperson_for_quote(self):
        for order in self:
            salesperson = order.partner_id.user_id or order.subscription_id.sale_order_id.user_id
            
            body = _("Quote needed for this order. Technician notes: %s") % order.pause_notes
            
            if salesperson:
                order.message_subscribe(partner_ids=salesperson.partner_id.ids)
                order.message_post(
                    body=body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    partner_ids=salesperson.partner_id.ids,
                )
            else:
                order.message_post(body=body)

    def action_authorize_report(self):
        self.ensure_one()
        self.write({'is_authorized_by_operator': True})
        self.message_post(body="✅ REPORTE AUTORIZADO por el operador de central.")

    def action_send_report_to_customer(self):
        self.ensure_one()
        if not self.is_authorized_by_operator:
            raise models.ValidationError(_("El reporte debe ser autorizado por el operador antes de enviarlo."))
        
        # 1. Generar PDF
        report_action = self.env.ref('sentinela_fsm.action_report_fsm_order')
        pdf_content, content_type = report_action._render_qweb_pdf(self.ids)
        
        # 2. Crear adjunto
        attachment = self.env['ir.attachment'].create({
            'name': f"Reporte_{self.name}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })

        # 3. Enviar Correo
        # Nota: Idealmente usar una plantilla, pero aquí lo hacemos directo para asegurar los adjuntos
        body = f"""
            <div style="font-family: Arial, sans-serif;">
                <h2>Reporte de Atención - Folio {self.name}</h2>
                <p>Estimado cliente,</p>
                <p>Adjunto encontrará el reporte detallado de la atención realizada por nuestro equipo en su domicilio.</p>
                <br/>
                <p><b>Resumen:</b> {self.resolution_notes or 'Revisión técnica completada.'}</p>
                <br/>
                <p>Atentamente,<br/><b>Central de Monitoreo Sentinela</b></p>
            </div>
        """
        
        self.message_post(
            body=body,
            partner_ids=self.partner_id.ids,
            attachment_ids=[attachment.id],
            subtype_xmlid='mail.mt_comment'
        )

        self.report_sent_date = fields.Datetime.now()
        self.message_post(body="📧 Reporte de patrullaje enviado al cliente con adjunto PDF.")
        return True
