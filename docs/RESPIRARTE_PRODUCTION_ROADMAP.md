
## Clarification — Telegram Pagos MVP

The existing n8n workflow named `Respirarte — Telegram Pagos MVP` is not part of Elvira and is not part of the appointment scheduling lifecycle.

It is a separate doctor-facing administrative workflow.

Purpose:

Allow Dra. D'Aleman to register received payments quickly through Telegram, potentially by voice, without opening Google Sheets manually.

Example doctor input:

"Paciente María López pagó 80.000 por terapia respiratoria."

Expected workflow:

Telegram message or voice input
→ n8n extracts payment data
→ payment row is appended to Respirarte CRM / Pagos tab
→ Telegram confirmation is sent back to the doctor

This workflow may remain in n8n because it is auxiliary administrative tooling.

It must stay separate from:

- Elvira patient conversation flow
- AppointmentRequest lifecycle
- doctor appointment approval
- appointment state transitions
- WhatsApp patient messaging

