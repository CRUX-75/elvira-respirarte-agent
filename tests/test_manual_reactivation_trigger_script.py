from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "manual_reactivation_trigger.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "manual_reactivation_trigger_script",
        SCRIPT_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_manual_trigger_parses_explicit_source_references():
    module = _load_module()

    assert module._parse_source_references(
        "TEST-001, TEST-002"
    ) == (
        "TEST-001",
        "TEST-002",
    )


def test_manual_trigger_refuses_duplicate_source_references():
    module = _load_module()

    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        module._parse_source_references(
            "TEST-001,TEST-001"
        )


def test_manual_trigger_refuses_more_than_three_contacts():
    module = _load_module()

    with pytest.raises(
        ValueError,
        match="Maximum 3",
    ):
        module._parse_source_references(
            "A,B,C,D"
        )


def test_manual_trigger_confirmation_is_campaign_specific():
    module = _load_module()

    assert (
        module._expected_confirmation(
            "manual-trigger-20260905"
        )
        == "CONFIRM:manual-trigger-20260905"
    )


def test_manual_trigger_script_has_no_whatsapp_dispatch_path():
    source = SCRIPT_PATH.read_text(
        encoding="utf-8"
    )

    assert "reactivation_template_dispatcher" not in source
    assert "send_whatsapp_message(" not in source
    assert "send_whatsapp_template_message(" not in source
