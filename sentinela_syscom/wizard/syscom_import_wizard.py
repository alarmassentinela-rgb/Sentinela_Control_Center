from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)

class SyscomImportWizard(models.TransientModel):
    _name = 'syscom.import.wizard'
    _description = 'Import Product from Syscom'

    import_type = fields.Selection([
        ('model', 'Por Modelo'),
        ('brand', 'Por Marca (Lote)')
    ], string='Tipo de Importación', default='model', required=True)

    model_name = fields.Char(string='Modelo / Búsqueda', help="Ejemplo: B50-TURBO o HIKVISION")
    limit = fields.Integer(string='Límite de Productos', default=10, help="Máximo de productos a importar por lote.")

    def _safe_float(self, value):
        """ Converts string to float safely, handling '-' and empty strings """
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    def _get_syscom_token(self):
        config = self.env['ir.config_parameter'].sudo()
        client_id = config.get_param('sentinela_syscom.client_id')
        client_secret = config.get_param('sentinela_syscom.client_secret')
        
        if not client_id or not client_secret:
            raise UserError("Por favor configure las credenciales de Syscom en Ajustes.")

        token_url = "https://developers.syscom.mx/oauth/token"
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            token_res = requests.post(token_url, data=token_data)
            token_res.raise_for_status()
            return token_res.json().get('access_token')
        except Exception as e:
            raise UserError(f"Error de autenticación con Syscom: {str(e)}")

    def _get_or_create_category(self, categories_data):
        """ Creates Odoo category hierarchy based on Syscom category list """
        if not categories_data:
            return False
            
        Cat = self.env['product.category']
        parent_id = self.env.ref('product.product_category_all').id
        
        # Sort by level (1 -> 2 -> 3) to create parents first
        valid_cats = [c for c in categories_data if isinstance(c, dict)]
        sorted_cats = sorted(valid_cats, key=lambda x: int(x.get('nivel', 99)))
        
        last_cat_id = False
        
        for cat_data in sorted_cats:
            if not isinstance(cat_data, dict):
                continue # Skip malformed category data
                
            syscom_cat_name = cat_data.get('nombre', 'General').strip()
            syscom_cat_id_str = str(cat_data.get('id'))
            
            _logger.info(f"SYSCOM CAT DEBUG: Processing '{syscom_cat_name}' (ID {syscom_cat_id_str}) under Parent ID {parent_id}")

            # 1. Search by Syscom ID (Most accurate)
            existing = Cat.search([('syscom_category_id', '=', syscom_cat_id_str)], limit=1)
            
            # 2. If not found, Search by Name AND Parent (Fallback)
            if not existing:
                existing = Cat.search([
                    ('name', '=', syscom_cat_name),
                    ('parent_id', '=', parent_id)
                ], limit=1)
            
            if existing:
                # Update parent if needed (fix hierarchy) and set ID
                if not existing.syscom_category_id:
                    existing.write({'syscom_category_id': syscom_cat_id_str})
                if existing.parent_id.id != parent_id:
                     # Only move if not root 'All' to avoid messing up manual categories
                     if parent_id != self.env.ref('product.product_category_all').id:
                        existing.write({'parent_id': parent_id})
                
                parent_id = existing.id
                last_cat_id = existing.id
            else:
                # Create new category
                new_cat = Cat.create({
                    'name': syscom_cat_name,
                    'parent_id': parent_id,
                    'syscom_category_id': syscom_cat_id_str
                })
                parent_id = new_cat.id
                last_cat_id = new_cat.id
                
        return last_cat_id

    def _import_single_product(self, product_data):
        if not isinstance(product_data, dict):
            _logger.error(f"SYSCOM SKIP: Data is not a dict: {product_data}")
            return False

        Product = self.env['product.template']
        syscom_id = str(product_data.get('producto_id'))
        
        _logger.info(f"SYSCOM DEBUG: Importando {product_data.get('modelo')} - Data: {product_data}")
        
        existing = Product.search([('syscom_id', '=', syscom_id)], limit=1)
        
        # Pricing Logic (Convert USD -> Company Currency)
        precios = product_data.get('precios', {})
        if not isinstance(precios, dict):
            precios = {} # Force dict if API returns list or other type
            
        _logger.info(f"SYSCOM PRICES DEBUG: {precios}") 
        
        # Exact Mapping from Syscom JSON
        price_usd = float(precios.get('precio_descuento') or 0.0) # This is your real cost (26.02)
        list_price_usd = float(precios.get('precio_lista') or 0.0) # (43.70)
        special_price_usd = float(precios.get('precio_especial') or 0.0) # (40.66)
        
        # Get USD Currency
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        company_currency = self.env.company.currency_id
        
        cost_in_company_currency = price_usd
        try:
            if usd and company_currency and usd != company_currency:
                rate = usd.rate
                if rate < 1.0: 
                    cost_in_company_currency = price_usd / rate
                else:
                    cost_in_company_currency = price_usd * rate
        except Exception as e:
            _logger.warning(f"Currency conversion failed: {e}")

        # Category Logic
        cat_id = False
        categorias_list = product_data.get('categorias', [])
        if categorias_list:
            cat_id = self._get_or_create_category(categorias_list)

        vals = {
            'name': product_data.get('titulo'),
            'default_code': product_data.get('modelo'),
            'list_price': cost_in_company_currency * 1.30,
            'standard_price': cost_in_company_currency,
            'syscom_id': syscom_id,
            'syscom_model': product_data.get('modelo'),
            'syscom_brand': product_data.get('marca'),
            'syscom_link': product_data.get('link_privado') or product_data.get('link'),
            'syscom_stock': int(product_data.get('total_existencia', 0)),
            'syscom_weight': self._safe_float(product_data.get('peso')),
            'syscom_description': product_data.get('descripcion', ''),
            'syscom_price_usd': price_usd,
            'syscom_list_price_usd': list_price_usd,
            'syscom_suggested_price_usd': special_price_usd,
            'weight': self._safe_float(product_data.get('peso')), # Peso nativo Odoo
            'l10n_mx_edi_code_sat': product_data.get('sat_key'), # Nuevo mapeo SAT
            'syscom_last_update': fields.Datetime.now(),
            'type': 'consu', # Consumible (Seguro)
        }
        
        if cat_id:
            vals['categ_id'] = cat_id

        # Image Download
        img_url = product_data.get('img_portada')
        if img_url:
            try:
                img_res = requests.get(img_url, timeout=10)
                if img_res.status_code == 200:
                    vals['image_1920'] = base64.b64encode(img_res.content)
            except Exception as e:
                _logger.warning(f"Failed to download image for {syscom_id}: {e}")

        if existing:
            existing.write(vals)
            return existing
        else:
            return Product.create(vals)

    def action_search_and_import(self):
        token = self._get_syscom_token()
        config = self.env['ir.config_parameter'].sudo()
        api_url = config.get_param('sentinela_syscom.api_url', 'https://developers.syscom.mx/api/v1')
        headers = {'Authorization': f'Bearer {token}'}
        
        search_url = f"{api_url}/productos"
        params = {'busqueda': self.model_name}
        
        if self.import_type == 'brand':
            # Syscom API might use different param for brand filter or simple search
            # We use general search for now which covers both
            pass

        try:
            res = requests.get(search_url, headers=headers, params=params)
            res.raise_for_status()
            _logger.info(f"SYSCOM RAW RESPONSE: {res.text}")
            data = res.json()
            
            products = []
            if isinstance(data, dict):
                products = data.get('productos', [])
            elif isinstance(data, list):
                products = data
            
            if not products:
                raise UserError("No se encontraron productos.")
            
            imported_ids = []
            count = 0
            
            # Limit loop
            for p in products:
                if count >= self.limit:
                    break
                prod = self._import_single_product(p)
                if prod:
                    imported_ids.append(prod.id)
                    count += 1
            
            # Show results
            if len(imported_ids) == 1:
                return {
                    'name': 'Producto Importado',
                    'view_mode': 'form',
                    'res_model': 'product.template',
                    'res_id': imported_ids[0],
                    'type': 'ir.actions.act_window',
                }
            else:
                return {
                    'name': f'{len(imported_ids)} Productos Importados',
                    'view_mode': 'list,form',
                    'res_model': 'product.template',
                    'domain': [('id', 'in', imported_ids)],
                    'type': 'ir.actions.act_window',
                }

        except Exception as e:
            raise UserError(f"Error en la importación: {str(e)}")