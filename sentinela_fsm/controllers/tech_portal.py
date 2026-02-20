from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class TechnicianPortal(http.Controller):

    @http.route(['/tech/dashboard'], type='http', auth="user", website=True)
    def technician_dashboard(self, **kw):
        """ Dashboard principal para el técnico """
        user = request.env.user
        # Verificación de seguridad simplificada para evitar errores de carga
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

    @http.route(['/tech/order/<int:order_id>/save'], type='http', auth="user", website=True, methods=['POST'])
    def technician_order_save(self, order_id, **post):
        """ Guardar datos técnicos capturados en campo """
        order = request.env['sentinela.fsm.order'].browse(order_id)
        if not order.exists():
            return request.redirect('/tech/dashboard')

        vals = {
            'resolution_notes': post.get('resolution_notes'),
            'alarm_zones': post.get('alarm_zones'),
            'vehicle_plate': post.get('vehicle_plate'),
            'vehicle_brand': post.get('vehicle_brand'),
            'vehicle_model': post.get('vehicle_model'),
            'sim_iccid': post.get('sim_iccid'),
            'install_lat': float(post.get('lat')) if post.get('lat') else 0.0,
            'install_lon': float(post.get('lon')) if post.get('lon') else 0.0,
        }
        order.write(vals)
        
        if post.get('action') == 'finish':
            order.action_finish()
            return request.redirect('/tech/dashboard?success=finished')
            
        return request.redirect(f'/tech/order/{order_id}?success=saved')
