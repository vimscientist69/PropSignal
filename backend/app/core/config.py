from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PropSignal API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://propsignal:propsignal@localhost:5432/propsignal"
    alembic_database_url: str = (
        "postgresql+psycopg://propsignal:propsignal@localhost:5432/propsignal"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
