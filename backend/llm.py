import asyncio
from openai import AsyncOpenAI
from config import settings
from prompts import (
    FRENCH_TUTOR_SYSTEM_PROMPT,
    build_lesson_prompt,
    build_conversation_prompt,
    build_scorer_prompt,
)


# ── Shared client factory ──────────────────────────────────────────────────

def _client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )


# ── Retry wrapper ──────────────────────────────────────────────────────────

async def _call_with_retry(messages: list, temperature: float, max_tokens: int, retries: int = 2) -> str:
    """
    Call the LLM and retry up to `retries` times on failure or empty response.
    Returns the raw response string.

    Why retry? DeepSeek occasionally times out or returns an empty string.
    Two retries with a short pause fixes ~95% of transient failures.
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = await _client().chat.completions.create(
                model=settings.deepseek_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content
            # Empty response — treat as a failure and retry
            last_error = ValueError("LLM returned empty response")
        except Exception as e:
            last_error = e

        if attempt < retries:
            await asyncio.sleep(1)  # short pause before retrying

    raise last_error


# ── Response parser (conversations / tutor mode) ───────────────────────────

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


# ── Tutor mode (home page free conversation) ──────────────────────────────

async def get_tutor_response(user_message: str, conversation_history: list[dict]) -> dict:
    messages = [
        {"role": "system", "content": FRENCH_TUTOR_SYSTEM_PROMPT},
        *conversation_history,
        {"role": "user", "content": user_message},
    ]
    raw = await _call_with_retry(messages, temperature=0.7, max_tokens=300)
    return _parse_response(raw)


# ── Lesson mode (Sophie teaches) ──────────────────────────────────────────

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
    """
    Call Sophie in lesson mode.
    Returns raw response text (caller extracts MESSAGE: field).

    Sophie's only job here is to TEACH. She never scores — that's handled
    by get_score() as a separate silent call.
    """
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

    return await _call_with_retry(messages, temperature=0.5, max_tokens=600)


# ── Silent scorer ──────────────────────────────────────────────────────────

async def get_score(
    word_fr: str,
    word_en: str,
    pattern_fr: str,
    student_input: str,
) -> int | None:
    """
    Silently score the student's sentence attempt.
    Returns an integer 0-100, or None if scoring fails.

    This is completely separate from Sophie's teaching response.
    The student never sees this call happen.
    """
    if not student_input or student_input.strip().lower() in ("start", ""):
        return None  # not a real attempt — nothing to score

    messages = [
        {"role": "system", "content": build_scorer_prompt(word_fr, word_en, pattern_fr)},
        {"role": "user", "content": student_input},
    ]

    try:
        raw = await _call_with_retry(messages, temperature=0.0, max_tokens=10)
        return int(raw.strip().split()[0])  # take first token, convert to int
    except (ValueError, TypeError):
        return None  # if the scorer returns garbage, skip scoring silently


# ── Generic raw call (scenarios, testing) ─────────────────────────────────

async def get_raw_response(
    system_prompt: str,
    user_message: str,
    history: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> str:
    """Generic LLM call — any system prompt, returns raw text."""
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]
    return await _call_with_retry(messages, temperature=temperature, max_tokens=max_tokens)


# ── Conversation mode (role-play scenarios) ───────────────────────────────

async def get_conversation_response(
    user_message: str,
    conversation_history: list[dict],
    scenario: dict,
) -> dict:
    raw = await get_raw_response(
        system_prompt=build_conversation_prompt(scenario),
        user_message=user_message,
        history=conversation_history,
        temperature=0.7,
        max_tokens=300,
    )
    return _parse_response(raw)
