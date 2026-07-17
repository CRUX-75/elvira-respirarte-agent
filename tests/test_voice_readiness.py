from app.config import settings
from app.services.readiness import build_ready_report


def test_readiness_does_not_require_allowlist_when_voice_is_off(
    monkeypatch,
):
    monkeypatch.setattr(settings, "voice_input_enabled", False)
    monkeypatch.setattr(settings, "voice_replies_enabled", False)
    monkeypatch.setattr(settings, "voice_allowed_phone_numbers", "")

    report = build_ready_report()

    assert "voice_allowed_phone_numbers_missing" not in (
        report["hard_failures"]
    )
    assert report["voice"]["allowed_phone_count"] == 0


def test_readiness_fails_closed_when_voice_has_no_allowlist(
    monkeypatch,
):
    monkeypatch.setattr(settings, "voice_input_enabled", True)
    monkeypatch.setattr(settings, "voice_replies_enabled", False)
    monkeypatch.setattr(settings, "voice_allowed_phone_numbers", "")

    report = build_ready_report()

    assert "voice_allowed_phone_numbers_missing" in (
        report["hard_failures"]
    )
    assert report["safety"]["voice_activation_allowed"] is False


def test_readiness_accepts_controlled_voice_configuration(
    monkeypatch,
):
    monkeypatch.setattr(settings, "voice_input_enabled", True)
    monkeypatch.setattr(settings, "voice_replies_enabled", True)
    monkeypatch.setattr(settings, "voice_reply_to_audio_only", True)
    monkeypatch.setattr(
        settings,
        "voice_allowed_phone_numbers",
        "573001112233",
    )

    report = build_ready_report()

    assert "voice_allowed_phone_numbers_missing" not in (
        report["hard_failures"]
    )
    assert "voice_replies_require_voice_input" not in (
        report["hard_failures"]
    )
    assert "voice_reply_scope_not_controlled" not in (
        report["hard_failures"]
    )
    assert report["voice"]["allowed_phone_count"] == 1
    assert report["safety"]["voice_activation_allowed"] is True
