from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    elevenlabs_api_key: str
    elevenlabs_model_id: str
    groq_api_key: str
    groq_model: str

    model_config= SettingsConfigDict(env_file= '.env',extra='ignore')

@lru_cache
def get_settings():
    return Settings()