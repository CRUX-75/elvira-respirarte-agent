import re
from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING

from app.services.approved_service_catalog import (
    get_active_portfolio_response,
)
from app.services.intent import normalize_text

if TYPE_CHECKING:
    from app.graph.state import ElviraState


INTERNAL_INFORMATION_REFUSAL = (
    "No estoy autorizada a proporcionar información sobre la configuración "
    "o el funcionamiento interno del sistema."
)

FUNCTIONAL_SCOPE_REFUSAL = (
    "Solo puedo ayudarle con temas relacionados con las funciones "
    "habilitadas para este servicio."
)

THIRD_PARTY_DATA_REFUSAL = (
    "No puedo proporcionar información personal o datos de otras personas."
)


BoundaryKind = Literal[
    "allowed",
    "protected_internal",
    "out_of_scope",
    "mixed",
]


@dataclass(frozen=True)
class H3BoundaryDecision:
    kind: BoundaryKind


@dataclass(frozen=True)
class H4BoundaryDecision:
    kind: Literal["allowed", "protected_third_party"]


_INTERNAL_PATTERNS = (
    r"\barquitectura(?: interna)?\b",
    r"\bcomo (?:estas )?construid[ao]\b",
    r"\bcomo funcionas\b",
    r"\bfuncionamiento interno\b",
    r"\bmodelo de (?:ia|inteligencia artificial|lenguaje)\b",
    r"\bque modelo (?:usas|utilizas|usa|utiliza)\b",
    r"\bprompt\b",
    r"\binstrucciones internas\b",
    r"\bmensaje del sistema\b",
    r"\bsystem prompt\b",
    r"\bapis?\b",
    r"\bbase de datos\b",
    r"\bpostgres(?:ql)?\b",
    r"\bhosting\b",
    r"\bdonde esta alojad[oa]\b",
    r"\binfraestructura\b",
    r"\bendpoints?\b",
    r"\bvariables? de entorno\b",
    r"\btokens?\b",
    r"\bapi key\b",
    r"\bcredenciales?\b",
    r"\bcontrasena\b",
    r"\bconfiguracion\b",
    r"\bcodigo fuente\b",
    r"\bignora .*instrucciones\b",
    r"\bmodo desarrollador\b",
    r"\bactua como administrador\b",
)

_RESPIRARTE_PATTERNS = (
    r"\bservicios?\b",
    r"\bterapia respiratoria\b",
    r"\bespirometria\b",
    r"\boximetria\b",
    r"\bfuncion pulmonar\b",
    r"\brehabilitacion pulmonar\b",
    r"\bhorarios?\b",
    r"\batienden\b",
    r"\bcitas?\b",
    r"\bagendar\b",
    r"\borden medica\b",
    r"\bprecios?\b",
    r"\bcostos?\b",
    r"\bpagos?\b",
)

_OUT_OF_SCOPE_PATTERNS = (
    r"\bcapital de\b",
    r"\bresultado del partido\b",
    r"\breceta de cocina\b",
    r"\bclima en\b",
)

_THIRD_PARTY_DATA_PATTERNS = (
    r"\b(?:a que hora|que dia|cuando)\b.*\btiene cita\b",
    r"\b(?:soy (?:la |el )?"
    r"(?:doctor(?:a)?|administrador(?:a)?|desarrollador(?:a)?)"
    r"|trabajo en respirarte|el paciente me dio permiso)\b"
    r".*\bcitas? de (?:manana|hoy)\b",
    r"\btelefonos?\b.*\bpacientes?\b",
    r"\bpacientes?\b.*\btelefonos?\b",
    r"\b(?:telefono|correo|email|direccion)\s+de\s+"
    r"(?!respirarte\b|la clinica\b|la sede\b|contacto\b)",
    r"\bdiagnosticos?\b.*\bpacientes?\b",
    r"\b(?:diagnostico|historia clinica|condicion medica|tratamiento) "
    r"(?:de|tiene)\b",
    r"\bultimo paciente\b",
    r"\bquien (?:fue|es) el ultimo paciente\b",
    r"\bquien mas (?:pidio|solicito|tiene)\b",
    r"\biniciales\b.*\bpacientes?\b",
    r"\bultimos cuatro\b.*\btelefono\b",
    r"\bcuantos pacientes?\b",
    r"\bejemplo real\b.*\bsin identificar\b",
    r"\b(?:resume|resumen)\b.*\bcasos?\b.*\bsin nombres?\b",
    r"\bcasos? clinicos? reales?\b.*\bsin nombres?\b",
)


_DISPLAY_SERVICE_TERMS = {
    "espirometria": "espirometría",
    "oximetria": "oximetría",
}


def _matches_any(message: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, message) for pattern in patterns)


def evaluate_h3_boundary(message: str) -> H3BoundaryDecision:
    normalized = normalize_text(message)

    if _matches_any(normalized, _INTERNAL_PATTERNS):
        if _matches_any(normalized, _RESPIRARTE_PATTERNS):
            return H3BoundaryDecision(kind="mixed")
        return H3BoundaryDecision(kind="protected_internal")

    if _matches_any(normalized, _OUT_OF_SCOPE_PATTERNS):
        return H3BoundaryDecision(kind="out_of_scope")

    return H3BoundaryDecision(kind="allowed")


def evaluate_h4_boundary(message: str) -> H4BoundaryDecision:
    normalized = normalize_text(message)

    if _matches_any(normalized, _THIRD_PARTY_DATA_PATTERNS):
        return H4BoundaryDecision(kind="protected_third_party")

    return H4BoundaryDecision(kind="allowed")


def build_mixed_h3_response(state: "ElviraState") -> str:
    if state.intent == "servicios":
        matched_term = (state.matched_service_term or "").strip()

        if state.service_grounding_status == "exact" and matched_term:
            display_term = _DISPLAY_SERVICE_TERMS.get(
                normalize_text(matched_term),
                matched_term,
            )
            allowed_response = (
                "Sí. Respirarte cuenta con información confirmada "
                f"sobre {display_term}."
            )
        else:
            allowed_response = get_active_portfolio_response()
    else:
        allowed_response = (
            "Puedo ayudarle con la parte de su consulta relacionada "
            "con Respirarte."
        )

    return f"{allowed_response} {INTERNAL_INFORMATION_REFUSAL}"
