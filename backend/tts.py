import io
import edge_tts
from config import settings


async def synthesize(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, settings.tts_voice)

    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    audio_buffer.seek(0)
    return audio_buffer.read()
