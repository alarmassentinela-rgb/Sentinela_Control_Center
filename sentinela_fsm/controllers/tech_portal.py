from odoo import http, _
from odoo.http import request
import logging
import base64

_logger = logging.getLogger(__name__)

class CustomerTracking(http.Controller):

    @http.route(['/rastreo/<string:token>', '/rastreo/<string:token>/'], type='http', auth="public", website=False, sitemap=False)
    def customer_tracking_view(self, token, **kw):
        """ Vista pública de rastreo simplificada """
        order = request.env['sentinela.fsm.order'].sudo().search([('tracking_token', '=', token)], limit=1)
        if not order or order.stage not in ['assigned', 'in_progress', 'paused']:
            return "<h3>El enlace de rastreo ha expirado o es inválido.</h3>"

        return request.render("sentinela_fsm.customer_tracking_map", {
            'order': order,
        })

    @http.route(['/rastreo/<string:token>/data'], type='json', auth="public", website=False)
    def customer_tracking_data(self, token, **kw):
        """ Datos de GPS para el mapa """
        order = request.env['sentinela.fsm.order'].sudo().search([('tracking_token', '=', token)], limit=1)
        if not order:
            return {'error': 'Not found'}
        
        location = order.get_last_location_from_traccar()
        if location:
            return {
                'lat': location['lat'],
                'lon': location['lon'],
                'speed': location['speed'],
                'status': order.stage
            }
        return {'error': 'No GPS signal'}

