from odoo import models, fields, api

class SentinelaSubscriptionSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    connecta_client_id = fields.Char(
        string='Connecta Client ID (Correo)',
        config_parameter='sentinela.connecta_client_id',
        help="El correo electrónico usado para entrar al portal de Connecta/floLIVE."
    )
    connecta_access_token = fields.Char(
        string='Connecta Access Token (Contraseña)',
        config_parameter='sentinela.connecta_access_token',
        help="La contraseña usada para entrar al portal de Connecta/floLIVE."
    )
    # --- Comandos SMS GPS (placeholders de las plantillas) ---
    gps_apn = fields.Char(
        string='APN de las SIM GPS',
        config_parameter='sentinela.gps_apn',
        default='gigsky-02',
        help="APN que se inyecta en {apn} de las plantillas de comando. Fijo para las SIM floLIVE = gigsky-02."
    )
    gps_server_senticar = fields.Char(
        string='Servidor GPS — SentiCar',
        config_parameter='sentinela.gps_server_senticar',
        default='gps.senticar.com',
        help="Host al que marcan los rastreadores de SentiCar (rellena {server}). Usar el DOMINIO "
             "(gps.senticar.com, DNS-only → IP fija) y NO la IP cruda: si cambia la IP fija solo se "
             "actualiza el registro A, sin reconfigurar los GPS. ⚠️ Con dominio, el comando GT06 usa "
             "modo 1 (SERVER,1,...); con IP cruda sería modo 0."
    )
    gps_server_tracksolid = fields.Char(
        string='Servidor GPS — Tracksolid',
        config_parameter='sentinela.gps_server_tracksolid',
        help="Host/IP del servidor para equipos en Tracksolid Pro (rellena {server})."
    )
    gps_server_smake = fields.Char(
        string='Servidor GPS — Smake',
        config_parameter='sentinela.gps_server_smake',
        help="Host/IP del servidor para equipos en Smake (rellena {server})."
    )
    # --- SentiCar / Traccar (API + portal) ---
    traccar_api_url = fields.Char(
        string='SentiCar — URL de la API', config_parameter='sentinela.traccar_api_url',
        default='http://192.168.3.2:8082',
        help="URL interna de la API de SentiCar/Traccar (LAN). Ej.: http://192.168.3.2:8082")
    traccar_api_user = fields.Char(
        string='SentiCar — Usuario API', config_parameter='sentinela.traccar_api_user',
        help="Cuenta de servicio admin de Traccar que usa la integración (Basic Auth).")
    traccar_api_password = fields.Char(
        string='SentiCar — Contraseña API', config_parameter='sentinela.traccar_api_password',
        help="Contraseña de la cuenta de servicio de Traccar.")
    senticar_public_url = fields.Char(
        string='SentiCar — URL pública (panel)', config_parameter='sentinela.senticar_public_url',
        default='https://radar.senticar.com',
        help="URL pública del panel (para los links de rastreo). Ej.: https://radar.senticar.com")
    senticar_portal_base = fields.Char(
        string='SentiCar — Base portal transportista', config_parameter='sentinela.senticar_portal_base',
        default='https://senticar.com',
        help="Dominio base para armar el enlace del portal del transportista (/senticar/t/<token>).")
    senticar_admin_user_id = fields.Char(
        string='SentiCar — IDs de admins', config_parameter='sentinela.senticar_admin_user_id',
        help="IDs de usuarios admin de Traccar que deben ver toda la flota (lista, ej.: 1,5).")
    senticar_reconcile_autoheal = fields.Boolean(
        string='Auto-corregir desajustes (reconciliación)', config_parameter='sentinela.senticar_reconcile_autoheal',
        default=True,
        help="Si está activo, el cron de reconciliación corrige en SentiCar el estado habilitado/"
             "deshabilitado para que coincida con Odoo (no toca SIM ni borra nada).")
    senticar_share_max_hours = fields.Integer(
        string='Máx. horas de link de rastreo', config_parameter='sentinela.senticar_share_max_hours',
        default=168,
        help="Tope de duración de un link de rastreo temporal (por defecto 168 = 7 días).")
    senticar_root_group = fields.Char(
        string='Grupo raíz SentiCar', config_parameter='sentinela.senticar_root_group',
        default='SentiCar',
        help="Nombre del grupo 'paraguas' bajo el que cuelgan los clientes sin distribuidor. "
             "Vacío = sin grupo raíz (clientes al nivel superior).")
