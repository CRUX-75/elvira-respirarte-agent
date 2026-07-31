import asyncio
from unittest.mock import Mock

from app.services.reactivation_template_dispatcher import (
    ReactivationTemplateDispatchResult,
)
from app.services.reactivation_template_runtime import (
    dispatch_reactivation_contacts_best_effort,
)


def test_batch_runtime_isolates_one_contact_failure_and_continues():
    dispatcher = Mock()

    async def dispatch(*, contact_id):
        if contact_id == "contact-2":
            raise RuntimeError("sensitive provider or persistence detail")

        return ReactivationTemplateDispatchResult(
            outcome="accepted",
            contact_id=contact_id,
            provider_message_id=f"wamid.{contact_id}",
            retryable=False,
        )

    dispatcher.dispatch.side_effect = dispatch

    result = asyncio.run(
        dispatch_reactivation_contacts_best_effort(
            contact_ids=[
                "contact-1",
                "contact-2",
                "contact-3",
            ],
            dispatcher=dispatcher,
        )
    )

    assert result.total == 3
    assert result.accepted == 2
    assert result.failed == 1
    assert result.ignored == 0

    assert [item.contact_id for item in result.results] == [
        "contact-1",
        "contact-2",
        "contact-3",
    ]
    assert [item.outcome for item in result.results] == [
        "accepted",
        "runtime_error",
        "accepted",
    ]

    failed_result = result.results[1]
    assert failed_result.provider_message_id is None
    assert failed_result.error_category == "dispatch_runtime_error"
    assert failed_result.retryable is True

    assert "sensitive" not in repr(result)
    assert "provider or persistence detail" not in repr(result)

    assert dispatcher.dispatch.call_count == 3
    dispatcher.dispatch.assert_any_call(contact_id="contact-1")
    dispatcher.dispatch.assert_any_call(contact_id="contact-2")
    dispatcher.dispatch.assert_any_call(contact_id="contact-3")
