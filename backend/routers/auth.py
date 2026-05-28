from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_token, hash_password, verify_password
from database import get_db
from models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new account.
    Hashes the password before storing — never saves the plain text.
    Returns a JWT token so the user is immediately logged in.
    """
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        current_level="A1",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"token": create_token(user.id), "email": user.email}


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Log in with email + password.
    Returns a JWT token on success, 401 on bad credentials.
    We give the same vague error for wrong email OR wrong password —
    this prevents attackers from probing which emails exist.
    """
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"token": create_token(user.id), "email": user.email}
