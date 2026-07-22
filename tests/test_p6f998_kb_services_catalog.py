import csv
import unicodedata
from pathlib import Path


SERVICES_CSV = Path("data/kb/datakbKB_Servicios.csv")


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    return "".join(
        char for char in value
        if not unicodedata.combining(char)
    )


def _services() -> dict[str, dict[str, str]]:
    with SERVICES_CSV.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == len({row["service_id"] for row in rows})
    return {row["service_id"]: row for row in rows}


def test_p6f998_therapy_is_active_without_home_oxygen_therapy():
    service = _services()["SRV-01"]
    techniques = _normalize(service["techniques"])
    answer = _normalize(service["public_answer_long"])

    assert service["is_active"] == "true"
    assert service["escalation_required"] == "false"
    assert "oxigenoterapia" not in techniques
    assert "no requiere orden medica" in answer
    assert "tres horas" in answer
    assert "30 y 45 minutos" in answer


def test_p6f998_retired_services_remain_inactive():
    services = _services()

    assert services["SRV-02"]["is_active"] == "false"
    assert services["SRV-05"]["is_active"] == "false"
    assert services["SRV-08"]["is_active"] == "false"

    assert "inactivo" in _normalize(
        services["SRV-02"]["public_answer_short"]
    )
    assert "no ofrece" in _normalize(
        services["SRV-05"]["public_answer_short"]
    )
    assert "no esta disponible" in _normalize(
        services["SRV-08"]["public_answer_short"]
    )


def test_p6f998_dynamic_oximetry_is_independent_active_service():
    service = _services()["SRV-07"]
    content = _normalize(
        " ".join(
            [
                service["service_name"],
                service["objective"],
                service["public_answer_short"],
                service["public_answer_long"],
                service["search_terms"],
            ]
        )
    )

    assert service["service_name"] == "Oximetría Dinámica"
    assert service["is_active"] == "true"
    assert service["modality"] == "Domiciliaria"
    assert service["escalation_required"] == "true"
    assert "orden medica" in content
    assert "validacion previa" in content
    assert "destete de oxigeno" in content


def test_p6f998_confirmed_pulmonary_services_are_present():
    services = _services()

    pulmonary_tests = _normalize(services["SRV-03"]["techniques"])
    rehabilitation = _normalize(services["SRV-04"]["techniques"])
    enterprise = _normalize(services["SRV-06"]["techniques"])

    assert "espirometria" in pulmonary_tests
    assert "caminata de seis minutos" in pulmonary_tests
    assert "test de cooper" in pulmonary_tests

    assert "gimnasio pulmonar" in rehabilitation
    assert "yoga respiratorio" in rehabilitation

    assert "tamizaje de salud respiratoria" in enterprise
    assert "espirometria ocupacional" in enterprise
    assert "jornadas empresariales de bienestar" in enterprise
