from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services import whatsapp


class FakeResponse:
    def __init__(self):
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"messages": [{"id": "wamid.template"}]}


class FakeAsyncClient:
    def __init__(self, captured):
        self.captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, *, headers, json):
        self.captured.update(url=url, headers=headers, payload=json)
        return FakeResponse()


def test_template_transport_builds_ordered_body_parameters(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        whatsapp,
        "settings",
        SimpleNamespace(
            whatsapp_phone_number_id="phone-id",
            whatsapp_token="token",
            whatsapp_api_url="https://graph.facebook.com/v25.0",
        ),
    )
    monkeypatch.setattr(
        whatsapp.httpx,
        "AsyncClient",
        lambda: FakeAsyncClient(captured),
    )

    parameters = [f"valor-{index}" for index in range(1, 11)]
    response = asyncio.run(
        whatsapp.send_whatsapp_template_message(
            telefono="573000000001",
            template_name="revision_humana",
            language_code="es_CO",
            body_parameters=parameters,
        )
    )

    assert response["messages"][0]["id"] == "wamid.template"
    assert captured["payload"]["type"] == "template"
    assert captured["payload"]["template"]["name"] == (
        "revision_humana"
    )
    assert captured["payload"]["template"]["language"] == {
        "code": "es_CO"
    }
    sent_parameters = captured["payload"]["template"]["components"][0][
        "parameters"
    ]
    assert [item["text"] for item in sent_parameters] == parameters
    assert all(item["type"] == "text" for item in sent_parameters)
