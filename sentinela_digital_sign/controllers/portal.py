from odoo import http, _
from odoo.http import request, content_disposition
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
import base64

class SignPortal(CustomerPortal):

    @http.route(['/my/document/<int:doc_id>/download'], type='http', auth="public", website=True)
    def portal_download_document(self, doc_id, access_token=None, **kw):
        try:
            doc_sudo = self._document_check_access('sentinela.sign.document', doc_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if doc_sudo.file_signed:
            content = base64.b64decode(doc_sudo.file_signed)
            filename = doc_sudo.filename_signed or f"{doc_sudo.name}_firmado.pdf"
            return request.make_response(
                content,
                [
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', content_disposition(filename))
                ]
            )
        return request.not_found()

    @http.route(['/my/document/<int:doc_id>'], type='http', auth="public", website=True)
    def portal_my_document(self, doc_id, access_token=None, **kw):
        try:
            doc_sudo = self._document_check_access('sentinela.sign.document', doc_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'doc': doc_sudo,
            'token': access_token,
            'partner_id': doc_sudo.partner_id.id,
            'report_type': 'html', # No es un reporte qweb, es visualización directa
        }
        return request.render("sentinela_digital_sign.portal_my_document_view", values)

    @http.route(['/my/document/<int:doc_id>/sign'], type='json', auth="public", website=True)
    def portal_sign_document(self, doc_id, access_token=None, name=None, signature=None):
        # Verificar acceso
        try:
            doc_sudo = self._document_check_access('sentinela.sign.document', doc_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid document access.')}

        if doc_sudo.state != 'sent':
             return {'error': _('El documento no está disponible para firmar.')}

        # Procesar firma
        doc_sudo.action_sign({
            'name': name,
            'signature': signature,
        })
        
        return {
            'force_refresh': True,
            'redirect_url': doc_sudo.get_portal_url(),
        }
