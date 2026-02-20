from odoo import models, fields, api, _

class FSMOrder(models.Model):
    _inherit = 'sentinela.fsm.order'

    alarm_event_id = fields.Many2one('sentinela.alarm.event', string='Evento de Alarma Origen')

    def action_start(self):
        """
        Al iniciar la orden, si es una instalación de alarma, 
        asignar automáticamente el siguiente número de cuenta disponible.
        """
        res = super(FSMOrder, self).action_start()
        
        for order in self:
            if order.service_type == 'install' and order.subscription_id and \
               order.subscription_id.service_type == 'alarm' and \
               not order.subscription_id.monitoring_account_number:
                
                # Obtener el siguiente número de la secuencia
                next_account = self.env['ir.sequence'].next_by_code('sentinela.monitoring.account')
                
                if next_account:
                    order.subscription_id.write({
                        'monitoring_account_number': next_account
                    })
                    # Sincronizar también al campo local de la orden para que el técnico lo vea fácil
                    order.monitoring_account_number = next_account
                    
                    # Notificar al técnico vía chatter y push
                    msg = _("🤖 Sistema: Se ha asignado automáticamente el número de cuenta de monitoreo: <b>%s</b>. Por favor, prográmalo en el panel.") % next_account
                    order.message_post(body=msg)
                    
                    if hasattr(order, 'send_push_notification'):
                        order.send_push_notification(
                            title="Cuenta Asignada",
                            message=f"Cuenta de Monitoreo: {next_account}",
                            recipient_user=order.technician_id,
                            notification_type='update'
                        )
        return res
