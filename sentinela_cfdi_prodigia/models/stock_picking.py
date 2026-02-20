from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    credit_note_id = fields.Many2one('account.move', string='Nota de Crédito Generada', readonly=True, copy=False)

    def action_generate_credit_note_from_return(self):
        self.ensure_one()
        if self.credit_note_id:
            raise UserError(_("Ya existe una nota de crédito vinculada a esta devolución: %s") % self.credit_note_id.name)
        
        # 1. Buscar la Orden de Venta de origen
        sale_order = self.sale_id
        if not sale_order:
            # Si no hay orden directa, intentar buscar por el documento de origen (ej. S00022)
            if self.origin:
                sale_order = self.env['sale.order'].search([('name', '=', self.origin)], limit=1)
        
        if not sale_order:
            raise UserError(_("No se pudo localizar la Orden de Venta original para esta devolución."))

        # 2. Buscar la factura publicada de esa orden
        invoice = sale_order.invoice_ids.filtered(lambda i: i.state == 'posted' and i.move_type == 'out_invoice')[:1]
        if not invoice:
            raise UserError(_("No se encontró una factura publicada para la orden %s.") % sale_order.name)

        # 3. Crear el reverso (Nota de Crédito) usando el wizard estándar
        reversal_wizard = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'reason': f'Devolución automatizada desde {self.name}',
            'journal_id': invoice.journal_id.id,
        })
        
        action = reversal_wizard.reverse_moves()
        nc = self.env['account.move'].browse(action['res_id'])

        # 4. Ajustar líneas: Solo dejar lo que realmente entró en este picking (WH/IN/...)
        returned_products = {line.product_id.id: line.quantity for line in self.move_ids if line.state == 'done'}
        
        for line in nc.invoice_line_ids:
            if line.product_id.id not in returned_products:
                line.unlink()
            else:
                line.quantity = returned_products[line.product_id.id]

        # 5. Vincular y notificar
        self.credit_note_id = nc.id
        nc.message_post(body=f"Nota de crédito generada automáticamente desde la devolución {self.name}")
        
        return {
            'name': _('Nota de Crédito Generada'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': nc.id,
            'type': 'ir.actions.act_window',
        }
