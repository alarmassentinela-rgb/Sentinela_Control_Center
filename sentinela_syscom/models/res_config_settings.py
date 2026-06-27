from odoo import models, fields, api
import requests
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    syscom_client_id = fields.Char(string='Client ID', config_parameter='sentinela_syscom.client_id')
    syscom_client_secret = fields.Char(string='Client Secret', config_parameter='sentinela_syscom.client_secret')
    syscom_api_url = fields.Char(string='API URL', default='https://developers.syscom.mx/api/v1', config_parameter='sentinela_syscom.api_url')
    # v18.0.1.2.0: Telegram para reporte nocturno del cron de sincronización
    syscom_telegram_token = fields.Char(
        string='Token Bot Telegram (reporte cron)',
        config_parameter='sentinela_syscom.telegram_token',
        help='Token del bot de Telegram que recibe el reporte diario del cron de actualización de precios/stock. Si está vacío, no se envía reporte.',
    )
    syscom_telegram_chat_id = fields.Char(
        string='Chat ID Telegram',
        config_parameter='sentinela_syscom.telegram_chat_id',
        help='ID del chat (usuario o grupo) que recibe el reporte diario.',
    )
    # v18.0.1.5.0: sincronización de productos NUEVOS + depuración de descontinuados
    # Char (no Text): res.config.settings NO admite Text en config_parameter (rompe el default_get
    # de TODA la página de Ajustes). El widget="text" de la vista conserva el multi-línea.
    syscom_sync_brands = fields.Char(
        string='Marcas a sincronizar (nuevos)',
        config_parameter='sentinela_syscom.sync_brands',
        help='Lista de MARCAS, UNA POR LÍNEA. El cron nocturno trae a Odoo los SKUs '
             'nuevos de estas marcas (los que aún no existen). Usa el nombre tal como '
             'aparece en Syscom (ej. "HiLook by HIKVISION"). Vacío = no importa nuevos '
             'por marca.',
    )
    syscom_sync_categories = fields.Char(
        string='Categorías a sincronizar (nuevos)',
        config_parameter='sentinela_syscom.sync_categories',
        help='Lista de CATEGORÍAS de Syscom, UNA POR LÍNEA (nombre o id, ej. '
             '"Videovigilancia"). El cron trae los SKUs nuevos de estas categorías. '
             '⚠️ Una categoría grande puede traer miles de productos. '
             'Vacío = no importa nuevos por categoría.',
    )
    syscom_max_rpm = fields.Integer(
        string='Máx. peticiones/min a Syscom',
        default=280,
        config_parameter='sentinela_syscom.max_requests_per_min',
        help='Tope de peticiones por minuto a la API de Syscom (el límite real es ~300). '
             'El cron se auto-regula bajo este número y paraleliza las llamadas de '
             'detalle sin pasarse. Bájalo si Syscom devuelve 429.',
    )
    syscom_autodelete_discontinued = fields.Boolean(
        string='Depurar descontinuados automáticamente',
        config_parameter='sentinela_syscom.autodelete_discontinued',
        default=True,
        help='Si está activo, el cron nocturno BORRA los productos descontinuados que no '
             'tengan movimiento (ventas/compras/stock/facturas) y ARCHIVA los que sí, '
             'preservando la historia contable.',
    )

    def action_test_syscom_connection(self):
        """ Tests the connection to Syscom API using the provided credentials """
        self.ensure_one()
        url = "https://developers.syscom.mx/oauth/token"
        data = {
            'client_id': self.syscom_client_id,
            'client_secret': self.syscom_client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                token = response.json().get('access_token')
                # Try a simple GET to verify full access
                api_url = self.syscom_api_url or 'https://developers.syscom.mx/api/v1'
                headers = {'Authorization': f'Bearer {token}'}
                # Check categories as a lightweight test
                test_res = requests.get(f'{api_url}/categorias', headers=headers)
                
                if test_res.status_code == 200:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Connection Successful',
                            'message': 'Successfully connected to Syscom API!',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
            
            raise UserError(f"Connection Failed: {response.text}")
            
        except Exception as e:
            raise UserError(f"Error connecting to Syscom: {str(e)}")
