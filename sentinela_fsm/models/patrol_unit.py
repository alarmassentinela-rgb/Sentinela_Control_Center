from odoo import models, fields, api, _


class PatrolUnit(models.Model):
    """Catálogo de unidades rastreables para patrullaje/verificación.

    Una "unidad" es un dispositivo que reporta posición a SentiCar/Traccar:
    puede ser el CELULAR asignado a un patrullero o el GPS de un VEHÍCULO.
    Es independiente de la persona: al despachar se elige patrullero + unidad,
    así un mismo vehículo lo pueden usar distintos patrulleros en distintos turnos.
    """
    _name = 'sentinela.patrol.unit'
    _description = 'Unidad de Patrulla (dispositivo SentiCar)'
    _order = 'unit_kind, name'

    name = fields.Char(string='Nombre', required=True,
        help='Identificación legible, ej. "Camioneta March" o "Celular Patrullero 1".')
    unit_kind = fields.Selection([
        ('phone', 'Celular'),
        ('vehicle', 'Vehículo'),
    ], string='Tipo', required=True, default='vehicle')
    traccar_device_id = fields.Char(string='ID SentiCar (Traccar)', required=True,
        help='ID numérico del dispositivo en SentiCar/Traccar (el deviceId que usa la API de posiciones).')
    license_plate = fields.Char(string='Placa',
        help='Solo para vehículos.')
    available = fields.Boolean(string='Disponible', default=True,
        help='Desmárcala para sacar la unidad de circulación (taller, baja) sin borrar su historial.')
    is_default_dispatch = fields.Boolean(string='Unidad por defecto al despachar',
        help='Unidad que se autoselecciona al enviar un patrullero (normalmente el celular '
             'compartido del turno). Solo una unidad debe tenerlo activo.')
    notes = fields.Char(string='Notas')

    _sql_constraints = [
        ('traccar_device_id_uniq', 'unique(traccar_device_id)',
         'Ya existe una unidad con ese ID de SentiCar.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(v.get('is_default_dispatch') for v in vals_list):
            records.filtered('is_default_dispatch')._enforce_single_default()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_default_dispatch'):
            self._enforce_single_default()
        return res

    def _enforce_single_default(self):
        """Solo una unidad puede ser la de despacho por defecto: desmarca las demás."""
        self.ensure_one() if len(self) == 1 else None
        others = self.search([('is_default_dispatch', '=', True), ('id', 'not in', self.ids)])
        others.write({'is_default_dispatch': False})

    @api.model
    def _get_default_dispatch_unit(self):
        return self.search([('is_default_dispatch', '=', True), ('available', '=', True)], limit=1)

    def name_get(self):
        res = []
        icons = {'phone': '📱', 'vehicle': '🚓'}
        for u in self:
            res.append((u.id, f"{icons.get(u.unit_kind, '')} {u.name}".strip()))
        return res
