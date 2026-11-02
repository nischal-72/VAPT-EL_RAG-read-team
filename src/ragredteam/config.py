"""Shared settings. Loads .env; defaults match CLAUDE.md stack locks and the §7 budget."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # Stack locks
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_llm_model: str = "mistral:7b-instruct-q4_0"
    ollama_embed_model: str = "nomic-embed-text:v1.5"

    # §7 token budget
    top_k: int = 3
    chunk_tokens: int = 400
    num_predict: int = 128

    # Day 4 naive keyword filter (temporary; mutation evades this)
    defense_keyword_filter: bool = False

    # Day 5 defenses, independently toggleable
    defense_input_sanitizer: bool = False
    defense_output_guard: bool = False

    # Full chunk/prompt text in logs only when true
    debug_trace: bool = False

    # Runtime state
    chroma_dir: Path = ROOT / "chroma_db"
    collection: str = "ragredteam"

    # Exfil monitor — loopback only, per rules of engagement
    exfil_host: str = "127.0.0.1"
    exfil_port: int = 9009
    exfil_log: Path = ROOT / "exfil_log.json"

    @field_validator("ollama_host")
    @classmethod
    def _loopback_only(cls, v: str) -> str:
        if urlparse(v).hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("rules of engagement: Ollama host must be loopback")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
