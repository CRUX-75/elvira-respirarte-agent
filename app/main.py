from dataclasses import asdict

from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.responses import PlainTextResponse

from app.models.message import IncomingMessage
from app.models.whatsapp import WhatsAppPayload
from app.graph.graph import process_message
from app.services.tracing import traced_process_message
from app.services.whatsapp import send_whatsapp_message
from app.repositories.logs import log_interaction, log_ignored, log_error
from app.repositories.patients import (
    clear_patient_appointment_context,
    get_or_create_patient_by_phone,
    update_patient_appointment_context,
    update_patient_state,
    update_patient_last_message,
)
from app.repositories.processed_messages import (
    is_message_processed,
    mark_message_processed,
)
from app.repositories.interactions import save_interaction
from app.repositories.postgres_appointment_request_repository import (
    PostgresAppointmentRequestRepository,
)
from app.services.appointment_context import (
    apply_appointment_context_to_state,
    apply_pending_exact_hour_confirmation_to_state,
    capture_appointment_context_from_state,
    capture_pending_exact_hour_confirmation_context,
    should_clear_appointment_context,
)
from app.services.appointment_request_runtime import (
    decide_appointment_request_persistence,
    is_exact_hour_without_explicit_franja_confirmation,
)
from app.services.appointment_request_service import AppointmentRequestService
from app.models.human_review import HumanReviewAction
from app.services.human_review_service import HumanReviewService
from app.db.session import engine
from app.config import settings
from app.services.readiness import build_ready_report


app = FastAPI(
    title="Elvira Respirarte Agent",
    version="0.2.1",
    description="Core conversacional determinístico para Respirarte.",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "elvira-respirarte-agent",
        "version": "0.2.1",
    }


@app.get("/ready")
def readiness_check():
    return build_ready_report()


