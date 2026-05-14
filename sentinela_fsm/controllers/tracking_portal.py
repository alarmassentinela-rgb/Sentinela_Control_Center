from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class CustomerTracking(http.Controller):

    @http.route(['/SentiCar/rastreo/<string:token>'], type='http', auth="public", website=True)
    def customer_tracking_view(self, token, **kw):
        """ Vista pública de rastreo para el cliente """
        # Usamos sudo() porque es acceso público sin login
        order = request.env['sentinela.fsm.order'].sudo().search([('tracking_token', '=', token)], limit=1)
        if not order or order.stage not in ['assigned', 'in_progress']:
            return request.render("sentinela_fsm.tracking_expired")

        return request.render("sentinela_fsm.customer_tracking_map", {
            'order': order,
        })

    @http.route(['/SentiCar/rastreo/<string:token>/data'], type='json', auth="public")
    def customer_tracking_data(self, token, **kw):
        """ API interna para que el mapa se actualice solo cada 5 segundos """
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
