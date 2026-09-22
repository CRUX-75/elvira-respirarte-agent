import pytest

from scripts.manual_reactivation_batch import (
    _parse_source_references,
)


def test_batch_script_accepts_ten_explicit_source_references():
    raw = ",".join(
        f"HIST-{index:03d}"
        for index in range(4, 14)
    )

    assert _parse_source_references(raw) == tuple(
        f"HIST-{index:03d}"
        for index in range(4, 14)
    )


def test_batch_script_refuses_more_than_ten_source_references():
    raw = ",".join(
        f"HIST-{index:03d}"
        for index in range(4, 15)
    )

    with pytest.raises(ValueError, match="Maximum 10"):
        _parse_source_references(raw)


import scripts.manual_reactivation_batch as batch_script


def test_batch_script_is_disabled_by_default(monkeypatch, capsys):
    monkeypatch.delenv(
        "REACTIVATION_BATCH_ENABLED",
        raising=False,
    )

    assert batch_script.main() == 2

    output = capsys.readouterr().out
    assert "REACTIVATION_BATCH_ENABLED" in output


from types import SimpleNamespace
from unittest.mock import Mock


def test_batch_script_preview_performs_no_writes_or_send(
    monkeypatch,
    capsys,
):
    source_references = tuple(
        f"HIST-{index:03d}"
        for index in range(4, 14)
    )

    monkeypatch.setenv("REACTIVATION_BATCH_ENABLED", "1")
    monkeypatch.setenv(
        "REACTIVATION_BATCH_CAMPAIGN_ID",
        "RESPIRARTE-REACT-002",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_CAMPAIGN_NAME",
        "Primer lote operativo",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_SOURCE_REFERENCES",
        ",".join(source_references),
    )
    monkeypatch.delenv(
        "REACTIVATION_BATCH_AUTHORIZATION",
        raising=False,
    )
    monkeypatch.delenv(
        "REACTIVATION_BATCH_SEND_AUTHORIZED",
        raising=False,
    )

    dependencies = SimpleNamespace(
        adapter=object(),
        context_resolver=object(),
        default_country_code="57",
    )

    build_dependencies = Mock(return_value=dependencies)
    monkeypatch.setattr(
        batch_script,
        "_build_preflight_dependencies",
        build_dependencies,
    )

    manual_preflight = SimpleNamespace()
    preflight_manual = Mock(return_value=manual_preflight)
    monkeypatch.setattr(
        batch_script,
        "preflight_manual_reactivation",
        preflight_manual,
    )

    batch_preflight = SimpleNamespace(
        requested=10,
        eligible=10,
        excluded=0,
        already_processed=0,
        estimated_sends=10,
        source_references=source_references,
        prepared_items=tuple(range(10)),
    )
    build_batch_preflight = Mock(return_value=batch_preflight)
    monkeypatch.setattr(
        batch_script,
        "build_reactivation_batch_preflight",
        build_batch_preflight,
    )

    token_builder = Mock(return_value="AUTHORIZE_BATCH:test-token")
    monkeypatch.setattr(
        batch_script,
        "build_reactivation_batch_authorization_token",
        token_builder,
    )

    assert batch_script.main() == 0

    output = capsys.readouterr().out
    assert "requested=10" in output
    assert "eligible=10" in output
    assert "excluded=0" in output
    assert "already_processed=0" in output
    assert "estimated_sends=10" in output
    assert "PREVIEW_ONLY=True" in output
    assert "writes_performed=False" in output
    assert "whatsapp_send=False" in output
    assert "AUTHORIZE_BATCH:test-token" in output



def test_batch_script_executes_only_after_complete_authorization(
    monkeypatch,
    capsys,
):
    campaign_id = "RESPIRARTE-REACT-002"
    source_references = tuple(
        f"HIST-{index:03d}"
        for index in range(4, 14)
    )

    monkeypatch.setenv("REACTIVATION_BATCH_ENABLED", "1")
    monkeypatch.setenv(
        "REACTIVATION_BATCH_CAMPAIGN_ID",
        campaign_id,
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_CAMPAIGN_NAME",
        "Primer lote operativo",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_SOURCE_REFERENCES",
        ",".join(source_references),
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_AUTHORIZATION",
        "AUTHORIZED-TOKEN",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_SEND_AUTHORIZED",
        "1",
    )

    preview_dependencies = SimpleNamespace(
        adapter=object(),
        context_resolver=object(),
        default_country_code="57",
    )
    monkeypatch.setattr(
        batch_script,
        "_build_preflight_dependencies",
        Mock(return_value=preview_dependencies),
    )
    monkeypatch.setattr(
        batch_script,
        "preflight_manual_reactivation",
        Mock(return_value=SimpleNamespace(runtime_error=0)),
    )

    batch_preflight = SimpleNamespace(
        requested=10,
        eligible=10,
        excluded=0,
        already_processed=0,
        estimated_sends=10,
        source_references=source_references,
        prepared_items=tuple(range(10)),
    )
    monkeypatch.setattr(
        batch_script,
        "build_reactivation_batch_preflight",
        Mock(return_value=batch_preflight),
    )
    monkeypatch.setattr(
        batch_script,
        "build_reactivation_batch_authorization_token",
        Mock(return_value="AUTHORIZED-TOKEN"),
    )

    authorization = SimpleNamespace(
        campaign_id=campaign_id,
        source_references=source_references,
        prepared_items=tuple(range(10)),
    )
    authorize = Mock(return_value=authorization)
    monkeypatch.setattr(
        batch_script,
        "authorize_reactivation_batch",
        authorize,
        raising=False,
    )

    contacts = tuple(
        SimpleNamespace(id=f"contact-{index}")
        for index in range(1, 11)
    )
    persistence = SimpleNamespace(contacts=contacts)

    persist = Mock(return_value=persistence)
    monkeypatch.setattr(
        batch_script,
        "persist_authorized_reactivation_batch",
        persist,
        raising=False,
    )

    execution_dependencies = SimpleNamespace(
        campaign_repository=Mock(),
        contact_repository=Mock(),
        dispatcher=Mock(),
    )
    monkeypatch.setattr(
        batch_script,
        "_build_execution_dependencies",
        Mock(return_value=execution_dependencies),
        raising=False,
    )

    activate = Mock(
        return_value=SimpleNamespace(
            id=campaign_id,
            status=SimpleNamespace(value="active"),
        )
    )
    monkeypatch.setattr(
        batch_script,
        "activate_manual_reactivation_campaign",
        activate,
        raising=False,
    )

    run_batch = Mock(return_value=object())
    monkeypatch.setattr(
        batch_script,
        "run_reactivation_batch",
        run_batch,
        raising=False,
    )

    batch_result = SimpleNamespace(
        total=10,
        accepted=10,
        failed=0,
        ignored=0,
    )
    asyncio_run = Mock(return_value=batch_result)
    monkeypatch.setattr(
        batch_script,
        "asyncio",
        SimpleNamespace(run=asyncio_run),
        raising=False,
    )

    assert batch_script.main() == 0

    output = capsys.readouterr().out
    assert "total=10" in output
    assert "accepted=10" in output
    assert "failed=0" in output
    assert "ignored=0" in output

    assert persist.call_count == 1
    assert activate.call_count == 1
    assert run_batch.call_count == 1
    assert asyncio_run.call_count == 1