class TechnicianPortal(http.Controller):

    @http.route(['/tech/dashboard'], type='http', auth="user", website=True)
    def technician_dashboard(self, **kw):
        """ Dashboard principal para el técnico """
        user = request.env.user
        FsmOrder = request.env['sentinela.fsm.order']
        orders = FsmOrder.search([
            ('technician_id', '=', user.id), 
            ('stage', 'not in', ['done', 'cancel'])
        ], order='priority desc, scheduled_date asc')

        return request.render("sentinela_fsm.tech_dashboard", {
            'orders': orders,
            'user': user,
        })

    @http.route(['/tech/order/<int:order_id>'], type='http', auth="user", website=True)
    def technician_order_view(self, order_id, **kw):
        """ Vista de ejecución de la orden """
        order = request.env['sentinela.fsm.order'].browse(order_id)
        if not order.exists() or (order.technician_id.id != request.env.user.id and not request.env.user.has_group('sentinela_fsm.group_fsm_manager')):
            return request.redirect('/tech/dashboard')

        return request.render("sentinela_fsm.tech_order_view", {
            'order': order,
        })

    @http.route(['/tech/order/<int:order_id>/start'], type='http', auth="user", website=True, methods=['POST'])
    def technician_order_start(self, order_id, **kw):
        order = request.env['sentinela.fsm.order'].browse(order_id)
        if order.exists():
            order.action_start()
        return request.redirect(f'/tech/order/{order_id}')

    @http.route(['/tech/order/<int:order_id>/resume'], type='http', auth="user", website=True, methods=['POST'])
    def technician_order_resume(self, order_id, **kw):
        order = request.env['sentinela.fsm.order'].browse(order_id)
        if order.exists():
            order.action_resume()
        return request.redirect(f'/tech/order/{order_id}')

    @http.route(['/tech/order/<int:order_id>/arrival'], type='http', auth="user", website=True, methods=['POST'])
    def technician_order_arrival(self, order_id, **post):
        """ Registrar llegada al sitio vía GPS del móvil """
        order = request.env['sentinela.fsm.order'].browse(order_id)
        if order.exists():
            order.action_arrival()
            # Guardar coordenadas de llegada
            if post.get('lat') and post.get('lon'):
                order.write({
                    'arrival_lat': float(post.get('lat')),
                    'arrival_lon': float(post.get('lon')),
                })
        return request.redirect(f'/tech/order/{order_id}')

    @http.route(['/tech/order/<int:order_id>/save'], type='http', auth="user", website=True, methods=['POST'])
    def technician_order_save(self, order_id, **post):
        """ Guardar datos técnicos capturados en campo """
        order = request.env['sentinela.fsm.order'].browse(order_id)
        if not order.exists():
            return request.redirect('/tech/dashboard')

        vals = {
            'resolution_notes': post.get('resolution_notes'),
            'received_by_name': post.get('received_by_name'),
            'received_by_relationship': post.get('received_by_relationship'),
            'alarm_zones': post.get('alarm_zones'),
            'alarm_panel_brand': post.get('alarm_panel_brand'),
            'alarm_panel_model': post.get('alarm_panel_model'),
            'monitoring_account_number': post.get('monitoring_account_number'),
            'vehicle_plate': post.get('vehicle_plate'),
            'vehicle_brand': post.get('vehicle_brand'),
            'vehicle_model': post.get('vehicle_model'),
            'sim_iccid': post.get('sim_iccid'),
            'internet_antenna_mac': post.get('internet_antenna_mac'),
            'internet_router_serial': post.get('internet_router_serial'),
            'internet_pppoe_user': post.get('internet_pppoe_user'),
            'internet_signal_dbm': post.get('internet_signal_dbm'),
            'cctv_dvr_brand': post.get('cctv_dvr_brand'),
            'cctv_dvr_model': post.get('cctv_dvr_model'),
            'cctv_num_cameras': int(post.get('cctv_num_cameras')) if post.get('cctv_num_cameras') else 0,
            'cctv_storage': post.get('cctv_storage'),
            'cctv_remote_user': post.get('cctv_remote_user'),
            'cctv_remote_pass': post.get('cctv_remote_pass'),
            'patrol_result': post.get('patrol_result'),
            'is_forced_entry': True if post.get('is_forced_entry') == 'on' else False,
            'police_notified': True if post.get('police_notified') == 'on' else False,
            'install_lat': float(post.get('lat')) if post.get('lat') else 0.0,
            'install_lon': float(post.get('lon')) if post.get('lon') else 0.0,
        }
        # PROCESAR FIRMA
        signature = post.get('customer_signature')
        if signature and 'base64,' in signature:
            vals['customer_signature'] = signature.split('base64,')[1]

        # VALIDACIÓN DE CIERRE: Bloquear si intenta finalizar sin firma
        if post.get('action') == 'finish' and not order.customer_signature and not vals.get('customer_signature'):
            return request.redirect(f'/tech/order/{order_id}?error=no_signature')

        order.write(vals)
        
        # PROCESAR CHECKLIST (Líneas de la orden)
        for line in order.checklist_ids:
            line_val = post.get(f'checklist_{line.id}')
            line.write({'is_done': True if line_val == 'on' else False})

        # PROCESAR SUBIDA DE EVIDENCIAS (FOTOS)
        files = request.httprequest.files.getlist('evidence_files')
        for file in files:
            if file.filename:
                file_content = file.read()
                if file_content:
                    encoded_content = base64.b64encode(file_content)
                    request.env['sentinela.fsm.evidence'].create({
                        'order_id': order.id,
                        'name': file.filename,
                        'image': encoded_content,
                        'evidence_type': 'after'
                    })
                    request.env['ir.attachment'].create({
                        'name': file.filename,
                        'datas': encoded_content,
                        'res_model': 'sentinela.fsm.order',
                        'res_id': order.id,
                    })

        if post.get('action') == 'finish':
            order.action_finish()
            return request.redirect('/tech/dashboard?success=finished')
            
        return request.redirect(f'/tech/order/{order_id}?success=saved')

    @http.route(['/tech/order/<int:order_id>/pause'], type='http', auth="user", website=True, methods=['POST'])
    def technician_order_pause(self, order_id, **post):
        order = request.env['sentinela.fsm.order'].browse(order_id)
        if order.exists():
            reason_id = int(post.get('pause_reason_id')) if post.get('pause_reason_id') else False
            order.action_pause(reason_id=reason_id, notes=post.get('pause_notes'))
        return request.redirect('/tech/dashboard')

    @http.route(['/tech/order/<int:order_id>/quote'], type='http', auth="user", website=True, methods=['POST'])
    def technician_order_quote(self, order_id, **post):
        order = request.env['sentinela.fsm.order'].browse(order_id)
        if order.exists() and post.get('quote_notes'):
            order.action_request_quote(post.get('quote_notes'))
        return request.redirect(f'/tech/order/{order_id}?success=quote_sent')
