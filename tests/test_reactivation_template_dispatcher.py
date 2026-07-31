import asyncio
from unittest.mock import Mock

import pytest

from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationCampaignContact,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
)
from app.services.reactivation_campaign_service import (
    ReactivationDeliveryClaim,
)
from app.services.reactivation_template_dispatcher import (
    ReactivationTemplateDispatchConfig,
    ReactivationTemplateDispatchRequest,
    ReactivationTemplateDispatcher,
)


def build_contact(**updates) -> ReactivationCampaignContact:
    values = {
        "id": "contact-1",
        "campaign_id": "campaign-1",
        "source_reference": "historico-001",
        "name": "Contacto de prueba",
        "phone_original": "300 000 0001",
        "phone_e164": "573000000001",
        "attended": True,
        "authorization_status": (
            ReactivationAuthorizationStatus.APPROVED
        ),
        "doctor_review_status": (
            ReactivationDoctorReviewStatus.APPROVED
        ),
        "status": ReactivationContactStatus.PENDING,
        "idempotency_key": "reactivation:key-001",
        "retryable": False,
        "attempt_count": 1,
        "claim_token": "claim-1",
    }
    values.update(updates)
    return ReactivationCampaignContact(**values)


def test_successful_dispatch_uses_approved_template_and_records_acceptance():
    contact_service = Mock()
    sender = Mock(
        return_value={
            "messages": [
                {
                    "id": "wamid.reactivation.001",
                }
            ]
        }
    )

    claimed_contact = build_contact()
    claim = ReactivationDeliveryClaim(
        contact=claimed_contact,
        token="claim-1",
    )

    accepted_contact = build_contact(
        status=ReactivationContactStatus.ACCEPTED,
        provider_message_id="wamid.reactivation.001",
        claim_token=None,
    )

    contact_service.claim_for_delivery.return_value = claim
    contact_service.record_accepted.return_value = accepted_contact

    dispatcher = ReactivationTemplateDispatcher(
        contact_service=contact_service,
        send_template=sender,
        config=ReactivationTemplateDispatchConfig(
            enabled=True,
        ),
        lease_seconds=120,
    )

    result = asyncio.run(
        dispatcher.dispatch(
            contact_id="contact-1",
        )
    )

    assert result.outcome == "accepted"
    assert result.contact_id == "contact-1"
    assert result.provider_message_id == "wamid.reactivation.001"
    assert result.retryable is False

    contact_service.claim_for_delivery.assert_called_once_with(
        contact_id="contact-1",
        lease_seconds=120,
    )

    sender.assert_called_once_with(
        to="573000000001",
        template_name="reactivacion_respirarte",
        language_code="es_CO",
        body_parameters=["Contacto de prueba"],
    )

    contact_service.record_accepted.assert_called_once_with(
        claim=claim,
        provider_message_id="wamid.reactivation.001",
    )

def test_dispatcher_is_disabled_by_default_without_claiming_or_sending():
    contact_service = Mock()
    sender = Mock()

    config = ReactivationTemplateDispatchConfig()

    assert config.enabled is False
    assert config.template_name == "reactivacion_respirarte"
    assert config.template_language == "es_CO"

    dispatcher = ReactivationTemplateDispatcher(
        contact_service=contact_service,
        send_template=sender,
        config=config,
    )

    result = asyncio.run(
        dispatcher.dispatch(
            contact_id="contact-1",
        )
    )

    assert result.outcome == "disabled"
    assert result.contact_id == "contact-1"
    assert result.provider_message_id is None
    assert result.retryable is False

    contact_service.claim_for_delivery.assert_not_called()
    contact_service.record_accepted.assert_not_called()
    contact_service.record_failed.assert_not_called()
    sender.assert_not_called()

@pytest.mark.parametrize(
    ("template_name", "template_language"),
    [
        ("revision_humana", "es_CO"),
        ("reactivacion_respirarte", "es_ES"),
    ],
)
def test_rejects_non_approved_template_contract(
    template_name,
    template_language,
):
    contact_service = Mock()
    sender = Mock()

    with pytest.raises(
        ValueError,
        match="approved reactivation template contract",
    ):
        ReactivationTemplateDispatcher(
            contact_service=contact_service,
            send_template=sender,
            config=ReactivationTemplateDispatchConfig(
                enabled=True,
                template_name=template_name,
                template_language=template_language,
            ),
        )

    contact_service.claim_for_delivery.assert_not_called()
    sender.assert_not_called()

def test_dispatch_accepts_safe_request_model():
    contact_service = Mock()
    sender = Mock(
        return_value={
            "messages": [
                {
                    "id": "wamid.reactivation.request",
                }
            ]
        }
    )

    claimed_contact = build_contact(
        id="contact-request",
        claim_token="claim-request",
    )
    claim = ReactivationDeliveryClaim(
        contact=claimed_contact,
        token="claim-request",
    )
    accepted_contact = build_contact(
        id="contact-request",
        status=ReactivationContactStatus.ACCEPTED,
        provider_message_id="wamid.reactivation.request",
        claim_token=None,
    )

    contact_service.claim_for_delivery.return_value = claim
    contact_service.record_accepted.return_value = accepted_contact

    request = ReactivationTemplateDispatchRequest(
        contact_id="  contact-request  ",
    )

    assert request.contact_id == "contact-request"

    dispatcher = ReactivationTemplateDispatcher(
        contact_service=contact_service,
        send_template=sender,
        config=ReactivationTemplateDispatchConfig(
            enabled=True,
        ),
    )

    result = asyncio.run(
        dispatcher.dispatch(
            request=request,
        )
    )

    assert result.outcome == "accepted"
    assert result.contact_id == "contact-request"

    contact_service.claim_for_delivery.assert_called_once_with(
        contact_id="contact-request",
        lease_seconds=120,
    )

