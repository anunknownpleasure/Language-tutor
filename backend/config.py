from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str
    groq_api_key: str

    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    groq_base_url: str = "https://api.groq.com/openai/v1"
    whisper_model: str = "whisper-large-v3-turbo"

    tts_voice: str = "fr-FR-DeniseNeural"

    class Config:
        env_file = ".env"


settings = Settings()
