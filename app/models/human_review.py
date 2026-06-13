from pydantic import BaseModel
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
