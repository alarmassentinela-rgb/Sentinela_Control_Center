"""post_init_hook: siembra el backend Syscom y migra credenciales legacy
(sentinela_syscom.*) a los secretos del backend, sin re-capturarlas a mano.
"""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    backend = env.ref("distributor_syscom.backend_syscom", raise_if_not_found=False)
    if not backend:
        return
    icp = env["ir.config_parameter"].sudo()
    # Migrar credenciales del módulo legacy sentinela_syscom si existen.
    mapping = {
        "client_id": "sentinela_syscom.client_id",
        "client_secret": "sentinela_syscom.client_secret",
        "token_cache": "sentinela_syscom.token_cache",
        "token_expiry": "sentinela_syscom.token_expiry",
    }
    copied = 0
    for secret_name, legacy_key in mapping.items():
        val = icp.get_param(legacy_key)
        if val and not backend.get_secret(secret_name):
            backend.set_secret(secret_name, val)
            copied += 1
    api = icp.get_param("sentinela_syscom.api_url")
    if api and not backend.api_url:
        backend.api_url = api
    _logger.info("distributor_syscom: backend sembrado, %s secretos migrados", copied)
