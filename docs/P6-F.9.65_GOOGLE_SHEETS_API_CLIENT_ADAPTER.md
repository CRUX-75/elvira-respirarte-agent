# P6-F.9.65 — Google Sheets API Client Adapter

## Status

SPEC / PRE-IMPLEMENTATION

## Objective

Create the real Google Sheets API client adapter required by the human review inbox writer.

This phase only prepares the client.

It must not connect the writer to the appointment runtime yet.

## Scope

Implement a minimal Google Sheets client compatible with the existing writer protocol:

- get_values(spreadsheet_id, range_name)
- append_row(spreadsheet_id, range_name, row)
- update_row(spreadsheet_id, range_name, row_number, row)

The client should authenticate using service account JSON from configuration.

## Required Dependencies

Use official Google libraries:

- google-api-python-client
- google-auth

## Safety Baseline

GOOGLE_SHEETS_ENABLED remains false by default.

This phase must not write to real Google Sheets automatically.

Tests must use mocks/fakes only.

## Out Of Scope

Do not implement:

- runtime wiring
- automatic writes from /webhook
- doctor action reader
- patient notification sending
- Telegram
- n8n
- Calendar
- campaigns
- doctor confirmation automation

## Closure Criteria

- Spec exists.
- Dependencies added.
- Tests added RED first.
- Minimal client implemented.
- Targeted tests GREEN.
- Full suite GREEN.
- No real Google Sheets write performed.
- Working tree clean.
