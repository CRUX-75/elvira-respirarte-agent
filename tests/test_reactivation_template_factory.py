from unittest.mock import Mock

import app.services.reactivation_template_factory as factory_module
from app.repositories.reactivation_campaigns import (
    ReactivationCampaignContactRepository,
)
from app.services.reactivation_campaign_service import (
    ReactivationCampaignContactService,
)
from app.services.reactivation_template_dispatcher import (
    DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE,
    DEFAULT_REACTIVATION_TEMPLATE_NAME,
    ReactivationTemplateDispatcher,
)
from app.services.reactivation_template_factory import (
    build_reactivation_template_dispatcher,
)


def test_factory_builds_real_productive_dependencies_disabled_by_default():
    engine = Mock()

    dispatcher = build_reactivation_template_dispatcher(
        engine=engine,
    )

    assert isinstance(dispatcher, ReactivationTemplateDispatcher)
    assert dispatcher.config.enabled is False
    assert (
        dispatcher.config.template_name
        == DEFAULT_REACTIVATION_TEMPLATE_NAME
    )
    assert (
        dispatcher.config.template_language
        == DEFAULT_REACTIVATION_TEMPLATE_LANGUAGE
    )

    assert isinstance(
        dispatcher.contact_service,
        ReactivationCampaignContactService,
    )
    assert isinstance(
        dispatcher.contact_service.repository,
        ReactivationCampaignContactRepository,
    )
    assert dispatcher.contact_service.repository.engine is engine

    assert (
        dispatcher.send_template
        is factory_module.send_reactivation_whatsapp_template
    )

    engine.begin.assert_not_called()
    engine.connect.assert_not_called()


def test_factory_requires_explicit_enablement_for_productive_dispatch():
    dispatcher = build_reactivation_template_dispatcher(
        engine=Mock(),
        enabled=True,
    )

    assert dispatcher.config.enabled is True


def test_factory_build_has_no_io_or_dispatch_side_effects(monkeypatch):
    engine = Mock()
    sender = Mock()

    monkeypatch.setattr(
        factory_module,
        "send_reactivation_whatsapp_template",
        sender,
    )

    dispatcher = build_reactivation_template_dispatcher(
        engine=engine,
        enabled=True,
    )

    assert dispatcher.config.enabled is True
    assert dispatcher.send_template is sender

    sender.assert_not_called()
    engine.begin.assert_not_called()
    engine.connect.assert_not_called()


def test_factory_does_not_execute_batch_or_wire_application_runtime():
    source = factory_module.__file__

    with open(source, encoding="utf-8") as handle:
        module_source = handle.read()

    forbidden = (
        "app.main",
        "reactivation_template_runtime",
        "dispatch_reactivation_contacts_best_effort",
        "prepare_reactivation_pilot_batch",
        ".dispatch(",
    )

    for token in forbidden:
        assert token not in module_source
