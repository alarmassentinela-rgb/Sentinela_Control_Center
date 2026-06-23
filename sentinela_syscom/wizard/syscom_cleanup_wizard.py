from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SyscomCleanupWizard(models.TransientModel):
    _name = 'syscom.cleanup.wizard'
    _description = 'Limpieza de Productos Syscom Descontinuados'

    total_discontinued = fields.Integer(string='Productos Descontinuados', readonly=True)
    to_delete_count = fields.Integer(string='A Eliminar (sin movimiento)', readonly=True)
    to_archive_count = fields.Integer(string='A Archivar (con movimiento)', readonly=True)
    preview_text = fields.Text(string='Preview', readonly=True)
    confirmed = fields.Boolean(string='Ejecutar limpieza definitiva')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        results = self._classify_discontinued()
        vals['total_discontinued'] = results['total']
        vals['to_delete_count'] = len(results['to_delete'])
        vals['to_archive_count'] = len(results['to_archive'])
        sample_delete = ', '.join(p.default_code or p.name[:30] for p in results['to_delete'][:5])
        sample_archive = ', '.join(p.default_code or p.name[:30] for p in results['to_archive'][:5])
        vals['preview_text'] = (
            f"Total descontinuados: {results['total']}\n\n"
            f"📦 A ELIMINAR (sin movimiento): {len(results['to_delete'])}\n"
            f"   Ejemplos: {sample_delete}{'...' if len(results['to_delete']) > 5 else ''}\n\n"
            f"📁 A ARCHIVAR (con movimiento, se ocultan pero se preserva historia): {len(results['to_archive'])}\n"
            f"   Ejemplos: {sample_archive}{'...' if len(results['to_archive']) > 5 else ''}"
        )
        return vals

    def _classify_discontinued(self):
        """Clasifica productos descontinuados en: eliminables vs archivables."""
        Product = self.env['product.template']
        discontinued = Product.search([
            ('syscom_discontinued', '=', True),
            ('active', '=', True),
        ])

        to_delete = self.env['product.template']
        to_archive = self.env['product.template']
        for p in discontinued:
            if self._has_movement(p):
                to_archive |= p
            else:
                to_delete |= p

        return {
            'total': len(discontinued),
            'to_delete': to_delete,
            'to_archive': to_archive,
        }

    def _has_movement(self, product):
        """Determina si un producto tiene movimiento contable/logístico.
        Delega en product.template._syscom_has_movement (lógica compartida con el cron)."""
        return product._syscom_has_movement()

    def action_execute(self):
        """Ejecuta la limpieza: elimina sin movimiento, archiva con movimiento."""
        self.ensure_one()
        if not self.confirmed:
            raise UserError(_("Debes marcar 'Ejecutar limpieza definitiva' para confirmar la operación."))
        results = self._classify_discontinued()
        deleted = len(results['to_delete'])
        archived = len(results['to_archive'])
        # Archivar primero (no rompe nada)
        if results['to_archive']:
            results['to_archive'].write({'active': False})
            _logger.info(f"SYSCOM CLEANUP: archived {archived} discontinued products with movement")
        # Eliminar después (puede fallar si hay alguna referencia que olvidamos)
        if results['to_delete']:
            try:
                results['to_delete'].unlink()
                _logger.info(f"SYSCOM CLEANUP: deleted {deleted} discontinued products without movement")
            except Exception as e:
                _logger.error(f"SYSCOM CLEANUP: delete failed, falling back to archive: {e}")
                results['to_delete'].write({'active': False})
                archived += deleted
                deleted = 0

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Limpieza Syscom Completada',
                'message': f'Eliminados: {deleted}. Archivados: {archived}.',
                'type': 'success',
                'sticky': True,
            },
        }
