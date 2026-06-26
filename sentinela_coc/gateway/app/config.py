# -*- coding: utf-8 -*-
"""Configuracion del Gateway (12-factor: todo por entorno). Prefijo COC_."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COC_", env_file=".env", extra="ignore")

    log_level: str = "INFO"

    # Odoo (sentinela_api)
    odoo_base_url: str = "http://192.168.3.2:8069"
    odoo_db: str = "V18"
    odoo_service_login: str = ""
    odoo_service_password: str = ""

    # Almacen propio del gateway
    gateway_db_url: str = "postgresql://coc:coc@localhost:5432/coc_gateway"

    # Seguridad (WS-5)
    jwt_secret: str = "change-me"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 30
    otp_ttl_sec: int = 300
    otp_max_attempts: int = 5

    # WhatsApp OTP (WS-5)
    wa_driver: str = "evoapi"
    wa_base_url: str = ""
    wa_api_key: str = ""
    wa_instance: str = ""


settings = Settings()
