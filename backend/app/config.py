from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    secret_key: str
    storage_backend: str = "local"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"
    # Comma-separated list of allowed CORS origins.
    # Example: CORS_ORIGINS=http://localhost:3000,https://app.example.com
    cors_origins: list[str] = ["http://localhost:3000"]

    # First-admin bootstrap — set via environment variables or .env file.
    # When both email and password are provided and no users exist, the app
    # will automatically create the first admin user on startup.
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_mandant_name: str = "Meine Firma"
    bootstrap_skr_variant: str = "skr03"


settings = Settings()
