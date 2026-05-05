from app.config import settings


APP_VERSION = "0.2.1"


def _configured(value: str | None) -> bool:
    return bool(value and value.strip())


def build_ready_report() -> dict:
    hard_failures: list[str] = []

    database_configured = _configured(settings.database_url)
    openai_configured = _configured(settings.openai_api_key)
    whatsapp_configured = (
        _configured(settings.whatsapp_verify_token)
        and _configured(settings.whatsapp_phone_number_id)
        and _configured(settings.whatsapp_token)
    )

    langsmith_tracing_enabled = str(settings.langsmith_tracing).lower() == "true"
    langsmith_configured = (
        langsmith_tracing_enabled
        and _configured(settings.langsmith_api_key)
        and _configured(settings.langsmith_project)
    )

    if not database_configured:
        hard_failures.append("database_url_missing")

    if not openai_configured:
        hard_failures.append("openai_config_missing")

    if not whatsapp_configured:
        hard_failures.append("whatsapp_config_missing")

    status = "ready" if not hard_failures else "not_ready"

    return {
        "status": status,
        "service": settings.app_name,
        "environment": settings.app_env,
        "app_version": APP_VERSION,
        "whatsapp_sending_enabled": settings.whatsapp_sending_enabled,
        "kb_runtime_enabled": settings.kb_runtime_enabled,
        "database": {
            "configured": database_configured,
        },
        "repositories": {
            "patients": "configured",
            "interactions": "configured",
            "processed_messages": "configured",
            "kb": "configured",
        },
        "langsmith": {
            "tracing_enabled": langsmith_tracing_enabled,
            "project": settings.langsmith_project,
            "configured": langsmith_configured,
        },
        "openai_configured": openai_configured,
        "whatsapp_configured": whatsapp_configured,
        "hard_failures": hard_failures,
        "safety": {
            "real_whatsapp_sending_allowed": settings.whatsapp_sending_enabled,
            "p6a_rule": "WHATSAPP_SENDING_ENABLED must remain false during P6-A",
        },
    }
