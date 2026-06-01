# P6-F.9.14.44 — Unavailable Date State Guard for fecha_cita Turns

## Status

CLOSED / RED-THEN-GREEN / GREEN

## Problem

When a patient provided a date during the appointment flow, the system could correctly resolve that the date was unavailable because it was a weekend, a Colombia holiday, or had no candidate slots.

However, the operational state still advanced incorrectly to:

- ST_CITA_FRANJA
- ask_preferred_time

This was unsafe because the patient was asked to choose a time window for a date that cannot be used.

## Example

With Colombia current date:

- 2026-06-01

Patient message:

- para el lunes

Resolved date:

- 2026-06-08
- Corpus Christi
- is_colombia_holiday = true
- es_dia_disponible = false
- slots_candidatos = []

Expected behavior:

- stay in ST_CITA_FECHA
- next_action = ask_preferred_date
- state_reason = unavailable_date_guard

## Implementation

Updated:

- app/graph/nodes.py
- app/services/llm.py
- tests/test_state_machine.py

The guard is applied in `node_resolve_date_context()` after deterministic date resolution, because only at that point the system knows whether the resolved date is a weekend, Colombia holiday, unavailable day, or has no candidate slots.

When the guard applies, the system forces:

- nuevo_estado = ST_CITA_FECHA
- estado_actual = ST_CITA_FECHA
- next_action = ask_preferred_date
- state_reason = unavailable_date_guard

## Response Behavior

`llm.py` now gives priority to `state_reason == "unavailable_date_guard"` inside `ask_preferred_date`.

This preserves the correct patient-facing response for unavailable dates:

- weekend: tells the patient that no consultations are handled that day
- Colombia holiday: tells the patient that the date is a holiday
- unavailable/no slots: asks the patient for another valid weekday

The generic initial appointment copy is still used only for normal appointment start / date request flows.

## Validation

Targeted validation:

- pytest tests/test_state_machine.py -q
- pytest tests/test_state_machine.py tests/test_llm_date_context.py tests/test_date_resolver.py -q

Known passing results during implementation:

- 21 passed
- 39 passed

## Safety Boundaries Preserved

Not touched:

- real POST /webhook
- WhatsApp sending
- Google Sheets
- Telegram
- n8n
- Calendar
- doctor confirmation automation
- therapy/session package tracking
