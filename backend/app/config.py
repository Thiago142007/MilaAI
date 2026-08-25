from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NOVA_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8765

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_protocol: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_vision_model: str = ""
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    llm_timeout_seconds: float = 120.0

    autonomy_mode: str = "assisted"

    agent_max_steps: int = 25
    agent_step_timeout_seconds: float = 90.0
    agent_loop_detection_threshold: int = 3

    db_path: str = "data/nova.db"
    log_level: str = "INFO"
    log_dir: str = "logs"

    tavily_api_key: str = ""
    brave_api_key: str = ""

    emergency_hotkey: str = "ctrl+alt+shift+x"

    workspace_root: str = ""

    @property
    def vision_model(self) -> str:
        return self.llm_vision_model or self.llm_model

    @property
    def api_keys(self) -> list[str]:
        raw = self.llm_api_key.replace("\n", ",").replace(";", ",")
        return [k.strip() for k in raw.split(",") if k.strip()]

    @property
    def workspace_path(self) -> Path:
        raw = self.workspace_root.strip()
        return Path(raw).expanduser().resolve() if raw else PROJECT_ROOT


@lru_cache
def get_settings() -> Settings:
    return Settings()
