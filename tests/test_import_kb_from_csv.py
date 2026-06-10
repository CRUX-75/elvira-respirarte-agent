from scripts import import_kb_from_csv


class FakeConnection:
    def __init__(self, engine):
        self.engine = engine

    def execute(self, query, params=None):
        self.engine.executed_query = str(query)
        self.engine.executed_params = params or {}


class FakeBegin:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        return FakeConnection(self.engine)

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    def __init__(self):
        self.executed_query = ""
        self.executed_params = {}

    def begin(self):
        return FakeBegin(self)


def test_import_services_inserts_and_updates_search_terms(monkeypatch):
    fake_engine = FakeEngine()

    monkeypatch.setattr(import_kb_from_csv, "engine", fake_engine)
    monkeypatch.setattr(
        import_kb_from_csv,
        "_read_csv",
        lambda path: [
            {
                "service_id": "SRV-01",
                "service_name": "Terapia Respiratoria",
                "category": "Atención domiciliaria",
                "objective": "Tratamiento respiratorio",
                "techniques": "Oxigenoterapia",
                "patient_scope": "Pediátrico",
                "modality": "Domiciliaria",
                "is_active": "true",
                "public_answer_short": "Sí, ofrecemos terapia respiratoria.",
                "public_answer_long": "Atención respiratoria domiciliaria.",
                "search_terms": "le silva el pecho, niño mocoso",
                "escalation_required": "false",
            }
        ],
    )

    imported = import_kb_from_csv.import_services()

    assert imported == 1
    assert "search_terms" in fake_engine.executed_query
    assert "search_terms = EXCLUDED.search_terms" in fake_engine.executed_query
    assert fake_engine.executed_params["search_terms"] == "le silva el pecho, niño mocoso"


def test_importer_uses_real_datakb_csv_filenames():
    assert import_kb_from_csv.SERVICES_CSV.name == "datakbKB_Servicios.csv"
    assert import_kb_from_csv.SCHEDULES_CSV.name == "datakbKB_Horarios.csv"
    assert import_kb_from_csv.RULES_CSV.name == "datakbKB_Reglas.csv"
