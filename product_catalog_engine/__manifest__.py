# -*- coding: utf-8 -*-
{
    "name": "Product Catalog Engine",
    "summary": "Motor de Catálogo: índice de búsqueda ligero, caché reemplazable y "
               "base de promoción/sincronización (D3a).",
    "version": "18.0.1.0.0",  # Catalog Engine 1.0.0
    "category": "Inventory/Catalog",
    "author": "Alea Systems",
    "website": "https://aleasystem.io",
    "license": "LGPL-3",
    "depends": ["distributor_connector_base", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/sync_policy_data.xml",
        "data/ir_cron_data.xml",
        "views/catalog_item_views.xml",
    ],
    "installable": True,
    "application": False,
}
