from functools import lru_cache
from hashlib import md5
from pathlib import Path
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
WEBAPP_DIST_INDEX = BASE_DIR / "telegram-site" / "frontend" / "dist" / "index.html"


def webapp_cache_bust() -> str:
    """Changes after each frontend build so Telegram reloads Mini App assets."""
    if WEBAPP_DIST_INDEX.is_file():
        return md5(WEBAPP_DIST_INDEX.read_bytes()).hexdigest()[:8]
    return md5(b"no-build").hexdigest()[:8]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bot API
    telegram_bot_token: str = ""
    telegram_admin_chat_id: int | None = None
    telegram_admin_ids: str = ""
    admin_analytics_live: bool = False
    support_telegram_username: str = "taton4i"

    # Telethon
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_phone: str = ""
    telethon_session_name: str = "lumo_session"
    # Railway: строка сессии (переживает redeploy без Volume). Получить: python scripts/export_telethon_session.py
    telethon_session_string: str = ""
    database_url: str = f"sqlite+aiosqlite:///{(BASE_DIR / 'lumo.db').as_posix()}"

    # LLM — gemini (Google) или openai (Groq, OpenRouter, Ollama и др.)
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.groq.com/openai/v1"
    openai_model: str = "llama-3.1-8b-instant"
    # Отдельный Groq-ключ только для категоризации интересов пользователей (не делит лимит с мониторингом)
    openai_user_api_key: str = ""
    llm_user_max_concurrent: int = 2
    llm_user_request_delay_seconds: float = 0.5

    # Limits & intervals
    max_user_channels: int = 5
    monitor_interval_minutes: int = 1440
    monitor_initial_posts_limit: int = 10
    monitor_initial_max_age_days: int = 7
    catalog_no_deadline_max_age_days: int = 7
    llm_max_concurrent: int = 1
    llm_processor_interval_seconds: int = 1200
    llm_health_check_interval_seconds: int = 3600
    llm_pending_scan_limit: int = 20
    llm_max_pairs_per_cycle: int = 2
    llm_max_message_age_days: int = 3
    llm_reanalyze_recent_count: int = 10
    llm_onboarding_max_pairs: int = 3
    llm_onboarding_seed_scan_limit: int = 10
    llm_classify_batch_limit: int = 5
    llm_backfill_batch_limit: int = 5
    llm_enable_pair_relevance: bool = False
    llm_interest_categorization: bool = True
    llm_request_delay_seconds: float = 5.0
    llm_429_max_retries: int = 1
    llm_429_retry_base_seconds: float = 8.0
    llm_health_fail_cache_seconds: int = 120
    llm_restart_cooldown_seconds: int = 300
    bot_polling_timeout_seconds: int = 25
    bot_http_timeout_seconds: float = 65.0
    notification_digest_size: int = 3
    notification_digest_max_flush: int = 3
    digest_cooldown_hours: int = 12
    catalog_notify_min_score: float = 3.0
    telethon_request_delay_seconds: float = 2.0
    require_public_channels: bool = True
    ai_search_daily_limit: int = 3
    subscription_reminder_interval_seconds: int = 3600

    # Partner B2B (AI Startify) — subscriptions_enforced=false пока бот бесплатный
    partner_api_key: str = ""
    subscriptions_enforced: bool = False
    subscription_preview_enabled: bool = True
    startify_checkout_url: str = ""
    # Lumo → Startify: POST новых конкурсов после мониторинга (см. docs/STARTIFY_CATALOG_WEBHOOK.md)
    startify_catalog_webhook_url: str = ""
    startify_catalog_push_enabled: bool = True
    kaspi_payment_phone: str = "+7 775 499 8313"

    # Training data (для будущего fine-tuning)
    training_data_enabled: bool = True
    training_data_dir: Path = BASE_DIR / "data" / "training"

    # Paths
    seed_channels_file: Path = BASE_DIR / "data" / "seed_channels.txt"
    log_dir: Path = BASE_DIR / "logs"

    # REST API (AI Startify Grants)
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:5173,http://localhost:3000"
    api_access_token: str = ""
    api_allow_dev_auth: bool = False
    google_oauth_client_id: str = ""
    web_auth_secret: str = ""
    web_admin_emails: str = ""
    api_enabled: bool = True
    auto_build_webapp: bool = True
    serve_mini_app: bool = True
    public_base_url: str = ""
    telegram_bot_username: str = "LumoAI1bot"
    telegram_webapp_url: str = ""
    mini_app_menu_text: str = "Open"
    community_telegram_handle: str = "Lumo Community"
    community_telegram_url: str = "https://t.me/+hA0CwgbStLI0MGRi"

    # full = bot + API + monitor + LLM; api = только REST (Mini App); worker = monitor + LLM без polling
    lumo_mode: str = "full"
    # На worker-сервисе включить бота: ENABLE_BOT_POLLING=true (второй Railway-сервис)
    enable_bot_polling: bool = False
    skip_instance_lock: bool = False
    telethon_session_path: str = ""

    @model_validator(mode="after")
    def railway_defaults(self) -> "Settings":
        """Railway: skip file lock; не форсируем full — можно split api + worker."""
        import os

        on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))
        if on_railway and not self.skip_instance_lock:
            object.__setattr__(self, "skip_instance_lock", True)
        return self

    @property
    def resolved_telethon_session_path(self) -> Path:
        if self.telethon_session_path.strip():
            return Path(self.telethon_session_path.strip())
        return BASE_DIR / self.telethon_session_name

    @property
    def is_api_only(self) -> bool:
        return self.lumo_mode.lower() == "api"

    @property
    def is_worker(self) -> bool:
        return self.lumo_mode.lower() in ("worker", "full")

    @property
    def is_bot_polling(self) -> bool:
        mode = self.lumo_mode.lower()
        if mode == "api":
            return False
        if mode == "worker":
            return self.enable_bot_polling
        return mode in ("bot", "full")

    @property
    def is_railway(self) -> bool:
        import os

        return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def is_admin(self, chat_id: int) -> bool:
        try:
            uid = int(chat_id)
        except (TypeError, ValueError):
            return False
        if self.telegram_admin_chat_id is not None and uid == int(self.telegram_admin_chat_id):
            return True
        for part in self.telegram_admin_ids.replace(";", ",").split(","):
            text = part.strip()
            if text and text.isdigit() and uid == int(text):
                return True
        return False

    def is_web_admin(self, email: str | None) -> bool:
        if not email or not self.web_admin_emails.strip():
            return False
        normalized = email.strip().lower()
        for part in self.web_admin_emails.replace(";", ",").split(","):
            text = part.strip().lower()
            if text and text == normalized:
                return True
        return False

    def user_is_admin(self, telegram_id: int, email: str | None = None) -> bool:
        return self.is_admin(telegram_id) or self.is_web_admin(email)

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider.lower() == "openai":
            return bool(self.openai_api_key)
        return bool(self.gemini_api_key)

    @property
    def llm_user_configured(self) -> bool:
        if self.llm_provider.lower() == "openai":
            return bool(self.openai_user_api_key_effective)
        return bool(self.gemini_api_key)

    @property
    def openai_user_api_key_effective(self) -> str:
        return (self.openai_user_api_key or self.openai_api_key).strip()

    @property
    def llm_model_name(self) -> str:
        if self.llm_provider.lower() == "openai":
            return self.openai_model
        return self.gemini_model

    @property
    def support_contact(self) -> str:
        name = self.support_telegram_username.strip().lstrip("@")
        return f"@{name}" if name else "@taton4i"

    @property
    def telegram_webapp_base_url(self) -> str:
        """HTTPS URL for Telegram WebApp buttons (no query string — BotFather domain match)."""
        explicit = (self.telegram_webapp_url or "").strip().rstrip("/")
        if explicit:
            return explicit
        base = (self.public_base_url or "").strip().rstrip("/")
        if not base:
            return ""
        if not base.endswith("/app"):
            base = f"{base}/app"
        return base

    @property
    def resolved_webapp_url(self) -> str:
        base = self.telegram_webapp_base_url
        if not base:
            return ""
        return f"{base}/?v={webapp_cache_bust()}"

    @field_validator("telegram_api_id", mode="before")
    @classmethod
    def empty_api_id_to_zero(cls, value: Any) -> Any:
        if value is None or value == "":
            return 0
        return value

    @field_validator("telegram_admin_chat_id", mode="before")
    @classmethod
    def empty_admin_id_to_none(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @field_validator("database_url", mode="after")
    @classmethod
    def resolve_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql+asyncpg://", 1)
        elif value.startswith("postgresql://") and "+asyncpg" not in value:
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        relative_prefix = "sqlite+aiosqlite:///./"
        if value.startswith(relative_prefix):
            rel = value[len(relative_prefix) :]
            abs_path = (BASE_DIR / rel).resolve()
            return f"sqlite+aiosqlite:///{abs_path.as_posix()}"
        from db.supabase_url import normalize_supabase_database_url

        return normalize_supabase_database_url(value)

    @field_validator("lumo_mode", mode="before")
    @classmethod
    def normalize_lumo_mode(cls, value: Any) -> str:
        text = str(value or "full").strip().lower()
        if text not in ("full", "worker", "bot"):
            return "full"
        return text

    @field_validator("gemini_model", mode="before")
    @classmethod
    def sanitize_gemini_model(cls, value: Any) -> str:
        if not value:
            return "gemini-2.5-flash"
        text = str(value).strip().split("#")[0].strip()
        return text.split()[0] if text.split() else "gemini-2.5-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
