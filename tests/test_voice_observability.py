import ast

from app.services.voice_observability import (
    emit_voice_event,
    safe_message_content_for_log,
)


def test_voice_event_drops_raw_content(capsys):
    emit_voice_event(
        "voice_stt_succeeded",
        whatsapp_message_id="wamid.voice.obs.001",
        status="success",
        transcript="contenido clínico privado",
        audio_content=b"private-audio",
        transcript_length=25,
    )

    event = ast.literal_eval(capsys.readouterr().out.strip())

    assert event == {
        "event": "voice_stt_succeeded",
        "whatsapp_message_id": "wamid.voice.obs.001",
        "status": "success",
        "transcript_length": 25,
    }


def test_audio_transcript_is_removed_from_general_log():
    assert (
        safe_message_content_for_log(
            msg_type="audio",
            mensaje="contenido clínico privado",
        )
        is None
    )


def test_text_message_remains_available_to_existing_log():
    assert safe_message_content_for_log(
        msg_type="text",
        mensaje="Quiero pedir una cita",
    ) == "Quiero pedir una cita"
