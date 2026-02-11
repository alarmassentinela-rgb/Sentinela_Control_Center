from odoo import http
from odoo.http import request
import json
from datetime import datetime

class AlarmSignalController(http.Controller):
    
    @http.route('/api/alarm/signals', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_alarm_signal(self, **kwargs):
        """
        Endpoint para recibir señales de alarma desde dispositivos de monitoreo
        """
        try:
            # Verificar autenticación por token
            token = request.httprequest.headers.get('Authorization')
            if not token or not self._validate_token(token):
                return {'status': 'error', 'message': 'Unauthorized'}
            
            # Obtener datos del cuerpo de la solicitud
            data = request.jsonrequest
            
            # Validar datos requeridos
            required_fields = ['device_id', 'signal_type']
            for field in required_fields:
                if field not in data:
                    return {'status': 'error', 'message': f'Missing required field: {field}'}
            
            # Buscar dispositivo
            device = request.env['sentinela.monitoring.device'].sudo().search(
                [('account_number', '=', data['device_id'])], limit=1
            )
            
            # Preparar datos de la señal
            signal_data = {
                'signal_type': data.get('signal_type'),
                'priority': data.get('priority', 'medium'),
                'raw_data': json.dumps(data),
                'received_date': datetime.now(),
            }

            if device:
                signal_data['device_id'] = device.id
                signal_data['description'] = data.get('description', '')
            else:
                # Caso: Cuenta desconocida
                signal_data['description'] = f"[CUENTA DESCONOCIDA: {data['device_id']}] " + data.get('description', '')
                signal_data['priority'] = 'high' # Alertar al operador
            
            signal = request.env['sentinela.alarm.signal'].sudo().create(signal_data)
            
            # Crear evento de alarma si es necesario (solo si hay dispositivo o si forzamos evento huérfano)
            if data.get('create_event', False):
                event_data = {
                    'name': f'Evento-{signal.name}',
                    'event_type': self._map_signal_to_event_type(data.get('signal_type')),
                    'priority': signal_data['priority'],
                    'description': signal_data['description'],
                    'start_date': datetime.now(),
                }
                if device:
                    event_data['device_id'] = device.id
                
                event = request.env['sentinela.alarm.event'].sudo().create(event_data)
                signal.alarm_event_id = event.id
            
            # Enviar notificaciones
            if device:
                self._send_notifications(signal, device)
            
            return {
                'status': 'success',
                'message': 'Signal received successfully',
                'signal_id': signal.id,
                'signal_ref': signal.name
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _validate_token(self, token):
        """
        Validar token de autenticación
        """
        # Aquí iría la lógica para validar el token
        # Por ahora, simplemente retornamos True para fines de demostración
        return True
    
    def _map_signal_to_event_type(self, signal_type):
        """
        Mapear tipo de señal a tipo de evento
        """
        mapping = {
            'alarm': 'burglary',
            'fire': 'fire',
            'medical': 'medical',
            'panic': 'panic',
            'duress': 'duress',
            'tamper': 'tamper',
            'trouble': 'trouble',
            'test': 'test',
            'false_alarm': 'false_alarm',
        }
        return mapping.get(signal_type, 'burglary')
    
    def _send_notifications(self, signal, device):
        """
        Enviar notificaciones por correo electrónico y mensajes internos
        """
        # Enviar notificación al operador encargado
        operator_group = request.env.ref('base.group_system')  # Grupo de operadores
        operators = request.env['res.users'].sudo().search([('groups_id', 'in', operator_group.id)])
        
        for operator in operators:
            signal.send_push_notification(
                title="Nueva Señal de Alarma",
                message=f"Se ha recibido una nueva señal de alarma del dispositivo {device.device_id}",
                recipient_user=operator,
                notification_type='alarm'
            )
        
        # Enviar notificación al cliente si está disponible
        if device.partner_id:
            template = request.env.ref('sentinela_monitoring.mail_template_alarm_received', raise_if_not_found=False)
            if template:
                signal.with_context(lang=device.partner_id.lang).message_post_with_source(
                    template,
                    email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
                )