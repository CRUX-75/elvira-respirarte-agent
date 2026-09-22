from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import scripts.manual_reactivation_batch_report as report_script


def test_batch_report_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv(
        "REACTIVATION_BATCH_REPORT_ENABLED",
        raising=False,
    )

    assert report_script.main() == 2


def test_batch_report_reads_contacts_and_prints_safe_metrics(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "REACTIVATION_BATCH_REPORT_ENABLED",
        "1",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_REPORT_CAMPAIGN_ID",
        "RESPIRARTE-REACT-002",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_META_UNIT_COST",
        "0.05",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_META_CURRENCY",
        "USD",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_META_PRICING_SOURCE",
        "Meta current marketing rate",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_META_PRICING_AS_OF",
        "2026-09-21",
    )
    monkeypatch.setenv(
        "REACTIVATION_BATCH_APPOINTMENT_CONTACT_IDS",
        "contact-2",
    )

    contacts = (object(), object())
    repository = Mock()
    repository.list_by_campaign_id.return_value = contacts

    monkeypatch.setattr(
        report_script,
        "_build_contact_repository",
        Mock(return_value=repository),
    )

    metrics = SimpleNamespace(
        total=2,
        delivered=2,
        read=1,
        replied=1,
        interested=1,
        appointment_requests=1,
        opt_out=0,
        total_cost=Decimal("0.10"),
        cost_per_delivered=Decimal("0.05"),
        cost_per_reply=Decimal("0.10"),
        cost_per_positive_response=Decimal("0.10"),
        cost_per_appointment_request=Decimal("0.10"),
        currency="USD",
        pricing_source="Meta current marketing rate",
    )
    calculate = Mock(return_value=metrics)
    monkeypatch.setattr(
        report_script,
        "calculate_reactivation_batch_metrics",
        calculate,
    )

    assert report_script.main() == 0

    repository.list_by_campaign_id.assert_called_once_with(
        campaign_id="RESPIRARTE-REACT-002",
    )

    output = capsys.readouterr().out
    assert "total=2" in output
    assert "delivered=2" in output
    assert "read=1" in output
    assert "replied=1" in output
    assert "interested=1" in output
    assert "appointment_requests=1" in output
    assert "opt_out=0" in output
    assert "total_cost=0.10" in output
    assert "pricing_as_of=2026-09-21" in output
