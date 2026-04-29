"""Configuration loaded from environment / .env via pydantic-settings.

All secrets, hostnames, and tunables flow through this module. No other
file in Foreman is allowed to read os.environ directly.
"""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_data_dir
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM ---
    anthropic_api_key: SecretStr = Field(..., alias="ANTHROPIC_API_KEY")
    foreman_llm_model: str = Field("claude-sonnet-4-6", alias="FOREMAN_LLM_MODEL")

    # --- GitHub ---
    github_token: SecretStr = Field(..., alias="GITHUB_TOKEN")
    github_host: str = Field("api.github.com", alias="GITHUB_HOST")
    github_user: str = Field(..., alias="GITHUB_USER")

    # --- Jira ---
    jira_base_url: str = Field(..., alias="JIRA_BASE_URL")
    jira_email: str = Field(..., alias="JIRA_EMAIL")
    jira_api_token: SecretStr = Field(..., alias="JIRA_API_TOKEN")

    # --- Slack ---
    slack_bot_token: SecretStr | None = Field(None, alias="SLACK_BOT_TOKEN")
    slack_user_token: SecretStr | None = Field(None, alias="SLACK_USER_TOKEN")
    slack_team_id: str | None = Field(None, alias="SLACK_TEAM_ID")
    slack_user_id: str | None = Field(None, alias="SLACK_USER_ID")

    # --- Scheduler ---
    foreman_briefing_time: str = Field("08:30", alias="FOREMAN_BRIEFING_TIME")
    foreman_briefing_timezone: str = Field("America/Los_Angeles", alias="FOREMAN_BRIEFING_TIMEZONE")
    foreman_pr_poll_minutes: int = Field(10, alias="FOREMAN_PR_POLL_MINUTES")
    foreman_jira_poll_minutes: int = Field(15, alias="FOREMAN_JIRA_POLL_MINUTES")
    foreman_slack_poll_minutes: int = Field(10, alias="FOREMAN_SLACK_POLL_MINUTES")

    # --- Storage ---
    foreman_data_dir: Path | None = Field(None, alias="FOREMAN_DATA_DIR")

    # --- Observability ---
    foreman_log_level: str = Field("INFO", alias="FOREMAN_LOG_LEVEL")
    foreman_debug: bool = Field(False, alias="FOREMAN_DEBUG")

    @property
    def data_dir(self) -> Path:
        """Resolved data directory. Honors override or falls back to platform default."""
        if self.foreman_data_dir is not None:
            return self.foreman_data_dir
        return Path(user_data_dir(appname="foreman", appauthor=False))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "foreman.db"


def load_settings() -> Settings:
    """Single point of entry for settings. Cache at the call site if needed."""
    return Settings()  # type: ignore[call-arg]
