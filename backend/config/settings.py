from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    tavily_api_key: str | None = None
    ollama_api_key: str | None = None
    ollama_host: str | None = None
    ollama_model: str | None = None
    database_url: str = "sqlite+aiosqlite:///./adaptive_research_agent.db"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    @property
    def has_ollama_api_key(self) -> bool:
        return bool((self.ollama_api_key or "").strip())

    @property
    def ollama_host_url(self) -> str:
        host = (self.ollama_host or "").strip().rstrip("/")
        local_hosts = {"", "http://localhost:11434", "http://127.0.0.1:11434"}

        if self.has_ollama_api_key and host in local_hosts:
            return "https://ollama.com"
        if host.endswith("/api"):
            return host[:-4]
        return host or "http://localhost:11434"

    @property
    def ollama_model_name(self) -> str:
        model = (self.ollama_model or "").strip()
        if model:
            return model
        if self.has_ollama_api_key:
            return "gpt-oss:120b"
        return "qwen2.5:14b-instruct-q4_K_M"

    @property
    def ollama_headers(self) -> dict[str, str]:
        if not self.has_ollama_api_key:
            return {}
        return {"Authorization": f"Bearer {self.ollama_api_key.strip()}"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
