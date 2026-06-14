"""F2.7.1 — Controller HTTP público para que el cliente autorice servicios
no incluidos en su plan vía magic link recibido por Telegram.

Diseño:
- Ruta pública (auth='public') — el token mismo es la autenticación.
- GET muestra la página con detalles del evento + monto + 2 botones.
- POST procesa la decisión, registrando IP + User-Agent para evidencia legal.
- Tokens ya usados muestran su estado final sin permitir cambiarlo.
"""
import logging

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class ServiceAuthorizationController(http.Controller):

    @http.route('/sentinela/autorizar/<string:token>', type='http',
                auth='public', csrf=False, methods=['GET', 'POST'])
    def authorize(self, token, **kwargs):
        # Buscar el token con sudo (cliente público no tiene acceso al modelo)
        tk = request.env['sentinela.service.authorization.token'].sudo().search(
            [('token', '=', token)], limit=1)
        if not tk:
            return request.render('sentinela_monitoring.authorization_invalid', {})

        # Magic link vencido (y aún sin responder) → tratarlo como inválido.
        if tk.state == 'pending' and tk.is_expired():
            return request.render('sentinela_monitoring.authorization_invalid', {})

        ip = request.httprequest.headers.get('X-Forwarded-For',
                                              request.httprequest.remote_addr or '')
        ua = request.httprequest.headers.get('User-Agent', '')

        if request.httprequest.method == 'POST':
            decision = kwargs.get('decision')
            if tk.state != 'pending':
                # Ya fue respondido — redirigir a la página de estado
                return request.render('sentinela_monitoring.authorization_already', {'tk': tk})
            try:
                if decision == 'authorize':
                    tk.authorize(ip=ip, user_agent=ua)
                elif decision == 'reject':
                    tk.reject(ip=ip, user_agent=ua)
                else:
                    return request.render('sentinela_monitoring.authorization_form',
                                           {'tk': tk, 'error': 'Decisión inválida.'})
            except Exception as e:
                _logger.exception("Authorization error for token %s", token[:8])
                return request.render('sentinela_monitoring.authorization_form',
                                       {'tk': tk, 'error': str(e)})
            return request.render('sentinela_monitoring.authorization_done', {'tk': tk})

        # GET
        if tk.state != 'pending':
            return request.render('sentinela_monitoring.authorization_already', {'tk': tk})
        return request.render('sentinela_monitoring.authorization_form', {'tk': tk})
