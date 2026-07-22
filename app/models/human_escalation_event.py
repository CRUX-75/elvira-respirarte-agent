from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class HumanEscalationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class HumanEscalationEvent(BaseModel):
    """Privacy-minimized event used for human escalation delivery."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    idempotency_key: str
    patient_id: str | None = None
    inbound_whatsapp_message_id: str
    escalation_action: str
    reason_code: str
    notification_text: str
    status: HumanEscalationStatus = HumanEscalationStatus.PENDING
    attempt_count: int = 0
    retryable: bool = True
    provider_message_id: str | None = None
    last_error_category: str | None = None
    claim_token: str | None = None
    claim_expires_at: datetime | None = None
    created_at: datetime
    last_attempt_at: datetime | None = None
    sent_at: datetime | None = None
