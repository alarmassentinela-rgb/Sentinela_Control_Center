from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class SentinelaMonitoringController(http.Controller):

    @http.route('/api/monitoring/signal', type='json', auth='none', methods=['POST'], csrf=False)
    def receive_signal(self, **kwargs):
        """
        Recibe una señal de alarma desde el receptor externo.
        Payload esperado:
        {
            'account': '1234',
            'code': '130',
            'partition': '01',
            'zone_user': '005',
            'protocol': 'contact_id'
        }
        """
        data = request.jsonrequest
        account = data.get('account')
        event_code = data.get('code')
        zone_num = int(data.get('zone_user', 0))
        partition = int(data.get('partition', 1))

        if not account or not event_code:
            return {'status': 'error', 'message': 'Missing account or code'}

        # 1. Buscar el dispositivo por número de cuenta (Sudo para saltar permisos de auth=none)
        device = request.env['sentinela.monitoring.device'].sudo().search([('account_number', '=', account)], limit=1)
        
        if not device:
            _logger.warning(f"MONITORING: Señal recibida de cuenta desconocida: {account}")
            return {'status': 'ignored', 'message': 'Account not found'}

        # 2. Buscar el significado del código
        code_ref = request.env['sentinela.alarm.code'].sudo().search([('code', '=', event_code)], limit=1)
        
        # 3. Buscar la zona
        zone = request.env['sentinela.monitoring.zone'].sudo().search([
            ('device_id', '=', device.id),
            ('zone_number', '=', zone_num),
            ('partition', '=', partition)
        ], limit=1)

        # 4. Registrar la señal cruda
        signal_vals = {
            'device_id': device.id,
            'name': f"{event_code} en Zona {zone_num}",
            'signal_type': code_ref.event_category if code_ref else 'alarm',
            'received_date': fields.Datetime.now(),
        }
        signal = request.env['sentinela.alarm.signal'].sudo().create(signal_vals)

        # 5. Si es una ALARMA (según el catálogo de códigos), crear un EVENTO para el operador
        if code_ref and code_ref.event_category == 'alarm':
            request.env['sentinela.alarm.event'].sudo().create({
                'name': f"{code_ref.name} - {zone.name if zone else 'Zona ' + str(data.get('zone_user'))}",
                'device_id': device.id,
                'event_type': 'burglary', # Simplificado por ahora
                'priority': code_ref.priority,
                'description': f"Señal recibida: {event_code}. Partición: {partition}. Zona/Usuario: {zone_num}",
            })
            _logger.info(f"MONITORING: ALARMA CREADA para cuenta {account}")

        return {'status': 'success', 'signal_id': signal.id}
