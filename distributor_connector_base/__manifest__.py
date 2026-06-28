# -*- coding: utf-8 -*-
{
    "name": "Distributor Connector Base (Catalog Engine SDK)",
    "summary": "SDK agnóstico del Motor de Catálogo: contrato de conectores, "
               "resiliencia, eventos, observabilidad y auditoría.",
    "version": "18.0.1.0.0",  # Catalog Engine 1.0.0 (ver lib/version.py)
    "category": "Inventory/Catalog",
    "author": "Alea Systems",
    "website": "https://aleasystem.io",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/distributor_backend_views.xml",
    ],
    "installable": True,
    "application": False,
}
