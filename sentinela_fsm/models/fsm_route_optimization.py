from odoo import models, fields, api
from geopy.distance import geodesic

class FSMRouteOptimization(models.Model):
    _name = 'sentinela.fsm.route.optimization'
    _description = 'Optimización de Rutas FSM'
    
    name = fields.Char(string='Nombre de la Ruta', required=True)
    technician_id = fields.Many2one('res.users', string='Técnico', required=True)
    date = fields.Date(string='Fecha', required=True, default=fields.Date.today)
    total_distance = fields.Float(string='Distancia Total (km)', compute='_compute_total_distance', store=True)
    total_duration = fields.Float(string='Duración Total (horas)', compute='_compute_total_duration', store=True)
    status = fields.Selection([
        ('draft', 'Borrador'),
        ('optimized', 'Optimizada'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada')
    ], string='Estado', default='draft')
    
    route_line_ids = fields.One2many('sentinela.fsm.route.line', 'route_id', string='Líneas de Ruta')
    order_ids = fields.Many2many('sentinela.fsm.order', string='Órdenes de Servicio')

    @api.model
    def create_route_for_technician(self, technician_id, date, order_ids):
        """Crear una ruta para un técnico con las órdenes especificadas"""
        route = self.create({
            'name': f'Ruta {technician_id.name} - {date}',
            'technician_id': technician_id.id,
            'date': date,
            'order_ids': [(6, 0, order_ids)]
        })
        
        # Crear líneas de ruta basadas en las órdenes
        route_lines = []
        orders = self.env['sentinela.fsm.order'].browse(order_ids)
        
        # Ordenar por proximidad geográfica
        sorted_orders = self._sort_orders_by_proximity(orders)
        
        for idx, order in enumerate(sorted_orders):
            route_lines.append((0, 0, {
                'sequence': idx + 1,
                'order_id': order.id,
                'estimated_duration': order.planned_duration or 1.0,
                'distance_from_previous': self._calculate_distance(idx, sorted_orders)
            }))
        
        route.route_line_ids = route_lines
        route.status = 'optimized'
        
        return route

    def _sort_orders_by_proximity(self, orders):
        """Ordenar órdenes por proximidad geográfica"""
        if not orders:
            return orders
            
        # Tomar la primera orden como punto de partida
        sorted_orders = [orders[0]]
        remaining_orders = orders[1:].sorted(key=lambda o: o.id)  # Orden temporal
        
        while remaining_orders:
            last_order = sorted_orders[-1]
            closest_order = min(
                remaining_orders,
                key=lambda o: self._get_distance_between_orders(last_order, o) if last_order.service_address_id and o.service_address_id else float('inf')
            )
            sorted_orders.append(closest_order)
            remaining_orders -= closest_order
        
        return sorted_orders

    def _get_distance_between_orders(self, order1, order2):
        """Calcular distancia entre dos órdenes"""
        if not order1.service_address_id or not order2.service_address_id:
            return float('inf')
            
        if not order1.service_address_id.partner_latitude or not order1.service_address_id.partner_longitude or \
           not order2.service_address_id.partner_latitude or not order2.service_address_id.partner_longitude:
            return float('inf')
        
        coord1 = (order1.service_address_id.partner_latitude, order1.service_address_id.partner_longitude)
        coord2 = (order2.service_address_id.partner_latitude, order2.service_address_id.partner_longitude)
        
        return geodesic(coord1, coord2).kilometers

    def _calculate_distance(self, index, orders):
        """Calcular distancia desde la orden anterior"""
        if index == 0:
            return 0.0  # Distancia desde origen
        
        if index > 0 and index < len(orders):
            return self._get_distance_between_orders(orders[index-1], orders[index])
        
        return 0.0

    @api.depends('route_line_ids.distance_from_previous')
    def _compute_total_distance(self):
        for route in self:
            route.total_distance = sum(line.distance_from_previous for line in route.route_line_ids)

    @api.depends('route_line_ids.estimated_duration')
    def _compute_total_duration(self):
        for route in self:
            route.total_duration = sum(line.estimated_duration for line in route.route_line_ids)

    def action_start_route(self):
        """Iniciar la ruta"""
        self.write({'status': 'in_progress'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ruta Iniciada',
                'message': f'La ruta {self.name} ha sido iniciada.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_complete_route(self):
        """Completar la ruta"""
        self.write({'status': 'completed'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ruta Completada',
                'message': f'La ruta {self.name} ha sido completada.',
                'type': 'success',
                'sticky': False,
            }
        }


class FSMRouteLine(models.Model):
    _name = 'sentinela.fsm.route.line'
    _description = 'Línea de Ruta FSM'
    _order = 'sequence'

    route_id = fields.Many2one('sentinela.fsm.route.optimization', string='Ruta', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Secuencia', required=True)
    order_id = fields.Many2one('sentinela.fsm.order', string='Orden de Servicio', required=True)
    estimated_duration = fields.Float(string='Duración Estimada (horas)', required=True)
    distance_from_previous = fields.Float(string='Distancia desde Anterior (km)')
    actual_start_time = fields.Datetime(string='Inicio Real')
    actual_end_time = fields.Datetime(string='Fin Real')
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada')
    ], string='Estado', default='pending')
    
    # Campos relacionados para mostrar información de la orden
    partner_id = fields.Many2one(related='order_id.partner_id', string='Cliente', store=True)
    service_address_id = fields.Many2one(related='order_id.service_address_id', string='Dirección de Servicio', store=True)
    scheduled_date = fields.Datetime(related='order_id.scheduled_date', string='Fecha Programada', store=True)