from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str
    debug: bool
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    database_url: str

    storage_path: str = "storage/documents"
    max_file_size: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    redis_host: str = "localhost"
    redis_port: int = 6379

settings = Settings()