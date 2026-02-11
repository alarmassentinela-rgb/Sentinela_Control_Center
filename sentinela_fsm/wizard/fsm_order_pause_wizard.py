# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class FsmOrderPauseWizard(models.TransientModel):
    _name = 'sentinela.fsm.order.pause.wizard'
    _description = 'FSM Order Pause Wizard'

    reason_id = fields.Many2one(
        'sentinela.fsm.pause.reason',
        string='Pause Reason',
        required=True
    )
    notes = fields.Text(string='Additional Notes')

    def action_pause(self):
        """Pauses the FSM Order and logs the reason."""
        self.ensure_one()
        order = self.env['sentinela.fsm.order'].browse(self.env.context.get('active_ids'))

        order.write({
            'stage': 'paused',
            'pause_reason_id': self.reason_id.id,
            'pause_notes': self.notes,
        })

        body = _("Order paused by %(user)s") % {'user': self.env.user.name}
        body += "<ul>"
        body += "<li><strong>" + _("Reason:") + "</strong> " + self.reason_id.name + "</li>"
        if self.notes:
            body += "<li><strong>" + _("Notes:") + "</strong> " + self.notes + "</li>"
        body += "</ul>"
        
        order.message_post(body=body)

        return {'type': 'ir.actions.act_window_close'}
