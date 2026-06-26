# -*- coding: utf-8 -*-
"""Creacion LAZY del usuario portal (Opcion A aprobada).

El usuario portal se crea en el PRIMER login (lo invoca el Gateway tras verificar
identidad), vinculado al res.partner del cliente. Asi:
  - NO se pre-crean miles de res.users.
  - Las RECORD RULES de Odoo (basadas en user.partner_id) son la PRIMERA linea de
    defensa del aislamiento entre clientes; el Gateway nunca las sustituye.
"""
import logging

from odoo import api, models

_logger = logging.getLogger('sentinela_api.security')


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _coc_ensure_portal_user(self, partner):
        """Devuelve (creando si hace falta) el usuario portal del partner dado.

        Idempotente. El login es sintetico (la autenticacion real ocurre en el
        Gateway, no por contrasena de Odoo). Se asignan los grupos base.group_portal
        + group_coc_portal (este ultimo ancla las record rules de aislamiento).
        """
        partner = partner.sudo()
        Users = self.sudo().with_context(active_test=False)

        existing = Users.search(
            [('partner_id', '=', partner.id), ('share', '=', True)], limit=1
        )
        if existing:
            return existing

        group_portal = self.env.ref('base.group_portal')
        group_coc = self.env.ref('sentinela_api.group_coc_portal')
        login = 'coc.partner.%d@portal.sentinela.mx' % partner.id

        vals = {
            'name': partner.name or login,
            'login': login,
            'email': partner.email or False,
            'partner_id': partner.id,
            'groups_id': [(6, 0, [group_portal.id, group_coc.id])],
            'active': True,
        }
        user = Users.with_context(no_reset_password=True).create(vals)
        # Auditoria de seguridad (WS-3 ampliara con IP/origen desde el Gateway).
        _logger.info(
            "COC: usuario portal creado uid=%s login=%s partner_id=%s",
            user.id, user.login, partner.id,
        )
        return user
