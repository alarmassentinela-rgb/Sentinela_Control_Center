from odoo import models, fields, api
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

_logger = logging.getLogger(__name__)


class _SyscomRateLimiter:
    """P3 (v18.0.1.7.0): regula el ritmo GLOBAL de peticiones a Syscom (thread-safe).
    El límite real de la API es 300/min (header x-ratelimit-limit); usamos un colchón.
    Como `wait()` retiene el lock mientras duerme, también serializa el arranque de
    los hilos del ThreadPoolExecutor al ritmo permitido."""

    def __init__(self, max_per_min=280):
        self._min_interval = 60.0 / max(1, max_per_min)
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            delay = self._next - now
            if delay > 0:
                time.sleep(delay)
                now = time.monotonic()
            self._next = now + self._min_interval


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

    @api.model
    def _syscom_session(self, token):
        """P2 (v18.0.1.7.0): requests.Session con keep-alive (pooling) + reintentos con
        backoff que respetan Retry-After (429/5xx). Mejora robustez y velocidad de la
        conexión (sin handshake TCP/TLS por llamada, reintenta baches de red/limite)."""
        s = requests.Session()
        retry = Retry(
            total=5, backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
        s.mount('https://', adapter)
        s.mount('http://', adapter)
        if token:
            s.headers.update({'Authorization': f'Bearer {token}'})
        return s

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

    # ------------------------------------------------------------------
    # Sincronización de catálogo (v18.0.1.7.0: P1 barrido por listado)
    # ------------------------------------------------------------------
    def _syscom_resolve_scopes(self, session, api_base, stats):
        """Resuelve sync_brands/sync_categories (una por línea) a filtros de la API
        [(param, id, label)]. Acepta nombre o id. Reporta los no resueltos.
        NO separar por coma/';': hay marcas con coma ('TELEWAVE, INC') y con '&amp;'."""
        params = self.env['ir.config_parameter'].sudo()

        def _split(raw):
            return [x.strip() for x in (raw or '').splitlines() if x.strip()]

        brand_names = _split(params.get_param('sentinela_syscom.sync_brands'))
        cat_names = _split(params.get_param('sentinela_syscom.sync_categories'))
        scopes, unresolved = [], []

        if brand_names:
            try:
                marcas = session.get(f'{api_base}/marcas', timeout=20).json()
            except Exception:
                marcas = []
            by_name = {str(m.get('nombre', '')).strip().lower(): str(m.get('id')) for m in marcas if isinstance(m, dict)}
            ids_set = {str(m.get('id')) for m in marcas if isinstance(m, dict)}
            for name in brand_names:
                if name in ids_set:
                    scopes.append(('marca', name, name))
                elif name.lower() in by_name:
                    scopes.append(('marca', by_name[name.lower()], name))
                else:
                    unresolved.append('marca:%s' % name)

        if cat_names:
            try:
                cats = session.get(f'{api_base}/categorias', timeout=20).json()
            except Exception:
                cats = []
            by_name = {str(c.get('nombre', '')).strip().lower(): str(c.get('id')) for c in cats if isinstance(c, dict)}
            ids_set = {str(c.get('id')) for c in cats if isinstance(c, dict)}
            for name in cat_names:
                if name in ids_set:
                    scopes.append(('categoria', name, name))
                elif name.lower() in by_name:
                    scopes.append(('categoria', by_name[name.lower()], name))
                else:
                    unresolved.append('categoria:%s' % name)

        stats['unresolved'] = unresolved
        return scopes

    def _syscom_fetch_details(self, session, api_base, pids, limiter, max_workers=8):
        """P3: descarga /productos/{id} en PARALELO (SOLO red, sin ORM — el ORM no es
        thread-safe). Devuelve {pid: ('ok', json) | ('404', None) | ('err', None)}."""
        results = {}
        if not pids:
            return results

        def _fetch(pid):
            limiter.wait()
            try:
                r = session.get(f'{api_base}/productos/{pid}', timeout=25)
                if r.status_code == 404:
                    return ('404', None)
                if r.status_code == 200:
                    return ('ok', r.json())
                return ('err', None)
            except Exception:
                return ('err', None)

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_fetch, pid): pid for pid in pids}
            for fut in as_completed(futs):
                results[futs[fut]] = fut.result()
        return results

    def _syscom_sync_catalog(self, session, api_base, tc, limiter, stats):
        """P1 (v18.0.1.7.0): BARRIDO POR LISTADO. Por cada marca/categoría configurada,
        pagina /productos (60/pág; el listado YA trae precio+stock+SAT) y en UNA pasada
        actualiza existentes SIN llamada de detalle y junta los nuevos. Los nuevos se
        enriquecen con /productos/{id} EN PARALELO y se crean.
        Esto sustituye las ~11k llamadas de detalle por noche por ~cientos de listados.
        Devuelve el set de IDs de plantilla 'barridos' (para el refresh de sobrantes)."""
        scopes = self._syscom_resolve_scopes(session, api_base, stats)
        swept = set()
        if not scopes:
            return swept

        # P6: precargar índice de existentes en 1 sola query (evita search_count por item)
        recs = self.with_context(active_test=False).search_read(
            ['|', ('syscom_id', '!=', False), ('default_code', '!=', False)],
            ['syscom_id', 'default_code', 'list_price', 'active'])
        by_sid = {r['syscom_id']: r['id'] for r in recs if r.get('syscom_id')}
        by_code = {r['default_code']: r['id'] for r in recs if r.get('default_code')}
        meta = {r['id']: (r['list_price'], r['active']) for r in recs}

        def _vals_from_list(p, pid):
            precios = p.get('precios') or {}
            costo = float(precios.get('precio_descuento') or 0)
            msrp = float(precios.get('precio_lista') or 0)
            exist = p.get('total_existencia')
            if exist is None:
                exist = (p.get('existencia') or {}).get('nuevo', 0)
            v = {
                'syscom_id': pid,
                'syscom_price_usd': costo,
                'syscom_list_price_usd': msrp,
                'syscom_stock': float(exist or 0),
                'syscom_last_update': fields.Datetime.now(),
            }
            if costo > 0:
                v['standard_price'] = costo * tc
            # SAT viene en el listado; NO tocamos caracteristicas/datasheet (solo el
            # detalle los trae; sobrescribirlos con vacío borraría lo enriquecido).
            if p.get('sat_description'):
                v['syscom_sat_description'] = p['sat_description']
            um = p.get('unidad_de_medida') or {}
            if isinstance(um, dict) and um.get('clave_unidad_sat'):
                v['syscom_sat_unit_key'] = um['clave_unidad_sat']
            return v, costo, msrp

        new_items = {}   # pid -> payload del listado (dedup por pid)
        processed = 0

        for sparam, sval, slabel in scopes:
            page, pages = 1, 1
            while page <= pages:
                limiter.wait()
                try:
                    r = session.get(f'{api_base}/productos',
                                    params={sparam: sval, 'pagina': page}, timeout=30).json()
                except Exception:
                    stats['errors'] += 1
                    break
                if not isinstance(r, dict):
                    break
                pages = int(r.get('paginas') or 1)
                prods = r.get('productos') or []
                if not prods:
                    break
                for p in prods:
                    pid = str(p.get('producto_id') or '')
                    modelo = p.get('modelo')
                    if not pid:
                        continue
                    tid = by_sid.get(pid) or (by_code.get(modelo) if modelo else None)
                    if tid:
                        swept.add(tid)
                        lp, active = meta.get(tid, (0.0, True))
                        if not active:
                            continue  # no resucitar archivados (ya quedan marcados swept)
                        v, costo, msrp = _vals_from_list(p, pid)
                        if costo <= 0:
                            stats['errors'] += 1
                            continue
                        # Opción B: list_price solo en rescate (<=1.0)
                        if (lp or 0.0) <= 1.0:
                            v['list_price'] = (msrp * tc) if msrp > 0 else (costo * tc * 1.30)
                        try:
                            self.browse(tid).write(v)
                            stats['updated'] += 1
                        except Exception:
                            stats['errors'] += 1
                    else:
                        new_items.setdefault(pid, p)
                    processed += 1
                    if processed % 200 == 0:
                        self.env.cr.commit()
                        self.env.invalidate_all()
                page += 1
            self.env.cr.commit()
            self.env.invalidate_all()

        # NUEVOS: enriquecer en paralelo (red) y crear (ORM en el hilo principal)
        if new_items:
            details = self._syscom_fetch_details(session, api_base, list(new_items.keys()), limiter)
            wiz = self.env['syscom.import.wizard'].create({})
            since = 0
            for pid, payload in new_items.items():
                status, dj = details.get(pid, ('err', None))
                detail = dj if (status == 'ok' and isinstance(dj, dict)) else payload
                try:
                    prod = wiz._import_single_product(detail)
                    if prod:
                        swept.add(prod.id)
                        stats['created'] += 1
                        since += 1
                except Exception:
                    stats['errors'] += 1
                if since >= 25:
                    self.env.cr.commit()
                    self.env.invalidate_all()
                    wiz = self.env['syscom.import.wizard'].create({})
                    since = 0
            self.env.cr.commit()
            self.env.invalidate_all()
        return swept

    def _syscom_refresh_unswept(self, session, api_base, tc, swept, limiter, stats):
        """Sobrantes: productos activos ligados a Syscom (o en 'rescate' list_price<=1.0)
        que el barrido por listado NO tocó — p. ej. marcas no configuradas o productos
        retirados de Syscom. Se actualizan por detalle (1 llamada c/u, en paralelo) y,
        de paso, se detectan descontinuados (404 / flag). Con todas las marcas
        configuradas, este conjunto son básicamente los descontinuados."""
        base = self.search([
            '|', ('syscom_id', '!=', False), ('list_price', '<=', 1.0),
            ('active', '=', True), ('default_code', '!=', False),
        ])
        leftover = base.filtered(lambda r: r.id not in swept)
        stats['leftover'] = len(leftover)
        if not leftover:
            return

        # Resolver syscom_id faltante (rescate) por búsqueda — secuencial, suelen ser pocos
        sid_by_tid = {}
        for r in leftover:
            sid = r.syscom_id
            if not sid and r.default_code:
                limiter.wait()
                try:
                    rs = session.get(f'{api_base}/productos', params={'busqueda': r.default_code}, timeout=15).json()
                    pl = (rs or {}).get('productos') or []
                    if pl:
                        sid = str(pl[0].get('producto_id'))
                except Exception:
                    sid = None
            if sid:
                sid_by_tid[r.id] = sid

        details = self._syscom_fetch_details(session, api_base, list(set(sid_by_tid.values())), limiter)
        since = 0
        for tid, sid in sid_by_tid.items():
            status, dj = details.get(sid, ('err', None))
            rec = self.browse(tid)
            try:
                if status == '404':
                    if not rec.syscom_discontinued:
                        rec.write({'syscom_discontinued': True, 'syscom_discontinued_date': fields.Date.today()})
                    stats['discontinued'] += 1
                elif status == 'ok' and isinstance(dj, dict):
                    if dj.get('descontinuado') is True and not rec.syscom_discontinued:
                        rec.write({'syscom_discontinued': True, 'syscom_discontinued_date': fields.Date.today()})
                        stats['discontinued'] += 1
                    precios = dj.get('precios') or {}
                    costo = float(precios.get('precio_descuento') or 0)
                    msrp = float(precios.get('precio_lista') or 0)
                    if costo > 0:
                        v = {
                            'syscom_id': sid,
                            'syscom_price_usd': costo, 'syscom_list_price_usd': msrp,
                            'standard_price': costo * tc,
                            'syscom_stock': float((dj.get('existencia') or {}).get('nuevo', 0)),
                            'syscom_last_update': fields.Datetime.now(),
                        }
                        v.update(self._syscom_extract_enrichment(dj))
                        if (rec.list_price or 0.0) <= 1.0:
                            v['list_price'] = (msrp * tc) if msrp > 0 else (costo * tc * 1.30)
                        rec.write(v)
                        stats['updated'] += 1
                else:
                    stats['errors'] += 1
            except Exception:
                stats['errors'] += 1
            since += 1
            if since % 200 == 0:
                self.env.cr.commit()
                self.env.invalidate_all()
        self.env.cr.commit()
        self.env.invalidate_all()

    def _syscom_cleanup_discontinued(self, stats):
        """Fase de limpieza: depura los descontinuados detectados. Borra los que NO
        tienen movimiento; archiva (active=False) los que SÍ (preserva historia)."""
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
        """Robot nocturno (v18.0.1.7.0) — sincronización EFICIENTE del catálogo Syscom.
        P1 barrido por listado (actualiza+crea sin las ~11k llamadas de detalle) ·
        P2 Session con reintentos/backoff · P3 ritmo auto-regulado + detalle en paralelo.
        Fases: (1) barrido por marcas/categorías de Ajustes; (2) refresh de sobrantes +
        detección de descontinuados (404/flag); (3) depuración de descontinuados.
        Commitea por lote en cada fase (resiliencia ante cortes + RAM acotada)."""
        start_time = datetime.now()
        params = self.env['ir.config_parameter'].sudo()
        telegram_token = params.get_param('sentinela_syscom.telegram_token')
        chat_id = params.get_param('sentinela_syscom.telegram_chat_id')
        stats = {'updated': 0, 'created': 0, 'discontinued': 0, 'archived': 0,
                 'deleted': 0, 'errors': 0, 'leftover': 0, 'unresolved': []}

        def send_telegram(msg):
            if not telegram_token or not chat_id:
                return  # Telegram opcional
            try:
                requests.post(f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                              data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
            except Exception:
                pass

        try:
            token = self._syscom_get_token()
            if not token:
                send_telegram("🚨 *Robot Syscom:* sin credenciales / token. Abortado.")
                return
            api_base = self._syscom_api_base()
            session = self._syscom_session(token)
            try:
                rpm = int(params.get_param('sentinela_syscom.max_requests_per_min') or 280)
            except Exception:
                rpm = 280
            limiter = _SyscomRateLimiter(rpm)

            # Tipo de cambio (fallback 17.26)
            tc = 17.26
            try:
                tcj = session.get(f'{api_base}/tipocambio', timeout=10).json()
                if tcj.get('normal'):
                    tc = float(tcj['normal'])
            except Exception:
                pass

            # Fase 1: barrido por listado (eficiente: actualiza + crea)
            swept = self._syscom_sync_catalog(session, api_base, tc, limiter, stats)

            # Fase 2: sobrantes + descontinuados
            try:
                self._syscom_refresh_unswept(session, api_base, tc, swept, limiter, stats)
            except Exception as e:
                _logger.exception("SYSCOM: fallo refresh de sobrantes: %s", e)

            # Fase 3: depurar descontinuados (toggle en Ajustes, ON por defecto)
            autodel = params.get_param('sentinela_syscom.autodelete_discontinued')
            if (autodel or 'True') != 'False':
                try:
                    self._syscom_cleanup_discontinued(stats)
                except Exception as e:
                    _logger.exception("SYSCOM: fallo depurando descontinuados: %s", e)

            mins = (datetime.now() - start_time).total_seconds() / 60.0
            msg = (
                f"🤖 *Robot Syscom* ✅ Finalizado en {mins:.1f} min\n"
                f"💰 Actualizados: {stats['updated']}\n"
                f"🆕 Nuevos: {stats['created']}\n"
                f"⛔ Descontinuados detectados: {stats['discontinued']}\n"
                f"🗑️ Borrados: {stats['deleted']} · 📁 Archivados: {stats['archived']}\n"
                f"↩️ Sobrantes revisados: {stats['leftover']} · ⚠️ Errores: {stats['errors']}"
            )
            if stats['unresolved']:
                msg += f"\n⚠️ Sin resolver en Ajustes: {', '.join(stats['unresolved'])}"
            send_telegram(msg)
        except Exception as e:
            _logger.exception("SYSCOM: error fatal en el cron: %s", e)
            send_telegram(f"🚨 *ERROR ROBOT:* {str(e)}")


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
