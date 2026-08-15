from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.reactivation_real_pilot import (
    preflight_reactivation_real_pilot,
)


def build_campaign(**updates):
    values = {
        "id": "campaign-1",
        "status": "active",
        "template_name": "reactivacion_respirarte",
        "template_language": "es_CO",
    }
    values.update(updates)
    return SimpleNamespace(**values)


def build_contact(**updates):
    values = {
        "id": "contact-1",
        "campaign_id": "campaign-1",
        "status": "eligible",
        "retryable": False,
        "provider_message_id": None,
    }
    values.update(updates)
    return SimpleNamespace(**values)


def test_preflight_loads_only_explicit_persisted_contacts_in_order():
    campaign_repository = Mock()
    contact_repository = Mock()

    campaign_repository.get_by_id.return_value = build_campaign()

    contact_1 = build_contact(id="contact-1")
    contact_2 = build_contact(id="contact-2")

    contact_repository.get_by_id.side_effect = [
        contact_1,
        contact_2,
    ]

    contacts = preflight_reactivation_real_pilot(
        campaign_id=" campaign-1 ",
        contact_ids=[
            " contact-1 ",
            "contact-2",
        ],
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
    )

    assert contacts == (
        contact_1,
        contact_2,
    )

    campaign_repository.get_by_id.assert_called_once_with(
        "campaign-1"
    )

    assert contact_repository.get_by_id.call_args_list == [
        (("contact-1",),),
        (("contact-2",),),
    ]


@pytest.mark.parametrize(
    "contact_ids",
    [
        [],
        ["contact-1", "contact-2", "contact-3", "contact-4"],
        ["contact-1", "contact-1"],
        ["contact-1", "   "],
    ],
)
def test_preflight_rejects_non_explicit_minimal_batch_before_reads(
    contact_ids,
):
    campaign_repository = Mock()
    contact_repository = Mock()

    with pytest.raises(ValueError):
        preflight_reactivation_real_pilot(
            campaign_id="campaign-1",
            contact_ids=contact_ids,
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
        )

    campaign_repository.get_by_id.assert_not_called()
    contact_repository.get_by_id.assert_not_called()


@pytest.mark.parametrize(
    ("campaign_updates", "expected_message"),
    [
        (
            {"status": "draft"},
            "active",
        ),
        (
            {"template_name": "otro_template"},
            "approved reactivation template",
        ),
        (
            {"template_language": "es_ES"},
            "approved reactivation template",
        ),
    ],
)
def test_preflight_rejects_campaign_gate_before_contact_reads(
    campaign_updates,
    expected_message,
):
    campaign_repository = Mock()
    contact_repository = Mock()

    campaign_repository.get_by_id.return_value = build_campaign(
        **campaign_updates
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        preflight_reactivation_real_pilot(
            campaign_id="campaign-1",
            contact_ids=["contact-1"],
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
        )

    contact_repository.get_by_id.assert_not_called()


@pytest.mark.parametrize(
    ("contact_updates", "expected_message"),
    [
        (
            {"campaign_id": "another-campaign"},
            "campaign",
        ),
        (
            {"provider_message_id": "wamid.already-sent"},
            "provider_message_id",
        ),
        (
            {
                "status": "failed",
                "retryable": False,
            },
            "dispatchable",
        ),
        (
            {
                "status": "pending",
                "retryable": False,
            },
            "dispatchable",
        ),
    ],
)
def test_preflight_rejects_non_dispatchable_persisted_contact(
    contact_updates,
    expected_message,
):
    campaign_repository = Mock()
    contact_repository = Mock()

    campaign_repository.get_by_id.return_value = build_campaign()
    contact_repository.get_by_id.return_value = build_contact(
        **contact_updates
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        preflight_reactivation_real_pilot(
            campaign_id="campaign-1",
            contact_ids=["contact-1"],
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
        )


def test_preflight_accepts_retryable_failed_contact():
    campaign_repository = Mock()
    contact_repository = Mock()

    campaign_repository.get_by_id.return_value = build_campaign()

    retryable_contact = build_contact(
        status="failed",
        retryable=True,
    )
    contact_repository.get_by_id.return_value = retryable_contact

    contacts = preflight_reactivation_real_pilot(
        campaign_id="campaign-1",
        contact_ids=["contact-1"],
        campaign_repository=campaign_repository,
        contact_repository=contact_repository,
    )

    assert contacts == (retryable_contact,)


def test_preflight_rejects_missing_persisted_objects():
    campaign_repository = Mock()
    contact_repository = Mock()

    campaign_repository.get_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="campaign",
    ):
        preflight_reactivation_real_pilot(
            campaign_id="campaign-missing",
            contact_ids=["contact-1"],
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
        )

    contact_repository.get_by_id.assert_not_called()

    campaign_repository.reset_mock()
    campaign_repository.get_by_id.return_value = build_campaign()
    contact_repository.get_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="contact",
    ):
        preflight_reactivation_real_pilot(
            campaign_id="campaign-1",
            contact_ids=["contact-missing"],
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
        )


