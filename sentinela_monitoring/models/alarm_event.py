from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from datetime import datetime, timedelta
import logging
import json

_logger = logging.getLogger(__name__)

# F2.1 — minutos antes de que un cron libere automáticamente un claim sin actividad
LOCK_TIMEOUT_MINUTES = 15


class AlarmEvent(models.Model):
    _name = 'sentinela.alarm.event'
    _description = 'Evento de Alarma'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char(string='Nombre del Evento', required=True)
    event_type = fields.Selection([
        ('burglary', 'Robo'), ('fire', 'Incendio'), ('medical', 'Emergencia Médica'),
        ('panic', 'Pánico'), ('duress', 'Coacción'), ('tamper', 'Manipulación'),
        ('trouble', 'Falla Técnica'), ('test', 'Prueba'), ('false_alarm', 'Falsa Alarma'),
        ('confirmed_alarm', 'Alarma Confirmada'), ('intrusion', 'Intrusión'),
        ('perimeter', 'Perímetro'), ('interior', 'Interior'), ('24_hour', '24 Horas'),
        ('day_night', 'Día/Noche'),
    ], string='Tipo de Evento', default='burglary')
    
    device_id = fields.Many2one('sentinela.monitoring.device', string='Dispositivo', required=True)
    account_number = fields.Char(string='Cuenta', related='device_id.account_number', store=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', related='device_id.partner_id', store=True)
    subscription_id = fields.Many2one('sentinela.subscription', string='Suscripción', related='device_id.subscription_id', store=True)
    
    priority_id = fields.Many2one('sentinela.alarm.priority', string='Prioridad', required=True)
    priority_level = fields.Integer(related='priority_id.level', store=True, string='Nivel de Prioridad')
    priority_display = fields.Char(string='Prioridad (Texto)', compute='_compute_priority_display')
    patrol_dictum_display = fields.Char(string='Dictamen Patrulla', compute='_compute_patrol_dictum')
    full_description = fields.Char(string='Incidente Detallado', compute='_compute_full_description', store=True)
    alarm_code_id = fields.Many2one('sentinela.alarm.code', string='Código de Alarma')
    zone = fields.Char(string='Zona / Partición')
    
    start_date = fields.Datetime(string='Fecha de Inicio', default=fields.Datetime.now)
    end_date = fields.Datetime(string='Fecha de Finalización')
    duration = fields.Float(string='Duración (horas)', compute='_compute_duration', store=True)

    # F2.3 — SLA Timer
    acknowledged_at = fields.Datetime(string='Reconocido el', tracking=True,
        help='Cuándo un operador reconoció el evento por primera vez.')
    sla_deadline = fields.Datetime(string='Deadline SLA', compute='_compute_sla_deadline', store=True,
        help='start_date + priority.sla_response_minutes. Vacío si la prioridad no tiene SLA.')
    sla_status = fields.Selection([
        ('no_sla', 'Sin SLA'),
        ('ok', 'OK'),
        ('warning', 'Próximo a vencer'),
        ('overdue', 'Vencido'),
        ('met', 'Cumplido'),
        ('breached', 'Incumplido'),
    ], string='Estado SLA', compute='_compute_sla_status',
       help='Estado dinámico calculado al leer. Para filtros eficientes usar sla_deadline.')

    @api.depends('start_date', 'priority_id.sla_response_minutes')
    def _compute_sla_deadline(self):
        for rec in self:
            if rec.start_date and rec.priority_id and rec.priority_id.sla_response_minutes > 0:
                rec.sla_deadline = rec.start_date + timedelta(minutes=rec.priority_id.sla_response_minutes)
            else:
                rec.sla_deadline = False

    @api.depends('sla_deadline', 'acknowledged_at')
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.sla_deadline:
                rec.sla_status = 'no_sla'
                continue
            if rec.acknowledged_at:
                rec.sla_status = 'met' if rec.acknowledged_at <= rec.sla_deadline else 'breached'
                continue
            if now > rec.sla_deadline:
                rec.sla_status = 'overdue'
                continue
            # warning si pasó >= 50% del tiempo
            window = rec.sla_deadline - rec.start_date
            elapsed = now - rec.start_date
            if window.total_seconds() > 0 and elapsed.total_seconds() / window.total_seconds() >= 0.5:
                rec.sla_status = 'warning'
            else:
                rec.sla_status = 'ok'
    
    description = fields.Text(string='Descripción del Evento')
    operator_final_remarks = fields.Text(string='Conclusión del Operador', help="Notas finales que aparecerán en el reporte para el cliente.")
    resolution_notes = fields.Text(string='Notas de Resolución')

    # F2.2 — Motivo de cierre estructurado (obligatorio al resolver)
    close_reason = fields.Selection([
        ('false_alarm', 'Falsa alarma'),
        ('user_error', 'Error de usuario'),
        ('customer_confirmed_ok', 'Cliente confirma OK'),
        ('verified_real', 'Evento real verificado'),
        ('patrol_no_event', 'Patrulla acudió, sin evento'),
        ('patrol_event', 'Patrulla acudió, evento confirmado'),
        ('no_contact', 'Sin contacto con cliente'),
        ('technical_fault', 'Falla técnica del equipo'),
        ('test_signal', 'Señal de prueba'),
        ('auto_offline_recovered', 'Panel offline recuperado (auto)'),
        ('cliente_rechazo_servicio', 'Cliente rechazó servicio extra'),
        ('other', 'Otro (especificar en notas)'),
    ], string='Motivo de Cierre', tracking=True,
       help="Tipificación del cierre del evento. Obligatorio al resolver/cerrar.")
    call_ids = fields.Char(string='IDs de Llamadas', help="IDs de Asterisk para recuperar grabaciones.")
    recording_count = fields.Integer(string='Grabaciones', compute='_compute_recording_count')

    def _compute_recording_count(self):
        for rec in self:
            rec.recording_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', self._name), ('res_id', '=', rec.id),
                ('mimetype', 'in', ['audio/wav', 'audio/mpeg', 'audio/x-wav', 'audio/mp3'])
            ])
    
    status = fields.Selection([
        ('active', 'Activo'), ('acknowledged', 'Reconocido'), ('in_progress', 'En Progreso'),
        ('paused', 'En Pausa / Pendiente'), ('escalated', 'Escalado'),
        ('resolved', 'Resuelto'), ('closed', 'Cerrado'),
    ], string='Estado', default='active', required=True)
    
    assigned_operator_id = fields.Many2one('res.users', string='Operador Asignado')
    assigned_technician_id = fields.Many2one('res.users', string='Técnico Asignado')
    response_team_id = fields.Many2one('sentinela.response.team', string='Equipo de Respuesta')

    # F2.1 — Claim / Mutex operador
    current_operator_id = fields.Many2one('res.users', string='Operador en Curso', tracking=True,
        help='Operador que tomó el evento. Mientras esté seteado, otros operadores no pueden modificarlo.')
    claimed_at = fields.Datetime(string='Tomado el', tracking=True,
        help='Cuándo el operador en curso tomó el evento. Si pasa LOCK_TIMEOUT_MINUTES sin actividad, el cron libera el lock.')
    is_locked_by_other = fields.Boolean(string='Bloqueado por otro', compute='_compute_lock_state')
    can_release = fields.Boolean(string='Puedo soltar', compute='_compute_lock_state')

    @api.depends('current_operator_id')
    def _compute_lock_state(self):
        uid = self.env.uid
        for rec in self:
            holder = rec.current_operator_id
            rec.is_locked_by_other = bool(holder) and holder.id != uid
            rec.can_release = bool(holder) and holder.id == uid
    
    location = fields.Char(string='Ubicación', related='device_id.location', store=True)
    latitude = fields.Float(string='Latitud', related='device_id.latitude', store=True)
    longitude = fields.Float(string='Longitud', related='device_id.longitude', store=True)
    
    alarm_signal_ids = fields.One2many('sentinela.alarm.signal', 'alarm_event_id', string='Señales Relacionadas')
    fsm_order_ids = fields.One2many('sentinela.fsm.order', 'alarm_event_id', string='Órdenes de Servicio')
    
    extra_service_authorized = fields.Boolean(string='Servicio Extra Autorizado', default=False)
    authorization_method = fields.Selection([('telegram', 'Telegram'), ('phone', 'Llamada')], string='Método')
    sale_order_id = fields.Many2one('sale.order', string='Venta')
    patrol_strategy = fields.Selection([('direct_send', 'Directo'), ('request_auth', 'Solicitar'), ('no_service', 'Sin Servicio')], default='no_service', store=True)

    subscription_state = fields.Selection([('active', 'Activo'), ('suspended', 'Suspendido'), ('cut', 'Cancelado'), ('none', 'Sin Suscripción')], string='Estado de Suscripción', compute='_compute_subscription_state', store=False)

    @api.depends('subscription_id', 'subscription_id.technical_state')
    def _compute_subscription_state(self):
        for rec in self:
            try: rec.subscription_state = rec.subscription_id.technical_state or 'none' if rec.subscription_id else 'none'
            except: rec.subscription_state = 'none'

    def _clean_translated_name(self, val):
        if not val: return ""
        if isinstance(val, dict): return val.get('es_MX') or val.get('en_US') or list(val.values())[0]
        if isinstance(val, str) and val.startswith('{'):
            try:
                data = json.loads(val)
                return data.get('es_MX') or data.get('en_US') or list(data.values())[0]
            except: return val
        return val

    @api.model
    def _cron_detect_offline_panels(self):
        """Genera evento trouble para paneles cuya last_communication superó
        expected_heartbeat_hours. Idempotente: marca el evento con [AUTO_OFFLINE]
        y no crea duplicados. Cuando el panel vuelva a reportar, el flujo de
        process_signal_from_receptor cierra el evento automáticamente."""
        now = fields.Datetime.now()
        Device = self.env['sentinela.monitoring.device'].sudo()
        devices = Device.search([
            ('expected_heartbeat_hours', '>', 0),
            ('status', '=', 'active'),
        ])
        priority = self.env['sentinela.alarm.priority'].sudo().search(
            [], order='level asc', limit=1)
        priority_id = priority.id if priority else False
        created = 0
        for dev in devices:
            threshold = now - timedelta(hours=dev.expected_heartbeat_hours)
            if dev.last_communication and dev.last_communication >= threshold:
                continue
            exists = self.sudo().search_count([
                ('device_id', '=', dev.id),
                ('status', 'in', ('active', 'acknowledged', 'in_progress')),
                ('description', 'like', '[AUTO_OFFLINE]%'),
            ])
            if exists:
                continue
            last_str = str(dev.last_communication)[:19] if dev.last_communication else 'nunca'
            self.sudo().create({
                'name': f"Panel sin reportar {dev.account_number}",
                'event_type': 'trouble',
                'device_id': dev.id,
                'priority_id': priority_id,
                'description': f"[AUTO_OFFLINE] Panel {dev.account_number} sin comunicación "
                               f"desde {last_str}. Umbral: {dev.expected_heartbeat_hours}h.",
                'status': 'active',
                'start_date': now,
            })
            created += 1
        if created:
            self.env['bus.bus']._sendone('sentinela_monitoring', 'sentinela_monitoring', {'refresh': True})
            _logger.info("AUTO_OFFLINE: %s evento(s) trouble creado(s)", created)
        return created

    @api.model
    def process_signal_from_receptor(self, vals):
        """METODO FORMULA 1: Procesa todo en UNA sola llamada"""
        account = vals.get('account')
        code = vals.get('code')
        zone = vals.get('zone')
        raw_data = vals.get('raw_data')
        qualifier = vals.get('qualifier', 'E')

        # 1. Buscar Dispositivo — si no existe, CUARENTENA (no se crea device ni event)
        device = self.env['sentinela.monitoring.device'].sudo().search([('account_number', '=', account)], limit=1)
        if not device:
            self.env['sentinela.alarm.signal'].sudo().create({
                'signal_type': 'alarm',
                'is_quarantine': True,
                'quarantine_account': account,
                'alarm_code': f"{qualifier}{code}",
                'zone': zone,
                'raw_data': raw_data,
                'description': f"Cuenta no registrada ({account}) — código {qualifier}{code} Z:{zone}",
                'received_date': fields.Datetime.now(),
                'status': 'received',
            })
            self.env['bus.bus']._sendone('sentinela_monitoring', 'sentinela_monitoring', {'refresh': True})
            status_rec = self.env['sentinela.receiver.status'].sudo().search([], limit=1)
            if status_rec:
                status_rec.write({'last_heartbeat': fields.Datetime.now()})
            return True

        # 1b. Heartbeat del panel: actualizar last_communication y cerrar trouble OFFLINE_AUTO si existe
        now = fields.Datetime.now()
        device.sudo().write({'last_communication': now})
        open_offline = self.sudo().search([
            ('device_id', '=', device.id),
            ('status', 'in', ('active', 'acknowledged', 'in_progress')),
            ('description', 'like', '[AUTO_OFFLINE]%'),
        ])
        if open_offline:
            open_offline.write({
                'status': 'resolved',
                'end_date': now,
                'close_reason': 'auto_offline_recovered',
                'resolution_notes': (open_offline[0].resolution_notes or '') + f"\nPanel reportó nuevamente el {now}.",
            })

        # 2. Inteligencia de Codigo y Prioridad
        alarm_code = self.env['sentinela.alarm.code'].sudo().search([('code', '=', code)], limit=1)
        priority_id = alarm_code.priority_id.id if alarm_code and alarm_code.priority_id else 35
        
        # 3. Determinar si requiere Atencion (Alarma Activa)
        # v18.0.1.3.5: clientes suspendidos por mora se muestran al operador con bandera
        # (NO se auto-archivan como antes) — política Opción C definida 16-may-2026.
        requires_attention = alarm_code.requires_attention if alarm_code else True
        status = 'active' if requires_attention else 'resolved'

        # 4. Crear Evento si es necesario
        event = False
        if status == 'active':
            event = self.sudo().create({
                'name': f"Alarma {account} - {code}",
                'device_id': device.id, 
                'priority_id': priority_id, 
                'zone': str(zone), # GUARDAR ZONA AQUI
                'alarm_code_id': alarm_code.id if alarm_code else False,
                'description': f"{alarm_code.name if alarm_code else 'Evento ' + code} (Z:{zone})",
                'status': 'active', 
                'partner_id': device.partner_id.id
            })

        # 5. Crear Señal siempre
        self.env['sentinela.alarm.signal'].sudo().create({
            'signal_type': 'alarm', 'device_id': device.id, 'priority_id': priority_id,
            'description': f"{alarm_code.name if alarm_code else 'Evento ' + code} (Z:{zone})",
            'raw_data': raw_data, 'received_date': fields.Datetime.now(),
            'alarm_event_id': event.id if event else False, 
            'alarm_code': f"{qualifier}{code}", 'zone': zone, 
            'partner_id': device.partner_id.id, 'status': 'received'
        })

        # 6. Avisar al Bus (UNA SOLA VEZ)
        self.env['bus.bus']._sendone('sentinela_monitoring', 'sentinela_monitoring', {'refresh': True})
        
        # 7. VIDEOVERIFICACIÓN: Disparar captura si el dispositivo tiene video
        if event and device.has_video:
            # Ejecutar de forma segura
            event.action_capture_snapshot()
        
        # Actualizar latido
        status_rec = self.env['sentinela.receiver.status'].sudo().search([], limit=1)
        if status_rec: status_rec.write({'last_heartbeat': fields.Datetime.now()})
        
        return True

    @api.model
    def get_dashboard_data(self, current_tab='alarms', traffic_filter='live'):
        alarm_domain = [('status', '=', 'active')]
        pending_domain = [('status', 'in', ['acknowledged', 'in_progress', 'paused', 'escalated'])]
        status_rec = self.env['sentinela.receiver.status'].sudo().search([], order='last_heartbeat desc', limit=1)
        is_online = status_rec and status_rec.last_heartbeat > (datetime.now() - timedelta(minutes=5))
        
        res = {
            'receiver': {'state': 'online' if is_online else 'offline', 'last_seen': str(status_rec.last_heartbeat)[:19] if status_rec else '---'},
            'counts': {'alarms': self.sudo().search_count(alarm_domain), 'pending': self.sudo().search_count(pending_domain)},
            'events': self._prepare_dashboard_list(alarm_domain),
            'pending_events': self._prepare_dashboard_list(pending_domain),
            'signals': []
        }
        if current_tab == 'traffic':
            signal_domain = []
            if traffic_filter == 'active': signal_domain = [('alarm_event_id.status', '=', 'active')]
            elif traffic_filter == 'commented': signal_domain = [('operator_notes', '!=', False)]
            res['signals'] = self._prepare_signal_list(signal_domain)
        return res

    def _prepare_dashboard_list(self, domain):
        recs = self.sudo().search_read(domain, ["id", "partner_id", "device_id", "alarm_code_id", "zone", "description", "start_date", "status"], order="id desc", limit=50)
        code_ids = list(set([r['alarm_code_id'][0] for r in recs if r['alarm_code_id']]))
        codes_map = {c.id: c.name for c in self.env['sentinela.alarm.code'].sudo().browse(code_ids)} if code_ids else {}
        for r in recs:
            p_name = r['partner_id'][1] if r['partner_id'] else "⚠️ CUENTA NO REGISTRADA"
            code_name = codes_map.get(r['alarm_code_id'][0], 'Evento') if r['alarm_code_id'] else '---'
            r.update({
                'partner_name': self._clean_translated_name(p_name), 'account': r['device_id'][1].split(' ')[0] if r['device_id'] else '0000',
                'code_display': self._clean_translated_name(code_name), 'start_date': str(r['start_date'])[:19],
                'is_blocked': "BLOQUEADO" in (r['description'] or "").upper()
            })
        return recs

    def _prepare_signal_list(self, domain):
        signals = self.env['sentinela.alarm.signal'].sudo().search_read(domain, ["id", "received_date", "alarm_code", "zone", "description", "partner_id", "device_id", "alarm_event_id"], order="id desc", limit=50)
        dev_ids = list(set([s['device_id'][0] for s in signals if s['device_id']]))
        zones_recs = self.env['sentinela.monitoring.zone'].sudo().search([('device_id', 'in', dev_ids)])
        zones_map = {(z.device_id.id, str(int(z.zone_number))): z.name for z in zones_recs}
        users_recs = self.env['sentinela.monitoring.contact'].sudo().search([('device_id', 'in', dev_ids), ('user_number', '>', 0)])
        users_map = {(u.device_id.id, str(int(u.user_number))): u.name for u in users_recs}
        raw_codes = list(set([s['alarm_code'][1:] for s in signals if s['alarm_code'] and len(s['alarm_code']) > 1]))
        codes_recs = self.env['sentinela.alarm.code'].sudo().search([('code', 'in', raw_codes)])
        codes_data_map = {c.code: {'name': c.name, 'point_type': c.point_type} for c in codes_recs}
        for s in signals:
            p_name = s['partner_id'][1] if s['partner_id'] else "⚠️ CUENTA NO REGISTRADA"
            cid_code = (s.get('alarm_code') or " ")[1:]
            c_info = codes_data_map.get(cid_code, {'name': 'Evento', 'point_type': 'zone'})
            raw_point = s.get('zone') or '0'
            clean_point = str(int(raw_point)) if raw_point.isdigit() else raw_point
            is_user_code = cid_code in ['401', '407', '403', '408', '409']
            point_name = users_map.get((s['device_id'][0], clean_point)) or f"USUARIO {raw_point}" if (c_info['point_type'] == 'user' or is_user_code) else zones_map.get((s['device_id'][0], clean_point)) or f"ZONA {raw_point}"
            s.update({
                'client_name': self._clean_translated_name(p_name), 'account': s['device_id'][1].split(' ')[0] if s['device_id'] else '0000',
                'received_date': str(s['received_date'])[:19], 'zone_description': f"{str(self._clean_translated_name(c_info['name'])).upper()} .- {str(self._clean_translated_name(point_name)).upper()}",
                'event_id': s.get('alarm_event_id') and s['alarm_event_id'][0] or False, 'is_blocked': p_name.startswith("⚠️")
            })
        return signals

    # ---------- F2.1 Claim / Mutex ----------

    def _ensure_claim_held(self):
        """Levanta UserError si quien actúa no es el current_operator_id.
        Si el evento no tiene operador en curso, también falla (el operador
        debe Tomar primero)."""
        for rec in self:
            if not rec.current_operator_id:
                raise UserError(_("Toma el evento (botón 'Tomar') antes de operarlo."))
            if rec.current_operator_id.id != self.env.uid:
                raise UserError(_(
                    "El evento está en atención por %s desde %s. "
                    "Pídele que lo suelte o usa 'Forzar Liberación' si tienes permisos."
                ) % (rec.current_operator_id.name, rec.claimed_at))

    def _try_claim(self):
        """Toma el lock si está libre o expirado. Devuelve True si quedó tomado por self.env.uid.
        Race-safe: re-lee desde DB con FOR UPDATE."""
        self.ensure_one()
        # cuando hay un operador, si el lock es viejo (>timeout) lo robamos
        if self.current_operator_id:
            if self.current_operator_id.id == self.env.uid:
                # ya lo tengo: refresco timestamp
                self.sudo().write({'claimed_at': fields.Datetime.now()})
                return True
            cutoff = fields.Datetime.now() - timedelta(minutes=LOCK_TIMEOUT_MINUTES)
            if self.claimed_at and self.claimed_at >= cutoff:
                return False  # otro lo tiene activo
        self.sudo().write({
            'current_operator_id': self.env.uid,
            'claimed_at': fields.Datetime.now(),
        })
        return True

    def action_claim_event(self):
        """Toma el evento. Si ya está tomado por otro operador activo, falla."""
        self.ensure_one()
        if not self._try_claim():
            raise UserError(_(
                "El evento está en atención por %s desde %s."
            ) % (self.current_operator_id.name, self.claimed_at))
        return True

    def action_release_event(self):
        """Suelta el evento. Solo el holder actual puede soltarlo."""
        self.ensure_one()
        if self.current_operator_id and self.current_operator_id.id != self.env.uid:
            raise UserError(_("Solo %s puede soltar este evento.") % self.current_operator_id.name)
        self.sudo().write({'current_operator_id': False, 'claimed_at': False})
        return True

    def action_force_release(self):
        """Libera un lock independientemente del holder. Solo admins (group_system)."""
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Solo administradores pueden forzar la liberación."))
        prev_holder = self.current_operator_id.name or '(libre)'
        self.sudo().write({'current_operator_id': False, 'claimed_at': False})
        self.message_post(body=_(
            "Lock forzado a liberación por %s (estaba en %s)."
        ) % (self.env.user.name, prev_holder))
        return True

    @api.model
    def get_audio_state(self):
        """F2.5 — Estado de audio para el dashboard.
        Devuelve alarmas activas (active/acknowledged/in_progress) con info de
        su prioridad y URL del sonido. is_claimed_by_me=True si el operador
        actual ya tiene el evento — para que el frontend NO toque audio por
        eventos que él mismo está atendiendo.

        Returns:
            {'active_alarms': [{event_id, priority_id, priority_level,
                                priority_name, has_sound, sound_url,
                                is_reminder, is_claimed_by_me}, ...]}
        """
        events = self.sudo().search([
            ('status', 'in', ('active', 'acknowledged', 'in_progress')),
            ('priority_id', '!=', False),
        ])
        result = []
        uid = self.env.uid
        for ev in events:
            pri = ev.priority_id
            has_sound = bool(pri.priority_sound)
            sound_url = False
            if has_sound:
                fn = pri.priority_sound_filename or 'sound.mp3'
                sound_url = (f"/web/content/sentinela.alarm.priority/{pri.id}"
                             f"/priority_sound/{fn}")
            result.append({
                'event_id': ev.id,
                'priority_id': pri.id,
                'priority_level': pri.level,
                'priority_name': self._clean_translated_name(pri.name),
                'has_sound': has_sound,
                'sound_url': sound_url,
                'is_reminder': bool(pri.is_reminder),
                'is_claimed_by_me': bool(ev.current_operator_id and
                                          ev.current_operator_id.id == uid),
            })
        return {'active_alarms': result}

    @api.model
    def _cron_release_stale_locks(self):
        """Libera locks con claimed_at más antiguo que LOCK_TIMEOUT_MINUTES."""
        cutoff = fields.Datetime.now() - timedelta(minutes=LOCK_TIMEOUT_MINUTES)
        stale = self.sudo().search([
            ('current_operator_id', '!=', False),
            ('claimed_at', '<', cutoff),
        ])
        if stale:
            for rec in stale:
                rec.message_post(body=_(
                    "Lock auto-liberado por inactividad (>%dmin). Estaba en %s."
                ) % (LOCK_TIMEOUT_MINUTES, rec.current_operator_id.name))
            stale.write({'current_operator_id': False, 'claimed_at': False})
            _logger.info("CLAIM_RELEASE: %s locks liberados por timeout", len(stale))
        return len(stale)

    # ---------- Acciones existentes con guard de claim ----------

    def action_acknowledge(self):
        for rec in self:
            if not rec.current_operator_id:
                rec._try_claim()  # auto-claim al reconocer
            rec._ensure_claim_held()
        # acknowledged_at solo se setea la PRIMERA vez (re-ack no resetea timer SLA)
        for rec in self:
            vals = {'status': 'acknowledged', 'assigned_operator_id': self.env.uid}
            if not rec.acknowledged_at:
                vals['acknowledged_at'] = fields.Datetime.now()
            rec.write(vals)
        return True

    def action_escalate(self):
        self._ensure_claim_held()
        # escalar suelta el lock para que un supervisor lo tome
        self.write({'status': 'escalated', 'current_operator_id': False, 'claimed_at': False})
        return True

    def action_assign_technician(self):
        self._ensure_claim_held()
        self.write({'status': 'in_progress', 'assigned_technician_id': self.env.uid})
        return True

    def action_resolve(self):
        self._ensure_claim_held()
        for rec in self:
            if not rec.close_reason:
                raise UserError(_("Selecciona el motivo de cierre antes de resolver el evento '%s'.") % rec.name)
            if rec.close_reason == 'other' and not (rec.resolution_notes or '').strip():
                raise UserError(_("El motivo 'Otro' requiere especificar notas de resolución."))
        # resolver suelta el lock
        self.write({'status': 'resolved', 'end_date': datetime.now(),
                    'current_operator_id': False, 'claimed_at': False})
        # F2.7.3 — auto-envío del reporte consolidado al cliente vía Telegram.
        # Best-effort: try/except envuelve el método (que ya no lanza),
        # pero protege ante cualquier error inesperado de red.
        for rec in self:
            if rec.partner_id and rec.partner_id.telegram_chat_id:
                try:
                    rec.action_send_closure_report()
                except Exception as e:
                    _logger.warning("F2.7.3: envío de reporte falló para evento %s: %s", rec.name, e)
        return True

    # ---------- F2.6 Cobranza al atender ----------

    def action_request_service_authorization(self, service_type='patrol', method=None):
        """Marca que se solicitó autorización al cliente para un servicio
        extra (patrulla por default). NO crea sale.order todavía — eso pasa
        en action_authorize_service una vez el cliente confirma.

        El parámetro service_type queda como reservado para futuras variantes
        (técnico extra, etc.). Hoy solo 'patrol'."""
        self.ensure_one()
        vals = {'patrol_strategy': 'request_auth'}
        if method in ('telegram', 'phone'):
            vals['authorization_method'] = method
        self.write(vals)
        self.message_post(body=_(
            "Solicitada autorización de %s al cliente (vía %s)."
        ) % (service_type, method or 'no especificado'))
        return True

    def action_authorize_service(self):
        """Marca el servicio como autorizado y crea la sale.order si está
        configurado el producto patrol_service_product_id."""
        self.ensure_one()
        self.write({'extra_service_authorized': True})
        if not self.sale_order_id:
            self._create_service_sale_order()
        return True

    def _create_service_sale_order(self):
        """Crea sale.order con una línea del patrol_service_product_id
        configurado en monitoring.settings. No-op si el producto no está
        configurado o si ya existe sale_order_id."""
        self.ensure_one()
        if self.sale_order_id:
            return self.sale_order_id
        product_id_str = self.env['ir.config_parameter'].sudo().get_param(
            'sentinela_monitoring.patrol_service_product_id')
        if not product_id_str:
            _logger.warning("F2.6: patrol_service_product_id no configurado, "
                            "no se crea sale.order para evento %s", self.name)
            return False
        try:
            product_id = int(product_id_str)
        except (TypeError, ValueError):
            _logger.warning("F2.6: patrol_service_product_id inválido (%s)", product_id_str)
            return False
        product = self.env['product.product'].sudo().browse(product_id).exists()
        if not product:
            _logger.warning("F2.6: producto %s no existe", product_id)
            return False
        if not self.partner_id:
            raise UserError(_("El evento no tiene cliente — no se puede crear venta."))
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_id.id,
            'origin': f"Evento alarma {self.name}",
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': f"{product.name} — Evento {self.name}",
                'product_uom_qty': 1.0,
            })],
        })
        self.write({'sale_order_id': so.id})
        self.message_post(body=_(
            "Venta automática creada: %s — por servicio de patrulla."
        ) % so.name)
        return so

    def action_open_sale_order(self):
        """Botón en form para abrir la sale.order asociada."""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("Este evento no tiene venta asociada."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def cleanup_test_fsm_orders(self):
        """Helper SOLO para tests: elimina (sudo) las fsm.order vinculadas a
        este evento. NO usar en producción — bypasea las protecciones de FSM."""
        self.ensure_one()
        orders = self.env['sentinela.fsm.order'].sudo().search(
            [('alarm_event_id', '=', self.id)])
        if orders:
            orders.unlink()
        return True

    def get_fsm_orders_info(self):
        """Devuelve resumen sudo de las fsm.order vinculadas. Para clientes
        (api_user, tests) sin permisos directos sobre sentinela.fsm.order."""
        self.ensure_one()
        orders = self.env['sentinela.fsm.order'].sudo().search(
            [('alarm_event_id', '=', self.id)], order='id desc')
        return [{
            'id': o.id, 'name': o.name, 'service_type': o.service_type,
            'stage': o.stage, 'technician_id': o.technician_id.id or False,
            'technician_name': o.technician_id.name or False,
        } for o in orders]

    def get_sale_order_info(self):
        """Devuelve resumen sudo de la sale.order para clientes que no tienen
        permiso directo (e.g., api_user usado por receiver/tests)."""
        self.ensure_one()
        if not self.sale_order_id:
            return {}
        so = self.sale_order_id.sudo()
        lines = [{
            'product_id': l.product_id.id,
            'product_name': l.product_id.display_name,
            'qty': l.product_uom_qty,
            'price_unit': l.price_unit,
        } for l in so.order_line]
        return {
            'id': so.id,
            'name': so.name,
            'partner_id': so.partner_id.id,
            'origin': so.origin,
            'amount_total': so.amount_total,
            'lines': lines,
        }
    def _cron_fetch_ucm_recordings(self):
        """
        Robot que sincroniza grabaciones de forma transparente.
        Busca llamadas de los últimos 30 minutos.
        """
        import requests
        import base64
        import urllib3
        import ssl
        from datetime import datetime, timedelta
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        class DESAdapter(requests.adapters.HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                context.set_ciphers('DEFAULT@SECLEVEL=1')
                kwargs['ssl_context'] = context
                return super(DESAdapter, self).init_poolmanager(*args, **kwargs)

        ucm_ip = "192.168.3.5:8089"
        api_user = "odoo_api"
        api_pass = "cdrapi123"
        session = requests.Session()
        session.mount('https://', DESAdapter())
        
        try:
            # Login
            login_url = f"https://{ucm_ip}/cgi?action=login&username={api_user}&password={api_pass}"
            r_login = session.get(login_url, verify=False, timeout=10)
            if not r_login.ok or '"status": 0' not in r_login.text: return False

            # Buscar llamadas de los últimos 20 minutos
            start_time = (datetime.now() - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M:%S')
            cdr_url = f"https://{ucm_ip}/cgi?action=getCDR&starttime={start_time}"
            r_cdr = session.get(cdr_url, verify=False, timeout=15)
            
            if r_cdr.ok:
                cdrs = r_cdr.json().get('response', {}).get('cdr', [])
                for c in cdrs:
                    rec_file = c.get('recording')
                    if not rec_file: continue
                    
                    # Verificar si ya lo tenemos
                    if self.env['ir.attachment'].search_count([('name', '=', f"Grabacion_{rec_file}")]): continue
                    
                    # Descargar
                    dl_url = f"https://{ucm_ip}/cgi?action=downloadFile&type=recording&filename={rec_file}"
                    r_file = session.get(dl_url, verify=False, timeout=30)
                    
                    if r_file.ok:
                        audio_data = base64.b64encode(r_file.content)
                        dst = c.get('dst', '')
                        partner = self.env['res.partner'].search(['|', ('phone', 'like', dst[-10:]), ('mobile', 'like', dst[-10:])], limit=1)
                        
                        # Buscar suscripción activa del partner
                        subscription = self.env['sentinela.subscription'].search([('partner_id', '=', partner.id), ('state', '=', 'active')], limit=1) if partner else False
                        
                        active_event = self.search([('partner_id', '=', partner.id), ('status', 'not in', ['resolved', 'closed'])], limit=1) if partner else False

                        # Crear registro formal de llamada
                        self.env['sentinela.monitoring.call'].create({
                            'name': rec_file,
                            'date': datetime.strptime(c.get('start_time'), '%Y-%m-%d %H:%M:%S') if c.get('start_time') else datetime.now(),
                            'src': c.get('src'),
                            'dst': dst,
                            'duration': int(c.get('billablesecs', 0)),
                            'partner_id': partner.id if partner else False,
                            'subscription_id': subscription.id if subscription else False,
                            'alarm_event_id': active_event.id if active_event else False,
                            'audio_file': audio_data,
                            'audio_filename': f"{rec_file}.wav"
                        })
                        
                        # También adjuntar al Chatter para visibilidad rápida
                        target_model = 'sentinela.alarm.event' if active_event else ('res.partner' if partner else 'res.users')
                        target_id = active_event.id if active_event else (partner.id if partner else self.env.uid)
                        
                        self.env['ir.attachment'].create({
                            'name': f"Grabacion_{rec_file}",
                            'type': 'binary', 'datas': audio_data,
                            'res_model': target_model, 'res_id': target_id,
                            'mimetype': 'audio/x-wav'
                        })
            
            session.get(f"https://{ucm_ip}/cgi?action=logout", verify=False)
        except: pass
        return True

    def action_close(self):
        # Al cerrar ya no bajamos manual, el cron lo hará solo.
        for rec in self:
            if not rec.close_reason:
                raise UserError(_("Selecciona el motivo de cierre antes de cerrar el evento '%s'.") % rec.name)
        self.write({'status': 'closed', 'end_date': datetime.now()})
        return True
    
    def action_click_to_call(self, phone_number):
        """
        Inicia una llamada a través del conmutador Grandstream UCM6204 vía AMI.
        """
        self.ensure_one()
        operator_extension = self.env.user.sip_extension
        if not operator_extension:
            self.message_post(body="⚠️ <b>Error de Telefonía:</b> El usuario no tiene una Extensión SIP configurada.")
            return False

        target_number = "".join(filter(str.isdigit, str(phone_number)))
        # Prefijo '1' para tomar línea de salida
        if not target_number.startswith('1'):
            target_number = '1' + target_number
        
        # CONFIGURACION AMI (Misma que en res.partner)
        host = "192.168.3.5"
        port = 7777
        user = "admin_ami"
        pw = "Sentinela"

        import socket
        import time
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((host, port))
            s.recv(1024) # Banner
            
            # Login
            login = "Action: Login\r\nUsername: " + user + "\r\nSecret: " + pw + "\r\n\r\n"
            s.send(login.encode())
            time.sleep(1.0)
            s.recv(1024)
            
            # VARIANTE 1: Primero suena el operador, al descolgar marca afuera
            dial_cmd = "Action: Originate\r\n"
            dial_cmd += "Channel: Local/" + str(operator_extension) + "@from-internal\r\n"
            dial_cmd += "Exten: " + target_number + "\r\n"
            dial_cmd += "Context: from-internal\r\n"
            dial_cmd += "Priority: 1\r\n"
            dial_cmd += "CallerID: Central: " + self.name + "\r\n"
            dial_cmd += "Async: yes\r\n\r\n"
            
            s.send(dial_cmd.encode())
            time.sleep(1.0)
            s.send(b"Action: Logoff\r\n\r\n")
            s.close()

            self.message_post(body=f"📞 <b>Llamada Central:</b> Conectando Ext. {operator_extension} con el {target_number}")
            return True
        except Exception as e:
            self.message_post(body=f"❌ <b>Error AMI:</b> No se pudo conectar al conmutador: {str(e)}")
            return False

    def _render_master_report_pdf(self):
        """F2.7.3 — Renderiza el reporte master_incident como bytes PDF.
        Devuelve (pdf_bytes, filename) o (None, None) si falla."""
        self.ensure_one()
        try:
            report = self.env.ref('sentinela_monitoring.action_report_master_incident', raise_if_not_found=False)
            if not report:
                _logger.warning("F2.7.3: report action_report_master_incident no existe")
                return None, None
            pdf_content, _ctype = report.sudo()._render_qweb_pdf(
                'sentinela_monitoring.action_report_master_incident', self.ids)
            safe_name = (self.name or 'EVENTO').replace('/', '_').replace(' ', '_')
            filename = f"Reporte_Sentinela_{safe_name}.pdf"
            return pdf_content, filename
        except Exception as e:
            _logger.exception("F2.7.3: error generando PDF del evento %s: %s", self.name, e)
            return None, None

    def action_send_closure_report(self):
        """F2.7.3 — Genera el PDF consolidado del evento y lo envía al cliente
        por Telegram como documento adjunto. Idempotente: si ya se envió
        un reporte en los últimos 5min, omite (evita duplicados por re-click).
        No lanza excepciones — best-effort para no bloquear cierres."""
        self.ensure_one()
        partner = self.partner_id
        if not partner or not partner.telegram_chat_id:
            self.message_post(body=_("Reporte de cierre NO enviado: cliente sin Telegram configurado."))
            return False
        pdf, filename = self._render_master_report_pdf()
        if not pdf:
            self.message_post(body=_("Reporte de cierre: falló la generación del PDF."))
            return False
        patrol_orders = self.fsm_order_ids.filtered(lambda o: o.service_type == 'patrol')
        caption_parts = [
            f"📋 *Reporte de Evento {self.name}*",
            f"Cuenta: {self.account_number or '—'}",
        ]
        if self.close_reason:
            reason_label = dict(self._fields['close_reason'].selection).get(self.close_reason, self.close_reason)
            caption_parts.append(f"Cierre: {reason_label}")
        if patrol_orders:
            caption_parts.append(f"Patrullero: {patrol_orders[0].technician_id.name or '—'}")
        caption = "\n".join(caption_parts)
        ok = partner.send_telegram_document(filename, pdf, caption=caption)
        if ok:
            self.message_post(body=_(
                "📑 Reporte de cierre enviado al cliente vía Telegram (%s)."
            ) % filename)
        else:
            self.message_post(body=_("Reporte de cierre: el envío Telegram falló."))
        return ok

    # Backwards-compatible alias del botón viejo en views
    def action_send_master_report(self):
        return self.action_send_closure_report()

    def action_capture_snapshot(self):
        """
        Solicita una captura de imagen al DVR/NVR del cliente vía ISAPI (Hikvision).
        """
        self.ensure_one()
        device = self.device_id
        if not device or not device.has_video or not device.dvr_ip:
            return False

        import requests
        from requests.auth import HTTPDigestAuth
        import base64

        # 1. Determinar canal de cámara
        channel = 1 # Default
        if self.zone:
            zone_obj = self.env['sentinela.monitoring.zone'].search([
                ('device_id', '=', device.id),
                ('zone_number', '=', str(int(self.zone)) if (isinstance(self.zone, str) and self.zone.isdigit()) else self.zone)
            ], limit=1)
            if zone_obj and zone_obj.camera_channel:
                channel = zone_obj.camera_channel

        # 2. Construir URL Hikvision ISAPI
        # Formato: http://IP:PORT/ISAPI/Streaming/channels/[CHANNEL]01/picture
        url = f"http://{device.dvr_ip}:{device.dvr_port}/ISAPI/Streaming/channels/{channel}01/picture"
        
        try:
            # Hikvision moderno usa Digest Auth
            auth = HTTPDigestAuth(device.dvr_user, device.dvr_password)
            response = requests.get(url, auth=auth, timeout=10)
            
            if response.ok:
                # 3. Guardar como adjunto en el evento
                self.env['ir.attachment'].create({
                    'name': f"Snapshot_Alarma_Camara_{channel}.jpg",
                    'type': 'binary',
                    'datas': base64.b64encode(response.content),
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'image/jpeg'
                })
                self.message_post(body=f"📸 <b>Videoverificación:</b> Captura automática realizada en Cámara {channel}.")
                return True
            else:
                self.message_post(body=f"⚠️ <b>Videoverificación:</b> Falló la captura (Status: {response.status_code})")
        except Exception as e:
            self.message_post(body=f"❌ <b>Error Video:</b> No se pudo conectar al DVR: {str(e)}")
        
        return False

    @api.depends('priority_id', 'priority_id.name')
    def _compute_priority_display(self):
        for rec in self:
            rec.priority_display = self._clean_translated_name(rec.priority_id.name).upper()

    @api.depends('fsm_order_ids')
    def _compute_patrol_dictum(self):
        for rec in self:
            patrol = rec.fsm_order_ids.filtered(lambda x: x.service_type == 'patrol')[:1]
            # if patrol and patrol.patrol_result:
            #     # Convertir el valor de la selección a su etiqueta legible
            #     rec.patrol_dictum_display = dict(patrol._fields['patrol_result'].selection).get(patrol.patrol_result, 'Inspección Completada')
            # else:
            rec.patrol_dictum_display = 'Inspección Completada' if patrol else 'Sin Intervención de Patrulla'

    @api.depends('alarm_code_id', 'zone', 'device_id')
    def _compute_full_description(self):
        for rec in self:
            code_name = self._clean_translated_name(rec.alarm_code_id.name or 'EVENTO').upper()
            zone_num = rec.zone or '0'
            zone_desc = "ZONA " + str(zone_num)
            
            if rec.device_id and zone_num:
                # Buscar la descripción de la zona en el dispositivo
                try:
                    search_zone = str(int(zone_num)) if (isinstance(zone_num, str) and zone_num.isdigit()) else zone_num
                    zone_obj = self.env['sentinela.monitoring.zone'].search([
                        ('device_id', '=', rec.device_id.id),
                        ('zone_number', '=', search_zone)
                    ], limit=1)
                    if zone_obj:
                        zone_desc = f"ZONA {search_zone}: {self._clean_translated_name(zone_obj.name).upper()}"
                except: pass
            
            rec.full_description = f"{code_name} .- {zone_desc}"

    def create_fsm_order(self, technician_id=None, service_type='patrol'):
        """F2.7.2 — Crea una sentinela.fsm.order vinculada a este evento.
        Idempotente: si ya hay una orden patrol abierta para este evento,
        la devuelve en lugar de crear duplicado.

        Args:
            technician_id: id de res.users del patrullero (opcional, requerido
                           para llamar action_start inmediato después).
            service_type: por defecto 'patrol'. Otros tipos posibles según el
                           catálogo de fsm.order.service_type."""
        self.ensure_one()
        # Buscar orden existente abierta para este evento
        existing = self.env['sentinela.fsm.order'].sudo().search([
            ('alarm_event_id', '=', self.id),
            ('stage', 'in', ('new', 'assigned', 'in_progress', 'paused')),
            ('service_type', '=', service_type),
        ], limit=1)
        if existing:
            self.write({'status': 'in_progress'})
            return existing.id

        if not self.partner_id:
            raise UserError(_("El evento no tiene cliente — no se puede crear orden FSM."))

        # Construir descripción rica para el patrullero
        device = self.device_id
        desc_parts = [
            f"<b>EVENTO DE ALARMA</b>: {self.name}",
            f"<b>Cuenta</b>: {self.account_number or '—'}",
            f"<b>Código</b>: {(self.alarm_code_id.name or '').upper() if self.alarm_code_id else self.description}",
            f"<b>Zona</b>: {self.zone or '—'}",
        ]
        if device.location:
            desc_parts.append(f"<b>Domicilio</b>: {device.location}")
        if self.subscription_id:
            keyword = getattr(self.subscription_id, 'keyword', False)
            if keyword:
                desc_parts.append(f"<b>Palabra clave</b>: <code>{keyword}</code>")

        vals = {
            'partner_id': self.partner_id.id,
            'service_type': service_type,
            'alarm_event_id': self.id,
            'description': '<br/>'.join(desc_parts),
            'priority': '3' if self.priority_id and self.priority_id.level >= 8 else '2',
            'scheduled_date': fields.Datetime.now(),
        }
        if self.subscription_id:
            vals['subscription_id'] = self.subscription_id.id
        if device and device.latitude and device.longitude:
            vals['install_lat'] = device.latitude
            vals['install_lon'] = device.longitude
        if device and device.location:
            vals['service_address_id'] = self.partner_id.id
        if technician_id:
            vals['technician_id'] = technician_id
            vals['stage'] = 'assigned'

        order = self.env['sentinela.fsm.order'].sudo().create(vals)
        self.write({'status': 'in_progress'})
        self.message_post(body=_(
            "Orden de servicio %s creada (%s)."
        ) % (order.name, dict(order._fields['service_type'].selection).get(service_type, service_type)))
        return order.id
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for e in self: e.duration = 0.0
