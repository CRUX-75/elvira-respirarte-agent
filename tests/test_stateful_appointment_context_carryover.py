from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


class FakeElviraResult:
    def __init__(
        self,
        *,
        intent: str,
        nuevo_estado: str,
        respuesta: str = "Respuesta de prueba",
        next_action: str | None = None,
        fecha_solicitada: str | None = None,
        fecha_solicitada_texto: str | None = None,
        slots_candidatos: list[str] | None = None,
        mensaje_original: str | None = None,
        is_weekend: bool | None = None,
        is_colombia_holiday: bool | None = None,
        es_dia_disponible: bool | None = None,
        colombia_holiday_name: str | None = None,
        opt_out: bool = False,
    ):
        self.intent = intent
        self.nuevo_estado = nuevo_estado
        self.respuesta = respuesta
        self.next_action = next_action
        self.state_reason = "test_reason"
        self.router_version = "test-router"
        self.state_machine_version = "test-state-machine"
        self.kb_used = False
        self.escalation_required = False
        self.opt_out = opt_out
        self.fecha_solicitada = fecha_solicitada
        self.fecha_solicitada_texto = fecha_solicitada_texto
        self.slots_candidatos = slots_candidatos or []
        self.mensaje_original = mensaje_original
        self.is_weekend = is_weekend
        self.is_colombia_holiday = is_colombia_holiday
        self.es_dia_disponible = es_dia_disponible
        self.colombia_holiday_name = colombia_holiday_name

    def model_dump(self):
        return {
            "intent": self.intent,
            "nuevo_estado": self.nuevo_estado,
            "respuesta": self.respuesta,
            "next_action": self.next_action,
            "state_reason": self.state_reason,
            "router_version": self.router_version,
            "state_machine_version": self.state_machine_version,
            "kb_used": self.kb_used,
            "escalation_required": self.escalation_required,
            "fecha_solicitada": self.fecha_solicitada,
            "fecha_solicitada_texto": self.fecha_solicitada_texto,
            "slots_candidatos": self.slots_candidatos,
            "mensaje_original": self.mensaje_original,
            "is_weekend": self.is_weekend,
            "is_colombia_holiday": self.is_colombia_holiday,
            "es_dia_disponible": self.es_dia_disponible,
            "colombia_holiday_name": self.colombia_holiday_name,
        }


def _patch_stateful_dependencies(monkeypatch, *, fake_result, patient):
    calls = {
        "save_interaction": None,
        "update_patient_state": None,
        "update_patient_last_message": None,
        "update_patient_appointment_context": None,
        "clear_patient_appointment_context": None,
        "appointment_service_call": None,
    }

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre: patient,
    )

    monkeypatch.setattr(
        main,
        "traced_process_message",
        lambda process_func, message: fake_result,
    )

    monkeypatch.setattr(
        main,
        "save_interaction",
        lambda **kwargs: calls.__setitem__("save_interaction", kwargs),
    )

    monkeypatch.setattr(
        main,
        "update_patient_state",
        lambda **kwargs: calls.__setitem__("update_patient_state", kwargs),
    )

    monkeypatch.setattr(
        main,
        "update_patient_last_message",
        lambda **kwargs: calls.__setitem__("update_patient_last_message", kwargs),
    )

    monkeypatch.setattr(
        main,
        "update_patient_appointment_context",
        lambda **kwargs: calls.__setitem__("update_patient_appointment_context", kwargs),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "clear_patient_appointment_context",
        lambda **kwargs: calls.__setitem__("clear_patient_appointment_context", kwargs),
        raising=False,
    )

    class FakePostgresAppointmentRequestRepository:
        def __init__(self, engine):
            self.engine = engine

    class FakeAppointmentRequestService:
        def __init__(self, repository):
            self.repository = repository

        def create_or_reuse_active_request(self, **kwargs):
            calls["appointment_service_call"] = kwargs
            return SimpleNamespace(
                id_solicitud="SOL-TEST-001",
                estado_solicitud="pendiente_confirmacion",
                source_interaction_id=kwargs.get("source_interaction_id"),
                fecha_solicitada=kwargs.get("fecha_solicitada"),
                franja_solicitada=kwargs.get("franja_solicitada"),
            )

    monkeypatch.setattr(main, "PostgresAppointmentRequestRepository", FakePostgresAppointmentRequestRepository)
    monkeypatch.setattr(main, "AppointmentRequestService", FakeAppointmentRequestService)

    return calls


