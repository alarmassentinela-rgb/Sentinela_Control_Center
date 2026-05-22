"""F3.2 — Portal cliente: /my/eventos para ver alarmas + detalle + descarga PDF."""
import logging

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

_logger = logging.getLogger(__name__)


class CustomerPortalEvents(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Hook que agrega contador 'alarm_event_count' al /my (lo usa el sidebar)."""
        values = super()._prepare_home_portal_values(counters)
        if 'alarm_event_count' in counters:
            partner = request.env.user.partner_id
            values['alarm_event_count'] = request.env['sentinela.alarm.event'].sudo().search_count(
                [('partner_id', '=', partner.id)])
        return values

    def _get_event_for_user(self, event_id):
        """Devuelve recordset del evento si el usuario actual puede verlo.
        Lanza AccessError o MissingError según el caso."""
        partner = request.env.user.partner_id
        event = request.env['sentinela.alarm.event'].sudo().browse(int(event_id)).exists()
        if not event:
            raise MissingError(_("Evento no encontrado."))
        if event.partner_id.id != partner.id:
            raise AccessError(_("No tiene permiso para ver este evento."))
        return event

    @http.route(['/my/eventos', '/my/eventos/page/<int:page>'],
                type='http', auth='user', website=False)
    def portal_my_events(self, page=1, sortby='date_desc', filterby='all', **kw):
        partner = request.env.user.partner_id
        Event = request.env['sentinela.alarm.event'].sudo()

        # Filtros por estado
        domain = [('partner_id', '=', partner.id)]
        if filterby == 'active':
            domain.append(('status', 'in', ('active', 'acknowledged', 'in_progress', 'paused', 'escalated')))
        elif filterby == 'resolved':
            domain.append(('status', 'in', ('resolved', 'closed')))

        # Sort
        order_map = {
            'date_desc': 'start_date desc',
            'date_asc': 'start_date asc',
            'priority': 'priority_id desc, start_date desc',
        }
        order = order_map.get(sortby, 'start_date desc')

        total = Event.search_count(domain)
        pager = portal_pager(
            url='/my/eventos',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=total,
            page=page,
            step=15,
        )
        events = Event.search(domain, order=order, limit=15, offset=pager['offset'])
        values = self._prepare_portal_layout_values()
        values.update({
            'events': events,
            'pager': pager,
            'page_name': 'alarm_events',
            'default_url': '/my/eventos',
            'sortby': sortby,
            'filterby': filterby,
            'sortings': {
                'date_desc': 'Más recientes',
                'date_asc': 'Más antiguos',
                'priority': 'Prioridad',
            },
            'filters': {
                'all': 'Todos',
                'active': 'Activos',
                'resolved': 'Resueltos',
            },
        })
        return request.render('sentinela_monitoring.portal_my_events', values)

    @http.route(['/my/eventos/<int:event_id>'],
                type='http', auth='user', website=False)
    def portal_event_detail(self, event_id, **kw):
        try:
            event = self._get_event_for_user(event_id)
        except (AccessError, MissingError):
            return request.redirect('/my/eventos')
        values = self._prepare_portal_layout_values()
        patrol = event.fsm_order_ids.filtered(lambda o: o.service_type == 'patrol')[:1]
        values.update({
            'event': event,
            'patrol_order': patrol,
            'page_name': 'alarm_event_detail',
        })
        return request.render('sentinela_monitoring.portal_event_detail', values)

    @http.route(['/my/eventos/<int:event_id>/pdf'],
                type='http', auth='user', website=False)
    def portal_event_pdf(self, event_id, **kw):
        try:
            event = self._get_event_for_user(event_id)
        except (AccessError, MissingError):
            return request.redirect('/my/eventos')
        report = request.env.ref(
            'sentinela_monitoring.action_report_master_incident', raise_if_not_found=False)
        if not report:
            return request.redirect(f'/my/eventos/{event_id}')
        pdf_content, _ctype = report.sudo()._render_qweb_pdf(
            'sentinela_monitoring.action_report_master_incident', [event.id])
        filename = f"Reporte_Sentinela_{(event.name or 'evento').replace('/', '_').replace(' ', '_')}.pdf"
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', str(len(pdf_content))),
            ],
        )