@app.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    """
    Meta webhook verification endpoint.

    Meta expects this endpoint to return the raw hub.challenge
    as plain text, not JSON.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=hub_challenge or "", status_code=200)

    raise HTTPException(status_code=403, detail="Verification failed")




def get_internal_admin_token() -> str | None:
    return settings.internal_admin_token


def create_human_review_repository():
    return PostgresAppointmentRequestRepository(engine)


def _validate_internal_admin_token(token: str | None) -> None:
    expected_token = get_internal_admin_token()

    if not expected_token or token != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal admin token",
        )


@app.post("/internal/human-review/actions")
def apply_human_review_action(
    action: HumanReviewAction,
    x_internal_admin_token: str | None = Header(
        default=None,
        alias="X-Internal-Admin-Token",
    ),
):
    _validate_internal_admin_token(x_internal_admin_token)

    repository = create_human_review_repository()
    service = HumanReviewService(repository=repository)

    result = service.apply_action(action)

    return result.model_dump()
@app.post("/webhook")
async def receive_webhook(payload: WhatsAppPayload):
    try:
        extracted = payload.extract_message()
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)

        log_error(
            telefono="unknown",
            error=f"Payload extraction failed: {error_type}: {error_message}",
        )

        print(
            {
                "event": "whatsapp_webhook_payload_extraction_failed",
                "error_type": error_type,
                "error_message": error_message,
                "delivery_status": "not_sent",
                "processed_marked": False,
            }
        )

        return {
            "status": "error",
            "reason": "payload_extraction_failed",
            "delivery_status": "not_sent",
            "processed_marked": False,
        }

    if not extracted:
        log_ignored(reason="no_message", payload_summary=str(payload.object))
        return {"status": "ignored", "reason": "no_message"}

    telefono = extracted.get("telefono")
    mensaje = extracted.get("mensaje")
    nombre = extracted.get("nombre")
    whatsapp_message_id = extracted.get("whatsapp_message_id")
    whatsapp_timestamp = extracted.get("whatsapp_timestamp")

    if not telefono or not mensaje:
        log_ignored(
            reason="missing_required_message_fields",
            payload_summary=str(
                {
                    "has_telefono": bool(telefono),
                    "has_mensaje": bool(mensaje),
                    "whatsapp_message_id": whatsapp_message_id,
                }
            ),
        )

        print(
            {
                "event": "whatsapp_webhook_missing_required_fields",
                "has_telefono": bool(telefono),
                "has_mensaje": bool(mensaje),
                "whatsapp_message_id": whatsapp_message_id,
                "whatsapp_timestamp": whatsapp_timestamp,
                "delivery_status": "not_sent",
                "processed_marked": False,
            }
        )

        return {
            "status": "ignored",
            "reason": "missing_required_message_fields",
            "delivery_status": "not_sent",
            "whatsapp_message_id": whatsapp_message_id,
            "whatsapp_timestamp": whatsapp_timestamp,
            "processed_marked": False,
        }

    # P4-D critical rule:
    # Deduplicate BEFORE calling LangGraph/LLM.
    try:
        already_processed = is_message_processed(whatsapp_message_id)
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)

        log_error(
            telefono=telefono,
            error=f"Deduplication check failed: {error_type}: {error_message}",
        )

        print(
            {
                "event": "whatsapp_webhook_deduplication_failed",
                "telefono": telefono,
                "whatsapp_message_id": whatsapp_message_id,
                "whatsapp_timestamp": whatsapp_timestamp,
                "error_type": error_type,
                "error_message": error_message,
                "delivery_status": "not_sent",
                "processed_marked": False,
            }
        )

        return {
            "status": "error",
            "reason": "deduplication_check_failed",
            "delivery_status": "not_sent",
            "whatsapp_message_id": whatsapp_message_id,
            "whatsapp_timestamp": whatsapp_timestamp,
            "processed_marked": False,
        }

    if already_processed:
        log_ignored(
            reason="duplicate_message",
            payload_summary=str(
                {
                    "telefono": telefono,
                    "whatsapp_message_id": whatsapp_message_id,
                }
            ),
        )

        print(
            {
                "event": "whatsapp_webhook_duplicate_ignored",
                "telefono": telefono,
                "whatsapp_message_id": whatsapp_message_id,
                "whatsapp_timestamp": whatsapp_timestamp,
            }
        )

        return {
            "status": "ignored",
            "reason": "duplicate_message",
            "whatsapp_message_id": whatsapp_message_id,
            "whatsapp_timestamp": whatsapp_timestamp,
        }

    try:
        patient = get_or_create_patient_by_phone(
            telefono=telefono,
            nombre=nombre,
        )

        estado_actual = patient.get("estado_actual") or "ST_INIT"

        message = IncomingMessage(
            telefono=telefono,
            mensaje=mensaje,
            nombre=nombre,
            estado_actual=estado_actual,
            opt_out=bool(patient.get("opt_out", False)),
        )

        result = traced_process_message(process_message, message)

        (
            result,
            appointment_request_decision,
            appointment_request_metadata,
        ) = _apply_appointment_request_runtime(
            result=result,
            patient=patient,
            telefono=telefono,
            nombre=nombre,
            source_interaction_id=whatsapp_message_id,
        )

        if settings.whatsapp_sending_enabled:
            try:
                await send_whatsapp_message(
                    telefono=telefono,
                    mensaje=result.respuesta,
                )

                delivery_status = "sent"
                logged_response = result.respuesta

            except Exception as send_error:
                error_type = type(send_error).__name__
                error_message = str(send_error)

                delivery_status = "send_failed"
                logged_response = f"[WHATSAPP_SEND_FAILED] {result.respuesta}"

                save_interaction(
                    patient_id=str(patient["id"]),
                    telefono=telefono,
                    nombre=nombre,
                    whatsapp_message_id=whatsapp_message_id,
                    whatsapp_timestamp=whatsapp_timestamp,
                    mensaje_usuario=mensaje,
                    respuesta_elvira=logged_response,
                    intent=result.intent,
                    estado_anterior=estado_actual,
                    nuevo_estado=estado_actual,
                    next_action=getattr(result, "next_action", None),
                    state_reason=f"WhatsApp send failed: {error_type}: {error_message}",
                    router_version=getattr(result, "router_version", None),
                    state_machine_version=getattr(result, "state_machine_version", None),
                    kb_used=bool(getattr(result, "kb_used", False)),
                    escalation_required=bool(getattr(result, "escalation_required", False)),
                    delivery_status=delivery_status,
                )

                log_error(
                    telefono=telefono,
                    error=f"WhatsApp send failed: {error_type}: {error_message}",
                )

                print(
                    {
                        "event": "whatsapp_send_failed",
                        "telefono": telefono,
                        "whatsapp_message_id": whatsapp_message_id,
                        "whatsapp_timestamp": whatsapp_timestamp,
                        "error_type": error_type,
                        "error_message": error_message,
                        "delivery_status": delivery_status,
                        "processed_marked": False,
                        "state_updated": False,
                    }
                )

                return {
                    "status": "error",
                    "reason": "whatsapp_send_failed",
                    "delivery_status": delivery_status,
                    "whatsapp_message_id": whatsapp_message_id,
                    "whatsapp_timestamp": whatsapp_timestamp,
                    "processed_marked": False,
                    "state_updated": False,
                }
        else:
            delivery_status = "sending_skipped"
            logged_response = f"[WHATSAPP_SENDING_DISABLED] {result.respuesta}"

        save_interaction(
            patient_id=str(patient["id"]),
            telefono=telefono,
            nombre=nombre,
            whatsapp_message_id=whatsapp_message_id,
            whatsapp_timestamp=whatsapp_timestamp,
            mensaje_usuario=mensaje,
            respuesta_elvira=logged_response,
            intent=result.intent,
            estado_anterior=estado_actual,
            nuevo_estado=result.nuevo_estado,
            next_action=getattr(result, "next_action", None),
            state_reason=getattr(result, "state_reason", None),
            router_version=getattr(result, "router_version", None),
            state_machine_version=getattr(result, "state_machine_version", None),
            kb_used=bool(getattr(result, "kb_used", False)),
            escalation_required=bool(getattr(result, "escalation_required", False)),
            delivery_status=delivery_status,
        )

        update_patient_state(
            patient_id=str(patient["id"]),
            nuevo_estado=result.nuevo_estado,
            opt_out=getattr(result, "opt_out", None),
        )

        update_patient_last_message(patient_id=str(patient["id"]))

        mark_message_processed(
            whatsapp_message_id=whatsapp_message_id,
            telefono=telefono,
        )

        # Keep old console/file logging during P4 for compatibility.
        log_interaction(
            telefono=telefono,
            mensaje=mensaje,
            intent=result.intent,
            estado_anterior=estado_actual,
            nuevo_estado=result.nuevo_estado,
            respuesta=logged_response,
        )

        print(
            {
                "event": "whatsapp_webhook_processed",
                "telefono": telefono,
                "nombre": nombre,
                "mensaje": mensaje,
                "patient_id": str(patient["id"]),
                "whatsapp_message_id": whatsapp_message_id,
                "whatsapp_timestamp": whatsapp_timestamp,
                "intent": result.intent,
                "estado_anterior": estado_actual,
                "nuevo_estado": result.nuevo_estado,
                "delivery_status": delivery_status,
                "whatsapp_sending_enabled": settings.whatsapp_sending_enabled,
            }
        )

        return {
            "status": delivery_status,
            "intent": result.intent,
            "respuesta": result.respuesta,
            "estado_anterior": estado_actual,
            "nuevo_estado": result.nuevo_estado,
            "whatsapp_sending_enabled": settings.whatsapp_sending_enabled,
            "whatsapp_message_id": whatsapp_message_id,
            "whatsapp_timestamp": whatsapp_timestamp,
            "patient_id": str(patient["id"]),
            "appointment_request_decision_reason": appointment_request_decision.reason,
            "appointment_request": appointment_request_metadata,
        }

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)

        log_error(telefono=telefono, error=f"{error_type}: {error_message}")

        print(
            {
                "event": "whatsapp_webhook_processing_failed",
                "telefono": telefono,
                "whatsapp_message_id": whatsapp_message_id,
                "whatsapp_timestamp": whatsapp_timestamp,
                "error_type": error_type,
                "error_message": error_message,
                "delivery_status": "not_sent",
                "processed_marked": False,
            }
        )

        return {
            "status": "error",
            "reason": "processing_failed",
            "delivery_status": "not_sent",
            "whatsapp_message_id": whatsapp_message_id,
            "whatsapp_timestamp": whatsapp_timestamp,
            "processed_marked": False,
        }


@app.post("/test/message")
def test_message(message: IncomingMessage):
    result = traced_process_message(process_message, message)
    return result.model_dump()



def _build_exact_hour_franja_confirmation_response(
    franja: str | None,
    slots: list[str] | None = None,
) -> str:
    if franja:
        slot_fmt = franja.replace("–", " a ")
        return (
            "Con gusto. Le aclaro que las atenciones domiciliarias se manejan por franjas, "
            f"no por una hora exacta garantizada. Para esa hora, la franja disponible es "
            f"de {slot_fmt}. ¿Desea que registre esa franja como preferencia?"
        )
    if slots and len(slots) == 1:
        slot_fmt = slots[0].replace("–", " a ")
        return (
            "Con gusto. Le aclaro que las atenciones domiciliarias se manejan por franjas, "
            f"no por una hora exacta garantizada. Para continuar, la franja disponible es "
            f"de {slot_fmt}. ¿Desea que registre esa franja como preferencia?"
        )
    if slots and len(slots) >= 2:
        s1 = slots[0].replace("–", " a ")
        s2 = slots[1].replace("–", " a ")
        return (
            "Con gusto. Le aclaro que las atenciones domiciliarias se manejan por franjas, "
            f"no por una hora exacta garantizada. Para continuar, elija una de las franjas "
            f"disponibles: de {s1} o de {s2}. ¿Cuál le queda mejor?"
        )
    return (
        "Con gusto. Le aclaro que las atenciones domiciliarias se manejan por franjas, "
        "no por una hora exacta garantizada. Por favor indíquenos su preferencia de franja."
    )

def _force_exact_hour_franja_confirmation_state_guard_response(result):
    result.nuevo_estado = "ST_CITA_FRANJA"
    result.next_action = "ask_confirm_exact_hour_as_slot"
    result.state_reason = "requires_exact_hour_franja_confirmation"
    return result


def _force_unsupported_slot_selection_guard_response(result):
    message = (getattr(result, "mensaje_original", None) or "").lower()
    is_vague_franja_confirmation = (
        "franja" in message
        or "registre" in message
        or "registrar" in message
    )
    is_loose_exact_hour_followup = (
        not is_vague_franja_confirmation
        and any(char.isdigit() for char in message)
        and ("a las" in message or "las " in message)
    )

    if (
        is_loose_exact_hour_followup
        and getattr(result, "nuevo_estado", None) == "ST_CITA_PENDIENTE"
    ):
        slots = list(getattr(result, "slots_candidatos", None) or [])

        if len(slots) == 1:
            slot = slots[0].replace("–", " a ")
            result.respuesta = (
                f"Su solicitud ya quedó registrada para la franja de {slot}. "
                "La hora exacta dentro de la franja será confirmada por la Dra. D’Aleman según disponibilidad."
            )
        else:
            result.respuesta = (
                "Su solicitud ya quedó registrada. "
                "La hora exacta será confirmada por la Dra. D’Aleman según disponibilidad."
            )

        result.nuevo_estado = "ST_CITA_PENDIENTE"
        result.next_action = "none"
        result.state_reason = "registered_request_exact_hour_followup"
        return result

    result.nuevo_estado = "ST_CITA_FRANJA"
    result.next_action = "ask_confirm_exact_hour_as_slot"
    result.state_reason = "unsupported_slot_selection_guard"
    result.respuesta = _build_exact_hour_franja_confirmation_response(
        None,
        slots=getattr(result, "slots_candidatos", None) or [],
    )
    return result


def _force_unavailable_date_guard_response(result):
    """Force safe appointment state/copy when carried date context is unavailable."""
    if not getattr(result, "fecha_solicitada", None):
        return result

    is_unavailable = (
        getattr(result, "is_weekend", False) is True
        or getattr(result, "is_colombia_holiday", False) is True
        or getattr(result, "es_dia_disponible", None) is False
        or not getattr(result, "slots_candidatos", None)
    )

    is_attempting_confirmation = (
        getattr(result, "nuevo_estado", None) == "ST_CITA_PENDIENTE"
        or getattr(result, "next_action", None) == "confirm_appointment_request"
    )

    if not (is_unavailable and is_attempting_confirmation):
        return result

    result.nuevo_estado = "ST_CITA_FECHA"
    result.next_action = "ask_preferred_date"
    result.state_reason = "unavailable_date_guard"

    date_text = getattr(result, "fecha_solicitada_texto", None) or "ese día"
    result.respuesta = (
        f"{date_text.capitalize()} no tenemos atención domiciliaria disponible. "
        "¿Le gustaría indicarme otro día entre semana para revisar las franjas disponibles?"
    )

    return result



def _apply_appointment_request_runtime(
    *,
    result,
    patient: dict,
    telefono: str,
    nombre: str | None,
    source_interaction_id: str | None,
):
    """
    Apply AppointmentRequest runtime logic shared by /webhook and /test/message-stateful.

    This helper does not send WhatsApp messages.
    It only:
    - applies appointment context carryover
    - evaluates AppointmentRequest persistence decision
    - persists AppointmentRequest when deterministic rules allow it
    - captures or clears appointment context
    - adjusts safe patient-facing copy for guarded appointment states
    """
    result = apply_appointment_context_to_state(
        result,
        patient.get("appointment_context"),
    )
    result = apply_pending_exact_hour_confirmation_to_state(
        result,
        patient.get("appointment_context"),
    )

    appointment_request_decision = decide_appointment_request_persistence(
        state=result,
        telefono=telefono,
        nombre=nombre,
        source_interaction_id=source_interaction_id,
    )

    if appointment_request_decision.reason in {
        "skipped_weekend",
        "skipped_colombia_holiday",
        "skipped_unavailable_date",
    }:
        result = _force_unavailable_date_guard_response(result)

    if (
        appointment_request_decision.reason
        == "requires_exact_hour_franja_confirmation"
        or (
            appointment_request_decision.reason == "skipped_wrong_state_or_action"
            and getattr(result, "state_reason", None) == "requires_exact_hour_franja_confirmation"
        )
    ):
        result = _force_exact_hour_franja_confirmation_state_guard_response(result)
        result.respuesta = _build_exact_hour_franja_confirmation_response(
            appointment_request_decision.franja_solicitada,
            slots=getattr(result, "slots_candidatos", None) or [],
        )

    if appointment_request_decision.reason == "skipped_unsupported_slot_selection":
        result = _force_unsupported_slot_selection_guard_response(result)

    appointment_request_metadata = None
    appointment_request_persisted = False

    if appointment_request_decision.should_persist:
        appointment_repository = PostgresAppointmentRequestRepository(engine)
        appointment_service = AppointmentRequestService(
            repository=appointment_repository,
        )
        appointment_request = appointment_service.create_or_reuse_active_request(
            telefono=appointment_request_decision.telefono or telefono,
            nombre_paciente=appointment_request_decision.nombre_paciente or nombre or "",
            servicio_solicitado=appointment_request_decision.servicio_solicitado or "",
            direccion_domicilio=appointment_request_decision.direccion_domicilio or "",
            fecha_solicitada=appointment_request_decision.fecha_solicitada,
            franja_solicitada=appointment_request_decision.franja_solicitada,
            source_interaction_id=appointment_request_decision.source_interaction_id,
            fuente=appointment_request_decision.canal_origen,
            estado_solicitud=appointment_request_decision.estado_solicitud or "nueva",
        )
        appointment_request_persisted = True
        appointment_request_metadata = {
            "id_solicitud": appointment_request.id_solicitud,
            "estado_solicitud": appointment_request.estado_solicitud,
            "source_interaction_id": appointment_request.source_interaction_id,
            "fecha_solicitada": appointment_request.fecha_solicitada,
            "franja_solicitada": appointment_request.franja_solicitada,
        }

    captured_appointment_context = (
        capture_pending_exact_hour_confirmation_context(
            result,
            appointment_request_decision,
        )
        or capture_appointment_context_from_state(result)
    )
    if captured_appointment_context:
        update_patient_appointment_context(
            telefono=telefono,
            appointment_context=captured_appointment_context,
        )

    if should_clear_appointment_context(result, persisted=appointment_request_persisted):
        clear_patient_appointment_context(telefono=telefono)

    return result, appointment_request_decision, appointment_request_metadata


@app.post("/test/message-stateful")
def test_message_stateful(message: IncomingMessage):
    """
    Production dry-run endpoint for multi-turn validation.

    This endpoint:
    - reads the current patient state from PostgreSQL
    - processes the message with that state
    - stores the interaction
    - updates the patient state
    - can persist AppointmentRequest in dry-run mode
    - can carry appointment context between turns
    - never sends a WhatsApp message
    """

    from uuid import uuid4

    telefono = message.telefono
    nombre = message.nombre
    mensaje = message.mensaje

    patient = get_or_create_patient_by_phone(
        telefono=telefono,
        nombre=nombre,
    )

    estado_actual = patient.get("estado_actual") or "ST_INIT"
    opt_out = bool(patient.get("opt_out", False))

    stateful_message = IncomingMessage(
        telefono=telefono,
        nombre=nombre,
        mensaje=mensaje,
        estado_actual=estado_actual,
        opt_out=opt_out,
    )

    result = traced_process_message(process_message, stateful_message)

    whatsapp_message_id = f"test-stateful-{uuid4()}"
    whatsapp_timestamp = None
    delivery_status = "sending_skipped"

    result = apply_appointment_context_to_state(
        result,
        patient.get("appointment_context"),
    )
    result = apply_pending_exact_hour_confirmation_to_state(
        result,
        patient.get("appointment_context"),
    )

    appointment_request_decision = decide_appointment_request_persistence(
        state=result,
        telefono=telefono,
        nombre=nombre,
        source_interaction_id=whatsapp_message_id,
    )

    if appointment_request_decision.reason in {
        "skipped_weekend",
        "skipped_colombia_holiday",
        "skipped_unavailable_date",
    }:
        result = _force_unavailable_date_guard_response(result)

    if (
        appointment_request_decision.reason
        == "requires_exact_hour_franja_confirmation"
        or (
            appointment_request_decision.reason == "skipped_wrong_state_or_action"
            and getattr(result, "state_reason", None) == "requires_exact_hour_franja_confirmation"
        )
    ):
        result = _force_exact_hour_franja_confirmation_state_guard_response(result)
        result.respuesta = _build_exact_hour_franja_confirmation_response(
            appointment_request_decision.franja_solicitada,
            slots=getattr(result, "slots_candidatos", None) or [],
        )

    if appointment_request_decision.reason == "skipped_unsupported_slot_selection":
        result = _force_unsupported_slot_selection_guard_response(result)

    appointment_request_metadata = None
    appointment_request_persisted = False

    if appointment_request_decision.should_persist:
        appointment_repository = PostgresAppointmentRequestRepository(engine)
        appointment_service = AppointmentRequestService(
            repository=appointment_repository,
        )
        appointment_request = appointment_service.create_or_reuse_active_request(
            telefono=appointment_request_decision.telefono or telefono,
            nombre_paciente=appointment_request_decision.nombre_paciente or nombre or "",
            servicio_solicitado=appointment_request_decision.servicio_solicitado or "",
            direccion_domicilio=appointment_request_decision.direccion_domicilio or "",
            fecha_solicitada=appointment_request_decision.fecha_solicitada,
            franja_solicitada=appointment_request_decision.franja_solicitada,
            source_interaction_id=appointment_request_decision.source_interaction_id,
            fuente=appointment_request_decision.canal_origen,
            estado_solicitud=appointment_request_decision.estado_solicitud or "nueva",
        )
        appointment_request_persisted = True
        appointment_request_metadata = {
            "id_solicitud": appointment_request.id_solicitud,
            "estado_solicitud": appointment_request.estado_solicitud,
            "source_interaction_id": appointment_request.source_interaction_id,
            "fecha_solicitada": appointment_request.fecha_solicitada,
            "franja_solicitada": appointment_request.franja_solicitada,
        }

    logged_response = f"[TEST_STATEFUL_WHATSAPP_SENDING_DISABLED] {result.respuesta}"

    save_interaction(
        patient_id=str(patient["id"]),
        telefono=telefono,
        nombre=nombre,
        whatsapp_message_id=whatsapp_message_id,
        whatsapp_timestamp=whatsapp_timestamp,
        mensaje_usuario=mensaje,
        respuesta_elvira=logged_response,
        intent=result.intent,
        estado_anterior=estado_actual,
        nuevo_estado=result.nuevo_estado,
        next_action=getattr(result, "next_action", None),
        state_reason=getattr(result, "state_reason", None),
        router_version=getattr(result, "router_version", None),
        state_machine_version=getattr(result, "state_machine_version", None),
        kb_used=bool(getattr(result, "kb_used", False)),
        escalation_required=bool(getattr(result, "escalation_required", False)),
        delivery_status=delivery_status,
    )

    update_patient_state(
        patient_id=str(patient["id"]),
        nuevo_estado=result.nuevo_estado,
        opt_out=getattr(result, "opt_out", None),
    )

    update_patient_last_message(patient_id=str(patient["id"]))

    captured_appointment_context = (
        capture_pending_exact_hour_confirmation_context(
            result,
            appointment_request_decision,
        )
        or capture_appointment_context_from_state(result)
    )
    if captured_appointment_context:
        update_patient_appointment_context(
            telefono=telefono,
            appointment_context=captured_appointment_context,
        )

    if should_clear_appointment_context(result, persisted=appointment_request_persisted):
        clear_patient_appointment_context(telefono=telefono)

    response = result.model_dump()
    response["test_endpoint"] = "message-stateful"
    response["delivery_status"] = delivery_status
    response["whatsapp_message_id"] = whatsapp_message_id
    response["persisted_state"] = result.nuevo_estado
    response["patient_id"] = str(patient["id"])
    response["appointment_request_decision"] = asdict(appointment_request_decision)
    response["appointment_request"] = appointment_request_metadata

    return response

