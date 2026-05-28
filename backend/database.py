import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# In production (Railway), DATABASE_URL is set as an environment variable
# pointing to their managed PostgreSQL.
# Locally, it falls back to SQLite so you don't need Postgres installed.
_DATABASE_URL = os.environ.get("DATABASE_URL")

if _DATABASE_URL:
    # Railway provides postgres:// URLs; SQLAlchemy async needs postgresql+asyncpg://
    DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    # Local development — use SQLite
    DB_DIR = Path(__file__).parent.parent / "data"
    DB_DIR.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR / 'tutor.db'}"

# The engine is the actual connection to the database.
# echo=True logs all SQL — turn off in production to keep logs clean.
IS_PRODUCTION = bool(os.environ.get("DATABASE_URL"))
engine = create_async_engine(DATABASE_URL, echo=not IS_PRODUCTION)

# A session is a unit of work — you open one, do reads/writes, then close it
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# All models (tables) will inherit from this base class
class Base(DeclarativeBase):
    pass


# Dependency — FastAPI routes call this to get a DB session
# The `yield` means: give the session to the route, wait for it to finish,
# then close the session automatically (even if there's an error)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
