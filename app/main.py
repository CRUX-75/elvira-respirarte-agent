from fastapi import FastAPI, Query, HTTPException
from app.models.message import IncomingMessage
from app.models.whatsapp import WhatsAppPayload
from app.graph.graph import process_message
from app.services.tracing import traced_process_message
from app.services.whatsapp import send_whatsapp_message
from app.repositories.logs import log_interaction, log_ignored, log_error
from app.config import settings

app = FastAPI(
    title="Elvira Respirarte Agent",
    version="0.2.0",
    description="Core conversacional determinístico para Respirarte.",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "elvira-respirarte-agent",
        "version": "0.2.0",
    }


@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge)
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

        await send_whatsapp_message(
            telefono=extracted["telefono"],
            mensaje=result.respuesta,
        )

        log_interaction(
            telefono=extracted["telefono"],
            mensaje=extracted["mensaje"],
            intent=result.intent,
            estado_anterior=message.estado_actual,
            nuevo_estado=result.nuevo_estado,
            respuesta=result.respuesta,
        )

        return {
            "status": "sent",
            "intent": result.intent,
            "respuesta": result.respuesta,
        }

    except Exception as e:
        log_error(telefono=extracted["telefono"], error=str(e))
        raise


@app.post("/test/message")
def test_message(message: IncomingMessage):
    result = traced_process_message(process_message, message)
    return result.model_dump()