from types import SimpleNamespace

from app.models.reactivation_campaign import ReactivationContactStatus
from app.services.reactivation_batch import (
    MAX_REACTIVATION_BATCH_CONTACTS,
    build_reactivation_batch_preflight,
)


def test_batch_limit_is_ten():
    assert MAX_REACTIVATION_BATCH_CONTACTS == 10


def test_batch_preflight_summarizes_ten_explicit_eligible_contacts():
    source_references = tuple(
        f"HIST-{index:03d}"
        for index in range(4, 14)
    )

    prepared_items = tuple(
        (
            SimpleNamespace(source_reference=source_reference),
            SimpleNamespace(
                status=ReactivationContactStatus.ELIGIBLE,
                exclusion_reasons=(),
            ),
        )
        for source_reference in source_references
    )

    preflight = SimpleNamespace(
        prepared_items=prepared_items,
    )

    result = build_reactivation_batch_preflight(
        preflight=preflight,
        source_references=source_references,
    )

    assert result.requested == 10
    assert result.eligible == 10
    assert result.excluded == 0
    assert result.already_processed == 0
    assert result.estimated_sends == 10
    assert result.source_references == source_references
    assert result.prepared_items == prepared_items


import pytest

from app.services.reactivation_batch import (
    authorize_reactivation_batch,
    build_reactivation_batch_authorization_token,
)


def test_batch_authorization_is_bound_to_campaign_and_exact_selection():
    source_references = tuple(
        f"HIST-{index:03d}"
        for index in range(4, 14)
    )

    prepared_items = tuple(
        (
            SimpleNamespace(source_reference=source_reference),
            SimpleNamespace(
                status=ReactivationContactStatus.ELIGIBLE,
                exclusion_reasons=(),
            ),
        )
        for source_reference in source_references
    )

    preflight = SimpleNamespace(
        requested=10,
        eligible=10,
        excluded=0,
        already_processed=0,
        estimated_sends=10,
        source_references=source_references,
        prepared_items=prepared_items,
    )

    token = build_reactivation_batch_authorization_token(
        campaign_id="RESPIRARTE-REACT-002",
        source_references=source_references,
    )

    authorization = authorize_reactivation_batch(
        campaign_id="RESPIRARTE-REACT-002",
        preflight=preflight,
        authorization_token=token,
    )

    assert authorization.campaign_id == "RESPIRARTE-REACT-002"
    assert authorization.source_references == source_references
    assert authorization.prepared_items == prepared_items

    with pytest.raises(ValueError, match="authorization"):
        authorize_reactivation_batch(
            campaign_id="RESPIRARTE-REACT-OTHER",
            preflight=preflight,
            authorization_token=token,
        )


import asyncio
from unittest.mock import Mock

from app.services.reactivation_batch import run_reactivation_batch
from app.services.reactivation_template_dispatcher import (
    ReactivationTemplateDispatchResult,
)


def test_authorized_batch_dispatches_ten_preflighted_contacts():
    campaign_id = "RESPIRARTE-REACT-002"
    source_references = tuple(
        f"HIST-{index:03d}"
        for index in range(4, 14)
    )

    campaign_repository = Mock()
    campaign_repository.get_by_id.return_value = SimpleNamespace(
        id=campaign_id,
        status="active",
        template_name="reactivacion_respirarte",
        template_language="es_CO",
    )

    contacts = tuple(
        SimpleNamespace(
            id=f"contact-{index}",
            campaign_id=campaign_id,
            source_reference=source_reference,
            status="eligible",
            retryable=False,
            provider_message_id=None,
        )
        for index, source_reference in enumerate(
            source_references,
            start=1,
        )
    )

    contact_repository = Mock()
    contact_repository.get_by_id.side_effect = contacts

    dispatcher = Mock()
    dispatcher.dispatch.side_effect = tuple(
        ReactivationTemplateDispatchResult(
            outcome="accepted",
            contact_id=contact.id,
            provider_message_id=f"wamid.batch.{index}",
            retryable=False,
        )
        for index, contact in enumerate(contacts, start=1)
    )

    authorization = SimpleNamespace(
        campaign_id=campaign_id,
        source_references=source_references,
    )

    result = asyncio.run(
        run_reactivation_batch(
            authorization=authorization,
            contact_ids=tuple(
                contact.id
                for contact in contacts
            ),
            campaign_repository=campaign_repository,
            contact_repository=contact_repository,
            dispatcher=dispatcher,
            send_authorized=True,
        )
    )

    assert result.total == 10
    assert result.accepted == 10
    assert result.failed == 0
    assert dispatcher.dispatch.call_count == 10
