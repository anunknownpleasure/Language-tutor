import base64
import json
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from llm import get_lesson_response, get_score
from models import LessonPattern, LessonProgress, UserVocabulary, User, Vocabulary
from stt import transcribe
from tts import synthesize_mixed

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

# Word is learned when: attempt_count >= 3 AND score >= 80
LEARNED_MIN_ATTEMPTS = 3
LEARNED_MIN_SCORE = 80
LESSONS_FOR_CONVERSATIONS = 5
LESSONS_FOR_TESTING = 10


# ── Request / Response shapes ──────────────────────────────────────────────

class WordStatus(BaseModel):
    id: int
    word_fr: str
    word_en: str
    example_sentence_fr: str
    score: float
    attempt_count: int
    status: str             # "introduced" or "learned"


class PatternInfo(BaseModel):
    pattern_fr: str
    pattern_en: str
    explanation: str
    tip: str | None


class LessonResponse(BaseModel):
    level: str
    lesson_number: int
    pattern: PatternInfo | None
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
    """
    Extract MESSAGE from Sophie's response.
    Handles multi-line messages — collects every line until ATTEMPT_SCORE or end of text.
    """
    lines = response_text.strip().splitlines()
    message_lines = []
    in_message = False

    for line in lines:
        if line.startswith("MESSAGE:"):
            in_message = True
            rest = line[8:].strip()
            if rest:
                message_lines.append(rest)
        elif line.startswith("ATTEMPT_SCORE:"):
            break          # ATTEMPT_SCORE always comes after MESSAGE — stop here
        elif in_message:
            message_lines.append(line)

    if message_lines:
        return "\n".join(message_lines).strip()

    # Fallback: return everything that isn't an ATTEMPT_SCORE line
    fallback = "\n".join(
        line for line in lines if not line.startswith("ATTEMPT_SCORE:")
    ).strip()
    return fallback or response_text.strip()


async def get_user_level(db: AsyncSession, user_id: int) -> str:
    """Return the user's current level (e.g. 'A1' or 'A2')."""
    user = await db.get(User, user_id)
    return user.current_level if user else "A1"


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


async def get_current_lesson_number(db: AsyncSession, user_id: int, level: str) -> int:
    """
    Find the first lesson the user hasn't completed yet.
    If all 10 are done, returns 10 (last lesson stays available for review).
    """
    result = await db.execute(
        select(LessonProgress.lesson_number).where(
            LessonProgress.user_id == user_id,
            LessonProgress.level == level,
            LessonProgress.completed == True,
        )
    )
    completed = {row for row in result.scalars().all()}

    for n in range(1, 11):
        if n not in completed:
            return n
    return 10  # all done — show last lesson for review


async def build_words_context(
    db: AsyncSession,
    user_id: int,
    current_vocabulary_id: int,
    level: str,
    lesson_number: int,
) -> str:
    """
    Build a one-line lesson-progress summary for Sophie's system prompt.
    Tells her which words are learned, which she's teaching now, and what's still ahead.
    Example: "Learned: bonjour, bonsoir | Teaching now: je m'appelle (my name is) | Still to cover: enchanté, au revoir"
    """
    # All words in this lesson
    words_result = await db.execute(
        select(Vocabulary).where(
            Vocabulary.level == level,
            Vocabulary.lesson_number == lesson_number,
        )
    )
    all_words = words_result.scalars().all()
    word_ids = [w.id for w in all_words]

    # Their progress rows (one query for all)
    uv_result = await db.execute(
        select(UserVocabulary).where(
            UserVocabulary.user_id == user_id,
            UserVocabulary.vocabulary_id.in_(word_ids),
        )
    )
    uv_map = {uv.vocabulary_id: uv for uv in uv_result.scalars().all()}

    learned = []
    current_label = ""

    for w in all_words:
        uv = uv_map.get(w.id)
        is_learned = uv and uv.status == "learned"

        if w.id == current_vocabulary_id:
            current_label = f"{w.word_fr} ({w.word_en})"
        elif is_learned:
            learned.append(w.word_fr)
        # Future words are intentionally hidden from Sophie

    parts = []
    if learned:
        parts.append(f"Learned so far: {', '.join(learned)}")
    parts.append(f"Teaching now: {current_label}")

    return " | ".join(parts)


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


