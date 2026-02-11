# -*- coding: utf-8 -*-
from odoo import models, fields

class FsmPauseReason(models.Model):
    _name = 'sentinela.fsm.pause.reason'
    _description = 'FSM Order Pause Reason'
    _order = 'sequence, name'

    name = fields.Char(string='Reason', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    is_quote_reason = fields.Boolean(
        string='Is Quote Reason',
        help="Check this if selecting this reason should trigger the 'quote needed' workflow for the sales team."
    )
    sequence = fields.Integer(string='Sequence', default=10)
