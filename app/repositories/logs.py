import logging
from datetime import datetime

from app.services.log_privacy import mask_phone, sanitize_log_text


logger = logging.getLogger("elvira")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# Prevent transport clients from exposing complete request URLs,
# including temporary WhatsApp media download URLs and query parameters.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def log_interaction(
    telefono: str,
    mensaje: str | None,
    intent: str,
    estado_anterior: str,
    nuevo_estado: str,
    respuesta: str | None,
) -> None:
    logger.info(
        "INTERACTION | telefono=%s | intent=%s | estado=%s->%s "
        "| msg_present=%s | resp_present=%s",
        mask_phone(telefono),
        intent,
        estado_anterior,
        nuevo_estado,
        bool(mensaje),
        bool(respuesta),
    )


def log_ignored(reason: str, payload_summary: str = "") -> None:
    logger.info(
        "IGNORED | reason=%s | payload=%s",
        reason,
        sanitize_log_text(payload_summary),
    )


def log_error(telefono: str, error: str) -> None:
    logger.error(
        "ERROR | telefono=%s | error=%s",
        mask_phone(telefono),
        sanitize_log_text(error),
    )
