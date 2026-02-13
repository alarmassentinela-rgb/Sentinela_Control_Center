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
        """ Automated task to update stock and price from Syscom with Auto-Linking and Dynamic TC """
        import requests
        import time
        
        # 1. Credenciales y Configuración
        config = self.env['ir.config_parameter'].sudo()
        client_id = config.get_param('sentinela_syscom.client_id')
        client_secret = config.get_param('sentinela_syscom.client_secret')
        api_url = config.get_param('sentinela_syscom.api_url', 'https://developers.syscom.mx/api/v1')
        
        if not client_id or not client_secret:
            return

        # 2. Obtener Token
        try:
            token_res = requests.post("https://developers.syscom.mx/oauth/token", data={
                'client_id': client_id, 
                'client_secret': client_secret, 
                'grant_type': 'client_credentials'
            }, timeout=20)
            token = token_res.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}
        except:
            return

        # 3. Obtener Tipo de Cambio de Syscom
        try:
            res_tc = requests.get(f"{api_url}/tipocambio", headers=headers, timeout=10)
            tc = float(res_tc.json().get('normal', 17.26))
        except:
            tc = 17.26 # Fallback preventivo

        # 4. Procesar todos los productos físicos que tengan modelo
        products = self.search([
            ('default_code', '!=', False),
            ('detailed_type', 'in', ['product', 'consu'])
        ])
        
        for count, prod in enumerate(products, 1):
            try:
                sys_id = prod.syscom_id
                
                # Auto-Vinculación si no tiene ID
                if not sys_id:
                    search_res = requests.get(f"{api_url}/productos?busqueda={prod.default_code}", headers=headers, timeout=10)
                    if search_res.status_code == 200:
                        results = search_res.json().get('productos', [])
                        if results:
                            sys_id = str(results[0].get('producto_id'))
                        else:
                            continue
                    else:
                        continue

                # Sincronización de Detalles
                res = requests.get(f"{api_url}/productos/{sys_id}", headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    precios = data.get('precios', {})
                    if not isinstance(precios, dict): precios = {}
                        
                    price_usd = float(precios.get('precio_descuento') or precios.get('precio_1') or 0.0)
                    list_price_usd = float(precios.get('precio_lista') or 0.0)
                    special_price_usd = float(precios.get('precio_especial') or 0.0)
                    
                    prod.write({
                        'syscom_id': sys_id,
                        'standard_price': price_usd * tc,
                        'syscom_price_usd': price_usd,
                        'syscom_list_price_usd': list_price_usd,
                        'syscom_suggested_price_usd': special_price_usd,
                        'syscom_stock': int(data.get('total_existencia', 0)),
                        'syscom_last_update': fields.Datetime.now()
                    })
                    
                    # Commit cada 20 para no perder avance y pausas para la API
                    if count % 20 == 0:
                        self.env.cr.commit()
                        time.sleep(0.5)
                        
            except Exception:
                continue
