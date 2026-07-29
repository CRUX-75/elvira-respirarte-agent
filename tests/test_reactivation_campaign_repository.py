from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.models.reactivation_campaign import (
    ReactivationAuthorizationStatus,
    ReactivationCampaign,
    ReactivationCampaignContact,
    ReactivationCampaignStatus,
    ReactivationContactStatus,
    ReactivationDoctorReviewStatus,
)
from app.repositories.reactivation_campaigns import (
    ReactivationCampaignContactRepository,
    ReactivationCampaignRepository,
)


NOW = datetime(
    2026,
    7,
    29,
    14,
    0,
    tzinfo=ZoneInfo("America/Bogota"),
)


class FakeMappings:
    def __init__(self, rows):
        self.rows = list(rows)

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


class FakeResult:
    def __init__(self, rows=()):
        self.rows = rows

    def mappings(self):
        return FakeMappings(self.rows)


class FakeConnection:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def execute(self, statement, params):
        self.calls.append(
            (
                str(statement),
                dict(params),
            )
        )

        if not self.responses:
            raise AssertionError(
                "Unexpected repository execute call."
            )

        return self.responses.pop(0)


class FakeBegin:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeEngine:
    def __init__(self, responses):
        self.connection = FakeConnection(responses)

    def begin(self):
        return FakeBegin(self.connection)


def campaign_row(**updates):
    row = {
        "id": "campaign-1",
        "name": "reactivacion_historica_2026",
        "template_name": "reactivacion_respirarte",
        "template_language": "es_CO",
        "status": "draft",
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(updates)
    return row


def contact_row(**updates):
    row = {
        "id": "contact-1",
        "campaign_id": "campaign-1",
        "source_reference": "historico-001",
        "name": "Paciente de prueba",
        "phone_original": "300 000 0001",
        "phone_e164": "573000000001",
        "attended": True,
        "authorization_status": "approved",
        "doctor_review_status": "approved",
        "status": "eligible",
        "exclusion_reasons": [],
        "idempotency_key": "reactivation:key-001",
        "provider_message_id": None,
        "retryable": False,
        "attempt_count": 0,
        "last_error_category": None,
        "claim_token": None,
        "claim_expires_at": None,
        "last_attempt_at": None,
        "accepted_at": None,
        "sent_at": None,
        "delivered_at": None,
        "read_at": None,
        "failed_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(updates)
    return row


def build_campaign():
    return ReactivationCampaign(
        id="campaign-1",
        name="reactivacion_historica_2026",
        template_name="reactivacion_respirarte",
        template_language="es_CO",
        status=ReactivationCampaignStatus.DRAFT,
        created_at=NOW,
        updated_at=NOW,
    )


def build_contact():
    return ReactivationCampaignContact(
        id="contact-1",
        campaign_id="campaign-1",
        source_reference="historico-001",
        name="Paciente de prueba",
        phone_original="300 000 0001",
        phone_e164="573000000001",
        attended=True,
        authorization_status=(
            ReactivationAuthorizationStatus.APPROVED
        ),
        doctor_review_status=(
            ReactivationDoctorReviewStatus.APPROVED
        ),
        status=ReactivationContactStatus.ELIGIBLE,
        idempotency_key="reactivation:key-001",
        created_at=NOW,
        updated_at=NOW,
    )


def test_campaign_create_or_get_returns_inserted_campaign():
    engine = FakeEngine(
        [
            FakeResult([campaign_row()]),
        ]
    )
    repository = ReactivationCampaignRepository(engine)

    persisted = repository.create_or_get(build_campaign())

    assert persisted.id == "campaign-1"
    assert persisted.status == ReactivationCampaignStatus.DRAFT

    sql, params = engine.connection.calls[0]

    assert "INSERT INTO reactivation_campaigns" in sql
    assert "ON CONFLICT (id) DO NOTHING" in sql
    assert params["status"] == "draft"


def test_campaign_create_or_get_loads_existing_after_conflict():
    engine = FakeEngine(
        [
            FakeResult([]),
            FakeResult([campaign_row()]),
        ]
    )
    repository = ReactivationCampaignRepository(engine)

    persisted = repository.create_or_get(build_campaign())

    assert persisted.id == "campaign-1"
    assert len(engine.connection.calls) == 2
    assert "SELECT" in engine.connection.calls[1][0]
    assert "WHERE id = :campaign_id" in engine.connection.calls[1][0]


def test_contact_create_or_get_uses_natural_campaign_phone_key():
    engine = FakeEngine(
        [
            FakeResult([contact_row()]),
        ]
    )
    repository = ReactivationCampaignContactRepository(engine)

    persisted = repository.create_or_get(build_contact())

    assert persisted.id == "contact-1"
    assert persisted.phone_e164 == "573000000001"

    sql, params = engine.connection.calls[0]

    assert (
        "INSERT INTO reactivation_campaign_contacts"
        in sql
    )
    assert "ON CONFLICT (" in sql
    assert "campaign_id" in sql
    assert "phone_e164" in sql
    assert "DO NOTHING" in sql
    assert params["status"] == "eligible"
    assert params["exclusion_reasons"] == "[]"


def test_contact_create_or_get_loads_existing_after_conflict():
    engine = FakeEngine(
        [
            FakeResult([]),
            FakeResult([contact_row()]),
        ]
    )
    repository = ReactivationCampaignContactRepository(engine)

    persisted = repository.create_or_get(build_contact())

    assert persisted.id == "contact-1"
    assert len(engine.connection.calls) == 2

    sql, params = engine.connection.calls[1]

    assert "SELECT" in sql
    assert "campaign_id = :campaign_id" in sql
    assert "phone_e164 = :phone_e164" in sql
    assert params == {
        "campaign_id": "campaign-1",
        "phone_e164": "573000000001",
    }


def test_try_claim_delivery_is_atomic_and_checks_patient_optout():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    contact_row(
                        status="pending",
                        claim_token="claim-1",
                        claim_expires_at=NOW,
                        last_attempt_at=NOW,
                        attempt_count=1,
                    )
                ]
            ),
        ]
    )
    repository = ReactivationCampaignContactRepository(engine)

    claimed = repository.try_claim_delivery(
        contact_id="contact-1",
        claim_token="claim-1",
        lease_seconds=120,
    )

    assert claimed is not None
    assert claimed.status == ReactivationContactStatus.PENDING
    assert claimed.claim_token == "claim-1"
    assert claimed.attempt_count == 1

    sql, params = engine.connection.calls[0]

    assert "UPDATE reactivation_campaign_contacts" in sql
    assert "status = 'pending'" in sql
    assert "attempt_count = attempt_count + 1" in sql
    assert "provider_message_id IS NULL" in sql
    assert "status = 'eligible'" in sql
    assert "status = 'failed'" in sql
    assert "retryable = TRUE" in sql
    assert "claim_expires_at <= NOW()" in sql
    assert "NOT EXISTS" in sql
    assert "FROM patients" in sql
    assert "patients.opt_out = TRUE" in sql
    assert params["lease_seconds"] == 120


