"""Controlled administrative entrypoint for P6-F.13 batch reactivation.

The preview path reads and evaluates explicit historical contacts only.
It performs no persistence, campaign activation or WhatsApp send.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.services.reactivation_batch import (
    authorize_reactivation_batch,
    build_reactivation_batch_authorization_token,
    build_reactivation_batch_preflight,
    persist_authorized_reactivation_batch,
    run_reactivation_batch,
)
from app.services.reactivation_manual_trigger import (
    activate_manual_reactivation_campaign,
    preflight_manual_reactivation,
)


_MAX_CONTACTS = 10

_ENABLE_ENV = "REACTIVATION_BATCH_ENABLED"
_CAMPAIGN_ID_ENV = "REACTIVATION_BATCH_CAMPAIGN_ID"
_CAMPAIGN_NAME_ENV = "REACTIVATION_BATCH_CAMPAIGN_NAME"
_SOURCE_REFERENCES_ENV = "REACTIVATION_BATCH_SOURCE_REFERENCES"
_DEFAULT_COUNTRY_CODE_ENV = (
    "REACTIVATION_BATCH_DEFAULT_COUNTRY_CODE"
)
_AUTHORIZATION_ENV = "REACTIVATION_BATCH_AUTHORIZATION"
_SEND_AUTHORIZED_ENV = "REACTIVATION_BATCH_SEND_AUTHORIZED"


def _parse_source_references(
    raw_value: str | None,
) -> tuple[str, ...]:
    raw = str(raw_value or "").strip()

    if not raw:
        raise ValueError(
            "At least one explicit source_reference is required"
        )

    source_references = tuple(
        value.strip()
        for value in raw.split(",")
    )

    if any(not value for value in source_references):
        raise ValueError(
            "source_reference values must be non-empty"
        )

    if len(source_references) > _MAX_CONTACTS:
        raise ValueError(
            "Maximum 10 source references are allowed"
        )

    if len(set(source_references)) != len(source_references):
        raise ValueError(
            "source_reference values must be unique"
        )

    return source_references


def _build_preflight_dependencies(
    *,
    campaign_id: str,
    default_country_code: str | None,
):
    from app.config import Settings
    from app.db.session import engine
    from app.repositories.patients import (
        find_patient_by_phone_read_only,
    )
    from app.services.reactivation_dry_run_factory import (
        build_reactivation_dry_run_dependencies,
    )

    return build_reactivation_dry_run_dependencies(
        settings=Settings(),
        campaign_id=campaign_id,
        default_country_code=default_country_code,
        engine=engine,
        patient_lookup=find_patient_by_phone_read_only,
    )



@dataclass(frozen=True)
class _ExecutionDependencies:
    campaign_repository: object
    contact_repository: object
    dispatcher: object


def _build_execution_dependencies() -> _ExecutionDependencies:
    from app.db.session import engine
    from app.repositories.reactivation_campaigns import (
        ReactivationCampaignContactRepository,
        ReactivationCampaignRepository,
    )
    from app.services.reactivation_template_factory import (
        build_reactivation_template_dispatcher,
    )

    return _ExecutionDependencies(
        campaign_repository=ReactivationCampaignRepository(
            engine
        ),
        contact_repository=ReactivationCampaignContactRepository(
            engine
        ),
        dispatcher=build_reactivation_template_dispatcher(
            engine=engine,
            enabled=True,
        ),
    )

def _print_preflight_summary(preflight) -> None:
    print(
        "reactivation_batch_preflight"
        f" requested={preflight.requested}"
        f" eligible={preflight.eligible}"
        f" excluded={preflight.excluded}"
        f" already_processed={preflight.already_processed}"
        f" estimated_sends={preflight.estimated_sends}"
    )


def main() -> int:
    if os.getenv(_ENABLE_ENV) != "1":
        print(
            "Batch reactivation disabled: "
            f"{_ENABLE_ENV} must be exactly 1."
        )
        return 2

    campaign_id = os.getenv(
        _CAMPAIGN_ID_ENV,
        "",
    ).strip()
    campaign_name = os.getenv(
        _CAMPAIGN_NAME_ENV,
        "",
    ).strip()

    if not campaign_id:
        print(
            "Batch reactivation refused: "
            f"{_CAMPAIGN_ID_ENV} is required."
        )
        return 2

    if not campaign_name:
        print(
            "Batch reactivation refused: "
            f"{_CAMPAIGN_NAME_ENV} is required."
        )
        return 2

    try:
        source_references = _parse_source_references(
            os.getenv(_SOURCE_REFERENCES_ENV)
        )
    except ValueError as exc:
        print(f"Batch reactivation refused: {exc}")
        return 2

    default_country_code = (
        os.getenv(
            _DEFAULT_COUNTRY_CODE_ENV,
            "",
        ).strip()
        or None
    )

    dependencies = _build_preflight_dependencies(
        campaign_id=campaign_id,
        default_country_code=default_country_code,
    )

    if dependencies is None:
        print(
            "Batch reactivation refused: "
            "preflight dependencies are unavailable."
        )
        return 2

    try:
        manual_preflight = preflight_manual_reactivation(
            adapter=dependencies.adapter,
            context_resolver=dependencies.context_resolver,
            default_country_code=(
                dependencies.default_country_code
            ),
        )

        if getattr(manual_preflight, "runtime_error", 0):
            raise RuntimeError("preflight runtime error")

        batch_preflight = build_reactivation_batch_preflight(
            preflight=manual_preflight,
            source_references=source_references,
        )
    except Exception:
        print(
            "Batch reactivation failed safely during preflight."
        )
        return 2

    _print_preflight_summary(batch_preflight)

    authorization_required = (
        build_reactivation_batch_authorization_token(
            campaign_id=campaign_id,
            source_references=(
                batch_preflight.source_references
            ),
        )
    )

    supplied_authorization = os.getenv(
        _AUTHORIZATION_ENV,
        "",
    ).strip()

    if not supplied_authorization:
        print()
        print("PREVIEW_ONLY=True")
        print("writes_performed=False")
        print("whatsapp_send=False")
        print(
            "authorization_required="
            f"{authorization_required}"
        )
        return 0

    if os.getenv(_SEND_AUTHORIZED_ENV) != "1":
        print(
            "Batch reactivation refused: "
            f"{_SEND_AUTHORIZED_ENV} must be exactly 1."
        )
        print("writes_performed=False")
        print("whatsapp_send=False")
        return 2

    try:
        authorization = authorize_reactivation_batch(
            campaign_id=campaign_id,
            preflight=batch_preflight,
            authorization_token=supplied_authorization,
        )
    except ValueError:
        print(
            "Batch reactivation refused: "
            "authorization is invalid."
        )
        print("writes_performed=False")
        print("whatsapp_send=False")
        return 2

    try:
        execution = _build_execution_dependencies()

        persistence = persist_authorized_reactivation_batch(
            campaign_name=campaign_name,
            authorization=authorization,
            campaign_repository=(
                execution.campaign_repository
            ),
            contact_repository=(
                execution.contact_repository
            ),
        )

        activate_manual_reactivation_campaign(
            campaign_id=campaign_id,
            campaign_repository=(
                execution.campaign_repository
            ),
        )

        batch_result = asyncio.run(
            run_reactivation_batch(
                authorization=authorization,
                contact_ids=tuple(
                    contact.id
                    for contact in persistence.contacts
                ),
                campaign_repository=(
                    execution.campaign_repository
                ),
                contact_repository=(
                    execution.contact_repository
                ),
                dispatcher=execution.dispatcher,
                send_authorized=True,
            )
        )
    except Exception:
        print(
            "Batch reactivation failed safely "
            "during authorized execution."
        )
        return 2

    print(
        "reactivation_batch_result"
        f" total={batch_result.total}"
        f" accepted={batch_result.accepted}"
        f" failed={batch_result.failed}"
        f" ignored={batch_result.ignored}"
    )

    return 0 if batch_result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
