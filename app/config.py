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
    whatsapp_api_url: str = "https://graph.facebook.com/v25.0"
    whatsapp_phone_number_id: str | None = None
    whatsapp_token: str | None = None
    whatsapp_sending_enabled: bool = False

    voice_input_enabled: bool = False
    voice_replies_enabled: bool = False
    voice_reply_to_audio_only: bool = True
    voice_stt_model: str = "gpt-4o-transcribe"
    voice_stt_language: str = "es"
    voice_tts_model: str = "gpt-4o-mini-tts"
    voice_tts_voice: str = "marin"
    voice_tts_response_format: str = "opus"
    voice_max_media_bytes: int = 16777216
    voice_processing_lease_seconds: int = 300

    database_url: str | None = None

    kb_runtime_enabled: bool = False
    internal_admin_token: str | None = None

    google_sheets_enabled: bool = False
    google_sheets_spreadsheet_id: str | None = None
    google_sheets_solicitudes_cita_tab: str = "Solicitudes_Cita"
    google_service_account_json: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