def test_try_claim_delivery_returns_none_when_locked_or_ineligible():
    engine = FakeEngine([FakeResult([])])
    repository = ReactivationCampaignContactRepository(engine)

    claimed = repository.try_claim_delivery(
        contact_id="contact-1",
        claim_token="claim-2",
    )

    assert claimed is None


def test_mark_accepted_requires_claim_and_commits_provider_id():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    contact_row(
                        status="accepted",
                        provider_message_id=(
                            "wamid.reactivation.001"
                        ),
                        retryable=False,
                        accepted_at=NOW,
                    )
                ]
            ),
        ]
    )
    repository = ReactivationCampaignContactRepository(engine)

    accepted = repository.mark_accepted(
        contact_id="contact-1",
        claim_token="claim-1",
        provider_message_id="wamid.reactivation.001",
    )

    assert accepted is not None
    assert accepted.status == ReactivationContactStatus.ACCEPTED
    assert accepted.provider_message_id == (
        "wamid.reactivation.001"
    )
    assert accepted.accepted_at == NOW

    sql, _ = engine.connection.calls[0]

    assert "status = 'accepted'" in sql
    assert "provider_message_id = :provider_message_id" in sql
    assert "claim_token = :claim_token" in sql
    assert "claim_token = NULL" in sql
    assert "retryable = FALSE" in sql


def test_mark_failed_preserves_safe_retry_decision():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    contact_row(
                        status="failed",
                        retryable=True,
                        failed_at=NOW,
                        last_error_category="network_error",
                    )
                ]
            ),
        ]
    )
    repository = ReactivationCampaignContactRepository(engine)

    failed = repository.mark_failed(
        contact_id="contact-1",
        claim_token="claim-1",
        error_category="network_error",
        retryable=True,
    )

    assert failed is not None
    assert failed.status == ReactivationContactStatus.FAILED
    assert failed.retryable is True
    assert failed.last_error_category == "network_error"

    sql, params = engine.connection.calls[0]

    assert "claim_token = :claim_token" in sql
    assert "provider_message_id IS NULL" in sql
    assert "claim_token = NULL" in sql
    assert params["retryable"] is True


