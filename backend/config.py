from pathlib import Path
from pydantic_settings import BaseSettings

ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    deepseek_api_key: str
    groq_api_key: str

    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    groq_base_url: str = "https://api.groq.com/openai/v1"
    whisper_model: str = "whisper-large-v3-turbo"

    tts_voice: str = "fr-FR-DeniseNeural"       # used for conversations (French)
    tts_voice_en: str = "en-GB-SoniaNeural"     # used for lessons (English explanations)

    # Used to sign JWTs — change this in production, keep it secret
    secret_key: str = "dev-secret-change-this-in-production"

    class Config:
        env_file = ENV_FILE


settings = Settings()
