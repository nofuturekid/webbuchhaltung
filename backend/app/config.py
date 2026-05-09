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


settings = Settings()
