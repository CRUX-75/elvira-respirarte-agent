from unittest.mock import Mock

from app.services import reactivation_template_transport
from app.services.reactivation_template_transport import (
    build_reactivation_template_payload,
)


def test_builds_exact_approved_meta_payload_without_sending(
    monkeypatch,
):
    sender = Mock()

    monkeypatch.setattr(
        reactivation_template_transport,
        "send_whatsapp_template_message",
        sender,
    )

    payload = build_reactivation_template_payload(
        to="573000000001",
        contact_name="Contacto de prueba",
    )

    assert payload == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "573000000001",
        "type": "template",
        "template": {
            "name": "reactivacion_respirarte",
            "language": {
                "code": "es_CO",
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": "Contacto de prueba",
                        }
                    ],
                }
            ],
        },
    }

    sender.assert_not_called()
