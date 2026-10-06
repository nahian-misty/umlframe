from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_DATABASE_URL = "mysql+pymysql://mistyy@localhost:3306/umlframe"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())


_load_env_file(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    jwt_secret_key: str = field(
        default_factory=lambda: os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    )
    # OpenRouter powers the optional LLM method implementation; with no key or no models the
    # feature reports itself as unavailable instead of failing at request time.
    openrouter_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", "").strip()
    )
    openrouter_models: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            model.strip()
            for model in os.environ.get("OPENROUTER_MODELS", "").split(",")
            if model.strip()
        )
    )
    openrouter_base_url: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    )


settings = Settings()
