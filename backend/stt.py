import io
from groq import AsyncGroq
from config import settings


async def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    client = AsyncGroq(api_key=settings.groq_api_key)

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = await client.audio.transcriptions.create(
        model=settings.whisper_model,
        file=audio_file,
        language="fr",
        response_format="text",
    )
    return response