# === F.3 REAL PILOT EXECUTION CONTRACT ===

import asyncio

from app.services.reactivation_real_pilot import (
    run_reactivation_real_pilot,
)
from app.services.reactivation_template_dispatcher import (
    ReactivationTemplateDispatchResult,
)


def test_real_pilot_requires_explicit_send_authorization():
    campaign_repository = Mock()
    contact_repository = Mock()
    dispatcher = Mock()

    campaign_repository.get_by_id.return_value = build_campaign()
    contact_repository.get_by_id.return_value = build_contact()

    with pytest.raises(
        ValueError,
        match="explicit send authorization",
    ):
        asyncio.run(
            run_reactivation_real_pilot(
                campaign_id="campaign-1",
                contact_ids=["contact-1"],
                campaign_repository=campaign_repository,
                contact_repository=contact_repository,
                dispatcher=dispatcher,
            )
        )

    campaign_repository.get_by_id.assert_called_once_with(
        "campaign-1"
    )
    contact_repository.get_by_id.assert_called_once_with(
        "contact-1"
    )
    dispatcher.dispatch.assert_not_called()


def test_real_pilot_dispatches_only_preflighted_ids_in_order():
    campaign_repository = Mock()
    contact_repository = Mock()
    dispatcher = Mock()

    campaign_repository.get_by_id.return_value = build_campaign()

    contact_1 = build_contact(id="contact-1")
    contact_2 = build_contact(id="contact-2")

    contact_repository.get_by_id.side_effect = [
        contact_1,
        contact_2,
    ]

    result_1 = ReactivationTemplateDispatchResult(
        outcome="accepted",
        contact_id="contact-1",
        provider_message_id="wamid.pilot.1",
        retryable=False,
    )
    result_2 = ReactivationTemplateDispatchResult(
        outcome="claimed_elsewhere_or_ineligible",
        contact_id="contact-2",
        provider_message_id=None,
        retryable=False,
    )

    dispatcher.dispatch.side_effect = [
        result_1,
        result_2,
    ]

    batch = asyncio.run(
        run_reactivation_real_pilot(
            campaign_id="campaign-1",
            contact_ids=[
                "contact-1",
                "contact-2",
            ],
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
            dispatcher=dispatcher,
            send_authorized=True,
        )
    )

    assert batch.results == (
        result_1,
        result_2,
    )

    assert dispatcher.dispatch.call_args_list == [
        ((), {"contact_id": "contact-1"}),
        ((), {"contact_id": "contact-2"}),
    ]


def test_real_pilot_preflight_failure_never_dispatches():
    campaign_repository = Mock()
    contact_repository = Mock()
    dispatcher = Mock()

    campaign_repository.get_by_id.return_value = build_campaign(
        status="draft"
    )

    with pytest.raises(
        ValueError,
        match="active",
    ):
        asyncio.run(
            run_reactivation_real_pilot(
                campaign_id="campaign-1",
                contact_ids=["contact-1"],
                campaign_repository=campaign_repository,
                contact_repository=contact_repository,
                dispatcher=dispatcher,
                send_authorized=True,
            )
        )

    contact_repository.get_by_id.assert_not_called()
    dispatcher.dispatch.assert_not_called()
