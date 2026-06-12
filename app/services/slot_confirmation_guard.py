import re


AFFIRMATIVE_SLOT_CONFIRMATIONS = {
    "si",
    "si por favor",
    "claro",
    "de acuerdo",
    "esta bien",
    "perfecto",
    "listo",
    "me sirve",
    "esa esta bien",
    "registrela",
    "me parece bien",
    "adelante",
    "ok",
    "okay",
    "dale",
    "bueno",
    "va",
    "correcto",
}


AFFIRMATIVE_SLOT_BLOCKERS = {
    "pero",
    "aunque",
    "mejor",
    "otro dia",
    "otra fecha",
    "no puedo",
    "no me sirve",
    "mas tarde",
    "mas temprano",
    "en la manana",
    "por la manana",
}


def _normalize_guard_text(text: str) -> str:
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


def is_simple_affirmative_slot_confirmation(message: str) -> bool:
    msg = _normalize_guard_text(message)
    msg = msg.strip(" !.¿?¡")

    if not msg:
        return False

    if "?" in message or "¿" in message:
        return False

    if any(blocker in msg for blocker in AFFIRMATIVE_SLOT_BLOCKERS):
        return False

    return any(
        msg == phrase
        or msg.startswith(f"{phrase} ")
        or msg.startswith(f"{phrase},")
        for phrase in AFFIRMATIVE_SLOT_CONFIRMATIONS
    )
