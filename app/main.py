from dataclasses import asdict

from fastapi import FastAPI, Query, HTTPException
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
    capture_appointment_context_from_state,
    should_clear_appointment_context,
)
from app.services.appointment_request_runtime import (
    decide_appointment_request_persistence,
)
from app.services.appointment_request_service import AppointmentRequestService
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



def _build_exact_hour_franja_confirmation_response(franja: str | None) -> str:
    if not franja:
        return (
            "Con gusto. Le cuento que la atención se maneja por franjas horarias "
            "y no es posible garantizar una hora exacta dentro del bloque. "
            "¿Desea que registremos su solicitud para una de las franjas disponibles?"
        )

    readable_franja = franja.replace("–", " a ")

    return (
        "Con gusto. Le cuento que la atención se maneja por franjas horarias "
        "y no es posible garantizar una hora exacta dentro del bloque. "
        f"Para esa hora, la franja correspondiente sería de {readable_franja}. "
        "¿Desea que registremos su solicitud para esa franja?"
    )

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

    appointment_request_decision = decide_appointment_request_persistence(
        state=result,
        telefono=telefono,
        nombre=nombre,
        source_interaction_id=whatsapp_message_id,
    )


    if (
        appointment_request_decision.reason
        == "requires_exact_hour_franja_confirmation"
    ):
        result.respuesta = _build_exact_hour_franja_confirmation_response(
            appointment_request_decision.franja_solicitada
        )

    logged_response = f"[TEST_STATEFUL_WHATSAPP_SENDING_DISABLED] {result.respuesta}"
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

    captured_appointment_context = capture_appointment_context_from_state(result)
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

