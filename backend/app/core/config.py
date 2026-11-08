from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Every field can be overridden with an ARIADNE_* env var."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ARIADNE_", extra="ignore")

    database_url: str = "postgresql+psycopg://ariadne:ariadne@localhost:5750/ariadne"
    jwt_secret: str = "dev-only-insecure-secret-change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Unlock every module regardless of progress (handy for demos and marking).
    unlock_all: bool = False


settings = Settings()