def test_malformed_persisted_phone_is_not_sent():
    contact_service = Mock()
    sender = Mock(
        return_value={
            "messages": [
                {
                    "id": "wamid.must-not-be-used",
                }
            ]
        }
    )

    claimed_contact = build_contact(
        phone_e164="57300ABC0001",
        claim_token="claim-invalid-phone",
    )
    claim = ReactivationDeliveryClaim(
        contact=claimed_contact,
        token="claim-invalid-phone",
    )
    failed_contact = build_contact(
        phone_e164="57300ABC0001",
        status=ReactivationContactStatus.FAILED,
        claim_token=None,
        retryable=False,
        last_error_category="invalid_template_contact_data",
    )

    contact_service.claim_for_delivery.return_value = claim
    contact_service.record_failed.return_value = failed_contact

    dispatcher = ReactivationTemplateDispatcher(
        contact_service=contact_service,
        send_template=sender,
        config=ReactivationTemplateDispatchConfig(
            enabled=True,
        ),
    )

    result = asyncio.run(
        dispatcher.dispatch(
            contact_id="contact-1",
        )
    )

    assert result.outcome == "failed"
    assert result.contact_id == "contact-1"
    assert result.error_category == "invalid_template_contact_data"
    assert result.retryable is False

    contact_service.record_failed.assert_called_once_with(
        claim=claim,
        error_category="invalid_template_contact_data",
        retryable=False,
    )
    contact_service.record_accepted.assert_not_called()
    sender.assert_not_called()

def test_failure_persistence_conflict_is_not_reported_as_persisted_failed():
    contact_service = Mock()
    sender = Mock(
        side_effect=TimeoutError(
            "sensitive timeout transport detail"
        )
    )

    claimed_contact = build_contact(
        claim_token="claim-timeout-conflict",
    )
    claim = ReactivationDeliveryClaim(
        contact=claimed_contact,
        token="claim-timeout-conflict",
    )

    contact_service.claim_for_delivery.return_value = claim
    contact_service.record_failed.return_value = None

    dispatcher = ReactivationTemplateDispatcher(
        contact_service=contact_service,
        send_template=sender,
        config=ReactivationTemplateDispatchConfig(
            enabled=True,
        ),
    )

    result = asyncio.run(
        dispatcher.dispatch(
            contact_id="contact-1",
        )
    )

    assert result.outcome == "failure_state_persistence_failed"
    assert result.contact_id == "contact-1"
    assert result.provider_message_id is None
    assert result.error_category == "network_timeout"
    assert result.retryable is False

    contact_service.record_failed.assert_called_once_with(
        claim=claim,
        error_category="network_timeout",
        retryable=True,
    )
    contact_service.record_accepted.assert_not_called()
    sender.assert_called_once()

    assert "sensitive timeout" not in repr(result)
    assert "transport detail" not in repr(result)

@pytest.mark.parametrize(
    (
        "accepted_side_effect",
        "accepted_return_value",
        "expected_error_category",
    ),
    [
        (
            RuntimeError(
                "sensitive acceptance persistence detail"
            ),
            None,
            "acceptance_persistence_error",
        ),
        (
            None,
            None,
            "acceptance_persistence_conflict",
        ),
    ],
)
def test_acceptance_persistence_ambiguity_attempts_terminal_failure(
    accepted_side_effect,
    accepted_return_value,
    expected_error_category,
):
    contact_service = Mock()
    sender = Mock(
        return_value={
            "messages": [
                {
                    "id": "wamid.reactivation.ambiguous",
                }
            ]
        }
    )

    claimed_contact = build_contact(
        claim_token="claim-ambiguous",
    )
    claim = ReactivationDeliveryClaim(
        contact=claimed_contact,
        token="claim-ambiguous",
    )

    contact_service.claim_for_delivery.return_value = claim
    contact_service.record_accepted.side_effect = (
        accepted_side_effect
    )
    contact_service.record_accepted.return_value = (
        accepted_return_value
    )
    contact_service.record_failed.return_value = build_contact(
        status=ReactivationContactStatus.FAILED,
        claim_token=None,
        retryable=False,
        last_error_category=expected_error_category,
    )

    dispatcher = ReactivationTemplateDispatcher(
        contact_service=contact_service,
        send_template=sender,
        config=ReactivationTemplateDispatchConfig(
            enabled=True,
        ),
    )

    result = asyncio.run(
        dispatcher.dispatch(
            contact_id="contact-1",
        )
    )

    assert result.outcome == "delivery_outcome_ambiguous"
    assert result.contact_id == "contact-1"
    assert (
        result.provider_message_id
        == "wamid.reactivation.ambiguous"
    )
    assert result.error_category == expected_error_category
    assert result.retryable is False

    contact_service.record_failed.assert_called_once_with(
        claim=claim,
        error_category=expected_error_category,
        retryable=False,
    )
    sender.assert_called_once()

    assert "sensitive acceptance" not in repr(result)
    assert "persistence detail" not in repr(result)
