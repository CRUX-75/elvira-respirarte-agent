import asyncio
import importlib
from datetime import datetime, timezone
from types import SimpleNamespace


RECEIVED_AT = datetime(
    2026,
    7,
    30,
    13,
    30,
    tzinfo=timezone.utc,
)


def runtime_function():
    module = importlib.import_module(
        "app.services.reactivation_response_runtime"
    )
    return getattr(
        module,
        "process_reactivation_response_best_effort",
    )


class FakeResponseService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def process_inbound_response(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class RecordingWriter:
    def __init__(self, *, explode=False):
        self.explode = explode
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)

        if self.explode:
            raise RuntimeError(
                "secret patient and provider information"
            )


def response_result(
    *,
    classification,
    safe_reason=None,
    global_opt_out=False,
    campaign_opt_out=False,
    escalation=False,
):
    return SimpleNamespace(
        contact_id="contact-001",
        response_event_id="response-event-001",
        inbound_whatsapp_message_id="wamid.inbound-001",
        response_classification=classification,
        response_safe_reason=safe_reason,
        global_opt_out_requested=global_opt_out,
        campaign_opt_out_requested=campaign_opt_out,
        requires_human_escalation=escalation,
        received_at=RECEIVED_AT,
    )


def run_runtime(
    *,
    service_result,
    global_writer=None,
    escalation_writer=None,
    message="Respuesta de prueba",
):
    return asyncio.run(
        runtime_function()(
            phone_e164="573000000001",
            inbound_whatsapp_message_id=(
                "wamid.inbound-001"
            ),
            message=message,
            received_at=RECEIVED_AT,
            response_service=FakeResponseService(
                service_result
            ),
            global_opt_out_writer=global_writer,
            escalation_writer=escalation_writer,
        )
    )


def test_unmatched_response_is_ignored_without_side_effects():
    global_writer = RecordingWriter()
    escalation_writer = RecordingWriter()

    result = run_runtime(
        service_result=None,
        global_writer=global_writer,
        escalation_writer=escalation_writer,
    )

    assert result == {
        "status": "reactivation_response_ignored",
        "response_matched": False,
        "response_classification": None,
        "global_opt_out_requested": False,
        "human_escalation_required": False,
        "actions_failed": 0,
    }
    assert global_writer.calls == []
    assert escalation_writer.calls == []


def test_campaign_refusal_does_not_create_global_optout():
    global_writer = RecordingWriter()
    escalation_writer = RecordingWriter()

    result = run_runtime(
        service_result=response_result(
            classification="campaign_refusal",
            safe_reason="explicit_refusal",
            campaign_opt_out=True,
        ),
        global_writer=global_writer,
        escalation_writer=escalation_writer,
    )

    assert result["status"] == "reactivation_response_processed"
    assert result["response_classification"] == (
        "campaign_refusal"
    )
    assert result["global_opt_out_requested"] is False
    assert result["human_escalation_required"] is False
    assert global_writer.calls == []
    assert escalation_writer.calls == []


def test_global_stop_request_calls_only_global_optout_writer():
    global_writer = RecordingWriter()
    escalation_writer = RecordingWriter()

    result = run_runtime(
        service_result=response_result(
            classification="global_opt_out",
            safe_reason="privacy_objection",
            global_opt_out=True,
            campaign_opt_out=True,
        ),
        global_writer=global_writer,
        escalation_writer=escalation_writer,
    )

    assert result["global_opt_out_requested"] is True
    assert result["human_escalation_required"] is False
    assert result["actions_failed"] == 0

    assert global_writer.calls == [
        {
            "phone_e164": "573000000001",
            "inbound_whatsapp_message_id": (
                "wamid.inbound-001"
            ),
            "response_event_id": "response-event-001",
            "safe_reason": "privacy_objection",
        }
    ]
    assert escalation_writer.calls == []


def test_positive_contact_request_creates_safe_escalation():
    global_writer = RecordingWriter()
    escalation_writer = RecordingWriter()
    raw_message = "Sí, me interesa. Por favor llámenme."

    result = run_runtime(
        service_result=response_result(
            classification="positive_contact_request",
            safe_reason="contact_requested",
            escalation=True,
        ),
        global_writer=global_writer,
        escalation_writer=escalation_writer,
        message=raw_message,
    )

    assert result["global_opt_out_requested"] is False
    assert result["human_escalation_required"] is True
    assert global_writer.calls == []

    assert escalation_writer.calls == [
        {
            "contact_id": "contact-001",
            "phone_e164": "573000000001",
            "inbound_whatsapp_message_id": (
                "wamid.inbound-001"
            ),
            "response_event_id": "response-event-001",
            "escalation_action": (
                "escalate_reactivation_interest"
            ),
            "response_classification": (
                "positive_contact_request"
            ),
            "response_safe_reason": "contact_requested",
            "occurred_at": RECEIVED_AT,
        }
    ]

    assert raw_message not in str(result)
    assert raw_message not in str(escalation_writer.calls)


def test_complaint_with_global_stop_runs_both_safe_actions():
    global_writer = RecordingWriter()
    escalation_writer = RecordingWriter()

    result = run_runtime(
        service_result=response_result(
            classification="global_opt_out",
            safe_reason="stop_contact_request",
            global_opt_out=True,
            campaign_opt_out=True,
            escalation=True,
        ),
        global_writer=global_writer,
        escalation_writer=escalation_writer,
    )

    assert result["global_opt_out_requested"] is True
    assert result["human_escalation_required"] is True
    assert len(global_writer.calls) == 1
    assert len(escalation_writer.calls) == 1
    assert (
        escalation_writer.calls[0]["escalation_action"]
        == "escalate_reactivation_complaint"
    )


def test_side_effect_failures_are_isolated_and_safe():
    global_writer = RecordingWriter(explode=True)
    escalation_writer = RecordingWriter(explode=True)

    result = run_runtime(
        service_result=response_result(
            classification="global_opt_out",
            safe_reason="stop_contact_request",
            global_opt_out=True,
            campaign_opt_out=True,
            escalation=True,
        ),
        global_writer=global_writer,
        escalation_writer=escalation_writer,
    )

    assert result == {
        "status": "reactivation_response_actions_failed",
        "response_matched": True,
        "response_classification": "global_opt_out",
        "global_opt_out_requested": True,
        "human_escalation_required": True,
        "actions_failed": 2,
    }

    assert (
        "secret patient and provider information"
        not in str(result)
    )
