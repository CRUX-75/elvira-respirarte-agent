"""Controlled administrative entrypoint for P6-F.12 manual reactivation.

Safety boundary:

- historical/prior-contact records only;
- explicit source_reference selection is mandatory;
- maximum three contacts per controlled execution;
- preflight runs before persistence;
- operator confirmation is campaign-specific;
- no automatic contact selection;
- no WhatsApp dispatcher or transport is invoked here;
- activation means campaign lifecycle ACTIVE, not message delivery.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_ENABLE_ENV = "REACTIVATION_MANUAL_TRIGGER_ENABLED"
_CAMPAIGN_ID_ENV = "REACTIVATION_MANUAL_CAMPAIGN_ID"
_CAMPAIGN_NAME_ENV = "REACTIVATION_MANUAL_CAMPAIGN_NAME"
_SOURCE_REFERENCES_ENV = "REACTIVATION_MANUAL_SOURCE_REFERENCES"
_CONFIRM_ENV = "REACTIVATION_MANUAL_CONFIRM"
_DEFAULT_COUNTRY_CODE_ENV = (
    "REACTIVATION_MANUAL_DEFAULT_COUNTRY_CODE"
)

_MAX_CONTACTS = 3


def _parse_source_references(
    raw_value: str | None,
) -> tuple[str, ...]:
    raw = str(raw_value or "").strip()

    if not raw:
        raise ValueError(
            "At least one explicit source_reference is required"
        )

    parts = tuple(
        item.strip()
        for item in raw.split(",")
    )

    if any(not item for item in parts):
        raise ValueError(
            "source_reference values must be non-empty"
        )

    if len(parts) > _MAX_CONTACTS:
        raise ValueError(
            f"Maximum {_MAX_CONTACTS} source references are allowed"
        )

    if len(set(parts)) != len(parts):
        raise ValueError(
            "source_reference values must be unique"
        )

    return parts


def _expected_confirmation(
    campaign_id: str,
) -> str:
    return f"CONFIRM:{campaign_id}"


def _print_preflight_summary(
    *,
    preflight,
    selection,
) -> None:
    print(
        "manual_reactivation_preflight"
        f" total={preflight.total}"
        f" eligible={preflight.eligible}"
        f" excluded={preflight.excluded}"
        f" invalid_input={preflight.invalid_input}"
        f" runtime_error={preflight.runtime_error}"
    )

    print(
        "manual_reactivation_selection"
        f" requested={len(selection.source_references)}"
        f" eligible={selection.eligible}"
        f" excluded={selection.excluded}"
    )

    for source_reference in selection.source_references:
        print(
            "selected_source_reference="
            f"{source_reference}"
        )


def main() -> int:
    if os.getenv(_ENABLE_ENV) != "1":
        print(
            "Manual reactivation trigger disabled: "
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
            "Manual reactivation trigger refused: "
            f"{_CAMPAIGN_ID_ENV} is required."
        )
        return 2

    if not campaign_name:
        print(
            "Manual reactivation trigger refused: "
            f"{_CAMPAIGN_NAME_ENV} is required."
        )
        return 2

    try:
        source_references = _parse_source_references(
            os.getenv(_SOURCE_REFERENCES_ENV)
        )
    except ValueError as exc:
        print(
            "Manual reactivation trigger refused: "
            f"{exc}"
        )
        return 2

    default_country_code = (
        os.getenv(
            _DEFAULT_COUNTRY_CODE_ENV,
            "",
        ).strip()
        or None
    )

    # Runtime imports intentionally happen only after administrative gates.
    from app.config import Settings
    from app.db.session import engine
    from app.repositories.patients import (
        find_patient_by_phone_read_only,
    )
    from app.repositories.reactivation_campaigns import (
        ReactivationCampaignContactRepository,
        ReactivationCampaignRepository,
    )
    from app.services.reactivation_dry_run_factory import (
        build_reactivation_dry_run_dependencies,
    )
    from app.services.reactivation_manual_trigger import (
        activate_manual_reactivation_campaign,
        persist_manual_reactivation_selection,
        preflight_manual_reactivation,
        select_manual_reactivation_items,
    )

    settings = Settings()

    dependencies = build_reactivation_dry_run_dependencies(
        settings=settings,
        campaign_id=campaign_id,
        default_country_code=default_country_code,
        engine=engine,
        patient_lookup=find_patient_by_phone_read_only,
    )

    if dependencies is None:
        print(
            "Manual reactivation trigger refused: "
            "dry-run or Google Sheets dependencies are unavailable."
        )
        return 2

    try:
        preflight = preflight_manual_reactivation(
            adapter=dependencies.adapter,
            context_resolver=dependencies.context_resolver,
            default_country_code=(
                dependencies.default_country_code
            ),
        )
    except Exception:
        print(
            "Manual reactivation trigger failed safely "
            "during preflight."
        )
        return 2

    if preflight.runtime_error:
        print(
            "Manual reactivation trigger refused: "
            "preflight contains runtime errors."
        )
        print(
            "runtime_error="
            f"{preflight.runtime_error}"
        )
        return 2

    try:
        selection = select_manual_reactivation_items(
            preflight=preflight,
            source_references=source_references,
            max_contacts=_MAX_CONTACTS,
        )
    except ValueError as exc:
        print(
            "Manual reactivation trigger refused: "
            f"{exc}"
        )
        return 2

    _print_preflight_summary(
        preflight=preflight,
        selection=selection,
    )

    if (
        selection.excluded
        or selection.eligible
        != len(selection.source_references)
    ):
        print(
            "Manual reactivation trigger refused: "
            "every explicitly selected contact must be eligible."
        )
        print("writes_performed=False")
        print("whatsapp_send=False")
        return 2

    expected_confirmation = _expected_confirmation(
        campaign_id
    )

    confirmation = os.getenv(
        _CONFIRM_ENV,
        "",
    ).strip()

    if confirmation != expected_confirmation:
        print()
        print("PREVIEW_ONLY=True")
        print("writes_performed=False")
        print("whatsapp_send=False")
        print(
            "confirmation_required="
            f"{expected_confirmation}"
        )
        return 0

    campaign_repository = ReactivationCampaignRepository(
        engine
    )
    contact_repository = (
        ReactivationCampaignContactRepository(
            engine
        )
    )

    existing_campaign = campaign_repository.get_by_id(
        campaign_id
    )

    if existing_campaign is None:
        try:
            persistence = (
                persist_manual_reactivation_selection(
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    selection=selection,
                    campaign_repository=campaign_repository,
                    contact_repository=contact_repository,
                )
            )
        except Exception as exc:
            print(
                "Manual reactivation persistence refused: "
                f"{type(exc).__name__}"
            )
            return 2

        persisted_contacts = persistence.contacts

    else:
        if existing_campaign.name != campaign_name:
            print(
                "Manual reactivation trigger refused: "
                "existing campaign name does not match."
            )
            return 2

        persisted = []

        for record, decision in selection.prepared_items:
            phone_e164 = str(
                decision.phone_e164 or ""
            ).strip()

            existing_contact = (
                contact_repository
                .get_by_campaign_phone_read_only(
                    campaign_id=campaign_id,
                    phone_e164=phone_e164,
                )
            )

            if existing_contact is None:
                print(
                    "Manual reactivation trigger refused: "
                    "campaign exists but selected contact "
                    "is not persisted."
                )
                return 2

            if (
                existing_contact.source_reference
                != record.source_reference
            ):
                print(
                    "Manual reactivation trigger refused: "
                    "persisted contact source_reference mismatch."
                )
                return 2

            persisted.append(existing_contact)

        persisted_contacts = tuple(persisted)

    try:
        campaign = activate_manual_reactivation_campaign(
            campaign_id=campaign_id,
            campaign_repository=campaign_repository,
        )
    except Exception as exc:
        print(
            "Manual reactivation activation refused: "
            f"{type(exc).__name__}"
        )
        return 2

    print()
    print("MANUAL_PREPARATION=COMPLETED")
    print(f"campaign_id={campaign.id}")
    print(f"campaign_status={campaign.status.value}")
    print(
        "persisted_contacts="
        f"{len(persisted_contacts)}"
    )
    print("whatsapp_send=False")
    print("provider_message_id_created=False")

    return 0


if __name__ == "__main__":
    main()
