# -*- coding: utf-8 -*-
{
    "name": "Distributor Connector — Syscom (reference)",
    "summary": "Conector de REFERENCIA del Motor de Catálogo para Syscom.",
    "version": "18.0.1.0.0",  # Syscom connector 1.0.0
    "category": "Inventory/Catalog",
    "author": "Alea Systems",
    "website": "https://aleasystem.io",
    "license": "LGPL-3",
    "depends": ["distributor_connector_base"],
    "data": [
        "data/distributor_backend.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
