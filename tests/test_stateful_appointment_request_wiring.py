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
        state_reason: str | None = "test_reason",
        fecha_solicitada: str | None = None,
        slots_candidatos: list[str] | None = None,
        mensaje_original: str | None = None,
        is_weekend: bool | None = None,
        is_colombia_holiday: bool | None = None,
        es_dia_disponible: bool | None = None,
    ):
        self.intent = intent
        self.nuevo_estado = nuevo_estado
        self.respuesta = respuesta
        self.next_action = next_action
        self.state_reason = state_reason
        self.router_version = "test-router"
        self.state_machine_version = "test-state-machine"
        self.kb_used = False
        self.escalation_required = False
        self.opt_out = False

        # Fields consumed by appointment_request_runtime decision function.
        self.fecha_solicitada = fecha_solicitada
        self.slots_candidatos = slots_candidatos or []
        self.mensaje_original = mensaje_original
        self.is_weekend = is_weekend
        self.is_colombia_holiday = is_colombia_holiday
        self.es_dia_disponible = es_dia_disponible

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
            "slots_candidatos": self.slots_candidatos,
            "mensaje_original": self.mensaje_original,
            "is_weekend": self.is_weekend,
            "is_colombia_holiday": self.is_colombia_holiday,
            "es_dia_disponible": self.es_dia_disponible,
        }


def _patch_stateful_endpoint_dependencies(monkeypatch, fake_result):
    calls = {
        "save_interaction": None,
        "update_patient_state": None,
        "update_patient_last_message": None,
        "update_patient_appointment_context": None,
        "clear_patient_appointment_context": None,
        "appointment_service_call": None,
        "whatsapp_send_called": False,
    }

    monkeypatch.setattr(
        main,
        "get_or_create_patient_by_phone",
        lambda telefono, nombre: {
            "id": "patient-001",
            "telefono": telefono,
            "nombre": nombre,
            "estado_actual": "ST_INIT",
            "opt_out": False,
        },
    )

    monkeypatch.setattr(
        main,
        "traced_process_message",
        lambda process_func, message: fake_result,
    )

    def fake_save_interaction(**kwargs):
        calls["save_interaction"] = kwargs

    def fake_update_patient_state(**kwargs):
        calls["update_patient_state"] = kwargs

    def fake_update_patient_last_message(**kwargs):
        calls["update_patient_last_message"] = kwargs

    def fake_update_patient_appointment_context(**kwargs):
        calls["update_patient_appointment_context"] = kwargs

    def fake_clear_patient_appointment_context(**kwargs):
        calls["clear_patient_appointment_context"] = kwargs

    monkeypatch.setattr(main, "save_interaction", fake_save_interaction)
    monkeypatch.setattr(main, "update_patient_state", fake_update_patient_state)
    monkeypatch.setattr(main, "update_patient_last_message", fake_update_patient_last_message)
    monkeypatch.setattr(main, "update_patient_appointment_context", fake_update_patient_appointment_context)
    monkeypatch.setattr(main, "clear_patient_appointment_context", fake_clear_patient_appointment_context)

    # These attributes do not exist yet before runtime wiring.
    # raising=False keeps this test file RED for response contract first,
    # and ready for the later minimal implementation.
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

    monkeypatch.setattr(
        main,
        "PostgresAppointmentRequestRepository",
        FakePostgresAppointmentRequestRepository,
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "AppointmentRequestService",
        FakeAppointmentRequestService,
        raising=False,
    )

    return calls


def test_stateful_endpoint_returns_skip_decision_for_general_message(monkeypatch):
    fake_result = FakeElviraResult(
        intent="general",
        nuevo_estado="ST_INIT",
        next_action="respond_general",
    )
    calls = _patch_stateful_endpoint_dependencies(monkeypatch, fake_result)

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "Hola buenos días",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["test_endpoint"] == "message-stateful"
    assert body["delivery_status"] == "sending_skipped"
    assert body["persisted_state"] == "ST_INIT"
    assert body["whatsapp_message_id"].startswith("test-stateful-")

    assert body["appointment_request_decision"]["should_persist"] is False
    assert body["appointment_request_decision"]["reason"] == "skipped_non_appointment_intent"
    assert body["appointment_request"] is None

    assert calls["appointment_service_call"] is None
    assert calls["save_interaction"]["delivery_status"] == "sending_skipped"
    assert calls["update_patient_state"]["nuevo_estado"] == "ST_INIT"


