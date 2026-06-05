import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from pipeline import run_pipeline
from routers import auth, lessons, conversations, testing
from database import Base, engine, AsyncSessionLocal
from models import Vocabulary, LessonPattern

# Works both locally (../frontend) and inside Docker (/app/frontend)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


async def _seed_if_empty(session):
    """Seed vocabulary and lesson patterns only if the table is empty."""
    # Import seed data from seed.py without running the full destructive seed
    from seed import VOCABULARY, LESSON_PATTERNS

    result = await session.execute(select(Vocabulary).limit(1))
    if result.scalar_one_or_none() is not None:
        print("Seed: vocabulary already present — skipping")
        return

    print("Seed: vocabulary table is empty — seeding now...")
    for level, lesson_num, pattern_fr, pattern_en, explanation, tip in LESSON_PATTERNS:
        session.add(LessonPattern(
            level=level,
            lesson_number=lesson_num,
            pattern_fr=pattern_fr,
            pattern_en=pattern_en,
            explanation=explanation,
            tip=tip,
        ))

    for word_fr, word_en, example, level, lesson_num in VOCABULARY:
        session.add(Vocabulary(
            word_fr=word_fr,
            word_en=word_en,
            example_sentence_fr=example,
            level=level,
            lesson_number=lesson_num,
        ))

    await session.commit()
    print(f"Seed: done — {len(VOCABULARY)} words, {len(LESSON_PATTERNS)} patterns")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts up, before it accepts any requests."""
    # Step 1 — Create all tables if they don't already exist
    # create_all is safe to call multiple times — it skips tables that are already there
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("DB: tables ready")

    # Step 2 — Seed vocabulary if the database is brand new (empty)
    async with AsyncSessionLocal() as session:
        await _seed_if_empty(session)

    yield   # Everything above runs on startup; everything below would run on shutdown


app = FastAPI(title="French Tutor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(lessons.router)
app.include_router(conversations.router)
app.include_router(testing.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(
    audio: UploadFile = File(...),
    history: str = Form(default="[]"),
):
    audio_bytes = await audio.read()
    conversation_history = json.loads(history)

    result = await run_pipeline(
        audio_bytes=audio_bytes,
        conversation_history=conversation_history,
        audio_filename=audio.filename or "audio.webm",
    )
    return result


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
