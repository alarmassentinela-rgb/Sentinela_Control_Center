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
    sale_order_id = fields.Many2one('sale.order', string='Venta de Origen', readonly=True, copy=False,
        help='Orden de venta que originó esta orden de servicio (trazabilidad).')
    description = fields.Html(string='Descripción del Problema/Solicitud', required=True)

    # Scheduling
    technician_id = fields.Many2one('res.users', string='Técnico Asignado', tracking=True)
    patrol_unit_id = fields.Many2one('sentinela.patrol.unit', string='Unidad de Patrulla',
        domain="[('available', '=', True)]", tracking=True,
        help='Dispositivo SentiCar a rastrear en esta orden (celular o vehículo). '
             'Si se deja vacío, se rastrea el celular configurado en el patrullero.')
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
        ('repair', 'Reparación / Falla (Correctivo)'),
        ('maintenance', 'Mantenimiento Preventivo'),
        ('revision', 'Revisión / Diagnóstico'),
        ('config', 'Configuración'),
        ('reconnection', 'Reconexión en Sitio'),
        ('transfer', 'Traslado / Reubicación'),
        ('removal', 'Retiro de Equipo / Desinstalación'),
        ('warranty', 'Garantía'),
        ('patrol', 'Patrullaje / Respuesta'),
        ('other', 'Otro')
    ], string='Tipo de Servicio', default='other')

    # Eje INDEPENDIENTE del tipo de trabajo: sobre QUÉ sistema/equipo es el servicio.
    # Una orden puede no tener suscripción (cliente sin contrato) o ser de algo que la
    # sub no contempla (CCTV, paneles solares, alarma sin monitoreo); por eso es un campo
    # propio de la orden, no se deriva solo de subscription_id. Se autollena desde la sub
    # cuando aplica (ver _onchange_subscription_id) y si no, lo elige el operador.
    service_category = fields.Selection([
        ('internet', 'Internet / WISP'),
        ('alarm', 'Alarma'),
        ('cctv', 'CCTV / Cámaras'),
        ('gps', 'GPS / Rastreo'),
        ('solar', 'Energía Solar (Paneles)'),
        ('access', 'Control de Acceso'),
        ('fence', 'Cercas Eléctricas'),
        ('fire', 'Detección de Incendio'),
        ('phone', 'Telefonía'),
        ('other', 'Otro'),
    ], string='Sistema / Tecnología', tracking=True,
       help='Sobre qué sistema o equipo es el servicio. Independiente del tipo de trabajo.')

    # Datos Técnicos capturados en campo (Instalaciones GPS)
    vehicle_brand = fields.Char(string='Marca del Vehículo')
    vehicle_model = fields.Char(string='Modelo del Vehículo')
    vehicle_color = fields.Char(string='Color de la Unidad')
    vehicle_plate = fields.Char(string='Placas')
    sim_iccid = fields.Char(string='ICCID de la SIM (TNF)')

    # Datos Técnicos capturados en campo (Instalaciones Alarma)
    alarm_panel_brand = fields.Char(string='Marca del Panel')
    alarm_panel_model = fields.Char(string='Modelo del Panel')
    alarm_zones = fields.Text(string='Listado de Zonas', help="Ej. Zona 1: Puerta, Zona 2: Cocina...")
    monitoring_account_number = fields.Char(string='Núm. Cuenta Monitoreo')

    # Datos Técnicos capturados en campo (Instalaciones Internet)
    internet_antenna_mac = fields.Char(string='MAC de Antena')
    internet_router_serial = fields.Char(string='Serie del Router')
    internet_signal_dbm = fields.Char(string='Potencia Señal (dBm)')
    internet_pppoe_user = fields.Char(string='Usuario PPPoE Asignado')

    # Datos Técnicos capturados en campo (Instalaciones CCTV)
    cctv_dvr_brand = fields.Char(string='Marca DVR/NVR')
    cctv_dvr_model = fields.Char(string='Modelo DVR/NVR')
    cctv_num_cameras = fields.Integer(string='Núm. Cámaras')
    cctv_storage = fields.Char(string='Disco Duro (TB/GB)')
    cctv_remote_user = fields.Char(string='Usuario Acceso Remoto')
    cctv_remote_pass = fields.Char(string='Password Acceso Remoto')

    # Coordenadas Reales de Instalación
    install_lat = fields.Float(string='Latitud Instalación', digits=(10, 7))
    install_lon = fields.Float(string='Longitud Instalación', digits=(10, 7))

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
    arrival_date = fields.Datetime(string='Llegada al Sitio')
    check_out_date = fields.Datetime(string='Check-Out (Fin)')

    # Coordenadas de llegada
    arrival_lat = fields.Float(string='Latitud Llegada', digits=(10, 7))
    arrival_lon = fields.Float(string='Longitud Llegada', digits=(10, 7))

    # Time Tracking
    actual_start_time = fields.Datetime(string='Inicio Real del Trabajo')
    actual_end_time = fields.Datetime(string='Fin Real del Trabajo')
    planned_duration = fields.Float(string='Duración Planificada (Horas)', default=1.0)
    actual_duration = fields.Float(string='Duración Real (Horas)', compute='_compute_actual_duration', store=True)
    travel_time = fields.Float(string='Tiempo de Viaje (Horas)')
    work_time = fields.Float(string='Tiempo de Trabajo (Horas)', compute='_compute_work_time', store=True)

    # F3.3 — ETA en vivo del patrullero
    last_eta_minutes = fields.Integer(string='Última ETA (min)',
        help='Minutos estimados para llegar al sitio según última posición GPS. 0 = sin dato.')
    last_eta_at = fields.Datetime(string='Última ETA calculada el', readonly=True)
    eta_updates_sent = fields.Integer(string='Updates ETA enviados', default=0, readonly=True,
        help='Máximo 3 notificaciones por orden para evitar spam al cliente.')

    # Resolution
    patrol_result = fields.Selection([
        ('no_news', 'Sin Novedad (Todo Seguro)'),
        ('false_alarm', 'Falsa Alarma (Error de Usuario)'),
        ('technical_fault', 'Falla Técnica (Falso Disparo)'),
        ('suspicious', 'Actividad Sospechosa Detectada'),
        ('intrusion_attempt', 'Intento de Intrusión (Daños Materiales)'),
        ('confirmed_intrusion', 'INTRUSIÓN CONFIRMADA / ROBO'),
        ('emergency_medical', 'Emergencia Médica Real'),
        ('fire_confirmed', 'Incendio Confirmado')
    ], string='Dictamen de la Patrulla')
    
    is_forced_entry = fields.Boolean(string='¿Hay señales de intrusión forzada?', default=False)
    police_notified = fields.Boolean(string='¿Se dio aviso a la Policía/911?', default=False)
    
    resolution_notes = fields.Text(string='Notas de Resolución')
    received_by_name = fields.Char(string='Nombre de quien recibe')
    received_by_relationship = fields.Char(string='Parentesco/Cargo')
    customer_signature = fields.Binary(string='Firma del Cliente')
    customer_rating = fields.Integer(string='Calificación del Cliente', help='Calificación del 1 al 5', default=0)
    customer_feedback = fields.Text(string='Comentarios del Cliente')

    # Report Authorization
    is_authorized_by_operator = fields.Boolean(string='Reporte Autorizado por Central', default=False, tracking=True)
    report_sent_date = fields.Datetime(string='Fecha de Envío a Cliente', readonly=True)

    is_fsm_manager = fields.Boolean(string="Is FSM Manager", compute='_compute_is_fsm_manager')
    work_log_ids = fields.One2many('sentinela.fsm.work.log', 'order_id', string='Bitácora de Trabajo')
    tracking_token = fields.Char(string='Token de Rastreo', copy=False, readonly=True)

    def _generate_tracking_token(self):
        import uuid
        for order in self:
            if not order.tracking_token:
                order.tracking_token = str(uuid.uuid4())

    def get_tracking_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/SentiCar/rastreo/{self.tracking_token}"

    def _compute_is_fsm_manager(self):
        for order in self:
            order.is_fsm_manager = self.env.user.has_group('sentinela_fsm.group_fsm_manager')

    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Al elegir/heredar una suscripción (p.ej. desde el botón 'Órdenes Técnicas'
        de la sub, que pasa default_subscription_id), rellena la orden con los datos
        que ya tiene la sub: cliente, dirección de servicio, coordenadas, cuenta de
        monitoreo y usuario PPPoE. Solo rellena lo vacío para no pisar capturas previas.
        NO toca service_type (el de la orden es el TIPO DE TRABAJO: instalación/
        reparación/...; la tecnología internet/alarma/gps ya la aporta subscription_id)."""
        sub = self.subscription_id
        if not sub:
            return

        def _to_float(v):
            try:
                return float(str(v).replace(',', ' ').split()[0])
            except (TypeError, ValueError, IndexError):
                return 0.0

        self.partner_id = sub.partner_id
        # Tecnología desde la sub (solo las que la sub contempla; CCTV/solar/etc. los pone
        # el operador a mano). Solo si la orden aún no tiene una elegida.
        tech_map = {'internet': 'internet', 'alarm': 'alarm', 'gps': 'gps'}
        if not self.service_category and sub.service_type in tech_map:
            self.service_category = tech_map[sub.service_type]
        if sub.service_address_id:
            self.service_address_id = sub.service_address_id
        if sub.monitoring_account_number and not self.monitoring_account_number:
            self.monitoring_account_number = sub.monitoring_account_number
        if sub.pppoe_user and not self.internet_pppoe_user:
            self.internet_pppoe_user = sub.pppoe_user
        lat, lon = _to_float(sub.latitude), _to_float(sub.longitude)
        if lat and not self.install_lat:
            self.install_lat = lat
        if lon and not self.install_lon:
            self.install_lon = lon
        if not self.description:
            plan = sub.product_id.name or sub.name
            self.description = _("<p>Servicio relacionado a la suscripción <b>%s</b> (%s).</p>") % (sub.name, plan)

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
            self.env['bus.bus']._sendone(
                recipient_user.partner_id,
                'simple_notification',
                notification['params']
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
        # No se puede programar sin técnico ni fecha: la tarea no le aparecería
        # a nadie en su lista de pendientes.
        if not self.technician_id:
            raise models.ValidationError(_("Asigna un técnico antes de programar la orden."))
        if not self.scheduled_date:
            raise models.ValidationError(_("Define la fecha y hora programada antes de asignar la orden al técnico."))
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

        # NOTIFICAR AL CLIENTE — F3: usa notify() para respetar canal preferido
        if (self.partner_id.notification_channel or 'both') != 'none':
            tracking_url = self.get_tracking_url()
            if self.service_type == 'patrol':
                oficial = self.technician_id.name or 'nuestro personal'
                msg = (f"🚨 *SENTINELA: EMERGENCIA EN CURSO*\n\n"
                       f"Hola *{self.partner_id.name}*, hemos activado nuestro protocolo de respuesta. "
                       f"La patrulla con el oficial *{oficial}* va en camino a su domicilio ahora mismo.\n\n"
                       f"🧭 *Siga la trayectoria de la patrulla en tiempo real (SentiCar):* \n{tracking_url}")
            else:
                msg = (f"🚀 *Sentinela: Técnico en camino*\n\n"
                       f"Hola *{self.partner_id.name}*, le informamos que nuestro técnico *{self.technician_id.name}* "
                       f"ha iniciado su orden de servicio *{self.name}* y se dirige a su domicilio.\n\n"
                       f"📍 *Ubicación:* {self.service_address_id.contact_address or self.partner_id.contact_address}\n\n"
                       f"🧭 *Siga a su técnico en tiempo real por SentiCar:* \n{tracking_url}")

            res = self.partner_id.notify(message=msg)
            sent = [c for c, ok in res.items() if ok]
            label = 'Patrulla' if self.service_type == 'patrol' else 'Técnico'
            self.message_post(body=f"📲 '{label} en camino' enviado al cliente — canales: {', '.join(sent) or 'NINGUNO'}.")

        # F3.3 — mandar primera ETA si es patrullaje y tenemos coordenadas
        if self.service_type == 'patrol':
            try:
                self.action_send_eta_update(force=True)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("ETA inicial falló para %s: %s", self.name, e)

    def action_arrival(self):
        """ Registra la llegada de la patrulla al sitio """
        self.ensure_one()
        self.arrival_date = fields.Datetime.now()

        # Intentar obtener ubicación desde Traccar o por contexto
        # Nota: El controlador pasará las coordenadas GPS del móvil si están disponibles

        self.message_post(body="📍 **ARRIBO AL SITIO:** El patrullero ha reportado su llegada al domicilio.")

        # Notificar al cliente — F3: usa notify() multi-canal
        if (self.partner_id.notification_channel or 'both') != 'none':
            msg = (f"🛡️ *Sentinela: Patrulla en sitio*\n\n"
                   f"Hola *{self.partner_id.name}*, le informamos que nuestra unidad de respuesta ya se encuentra en su domicilio (Folio: {self.name}).\n"
                   f"El patrullero iniciará la inspección perimetral de seguridad.")
            self.partner_id.notify(message=msg)

        return True

    def action_finish(self):
        # BLOQUEO DE SEGURIDAD: Validar firma antes de permitir el cierre
        if not self.customer_signature:
            raise models.ValidationError(_("No se puede finalizar la orden sin la firma de conformidad del cliente."))

        # Registrar el avance final en la bitácora
        self.env['sentinela.fsm.work.log'].create({
            'order_id': self.id,
            'notes': f"FINALIZACIÓN: {self.resolution_notes or 'Trabajo completado.'}",
            'stage_at_moment': 'done'
        })

        # Generar movimientos de inventario antes de cerrar
        if self.equipment_ids:
            self._create_stock_moves()

        # Sincronizar datos técnicos al contrato si existe
        if self.subscription_id:
            sub_vals = {}
            
            # Sincronizar Ubicación GPS Real (Desde Instalación o Check-In)
            final_lat = self.install_lat or self.check_in_lat
            final_lon = self.install_lon or self.check_in_lon

            if final_lat and final_lon:
                sub_vals['latitude'] = str(final_lat)
                sub_vals['longitude'] = str(final_lon)
                
                # 1. Propagar a la Dirección de Servicio (Contacto)
                if self.service_address_id:
                    self.service_address_id.write({
                        'partner_latitude': final_lat,
                        'partner_longitude': final_lon
                    })
                
                # 2. Propagar a Dispositivos de Monitoreo vinculados a la suscripción
                monitoring_devices = self.env['sentinela.monitoring.device'].search([
                    ('subscription_id', '=', self.subscription_id.id)
                ])
                if monitoring_devices:
                    monitoring_devices.write({
                        'latitude': final_lat,
                        'longitude': final_lon
                    })

            # Datos Vehículo (GPS) — la suscripción tiene marca y modelo en campos separados
            if self.vehicle_brand: sub_vals['vehicle_brand'] = self.vehicle_brand
            if self.vehicle_model: sub_vals['vehicle_model'] = self.vehicle_model
            if self.vehicle_plate: sub_vals['vehicle_plate'] = self.vehicle_plate
            if self.vehicle_color: sub_vals['vehicle_color'] = self.vehicle_color
            if self.sim_iccid: sub_vals['sim_iccid'] = self.sim_iccid
            
            # Datos Alarma
            if self.alarm_panel_brand: sub_vals['equipment_brand'] = self.alarm_panel_brand
            if self.alarm_panel_model: sub_vals['equipment_model'] = self.alarm_panel_model
            if self.monitoring_account_number: sub_vals['monitoring_account_number'] = self.monitoring_account_number
            if self.alarm_zones:
                current_notes = self.subscription_id.description or ""
                sub_vals['description'] = current_notes + f"<br/><b>Zonas (Instalación):</b><br/>{self.alarm_zones}"

            # Datos Internet
            if self.internet_antenna_mac: sub_vals['location_notes'] = (self.subscription_id.location_notes or "") + f"\nMAC Antena: {self.internet_antenna_mac}"
            if self.internet_pppoe_user: sub_vals['pppoe_user'] = self.internet_pppoe_user
            
            # Sincronización de Números de Serie desde Equipos usados
            main_equipment = self.equipment_ids.filtered(lambda e: e.lot_id and (e.product_id.is_subscription or e.product_id == self.subscription_id.product_id))
            if not main_equipment and self.equipment_ids:
                # Fallback: Usar el primer equipo que tenga serie si no se detectó por tipo
                main_equipment = self.equipment_ids.filtered(lambda e: e.lot_id)[:1]
            
            if main_equipment:
                sub_vals['serial_number_id'] = main_equipment[0].lot_id.id
                sub_vals['equipment_serial'] = main_equipment[0].lot_id.name
            
            # Actualizar Fecha de Último Mantenimiento si es un servicio técnico
            if self.service_type in ['install', 'repair', 'maintenance', 'other']:
                sub_vals['last_maintenance_date'] = fields.Date.today()

            # Si es mantenimiento preventivo, reprogramar el siguiente ciclo desde HOY
            # (el cron pudo haberlo adelantado ya; esto lo ancla a la fecha real de servicio).
            if self.service_type == 'maintenance' and self.subscription_id.maintenance_frequency not in (False, '0'):
                from dateutil.relativedelta import relativedelta
                months = int(self.subscription_id.maintenance_frequency)
                sub_vals['next_maintenance_date'] = fields.Date.today() + relativedelta(months=months)
            
            # Punto 4: Cierre automático por Retiro de Equipo
            if self.service_type == 'removal':
                sub_vals['state'] = 'closed'
                sub_vals['technical_state'] = 'cut'
                self.subscription_id.message_post(body=f"CONTRATO CERRADO AUTOMÁTICAMENTE: Se finalizó la orden de retiro/desinstalación {self.name}.")

            if sub_vals:
                self.subscription_id.write(sub_vals)
                self.message_post(body="✅ Geolocalización, números de serie y datos técnicos sincronizados al contrato.")

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
            # Generar token de rastreo
            import uuid
            vals['tracking_token'] = str(uuid.uuid4())
        
        orders = super().create(vals_list)
        
        # Auto-populate checklist if templates exist
        for order in orders:
            order._populate_checklist()
            
        return orders

    def _populate_checklist(self):
        """ Copies templates to order lines based on service type AND technology """
        # Determinar tecnología: desde la suscripción si la hay; si no (cliente sin
        # contrato), usar el Sistema/Tecnología capturado en la propia orden.
        tech = 'all'
        if self.subscription_id:
            tech = self.subscription_id.service_type
        elif self.service_category:
            tech = self.service_category
        
        # Buscar tareas que apliquen a este servicio y esta tecnología.
        # En PATRULLAJE el checklist es propio (perímetro/puertas/sospechosos): NO se
        # mezclan las tareas genéricas 'all' (que son de instalación/configuración).
        if self.service_type == 'patrol':
            domain = [('service_type', '=', 'patrol')]
        else:
            domain = [
                ('service_type', 'in', ['all', self.service_type]),
                ('tech_category', 'in', ['all', tech])
            ]

        templates = self.env['sentinela.fsm.task.template'].search(domain, order='sequence asc')
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

    def action_resume(self):
        self.ensure_one()
        self.write({
            'stage': 'in_progress',
            'pause_reason_id': False,
            'pause_notes': False,
        })
        self.message_post(body=_("Order resumed by %s.") % self.env.user.name)

    def action_pause(self, reason_id=None, notes=False):
        """ Pausa la orden con un motivo específico y guarda en bitácora """
        self.ensure_one()
        self.write({
            'stage': 'paused',
            'pause_reason_id': reason_id,
            'pause_notes': notes,
        })
        # Registrar en la bitácora cronológica
        if notes:
            self.env['sentinela.fsm.work.log'].create({
                'order_id': self.id,
                'notes': f"PAUSA ({self.pause_reason_id.name or 'Sin motivo'}): {notes}",
                'stage_at_moment': 'paused'
            })
        
        msg = f"Orden PAUSADA por el técnico. Motivo: {self.pause_reason_id.name or 'No especificado'}. <br/>Notas: {notes or ''}"
        self.message_post(body=msg)
        return True

    def action_request_quote(self, req_notes):
        """ Crea una requisición de cotización enriquecida con contexto técnico """
        self.ensure_one()
        salesperson = self.partner_id.user_id or self.env.user
        
        # Construir BLOQUE DE CONTEXTO TÉCNICO para el vendedor
        tech_context = ""
        if self.alarm_panel_brand or self.alarm_panel_model:
            tech_context += f"<li><b>SISTEMA DE ALARMA:</b> {self.alarm_panel_brand or ''} {self.alarm_panel_model or ''}</li>"
        if self.cctv_dvr_brand or self.cctv_dvr_model:
            tech_context += f"<li><b>SISTEMA CCTV:</b> {self.cctv_dvr_brand or ''} {self.cctv_dvr_model or ''} ({self.cctv_num_cameras} cámaras)</li>"
        if self.internet_router_serial:
            tech_context += f"<li><b>INTERNET:</b> Router {self.internet_router_serial}</li>"
        if self.vehicle_brand or self.vehicle_model:
            tech_context += f"<li><b>VEHÍCULO:</b> {self.vehicle_brand or ''} {self.vehicle_model or ''} (Placas: {self.vehicle_plate or 'N/A'})</li>"

        full_note = f"""
            <div style="font-family: Arial, sans-serif;">
                <p style="color: #e67e22; font-size: 16px;"><b>⚠️ REQUISICIÓN DESDE CAMPO</b></p>
                <p><b>Lo que solicita el cliente:</b><br/>{req_notes}</p>
                <hr/>
                <p style="font-size: 12px; color: #666;"><b>DATOS TÉCNICOS EN SITIO (PARA COMPATIBILIDAD):</b></p>
                <ul style="font-size: 12px; color: #666;">
                    {tech_context or '<li>No hay datos técnicos registrados aún.</li>'}
                </ul>
                <p style="font-size: 11px;"><i>Solicitado por: {self.technician_id.name}</i></p>
            </div>
        """

        # Crear Actividad para ventas
        self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'note': full_note,
            'summary': f"💰 Cotizar adicional: {req_notes[:30]}...",
            'user_id': salesperson.id,
            'res_id': self.id,
            'res_model_id': self.env['ir.model']._get(self._name).id,
            'date_deadline': fields.Date.today(),
        })
        
        self.message_post(body=f"📝 <b>REQUISICIÓN ENVIADA A VENTAS:</b> {req_notes}")
        return True

    # ---------------- F3.3 ETA en vivo ----------------

    MAX_ETA_UPDATES_PER_ORDER = 3
    AVG_SPEED_KMH = 35.0  # ciudad mexicana promedio con tráfico

    def _haversine_km(self, lat1, lon1, lat2, lon2):
        """Distancia en km entre 2 puntos lat/lon (fórmula Haversine)."""
        import math
        R = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlmb = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _destination_coords(self):
        """Coordenadas del sitio: prioriza alarm_event.device, fallback partner."""
        self.ensure_one()
        if self.alarm_event_id and self.alarm_event_id.device_id:
            dev = self.alarm_event_id.device_id
            if dev.latitude and dev.longitude:
                return dev.latitude, dev.longitude
        if self.partner_id.partner_latitude and self.partner_id.partner_longitude:
            return self.partner_id.partner_latitude, self.partner_id.partner_longitude
        return None, None

    def _patrol_current_coords(self):
        """Lee coordenadas actuales del patrullero: 1) Traccar live, 2) last_gps_*."""
        self.ensure_one()
        # Intento 1: Traccar (live)
        loc = self.get_last_location_from_traccar()
        if loc and loc.get('lat') and loc.get('lon'):
            return loc['lat'], loc['lon']
        # Intento 2: cache last_gps_* del partner del technician
        if self.technician_id and self.technician_id.partner_id:
            p = self.technician_id.partner_id
            if p.last_gps_lat and p.last_gps_lng:
                return p.last_gps_lat, p.last_gps_lng
        return None, None

    def _compute_eta_minutes(self):
        """Calcula ETA en minutos. Devuelve int o None."""
        self.ensure_one()
        dest_lat, dest_lon = self._destination_coords()
        cur_lat, cur_lon = self._patrol_current_coords()
        if not (dest_lat and dest_lon and cur_lat and cur_lon):
            return None
        distance_km = self._haversine_km(cur_lat, cur_lon, dest_lat, dest_lon)
        if distance_km <= 0:
            return 0
        # ETA aproximado: distance / velocidad. Sumamos 50% por trafico/ruta real vs línea recta.
        hours = (distance_km / self.AVG_SPEED_KMH) * 1.5
        return max(1, int(round(hours * 60)))

    def action_send_eta_update(self, force=False):
        """Recalcula ETA y notifica al cliente si:
        - El ETA cambió ≥ 2 min desde el último, O force=True.
        - eta_updates_sent < MAX_ETA_UPDATES_PER_ORDER.
        - El cliente acepta notificaciones (notification_channel != 'none').
        Best-effort, no lanza."""
        self.ensure_one()
        if self.arrival_date:
            return False  # ya llegó, no tiene sentido
        if self.eta_updates_sent >= self.MAX_ETA_UPDATES_PER_ORDER and not force:
            return False
        if (self.partner_id.notification_channel or 'both') == 'none':
            return False
        eta = self._compute_eta_minutes()
        if eta is None:
            return False
        # Cambio material
        prev = self.last_eta_minutes or 0
        if not force and prev > 0 and abs(prev - eta) < 2:
            return False
        msg = (f"🛡️ *Sentinela: Patrullero en camino*\n\n"
               f"Hola *{self.partner_id.name}*, su patrullero está a aproximadamente "
               f"*{eta} minutos* de llegar a su domicilio (Folio: {self.name}).")
        res = self.partner_id.notify(message=msg)
        if any(res.values()):
            self.write({
                'last_eta_minutes': eta,
                'last_eta_at': fields.Datetime.now(),
                'eta_updates_sent': self.eta_updates_sent + 1,
            })
            self.message_post(body=f"📍 ETA enviada al cliente: {eta} min. Canales: {', '.join(c for c, ok in res.items() if ok)}.")
            return True
        return False

    @api.model
    def _cron_send_eta_updates(self):
        """Cron periódico: actualiza ETA de patrullas activas sin arribo aún."""
        orders = self.sudo().search([
            ('service_type', '=', 'patrol'),
            ('stage', 'in', ('assigned', 'in_progress')),
            ('arrival_date', '=', False),
            ('eta_updates_sent', '<', self.MAX_ETA_UPDATES_PER_ORDER),
        ])
        sent = 0
        for o in orders:
            if o.action_send_eta_update():
                sent += 1
        return sent

    def get_last_location_from_traccar(self):
        """ Obtiene la última posición de la unidad de patrulla desde Traccar.

        Prioridad: la unidad elegida en la orden (celular o vehículo del catálogo);
        si no hay, el celular configurado en el patrullero (compatibilidad).
        """
        self.ensure_one()
        traccar_id = (self.patrol_unit_id.traccar_device_id
                      or self.technician_id.partner_id.traccar_device_id)
        if not traccar_id:
            return False
        
        import requests
        from requests.auth import HTTPBasicAuth

        # Config de la API de Traccar (Ajustes de Central → Radar SentiCar / Traccar).
        # Fallback a los valores históricos si no se ha configurado.
        ICP = self.env['ir.config_parameter'].sudo()
        base = (ICP.get_param('sentinela.traccar_api_url') or 'http://172.20.0.2:8082').rstrip('/')
        user = ICP.get_param('sentinela.traccar_api_user') or 'admin'
        password = ICP.get_param('sentinela.traccar_api_password') or 'admin'
        url = f"{base}/api/positions"
        params = {'deviceId': traccar_id}

        try:
            res = requests.get(url, params=params, auth=HTTPBasicAuth(user, password), timeout=5)
            if res.ok and res.json():
                pos = res.json()[0]
                lat = pos.get('latitude') or 0.0
                lon = pos.get('longitude') or 0.0
                # Traccar devuelve 0,0 ("isla nula" frente a África) cuando el dispositivo
                # aún no tiene fix GPS real. No es una posición: trátalo como sin señal.
                if abs(lat) < 0.0001 and abs(lon) < 0.0001:
                    return False
                return {
                    'lat': lat,
                    'lon': lon,
                    'speed': pos.get('speed'),
                    'last_update': pos.get('fixTime')
                }
        except:
            pass
        return False

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

class SentinelaFsmWorkLog(models.Model):
    _name = 'sentinela.fsm.work.log'
    _description = 'Bitácora de Trabajo FSM'
    _order = 'date desc'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', ondelete='cascade', required=True)
    technician_id = fields.Many2one('res.users', string='Técnico', default=lambda self: self.env.user)
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now)
    notes = fields.Text(string='Notas / Actividad')
    
    stage_at_moment = fields.Selection([
        ('new', 'Nueva'),
        ('assigned', 'Asignada'),
        ('in_progress', 'En Proceso'),
        ('paused', 'Pausada'),
        ('done', 'Finalizada'),
        ('cancel', 'Cancelada')
    ], string='Estado al Registrar')
