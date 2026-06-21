import random
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FsmRaffleDrawWizard(models.TransientModel):
    _name = 'sentinela.fsm.raffle.draw.wizard'
    _description = 'Sorteo de Rifa de Satisfacción'

    date_from = fields.Date(string='Desde', required=True,
        default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Hasta', required=True,
        default=lambda self: fields.Date.today())
    only_unwon = fields.Boolean(string='Excluir órdenes que ya ganaron', default=True)
    entry_count = fields.Integer(string='Participaciones en el rango', readonly=True)

    winner_order_id = fields.Many2one('sentinela.fsm.order', string='Orden Ganadora', readonly=True)
    winner_partner = fields.Char(string='Cliente Ganador', readonly=True)
    winner_ticket = fields.Char(string='Boleto Ganador', readonly=True)

    def _entry_domain(self):
        self.ensure_one()
        domain = [
            ('raffle_ticket', '!=', False),
            ('survey_submitted_date', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('survey_submitted_date', '<', fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)),
        ]
        if self.only_unwon:
            domain.append(('raffle_won', '=', False))
        return domain

    @api.onchange('date_from', 'date_to', 'only_unwon')
    def _onchange_count(self):
        for w in self:
            if w.date_from and w.date_to:
                w.entry_count = self.env['sentinela.fsm.order'].search_count(w._entry_domain())
            else:
                w.entry_count = 0

    def action_draw(self):
        self.ensure_one()
        entries = self.env['sentinela.fsm.order'].search(self._entry_domain())
        if not entries:
            raise UserError(_("No hay participaciones (encuestas respondidas con boleto) en ese rango."))
        winner = entries[random.randint(0, len(entries) - 1)]
        winner.write({'raffle_won': True, 'raffle_won_date': fields.Datetime.now()})
        winner.message_post(body=_(
            "🎉 <b>¡Ganador de la rifa!</b> Boleto <b>%s</b> (sorteo %s a %s).") % (
            winner.raffle_ticket, self.date_from, self.date_to))
        self.write({
            'entry_count': len(entries),
            'winner_order_id': winner.id,
            'winner_partner': winner.partner_id.name,
            'winner_ticket': winner.raffle_ticket,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Resultado del Sorteo'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_winner(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sentinela.fsm.order',
            'res_id': self.winner_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
