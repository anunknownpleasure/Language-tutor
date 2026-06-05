import json
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pipeline import run_pipeline
from routers import auth, lessons, conversations, testing

# Works both locally (../frontend) and inside Docker (/app/frontend)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="French Tutor API")

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
