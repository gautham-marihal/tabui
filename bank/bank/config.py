"""Settings, read once from the environment, and from bank/.env when it exists (environment variables win). Defaults
suit a laptop running this folder's docker-compose database."""

import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    """KEY=value lines; blank lines and # comments are skipped, and quotes around a value are taken off."""
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


_FILE = _read_env_file(ENV_FILE)


def _setting(name: str, default: str) -> str:
    return os.environ.get(name) or _FILE.get(name) or default


@dataclass(frozen=True)
class Settings:
    # postgresql+psycopg://user:password@host:port/database
    database_url: str
    # the secret mixed into the fingerprints of login codes and ID numbers (see security.py); change it in any shared setup
    pepper: str
    # when set, the API answers only under /<key> (a private address); anything else is a 404
    access_key: str
    # the key the CRM routes (/crm/...) ask for, as "Authorization: Bearer <key>"; without one set they answer no one
    crm_api_key: str
    port: int


def load_settings() -> Settings:
    return Settings(
        database_url=_setting("BANK_DATABASE_URL", "postgresql+psycopg://bank:bank@localhost:5434/bank"),
        pepper=_setting("BANK_PEPPER", "tabui-bank-local-pepper"),
        access_key=_setting("MOCK_BANK_KEY", ""),
        crm_api_key=_setting("BANK_API_KEY", ""),
        port=int(_setting("PORT", "4310")),
    )


settings = load_settings()

# The one-time password the mock bank "sends" by SMS: always this, so a tester can key it in. Stored hashed like any other.
MOCK_OTP = _setting("MOCK_OTP", "123456")
