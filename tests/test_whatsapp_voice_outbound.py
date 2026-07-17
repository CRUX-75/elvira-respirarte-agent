import asyncio

import app.services.whatsapp_media as media_service


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def post(self, url, **kwargs):
        file_content = None
        files = kwargs.get("files")

        if files:
            file_content = files["file"][1].read()

        self.calls.append(
            {
                "url": url,
                "kwargs": kwargs,
                "file_content": file_content,
            }
        )
        return FakeResponse(self.payload)


def configure_credentials(monkeypatch):
    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_phone_number_id",
        "phone-number-001",
    )
    monkeypatch.setattr(
        media_service.settings,
        "whatsapp_token",
        "token-001",
    )


def test_upload_whatsapp_voice_media(monkeypatch, tmp_path):
    configure_credentials(monkeypatch)
    audio_path = tmp_path / "reply.ogg"
    audio_path.write_bytes(b"OggSvoice-data")
    client = FakeClient({"id": "uploaded-media-001"})

    result = asyncio.run(
        media_service.upload_whatsapp_voice_media(
            audio_path,
            client=client,
        )
    )

    call = client.calls[0]

    assert result.media_id == "uploaded-media-001"
    assert call["url"].endswith("/phone-number-001/media")
    assert call["kwargs"]["data"] == {
        "messaging_product": "whatsapp",
    }
    assert call["kwargs"]["files"]["file"][2] == "audio/ogg"
    assert call["file_content"] == b"OggSvoice-data"


def test_upload_whatsapp_voice_media_rejects_non_ogg(
    monkeypatch,
    tmp_path,
):
    configure_credentials(monkeypatch)
    audio_path = tmp_path / "reply.ogg"
    audio_path.write_bytes(b"not-ogg")

    try:
        asyncio.run(
            media_service.upload_whatsapp_voice_media(
                audio_path,
                client=FakeClient({"id": "unused"}),
            )
        )
    except ValueError as exc:
        assert str(exc) == "Outbound voice file is not OGG/Opus"
    else:
        raise AssertionError("Expected invalid OGG rejection")


def test_send_whatsapp_voice_note_uses_uploaded_media(monkeypatch):
    configure_credentials(monkeypatch)
    client = FakeClient(
        {
            "messages": [
                {"id": "wamid.voice.reply.001"},
            ]
        }
    )

    response = asyncio.run(
        media_service.send_whatsapp_voice_note(
            telefono="573009450001",
            media_id="uploaded-media-001",
            client=client,
        )
    )

    payload = client.calls[0]["kwargs"]["json"]

    assert payload == {
        "messaging_product": "whatsapp",
        "to": "573009450001",
        "type": "audio",
        "audio": {
            "id": "uploaded-media-001",
            "voice": True,
        },
    }
    assert response["messages"][0]["id"] == "wamid.voice.reply.001"
