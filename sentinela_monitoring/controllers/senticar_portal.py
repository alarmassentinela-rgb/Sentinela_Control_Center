from odoo import http
from odoo.http import request

class SenticarPortal(http.Controller):

    @http.route('/web/senticar/test', type='http', auth="none")
    def senticar_test(self, **kw):
        return "¡SentiCar está vivo! Ruta de Sistema Activada."

    @http.route('/web/senticar/radar', type='http', auth="public")
    def senticar_radar(self, **kw):
        """ Dashboard de Monitoreo Nativo SentiCar """
        devices = request.env['sentinela.monitoring.device'].sudo().search([('status', '=', 'active')])
        return request.render("sentinela_monitoring.senticar_radar_view", {
            'devices': devices,
            'device_count': len(devices),
        })