def test_get_by_provider_message_id_uses_wamid_correlation():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    contact_row(
                        status="delivered",
                        provider_message_id=(
                            "wamid.reactivation.001"
                        ),
                        delivered_at=NOW,
                    )
                ]
            ),
        ]
    )
    repository = ReactivationCampaignContactRepository(engine)

    contact = repository.get_by_provider_message_id(
        "wamid.reactivation.001"
    )

    assert contact is not None
    assert contact.id == "contact-1"

    sql, params = engine.connection.calls[0]

    assert "provider_message_id = :provider_message_id" in sql
    assert params == {
        "provider_message_id": "wamid.reactivation.001",
    }


def test_provider_delivered_status_updates_monotonically_by_wamid():
    engine = FakeEngine(
        [
            FakeResult(
                [
                    contact_row(
                        status="delivered",
                        provider_message_id=(
                            "wamid.reactivation.001"
                        ),
                        retryable=False,
                        delivered_at=NOW,
                    )
                ]
            ),
        ]
    )
    repository = ReactivationCampaignContactRepository(engine)

    delivered = repository.apply_provider_status(
        provider_message_id="wamid.reactivation.001",
        provider_status="delivered",
        occurred_at=NOW,
    )

    assert delivered is not None
    assert delivered.status == ReactivationContactStatus.DELIVERED
    assert delivered.delivered_at == NOW

    sql, params = engine.connection.calls[0]

    assert "provider_message_id = :provider_message_id" in sql
    assert (
        "status IN ('accepted', 'sent', 'delivered', 'failed')"
        in sql
    )
    assert params["occurred_at"] == NOW


def test_out_of_order_sent_callback_cannot_regress_delivered():
    engine = FakeEngine([FakeResult([])])
    repository = ReactivationCampaignContactRepository(engine)

    result = repository.apply_provider_status(
        provider_message_id="wamid.reactivation.001",
        provider_status="sent",
        occurred_at=NOW,
    )

    assert result is None

    sql, _ = engine.connection.calls[0]

    assert (
        "status IN ('accepted', 'sent', 'failed')"
        in sql
    )

    allowed_statuses = sql.split("status IN", 1)[1]
    assert "delivered" not in allowed_statuses
    assert "read" not in allowed_statuses


def test_repository_rejects_invalid_lease_and_provider_status():
    repository = ReactivationCampaignContactRepository(
        FakeEngine([])
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        repository.try_claim_delivery(
            contact_id="contact-1",
            claim_token="claim-1",
            lease_seconds=0,
        )

    with pytest.raises(
        ValueError,
        match="Unsupported WhatsApp provider status",
    ):
        repository.apply_provider_status(
            provider_message_id="wamid.reactivation.001",
            provider_status="unknown",
            occurred_at=NOW,
        )

def test_claim_requires_active_campaign_before_delivery():
    engine = FakeEngine([FakeResult([])])
    repository = ReactivationCampaignContactRepository(engine)

    claimed = repository.try_claim_delivery(
        contact_id="contact-1",
        claim_token="claim-active-guard",
    )

    assert claimed is None

    sql, _ = engine.connection.calls[0]
    normalized_sql = " ".join(sql.split())

    assert "FROM reactivation_campaigns" in normalized_sql
    assert (
        "reactivation_campaigns.id = "
        "reactivation_campaign_contacts.campaign_id"
        in normalized_sql
    )
    assert "reactivation_campaigns.status = 'active'" in (
        normalized_sql
    )

    assert "FROM patients" in normalized_sql
    assert "patients.opt_out = TRUE" in normalized_sql


@pytest.mark.parametrize(
    (
        "provider_status",
        "persisted_status",
        "allowed_current",
    ),
    [
        (
            "sent",
            "sent",
            "status IN ('accepted', 'sent', 'failed')",
        ),
        (
            "delivered",
            "delivered",
            (
                "status IN "
                "('accepted', 'sent', 'delivered', 'failed')"
            ),
        ),
        (
            "read",
            "read",
            (
                "status IN "
                "('accepted', 'sent', 'delivered', 'read', "
                "'failed')"
            ),
        ),
    ],
)
def test_provider_progress_callbacks_can_recover_from_failed(
    provider_status,
    persisted_status,
    allowed_current,
):
    engine = FakeEngine(
        [
            FakeResult(
                [
                    contact_row(
                        status=persisted_status,
                        provider_message_id=(
                            "wamid.reactivation.recovery"
                        ),
                        retryable=False,
                    )
                ]
            )
        ]
    )
    repository = ReactivationCampaignContactRepository(engine)

    result = repository.apply_provider_status(
        provider_message_id=(
            "wamid.reactivation.recovery"
        ),
        provider_status=provider_status,
        occurred_at=NOW,
    )

    assert result is not None
    assert result.status == ReactivationContactStatus(
        persisted_status
    )

    sql, _ = engine.connection.calls[0]
    normalized_sql = " ".join(sql.split())

    assert allowed_current in normalized_sql

