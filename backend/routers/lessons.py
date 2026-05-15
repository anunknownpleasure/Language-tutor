from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from llm import get_lesson_response
from models import LessonProgress, UserVocabulary, Vocabulary

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

# Hardcoded test user until auth is added
TEST_USER_ID = 1

# Word is learned when: attempt_count >= 3 AND score >= 80
LEARNED_MIN_ATTEMPTS = 3
LEARNED_MIN_SCORE = 80
LESSONS_FOR_CONVERSATIONS = 5
LESSONS_FOR_TESTING = 10


# ── Request / Response shapes ──────────────────────────────────────────────

class RespondRequest(BaseModel):
    vocabulary_id: int      # which word is being practiced
    message: str            # what the learner typed
    history: list[dict]     # conversation history for this word session


class WordStatus(BaseModel):
    id: int
    word_fr: str
    word_en: str
    example_sentence_fr: str
    score: float
    attempt_count: int
    status: str             # "introduced" or "learned"


class LessonResponse(BaseModel):
    level: str
    lesson_number: int
    words: list[WordStatus]
    lessons_completed: int
    conversations_unlocked: bool
    testing_unlocked: bool


# ── Helper functions ───────────────────────────────────────────────────────

def calculate_new_score(old_score: float, attempt_score: int) -> float:
    """Apply weighted formula and clamp between 0 and 100."""
    if attempt_score >= 60:
        new_score = old_score + 0.3 * attempt_score
    else:
        new_score = old_score - 0.2 * attempt_score
    return max(0.0, min(100.0, new_score))


def parse_attempt_score(response_text: str) -> int | None:
    """Extract ATTEMPT_SCORE from Sophie's response. Returns None if not present."""
    for line in response_text.strip().splitlines():
        if line.startswith("ATTEMPT_SCORE:"):
            try:
                return int(line[14:].strip())
            except ValueError:
                return None
    return None


def parse_message(response_text: str) -> str:
    """Extract MESSAGE from Sophie's response."""
    for line in response_text.strip().splitlines():
        if line.startswith("MESSAGE:"):
            return line[8:].strip()
    # Fallback: return the whole response if format isn't followed
    return response_text.strip()


async def get_lessons_completed(db: AsyncSession, user_id: int, level: str) -> int:
    """Count how many lessons are completed for a user at a given level."""
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.level == level,
            LessonProgress.completed == True,
        )
    )
    return len(result.scalars().all())


async def get_or_create_user_vocabulary(
    db: AsyncSession, user_id: int, vocabulary_id: int
) -> UserVocabulary:
    """Get existing UserVocabulary row or create a new one."""
    result = await db.execute(
        select(UserVocabulary).where(
            UserVocabulary.user_id == user_id,
            UserVocabulary.vocabulary_id == vocabulary_id,
        )
    )
    uv = result.scalar_one_or_none()
    if not uv:
        uv = UserVocabulary(user_id=user_id, vocabulary_id=vocabulary_id)
        db.add(uv)
        await db.flush()
    return uv


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("", response_model=LessonResponse)
async def get_lesson(db: AsyncSession = Depends(get_db)):
    """Return the current lesson words and progress for the test user."""

    # For now hardcode level A1 lesson 1 — will use user's actual progress later
    level = "A1"
    lesson_number = 1

    # Fetch the 7 words for this lesson
    result = await db.execute(
        select(Vocabulary).where(
            Vocabulary.level == level,
            Vocabulary.lesson_number == lesson_number,
        )
    )
    vocab_words = result.scalars().all()

    # Build word status list
    words = []
    for word in vocab_words:
        uv = await get_or_create_user_vocabulary(db, TEST_USER_ID, word.id)
        await db.commit()
        words.append(WordStatus(
            id=word.id,
            word_fr=word.word_fr,
            word_en=word.word_en,
            example_sentence_fr=word.example_sentence_fr,
            score=uv.score,
            attempt_count=uv.attempt_count,
            status=uv.status,
        ))

    lessons_completed = await get_lessons_completed(db, TEST_USER_ID, level)

    return LessonResponse(
        level=level,
        lesson_number=lesson_number,
        words=words,
        lessons_completed=lessons_completed,
        conversations_unlocked=lessons_completed >= LESSONS_FOR_CONVERSATIONS,
        testing_unlocked=lessons_completed >= LESSONS_FOR_TESTING,
    )


@router.post("/respond")
async def respond(req: RespondRequest, db: AsyncSession = Depends(get_db)):
    """
    User sends a message practicing a word.
    Sophie evaluates it, we update the score, check if word is learned.
    """

    # Fetch the word being practiced
    word = await db.get(Vocabulary, req.vocabulary_id)
    if not word:
        return {"error": "Word not found"}

    # Get or create the user's progress record for this word
    uv = await get_or_create_user_vocabulary(db, TEST_USER_ID, req.vocabulary_id)

    # Call the LLM with the lesson prompt for this specific word
    raw_response = await get_lesson_response(
        word_fr=word.word_fr,
        word_en=word.word_en,
        example_fr=word.example_sentence_fr,
        user_message=req.message,
        history=req.history,
    )

    # Parse Sophie's response
    message = parse_message(raw_response)
    attempt_score = parse_attempt_score(raw_response)

    word_learned = False
    lesson_complete = False

    # Only update score if Sophie included an ATTEMPT_SCORE
    if attempt_score is not None:
        uv.score = calculate_new_score(uv.score, attempt_score)
        uv.attempt_count += 1
        uv.updated_at = datetime.utcnow()

        # Check if word is now learned
        if uv.attempt_count >= LEARNED_MIN_ATTEMPTS and uv.score >= LEARNED_MIN_SCORE:
            uv.status = "learned"
            word_learned = True

        await db.commit()

        # Check if all 7 words in this lesson are learned
        result = await db.execute(
            select(Vocabulary).where(
                Vocabulary.level == word.level,
                Vocabulary.lesson_number == word.lesson_number,
            )
        )
        lesson_words = result.scalars().all()
        lesson_word_ids = [w.id for w in lesson_words]

        learned_result = await db.execute(
            select(UserVocabulary).where(
                UserVocabulary.user_id == TEST_USER_ID,
                UserVocabulary.vocabulary_id.in_(lesson_word_ids),
                UserVocabulary.status == "learned",
            )
        )
        learned_count = len(learned_result.scalars().all())

        if learned_count == len(lesson_words):
            # Mark lesson as complete
            lesson_result = await db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == TEST_USER_ID,
                    LessonProgress.level == word.level,
                    LessonProgress.lesson_number == word.lesson_number,
                )
            )
            lp = lesson_result.scalar_one_or_none()
            if not lp:
                lp = LessonProgress(
                    user_id=TEST_USER_ID,
                    level=word.level,
                    lesson_number=word.lesson_number,
                )
                db.add(lp)
            if not lp.completed:
                lp.completed = True
                lp.completed_at = datetime.utcnow()
                lesson_complete = True
            await db.commit()

    return {
        "message": message,
        "attempt_score": attempt_score,
        "new_score": uv.score,
        "attempt_count": uv.attempt_count,
        "word_learned": word_learned,
        "lesson_complete": lesson_complete,
    }
