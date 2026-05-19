import random
import json
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from llm import get_raw_response
from models import LessonProgress, TestResult, UserVocabulary, Vocabulary, User
from pipeline import run_pipeline

router = APIRouter(prefix="/api/test", tags=["testing"])

TEST_USER_ID = 1
LESSONS_TO_UNLOCK_TESTING = 1   # lowered for development — raise to 10 for production
PASS_THRESHOLD = 70             # score needed to pass each stage


# ── Helper: fetch learned vocabulary for this user ─────────────────────────
# We use this in all three stages — the test is always based on what they know

async def get_learned_words(db: AsyncSession, user_id: int) -> list[Vocabulary]:
    result = await db.execute(
        select(Vocabulary)
        .join(UserVocabulary, UserVocabulary.vocabulary_id == Vocabulary.id)
        .where(
            UserVocabulary.user_id == user_id,
            UserVocabulary.status == "learned",
        )
    )
    learned = result.scalars().all()

    # Fallback: if nothing learned yet, use A1 lesson 1 words so testing is always usable
    if not learned:
        result = await db.execute(
            select(Vocabulary).where(
                Vocabulary.level == "A1",
                Vocabulary.lesson_number == 1,
            )
        )
        learned = result.scalars().all()

    return learned


# ── Helper: get user's current level ──────────────────────────────────────

async def get_user_level(db: AsyncSession, user_id: int) -> str:
    user = await db.get(User, user_id)
    return user.current_level if user else "A1"


# ── Helper: check if testing is unlocked ──────────────────────────────────

async def is_testing_unlocked(db: AsyncSession, user_id: int, level: str) -> bool:
    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.level == level,
            LessonProgress.completed == True,
        )
    )
    completed_count = len(result.scalars().all())
    return completed_count >= LESSONS_TO_UNLOCK_TESTING


# ── GET /api/test ──────────────────────────────────────────────────────────
# Returns the questions for the requested stage
# Stage 1: multiple choice questions
# Stage 2: translation questions (just the English words to translate)
# Stage 3: a scenario to have a conversation in (A2 only)

@router.get("")
async def get_test(stage: int = 1, db: AsyncSession = Depends(get_db)):
    """
    Returns test questions for the given stage.
    Stage is passed as a query parameter: /api/test?stage=1
    """

    level = await get_user_level(db, TEST_USER_ID)
    unlocked = await is_testing_unlocked(db, TEST_USER_ID, level)

    if not unlocked:
        return {
            "unlocked": False,
            "message": f"Complete {LESSONS_TO_UNLOCK_TESTING} lesson(s) to unlock testing."
        }

    # Stage 3 is only available from A2
    if stage == 3 and level == "A1":
        return {"error": "Stage 3 is only available from A2 level."}

    words = await get_learned_words(db, TEST_USER_ID)

    # Pick up to 10 words randomly for the test
    # random.sample picks N unique items from a list without repeating
    test_words = random.sample(words, min(10, len(words)))

    if stage == 1:
        # Multiple choice: for each word, show the English and give 4 French options
        # One correct answer + 3 random wrong answers from other words
        questions = []
        all_french = [w.word_fr for w in words]

        for word in test_words:
            # Get 3 wrong options (words that are NOT the correct answer)
            wrong_options = [w for w in all_french if w != word.word_fr]
            # Pick 3 random wrong ones
            distractors = random.sample(wrong_options, min(3, len(wrong_options)))
            # Combine correct + wrong, shuffle so correct isn't always first
            options = [word.word_fr] + distractors
            random.shuffle(options)

            questions.append({
                "vocabulary_id": word.id,
                "english": word.word_en,
                "options": options,
                "correct": word.word_fr,   # we send this to the browser for self-grading
            })

        return {"stage": 1, "questions": questions, "unlocked": True}

    elif stage == 2:
        # Translation: show English word, user types French
        questions = [
            {
                "vocabulary_id": word.id,
                "english": word.word_en,
                "example_sentence": word.example_sentence_fr,
            }
            for word in test_words
        ]
        return {"stage": 2, "questions": questions, "unlocked": True}

    elif stage == 3:
        # Conversation: generate one scenario using learned words
        word_list = ", ".join([f"{w.word_fr} ({w.word_en})" for w in test_words])
        raw = await get_raw_response(
            system_prompt="""Generate exactly 1 French conversation scenario as JSON.
Format: {"title": "...", "description": "...", "sophie_role": "...", "goal": "...", "opening_line": "..."}
opening_line must be in French. All other fields in English. Return JSON only.""",
            user_message=f"Learner knows: {word_list}",
            history=[],
            temperature=0.7,
        )
        try:
            scenario = json.loads(raw)
        except json.JSONDecodeError:
            scenario = {
                "title": "At the café",
                "description": "Order something and pay the bill.",
                "sophie_role": "You are a café waiter.",
                "goal": "Complete the order using your French vocabulary.",
                "opening_line": "Bonjour ! Qu'est-ce que je vous sers ?"
            }
        return {"stage": 3, "scenario": scenario, "unlocked": True}


