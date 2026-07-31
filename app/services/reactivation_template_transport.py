from __future__ import annotations

from app.services.reactivation_template_dispatcher import (
    DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE,
    DEFAULT_REACTIVATION_TEMPLATE_NAME,
)
from app.services.whatsapp import (
    send_whatsapp_template_message,
)


def build_reactivation_template_payload(
    *,
    to: str,
    contact_name: str,
) -> dict:
    """
    Build the exact approved Meta payload without sending it.

    The returned payload contains one ordered body parameter and
    performs no HTTP, persistence or runtime operation.
    """

    recipient = str(to or "").strip()
    name = str(contact_name or "").strip()

    if not recipient:
        raise ValueError(
            "Reactivation template recipient is required."
        )

    if not name:
        raise ValueError(
            "Reactivation template contact name is required."
        )

    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": DEFAULT_REACTIVATION_TEMPLATE_NAME,
            "language": {
                "code": DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE,
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": name,
                        }
                    ],
                }
            ],
        },
    }


async def send_reactivation_whatsapp_template(
    *,
    to: str,
    template_name: str,
    language_code: str,
    body_parameters: list[str],
) -> dict:
    """
    Adapt the generic WhatsApp template transport to the
    immutable approved reactivation contract.

    This adapter does not enable campaigns, select contacts or
    contain persistence and lifecycle logic.
    """

    recipient = str(to or "").strip()
    normalized_template_name = str(
        template_name or ""
    ).strip()
    normalized_language_code = str(
        language_code or ""
    ).strip()
    normalized_parameters = [
        str(value or "").strip()
        for value in body_parameters or []
    ]

    approved_contract = (
        normalized_template_name
        == DEFAULT_REACTIVATION_TEMPLATE_NAME
        and normalized_language_code
        == DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE
        and len(normalized_parameters) == 1
        and bool(normalized_parameters[0])
    )

    if not approved_contract:
        raise ValueError(
            "The approved reactivation template contract "
            "requires reactivacion_respirarte, es_CO and "
            "exactly one non-empty body parameter."
        )

    if not recipient:
        raise ValueError(
            "Reactivation template recipient is required."
        )

    return await send_whatsapp_template_message(
        telefono=recipient,
        template_name=normalized_template_name,
        language_code=normalized_language_code,
        body_parameters=normalized_parameters,
    )