def test_stateful_endpoint_captures_context_after_fecha_cita(monkeypatch):
    fake_result = FakeElviraResult(
        intent="fecha_cita",
        nuevo_estado="ST_CITA_FRANJA",
        next_action="ask_appointment_time_window",
        fecha_solicitada="2026-05-29",
        fecha_solicitada_texto="viernes 29 de mayo",
        slots_candidatos=["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
        is_weekend=False,
        is_colombia_holiday=False,
        es_dia_disponible=True,
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FECHA",
        "opt_out": False,
        "appointment_context": None,
    }

    calls = _patch_stateful_dependencies(monkeypatch, fake_result=fake_result, patient=patient)

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "El viernes",
        },
    )

    assert response.status_code == 200

    assert calls["update_patient_appointment_context"] == {
        "telefono": "573001112233",
        "appointment_context": {
            "fecha_solicitada": "2026-05-29",
            "fecha_solicitada_texto": "viernes 29 de mayo",
            "slots_candidatos": ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
        },
    }

    assert calls["appointment_service_call"] is None
    assert calls["clear_patient_appointment_context"] is None


def test_stateful_endpoint_replaces_existing_context_with_new_absolute_date(monkeypatch):
    fake_result = FakeElviraResult(
        intent="fecha_cita",
        nuevo_estado="ST_CITA_FRANJA",
        next_action="ask_appointment_time_window",
        fecha_solicitada="2026-07-23",
        fecha_solicitada_texto="jueves 23 de julio",
        slots_candidatos=[
            "3:00 p. m.–5:00 p. m.",
            "5:00 p. m.–7:00 p. m.",
        ],
        is_weekend=False,
        is_colombia_holiday=False,
        es_dia_disponible=True,
        mensaje_original="jueves 23 de julio de 2026",
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": {
            "fecha_solicitada": "2026-07-16",
            "fecha_solicitada_texto": "jueves 16 de julio",
            "slots_candidatos": [
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
        },
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "jueves 23 de julio de 2026",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["fecha_solicitada"] == "2026-07-23"
    assert body["fecha_solicitada_texto"] == "jueves 23 de julio"
    assert body["slots_candidatos"] == [
        "3:00 p. m.–5:00 p. m.",
        "5:00 p. m.–7:00 p. m.",
    ]

    assert calls["update_patient_appointment_context"] == {
        "telefono": "573001112233",
        "appointment_context": {
            "fecha_solicitada": "2026-07-23",
            "fecha_solicitada_texto": "jueves 23 de julio",
            "slots_candidatos": [
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
        },
    }

    assert calls["appointment_service_call"] is None
    assert calls["clear_patient_appointment_context"] is None


def test_stateful_endpoint_applies_context_before_hora_cita_persistence(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada=None,
        slots_candidatos=[],
        mensaje_original="la primera franja está bien",
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": {
            "fecha_solicitada": "2026-05-29",
            "fecha_solicitada_texto": "viernes 29 de mayo",
            "slots_candidatos": ["3:00 p. m.–5:00 p. m.", "5:00 p. m.–7:00 p. m."],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
        },
    }

    calls = _patch_stateful_dependencies(monkeypatch, fake_result=fake_result, patient=patient)

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "la primera franja está bien",
        },
    )

    assert response.status_code == 200
    body = response.json()

    print(body)
    assert body["appointment_request_decision"]["should_persist"] is True

    # The runtime decision currently selects one concrete candidate slot.




