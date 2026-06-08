import re
from app.graph.state import Intent


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    replacements = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = text.replace("maniana", "manana")
    text = re.sub(r"\s+", " ", text)
    return text


def classify_intent(message: str, current_state: str = "ST_INIT") -> Intent:

    msg = normalize_text(message)
    if not msg:
        return "general"

    # OPTOUT — prioridad máxima
    optout_patterns = [
        r"\bno quiero recibir\b", r"\bno me escriban\b", r"\bno mas mensajes\b",
        r"\bcancelar mensajes\b", r"\bdarme de baja\b", r"\bopt ?out\b",
        r"\bdejar de recibir\b",
    ]
    if any(re.search(p, msg) for p in optout_patterns):
        return "optout"

    # URGENCIA
    urgency_patterns = [
        r"\burgente\b", r"\bemergencia\b", r"\bno puede respirar\b",
        r"\bno puedo respirar\b", r"\bdificultad para respirar\b",
        r"\bse esta ahogando\b", r"\bdolor en el pecho\b",
        r"\bdolor fuerte en el pecho\b", r"\bme cuesta respirar\b",
        r"\bme falta el aire\b", r"\bse me dificulta respirar\b",
        r"\blabios morados\b", r"\bdedos morados\b",
        r"\bsaturacion baja\b", r"\bsaturacion muy baja\b",
        r"\bsaturacion esta baja\b", r"\bsaturacion esta muy baja\b",
        r"\bsaturacion.*muy baja\b", r"\bsaturacion.*baja\b",
        r"\bme estoy ahogando\b",
    ]
    if any(re.search(p, msg) for p in urgency_patterns):
        return "urgencia"

    # CITA
    appointment_patterns = [
        r"\bcita\b", r"\bagendar\b", r"\bprogramar\b",
        r"\bpedir una cita\b", r"\bsacar una cita\b", r"\bquiero una cita\b",
    ]
    if any(re.search(p, msg) for p in appointment_patterns):
        return "cita"

    # FECHA/HORA por contexto de cita
    date_context_states = {"ST_CITA_FECHA", "ST_CITA_FRANJA", "ST_CITA_PENDIENTE"}
    if current_state in date_context_states:
        clarification_patterns = [
            r"\bcual fecha\b",
            r"\bque fecha\b",
            r"\bfecha indicada\b",
            r"\bno entendi\b",
            r"\bque quiere decir\b",
        ]
        if any(re.search(p, msg) for p in clarification_patterns):
            return "fecha_cita"

        time_patterns = [
            r"\b\d{1,2}\s*(am|pm)\b",
            r"\b\d{1,2}:\d{2}\b",
            r"\ba las \d{1,2}\b",
            r"\bpara la de las \d{1,2}\b",
            r"\bla de las \d{1,2}\b",
            r"\bpara la de \d{1,2}\b",
            r"\bla de \d{1,2}\b",
            r"\bpara la de las (?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\b",
            r"\bla de las (?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\b",
            r"\bpara la de (?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\b",
            r"\bla de (?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\b",
        ]

        # If we are still waiting for a date, a slot/hour preference is still
        # part of the appointment flow. It must not fall back to general.
        if current_state == "ST_CITA_FECHA" and any(re.search(p, msg) for p in time_patterns):
            return "hora_cita"

        # In ST_CITA_FRANJA, the patient is expected to select or accept a time slot.
        # Therefore short phrases like "de 3 a 5", "la primera" or "me sirve"
        # must be interpreted as appointment time selection, not as general intent.
        if current_state == "ST_CITA_FRANJA":
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

                # Selecciones generales de franja cuando ya estamos esperando horario
                r"\ben la tarde\b",
                r"\bpor la tarde\b",
                r"\btarde\b",
                r"\ben la manana\b",
                r"\bpor la manana\b",
                r"\bmanana\b",
                r"\ben la noche\b",
                r"\bpor la noche\b",
                r"\bnoche\b",

                # Selecciones horarias en lenguaje natural colombiano
                r"\bla de \d{1,2}(?: de la (?:manana|tarde|noche))?\b",
                r"\bla de (?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)(?: de la (?:manana|tarde|noche))?\b",
                r"\ba las (?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\b",
                r"\b(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce) de la (?:manana|tarde|noche)\b",
                r"\btipo \d{1,2}\b",
                r"\btipo (?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\b",
                r"\ba eso de las \d{1,2}\b",
                r"\ba eso de las (?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\b",
            ]
            if any(re.search(p, msg) for p in time_patterns + slot_selection_patterns):
                return "hora_cita"

        date_patterns = [
            r"\bmanana\b", r"\bhoy\b", r"\bpasado manana\b",
            r"\b(?:el )?lunes\b", r"\b(?:el )?martes\b", r"\b(?:el )?miercoles\b",
            r"\b(?:el )?jueves\b", r"\b(?:el )?viernes\b", r"\b(?:el )?sabado\b",
            r"\b(?:el )?domingo\b",
            r"\ben la manana\b", r"\ben la tarde\b", r"\ben la noche\b",
        ]
        if any(re.search(p, msg) for p in date_patterns):
            return "fecha_cita"

        if any(re.search(p, msg) for p in time_patterns):
            return "hora_cita"

    # PAGO
    price_patterns = [
        r"\bcuanto cuesta\b", r"\bprecio\b", r"\bvalor\b",
        r"\btarifa\b", r"\bcosto\b", r"\bcuanto vale\b",
    ]
    if any(re.search(p, msg) for p in price_patterns):
        return "pago"

    # SERVICIOS
    service_patterns = [
        r"\bservicios\b", r"\bque hacen\b", r"\bque ofrecen\b",
        r"\bterapia respiratoria\b", r"\btraqueostomia\b", r"\bespirometria\b",
        r"\bpruebas de funcion pulmonar\b", r"\brehabilitacion pulmonar\b",
        r"\bcurso profilactico\b", r"\bsalud respiratoria empresarial\b", r"\bsst\b",
    ]
    if any(re.search(p, msg) for p in service_patterns):
        return "servicios"

    # HORARIOS
    schedule_patterns = [
        r"\bhorario\b", r"\batienden\b", r"\bcuando atienden\b",
        r"\bque dias\b", r"\ba que hora\b", r"\bdias de atencion\b",
        r"\bsabado\b", r"\bdomingo\b", r"\btarde\b.*\batienden\b",
    ]
    if any(re.search(p, msg) for p in schedule_patterns):
        return "horarios"

    # REGLAS
    rules_patterns = [
        r"\bcancelar\b", r"\bcancelacion\b", r"\bpolitica\b",
        r"\bcomo funciona\b", r"\brequisitos\b",
    ]
    if any(re.search(p, msg) for p in rules_patterns):
        return "reglas"

    return "general"
