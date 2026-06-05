# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home

# Técnico/Patrullero "puro": miembro de Técnico pero NO de Recepción/Despacho,
# Coordinador/Manager ni Administrador del sistema. Esos sí usan el backend.
FIELD_TECH_SPEC = (
    'sentinela_fsm.group_fsm_user'
    ',!sentinela_fsm.group_fsm_dispatcher'
    ',!sentinela_fsm.group_fsm_manager'
    ',!base.group_system'
)


class FsmHome(Home):

    def _user_is_field_tech(self, uid):
        if not uid:
            return False
        user = request.env['res.users'].sudo().browse(uid)
        return bool(user.exists()) and user.has_groups(FIELD_TECH_SPEC)

    def _login_redirect(self, uid, redirect=None):
        # Tras iniciar sesión sin destino explícito, el técnico de campo
        # aterriza directo en su app, no en el backend de Odoo.
        if not redirect and self._user_is_field_tech(uid):
            return '/tech/dashboard'
        return super()._login_redirect(uid, redirect=redirect)

    @http.route()
    def web_client(self, s_action=None, **kw):
        # Bloquea el backend de Odoo (/web, /odoo) a los técnicos de campo:
        # si entran ahí, se les manda a su tablero.
        if request.session.uid and self._user_is_field_tech(request.session.uid):
            return request.redirect('/tech/dashboard')
        return super().web_client(s_action=s_action, **kw)
