from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import app.services.reactivation_campaign_service as service_module


RECEIVED_AT = datetime(
    2026,
    7,
    30,
    13,
    0,
    tzinfo=timezone.utc,
)


class FakeResponseRepository:
    def __init__(self, *, contact=None):
        self.contact = contact
        self.find_calls = []
        self.record_calls = []

    def find_latest_response_candidate_by_phone(
        self,
        *,
        phone_e164,
    ):
        self.find_calls.append(
            {"phone_e164": phone_e164}
        )
        return self.contact

    def record_response_event(self, **kwargs):
        self.record_calls.append(kwargs)

        return SimpleNamespace(
            id="response-event-001",
            contact_id=kwargs["contact_id"],
            inbound_whatsapp_message_id=(
                kwargs["inbound_whatsapp_message_id"]
            ),
            response_classification=(
                kwargs["response_classification"]
            ),
            response_safe_reason=kwargs["response_safe_reason"],
            global_opt_out_requested=(
                kwargs["global_opt_out_requested"]
            ),
            campaign_opt_out_requested=(
                kwargs["campaign_opt_out_requested"]
            ),
            requires_human_escalation=(
                kwargs["requires_human_escalation"]
            ),
            received_at=kwargs["received_at"],
        )


def build_service(repository):
    service_class = getattr(
        service_module,
        "ReactivationCampaignResponseService",
    )
    return service_class(repository)


def classification_value(result) -> str:
    value = result.response_classification
    return getattr(value, "value", value)


def safe_reason_value(result) -> str | None:
    value = result.response_safe_reason

    if value is None:
        return None

    return getattr(value, "value", value)


def test_campaign_refusal_is_correlated_classified_and_persisted():
    repository = FakeResponseRepository(
        contact=SimpleNamespace(id="contact-001")
    )
    service = build_service(repository)

    result = service.process_inbound_response(
        phone_e164=" 573000000001 ",
        inbound_whatsapp_message_id=" wamid.inbound-001 ",
        message="Gracias, pero no me interesa",
        received_at=RECEIVED_AT,
    )

    assert result is not None
    assert result.contact_id == "contact-001"
    assert result.response_event_id == "response-event-001"
    assert (
        classification_value(result)
        == "campaign_refusal"
    )
    assert result.global_opt_out_requested is False
    assert result.campaign_opt_out_requested is True
    assert result.requires_human_escalation is False
    assert safe_reason_value(result) == "explicit_refusal"

    assert repository.find_calls == [
        {"phone_e164": "573000000001"}
    ]
    assert repository.record_calls == [
        {
            "contact_id": "contact-001",
            "inbound_whatsapp_message_id": (
                "wamid.inbound-001"
            ),
            "response_classification": "campaign_refusal",
            "response_safe_reason": "explicit_refusal",
            "global_opt_out_requested": False,
            "campaign_opt_out_requested": True,
            "requires_human_escalation": False,
            "received_at": RECEIVED_AT,
        }
    ]


def test_unmatched_phone_returns_none_without_persistence():
    repository = FakeResponseRepository(contact=None)
    service = build_service(repository)

    result = service.process_inbound_response(
        phone_e164="573000000099",
        inbound_whatsapp_message_id="wamid.inbound-099",
        message="No me interesa",
        received_at=RECEIVED_AT,
    )

    assert result is None
    assert repository.find_calls == [
        {"phone_e164": "573000000099"}
    ]
    assert repository.record_calls == []


def test_global_stop_request_remains_distinct_from_campaign_refusal():
    repository = FakeResponseRepository(
        contact=SimpleNamespace(id="contact-002")
    )
    service = build_service(repository)

    result = service.process_inbound_response(
        phone_e164="573000000002",
        inbound_whatsapp_message_id="wamid.inbound-002",
        message="No autorizo estos mensajes",
        received_at=RECEIVED_AT,
    )

    assert result is not None
    assert classification_value(result) == "global_opt_out"
    assert result.global_opt_out_requested is True
    assert result.campaign_opt_out_requested is True
    assert result.requires_human_escalation is False


def test_positive_contact_request_exposes_safe_escalation_action():
    repository = FakeResponseRepository(
        contact=SimpleNamespace(id="contact-003")
    )
    service = build_service(repository)

    result = service.process_inbound_response(
        phone_e164="573000000003",
        inbound_whatsapp_message_id="wamid.inbound-003",
        message="Sí, me interesa. Por favor llámenme.",
        received_at=RECEIVED_AT,
    )

    assert result is not None
    assert (
        classification_value(result)
        == "positive_contact_request"
    )
    assert result.global_opt_out_requested is False
    assert result.campaign_opt_out_requested is False
    assert result.requires_human_escalation is True
    assert safe_reason_value(result) == "contact_requested"


def test_processing_result_does_not_expose_raw_message():
    repository = FakeResponseRepository(
        contact=SimpleNamespace(id="contact-004")
    )
    service = build_service(repository)

    raw_message = "Sí, me interesa. Por favor llámenme."

    result = service.process_inbound_response(
        phone_e164="573000000004",
        inbound_whatsapp_message_id="wamid.inbound-004",
        message=raw_message,
        received_at=RECEIVED_AT,
    )

    assert result is not None

    serialized = result.model_dump(mode="json")

    assert raw_message not in str(serialized)
    assert "message" not in serialized
    assert "raw_message" not in serialized
    assert "message_text" not in serialized
    assert "response_text" not in serialized


def test_missing_identifiers_are_rejected_before_repository_calls():
    repository = FakeResponseRepository(
        contact=SimpleNamespace(id="contact-005")
    )
    service = build_service(repository)

    invalid_cases = (
        {
            "phone_e164": "",
            "inbound_whatsapp_message_id": "wamid.inbound-005",
        },
        {
            "phone_e164": "573000000005",
            "inbound_whatsapp_message_id": "",
        },
    )

    for invalid_case in invalid_cases:
        with pytest.raises(ValueError):
            service.process_inbound_response(
                phone_e164=invalid_case["phone_e164"],
                inbound_whatsapp_message_id=(
                    invalid_case[
                        "inbound_whatsapp_message_id"
                    ]
                ),
                message="Respuesta",
                received_at=RECEIVED_AT,
            )

    assert repository.find_calls == []
    assert repository.record_calls == []
