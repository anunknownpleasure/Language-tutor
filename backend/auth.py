"""
auth.py — two responsibilities:
  1. Passwords: hash on register, verify on login (bcrypt via passlib)
  2. Tokens:    create on login, decode on every protected request (JWT via python-jose)
"""
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import User

# ── Password hashing ──────────────────────────────────────────────────────
# CryptContext wraps bcrypt — bcrypt is intentionally slow to resist brute force

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Turn a plain-text password into a bcrypt hash for storage."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a typed password against the stored hash. Returns True/False."""
    return pwd_context.verify(plain, hashed)


# ── JWT tokens ────────────────────────────────────────────────────────────
# A JWT is a signed JSON payload. We put the user's ID inside and sign it
# with SECRET_KEY. Anyone can read the payload, but only we can produce a
# valid signature — so we can trust what's inside.

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30


def create_token(user_id: int) -> str:
    """Create a signed JWT containing the user ID and an expiry timestamp."""
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    """
    Verify a JWT's signature and return the user ID inside it.
    Raises HTTP 401 if the token is invalid, expired, or tampered with.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token — please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependency ────────────────────────────────────────────────────
# get_current_user is declared as a Depends() in any route that requires auth.
# FastAPI calls it automatically, extracts the token from the Authorization
# header, verifies it, loads the User from the DB, and injects it into the
# route function. If anything fails, a 401 is returned before the route runs.

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency — validates the JWT and returns the logged-in User."""
    user_id = decode_token(credentials.credentials)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
