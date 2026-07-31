import asyncio
from unittest.mock import AsyncMock

import pytest

from app.services import reactivation_template_transport


def test_reactivation_adapter_maps_to_generic_whatsapp_transport(
    monkeypatch,
):
    captured = {}

    async def fake_whatsapp_send(
        *,
        telefono,
        template_name,
        language_code,
        body_parameters,
    ):
        captured.update(
            telefono=telefono,
            template_name=template_name,
            language_code=language_code,
            body_parameters=body_parameters,
        )
        return {
            "messages": [
                {
                    "id": "wamid.reactivation.adapter",
                }
            ]
        }

    monkeypatch.setattr(
        reactivation_template_transport,
        "send_whatsapp_template_message",
        fake_whatsapp_send,
    )

    response = asyncio.run(
        reactivation_template_transport
        .send_reactivation_whatsapp_template(
            to="573000000001",
            template_name="reactivacion_respirarte",
            language_code="es_CO",
            body_parameters=["Contacto de prueba"],
        )
    )

    assert captured == {
        "telefono": "573000000001",
        "template_name": "reactivacion_respirarte",
        "language_code": "es_CO",
        "body_parameters": ["Contacto de prueba"],
    }
    assert response == {
        "messages": [
            {
                "id": "wamid.reactivation.adapter",
            }
        ]
    }

@pytest.mark.parametrize(
    (
        "template_name",
        "language_code",
        "body_parameters",
    ),
    [
        (
            "revision_humana",
            "es_CO",
            ["Contacto de prueba"],
        ),
        (
            "reactivacion_respirarte",
            "es_ES",
            ["Contacto de prueba"],
        ),
        (
            "reactivacion_respirarte",
            "es_CO",
            [],
        ),
        (
            "reactivacion_respirarte",
            "es_CO",
            [""],
        ),
        (
            "reactivacion_respirarte",
            "es_CO",
            [
                "Contacto de prueba",
                "Parámetro adicional",
            ],
        ),
    ],
)
def test_adapter_rejects_nonapproved_contract_without_sending(
    monkeypatch,
    template_name,
    language_code,
    body_parameters,
):
    sender = AsyncMock(
        return_value={
            "messages": [
                {
                    "id": "wamid.must-not-be-used",
                }
            ]
        }
    )

    monkeypatch.setattr(
        reactivation_template_transport,
        "send_whatsapp_template_message",
        sender,
    )

    with pytest.raises(
        ValueError,
        match="approved reactivation template contract",
    ):
        asyncio.run(
            reactivation_template_transport
            .send_reactivation_whatsapp_template(
                to="573000000001",
                template_name=template_name,
                language_code=language_code,
                body_parameters=body_parameters,
            )
        )

    sender.assert_not_awaited()
