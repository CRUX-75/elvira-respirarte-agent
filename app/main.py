from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import PlainTextResponse

from app.models.message import IncomingMessage
from app.models.whatsapp import WhatsAppPayload
from app.graph.graph import process_message
from app.services.tracing import traced_process_message
from app.services.whatsapp import send_whatsapp_message
from app.repositories.logs import log_interaction, log_ignored, log_error
from app.config import settings


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
    extracted = payload.extract_message()

    if not extracted:
        log_ignored(reason="no_message", payload_summary=str(payload.object))
        return {"status": "ignored"}

    message = IncomingMessage(
        telefono=extracted["telefono"],
        mensaje=extracted["mensaje"],
        nombre=extracted.get("nombre"),
        estado_actual="ST_INIT",
        opt_out=False,
    )

    try:
        result = traced_process_message(process_message, message)

        if settings.whatsapp_sending_enabled:
            await send_whatsapp_message(
                telefono=extracted["telefono"],
                mensaje=result.respuesta,
            )

            delivery_status = "sent"
            logged_response = result.respuesta
        else:
            delivery_status = "sending_skipped"
            logged_response = f"[WHATSAPP_SENDING_DISABLED] {result.respuesta}"

        log_interaction(
            telefono=extracted["telefono"],
            mensaje=extracted["mensaje"],
            intent=result.intent,
            estado_anterior=message.estado_actual,
            nuevo_estado=result.nuevo_estado,
            respuesta=logged_response,
        )

        print(
            {
                "event": "whatsapp_webhook_processed",
                "telefono": extracted["telefono"],
                "nombre": extracted.get("nombre"),
                "mensaje": extracted["mensaje"],
                "whatsapp_message_id": extracted.get("whatsapp_message_id"),
                "whatsapp_timestamp": extracted.get("whatsapp_timestamp"),
                "intent": result.intent,
                "estado_anterior": message.estado_actual,
                "nuevo_estado": result.nuevo_estado,
                "delivery_status": delivery_status,
                "whatsapp_sending_enabled": settings.whatsapp_sending_enabled,
            }
        )

        return {
            "status": delivery_status,
            "intent": result.intent,
            "respuesta": result.respuesta,
            "whatsapp_sending_enabled": settings.whatsapp_sending_enabled,
            "whatsapp_message_id": extracted.get("whatsapp_message_id"),
            "whatsapp_timestamp": extracted.get("whatsapp_timestamp"),
        }

    except Exception as e:
        log_error(telefono=extracted["telefono"], error=str(e))
        raise


@app.post("/test/message")
def test_message(message: IncomingMessage):
    result = traced_process_message(process_message, message)
    return result.model_dump()