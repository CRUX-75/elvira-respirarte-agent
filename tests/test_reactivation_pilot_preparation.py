from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.reactivation_pilot_preparation as pilot_module
from app.models.reactivation_campaign import (
    ReactivationCampaignStatus,
    ReactivationContactStatus,
    ReactivationExclusionReason,
)
from app.services.reactivation_dry_run import ReactivationDryRunContext
from app.services.reactivation_pilot_preparation import (
    ReactivationPilotCandidate,
    prepare_reactivation_pilot_batch,
)


def build_campaign(**updates):
    values = {
        "id": "pilot-campaign-1",
        "status": ReactivationCampaignStatus.ACTIVE,
        "template_name": "reactivacion_respirarte",
        "template_language": "es_CO",
    }
    values.update(updates)
    return SimpleNamespace(**values)


def build_record(index=1, **updates):
    values = {
        "row_number": index + 1,
        "source_reference": f"hist-pilot-{index:03d}",
        "phone_original": f"30000000{index:02d}",
        "attended": "SI",
        "authorization_status": "SI",
        "doctor_review_status": "APROBADO",
    }
    values.update(updates)
    return SimpleNamespace(**values)


def build_candidate(index=1, *, context=None):
    return ReactivationPilotCandidate(
        record=build_record(index),
        context=context or ReactivationDryRunContext(),
    )


@pytest.mark.parametrize(
    "candidates",
    [
        (),
        tuple(build_candidate(index) for index in range(1, 5)),
    ],
)
def test_pilot_batch_requires_between_one_and_three_explicit_contacts(
    candidates,
):
    with pytest.raises(
        ValueError,
        match="between 1 and 3 explicit contacts",
    ):
        prepare_reactivation_pilot_batch(
            campaign=build_campaign(),
            candidates=candidates,
            default_country_code="57",
        )


def test_pilot_batch_requires_active_campaign():
    with pytest.raises(
        ValueError,
        match="campaign must be active",
    ):
        prepare_reactivation_pilot_batch(
            campaign=build_campaign(
                status=ReactivationCampaignStatus.READY,
            ),
            candidates=(build_candidate(),),
            default_country_code="57",
        )


@pytest.mark.parametrize(
    ("template_name", "template_language"),
    [
        ("revision_humana", "es_CO"),
        ("reactivacion_respirarte", "es_ES"),
    ],
)
def test_pilot_batch_requires_approved_template_contract(
    template_name,
    template_language,
):
    with pytest.raises(
        ValueError,
        match="approved reactivation template contract",
    ):
        prepare_reactivation_pilot_batch(
            campaign=build_campaign(
                template_name=template_name,
                template_language=template_language,
            ),
            candidates=(build_candidate(),),
            default_country_code="57",
        )


def test_pilot_batch_reuses_existing_full_eligibility_contract():
    decisions = prepare_reactivation_pilot_batch(
        campaign=build_campaign(),
        candidates=(build_candidate(),),
        default_country_code="57",
    )

    assert len(decisions) == 1
    assert decisions[0].status == ReactivationContactStatus.ELIGIBLE
    assert decisions[0].phone_e164 == "573000000001"
    assert decisions[0].exclusion_reasons == ()


def test_pilot_batch_excludes_existing_patient_optout():
    candidate = build_candidate(
        context=ReactivationDryRunContext(
            patient_opt_out=True,
        ),
    )

    decisions = prepare_reactivation_pilot_batch(
        campaign=build_campaign(),
        candidates=(candidate,),
        default_country_code="57",
    )

    assert len(decisions) == 1
    assert decisions[0].status == ReactivationContactStatus.EXCLUDED
    assert (
        ReactivationExclusionReason.EXISTING_OPT_OUT
        in decisions[0].exclusion_reasons
    )


def test_pilot_preparation_has_no_delivery_or_persistence_dependencies():
    source = Path(pilot_module.__file__).read_text(encoding="utf-8")

    forbidden = (
        "reactivation_template_dispatcher",
        "reactivation_template_runtime",
        "reactivation_template_transport",
        "app.services.whatsapp",
        "app.repositories",
        "try_claim_delivery",
        "send_template",
    )

    for token in forbidden:
        assert token not in source
