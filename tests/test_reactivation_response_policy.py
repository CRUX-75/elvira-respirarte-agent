import app.services.reactivation_domain as reactivation_domain


def decide(message: str):
    policy = getattr(
        reactivation_domain,
        "decide_reactivation_response",
    )
    return policy(message)


def classification_value(decision) -> str:
    value = decision.response_classification
    return getattr(value, "value", value)


def safe_reason_value(decision) -> str | None:
    value = decision.response_safe_reason

    if value is None:
        return None

    return getattr(value, "value", value)


def test_strong_stop_request_is_global_and_campaign_optout():
    decision = decide("No autorizo estos mensajes")

    assert classification_value(decision) == "global_opt_out"
    assert decision.global_opt_out_requested is True
    assert decision.campaign_opt_out_requested is True
    assert decision.requires_human_escalation is False
    assert safe_reason_value(decision) is not None


def test_soft_reactivation_refusal_is_not_global_optout():
    decision = decide("Gracias, pero no me interesa")

    assert classification_value(decision) == "campaign_refusal"
    assert decision.global_opt_out_requested is False
    assert decision.campaign_opt_out_requested is True
    assert decision.requires_human_escalation is False
    assert safe_reason_value(decision) == "explicit_refusal"


def test_positive_contact_request_requires_human_followup():
    decision = decide(
        "Sí, me interesa. Por favor llámenme."
    )

    assert (
        classification_value(decision)
        == "positive_contact_request"
    )
    assert decision.global_opt_out_requested is False
    assert decision.campaign_opt_out_requested is False
    assert decision.requires_human_escalation is True
    assert safe_reason_value(decision) == "contact_requested"


def test_complaint_without_stop_request_escalates_without_optout():
    decision = decide(
        "Me cobraron algo incorrecto, por favor revisen."
    )

    assert classification_value(decision) == "complaint"
    assert decision.global_opt_out_requested is False
    assert decision.campaign_opt_out_requested is False
    assert decision.requires_human_escalation is True
    assert safe_reason_value(decision) == "complaint"


def test_ambiguous_response_does_not_create_destructive_actions():
    decision = decide("¿Quién habla?")

    assert classification_value(decision) == "ambiguous"
    assert decision.global_opt_out_requested is False
    assert decision.campaign_opt_out_requested is False
    assert decision.requires_human_escalation is False
    assert safe_reason_value(decision) is None


def test_complaint_with_stop_request_escalates_and_opts_out():
    decision = decide(
        "Tengo una queja y no vuelvan a contactarme."
    )

    assert classification_value(decision) == "global_opt_out"
    assert decision.global_opt_out_requested is True
    assert decision.campaign_opt_out_requested is True
    assert decision.requires_human_escalation is True
    assert safe_reason_value(decision) is not None


def test_policy_decision_does_not_expose_raw_message():
    decision = decide(
        "Sí, me interesa. Por favor llámenme."
    )

    serialized = decision.model_dump(mode="json")

    assert "message" not in serialized
    assert "raw_message" not in serialized
    assert "message_text" not in serialized
    assert "response_text" not in serialized
