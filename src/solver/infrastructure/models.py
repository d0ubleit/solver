"""SQLAlchemy ORM models for the Solver application."""

import uuid
from datetime import datetime, timezone as tz

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship

from solver.infrastructure.database import Base


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(tz.utc)


def _new_uuid() -> str:
    """Generate a new UUID as a string."""
    return str(uuid.uuid4())


class UserModel(Base):
    """SQLAlchemy model for users."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), default="")
    timezone = Column(String(100), default="UTC")
    proactive_level = Column(String(50), default="moderate")
    proactive_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    problems = relationship("ProblemModel", back_populates="user", lazy="selectin")


class ProblemModel(Base):
    """SQLAlchemy model for problems."""

    __tablename__ = "problems"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    status = Column(String(50), default="draft", index=True)
    priority = Column(String(50), default="medium")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("UserModel", back_populates="problems")
    steps = relationship(
        "StepModel",
        back_populates="problem",
        lazy="selectin",
        order_by="StepModel.step_order",
        cascade="all, delete-orphan",
    )
    conversation_context = relationship(
        "ConversationContextModel",
        back_populates="problem",
        uselist=False,
        cascade="all, delete-orphan",
    )


class StepModel(Base):
    """SQLAlchemy model for solution steps."""

    __tablename__ = "solution_steps"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    problem_id = Column(
        String(36), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_order = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    ai_suggestion = Column(Text, default="")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    problem = relationship("ProblemModel", back_populates="steps")


class ConversationContextModel(Base):
    """SQLAlchemy model for conversation contexts."""

    __tablename__ = "conversation_contexts"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    problem_id = Column(
        String(36),
        ForeignKey("problems.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    messages = Column(JSON, default=list)
    summary = Column(Text, default="")
    tokens_used = Column(Integer, default=0)
    last_activity_at = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    problem = relationship("ProblemModel", back_populates="conversation_context")


class ProactiveTriggerModel(Base):
    """SQLAlchemy model for proactive triggers/scheduled notifications."""

    __tablename__ = "proactive_triggers"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    problem_id = Column(String(36), ForeignKey("problems.id"), nullable=False, index=True)
    trigger_type = Column(String(50), nullable=False)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    fired_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=_utcnow)
