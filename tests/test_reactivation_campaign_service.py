from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID
from zoneinfo import ZoneInfo

from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationCampaignContact,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
)
from app.services.reactivation_campaign_service import (
    ReactivationCampaignContactService,
    ReactivationDeliveryClaim,
)


NOW = datetime(
    2026,
    7,
    29,
    15,
    0,
    tzinfo=ZoneInfo("America/Bogota"),
)


def build_contact(**updates):
    values = {
        "id": "contact-1",
        "campaign_id": "campaign-1",
        "source_reference": "historico-001",
        "name": "Paciente de prueba",
        "phone_original": "300 000 0001",
        "phone_e164": "573000000001",
        "attended": True,
        "authorization_status": (
            ReactivationAuthorizationStatus.APPROVED
        ),
        "doctor_review_status": (
            ReactivationDoctorReviewStatus.APPROVED
        ),
        "status": ReactivationContactStatus.ELIGIBLE,
        "idempotency_key": "reactivation:key-001",
        "retryable": False,
        "attempt_count": 0,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(updates)
    return ReactivationCampaignContact(**values)


def test_claim_for_delivery_uses_atomic_repository_claim():
    repository = Mock()

    def persist_claim(**kwargs):
        return build_contact(
            status=ReactivationContactStatus.PENDING,
            claim_token=kwargs["claim_token"],
            attempt_count=1,
            last_attempt_at=NOW,
        )

    repository.try_claim_delivery.side_effect = persist_claim
    service = ReactivationCampaignContactService(repository)

    claim = service.claim_for_delivery(
        contact_id="contact-1",
        lease_seconds=90,
    )

    assert claim is not None
    assert isinstance(claim, ReactivationDeliveryClaim)
    assert claim.contact.id == "contact-1"

    UUID(claim.token)

    repository.try_claim_delivery.assert_called_once_with(
        contact_id="contact-1",
        claim_token=claim.token,
        lease_seconds=90,
    )


def test_claim_for_delivery_returns_none_when_repository_rejects_claim():
    repository = Mock()
    repository.try_claim_delivery.return_value = None
    service = ReactivationCampaignContactService(repository)

    claim = service.claim_for_delivery(
        contact_id="contact-1",
    )

    assert claim is None
    repository.try_claim_delivery.assert_called_once()


def test_record_accepted_uses_claim_token_and_provider_id():
    accepted_contact = build_contact(
        status=ReactivationContactStatus.ACCEPTED,
        claim_token=None,
        provider_message_id="wamid.reactivation.001",
        retryable=False,
        accepted_at=NOW,
    )

    repository = Mock()
    repository.mark_accepted.return_value = accepted_contact
    service = ReactivationCampaignContactService(repository)

    claim = ReactivationDeliveryClaim(
        contact=build_contact(
            status=ReactivationContactStatus.PENDING,
            claim_token="claim-1",
        ),
        token="claim-1",
    )

    result = service.record_accepted(
        claim=claim,
        provider_message_id="wamid.reactivation.001",
    )

    assert result is accepted_contact
    assert result.status == ReactivationContactStatus.ACCEPTED

    repository.mark_accepted.assert_called_once_with(
        contact_id="contact-1",
        claim_token="claim-1",
        provider_message_id="wamid.reactivation.001",
    )


def test_record_failed_uses_claim_and_preserves_retry_decision():
    failed_contact = build_contact(
        status=ReactivationContactStatus.FAILED,
        claim_token=None,
        retryable=True,
        failed_at=NOW,
        last_error_category="network_error",
    )

    repository = Mock()
    repository.mark_failed.return_value = failed_contact
    service = ReactivationCampaignContactService(repository)

    claim = ReactivationDeliveryClaim(
        contact=build_contact(
            status=ReactivationContactStatus.PENDING,
            claim_token="claim-1",
        ),
        token="claim-1",
    )

    result = service.record_failed(
        claim=claim,
        error_category="network_error",
        retryable=True,
    )

    assert result is failed_contact
    assert result.retryable is True

    repository.mark_failed.assert_called_once_with(
        contact_id="contact-1",
        claim_token="claim-1",
        error_category="network_error",
        retryable=True,
    )


def test_record_provider_status_delegates_wamid_correlation():
    delivered_contact = build_contact(
        status=ReactivationContactStatus.DELIVERED,
        provider_message_id="wamid.reactivation.001",
        delivered_at=NOW,
    )

    repository = Mock()
    repository.apply_provider_status.return_value = (
        delivered_contact
    )
    service = ReactivationCampaignContactService(repository)

    result = service.record_provider_status(
        provider_message_id="wamid.reactivation.001",
        provider_status="delivered",
        occurred_at=NOW,
        error_category=None,
    )

    assert result is delivered_contact

    repository.apply_provider_status.assert_called_once_with(
        provider_message_id="wamid.reactivation.001",
        provider_status="delivered",
        occurred_at=NOW,
        error_category=None,
    )


def test_record_provider_status_returns_none_for_unmatched_wamid():
    repository = Mock()
    repository.apply_provider_status.return_value = None
    service = ReactivationCampaignContactService(repository)

    result = service.record_provider_status(
        provider_message_id="wamid.unknown",
        provider_status="read",
        occurred_at=NOW,
        error_category=None,
    )

    assert result is None


def test_delivery_claim_requires_matching_contact_token_when_present():
    contact = build_contact(
        status=ReactivationContactStatus.PENDING,
        claim_token="claim-contact",
    )

    try:
        ReactivationDeliveryClaim(
            contact=contact,
            token="claim-other",
        )
    except ValueError as error:
        assert "claim token" in str(error).lower()
    else:
        raise AssertionError(
            "A mismatched persisted claim token must be rejected."
        )


def test_service_module_is_persistence_agnostic():
    source = Path(
        "app/services/reactivation_campaign_service.py"
    ).read_text(encoding="utf-8").lower()

    forbidden_fragments = [
        "sqlalchemy",
        "insert into",
        "update reactivation_",
        "delete from",
        "engine.begin",
        "from app.db.session",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source
