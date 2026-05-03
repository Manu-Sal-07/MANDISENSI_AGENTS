from pydantic import BaseSettings


class Settings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_cache_ttl: int = 3600
    log_level: str = "INFO"

    class Config:
        env_prefix = "MANDISENSE_"


settings = Settings()
