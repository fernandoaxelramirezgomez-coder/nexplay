from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Nexplay Scoring API"
    api_prefix: str = "/api/v1"
    model_version: str = "sim-0.1.0"


settings = Settings()
