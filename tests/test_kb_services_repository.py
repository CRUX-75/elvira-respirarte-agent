from app.repositories import kb_services


class FakeResult:
    def __init__(self, rows=None, first_row=None):
        self.rows = rows or []
        self.first_row = first_row

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.first_row


class FakeConnection:
    def __init__(self, engine):
        self.engine = engine

    def execute(self, query, params=None):
        self.engine.executed_query = str(query)
        self.engine.executed_params = params or {}
        return FakeResult(
            rows=self.engine.rows,
            first_row=self.engine.first_row,
        )


class FakeBegin:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        return FakeConnection(self.engine)

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    def __init__(self, rows=None, first_row=None):
        self.rows = rows or []
        self.first_row = first_row
        self.executed_query = ""
        self.executed_params = {}

    def begin(self):
        return FakeBegin(self)


def test_get_active_services_selects_search_terms():
    engine = FakeEngine(
        rows=[
            {
                "service_id": "SRV-01",
                "service_name": "Terapia Respiratoria",
                "search_terms": "le silba el pecho, niño mocoso",
            }
        ]
    )

    result = kb_services.get_active_services(engine)

    assert "search_terms" in engine.executed_query
    assert result[0]["search_terms"] == "le silba el pecho, niño mocoso"


def test_get_service_by_id_selects_search_terms():
    engine = FakeEngine(
        first_row={
            "service_id": "SRV-01",
            "service_name": "Terapia Respiratoria",
            "search_terms": "destete de oxígeno",
        }
    )

    result = kb_services.get_service_by_id(engine, "SRV-01")

    assert "search_terms" in engine.executed_query
    assert engine.executed_params == {"service_id": "SRV-01"}
    assert result["search_terms"] == "destete de oxígeno"


def test_search_services_searches_inside_search_terms():
    engine = FakeEngine(
        rows=[
            {
                "service_id": "SRV-01",
                "service_name": "Terapia Respiratoria",
                "search_terms": "le silva el pecho",
            }
        ]
    )

    result = kb_services.search_services(engine, "le silva")

    assert "OR search_terms ILIKE :search" in engine.executed_query
    assert engine.executed_params == {"search": "%le silva%"}
    assert result[0]["service_id"] == "SRV-01"
