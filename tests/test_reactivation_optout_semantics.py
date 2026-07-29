import pytest

from app.models.message import IncomingMessage
from app.graph.graph import process_message
from app.services import reactivation_domain


def classify(
    message,
    *,
    reactivation_context=True,
):
    return (
        reactivation_domain
        .classify_reactivation_response_semantics(
            message,
            reactivation_context=reactivation_context,
        )
    )


@pytest.mark.parametrize(
    ("message", "safe_reason"),
    [
        (
            "No me escriban más",
            "stop_contact_request",
        ),
        (
            "Por favor eliminen mi número",
            "stop_contact_request",
        ),
        (
            "Bórrenme de su lista",
            "stop_contact_request",
        ),
        (
            "Déjenme en paz",
            "stop_contact_request",
        ),
        (
            "No autorizo estos mensajes",
            "privacy_objection",
        ),
        (
            "¿De dónde sacaron mis datos? No me contacten",
            "privacy_objection",
        ),
        (
            "No quiero recibir publicidad",
            "explicit_refusal",
        ),
        (
            "No deseo más mensajes",
            "explicit_refusal",
        ),
    ],
)
def test_strong_stop_requests_are_optout_in_any_context(
    message,
    safe_reason,
):
    for reactivation_context in (False, True):
        decision = classify(
            message,
            reactivation_context=reactivation_context,
        )

        assert decision.is_opt_out is True
        assert decision.safe_reason.value == safe_reason


@pytest.mark.parametrize(
    "message",
    [
        "No gracias",
        "No me interesa",
        "Gracias pero no",
        "Paso",
        "No deseo el servicio",
    ],
)
def test_soft_refusal_is_optout_in_reactivation_context(
    message,
):
    decision = classify(
        message,
        reactivation_context=True,
    )

    assert decision.is_opt_out is True
    assert decision.safe_reason.value == "explicit_refusal"
    assert decision.requires_human_escalation is False


@pytest.mark.parametrize(
    "message",
    [
        "No gracias",
        "No me interesa",
        "Gracias pero no",
    ],
)
def test_soft_refusal_is_not_global_optout_without_campaign_context(
    message,
):
    decision = classify(
        message,
        reactivation_context=False,
    )

    assert decision.is_opt_out is False
    assert decision.safe_reason is None


@pytest.mark.parametrize(
    "message",
    [
        "No me escrivan mas",
        "Borrenme d la lista",
        "No autirizo estos mensajes",
        "No msj porfa",
        "NO NO NO ME ESCRIBAN MÁS",
        "No me escriban 😡😡",
    ],
)
def test_typographical_abbreviated_and_emphatic_rejection(
    message,
):
    decision = classify(
        message,
        reactivation_context=True,
    )

    assert decision.is_opt_out is True
    assert decision.safe_reason is not None


@pytest.mark.parametrize(
    "message",
    [
        "Dejen de molestar",
        "Déjenme quieto",
        "No jodan más",
        "Qué fastidio, no vuelvan a escribir",
        "Váyanse al carajo, no me contacten",
    ],
)
def test_colombian_or_hostile_rejection_is_optout(
    message,
):
    decision = classify(
        message,
        reactivation_context=True,
    )

    assert decision.is_opt_out is True
    assert decision.safe_reason.value == "hostile_rejection"
    assert decision.requires_human_escalation is False


@pytest.mark.parametrize(
    "message",
    [
        "El servicio fue malo y necesito que me respondan",
        "Tengo una queja y quiero una solución",
        "Me cobraron algo incorrecto, por favor revisen",
        "Necesito hablar con la doctora por una inconformidad",
    ],
)
def test_complaint_requesting_solution_does_not_imply_optout(
    message,
):
    decision = classify(
        message,
        reactivation_context=True,
    )

    assert decision.complaint_detected is True
    assert decision.requires_human_escalation is True
    assert decision.is_opt_out is False
    assert decision.safe_reason is None


@pytest.mark.parametrize(
    "message",
    [
        "El servicio fue malo, solucionen eso y no me escriban más",
        "Tengo una queja. Borren mi número de su lista",
        "Quiero hablar con la doctora y no vuelvan a contactarme",
    ],
)
def test_complaint_with_stop_request_is_escalation_and_optout(
    message,
):
    decision = classify(
        message,
        reactivation_context=True,
    )

    assert decision.complaint_detected is True
    assert decision.requires_human_escalation is True
    assert decision.is_opt_out is True
    assert decision.safe_reason is not None


def test_semantic_decision_does_not_store_raw_hostile_message():
    raw_message = "Váyanse al carajo, no me contacten"

    decision = classify(
        raw_message,
        reactivation_context=True,
    )

    serialized = decision.model_dump()

    assert raw_message not in serialized.values()
    assert "raw_message" not in serialized
    assert "message" not in serialized
    assert serialized["safe_reason"] == "hostile_rejection"


def test_strong_new_stop_request_reaches_existing_optout_flow():
    message = IncomingMessage(
        telefono="573000000001",
        mensaje="No autorizo estos mensajes",
    )

    result = process_message(message)

    assert result.intent == "optout"
    assert result.next_action == "confirm_optout"
    assert result.nuevo_estado == "ST_OPTOUT"
    assert result.opt_out is True


def test_typographical_stop_request_reaches_existing_optout_flow():
    message = IncomingMessage(
        telefono="573000000001",
        mensaje="No me escrivan mas",
    )

    result = process_message(message)

    assert result.intent == "optout"
    assert result.next_action == "confirm_optout"
    assert result.nuevo_estado == "ST_OPTOUT"
    assert result.opt_out is True


def test_voice_transcript_uses_same_semantic_contract():
    transcript = "No gracias, no me interesa"

    decision = classify(
        transcript,
        reactivation_context=True,
    )

    assert decision.is_opt_out is True
    assert decision.safe_reason.value == "explicit_refusal"
