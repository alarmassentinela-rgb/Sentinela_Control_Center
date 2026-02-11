from odoo import models, fields, api
from datetime import datetime, timedelta

class FSMDashboard(models.Model):
    _name = 'sentinela.fsm.dashboard'
    _description = 'Dashboard de Desempeño FSM'
    
    name = fields.Char(string='Nombre del Dashboard', required=True)
    technician_id = fields.Many2one('res.users', string='Técnico')
    period_start = fields.Date(string='Periodo Desde', required=True, default=fields.Date.today)
    period_end = fields.Date(string='Periodo Hasta', required=True, default=lambda self: fields.Date.today() + timedelta(days=30))
    
    # Métricas principales
    total_orders = fields.Integer(string='Total de Órdenes', compute='_compute_metrics')
    completed_orders = fields.Integer(string='Órdenes Completadas', compute='_compute_metrics')
    completion_rate = fields.Float(string='Tasa de Completación (%)', compute='_compute_metrics')
    avg_resolution_time = fields.Float(string='Tiempo Promedio de Resolución (horas)', compute='_compute_metrics')
    avg_customer_rating = fields.Float(string='Calificación Promedio del Cliente', compute='_compute_metrics')
    
    # Métricas de eficiencia
    on_time_completion_rate = fields.Float(string='Tasa de Cumplimiento a Tiempo (%)', compute='_compute_metrics')
    avg_travel_time = fields.Float(string='Tiempo Promedio de Viaje (horas)', compute='_compute_metrics')
    avg_work_time = fields.Float(string='Tiempo Promedio de Trabajo (horas)', compute='_compute_metrics')
    
    @api.depends('technician_id', 'period_start', 'period_end')
    def _compute_metrics(self):
        for record in self:
            domain = [
                ('create_date', '>=', record.period_start),
                ('create_date', '<=', record.period_end),
            ]
            
            if record.technician_id:
                domain.append(('technician_id', '=', record.technician_id.id))
            
            orders = self.env['sentinela.fsm.order'].search(domain)
            record.total_orders = len(orders)
            
            completed_orders = orders.filtered(lambda o: o.stage == 'done')
            record.completed_orders = len(completed_orders)
            
            if record.total_orders > 0:
                record.completion_rate = (record.completed_orders / record.total_orders) * 100
            else:
                record.completion_rate = 0.0
            
            # Calcular tiempo promedio de resolución
            if completed_orders:
                total_resolution_time = sum(order.actual_duration for order in completed_orders if order.actual_duration)
                record.avg_resolution_time = total_resolution_time / len(completed_orders)
                
                # Calcular calificación promedio
                ratings = [order.customer_rating for order in completed_orders if order.customer_rating > 0]
                if ratings:
                    record.avg_customer_rating = sum(ratings) / len(ratings)
                else:
                    record.avg_customer_rating = 0.0
                    
                # Calcular tiempo promedio de viaje
                total_travel_time = sum(order.travel_time for order in completed_orders if order.travel_time)
                record.avg_travel_time = total_travel_time / len(completed_orders)
                
                # Calcular tiempo promedio de trabajo
                total_work_time = sum(order.work_time for order in completed_orders if order.work_time)
                record.avg_work_time = total_work_time / len(completed_orders)
                
                # Calcular tasa de cumplimiento a tiempo
                on_time_orders = completed_orders.filtered(
                    lambda o: o.scheduled_date and o.check_out_date and 
                    o.check_out_date <= o.scheduled_date + timedelta(hours=o.planned_duration or 1)
                )
                record.on_time_completion_rate = (len(on_time_orders) / len(completed_orders)) * 100
            else:
                record.avg_resolution_time = 0.0
                record.avg_customer_rating = 0.0
                record.avg_travel_time = 0.0
                record.avg_work_time = 0.0
                record.on_time_completion_rate = 0.0

    def action_refresh(self):
        """Método para actualizar manualmente las métricas"""
        self._compute_metrics()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Métricas Actualizadas',
                'message': 'Las métricas han sido recalculadas exitosamente.',
                'type': 'success',
                'sticky': False,
            }
        }