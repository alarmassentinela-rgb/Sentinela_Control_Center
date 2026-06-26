from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CfdiCancelWizard(models.TransientModel):
    _name = 'sentinela.cfdi.cancel.wizard'
    _description = 'Asistente de Cancelación de CFDI ante el SAT'

    move_id = fields.Many2one('account.move', string='Factura', required=True, readonly=True)
    cfdi_uuid = fields.Char(related='move_id.cfdi_uuid', string='Folio Fiscal a cancelar', readonly=True)
    motivo = fields.Selection([
        ('01', '01 - Comprobante emitido con errores con relación (requiere folio sustituto)'),
        ('02', '02 - Comprobante emitido con errores sin relación'),
        ('03', '03 - No se llevó a cabo la operación'),
        ('04', '04 - Operación nominativa relacionada en factura global'),
    ], string='Motivo de Cancelación (SAT)', required=True, default='02')
    folio_sustitucion = fields.Char(
        string='Folio Fiscal que lo sustituye (UUID)',
        help='Obligatorio solo si el motivo es 01: UUID de la factura nueva que reemplaza a la cancelada.')

    @api.onchange('motivo')
    def _onchange_motivo(self):
        if self.motivo != '01':
            self.folio_sustitucion = False

    def action_confirm_cancel(self):
        self.ensure_one()
        if self.motivo == '01' and not self.folio_sustitucion:
            raise UserError(_('El motivo 01 requiere el Folio Fiscal (UUID) que sustituye al cancelado.'))
        self.move_id.action_cfdi_cancel_prodigia(
            motivo=self.motivo,
            folio_sustitucion=self.folio_sustitucion or None,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('CFDI cancelado'),
                'message': _('Se solicitó la cancelación del folio %s ante el SAT. Revisa el acuse en la factura.') % (self.cfdi_uuid or ''),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
