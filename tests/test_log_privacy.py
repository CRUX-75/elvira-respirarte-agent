import ast
import logging

from app.repositories import logs
from app.services.log_privacy import (
    mask_phone,
    print_safe_event,
    pseudonymize_identifier,
    sanitize_log_payload,
    sanitize_log_text,
)


def test_phone_is_masked_preserving_only_last_four_digits():
    masked = mask_phone("4915215952007")

    assert masked.endswith("2007")
    assert "4915215952007" not in masked


def test_identifier_is_replaced_by_stable_hash():
    assert pseudonymize_identifier(
        "wamid.voice.obs.001"
    ) == "sha256:88654754679e"


def test_structured_payload_redacts_personal_identifiers():
    sanitized = sanitize_log_payload(
        {
            "event": "whatsapp_webhook_processed",
            "telefono": "4915215952007",
            "nombre": "Paciente Control",
            "patient_id": "patient-123",
            "whatsapp_message_id": "wamid.voice.obs.001",
            "delivery_status": "sent",
        }
    )

    assert sanitized["telefono"].endswith("2007")
    assert sanitized["nombre"] == "[redacted]"
    assert sanitized["patient_id"] == "sha256:1985450135cd"
    assert sanitized["whatsapp_message_id"] == "sha256:88654754679e"
    assert sanitized["delivery_status"] == "sent"


def test_unstructured_summary_does_not_keep_raw_phone_or_wamid():
    raw = (
        "{'telefono': '4915215952007', "
        "'whatsapp_message_id': 'wamid.voice.obs.001'}"
    )

    sanitized = sanitize_log_text(raw)

    assert "4915215952007" not in sanitized
    assert "wamid.voice.obs.001" not in sanitized
    assert "2007" in sanitized
    assert "sha256:88654754679e" in sanitized


def test_safe_print_sanitizes_before_writing(capsys):
    print_safe_event(
        {
            "event": "voice_reply_sent",
            "telefono": "4915215952007",
            "whatsapp_message_id": "wamid.voice.obs.001",
        }
    )

    event = ast.literal_eval(capsys.readouterr().out.strip())

    assert event["telefono"].endswith("2007")
    assert event["whatsapp_message_id"] == "sha256:88654754679e"


def test_http_transport_loggers_are_not_in_info_mode():
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_exception_text_redacts_complete_url_and_query_parameters():
    raw = (
        "Client error '403 Forbidden' for url "
        "'https://lookaside.fbsbx.com/whatsapp_business/attachments/"
        "?mid=123&hash=secret-token'"
    )

    sanitized = sanitize_log_text(raw)

    assert "https://" not in sanitized
    assert "lookaside.fbsbx.com" not in sanitized
    assert "hash=secret-token" not in sanitized
    assert "[redacted_url]" in sanitized
