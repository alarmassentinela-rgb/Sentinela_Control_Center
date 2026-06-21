from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class CustomerSurvey(http.Controller):
    """Encuesta pública de satisfacción del cliente (califica al técnico) + boleto de rifa."""

    def _get_order(self, token):
        if not token:
            return False
        return request.env['sentinela.fsm.order'].sudo().search(
            [('survey_token', '=', token)], limit=1)

    @http.route(['/encuesta/<string:token>'], type='http', auth="public", website=True, sitemap=False)
    def survey_form(self, token, **kw):
        order = self._get_order(token)
        if not order:
            return request.render("sentinela_fsm.survey_invalid")
        if order.survey_submitted_date:
            # Ya respondió: mostramos su boleto, no dejamos volver a votar.
            return request.render("sentinela_fsm.survey_thanks", {'order': order})
        return request.render("sentinela_fsm.survey_form", {'order': order})

    @http.route(['/encuesta/<string:token>/submit'], type='http', auth="public",
                website=True, methods=['POST'], csrf=False)
    def survey_submit(self, token, **post):
        order = self._get_order(token)
        if not order:
            return request.render("sentinela_fsm.survey_invalid")
        if not order.survey_submitted_date:
            order.register_survey_response(post.get('rating'), post.get('feedback'))
        return request.render("sentinela_fsm.survey_thanks", {'order': order})
