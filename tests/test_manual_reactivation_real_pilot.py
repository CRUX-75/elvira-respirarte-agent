import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import scripts.manual_reactivation_real_pilot as pilot_script


ENABLE_ENV = "REACTIVATION_REAL_PILOT_ENABLED"
SEND_ENV = "REACTIVATION_REAL_PILOT_SEND_AUTHORIZED"
CAMPAIGN_ENV = "REACTIVATION_REAL_PILOT_CAMPAIGN_ID"
CONTACTS_ENV = "REACTIVATION_REAL_PILOT_CONTACT_IDS"


def clear_pilot_env(monkeypatch):
    for name in (
        ENABLE_ENV,
        SEND_ENV,
        CAMPAIGN_ENV,
        CONTACTS_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


def test_manual_real_pilot_is_disabled_by_default(
    monkeypatch,
):
    clear_pilot_env(monkeypatch)

    build_dispatcher = Mock()
    run_pilot = Mock()

    monkeypatch.setattr(
        pilot_script,
        "build_reactivation_template_dispatcher",
        build_dispatcher,
    )
    monkeypatch.setattr(
        pilot_script,
        "run_reactivation_real_pilot",
        run_pilot,
    )

    assert pilot_script.main() == 2

    build_dispatcher.assert_not_called()
    run_pilot.assert_not_called()


@pytest.mark.parametrize(
    "enabled_value",
    [
        "",
        "0",
        "true",
        "TRUE",
        "yes",
        "2",
    ],
)
def test_manual_real_pilot_requires_exact_enable_flag(
    monkeypatch,
    enabled_value,
):
    clear_pilot_env(monkeypatch)

    monkeypatch.setenv(ENABLE_ENV, enabled_value)

    build_dispatcher = Mock()
    monkeypatch.setattr(
        pilot_script,
        "build_reactivation_template_dispatcher",
        build_dispatcher,
    )

    assert pilot_script.main() == 2
    build_dispatcher.assert_not_called()


def test_manual_real_pilot_requires_campaign_before_dispatcher(
    monkeypatch,
):
    clear_pilot_env(monkeypatch)

    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.setenv(SEND_ENV, "1")
    monkeypatch.setenv(CONTACTS_ENV, "contact-1")

    build_dispatcher = Mock()
    monkeypatch.setattr(
        pilot_script,
        "build_reactivation_template_dispatcher",
        build_dispatcher,
    )

    assert pilot_script.main() == 2
    build_dispatcher.assert_not_called()


@pytest.mark.parametrize(
    "raw_contacts",
    [
        "",
        "   ",
        "contact-1,",
        ",contact-1",
        "contact-1,,contact-2",
        "contact-1,contact-1",
        "contact-1,contact-2,contact-3,contact-4",
    ],
)
def test_manual_real_pilot_rejects_invalid_explicit_batch_before_dispatcher(
    monkeypatch,
    raw_contacts,
):
    clear_pilot_env(monkeypatch)

    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.setenv(SEND_ENV, "1")
    monkeypatch.setenv(CAMPAIGN_ENV, "campaign-1")
    monkeypatch.setenv(CONTACTS_ENV, raw_contacts)

    build_dispatcher = Mock()
    monkeypatch.setattr(
        pilot_script,
        "build_reactivation_template_dispatcher",
        build_dispatcher,
    )

    assert pilot_script.main() == 2
    build_dispatcher.assert_not_called()


@pytest.mark.parametrize(
    "send_value",
    [
        "",
        "0",
        "true",
        "TRUE",
        "yes",
        "2",
    ],
)
def test_manual_real_pilot_requires_exact_send_authorization_before_dispatcher(
    monkeypatch,
    send_value,
):
    clear_pilot_env(monkeypatch)

    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.setenv(SEND_ENV, send_value)
    monkeypatch.setenv(CAMPAIGN_ENV, "campaign-1")
    monkeypatch.setenv(
        CONTACTS_ENV,
        "contact-1,contact-2",
    )

    build_dispatcher = Mock()
    run_pilot = Mock()

    monkeypatch.setattr(
        pilot_script,
        "build_reactivation_template_dispatcher",
        build_dispatcher,
    )
    monkeypatch.setattr(
        pilot_script,
        "run_reactivation_real_pilot",
        run_pilot,
    )

    assert pilot_script.main() == 2

    build_dispatcher.assert_not_called()
    run_pilot.assert_not_called()


def test_manual_real_pilot_builds_enabled_dispatcher_only_after_all_gates(
    monkeypatch,
):
    clear_pilot_env(monkeypatch)

    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.setenv(SEND_ENV, "1")
    monkeypatch.setenv(
        CAMPAIGN_ENV,
        " campaign-1 ",
    )
    monkeypatch.setenv(
        CONTACTS_ENV,
        " contact-1 , contact-2 ",
    )

    campaign_repository = Mock()
    contact_repository = Mock()
    dispatcher = Mock()

    monkeypatch.setattr(
        pilot_script,
        "ReactivationCampaignRepository",
        Mock(return_value=campaign_repository),
    )
    monkeypatch.setattr(
        pilot_script,
        "ReactivationCampaignContactRepository",
        Mock(return_value=contact_repository),
    )

    build_dispatcher = Mock(
        return_value=dispatcher
    )
    monkeypatch.setattr(
        pilot_script,
        "build_reactivation_template_dispatcher",
        build_dispatcher,
    )

    batch = SimpleNamespace(
        total=2,
        accepted=1,
        failed=0,
        ignored=1,
    )

    run_pilot = Mock(return_value=batch)
    monkeypatch.setattr(
        pilot_script,
        "run_reactivation_real_pilot",
        run_pilot,
    )

    asyncio_run = Mock(return_value=batch)
    monkeypatch.setattr(
        pilot_script.asyncio,
        "run",
        asyncio_run,
    )

    assert pilot_script.main() == 0

    build_dispatcher.assert_called_once_with(
        engine=pilot_script.engine,
        enabled=True,
    )

    run_pilot.assert_called_once_with(
        campaign_id="campaign-1",
        contact_ids=(
            "contact-1",
            "contact-2",
        ),
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
        dispatcher=dispatcher,
        send_authorized=True,
    )

    asyncio_run.assert_called_once_with(
        run_pilot.return_value
    )


def test_manual_real_pilot_fails_safely_on_runtime_error(
    monkeypatch,
):
    clear_pilot_env(monkeypatch)

    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.setenv(SEND_ENV, "1")
    monkeypatch.setenv(CAMPAIGN_ENV, "campaign-1")
    monkeypatch.setenv(CONTACTS_ENV, "contact-1")

    monkeypatch.setattr(
        pilot_script,
        "ReactivationCampaignRepository",
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        pilot_script,
        "ReactivationCampaignContactRepository",
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        pilot_script,
        "build_reactivation_template_dispatcher",
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        pilot_script,
        "run_reactivation_real_pilot",
        Mock(side_effect=RuntimeError("sensitive detail")),
    )

    assert pilot_script.main() == 2
