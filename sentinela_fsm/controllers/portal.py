from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class CustomerPortalFSM(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        # Count only orders belonging to this customer
        FsmOrder = request.env['sentinela.fsm.order']
        values['fsm_count'] = FsmOrder.search_count([('partner_id', '=', partner.id)])
        
        return values

    @http.route(['/my/services', '/my/services/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_services(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        FsmOrder = request.env['sentinela.fsm.order']

        domain = [('partner_id', '=', partner.id)]

        # Pager
        fsm_count = FsmOrder.search_count(domain)
        pager = portal_pager(
            url="/my/services",
            url_args={},
            total=fsm_count,
            page=page,
            step=10
        )

        orders = FsmOrder.search(domain, order='create_date desc', limit=10, offset=pager['offset'])
        values.update({
            'fsm_orders': orders,
            'page_name': 'fsm',
            'pager': pager,
            'default_url': '/my/services',
            'order': False, # KILLER FIX: Prevent portal_breadcrumbs from finding a fake 'order'
        })
        return request.render("sentinela_fsm.portal_my_services", values)

    @http.route(['/my/services/new'], type='http', auth="user", website=True)
    def portal_new_service(self, **kw):
        partner = request.env.user.partner_id
        # Get subscriptions for this partner
        subscriptions = request.env['sentinela.subscription'].search([('partner_id', '=', partner.id)])
        
        return request.render("sentinela_fsm.portal_create_service", {
            'partner': partner,
            'subscriptions': subscriptions,
        })

    @http.route(['/my/services/submit'], type='http', auth="user", website=True, methods=['POST'])
    def portal_submit_service(self, **post):
        if not post.get('description'):
            return request.redirect('/my/services/new?error=description')

        partner = request.env.user.partner_id
        
        # Get subscription if selected
        sub_id = False
        if post.get('subscription_id'):
            sub_id = int(post.get('subscription_id'))
            # Security check: ensure sub belongs to partner
            sub = request.env['sentinela.subscription'].browse(sub_id)
            if sub.partner_id.id != partner.id:
                sub_id = False # Hacker prevention

        vals = {
            'partner_id': partner.id,
            'service_address_id': partner.id, 
            'subscription_id': sub_id,
            'description': post.get('description'),
            'priority': '1' if post.get('urgent') else '0',
            'service_type': 'repair', 
            'stage': 'new',
            'resolution_notes': 'Reportado desde Portal Web'
        }
        
        request.env['sentinela.fsm.order'].create(vals)
        return request.redirect('/my/services?success=True')
