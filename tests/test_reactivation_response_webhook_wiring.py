from pathlib import Path


def _main_source() -> str:
    return Path("app/main.py").read_text(
        encoding="utf-8"
    )


def test_webhook_wires_reactivation_response_runtime():
    source = _main_source()

    assert (
        "from app.services.reactivation_response_runtime import ("
        in source
    )
    assert (
        "process_reactivation_response_best_effort"
        in source
    )
    assert (
        "ReactivationCampaignResponseService"
        in source
    )
    assert (
        "ReactivationCampaignContactRepository"
        in source
    )


def test_reactivation_correlation_runs_after_voice_transcription():
    source = _main_source()

    voice_index = source.index(
        '"event": "whatsapp_voice_transcribed"'
    )

    correlation_index = source.index(
        "await process_reactivation_response_best_effort(",
        voice_index,
    )

    patient_index = source.index(
        "patient = get_or_create_patient_by_phone(",
        correlation_index,
    )

    assert voice_index < correlation_index < patient_index


def test_reactivation_correlation_uses_transcribed_or_text_message():
    source = _main_source()

    start = source.index(
        "await process_reactivation_response_best_effort("
    )

    end = source.index(
        "patient = get_or_create_patient_by_phone(",
        start,
    )

    wiring = source[start:end]

    assert "phone_e164=telefono" in wiring
    assert (
        "inbound_whatsapp_message_id=whatsapp_message_id"
        in wiring
    )
    assert "message=mensaje" in wiring

    # General webhook already owns these side effects.
    # Reactivation wiring must only correlate/persist.
    assert "global_opt_out_writer=" not in wiring
    assert "escalation_writer=" not in wiring