# ── POST /api/test/submit ──────────────────────────────────────────────────
# Receives answers, grades them, saves result to DB

@router.post("/submit")
async def submit_test(
    stage: int,
    answers: str = Form(...),   # JSON string of answers
    db: AsyncSession = Depends(get_db),
):
    """
    Grades the submitted answers for the given stage.
    Stage 1: answers = [{"vocabulary_id": 1, "selected": "bonjour"}]
    Stage 2: answers = [{"vocabulary_id": 1, "typed": "bonjour"}]
    """

    level = await get_user_level(db, TEST_USER_ID)
    parsed_answers = json.loads(answers)
    score = 0

    if stage == 1:
        # Auto-grade: compare selected answer against correct word in DB
        correct_count = 0
        for answer in parsed_answers:
            word = await db.get(Vocabulary, answer["vocabulary_id"])
            if word and answer.get("selected") == word.word_fr:
                correct_count += 1
        # Score = percentage of correct answers
        score = int((correct_count / len(parsed_answers)) * 100) if parsed_answers else 0

    elif stage == 2:
        # LLM grades each translation
        # We ask DeepSeek to score each typed answer against the correct French word
        scores = []
        for answer in parsed_answers:
            word = await db.get(Vocabulary, answer["vocabulary_id"])
            if not word:
                continue

            raw = await get_raw_response(
                system_prompt="""You are grading a French translation exercise.
The learner was asked to translate an English word into French.
Score their answer from 0 to 100:
  90-100: correct French word or very close acceptable variant
  60-89: mostly correct but spelling error or minor mistake
  30-59: partially correct or related word
  0-29: wrong or blank

Respond with a single number only. No explanation.""",
                user_message=f"English word: {word.word_en}\nCorrect French: {word.word_fr}\nLearner typed: {answer.get('typed', '')}",
                history=[],
                temperature=0.1,   # very low — we want consistent grading, not creative
                max_tokens=10,
            )
            try:
                scores.append(int(raw.strip()))
            except ValueError:
                scores.append(0)

        score = int(sum(scores) / len(scores)) if scores else 0

    # Determine pass/fail
    passed = score >= PASS_THRESHOLD

    # Save result to DB
    result = TestResult(
        user_id=TEST_USER_ID,
        level=level,
        stage=stage,
        score=score,
        passed=passed,
        completed_at=datetime.utcnow(),
    )
    db.add(result)

    # If all required stages passed, advance the user's level
    if passed:
        await check_and_advance_level(db, TEST_USER_ID, level, stage)

    await db.commit()

    return {
        "stage": stage,
        "score": score,
        "passed": passed,
        "pass_threshold": PASS_THRESHOLD,
    }


# ── GET /api/test/status ───────────────────────────────────────────────────
# Returns which stages are completed and whether the user passed overall

@router.get("/status")
async def get_test_status(db: AsyncSession = Depends(get_db)):
    """Returns the user's test progress for their current level."""

    level = await get_user_level(db, TEST_USER_ID)
    unlocked = await is_testing_unlocked(db, TEST_USER_ID, level)

    # Fetch all test results for this user at this level
    result = await db.execute(
        select(TestResult).where(
            TestResult.user_id == TEST_USER_ID,
            TestResult.level == level,
        ).order_by(TestResult.completed_at)
    )
    results = result.scalars().all()

    # Build a summary per stage (take the latest attempt for each stage)
    stages = {}
    for r in results:
        stages[r.stage] = {"score": r.score, "passed": r.passed}

    # Required stages depend on level
    required_stages = [1, 2] if level == "A1" else [1, 2, 3]
    all_passed = all(stages.get(s, {}).get("passed", False) for s in required_stages)

    return {
        "level": level,
        "unlocked": unlocked,
        "stages": stages,
        "required_stages": required_stages,
        "all_passed": all_passed,
    }


# ── Helper: advance level if all stages passed ─────────────────────────────

async def check_and_advance_level(
    db: AsyncSession, user_id: int, current_level: str, just_passed_stage: int
):
    """
    Check if all required stages are now passed.
    If yes, advance the user to the next level.
    """

    required_stages = [1, 2] if current_level == "A1" else [1, 2, 3]

    # Fetch latest pass/fail for each required stage
    all_passed = True
    for stage in required_stages:
        if stage == just_passed_stage:
            continue   # we just passed this one, no need to check DB
        result = await db.execute(
            select(TestResult).where(
                TestResult.user_id == user_id,
                TestResult.level == current_level,
                TestResult.stage == stage,
                TestResult.passed == True,
            )
        )
        if not result.scalar_one_or_none():
            all_passed = False
            break

    if all_passed:
        user = await db.get(User, user_id)
        if user and current_level == "A1":
            user.current_level = "A2"
            print(f"User {user_id} advanced to A2!")
