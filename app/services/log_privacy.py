from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any


_PHONE_KEYS = {
    "telefono",
    "phone",
    "phone_number",
}

_REDACTED_KEYS = {
    "nombre",
}

_HASHED_IDENTIFIER_KEYS = {
    "whatsapp_message_id",
    "patient_id",
    "source_interaction_id",
}

_WAMID_PATTERN = re.compile(r"wamid\.[A-Za-z0-9._~+/=-]+")
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_PHONE_PATTERN = re.compile(
    r"((?:telefono|phone(?:_number)?)[^0-9+]{0,12})(\+?\d{6,20})",
    re.IGNORECASE,
)
_PATIENT_ID_PATTERN = re.compile(
    r"((?:patient_id)[^A-Za-z0-9]{0,12})([A-Za-z0-9._:-]{8,})",
    re.IGNORECASE,
)


def mask_phone(value: Any) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        return "unknown"

    if len(normalized) <= 4:
        return "*" * len(normalized)

    return f"{'*' * (len(normalized) - 4)}{normalized[-4:]}"


def pseudonymize_identifier(value: Any) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        return "unknown"

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"sha256:{digest}"


def sanitize_log_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    sanitized = _WAMID_PATTERN.sub(
        lambda match: pseudonymize_identifier(match.group(0)),
        value,
    )
    sanitized = _URL_PATTERN.sub("[redacted_url]", sanitized)
    sanitized = _PHONE_PATTERN.sub(
        lambda match: f"{match.group(1)}{mask_phone(match.group(2))}",
        sanitized,
    )
    sanitized = _PATIENT_ID_PATTERN.sub(
        lambda match: (
            f"{match.group(1)}"
            f"{pseudonymize_identifier(match.group(2))}"
        ),
        sanitized,
    )

    return sanitized


def sanitize_log_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}

    for key, value in payload.items():
        normalized_key = str(key)

        if normalized_key in _PHONE_KEYS:
            sanitized[normalized_key] = mask_phone(value)
        elif normalized_key in _REDACTED_KEYS:
            sanitized[normalized_key] = "[redacted]"
        elif normalized_key in _HASHED_IDENTIFIER_KEYS:
            sanitized[normalized_key] = pseudonymize_identifier(value)
        elif isinstance(value, Mapping):
            sanitized[normalized_key] = sanitize_log_payload(value)
        elif isinstance(value, (list, tuple)):
            sanitized[normalized_key] = [
                sanitize_log_payload(item)
                if isinstance(item, Mapping)
                else sanitize_log_text(item)
                for item in value
            ]
        else:
            sanitized[normalized_key] = sanitize_log_text(value)

    return sanitized


def print_safe_event(payload: Mapping[str, Any]) -> None:
    print(sanitize_log_payload(payload))
