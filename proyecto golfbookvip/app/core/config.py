from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "golfbookvip"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    BASE_URL: str = "https://api.golfbookvip.com"

    # Database
    DATABASE_URL: str
    POSTGRES_DB: str = "golfbookvip"
    POSTGRES_USER: str = "golfuser"
    POSTGRES_PASSWORD: str = ""

    # Redis
    REDIS_URL: str = ""
    REDIS_PASSWORD: str = ""

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""

    # Firebase
    FIREBASE_CREDENTIALS: str = "/app/firebase-credentials.json"
    FIREBASE_PROJECT_ID: str = "golfbookvip"

    # Email
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "contacto@golfbookvip.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "GolfBookVIP"
    MAIL_STARTTLS: bool = True
    MAIL_TIMEOUT: int = 15
    # Token para que el cron externo dispare el endpoint de recordatorios
    REMINDER_CRON_TOKEN: str = ""

    # Storage
    STORAGE_TYPE: str = "local"
    MEDIA_ROOT: str = "/app/media"
    MEDIA_URL: str = "https://api.golfbookvip.com/media/"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "golfbookvip-media"
    AWS_REGION: str = "us-east-1"

    # APIs externas
    OPENWEATHER_API_KEY: str = ""
    SENTRY_DSN: str = ""
    GEMINI_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: str = '["https://golfbookvip.com","https://www.golfbookvip.com"]'

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
