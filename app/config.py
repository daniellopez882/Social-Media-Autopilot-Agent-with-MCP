"""
Configuration.

The previous code had no settings module. Three facts about how it read the
environment explain most of what went wrong:

* ``MOCK_MODE = os.getenv("MOCK_MODE", "true")`` -- the default was *on*. An
  operator who never set the variable ran a system whose scheduler returned
  ``"MOCK SCHEDULED: All posts queued for 9 AM."`` and whose API reported that
  as success.
* It was read once, at import time, in ``app/graphs/nodes.py``. Setting the
  variable after any import changed nothing, which is why the root test
  scripts set it inside ``if __name__ == "__main__"`` and it had no effect
  under pytest.
* ``except ImportError: MOCK_MODE = True`` -- if ``crewai`` was not
  installable (it declares ``<3.14``, and this machine's default Python is
  3.14), the system silently became a mock system rather than failing.

Mock mode is now opt-in, read at call time, and refused in production.
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_API_KEY = ""
DEFAULT_MODEL = "gpt-4o"

_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Off unless asked for. See the module docstring.
    MOCK_MODE: bool = False

    # Required on every state-changing route. Empty means unauthenticated,
    # which is refused outside development.
    API_KEY: str = INSECURE_API_KEY

    # Comma-separated origins. Empty by default: the API serves the dashboard
    # itself, so browser requests are same-origin and no CORS is needed.
    CORS_ALLOW_ORIGINS: str = ""

    # Model providers. Only OpenAI is wired; the README used to describe a
    # Claude/GPT-4 mix that the code never implemented.
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = DEFAULT_MODEL

    # Social platform credentials. Present or absent, the tools that would use
    # them are not implemented; see app/tools/social_tools.py.
    TWITTER_API_KEY: str = ""
    META_ACCESS_TOKEN: str = ""
    BUFFER_ACCESS_TOKEN: str = ""

    # Pending approvals live in process memory. They expire rather than
    # accumulating for the life of the process.
    APPROVAL_TTL_SECONDS: int = Field(default=24 * 3600, ge=60)
    APPROVAL_MAX_PENDING: int = Field(default=1000, ge=1)

    MAX_CONTENT_CHARS: int = Field(default=20_000, ge=100)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return _split(self.CORS_ALLOW_ORIGINS)

    @property
    def has_api_key(self) -> bool:
        return bool(self.API_KEY.strip())

    @field_validator("MOCK_MODE", mode="before")
    @classmethod
    def _blank_means_off(cls, value: object) -> object:
        # `MOCK_MODE=` with nothing after it is a plausible line in a .env
        # file. pydantic would refuse it as an unparseable boolean at import
        # time; treat it as unset, which is off.
        if isinstance(value, str) and not value.strip():
            return False
        return value

    @model_validator(mode="after")
    def _normalise(self) -> Settings:
        level = self.LOG_LEVEL.strip().upper()
        if level not in _LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL={self.LOG_LEVEL!r} is not one of {sorted(_LOG_LEVELS)}")
        object.__setattr__(self, "LOG_LEVEL", level)
        return self

    def problems(self) -> list[str]:
        """
        Everything that makes this configuration unfit to serve.

        Returned as a list rather than raised one at a time, so an operator
        sees the whole picture on the first failed start.
        """
        found: list[str] = []
        if self.is_production and self.MOCK_MODE:
            found.append(
                "MOCK_MODE is on in production. The system would report scheduled "
                "posts that were never scheduled."
            )
        if self.is_production and not self.has_api_key:
            found.append(
                "API_KEY is not set. Every state-changing route would be open. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        if not self.MOCK_MODE and not self.OPENAI_API_KEY.strip():
            found.append("OPENAI_API_KEY is not set and MOCK_MODE is off; no model can be built.")
        return found

    def validate_or_raise(self) -> None:
        found = self.problems()
        if found:
            raise ValueError("Invalid configuration:\n  - " + "\n  - ".join(found))


settings = Settings()