async def fetch_lesson_pattern(
    db: AsyncSession, level: str, lesson_number: int
) -> LessonPattern | None:
    """Fetch the MT pattern for a given lesson."""
    result = await db.execute(
        select(LessonPattern).where(
            LessonPattern.level == level,
            LessonPattern.lesson_number == lesson_number,
        )
    )
    return result.scalar_one_or_none()


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("", response_model=LessonResponse)
async def get_lesson(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current lesson words, pattern, and progress for the logged-in user."""

    level = await get_user_level(db, current_user.id)
    lesson_number = await get_current_lesson_number(db, current_user.id, level)

    # Fetch the 7 vocabulary words for this lesson
    result = await db.execute(
        select(Vocabulary).where(
            Vocabulary.level == level,
            Vocabulary.lesson_number == lesson_number,
        )
    )
    vocab_words = result.scalars().all()

    # Fetch the MT pattern for this lesson
    pattern = await fetch_lesson_pattern(db, level, lesson_number)

    # Build word status list
    words = []
    for word in vocab_words:
        uv = await get_or_create_user_vocabulary(db, current_user.id, word.id)
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

    lessons_completed = await get_lessons_completed(db, current_user.id, level)

    return LessonResponse(
        level=level,
        lesson_number=lesson_number,
        pattern=PatternInfo(
            pattern_fr=pattern.pattern_fr,
            pattern_en=pattern.pattern_en,
            explanation=pattern.explanation,
            tip=pattern.tip,
        ) if pattern else None,
        words=words,
        lessons_completed=lessons_completed,
        conversations_unlocked=lessons_completed >= LESSONS_FOR_CONVERSATIONS,
        testing_unlocked=lessons_completed >= LESSONS_FOR_TESTING,
    )


@router.post("/respond")
async def respond(
    vocabulary_id: int = Form(...),
    history: str = Form(default="[]"),
    message: str = Form(default=""),
    audio: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The learner sends either text or audio.
    Sophie responds with text + audio (TTS).
    """

    # Fetch the word being practiced
    word = await db.get(Vocabulary, vocabulary_id)
    if not word:
        return {"error": "Word not found"}

    # Fetch the MT pattern for this word's lesson
    pattern = await fetch_lesson_pattern(db, word.level, word.lesson_number)

    # If audio was sent, transcribe it first — that becomes the message
    transcribed = None
    if audio and audio.filename:
        audio_bytes = await audio.read()
        transcribed = await transcribe(audio_bytes, audio.filename or "audio.webm")
        message = transcribed

    parsed_history = json.loads(history)

    # Get or create the user's progress row for this word
    uv = await get_or_create_user_vocabulary(db, current_user.id, vocabulary_id)

    # Fetch user's level for the prompt
    level = await get_user_level(db, current_user.id)

    # Build lesson-progress context so Sophie knows where we are in the lesson
    words_context = await build_words_context(
        db, current_user.id, vocabulary_id, word.level, word.lesson_number
    )

    # Call the LLM — wrapped so a LLM failure returns a graceful message
    try:
        raw_response = await get_lesson_response(
            pattern_fr=pattern.pattern_fr if pattern else "",
            pattern_en=pattern.pattern_en if pattern else "",
            pattern_explanation=pattern.explanation if pattern else "",
            pattern_tip=pattern.tip or "",
            word_fr=word.word_fr,
            word_en=word.word_en,
            example_fr=word.example_sentence_fr,
            words_context=words_context,
            user_message=message,
            history=parsed_history,
            level=level,
        )
    except Exception as e:
        print(f"LLM error in lesson respond: {e}")
        return {
            "message": "Sorry, I had trouble responding — please try again.",
            "audio_base64": None,
            "transcribed": transcribed,
            "attempt_score": None,
            "new_score": uv.score,
            "attempt_count": uv.attempt_count,
            "word_learned": False,
            "lesson_complete": False,
        }

    # Parse Sophie's response — she only returns MESSAGE: now, no ATTEMPT_SCORE
    sophie_message = parse_message(raw_response)

    # Silent scorer — completely separate LLM call, student never sees this
    # Only runs when the student actually typed something (not the hidden "start" trigger)
    attempt_score = None
    if message and message.strip().lower() != "start":
        try:
            attempt_score = await get_score(
                word_fr=word.word_fr,
                word_en=word.word_en,
                pattern_fr=pattern.pattern_fr if pattern else "",
                student_input=message,
            )
        except Exception as e:
            print(f"Scorer error (skipped): {e}")

    # Convert Sophie's reply to speech using mixed-language TTS
    # English parts → American voice, [FR]...[/FR] parts → French voice
    audio_base64 = None
    try:
        tts_bytes = await synthesize_mixed(sophie_message)
        audio_base64 = base64.b64encode(tts_bytes).decode()
    except Exception as e:
        print(f"TTS error (audio skipped): {e}")

    word_learned = False
    lesson_complete = False

    # Update score silently if the scorer returned a number
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
                UserVocabulary.user_id == current_user.id,
                UserVocabulary.vocabulary_id.in_(lesson_word_ids),
                UserVocabulary.status == "learned",
            )
        )
        learned_count = len(learned_result.scalars().all())

        if learned_count == len(lesson_words):
            lesson_result = await db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == current_user.id,
                    LessonProgress.level == word.level,
                    LessonProgress.lesson_number == word.lesson_number,
                )
            )
            lp = lesson_result.scalar_one_or_none()
            if not lp:
                lp = LessonProgress(
                    user_id=current_user.id,
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
        "message": sophie_message,
        "audio_base64": audio_base64,       # Sophie speaks her reply
        "transcribed": transcribed,          # what the mic heard (None if text was used)
        "attempt_score": attempt_score,
        "new_score": uv.score,
        "attempt_count": uv.attempt_count,
        "word_learned": word_learned,
        "lesson_complete": lesson_complete,
    }
