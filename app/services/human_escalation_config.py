from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from app.services.human_escalation import normalize_whatsapp_number


@dataclass(frozen=True)
class HumanEscalationConfig:
    enabled: bool
    whatsapp_number: str | None

    @property
    def ready(self) -> bool:
        return self.enabled and self.whatsapp_number is not None


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value

    return str(value or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "si",
        "sí",
    }


def _setting_value(
    settings_obj: object | None,
    *,
    lowercase_name: str,
    uppercase_name: str,
) -> object | None:
    if settings_obj is None:
        return None

    lowercase_value = getattr(
        settings_obj,
        lowercase_name,
        None,
    )

    if lowercase_value is not None:
        return lowercase_value

    return getattr(
        settings_obj,
        uppercase_name,
        None,
    )


def load_human_escalation_config(
    *,
    settings_obj: object | None = None,
    environ: Mapping[str, str] | None = None,
) -> HumanEscalationConfig:
    env = environ if environ is not None else os.environ

    configured_enabled = _setting_value(
        settings_obj,
        lowercase_name="human_escalation_enabled",
        uppercase_name="HUMAN_ESCALATION_ENABLED",
    )

    configured_number = _setting_value(
        settings_obj,
        lowercase_name="human_escalation_whatsapp_number",
        uppercase_name="HUMAN_ESCALATION_WHATSAPP_NUMBER",
    )

    enabled_raw = (
        configured_enabled
        if configured_enabled is not None
        else env.get(
            "HUMAN_ESCALATION_ENABLED",
            "false",
        )
    )

    number_raw = (
        configured_number
        if configured_number not in {None, ""}
        else env.get(
            "HUMAN_ESCALATION_WHATSAPP_NUMBER",
            "",
        )
    )

    return HumanEscalationConfig(
        enabled=_parse_bool(enabled_raw),
        whatsapp_number=normalize_whatsapp_number(
            str(number_raw or "")
        ),
    )