def test_stateful_endpoint_returns_skip_decision_for_initial_cita(monkeypatch):
    fake_result = FakeElviraResult(
        intent="cita",
        nuevo_estado="ST_CITA_FECHA",
        next_action="ask_appointment_date",
    )
    calls = _patch_stateful_endpoint_dependencies(monkeypatch, fake_result)

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "Quiero pedir una cita",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["appointment_request_decision"]["should_persist"] is False
    assert body["appointment_request_decision"]["reason"] == "skipped_initial_cita_intent"
    assert body["appointment_request"] is None
    assert calls["appointment_service_call"] is None


def test_stateful_endpoint_returns_skip_decision_for_fecha_cita(monkeypatch):
    fake_result = FakeElviraResult(
        intent="fecha_cita",
        nuevo_estado="ST_CITA_FRANJA",
        next_action="ask_appointment_time_window",
        fecha_solicitada="2026-05-29",
        es_dia_disponible=True,
    )
    calls = _patch_stateful_endpoint_dependencies(monkeypatch, fake_result)

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "Mañana",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["appointment_request_decision"]["should_persist"] is False
    assert body["appointment_request_decision"]["reason"] == "skipped_fecha_cita_waiting_for_time"
    assert body["appointment_request"] is None
    assert calls["appointment_service_call"] is None


def test_stateful_endpoint_persists_ready_hora_cita_with_synthetic_source_interaction_id(monkeypatch):
    fake_result = FakeElviraResult(
        intent="hora_cita",
        nuevo_estado="ST_CITA_PENDIENTE",
        next_action="confirm_appointment_request",
        fecha_solicitada="2026-05-29",
        slots_candidatos=["14:00-18:00"],
        mensaje_original="A las 3",
        is_weekend=False,
        is_colombia_holiday=False,
        es_dia_disponible=True,
    )
    calls = _patch_stateful_endpoint_dependencies(monkeypatch, fake_result)

    response = client.post(
        "/test/message-stateful",
        json={
            "telefono": "573001112233",
            "nombre": "Paciente Test",
            "mensaje": "A las 3",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["test_endpoint"] == "message-stateful"
    assert body["delivery_status"] == "sending_skipped"
    assert body["persisted_state"] == "ST_CITA_PENDIENTE"
    assert body["whatsapp_message_id"].startswith("test-stateful-")

    assert body["appointment_request_decision"]["should_persist"] is True
    assert (
        body["appointment_request_decision"]["reason"]
        == "allowed_hora_cita_ready_for_human_review"
    )
    assert body["appointment_request_decision"]["source_interaction_id"] == body["whatsapp_message_id"]

    assert body["appointment_request"]["id_solicitud"] == "SOL-TEST-001"
    assert body["appointment_request"]["estado_solicitud"] == "pendiente_confirmacion"
    assert body["appointment_request"]["source_interaction_id"] == body["whatsapp_message_id"]

    assert calls["appointment_service_call"]["telefono"] == "573001112233"
    assert calls["appointment_service_call"]["nombre_paciente"] == "Paciente Test"
    assert calls["appointment_service_call"]["fecha_solicitada"] == "2026-05-29"
    assert calls["appointment_service_call"]["franja_solicitada"] == "14:00-18:00"
    assert calls["appointment_service_call"]["source_interaction_id"] == body["whatsapp_message_id"]

    assert calls["save_interaction"]["whatsapp_message_id"] == body["whatsapp_message_id"]
    assert calls["save_interaction"]["delivery_status"] == "sending_skipped"
    assert calls["update_patient_state"]["nuevo_estado"] == "ST_CITA_PENDIENTE"
