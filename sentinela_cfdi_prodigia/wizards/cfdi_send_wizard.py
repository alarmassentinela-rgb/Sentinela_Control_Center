import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CfdiSendWizard(models.TransientModel):
    _name = 'sentinela.cfdi.send.wizard'
    _description = 'Enviar Factura/Remisión al Cliente'

    move_id = fields.Many2one('account.move', string='Documento', required=True, readonly=True)
    partner_ids = fields.Many2many(
        'res.partner', string='Enviar a (contactos del cliente)',
        help='Contactos registrados del cliente con correo. Quita los que no quieras y/o agrega otros.')
    extra_emails = fields.Char(
        string='Otros correos (manual)',
        help='Correos que no están en la lista, separados por coma. Ej: juan@correo.com, otro@correo.com')

    def action_send(self):
        self.ensure_one()
        emails = [p.email.strip() for p in self.partner_ids if p.email and p.email.strip()]
        if self.extra_emails:
            emails += [e.strip() for e in re.split(r'[,;\s]+', self.extra_emails) if e.strip()]
        # dedup conservando orden
        emails = list(dict.fromkeys(emails))
        if not emails:
            raise UserError(_('Selecciona al menos un contacto o escribe un correo manualmente.'))
        self.move_id._cfdi_send_invoice_email(force_recipients=emails)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Correo enviado'),
                'message': _('Enviado a: %s') % ', '.join(emails),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
