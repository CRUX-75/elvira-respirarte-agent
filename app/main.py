from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse

from app.models.message import IncomingMessage
from app.models.whatsapp import WhatsAppPayload
from app.graph.graph import process_message
from app.services.tracing import traced_process_message
from app.services.whatsapp import send_whatsapp_message
from app.repositories.logs import log_interaction, log_ignored, log_error
from app.repositories.patients import (
    get_or_create_patient_by_phone,
    update_patient_state,
    update_patient_last_message,
)
from app.repositories.processed_messages import (
    is_message_processed,
    mark_message_processed,
)
from app.repositories.interactions import save_interaction
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