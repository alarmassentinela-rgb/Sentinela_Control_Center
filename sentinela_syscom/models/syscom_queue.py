from odoo import models, fields, api
import logging

class SyscomImportQueue(models.Model):
    _name = 'syscom.import.queue'
    _description = 'Cola de Importación Syscom'

    category_ids = fields.Char(string='Categorías', required=True)
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('done', 'Completado'),
        ('error', 'Error')
    ], default='pending')
    message = fields.Text(string='Resultado')

    @api.model
    def process_queue(self):
        """Método llamado por el Cron para procesar la cola"""
        jobs = self.search([('status', '=', 'pending')], limit=1)
        for job in jobs:
            job.write({'status': 'processing'})
            self.env.cr.commit() # Bloquear para que otros crons no lo tomen
            
            try:
                cat_list = [c.strip() for c in job.category_ids.split(',')]
                count = self.env['product.template'].import_from_syscom_categories(cat_list)
                job.write({
                    'status': 'done',
                    'message': f'Exitoso: {count} productos creados.'
                })
            except Exception as e:
                job.write({
                    'status': 'error',
                    'message': str(e)
                })
            self.env.cr.commit()