def test_stateful_endpoint_authoritative_context_overrides_contradictory_hora_cita_state(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-30",
        fecha_solicitada_texto="sábado 30 de mayo",
        slots_candidatos=["existing"],
        es_dia_disponible=False,
        is_weekend=True,
        is_colombia_holiday=True,
        colombia_holiday_name="Corpus Christi",
        mensaje_original="la segunda",
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": {
            "fecha_solicitada": "2026-05-29",
            "fecha_solicitada_texto": "viernes 29 de mayo",
            "slots_candidatos": [
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
        },
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "la segunda",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["fecha_solicitada"] == "2026-05-29"
    assert body["fecha_solicitada_texto"] == "viernes 29 de mayo"
    assert body["slots_candidatos"] == [
        "3:00 p. m.–5:00 p. m.",
        "5:00 p. m.–7:00 p. m.",
    ]
    assert body["es_dia_disponible"] is True
    assert body["is_weekend"] is False
    assert body["is_colombia_holiday"] is False
    assert body["colombia_holiday_name"] is None

    assert body["appointment_request_decision"]["should_persist"] is True
    assert body["appointment_request_decision"]["fecha_solicitada"] == "2026-05-29"
    assert body["appointment_request_decision"]["franja_solicitada"] == "5:00 p. m.–7:00 p. m."
    assert body["appointment_request"] is not None
    assert body["appointment_request"]["fecha_solicitada"] == "2026-05-29"
    assert body["appointment_request"]["franja_solicitada"] == "5:00 p. m.–7:00 p. m."

    assert calls["appointment_service_call"]["fecha_solicitada"] == "2026-05-29"
    assert calls["appointment_service_call"]["franja_solicitada"] == "5:00 p. m.–7:00 p. m."
    assert calls["clear_patient_appointment_context"] == {"telefono": "573001112233"}



def test_stateful_endpoint_returns_exact_hour_franja_confirmation_copy(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada=None,
        slots_candidatos=[],
        mensaje_original="se puede a las 5?",
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": {
            "fecha_solicitada": "2026-05-29",
            "fecha_solicitada_texto": "viernes 29 de mayo",
            "slots_candidatos": [
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
        },
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "se puede a las 5?",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["appointment_request_decision"]["should_persist"] is False
    assert (
        body["appointment_request_decision"]["reason"]
        == "requires_exact_hour_franja_confirmation"
    )
    assert (
        body["appointment_request_decision"]["franja_solicitada"]
        == "5:00 p. m.–7:00 p. m."
    )
    assert body["appointment_request"] is None

    assert body["nuevo_estado"] == "ST_CITA_FRANJA"
    assert body["persisted_state"] == "ST_CITA_FRANJA"
    assert body["next_action"] == "ask_confirm_exact_hour_as_slot"
    assert calls["save_interaction"]["nuevo_estado"] == "ST_CITA_FRANJA"
    assert calls["save_interaction"]["next_action"] == "ask_confirm_exact_hour_as_slot"
    assert calls["update_patient_state"]["nuevo_estado"] == "ST_CITA_FRANJA"

    assert "atenciones domiciliarias se manejan por franjas" in body["respuesta"]
    assert "no por una hora exacta garantizada" in body["respuesta"]
    assert "la franja disponible es" in body["respuesta"]
    assert "5:00 p. m. a 7:00 p. m." in body["respuesta"]
    assert "Desea que registre esa franja" in body["respuesta"]
    # assert eliminado: nuevo texto no incluye ¿Cuál le queda mejor? cuando franja es específica
    assert "¿Desea que registre esa franja?" not in body["respuesta"]

    assert calls["appointment_service_call"] is None
    assert calls["clear_patient_appointment_context"] is None
    assert "la franja disponible es" in calls["save_interaction"]["respuesta_elvira"]


def test_stateful_endpoint_persists_after_pending_exact_hour_franja_confirmation(monkeypatch):
    fake_result = FakeElviraResult(
        intent="general",
        nuevo_estado="ST_CITA_FRANJA",
        next_action="answer_general",
        fecha_solicitada=None,
        slots_candidatos=[],
        mensaje_original="si",
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": {
            "fecha_solicitada": "2026-06-01",
            "fecha_solicitada_texto": "lunes 1 de junio",
            "slots_candidatos": [
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
            "pending_exact_hour_franja": "5:00 p. m.–7:00 p. m.",
            "pending_exact_hour_text": "se puede a las 5?",
            "pending_exact_hour_requires_confirmation": True,
        },
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "si",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["intent"] == "general"
    assert body["nuevo_estado"] == "ST_CITA_FRANJA"
    assert body["next_action"] == "answer_general"
    assert body["persisted_state"] == "ST_CITA_FRANJA"

    assert body["appointment_request_decision"]["should_persist"] is False
    assert body["appointment_request_decision"]["reason"] == "skipped_non_appointment_intent"
    assert body["appointment_request"] is None

    assert calls["appointment_service_call"] is None
    assert calls["clear_patient_appointment_context"] is None
    assert "queda registrada" not in body["respuesta"].lower()




def test_stateful_endpoint_rejects_vague_register_that_franja_after_exact_hour_guard(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada=None,
        slots_candidatos=[],
        mensaje_original="sí, registre esa franja",
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": {
            "fecha_solicitada": "2026-06-09",
            "fecha_solicitada_texto": "martes 9 de junio",
            "slots_candidatos": [
                "3:00 p. m.–5:00 p. m.",
                "5:00 p. m.–7:00 p. m.",
            ],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
            "pending_exact_hour_franja": "3:00 p. m.–5:00 p. m.",
            "pending_exact_hour_text": "no se podria a las 4?",
            "pending_exact_hour_requires_confirmation": True,
        },
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "sí, registre esa franja",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["nuevo_estado"] == "ST_CITA_FRANJA"
    assert body["persisted_state"] == "ST_CITA_FRANJA"
    assert body["next_action"] == "ask_confirm_exact_hour_as_slot"
    assert body["state_reason"] == "unsupported_slot_selection_guard"

    assert body["appointment_request_decision"]["should_persist"] is False
    assert body["appointment_request_decision"]["reason"] == "skipped_unsupported_slot_selection"
    assert body["appointment_request"] is None

    assert "queda registrada" not in body["respuesta"].lower()
    assert "3:00 p. m. a 5:00 p. m." in body["respuesta"]
    assert "5:00 p. m. a 7:00 p. m." in body["respuesta"]
    assert "indíquenos su preferencia de franja" not in body["respuesta"]
    # assert eliminado: nuevo texto dinámico no lista franjas cuando slots vacíos
    # assert eliminado: idem

    assert calls["appointment_service_call"] is None


def test_stateful_endpoint_pending_request_exact_hour_followup_does_not_register_again(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-06-09",
        slots_candidatos=["3:00 p. m.–5:00 p. m."],
        mensaje_original="Pueden llegar a las 4",
    )
    fake_result.estado_actual = "ST_CITA_PENDIENTE"
    fake_result.estado_anterior = "ST_CITA_PENDIENTE"
    fake_result.appointment_context = {
        "fecha_solicitada": "2026-06-09",
        "fecha_solicitada_texto": "martes 9 de junio",
        "slots_candidatos": ["3:00 p. m.–5:00 p. m."],
        "franja_solicitada": "3:00 p. m.–5:00 p. m.",
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
    }

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_PENDIENTE",
        "opt_out": False,
        "appointment_context": fake_result.appointment_context,
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "Pueden llegar a las 4",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["nuevo_estado"] == "ST_CITA_PENDIENTE"
    assert body["persisted_state"] == "ST_CITA_PENDIENTE"
    assert body["next_action"] == "none"
    assert body["state_reason"] == "registered_request_exact_hour_followup"

    assert body["appointment_request_decision"]["should_persist"] is False
    assert body["appointment_request"] is None
    assert calls["appointment_service_call"] is None

    assert "queda registrada su solicitud" not in body["respuesta"].lower()
    assert "su solicitud ya quedó registrada" in body["respuesta"].lower()
    assert "3:00 p. m. a 5:00 p. m." in body["respuesta"]
    assert "hora exacta" in body["respuesta"].lower()
    assert "Dra. D’Aleman" in body["respuesta"]

def test_stateful_endpoint_missing_date_does_not_claim_request_was_registered(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        respuesta=(
            "Perfecto, queda registrada su solicitud para esa franja. "
            "La Dra. D’Aleman revisará la disponibilidad."
        ),
        next_action="confirm_appointment_request",
        fecha_solicitada=None,
        slots_candidatos=["3:00 p. m.–5:00 p. m."],
        mensaje_original="En la primera franja",
        is_weekend=False,
        is_colombia_holiday=False,
        es_dia_disponible=True,
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": None,
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "En la primera franja",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["appointment_request_decision"]["should_persist"] is False
    assert (
        body["appointment_request_decision"]["reason"]
        == "skipped_missing_fecha_solicitada"
    )
    assert body["appointment_request"] is None
    assert calls["appointment_service_call"] is None

    assert body["nuevo_estado"] == "ST_CITA_FECHA"
    assert body["persisted_state"] == "ST_CITA_FECHA"
    assert body["next_action"] == "ask_preferred_date"
    assert body["state_reason"] == "missing_appointment_date_guard"

    response_text = body["respuesta"].lower()

    assert "queda registrada" not in response_text
    assert "registrada su solicitud" not in response_text
    assert "la doctora revisará" not in response_text
    assert "dra. d’aleman revisará" not in response_text
    assert "qué día" in response_text or "fecha" in response_text

    assert calls["save_interaction"]["nuevo_estado"] == "ST_CITA_FECHA"
    assert calls["save_interaction"]["next_action"] == "ask_preferred_date"
    assert calls["update_patient_state"]["nuevo_estado"] == "ST_CITA_FECHA"


def test_stateful_endpoint_persists_single_wednesday_slot_from_carried_context(
    monkeypatch,
):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada=None,
        slots_candidatos=[],
        mensaje_original="sí, esa franja",
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": {
            "fecha_solicitada": "2026-06-17",
            "fecha_solicitada_texto": "miércoles 17 de junio",
            "slots_candidatos": ["3:00 p. m.–6:00 p. m."],
            "es_dia_disponible": True,
            "is_weekend": False,
            "is_colombia_holiday": False,
            "colombia_holiday_name": None,
        },
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "sí, esa franja",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["fecha_solicitada"] == "2026-06-17"
    assert body["fecha_solicitada_texto"] == "miércoles 17 de junio"
    assert body["slots_candidatos"] == ["3:00 p. m.–6:00 p. m."]
    assert body["es_dia_disponible"] is True
    assert body["is_weekend"] is False
    assert body["is_colombia_holiday"] is False

    decision = body["appointment_request_decision"]

    assert decision["should_persist"] is True
    assert decision["reason"] == "allowed_hora_cita_ready_for_human_review"
    assert decision["fecha_solicitada"] == "2026-06-17"
    assert decision["franja_solicitada"] == "3:00 p. m.–6:00 p. m."

    assert body["appointment_request"] is not None
    assert body["appointment_request"]["fecha_solicitada"] == "2026-06-17"
    assert (
        body["appointment_request"]["franja_solicitada"]
        == "3:00 p. m.–6:00 p. m."
    )

    assert calls["appointment_service_call"]["fecha_solicitada"] == "2026-06-17"
    assert (
        calls["appointment_service_call"]["franja_solicitada"]
        == "3:00 p. m.–6:00 p. m."
    )
    assert calls["clear_patient_appointment_context"] == {
        "telefono": "573001112233"
    }


def test_stateful_endpoint_weekend_guard_blocks_sunday_persistence(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        respuesta=(
            "Perfecto, queda registrada su solicitud para esa franja. "
            "La Dra. D’Aleman revisará la disponibilidad."
        ),
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-17",
        fecha_solicitada_texto="domingo 17 de mayo",
        slots_candidatos=[],
        mensaje_original="sí, esa franja",
        is_weekend=True,
        is_colombia_holiday=False,
        es_dia_disponible=False,
        colombia_holiday_name=None,
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": None,
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "sí, esa franja",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["fecha_solicitada"] == "2026-05-17"
    assert body["fecha_solicitada_texto"] == "domingo 17 de mayo"
    assert body["is_weekend"] is True
    assert body["is_colombia_holiday"] is False
    assert body["es_dia_disponible"] is False
    assert body["slots_candidatos"] == []

    decision = body["appointment_request_decision"]

    assert decision["should_persist"] is False
    assert decision["reason"] == "skipped_weekend"
    assert decision["fecha_solicitada"] == "2026-05-17"

    assert body["appointment_request"] is None
    assert calls["appointment_service_call"] is None

    assert body["nuevo_estado"] == "ST_CITA_FECHA"
    assert body["persisted_state"] == "ST_CITA_FECHA"
    assert body["next_action"] == "ask_preferred_date"
    assert body["state_reason"] == "unavailable_date_guard"

    response_text = body["respuesta"].lower()

    assert "queda registrada" not in response_text
    assert "registrada su solicitud" not in response_text
    assert "la doctora revisará" not in response_text
    assert "dra. d’aleman revisará" not in response_text
    assert "domingo 17 de mayo" in response_text
    assert "no tenemos atención domiciliaria disponible" in response_text
    assert "otro día" in response_text

    assert calls["save_interaction"]["nuevo_estado"] == "ST_CITA_FECHA"
    assert calls["save_interaction"]["next_action"] == "ask_preferred_date"
    assert (
        calls["save_interaction"]["state_reason"]
        == "unavailable_date_guard"
    )
    assert (
        "no tenemos atención domiciliaria disponible"
        in calls["save_interaction"]["respuesta_elvira"].lower()
    )
    assert calls["update_patient_state"]["nuevo_estado"] == "ST_CITA_FECHA"

    assert calls["update_patient_appointment_context"] is None
    assert calls["clear_patient_appointment_context"] is None


def test_stateful_endpoint_weekend_guard_blocks_saturday_persistence(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        respuesta=(
            "Perfecto, queda registrada su solicitud para esa franja. "
            "La Dra. D’Aleman revisará la disponibilidad."
        ),
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-30",
        fecha_solicitada_texto="sábado 30 de mayo",
        slots_candidatos=[],
        mensaje_original="sí, esa franja",
        is_weekend=True,
        is_colombia_holiday=False,
        es_dia_disponible=False,
        colombia_holiday_name=None,
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": None,
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "sí, esa franja",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["fecha_solicitada"] == "2026-05-30"
    assert body["fecha_solicitada_texto"] == "sábado 30 de mayo"
    assert body["is_weekend"] is True
    assert body["is_colombia_holiday"] is False
    assert body["es_dia_disponible"] is False
    assert body["slots_candidatos"] == []

    decision = body["appointment_request_decision"]

    assert decision["should_persist"] is False
    assert decision["reason"] == "skipped_weekend"
    assert decision["fecha_solicitada"] == "2026-05-30"

    assert body["appointment_request"] is None
    assert calls["appointment_service_call"] is None

    assert body["nuevo_estado"] == "ST_CITA_FECHA"
    assert body["persisted_state"] == "ST_CITA_FECHA"
    assert body["next_action"] == "ask_preferred_date"
    assert body["state_reason"] == "unavailable_date_guard"

    response_text = body["respuesta"].lower()

    assert "queda registrada" not in response_text
    assert "registrada su solicitud" not in response_text
    assert "la doctora revisará" not in response_text
    assert "dra. d’aleman revisará" not in response_text
    assert "sábado 30 de mayo" in response_text
    assert "no tenemos atención domiciliaria disponible" in response_text
    assert "otro día" in response_text

    assert calls["save_interaction"]["nuevo_estado"] == "ST_CITA_FECHA"
    assert calls["save_interaction"]["next_action"] == "ask_preferred_date"
    assert (
        calls["save_interaction"]["state_reason"]
        == "unavailable_date_guard"
    )
    assert (
        "no tenemos atención domiciliaria disponible"
        in calls["save_interaction"]["respuesta_elvira"].lower()
    )
    assert calls["update_patient_state"]["nuevo_estado"] == "ST_CITA_FECHA"

    assert calls["update_patient_appointment_context"] is None
    assert calls["clear_patient_appointment_context"] is None


def test_stateful_endpoint_holiday_guard_blocks_persistence_and_names_holiday(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        respuesta=(
            "Perfecto, queda registrada su solicitud para esa franja. "
            "La Dra. D’Aleman revisará la disponibilidad."
        ),
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-18",
        fecha_solicitada_texto="lunes 18 de mayo",
        slots_candidatos=[],
        mensaje_original="sí, esa franja",
        is_weekend=False,
        is_colombia_holiday=True,
        es_dia_disponible=False,
        colombia_holiday_name="Ascensión de Jesús",
    )

    patient = {
        "id": "patient-001",
        "telefono": "573001112233",
        "nombre": "Paciente Test",
        "estado_actual": "ST_CITA_FRANJA",
        "opt_out": False,
        "appointment_context": None,
    }

    calls = _patch_stateful_dependencies(
        monkeypatch,
        fake_result=fake_result,
        patient=patient,
    )

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "sí, esa franja",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["fecha_solicitada"] == "2026-05-18"
    assert body["fecha_solicitada_texto"] == "lunes 18 de mayo"
    assert body["is_weekend"] is False
    assert body["is_colombia_holiday"] is True
    assert body["colombia_holiday_name"] == "Ascensión de Jesús"
    assert body["es_dia_disponible"] is False
    assert body["slots_candidatos"] == []

    decision = body["appointment_request_decision"]

    assert decision["should_persist"] is False
    assert decision["reason"] == "skipped_colombia_holiday"
    assert decision["fecha_solicitada"] == "2026-05-18"

    assert body["appointment_request"] is None
    assert calls["appointment_service_call"] is None

    assert body["nuevo_estado"] == "ST_CITA_FECHA"
    assert body["persisted_state"] == "ST_CITA_FECHA"
    assert body["next_action"] == "ask_preferred_date"
    assert body["state_reason"] == "unavailable_date_guard"

    response_text = body["respuesta"].lower()

    assert "queda registrada" not in response_text
    assert "registrada su solicitud" not in response_text
    assert "la doctora revisará" not in response_text
    assert "dra. d’aleman revisará" not in response_text
    assert "lunes 18 de mayo" in response_text
    assert "ascensión de jesús" in response_text
    assert "no tenemos atención domiciliaria disponible" in response_text
    assert "otro día" in response_text

    assert calls["save_interaction"]["nuevo_estado"] == "ST_CITA_FECHA"
    assert calls["save_interaction"]["next_action"] == "ask_preferred_date"
    assert (
        calls["save_interaction"]["state_reason"]
        == "unavailable_date_guard"
    )
    assert (
        "ascensión de jesús"
        in calls["save_interaction"]["respuesta_elvira"].lower()
    )
    assert calls["update_patient_state"]["nuevo_estado"] == "ST_CITA_FECHA"

    assert calls["update_patient_appointment_context"] is None
    assert calls["clear_patient_appointment_context"] is None


def test_stateful_endpoint_carries_wednesday_context_across_two_calls(

    monkeypatch,
):
    import json

    from app.graph import nodes as graph_nodes
    from app.repositories import patients as patient_repository

    expected_context = {
        "fecha_solicitada": "2026-07-22",
        "fecha_solicitada_texto": "miércoles 22 de julio",
        "slots_candidatos": ["3:00 p. m.–6:00 p. m."],
        "es_dia_disponible": True,
        "is_weekend": False,
        "is_colombia_holiday": False,
        "colombia_holiday_name": None,
    }

    class StatefulResult:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class StatefulPatientConnection:
        def __init__(self):
            self.patient = {
                "id": "patient-wednesday-two-turns",
                "telefono": "573009890090",
                "nombre": "Swagger Miércoles Carryover",
                "estado_actual": "ST_CITA_FECHA",
                "opt_out": False,
                "appointment_context": None,
            }
            self.patient_reads = []

        def execute(self, statement, params=None):
            sql = " ".join(str(statement).split())
            params = params or {}

            if "SELECT" in sql and "FROM patients" in sql:
                row = dict(self.patient)

                # Reproduce la proyección SQL real. El contexto solo estará
                # disponible si la consulta del repositorio lo selecciona.
                if "SELECT *" not in sql and "appointment_context" not in sql:
                    row.pop("appointment_context", None)

                self.patient_reads.append(dict(row))

                return StatefulResult(
                    SimpleNamespace(_mapping=row),
                )

            if "INSERT INTO patients" in sql:
                return StatefulResult(
                    SimpleNamespace(_mapping=dict(self.patient)),
                )

            if (
                "UPDATE patients" in sql
                and "appointment_context = NULL" in sql
            ):
                self.patient["appointment_context"] = None
                return StatefulResult()

            if (
                "UPDATE patients" in sql
                and "appointment_context" in sql
                and "appointment_context = NULL" not in sql
            ):
                stored_context = params["appointment_context"]

                if isinstance(stored_context, str):
                    stored_context = json.loads(stored_context)

                self.patient["appointment_context"] = stored_context
                return StatefulResult()

            if (
                "UPDATE patients" in sql
                and "estado_actual = :nuevo_estado" in sql
            ):
                self.patient["estado_actual"] = params["nuevo_estado"]

                if "opt_out" in params:
                    self.patient["opt_out"] = params["opt_out"]

                return StatefulResult()

            if (
                "UPDATE patients" in sql
                and "last_message_at = NOW()" in sql
            ):
                return StatefulResult()

            raise AssertionError(
                f"SQL no esperado en prueba stateful: {sql}"
            )

    class StatefulPatientEngine:
        def __init__(self):
            self.conn = StatefulPatientConnection()

        def begin(self):
            return self

        def __enter__(self):
            return self.conn

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_engine = StatefulPatientEngine()

    monkeypatch.setattr(
        patient_repository,
        "engine",
        fake_engine,
    )

    # El endpoint utiliza las funciones reales del repositorio de pacientes.
    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        patient_repository.get_or_create_patient_by_phone,
    )
    monkeypatch.setattr(
        main,
        "update_patient_state",
        patient_repository.update_patient_state,
    )
    monkeypatch.setattr(
        main,
        "update_patient_last_message",
        patient_repository.update_patient_last_message,
    )
    monkeypatch.setattr(
        main,
        "update_patient_appointment_context",
        patient_repository.update_patient_appointment_context,
    )
    monkeypatch.setattr(
        main,
        "clear_patient_appointment_context",
        patient_repository.clear_patient_appointment_context,
    )

    def fake_classify_intent(*, message, current_state):
        if message == "Quiero agendar una cita para el miércoles 22 de julio de 2026":
            return "cita"

        if message == "sí, esa franja":
            return "hora_cita"

        raise AssertionError(
            f"Mensaje inesperado para clasificación: {message!r}"
        )

    def fake_generate_llm_response(state):
        state.respuesta = "Respuesta de prueba"
        return state

    monkeypatch.setattr(
        graph_nodes,
        "classify_intent",
        fake_classify_intent,
    )
    monkeypatch.setattr(
        graph_nodes,
        "generate_llm_response",
        fake_generate_llm_response,
    )
    monkeypatch.setattr(
        graph_nodes.settings,
        "kb_runtime_enabled",
        False,
    )

    processed_states = []

    def real_traced_process_message(process_func, message):
        processed_states.append(message.estado_actual)
        return process_func(message)

    monkeypatch.setattr(
        main,
        "traced_process_message",
        real_traced_process_message,
    )
    monkeypatch.setattr(
        main,
        "save_interaction",
        lambda **kwargs: None,
    )

    appointment_calls = []

    class FakePostgresAppointmentRequestRepository:
        def __init__(self, engine):
            self.engine = engine

    class FakeAppointmentRequestService:
        def __init__(self, repository):
            self.repository = repository

        def create_or_reuse_active_request(self, **kwargs):
            appointment_calls.append(kwargs)

            return SimpleNamespace(
                id_solicitud="SOL-WEDNESDAY-TWO-TURNS",
                estado_solicitud="pendiente_confirmacion",
                source_interaction_id=kwargs.get(
                    "source_interaction_id"
                ),
                fecha_solicitada=kwargs.get("fecha_solicitada"),
                franja_solicitada=kwargs.get("franja_solicitada"),
            )

    monkeypatch.setattr(
        main,
        "PostgresAppointmentRequestRepository",
        FakePostgresAppointmentRequestRepository,
    )
    monkeypatch.setattr(
        main,
        "AppointmentRequestService",
        FakeAppointmentRequestService,
    )

    first_response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573009890090",
            "nombre": "Swagger Miércoles Carryover",
            "mensaje": "Quiero agendar una cita para el miércoles 22 de julio de 2026",
        },
    )

    assert first_response.status_code == 200

    first_body = first_response.json()

    assert first_body["nuevo_estado"] == "ST_CITA_FRANJA"
    assert first_body["fecha_solicitada"] == "2026-07-22"
    assert (
        first_body["fecha_solicitada_texto"]
        == "miércoles 22 de julio"
    )
    assert first_body["slots_candidatos"] == [
        "3:00 p. m.–6:00 p. m."
    ]

    # El primer POST debe guardar estado y contexto.
    assert fake_engine.conn.patient["estado_actual"] == "ST_CITA_FRANJA"
    context_after_first_turn = fake_engine.conn.patient["appointment_context"]
    assert appointment_calls == []

    second_response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573009890090",
            "nombre": "Swagger Miércoles Carryover",
            "mensaje": "sí, esa franja",
        },
    )

    assert second_response.status_code == 200

    second_body = second_response.json()

    assert processed_states == [
        "ST_CITA_FECHA",
        "ST_CITA_FRANJA",
    ]

    assert context_after_first_turn == expected_context

    # El segundo POST debe leer el contexto escrito por el primero.
    assert len(fake_engine.conn.patient_reads) == 2
    assert (
        fake_engine.conn.patient_reads[1]["appointment_context"]
        == expected_context
    )

    assert second_body["fecha_solicitada"] == "2026-07-22"
    assert (
        second_body["fecha_solicitada_texto"]
        == "miércoles 22 de julio"
    )
    assert second_body["slots_candidatos"] == [
        "3:00 p. m.–6:00 p. m."
    ]

    decision = second_body["appointment_request_decision"]

    assert decision["should_persist"] is True
    assert (
        decision["reason"]
        == "allowed_hora_cita_ready_for_human_review"
    )
    assert decision["fecha_solicitada"] == "2026-07-22"
    assert (
        decision["franja_solicitada"]
        == "3:00 p. m.–6:00 p. m."
    )

    assert second_body["nuevo_estado"] == "ST_CITA_PENDIENTE"
    assert second_body["persisted_state"] == "ST_CITA_PENDIENTE"
    assert second_body["appointment_request"] is not None

    assert len(appointment_calls) == 1
    assert appointment_calls[0]["fecha_solicitada"] == "2026-07-22"
    assert (
        appointment_calls[0]["franja_solicitada"]
        == "3:00 p. m.–6:00 p. m."
    )

    assert fake_engine.conn.patient["appointment_context"] is None
