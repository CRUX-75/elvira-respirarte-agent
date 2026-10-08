from datetime import date
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, model_validator
from typing import Literal


HumanReviewActionType = Literal[
    "confirm",
    "request_missing_data",
    "propose_alternative",
    "reschedule",
    "cancel",
    "close",
]


class HumanReviewAction(BaseModel):
    id_solicitud: str
    action: str
    actor: str
    notes: str | None = None
    confirmed_date: str | None = None
    confirmed_franja: str | None = None
    alternative_date: str | None = None
    alternative_franja: str | None = None
    missing_fields: list[str] | None = None
    reason: str | None = None


class HumanReviewResult(BaseModel):
    success: bool
    id_solicitud: str
    previous_status: str | None = None
    new_status: str | None = None
    action: str
    message: str
    should_notify_patient: bool = False
    patient_message: str | None = None
    error_code: str | None = None


class HumanReviewCommand(HumanReviewAction):
    decision_id: UUID | None = None
    expected_updated_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_decision_contract(self):
        if (self.decision_id is None) != (self.expected_updated_at is None):
            raise ValueError("decision_id and expected_updated_at are required together")

        if self.decision_id is not None:
            if not self.actor.strip() or not self.id_solicitud.strip():
                raise ValueError("actor and id_solicitud must not be empty")

            if self.action == "confirm":
                if not self.confirmed_date or not (self.confirmed_franja or '').strip():
                    raise ValueError("confirmed_date and confirmed_franja are required")

            for value in (self.confirmed_date, self.alternative_date):
                if value is not None and date.fromisoformat(value).isoformat() != value:
                    raise ValueError("decision dates must use YYYY-MM-DD")

        return self
