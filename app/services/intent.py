import re

from app.graph.state import Intent
from app.services.slot_confirmation_guard import (
    is_simple_affirmative_slot_confirmation,
)


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower().strip()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    text = text.replace("maniana", "manana")
    text = re.sub(r"\s+", " ", text)

    return text


def _is_explicit_tomorrow_reference(message: str) -> bool:
    patterns = [
        r"^manana$",
        r"^manana\b",
        r"\bpara manana\b",
        r"\bel dia de manana\b",
    ]
    return any(re.search(pattern, message) for pattern in patterns)


def classify_intent(
    message: str,
    current_state: str = "ST_INIT",
) -> Intent:
    msg = normalize_text(message)

    if not msg:
        return "general"

    # OPTOUT — prioridad máxima
    optout_patterns = [
        r"\bno quiero recibir\b",
        r"\bno me escriban\b",
        r"\bno mas mensajes\b",
        r"\bcancelar mensajes\b",
        r"\bdarme de baja\b",
        r"\bopt ?out\b",
        r"\bdejar de recibir\b",
    ]
    if any(re.search(pattern, msg) for pattern in optout_patterns):
        return "optout"

    # URGENCIA
    urgency_patterns = [
        r"\burgente\b",
        r"\bemergencia\b",
        r"\bno puede respirar\b",
        r"\bno puedo respirar\b",
        r"\bdificultad para respirar\b",
        r"\bse esta ahogando\b",
        r"\bdolor en el pecho\b",
        r"\bdolor fuerte en el pecho\b",
        r"\bme cuesta respirar\b",
        r"\bme falta el aire\b",
        r"\bse me dificulta respirar\b",
        r"\blabios morados\b",
        r"\bdedos morados\b",
        r"\bsaturacion baja\b",
        r"\bsaturacion muy baja\b",
        r"\bsaturacion esta baja\b",
        r"\bsaturacion esta muy baja\b",
        r"\bsaturacion.*muy baja\b",
        r"\bsaturacion.*baja\b",
        r"\bme estoy ahogando\b",
    ]
    if any(re.search(pattern, msg) for pattern in urgency_patterns):
        return "urgencia"

    # CITA
    appointment_patterns = [
        r"\bcita\b",
        r"\bagendar\b",
        r"\bprogramar\b",
        r"\bpedir una cita\b",
        r"\bsacar una cita\b",
        r"\bquiero una cita\b",
    ]
    if any(re.search(pattern, msg) for pattern in appointment_patterns):
        return "cita"

    # FECHA/HORA por contexto de cita
    date_context_states = {
        "ST_CITA_FECHA",
        "ST_CITA_FRANJA",
        "ST_CITA_PENDIENTE",
    }

    if current_state in date_context_states:
        clarification_patterns = [
            r"\bcual fecha\b",
            r"\bque fecha\b",
            r"\bfecha indicada\b",
            r"\bno entendi\b",
            r"\bque quiere decir\b",
        ]
        if any(re.search(pattern, msg) for pattern in clarification_patterns):
            return "fecha_cita"

        time_patterns = [
            r"\b\d{1,2}\s*(am|pm)\b",
            r"\b\d{1,2}:\d{2}\b",
            r"\ba las \d{1,2}\b",
            r"\bpara la de las \d{1,2}\b",
            r"\bla de las \d{1,2}\b",
            r"\bpara la de \d{1,2}\b",
            r"\bla de \d{1,2}\b",
            (
                r"\bpara la de las "
                r"(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                r"nueve|diez|once|doce)\b"
            ),
            (
                r"\bla de las "
                r"(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                r"nueve|diez|once|doce)\b"
            ),
            (
                r"\bpara la de "
                r"(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                r"nueve|diez|once|doce)\b"
            ),
            (
                r"\bla de "
                r"(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                r"nueve|diez|once|doce)\b"
            ),
        ]

        # Si todavía se espera una fecha, una preferencia horaria sigue siendo
        # parte del flujo de cita y no debe caer en intención general.
        if current_state == "ST_CITA_FECHA" and any(
            re.search(pattern, msg) for pattern in time_patterns
        ):
            return "hora_cita"

        if current_state == "ST_CITA_FRANJA":
            # "Mañana" como referencia al día debe reemplazar la fecha anterior.
            # No debe confundirse con "en la mañana" como franja del día.
            if _is_explicit_tomorrow_reference(msg):
                return "fecha_cita"

            if is_simple_affirmative_slot_confirmation(msg):
                return "hora_cita"

            slot_selection_patterns = [
                r"\bde\s+\d{1,2}\s+a\s+\d{1,2}\b",
                r"\b\d{1,2}\s+a\s+\d{1,2}\b",
                r"\bde\s+\d{1,2}:\d{2}\s+a\s+\d{1,2}:\d{2}\b",
                r"\b\d{1,2}:\d{2}\s+a\s+\d{1,2}:\d{2}\b",
                r"\bprimera\b",
                r"\bla primera\b",
                r"\bsegunda\b",
                r"\bla segunda\b",
                r"\bese horario\b",
                r"\besa franja\b",
                r"\besta bien\b",
                r"\bme sirve\b",
                r"\bme queda bien\b",

                # Selecciones generales de franja cuando ya se espera horario.
                r"\ben la tarde\b",
                r"\bpor la tarde\b",
                r"\btarde\b",
                r"\ben la manana\b",
                r"\bpor la manana\b",
                r"\bmanana\b",
                r"\ben la noche\b",
                r"\bpor la noche\b",
                r"\bnoche\b",

                # Selecciones horarias en lenguaje natural colombiano.
                (
                    r"\bla de \d{1,2}"
                    r"(?: de la (?:manana|tarde|noche))?\b"
                ),
                (
                    r"\bla de "
                    r"(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                    r"nueve|diez|once|doce)"
                    r"(?: de la (?:manana|tarde|noche))?\b"
                ),
                (
                    r"\ba las "
                    r"(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                    r"nueve|diez|once|doce)\b"
                ),
                (
                    r"\b(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                    r"nueve|diez|once|doce) "
                    r"de la (?:manana|tarde|noche)\b"
                ),
                r"\btipo \d{1,2}\b",
                (
                    r"\btipo "
                    r"(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                    r"nueve|diez|once|doce)\b"
                ),
                r"\ba eso de las \d{1,2}\b",
                (
                    r"\ba eso de las "
                    r"(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|"
                    r"nueve|diez|once|doce)\b"
                ),
            ]

            if any(
                re.search(pattern, msg)
                for pattern in time_patterns + slot_selection_patterns
            ):
                return "hora_cita"

        date_patterns = [
            r"\bmanana\b",
            r"\bhoy\b",
            r"\bpasado manana\b",
            r"\b(?:el )?lunes\b",
            r"\b(?:el )?martes\b",
            r"\b(?:el )?miercoles\b",
            r"\b(?:el )?jueves\b",
            r"\b(?:el )?viernes\b",
            r"\b(?:el )?sabado\b",
            r"\b(?:el )?domingo\b",
            r"\ben la manana\b",
            r"\ben la tarde\b",
            r"\ben la noche\b",
        ]
        if any(re.search(pattern, msg) for pattern in date_patterns):
            return "fecha_cita"

        if any(re.search(pattern, msg) for pattern in time_patterns):
            return "hora_cita"

    # PAGO
    price_patterns = [
        r"\bcuanto cuesta\b",
        r"\bprecio\b",
        r"\bvalor\b",
        r"\btarifa\b",
        r"\bcosto\b",
        r"\bcuanto vale\b",
    ]
    if any(re.search(pattern, msg) for pattern in price_patterns):
        return "pago"

    # SERVICIOS
    service_patterns = [
        r"\bservicios\b",
        r"\bque hacen\b",
        r"\bque ofrecen\b",
        r"\bterapia respiratoria\b",
        r"\btraqueostomia\b",
        r"\bespirometria\b",
        r"\bpruebas de funcion pulmonar\b",
        r"\brehabilitacion pulmonar\b",
        r"\bcurso profilactico\b",
        r"\bsalud respiratoria empresarial\b",
        r"\bsst\b",
    ]
    if any(re.search(pattern, msg) for pattern in service_patterns):
        return "servicios"

    # HORARIOS
    schedule_patterns = [
        r"\bhorario\b",
        r"\batienden\b",
        r"\bcuando atienden\b",
        r"\bque dias\b",
        r"\ba que hora\b",
        r"\bdias de atencion\b",
        r"\bsabado\b",
        r"\bdomingo\b",
        r"\btarde\b.*\batienden\b",
    ]
    if any(re.search(pattern, msg) for pattern in schedule_patterns):
        return "horarios"

    # REGLAS
    rules_patterns = [
        r"\bcancelar\b",
        r"\bcancelacion\b",
        r"\bpolitica\b",
        r"\bcomo funciona\b",
        r"\brequisitos\b",
    ]
    if any(re.search(pattern, msg) for pattern in rules_patterns):
        return "reglas"

    return "general"