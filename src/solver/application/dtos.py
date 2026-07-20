"""Data Transfer Objects for the application layer."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateProblemDTO(BaseModel):
    """DTO for creating a new problem."""

    title: str = Field(..., min_length=1, max_length=500, description="Problem title")
    description: str = Field(default="", max_length=5000, description="Problem description")


class ProblemResponseDTO(BaseModel):
    """DTO for problem responses to the presentation layer."""

    id: UUID
    user_id: UUID
    title: str
    description: str
    status: str
    priority: str
    total_steps: int
    completed_steps: int
    progress_percentage: float
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    steps: list["StepResponseDTO"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class StepResponseDTO(BaseModel):
    """DTO for step responses."""

    id: UUID
    step_order: int
    description: str
    status: str
    ai_suggestion: str
    completed_at: datetime | None = None
    created_at: datetime


class AIAnalysisRequestDTO(BaseModel):
    """DTO for requesting AI analysis of a problem."""

    problem_title: str
    problem_description: str
    conversation_history: list[dict[str, str]] = Field(default_factory=list)


class AIAnalysisResponseDTO(BaseModel):
    """DTO for AI analysis results."""

    analysis: str = Field(..., description="AI's analysis of the problem")
    steps: list[str] = Field(
        default_factory=list,
        description="Recommended action steps",
    )
    tokens_used: int = Field(default=0, description="Number of tokens consumed")


class UpdateStepDTO(BaseModel):
    """DTO for updating a step's status."""

    status: str = Field(..., description="New step status")


class UserResponseDTO(BaseModel):
    """DTO for user responses."""

    id: UUID
    telegram_id: int
    username: str
    timezone: str
    proactive_level: str
    proactive_enabled: bool
    created_at: datetime
