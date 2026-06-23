# -*- coding: utf-8 -*-
"""Wizard de programación rápida desde el tablero de despacho.

Permite al operador fijar fecha (y técnico) de una orden "Sin programar" sin abrir
el formulario completo. Reusa `action_assign` de la orden para mover la etapa a
'Asignado' y notificar al técnico cuando hay técnico + fecha.
"""

from odoo import fields, models, _


class FsmScheduleWizard(models.TransientModel):
    _name = 'sentinela.fsm.schedule.wizard'
    _description = 'Programar orden de servicio (rápido)'

    order_id = fields.Many2one('sentinela.fsm.order', string='Orden',
                               required=True, ondelete='cascade')
    scheduled_date = fields.Datetime(string='Fecha Programada', required=True)
    technician_id = fields.Many2one('res.users', string='Técnico')

    def action_schedule(self):
        self.ensure_one()
        order = self.order_id
        vals = {'scheduled_date': self.scheduled_date}
        if self.technician_id:
            vals['technician_id'] = self.technician_id.id
        order.write(vals)
        # Con técnico + fecha y aún en 'Nuevo', programa de verdad (mueve a 'Asignado'
        # y dispara la notificación al técnico). action_assign valida ambos campos.
        if order.technician_id and order.scheduled_date and order.stage == 'new':
            order.action_assign()
        return {'type': 'ir.actions.act_window_close'}
