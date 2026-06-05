import io
import re
import edge_tts
from config import settings


def clean_for_tts(text: str) -> str:
    """
    Strip markdown symbols that TTS would read out loud as words.
    e.g. **bold** → bold, *italic* → italic, # Heading → Heading
    Also strip [FR]...[/FR] tags (they're handled separately in synthesize_mixed).
    """
    text = re.sub(r'\[/?FR\]', '', text)          # remove [FR] and [/FR] tags
    text = re.sub(r'\*+', '', text)               # remove * and **
    text = re.sub(r'_+', '', text)                # remove _ and __
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # remove # headings
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)   # [link](url) → link
    return text.strip()


async def synthesize(text: str, voice: str = None) -> bytes:
    """Synthesize a single-language text block."""
    voice = voice or settings.tts_voice
    communicate = edge_tts.Communicate(clean_for_tts(text), voice)

    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    audio_buffer.seek(0)
    return audio_buffer.read()


async def synthesize_mixed(text: str) -> bytes:
    """
    Synthesize text that contains mixed English and French.

    Sophie wraps French words/phrases in [FR]...[/FR] tags.
    This function splits on those tags and speaks each segment
    with the appropriate voice:
      - English → en-US-JennyNeural (American)
      - French  → fr-FR-DeniseNeural

    Example input:
      "The pattern is [FR]Je m'appelle[/FR] followed by your name."

    Result: three audio chunks joined together.
    """
    # Split into alternating [English, French, English, French, ...] segments
    # re.split with a capturing group keeps the matched text in the list
    parts = re.split(r'\[FR\](.*?)\[/FR\]', text, flags=re.DOTALL)

    # parts[0] = English, parts[1] = French, parts[2] = English, ...
    combined = io.BytesIO()

    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue

        # Even indices → English, odd indices → French
        if i % 2 == 0:
            voice = settings.tts_voice_en
        else:
            voice = settings.tts_voice

        chunk = await synthesize(part, voice=voice)
        combined.write(chunk)

    combined.seek(0)
    return combined.read()
