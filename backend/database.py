from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Always resolve to Language-tutor/data/tutor.db regardless of where Python is run from
DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR / 'tutor.db'}"

# The engine is the actual connection to the database
# echo=True prints all SQL queries to the terminal — helpful for learning
engine = create_async_engine(DATABASE_URL, echo=True)

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
