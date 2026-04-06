from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Google AI
    gemini_api_key: str = ""

    # Database
    gcp_project_id: str = "my-first-project"
    gcp_region: str = "us-central1"
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "nexus_db"
    db_user: str = "nexus_user"
    db_password: str = ""

    # Google Calendar
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8080/api/v1/auth/google/callback"
    google_calendar_credentials_path: str = "credentials/google_calendar.json"

    # Asana
    asana_access_token: str = ""
    asana_workspace_gid: str = ""
    asana_default_project_gid: str = ""

    # Slack
    slack_bot_token: str = ""
    slack_default_channel: str = "#general"

    # App
    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-in-prod"
    app_port: int = 8080
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # Agent
    agent_model: str = "gemini-1.5-flash"
    agent_max_turns: int = 10
    workflow_timeout_seconds: int = 120

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
