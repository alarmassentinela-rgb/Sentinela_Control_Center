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
    # v18.0.1.4.0: enriquecimiento de ficha desde la API de Syscom
    syscom_sat_description = fields.Char(string='Descripción SAT')
    syscom_sat_unit_key = fields.Char(string='Clave Unidad SAT', help='Clave de unidad del SAT (ej. H87 = Pieza) según Syscom.')
    syscom_caracteristicas = fields.Html(string='Características Syscom')
    syscom_datasheet_url = fields.Char(string='Ficha Técnica (URL)')
    # v18.0.1.3.0: marcado de productos descontinuados
    syscom_discontinued = fields.Boolean(
        string='Descontinuado en Syscom',
        default=False,
        index=True,
        help='Se marca automáticamente cuando la API de Syscom devuelve 404 o el flag descontinuado en la sincronización nocturna. Productos descontinuados aún visibles aquí pueden depurarse desde el wizard "Limpiar Productos Descontinuados".',
    )
    syscom_discontinued_date = fields.Date(
        string='Detectado descontinuado',
        readonly=True,
    )

    @api.model
    @api.model
    def _syscom_extract_enrichment(self, payload):
        """Extrae datos de enriquecimiento de la ficha Syscom (/productos/{id}):
        descripción SAT, clave de unidad SAT, características (HTML) y ficha técnica."""
        import html as _html
        datasheet = False
        for r in (payload.get('recursos') or []):
            if isinstance(r, dict) and 'ficha' in (r.get('recurso') or '').lower():
                datasheet = r.get('path')
                break
        caracs = payload.get('caracteristicas') or []
        caracs_html = False
        if isinstance(caracs, list) and caracs:
            caracs_html = '<ul>' + ''.join('<li>%s</li>' % _html.escape(str(c)) for c in caracs) + '</ul>'
        um = payload.get('unidad_de_medida') or {}
        return {
            'syscom_sat_description': payload.get('sat_description'),
            'syscom_sat_unit_key': um.get('clave_unidad_sat') if isinstance(um, dict) else False,
            'syscom_caracteristicas': caracs_html,
            'syscom_datasheet_url': datasheet,
        }

    def _cron_update_syscom_products(self):
        """Robot Nocturno con Reporte a Telegram"""
        start_time = datetime.now()
        params = self.env['ir.config_parameter'].sudo()
        client_id = params.get_param('sentinela_syscom.client_id')
        client_secret = params.get_param('sentinela_syscom.client_secret')
        # v18.0.1.2.0: credenciales Telegram leídas desde ir.config_parameter
        telegram_token = params.get_param('sentinela_syscom.telegram_token')
        chat_id = params.get_param('sentinela_syscom.telegram_chat_id')

        stats = {'total': 0, 'success': 0, 'errors': 0}

        def send_telegram(msg):
            if not telegram_token or not chat_id:
                return  # Telegram opcional: si no hay config, no envía
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
            # Search for linked products OR products with price <= 1.0 to rescue them
            products = self.search([
                '|', ('syscom_id', '!=', False), ('list_price', '<=', 1.0),
                ('active', '=', True),
                ('default_code', '!=', False)
            ])
            stats['total'] = len(products)
            tc = 17.26
            
            # Fetch actual TC if possible
            try:
                res_tc = requests.get('https://developers.syscom.mx/api/v1/tipocambio', headers=headers, timeout=10)
                tc_val = res_tc.json().get('normal')
                if tc_val: tc = float(tc_val)
            except: pass

            for p in products:
                try:
                    sys_id = p.syscom_id
                    if not sys_id:
                        search_url = f'https://developers.syscom.mx/api/v1/productos?busqueda={p.default_code}'
                        res_search = requests.get(search_url, headers=headers, timeout=10).json()
                        prods = res_search.get('productos', [])
                        if prods:
                            sys_id = str(prods[0].get('producto_id'))
                        else:
                            continue

                    url_prod = f'https://developers.syscom.mx/api/v1/productos/{sys_id}'
                    res_raw = requests.get(url_prod, headers=headers, timeout=10)
                    # v18.0.1.3.0: detección automática de descontinuados
                    if res_raw.status_code == 404:
                        if not p.syscom_discontinued:
                            p.write({
                                'syscom_discontinued': True,
                                'syscom_discontinued_date': fields.Date.today(),
                            })
                        stats['errors'] += 1
                        continue
                    res_prod = res_raw.json()
                    # Si Syscom marca explícitamente como descontinuado en el payload
                    if res_prod.get('descontinuado') is True:
                        if not p.syscom_discontinued:
                            p.write({
                                'syscom_discontinued': True,
                                'syscom_discontinued_date': fields.Date.today(),
                            })

                    precios = res_prod.get('precios', {})
                    # MSRP / Precio al Público
                    msrp_usd = float(precios.get('precio_lista') or res_prod.get('precio_lista', 0))
                    # Tu Costo / Precio Distribuidor
                    costo_usd = float(precios.get('precio_descuento') or res_prod.get('precio_descuento', 0))
                    
                    if costo_usd > 0:
                        vals = {
                            'syscom_id': sys_id,
                            'syscom_price_usd': costo_usd,
                            'syscom_list_price_usd': msrp_usd,
                            'standard_price': costo_usd * tc,
                            'syscom_stock': float(res_prod.get('existencia', {}).get('nuevo', 0)),
                            'syscom_last_update': fields.Datetime.now(),
                        }
                        # v18.0.1.4.0: enriquecimiento (SAT, características, ficha técnica)
                        vals.update(self._syscom_extract_enrichment(res_prod))
                        # Opción B: el precio de venta SOLO se fija si el producto
                        # nunca tuvo precio real (<=1.0, "rescate"). Si ya tiene precio
                        # de venta capturado, se respeta y no se sobre-escribe.
                        if (p.list_price or 0.0) <= 1.0:
                            if msrp_usd > 0:
                                vals['list_price'] = msrp_usd * tc
                            else:
                                vals['list_price'] = (costo_usd * tc) * 1.30
                        p.write(vals)
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
