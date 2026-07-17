from app.models.whatsapp import WhatsAppPayload


def build_meta_audio_payload(audio: dict) -> WhatsAppPayload:
    return WhatsAppPayload(
        object="whatsapp_business_account",
        entry=[
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Paciente Voz Test",
                                    },
                                    "wa_id": "573009450001",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "573009450001",
                                    "id": "wamid.p6f993.audio.001",
                                    "timestamp": "1790000100",
                                    "type": "audio",
                                    "audio": audio,
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    )


def test_extract_message_from_meta_voice_note_payload():
    payload = build_meta_audio_payload(
        {
            "id": "audio-media-id-001",
            "mime_type": "audio/ogg; codecs=opus",
            "sha256": "audio-sha256-test",
            "voice": True,
        }
    )

    assert payload.extract_message() == {
        "telefono": "573009450001",
        "nombre": "Paciente Voz Test",
        "msg_type": "audio",
        "whatsapp_message_id": "wamid.p6f993.audio.001",
        "whatsapp_timestamp": "1790000100",
        "mensaje": None,
        "media_id": "audio-media-id-001",
        "mime_type": "audio/ogg; codecs=opus",
        "sha256": "audio-sha256-test",
        "voice": True,
    }


def test_extract_message_returns_none_for_voice_note_without_media_id():
    payload = build_meta_audio_payload(
        {
            "mime_type": "audio/ogg; codecs=opus",
            "sha256": "audio-sha256-test",
            "voice": True,
        }
    )

    assert payload.extract_message() is None
