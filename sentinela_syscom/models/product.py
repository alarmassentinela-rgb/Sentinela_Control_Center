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

    # ------------------------------------------------------------------
    # Helpers compartidos (cron + wizards)
    # ------------------------------------------------------------------
    @api.model
    def _syscom_get_token(self):
        """OAuth client_credentials → access_token (o None si no hay credenciales/falla)."""
        params = self.env['ir.config_parameter'].sudo()
        cid = params.get_param('sentinela_syscom.client_id')
        sec = params.get_param('sentinela_syscom.client_secret')
        if not cid or not sec:
            return None
        try:
            r = requests.post('https://developers.syscom.mx/oauth/token', data={
                'client_id': cid, 'client_secret': sec, 'grant_type': 'client_credentials',
            }, timeout=15)
            return r.json().get('access_token')
        except Exception:
            return None

    @api.model
    def _syscom_api_base(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'sentinela_syscom.api_url', 'https://developers.syscom.mx/api/v1')

    def _syscom_has_movement(self):
        """¿El producto tiene movimiento contable/logístico? (insumo de la limpieza
        de descontinuados; usado por el cron y por el wizard de limpieza)."""
        self.ensure_one()
        variant_ids = self.product_variant_ids.ids
        if not variant_ids:
            return False
        # 1. Inventario actual > 0
        if any(v.qty_available > 0 for v in self.product_variant_ids):
            return True
        # 2. Líneas en facturas posted (cliente o proveedor)
        if self.env['account.move.line'].search_count([
            ('product_id', 'in', variant_ids), ('move_id.state', '=', 'posted'),
        ]):
            return True
        # 3. Ventas no canceladas
        if self.env['sale.order.line'].search_count([
            ('product_id', 'in', variant_ids), ('state', 'not in', ('cancel',)),
        ]):
            return True
        # 4. Compras no canceladas
        if self.env['purchase.order.line'].search_count([
            ('product_id', 'in', variant_ids), ('state', 'not in', ('cancel',)),
        ]):
            return True
        # 5. Movimientos de inventario no cancelados
        if self.env['stock.move'].search_count([
            ('product_id', 'in', variant_ids), ('state', 'not in', ('cancel', 'draft')),
        ]):
            return True
        return False

    def _syscom_sync_new_products(self, headers, api_base, stats):
        """Fase B (v18.0.1.5.0): trae a Odoo los SKUs NUEVOS de las marcas y/o
        categorías configuradas en Ajustes (`sync_brands` / `sync_categories`),
        para mantener el catálogo 'a la par' con Syscom. Solo crea los que aún no
        existen (match por syscom_id O default_code, incluidos archivados → NO se
        re-importan descontinuados ya depurados)."""
        params = self.env['ir.config_parameter'].sudo()
        # Separar SOLO por salto de línea: hay marcas con coma ("TELEWAVE, INC") y
        # hasta con ';' embebido ("W&amp;W") en el nombre, así que coma/';' no sirven.
        def _split(raw):
            return [x.strip() for x in (raw or '').splitlines() if x.strip()]
        brand_names = _split(params.get_param('sentinela_syscom.sync_brands'))
        cat_names = _split(params.get_param('sentinela_syscom.sync_categories'))
        if not brand_names and not cat_names:
            return

        filters = []   # (param, value, label_legible)
        unresolved = []
        # Resolver marcas (acepta nombre o id) contra /marcas
        if brand_names:
            try:
                marcas = requests.get(f'{api_base}/marcas', headers=headers, timeout=20).json()
            except Exception:
                marcas = []
            by_name = {str(m.get('nombre', '')).strip().lower(): str(m.get('id')) for m in marcas if isinstance(m, dict)}
            ids_set = {str(m.get('id')) for m in marcas if isinstance(m, dict)}
            for name in brand_names:
                if name in ids_set:
                    filters.append(('marca', name, name))
                elif name.lower() in by_name:
                    filters.append(('marca', by_name[name.lower()], name))
                else:
                    unresolved.append('marca:%s' % name)
        # Resolver categorías (acepta nombre o id) contra /categorias
        if cat_names:
            try:
                cats = requests.get(f'{api_base}/categorias', headers=headers, timeout=20).json()
            except Exception:
                cats = []
            cby_name = {str(c.get('nombre', '')).strip().lower(): str(c.get('id')) for c in cats if isinstance(c, dict)}
            cids_set = {str(c.get('id')) for c in cats if isinstance(c, dict)}
            for name in cat_names:
                if name in cids_set:
                    filters.append(('categoria', name, name))
                elif name.lower() in cby_name:
                    filters.append(('categoria', cby_name[name.lower()], name))
                else:
                    unresolved.append('categoria:%s' % name)

        stats['unresolved'] = unresolved
        wiz = self.env['syscom.import.wizard'].create({})
        Product = self.with_context(active_test=False)
        since_commit = 0
        for fparam, fval, flabel in filters:
            page, pages = 1, 1
            while page <= pages:
                try:
                    r = requests.get(f'{api_base}/productos', headers=headers,
                                     params={fparam: fval, 'pagina': page}, timeout=30).json()
                except Exception:
                    break
                if not isinstance(r, dict):
                    break
                pages = int(r.get('paginas') or 1)
                prods = r.get('productos', [])
                if not prods:
                    break
                for p in prods:
                    pid = str(p.get('producto_id') or '')
                    modelo = p.get('modelo')
                    if not pid:
                        continue
                    # ¿ya existe? (incluye archivados, para no re-crear descontinuados)
                    if modelo:
                        dom = ['|', ('syscom_id', '=', pid), ('default_code', '=', modelo)]
                    else:
                        dom = [('syscom_id', '=', pid)]
                    if Product.search_count(dom):
                        continue
                    # ficha de detalle (descripción/características/SAT); si falla, usa el de búsqueda
                    detail = p
                    try:
                        rd = requests.get(f'{api_base}/productos/{pid}', headers=headers, timeout=25)
                        if rd.status_code == 200:
                            detail = rd.json()
                    except Exception:
                        pass
                    try:
                        prod = wiz._import_single_product(detail)
                        if prod:
                            stats['new'] += 1
                            since_commit += 1
                    except Exception:
                        stats['errors'] += 1
                    # v18.0.1.6.0: commit por lotes + liberar caché (las fichas traen
                    # HTML/imágenes pesadas; sin esto la RAM crece sin techo y un corte
                    # tira todo lo importado en la transacción).
                    if since_commit >= 25:
                        self.env.cr.commit()
                        self.env.invalidate_all()
                        wiz = self.env['syscom.import.wizard'].create({})
                        Product = self.with_context(active_test=False)
                        since_commit = 0
                page += 1
            # cerrar lote al terminar cada marca/categoría
            self.env.cr.commit()
            self.env.invalidate_all()
            wiz = self.env['syscom.import.wizard'].create({})
            Product = self.with_context(active_test=False)
            since_commit = 0

    def _syscom_cleanup_discontinued(self, stats):
        """Fase C (v18.0.1.5.0): depura los descontinuados detectados. Borra los que
        NO tienen movimiento; archiva (active=False) los que SÍ (preserva historia)."""
        discontinued = self.search([
            ('syscom_discontinued', '=', True), ('active', '=', True),
        ])
        to_delete = self.browse()
        to_archive = self.browse()
        for p in discontinued:
            if p._syscom_has_movement():
                to_archive |= p
            else:
                to_delete |= p
        if to_archive:
            to_archive.write({'active': False})
            stats['archived'] += len(to_archive)
        if to_delete:
            cnt = len(to_delete)
            try:
                to_delete.unlink()
                stats['deleted'] += cnt
            except Exception:
                # Fallback: si algún unlink falla por referencias, archiva
                to_delete.write({'active': False})
                stats['archived'] += cnt

    def _cron_update_syscom_products(self):
        """Robot Nocturno con Reporte a Telegram.
        Fase A: actualiza precio/stock/enriquecimiento de productos ya ligados + detecta
                descontinuados (404 o flag).
        Fase B (v18.0.1.5.0): importa SKUs nuevos de marcas/categorías configuradas.
        Fase C (v18.0.1.5.0): depura descontinuados (borra sin movimiento / archiva con)."""
        start_time = datetime.now()
        params = self.env['ir.config_parameter'].sudo()
        client_id = params.get_param('sentinela_syscom.client_id')
        client_secret = params.get_param('sentinela_syscom.client_secret')
        # v18.0.1.2.0: credenciales Telegram leídas desde ir.config_parameter
        telegram_token = params.get_param('sentinela_syscom.telegram_token')
        chat_id = params.get_param('sentinela_syscom.telegram_chat_id')

        stats = {'total': 0, 'success': 0, 'errors': 0, 'new': 0, 'archived': 0, 'deleted': 0, 'unresolved': []}

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

            for idx, p in enumerate(products, 1):
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
                # v18.0.1.6.0: commit por lotes + liberar caché ORM. Una corrida completa
                # son ~11k productos / horas; sin esto, un corte (SSH/OOM/reinicio) tira
                # TODO el avance (corre en 1 sola transacción) y la RAM se dispara.
                if idx % 200 == 0:
                    self.env.cr.commit()
                    self.env.invalidate_all()

            # Fase B: importar SKUs nuevos de marcas/categorías configuradas
            try:
                self._syscom_sync_new_products(headers, self._syscom_api_base(), stats)
            except Exception as e:
                _logger.exception("SYSCOM: fallo importando productos nuevos: %s", e)

            # Fase C: depurar descontinuados (borrar sin movimiento / archivar con)
            # Activo por defecto; se apaga con el toggle en Ajustes.
            autodel = params.get_param('sentinela_syscom.autodelete_discontinued')
            if (autodel or 'True') != 'False':
                try:
                    self._syscom_cleanup_discontinued(stats)
                except Exception as e:
                    _logger.exception("SYSCOM: fallo depurando descontinuados: %s", e)

            msg = (
                f"🤖 *Reporte Robot Syscom*\n✅ *Estado:* Finalizado\n"
                f"📦 *Procesados:* {stats['total']}\n💰 *Actualizados:* {stats['success']}\n"
                f"🆕 *Nuevos importados:* {stats['new']}\n"
                f"🗑️ *Borrados (descontinuados sin mov.):* {stats['deleted']}\n"
                f"📁 *Archivados (descontinuados con mov.):* {stats['archived']}"
            )
            if stats.get('unresolved'):
                msg += f"\n⚠️ *Sin resolver en Ajustes:* {', '.join(stats['unresolved'])}"
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
