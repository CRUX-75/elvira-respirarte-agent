from app.services.voice_text_normalizer import (
    normalize_text_for_speech,
)


def test_p6f999_converts_times_and_units_for_speech():
    written = (
        "La sesión dura de 30 a 45 minutos. "
        "La franja es de 3:00 p. m. a 5:00 p. m. "
        "Se requieren 3 horas de ayuno."
    )

    spoken = normalize_text_for_speech(written)

    assert "treinta a cuarenta y cinco minutos" in spoken
    assert "tres de la tarde a cinco de la tarde" in spoken
    assert "tres horas de ayuno" in spoken


def test_p6f999_converts_24_hour_times():
    spoken = normalize_text_for_speech(
        "La franja es 15:00–17:00."
    )

    assert spoken == (
        "La franja es tres de la tarde "
        "a cinco de la tarde."
    )


def test_p6f999_expands_common_abbreviations():
    spoken = normalize_text_for_speech(
        "La Dra. D'Aleman revisará la solicitud."
    )

    assert spoken == (
        "La doctora D'Aleman revisará la solicitud."
    )


def test_p6f999_softens_visual_lists_for_audio():
    written = (
        "Necesita:\n"
        "- Orden médica;\n"
        "- Validación previa."
    )

    spoken = normalize_text_for_speech(written)

    assert "\n" not in spoken
    assert "- " not in spoken
    assert ";" not in spoken
    assert "Orden médica" in spoken
    assert "Validación previa" in spoken


def test_p6f999_preserves_clinical_content():
    written = (
        "La oximetría dinámica requiere orden médica "
        "y validación previa."
    )

    spoken = normalize_text_for_speech(written)

    assert spoken == written


def test_p6f999_is_idempotent():
    written = (
        "La sesión es a las 3:00 p. m. "
        "y dura 30 minutos."
    )

    once = normalize_text_for_speech(written)
    twice = normalize_text_for_speech(once)

    assert twice == once


def test_p6f999_empty_text_remains_empty():
    assert normalize_text_for_speech("   ") == ""


def test_p6f999_preserves_sentence_stop_after_spoken_time():
    spoken = normalize_text_for_speech(
        "La cita es a las 3:00 p. m. "
        "Debe llegar con anticipación."
    )

    assert spoken == (
        "La cita es a las tres de la tarde. "
        "Debe llegar con anticipación."
    )


def test_p6f999_does_not_insert_stop_inside_time_range():
    spoken = normalize_text_for_speech(
        "La franja es de 3:00 p. m. a 5:00 p. m."
    )

    assert spoken == (
        "La franja es de tres de la tarde "
        "a cinco de la tarde."
    )


def test_p6f999_converts_between_numeric_range():
    written = (
        "La terapia respiratoria dura entre 30 y 45 minutos."
    )

    spoken = normalize_text_for_speech(written)

    assert spoken == (
        "La terapia respiratoria dura entre treinta "
        "y cuarenta y cinco minutos."
    )
