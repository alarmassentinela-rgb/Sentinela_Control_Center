# -*- coding: utf-8 -*-
"""Serializadores (DTO) estables del COC.

Regla: el contrato de la API NO debe romperse si cambia un modelo de Odoo.
Por eso serializamos explicitamente (no exponemos `read()` crudo). Un campo nuevo
en Odoo no aparece en la API hasta que se agrega aqui a proposito.
"""


def serialize_partner(partner):
    """Perfil minimo del cliente para GET /v1/me."""
    return {
        'id': partner.id,
        'name': partner.name,
        'email': partner.email or None,
        'phone': partner.phone or partner.mobile or None,
        'is_company': partner.is_company,
        # Pista de alcance para el empresarial (techo = entidad comercial):
        'commercial_partner_id': partner.commercial_partner_id.id,
    }
