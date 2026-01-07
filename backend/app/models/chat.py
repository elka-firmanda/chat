"""Chat-related Pydantic models."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    description: str
    status: PlanStepStatus = PlanStepStatus.PENDING
    result: str | None = None
    agent: str | None = None


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str
    session_id: str | None = None
    deep_search: bool = False


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    session_id: str
    message: Message
    plan: list[PlanStep] | None = None
