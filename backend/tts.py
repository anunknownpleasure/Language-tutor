import io
import re
import edge_tts
from config import settings


def clean_for_tts(text: str) -> str:
    """
    Strip markdown symbols that TTS would read out loud as words.
    e.g. **bold** → bold, *italic* → italic, # Heading → Heading
    """
    text = re.sub(r'\*+', '', text)       # remove * and **
    text = re.sub(r'_+', '', text)        # remove _ and __
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # remove # headings
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)   # [link text](url) → link text
    return text.strip()


async def synthesize(text: str, voice: str = None) -> bytes:
    voice = voice or settings.tts_voice
    communicate = edge_tts.Communicate(clean_for_tts(text), voice)

    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    audio_buffer.seek(0)
    return audio_buffer.read()
