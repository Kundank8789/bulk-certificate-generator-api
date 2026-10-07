from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./certificate_generator.db"
    storage_dir: str = "storage/certificates"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
