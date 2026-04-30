import base64
from stt import transcribe
from llm import get_tutor_response
from tts import synthesize


async def run_pipeline(
    audio_bytes: bytes,
    conversation_history: list[dict],
    audio_filename: str = "audio.webm",
) -> dict:
    # Stage 1: speech to text
    transcript = await transcribe(audio_bytes, audio_filename)

    # Stage 2: LLM response
    llm_result = await get_tutor_response(transcript, conversation_history)

    # Stage 3: text to speech
    audio_out = await synthesize(llm_result["response_fr"])
    audio_b64 = base64.b64encode(audio_out).decode("utf-8")

    return {
        "transcript": transcript,
        "response_fr": llm_result["response_fr"],
        "response_en": llm_result["response_en"],
        "correction": llm_result.get("correction", ""),
        "audio_base64": audio_b64,
    }
