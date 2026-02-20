from odoo import models, fields, api
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    syscom_id = fields.Char(string='ID de Producto Syscom')
    syscom_model = fields.Char(string='Modelo Syscom')
    syscom_brand = fields.Char(string='Marca Syscom')
    syscom_stock = fields.Float(string='Existencia Syscom')
    syscom_last_update = fields.Datetime(string='Última Sincronización')
    syscom_link = fields.Char(string='Link Syscom')
    syscom_weight = fields.Float(string='Peso (kg)')
    syscom_list_price_usd = fields.Float(string='Precio de Lista USD')
    syscom_suggested_price_usd = fields.Float(string='Precio Especial USD')
    syscom_price_usd = fields.Float(string='Precio Distribuidor 1 USD')
    syscom_description = fields.Html(string='Descripción Técnica Syscom')

    @api.model
    def _cron_update_syscom_products(self):
        """Robot Nocturno con Reporte a Telegram"""
        start_time = datetime.now()
        params = self.env['ir.config_parameter'].sudo()
        client_id = params.get_param('sentinela_syscom.client_id')
        client_secret = params.get_param('sentinela_syscom.client_secret')
        telegram_token = "8373567654:AAGyLpZttCUaHh-LymQwEHRBOqwtVNXYN10" # Nuevo Token del bot Sentinela 2026
        chat_id = "7965190381"

        stats = {'total': 0, 'success': 0, 'errors': 0}
        
        def send_telegram(msg):
            try:
                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                requests.post(url, data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
            except: pass

        try:
            res_token = requests.post('https://developers.syscom.mx/oauth/token', data={
                'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'client_credentials'
            }, timeout=15)
            token = res_token.json().get('access_token')
            if not token: return

            headers = {'Authorization': f'Bearer {token}'}
            products = self.search([('syscom_id', '!=', False), ('active', '=', True)])
            stats['total'] = len(products)
            tc = 17.26
            margin = 1.30
            
            for p in products:
                try:
                    url_prod = f'https://developers.syscom.mx/api/v1/productos/{p.syscom_id}'
                    res_prod = requests.get(url_prod, headers=headers, timeout=10).json()
                    costo_usd = float(res_prod.get('precio_lista', 0))
                    if costo_usd > 0:
                        p.write({
                            'standard_price': costo_usd * tc,
                            'list_price': costo_usd * tc * margin,
                            'syscom_stock': float(res_prod.get('existencia', {}).get('nuevo', 0)),
                            'syscom_last_update': fields.Datetime.now(),
                        })
                        stats['success'] += 1
                    else: stats['errors'] += 1
                except: stats['errors'] += 1
            
            msg = (f"🤖 *Reporte Robot Syscom*\n✅ *Estado:* Finalizado\n📦 *Procesados:* {stats['total']}\n💰 *Actualizados:* {stats['success']}")
            send_telegram(msg)
        except Exception as e: send_telegram(f"🚨 *ERROR ROBOT:* {str(e)}")

class AccountMove(models.Model):
    _inherit = 'account.move'

    syscom_folio = fields.Char(string='Folio Syscom', readonly=True, copy=False)

    def action_sync_syscom_invoices(self):
        """Sincronización manual de facturas desde Syscom"""
        params = self.env['ir.config_parameter'].sudo()
        client_id = params.get_param('sentinela_syscom.client_id')
        client_secret = params.get_param('sentinela_syscom.client_secret')
        
        res_token = requests.post('https://developers.syscom.mx/oauth/token', data={
            'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'client_credentials'
        }, timeout=15)
        token = res_token.json().get('access_token')
        if not token: return
        
        headers = {'Authorization': f'Bearer {token}'}
        res_f = requests.get('https://developers.syscom.mx/api/v1/facturas', headers=headers, timeout=15).json()
        facturas = res_f.get('facturas', [])
        
        syscom_partner = self.env['res.partner'].search([('ref', '=', 'PROV-SYSCOM')], limit=1)
        if not syscom_partner: return

        count = 0
        for f in facturas:
            folio = f.get('folio_factura')
            if self.search_count([('syscom_folio', '=', folio)]): continue
            
            res_d = requests.get(f'https://developers.syscom.mx/api/v1/facturas/{folio}', headers=headers, timeout=15).json()
            
            invoice_vals = {
                'move_type': 'in_invoice',
                'partner_id': syscom_partner.id,
                'ref': folio,
                'syscom_folio': folio,
                'invoice_date': f.get('fecha'),
                'invoice_line_ids': [],
            }
            
            for item in res_d.get('productos', []):
                product = self.env['product.product'].search([('default_code', '=', item.get('cod_art'))], limit=1)
                line_vals = {
                    'name': item.get('titulo'),
                    'quantity': float(item.get('cantidad', 1)),
                    'price_unit': float(item.get('precio_unitario', 0)),
                    'product_id': product.id if product else False,
                }
                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
            
            self.create(invoice_vals)
            count += 1
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Syscom', 'message': f'Importadas {count} facturas.', 'sticky': False}
        }
