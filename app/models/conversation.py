from datetime import UTC, datetime as DateTime
from enum import StrEnum

from pydantic import BaseModel, Field


class Stage(StrEnum):
    AWAITING_NAME = "awaiting_name"
    AWAITING_SERVICE = "awaiting_service"
    AWAITING_DATETIME = "awaiting_datetime"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    BOOKED = "booked"
    CANCELLED = "cancelled"


class ConversationSlots(BaseModel):
    patient_name: str | None = None
    service: str | None = None
    datetime: DateTime | None = None


class TurnLog(BaseModel):
    role: str
    message: str
    timestamp: DateTime = Field(default_factory=lambda: DateTime.now(UTC))


class ConversationState(BaseModel):
    call_id: str
    clinic_id: str
    caller_number: str | None = None
    stage: Stage = Stage.AWAITING_NAME
    slots: ConversationSlots = Field(default_factory=ConversationSlots)
    created_at: DateTime = Field(default_factory=lambda: DateTime.now(UTC))
    updated_at: DateTime = Field(default_factory=lambda: DateTime.now(UTC))
    turns: list[TurnLog] = Field(default_factory=list)


class ConversationResult(BaseModel):
    state: ConversationState
    reply: str
    ready_to_book: bool = False
