from app.models.appointment_request import AppointmentRequest
from app.models.human_review import HumanReviewAction, HumanReviewResult


VALID_ACTIONS = {
    "confirm",
    "request_missing_data",
    "propose_alternative",
    "reschedule",
    "cancel",
    "close",
}


ALLOWED_TRANSITIONS = {
    "confirm": {
        "nueva": "confirmada",
        "pendiente_confirmacion": "confirmada",
        "reagendada": "confirmada",
    },
    "request_missing_data": {
        "nueva": "pendiente_datos",
        "pendiente_confirmacion": "pendiente_datos",
    },
    "propose_alternative": {
        "pendiente_confirmacion": "pendiente_confirmacion",
    },
    "reschedule": {
        "confirmada": "reagendada",
        "pendiente_confirmacion": "reagendada",
    },
    "cancel": {
        "nueva": "cancelada",
        "pendiente_datos": "cancelada",
        "pendiente_confirmacion": "cancelada",
        "confirmada": "cancelada",
        "reagendada": "cancelada",
    },
    "close": {
        "confirmada": "cerrada",
        "reagendada": "cerrada",
        "cancelada": "cerrada",
    },
}


class HumanReviewService:
    def __init__(self, repository):
        self.repository = repository

    def apply_action(self, action: HumanReviewAction) -> HumanReviewResult:
        if action.action not in VALID_ACTIONS:
            return self._error(action, "invalid_action", "Unsupported human review action.")

        missing_error = self._validate_required_fields(action)
        if missing_error:
            return self._error(action, "missing_required_fields", missing_error)

        request = self.repository.get_by_id(action.id_solicitud)
        if request is None:
            return self._error(action, "request_not_found", "Appointment request was not found.")

        previous_status = request.estado_solicitud
        new_status = ALLOWED_TRANSITIONS.get(action.action, {}).get(previous_status)

        if new_status is None:
            return HumanReviewResult(
                success=False,
                id_solicitud=action.id_solicitud,
                previous_status=previous_status,
                new_status=None,
                action=action.action,
                message="Transition is not allowed.",
                error_code="forbidden_transition",
            )

        updates = self._build_request_updates(action, new_status)
        updated_request = request.model_copy(update=updates)
        self.repository.update(updated_request)

        patient_message = self._build_patient_message(action, request)
        should_notify_patient = action.action != "close"

        return HumanReviewResult(
            success=True,
            id_solicitud=action.id_solicitud,
            previous_status=previous_status,
            new_status=new_status,
            action=action.action,
            message="Human review action applied.",
            should_notify_patient=should_notify_patient,
            patient_message=patient_message,
            error_code=None,
        )

    def _validate_required_fields(self, action: HumanReviewAction) -> str | None:
        if action.action == "request_missing_data" and not action.missing_fields:
            return "missing_fields is required for request_missing_data."

        if action.action in {"propose_alternative", "reschedule"}:
            if not action.alternative_date or not action.alternative_franja:
                return "alternative_date and alternative_franja are required."

        return None

    def _build_request_updates(
        self,
        action: HumanReviewAction,
        new_status: str,
    ) -> dict:
        updates = {
            "estado_solicitud": new_status,
            "updated_by": action.actor,
        }

        if action.action == "confirm":
            if action.confirmed_date:
                updates["fecha_confirmada"] = action.confirmed_date
            if action.confirmed_franja:
                updates["franja_confirmada"] = action.confirmed_franja

        if action.action == "request_missing_data":
            missing_fields = ", ".join(action.missing_fields or [])
            updates["observaciones"] = self._append_note(
                action.notes,
                f"Datos faltantes solicitados: {missing_fields}",
            )

        if action.action == "propose_alternative":
            updates["fecha_aceptada"] = action.alternative_date
            updates["franja_aceptada"] = action.alternative_franja
            updates["observaciones"] = self._append_note(
                action.notes,
                action.reason,
            )

        if action.action == "reschedule":
            updates["fecha_confirmada"] = action.alternative_date
            updates["franja_confirmada"] = action.alternative_franja
            updates["motivo_reagendamiento"] = action.reason or action.notes

        if action.action == "cancel":
            updates["motivo_cancelacion"] = action.reason or action.notes

        if action.action == "close" and action.notes:
            updates["observaciones"] = action.notes

        return updates

    def _append_note(self, *parts: str | None) -> str | None:
        cleaned = [part for part in parts if part]
        if not cleaned:
            return None
        return " | ".join(cleaned)

    def _build_patient_message(
        self,
        action: HumanReviewAction,
        request: AppointmentRequest,
    ) -> str | None:
        fecha = (
            action.confirmed_date
            or action.alternative_date
            or request.fecha_solicitada
        )
        franja = (
            action.confirmed_franja
            or action.alternative_franja
            or request.franja_solicitada
        )

        if action.action == "confirm":
            return f"Su cita ha sido confirmada para el {fecha} en la franja {franja}."

        if action.action == "request_missing_data":
            fields = ", ".join(action.missing_fields or [])
            return f"Para continuar con su solicitud, por favor indíquenos: {fields}."

        if action.action == "propose_alternative":
            return (
                f"La Dra. D'Aleman no tiene disponibilidad en la franja solicitada. "
                f"Puede atenderle el {fecha} en la franja {franja}. "
                "¿Desea que dejemos esa opción como solicitud?"
            )

        if action.action == "reschedule":
            return f"Su cita ha sido reagendada para el {fecha} en la franja {franja}."

        if action.action == "cancel":
            return "Su solicitud de cita ha sido cancelada. Si necesita una nueva atención, puede escribirnos nuevamente."

        if action.action == "close":
            return None

        return None

    def _error(
        self,
        action: HumanReviewAction,
        error_code: str,
        message: str,
    ) -> HumanReviewResult:
        return HumanReviewResult(
            success=False,
            id_solicitud=action.id_solicitud,
            previous_status=None,
            new_status=None,
            action=action.action,
            message=message,
            should_notify_patient=False,
            patient_message=None,
            error_code=error_code,
        )
