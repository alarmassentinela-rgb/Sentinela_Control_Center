# -*- coding: utf-8 -*-
"""Configuración del Gateway (12-factor: todo por entorno). Prefijo COC_."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COC_", env_file=".env", extra="ignore")

    log_level: str = "INFO"

    # Almacén propio del gateway
    gateway_db_url: str = "postgresql+psycopg://coc:coc@localhost:5432/coc_gateway"

    # Odoo (sentinela_api) — handshake de sesión efímera
    odoo_base_url: str = "http://192.168.3.2:8075"
    coc_shared_secret: str = "change-me"          # secreto compartido gateway↔Odoo

    # Seguridad / tokens
    jwt_secret: str = "change-me"
    jwt_access_ttl_min: int = 15                   # access JWT corto
    jwt_refresh_ttl_days: int = 30                 # refresh independiente

    # Política de contraseñas
    password_min_length: int = 8

    # OTP
    otp_provider: str = "mock"                     # mock | evoapi
    otp_length: int = 6
    otp_ttl_sec: int = 300                         # 5 min máximo
    otp_max_attempts: int = 3                      # 3 intentos por código
    otp_cooldown_sec: int = 60                     # cooldown entre solicitudes (mismo teléfono)
    # Rate limiting (ventana + máximos por dimensión)
    otp_rate_window_sec: int = 3600
    otp_max_per_phone: int = 5
    otp_max_per_ip: int = 10
    otp_max_per_device: int = 5

    # Driver WhatsApp (EvoApi) — se usa cuando otp_provider=evoapi
    wa_base_url: str = ""
    wa_api_key: str = ""
    wa_instance: str = ""


settings = Settings()
