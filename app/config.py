from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    app_name: str = "elvira-respirarte-agent"

    langsmith_tracing: str = "false"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str | None = None
    langsmith_project: str = "elvira-respirarte-local"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    whatsapp_verify_token: str | None = None
    whatsapp_api_url: str = "https://graph.facebook.com/v19.0"
    whatsapp_phone_number_id: str | None = None
    whatsapp_token: str | None = None
    whatsapp_sending_enabled: bool = False

    database_url: str | None = None

    kb_runtime_enabled: bool = False
    internal_admin_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()