from odoo import http
from odoo.http import request


class SenticarTransportistaPortal(http.Controller):
    """Mini-portal para el transportista (cliente GPS): entra con su link personal (token),
    ve SUS unidades y genera links de rastreo temporales para compartir con sus clientes
    (dueños de la carga). Sin necesidad de cuenta Odoo ni de SentiCar."""

    def _partner_by_token(self, token):
        if not token:
            return None
        return request.env['res.partner'].sudo().search(
            [('senticar_portal_token', '=', token)], limit=1)

    def _devices(self, partner):
        """Equipos GPS del transportista (de sus suscripciones GPS activas/suspendidas)."""
        subs = request.env['sentinela.subscription'].sudo().search([
            ('partner_id', '=', partner.id),
            ('service_type', '=', 'gps'),
            ('state', 'in', ('active', 'suspension')),
        ])
        return subs.mapped('gps_device_ids')

    @http.route('/senticar/t/<token>', type='http', auth='public', website=False, csrf=False)
    def portal(self, token, **kw):
        partner = self._partner_by_token(token)
        if not partner:
            return request.render('sentinela_subscriptions.senticar_transportista_invalid')
        devices = self._devices(partner)
        generated = {}
        if request.httprequest.method == 'POST':
            dev_id = kw.get('device_id')
            hours = kw.get('hours') or 24
            dev = devices.filtered(lambda d: str(d.id) == str(dev_id))
            if dev and dev.senticar_device_id:
                res = request.env['sentinela.senticar.service'].sudo().create_share_link(
                    dev.senticar_device_id, hours=hours, label=dev.name or 'Rastreo')
                if res.get('ok'):
                    generated[dev.id] = res['link']
                else:
                    generated[dev.id] = 'ERROR: ' + (res.get('detail') or '')
        return request.render('sentinela_subscriptions.senticar_transportista_portal', {
            'partner': partner,
            'devices': devices,
            'generated': generated,
            'token': token,
        })
