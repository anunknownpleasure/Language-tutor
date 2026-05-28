import json
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from llm import get_raw_response
from models import User, UserVocabulary, Vocabulary
from pipeline import run_pipeline
from prompts import build_conversation_prompt, build_scenario_prompt

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("/scenarios")
async def get_scenarios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate 3 scenario options based on the user's learned vocabulary."""

    # Fetch all learned vocabulary for this user
    result = await db.execute(
        select(Vocabulary)
        .join(UserVocabulary, UserVocabulary.vocabulary_id == Vocabulary.id)
        .where(
            UserVocabulary.user_id == current_user.id,
            UserVocabulary.status == "learned",
        )
    )
    learned_words = result.scalars().all()

    # If user hasn't learned anything yet, use A1 lesson 1 words as fallback
    if not learned_words:
        result = await db.execute(
            select(Vocabulary).where(
                Vocabulary.level == "A1",
                Vocabulary.lesson_number == 1,
            )
        )
        learned_words = result.scalars().all()

    word_list = ", ".join([f"{w.word_fr} ({w.word_en})" for w in learned_words])
    prompt = build_scenario_prompt(word_list)

    # Ask DeepSeek to generate 3 scenarios
    raw = await get_raw_response(
        system_prompt=prompt,
        user_message="Generate 3 scenarios for this learner.",
        history=[],
        temperature=0.8,
    )

    try:
        scenarios = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback scenarios if JSON parsing fails
        scenarios = [
            {
                "title": "At the Café",
                "description": "Order a coffee and greet the waiter politely.",
                "sophie_role": "You are a friendly café waiter in Paris.",
                "goal": "Use bonjour, merci, and s'il vous plaît correctly.",
                "opening_line": "Bonjour ! Qu'est-ce que je vous sers ?"
            }
        ]

    return {"scenarios": scenarios}


@router.post("/chat")
async def chat(
    audio: UploadFile = File(...),
    history: str = Form(default="[]"),
    scenario: str = Form(default="{}"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run the voice pipeline with scenario context injected."""
    audio_bytes = await audio.read()
    conversation_history = json.loads(history)
    scenario_data = json.loads(scenario)

    result = await run_pipeline(
        audio_bytes=audio_bytes,
        conversation_history=conversation_history,
        audio_filename=audio.filename or "audio.webm",
        scenario=scenario_data if scenario_data else None,
    )
    return result
