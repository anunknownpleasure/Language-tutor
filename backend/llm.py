from openai import AsyncOpenAI
from config import settings
from prompts import FRENCH_TUTOR_SYSTEM_PROMPT, build_lesson_prompt


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
    word_fr: str,
    word_en: str,
    example_fr: str,
    user_message: str,
    history: list[dict],
) -> str:
    """Call the LLM in lesson mode. Returns raw response text for the caller to parse."""
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    messages = [
        {"role": "system", "content": build_lesson_prompt(word_fr, word_en, example_fr)},
        *history,
        {"role": "user", "content": user_message},
    ]

    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        temperature=0.5,   # lower than conversation — we want consistent teaching
        max_tokens=400,
    )

    return response.choices[0].message.content
