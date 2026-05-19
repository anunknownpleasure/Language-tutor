from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class LessonPattern(Base):
    """One row per lesson — holds the MT sentence pattern for that lesson."""
    __tablename__ = "lesson_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String, nullable=False)           # "A1" or "A2"
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10
    pattern_fr: Mapped[str] = mapped_column(String, nullable=False)      # e.g. "Je voudrais..."
    pattern_en: Mapped[str] = mapped_column(String, nullable=False)      # "I would like..."
    explanation: Mapped[str] = mapped_column(Text, nullable=False)       # how the pattern works
    tip: Mapped[str] = mapped_column(Text, nullable=True)                # pronunciation / grammar tip


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    current_level: Mapped[str] = mapped_column(String, default="A1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vocabulary: Mapped[list["UserVocabulary"]] = relationship(back_populates="user")
    lesson_progress: Mapped[list["LessonProgress"]] = relationship(back_populates="user")
    test_results: Mapped[list["TestResult"]] = relationship(back_populates="user")


class Vocabulary(Base):
    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_fr: Mapped[str] = mapped_column(String, nullable=False)
    word_en: Mapped[str] = mapped_column(String, nullable=False)
    example_sentence_fr: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)        # "A1" or "A2"
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10

    user_vocabulary: Mapped[list["UserVocabulary"]] = relationship(back_populates="vocabulary")


class UserVocabulary(Base):
    __tablename__ = "user_vocabulary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    vocabulary_id: Mapped[int] = mapped_column(ForeignKey("vocabulary.id"), nullable=False)
    score: Mapped[float] = mapped_column(Integer, default=0)       # running score 0-100
    attempt_count: Mapped[int] = mapped_column(Integer, default=0) # total attempts made
    status: Mapped[str] = mapped_column(String, default="introduced")  # "introduced" or "learned"
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="vocabulary")
    vocabulary: Mapped["Vocabulary"] = relationship(back_populates="user_vocabulary")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="lesson_progress")


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[int] = mapped_column(Integer, nullable=False)   # 1, 2, or 3
    score: Mapped[int] = mapped_column(Integer, nullable=False)   # 0-100
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="test_results")
