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
    assert "por favor elija una de las franjas disponibles" in body["respuesta"]
    assert "3:00 p. m. a 5:00 p. m." in body["respuesta"]
    assert "5:00 p. m. a 7:00 p. m." in body["respuesta"]
    assert "¿Cuál le queda mejor?" in body["respuesta"]
    assert "¿Desea que registre esa franja?" not in body["respuesta"]

    assert calls["appointment_service_call"] is None
    assert calls["clear_patient_appointment_context"] is None
    assert "por favor elija una de las franjas disponibles" in calls["save_interaction"]["respuesta_elvira"]


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


