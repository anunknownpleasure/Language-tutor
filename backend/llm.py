from openai import AsyncOpenAI
from config import settings
from prompts import FRENCH_TUTOR_SYSTEM_PROMPT, build_lesson_prompt, build_conversation_prompt


def _parse_response(raw: str) -> dict:
    result = {"response_fr": "", "response_en": "", "correction": ""}
    for line in raw.strip().splitlines():
        if line.startswith("FRENCH:"):
            result["response_fr"] = line[7:].strip()
        elif line.startswith("ENGLISH:"):
            result["response_en"] = line[8:].strip()
        elif line.startswith("CORRECTION:"):
            result["correction"] = line[11:].strip()
    return result


async def get_tutor_response(user_message: str, conversation_history: list[dict]) -> dict:
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    messages = [
        {"role": "system", "content": FRENCH_TUTOR_SYSTEM_PROMPT},
        *conversation_history,
        {"role": "user", "content": user_message},
    ]

    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        temperature=0.7,
        max_tokens=300,
    )

    raw = response.choices[0].message.content
    return _parse_response(raw)


async def get_lesson_response(
    pattern_fr: str,
    pattern_en: str,
    pattern_explanation: str,
    pattern_tip: str,
    word_fr: str,
    word_en: str,
    example_fr: str,
    words_context: str = "",
    user_message: str = "",
    history: list[dict] = None,
    level: str = "A1",
) -> str:
    """Call the LLM in lesson mode — Michael Thomas method.
    Returns raw response text for the caller to parse (MESSAGE: / ATTEMPT_SCORE:)."""
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    history = history or []

    system_prompt = build_lesson_prompt(
        pattern_fr=pattern_fr,
        pattern_en=pattern_en,
        pattern_explanation=pattern_explanation,
        pattern_tip=pattern_tip,
        word_fr=word_fr,
        word_en=word_en,
        example_fr=example_fr,
        words_context=words_context,
        level=level,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        temperature=0.5,
        max_tokens=600,   # MT intro messages are rich — give enough room
    )

    return response.choices[0].message.content


async def get_raw_response(
    system_prompt: str,
    user_message: str,
    history: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> str:
    """Generic LLM call — any system prompt, returns raw text. Used by scenarios and testing."""
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


async def get_conversation_response(
    user_message: str,
    conversation_history: list[dict],
    scenario: dict,
) -> dict:
    """Call the LLM in conversation mode with a scenario injected."""
    raw = await get_raw_response(
        system_prompt=build_conversation_prompt(scenario),
        user_message=user_message,
        history=conversation_history,
        temperature=0.7,
        max_tokens=300,
    )
    return _parse_response(raw)
