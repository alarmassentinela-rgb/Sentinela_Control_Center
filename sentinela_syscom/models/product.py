from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    syscom_id = fields.Char(string='Syscom ID', help="Internal ID in Syscom database")
    syscom_model = fields.Char(string='Syscom Model', help="Model name used in Syscom")
    syscom_brand = fields.Char(string='Syscom Brand')
    syscom_last_update = fields.Datetime(string='Last Syscom Sync')
    
    # Campo para guardar la URL de la ficha tecnica o imagen
    syscom_link = fields.Char(string='Syscom Link')
    
    # Informacion extendida
    syscom_stock = fields.Integer(string='Stock en Syscom', readonly=True, help="Existencia total en almacenes de Syscom.")
    syscom_weight = fields.Float(string='Peso (kg)', readonly=True)
    syscom_description = fields.Html(string='Descripción Técnica')
    
    # Precios de Referencia en USD
    syscom_price_usd = fields.Float(string='Costo USD (Syscom)', readonly=True, help="Tu costo de compra en USD.")
    syscom_list_price_usd = fields.Float(string='Precio Lista USD (Syscom)', readonly=True)
    syscom_suggested_price_usd = fields.Float(string='Precio Sugerido USD', readonly=True)

    def _cron_update_syscom_products(self):
        """ Automated task to update stock and price from Syscom """
        # Get Token
        config = self.env['ir.config_parameter'].sudo()
        client_id = config.get_param('sentinela_syscom.client_id')
        client_secret = config.get_param('sentinela_syscom.client_secret')
        api_url = config.get_param('sentinela_syscom.api_url', 'https://developers.syscom.mx/api/v1')
        
        if not client_id or not client_secret:
            return # No credentials, skip

        import requests
        try:
            token_url = "https://developers.syscom.mx/oauth/token"
            token_res = requests.post(token_url, data={
                'client_id': client_id, 
                'client_secret': client_secret, 
                'grant_type': 'client_credentials'
            })
            if token_res.status_code != 200:
                return # Auth failed
            token = token_res.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}
        except:
            return

        # Find products linked to Syscom
        products = self.search([('syscom_id', '!=', False)])
        
        for prod in products:
            try:
                # Get Product Detail
                res = requests.get(f"{api_url}/productos/{prod.syscom_id}", headers=headers, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    
                    # Get Price
                    precios = data.get('precios', {})
                    if not isinstance(precios, dict):
                        precios = {}
                        
                    price_usd = float(precios.get('precio_descuento') or precios.get('precio_1') or 0.0)
                    list_price_usd = float(precios.get('precio_lista') or 0.0)
                    special_price_usd = float(precios.get('precio_especial') or 0.0)
                    
                    # Convert to Company Currency
                    usd = self.env.ref('base.USD', raise_if_not_found=False)
                    company_currency = self.env.company.currency_id
                    new_cost = price_usd
                    
                    if usd and company_currency and usd != company_currency:
                        rate = usd.rate
                        if rate < 1.0:
                            new_cost = price_usd / rate
                        else:
                            new_cost = price_usd * rate
                    
                    # Get Stock
                    new_stock = int(data.get('total_existencia', 0))
                    
                    # Update
                    prod.write({
                        'standard_price': new_cost,
                        'syscom_stock': new_stock,
                        'syscom_price_usd': price_usd,
                        'syscom_list_price_usd': list_price_usd,
                        'syscom_suggested_price_usd': special_price_usd,
                        'l10n_mx_edi_code_sat': data.get('sat_key'),
                        'syscom_last_update': fields.Datetime.now()
                    })
                    # Commit every 10 records to save progress
                    if prod.id % 10 == 0:
                        self.env.cr.commit()
                        
            except Exception as e:
                continue # Skip error on single product
