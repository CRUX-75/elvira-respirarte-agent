from inspect import getsource

from app.repositories.reactivation_campaigns import (
    ReactivationCampaignContactRepository,
)


def repository_source() -> str:
    return getsource(
        ReactivationCampaignContactRepository.record_response_event
    )


def test_duplicate_inbound_lookup_is_scoped_to_original_contact():
    source = repository_source()

    existing_event_lookup = source.split(
        "FROM reactivation_campaign_response_events",
        1,
    )[1]

    assert "AND contact_id = :contact_id" in (
        existing_event_lookup
    )


def test_response_summary_is_updated_only_by_latest_response():
    source = repository_source()

    update_block = source.split(
        "UPDATE reactivation_campaign_contacts",
        1,
    )[1].split(
        "RETURNING id",
        1,
    )[0]

    normalized_update_block = " ".join(
        update_block.split()
    )

    ordering_guard = (
        "responded_at IS NULL "
        "OR COALESCE(:received_at, NOW()) >= responded_at"
    )

    assert ordering_guard in normalized_update_block

    for field in (
        "inbound_whatsapp_message_id",
        "response_classification",
        "response_safe_reason",
        "response_requires_human_escalation",
        "responded_at",
    ):
        assert (
            f"{field} = CASE"
            in normalized_update_block
        )

    assert (
        "WHEN :campaign_opt_out_requested "
        "THEN 'opted_out'"
    ) in normalized_update_block
    assert "ELSE status" in normalized_update_block
