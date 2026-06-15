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
