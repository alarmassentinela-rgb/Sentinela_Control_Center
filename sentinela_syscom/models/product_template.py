from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    syscom_product_id = fields.Char(string='ID de Producto Syscom', help="ID único de la API de Syscom")
    syscom_model = fields.Char(string='Modelo Syscom', help="Modelo exacto en Syscom")

    @api.model
    def _cron_update_syscom_products(self):
        """Función profesional para actualización nocturna masiva"""
        _logger.info("SENTINELA: Iniciando Robot Nocturno de Syscom (Precios y Stock)")
        
        params = self.env['ir.config_parameter'].sudo()
        client_id = params.get_param('sentinela_syscom.client_id')
        client_secret = params.get_param('sentinela_syscom.client_secret')
        
        if not client_id or not client_secret:
            _logger.error("SENTINELA: Error - Faltan llaves de API")
            return

        try:
            # 1. Obtener Token (URL oficial 2026)
            token_url = 'https://developers.syscom.mx/oauth/token'
            res_token = requests.post(token_url, data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'client_credentials'
            }, timeout=15)
            token = res_token.json().get('access_token')
            
            if not token:
                _logger.error("SENTINELA: Token inválido")
                return

            # 2. Buscar productos vinculados
            headers = {'Authorization': f'Bearer {token}'}
            products = self.search([('syscom_product_id', '!=', False), ('active', '=', True)])
            tc = 17.26
            margin = 1.30
            
            count = 0
            for p in products:
                try:
                    url_prod = f'https://developers.syscom.mx/api/v1/productos/{p.syscom_product_id}'
                    res_prod = requests.get(url_prod, headers=headers, timeout=10).json()
                    
                    costo_usd = float(res_prod.get('precio_lista', 0))
                    existencia = float(res_prod.get('existencia', {}).get('nuevo', 0))
                    
                    if costo_usd > 0:
                        p.write({
                            'standard_price': costo_usd * tc,
                            'list_price': costo_usd * tc * margin,
                            # Aquí podríamos actualizar stock si fuera necesario
                        })
                        count += 1
                except: continue
            
            _logger.info(f"SENTINELA: Sincronización exitosa. {count} productos actualizados.")
            
        except Exception as e:
            _logger.error(f"SENTINELA: Fallo en el Robot Nocturno: {str(e)}")
