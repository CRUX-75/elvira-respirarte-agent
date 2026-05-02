import logging
from datetime import datetime

logger = logging.getLogger("elvira")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def log_interaction(
    telefono: str,
    mensaje: str,
    intent: str,
    estado_anterior: str,
    nuevo_estado: str,
    respuesta: str,
) -> None:
    logger.info(
        "INTERACTION | telefono=%s | intent=%s | estado=%s->%s | msg=%r | resp=%r",
        telefono,
        intent,
        estado_anterior,
        nuevo_estado,
        mensaje,
        respuesta,
    )


def log_ignored(reason: str, payload_summary: str = "") -> None:
    logger.info("IGNORED | reason=%s | payload=%s", reason, payload_summary)


def log_error(telefono: str, error: str) -> None:
    logger.error("ERROR | telefono=%s | error=%s", telefono, error)