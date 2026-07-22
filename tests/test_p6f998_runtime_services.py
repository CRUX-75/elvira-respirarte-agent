from app.services.approved_service_catalog import (
    get_active_approved_services,
    get_approved_service_by_id,
    get_unavailable_service_response,
    unavailable_service_requires_escalation,
)
from app.services.intent import classify_intent
from app.services.kb import (
    _build_services_context,
    get_kb_context,
)


def test_p6f998_active_runtime_catalog_uses_approved_services():
    active_ids = {
        row["service_id"]
        for row in get_active_approved_services()
    }

    assert active_ids == {
        "SRV-01",
        "SRV-03",
        "SRV-04",
        "SRV-06",
        "SRV-07",
    }


def test_p6f998_dynamic_oximetry_is_exact_without_database_change():
    result = get_kb_context(
        None,
        intent="servicios",
        message="Necesito información sobre oximetría dinámica",
        estado_actual="ST_GENERAL",
    )

    assert result["matched_service_id"] == "SRV-07"
    assert result["matched_service_field"] == "service_name"
    assert result["service_grounding_status"] == "exact"
    assert "orden médica" in result["kb_context"].lower()


def test_p6f998_stale_database_rows_are_replaced_or_removed():
    context = _build_services_context(
        [
            {
                "service_id": "SRV-01",
                "service_name": "Terapia Respiratoria",
                "techniques": "Oxigenoterapia, oximetría",
                "is_active": True,
            },
            {
                "service_id": "SRV-05",
                "service_name": "Curso Profiláctico Materno",
                "public_answer_short": "Sí, está disponible.",
                "is_active": True,
            },
        ]
    ).lower()

    assert "oxigenoterapia" not in context
    assert "curso" not in context
    assert "terapia respiratoria" in context


def test_p6f998_unavailable_services_have_deterministic_intent():
    messages = [
        "¿Ofrecen oxigenoterapia domiciliaria?",
        "Necesito oxígeno domiciliario",
        "¿Tienen curso psicoprofiláctico materno?",
        "Quiero el curso para gestantes",
    ]

    for message in messages:
        assert (
            classify_intent(message)
            == "servicio_no_disponible"
        )


def test_p6f998_urgency_still_wins_for_critical_message():
    assert (
        classify_intent(
            "Necesito oxigenoterapia y no puedo respirar"
        )
        == "urgencia"
    )


def test_p6f998_unavailable_responses_are_service_specific():
    oxygen = get_unavailable_service_response(
        "Necesito oxigenoterapia domiciliaria"
    )
    course = get_unavailable_service_response(
        "¿Tienen curso psicoprofiláctico?"
    )
    tracheostomy = get_unavailable_service_response(
        "Paciente traqueostomizado"
    )

    assert "institución" in oxygen
    assert "multidisciplinario" in course
    assert "especialista" in tracheostomy


def test_p6f998_dynamic_service_keeps_clinical_requirements():
    service = get_approved_service_by_id("SRV-07")

    assert service is not None
    assert service["is_active"] is True
    assert service["escalation_required"] is True
    assert "orden médica" in service["public_answer_short"]


def test_p6f998_only_tracheostomy_requires_automatic_escalation():
    assert unavailable_service_requires_escalation(
        "Paciente traqueostomizado"
    ) is True

    assert unavailable_service_requires_escalation(
        "Necesito oxigenoterapia domiciliaria"
    ) is False

    assert unavailable_service_requires_escalation(
        "Quiero el curso psicoprofiláctico"
    ) is False
