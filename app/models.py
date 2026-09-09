"""Input models and small shared helpers for the local tester."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator


LanguageCode = Literal["hi", "mr", "en"]
Provider = Literal["RAYA", "RINGG"]


def generate_test_session_id() -> str:
    """Generate a new locally identifiable test session; never reuse production IDs."""
    return f"tester-{uuid.uuid4()}"


class VoiceRequest(BaseModel):
    """Confirmed query parameters for the MH Voice GET endpoint.

    The route accepts query, session_id, source_lang, target_lang, user_id,
    provider, and process_id. The latter three are optional advanced fields.
    """

    query: str = Field(min_length=1, max_length=4_000)
    session_id: str | None = Field(default=None, max_length=256)
    source_lang: LanguageCode = "mr"
    target_lang: LanguageCode = "mr"
    user_id: str | None = Field(default=None, max_length=256)
    provider: Provider | None = None
    process_id: str | None = Field(default=None, max_length=256)
    scenario: str | None = Field(default=None, max_length=100)

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must contain text")
        return value

    @field_validator("session_id", "user_id", "process_id", mode="before")
    @classmethod
    def blank_strings_are_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    def resolved_session(self) -> "VoiceRequest":
        if self.session_id:
            return self
        return self.model_copy(update={"session_id": generate_test_session_id()})

    def remote_params(self) -> dict[str, str]:
        """Build only confirmed upstream query parameters, omitting empty optional ones."""
        values: dict[str, str] = {
            "query": self.query,
            "session_id": self.session_id or generate_test_session_id(),
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
        }
        for name in ("user_id", "provider", "process_id"):
            value = getattr(self, name)
            if value:
                values[name] = value
        return values


class BenchmarkRequest(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=100)
    repetitions: int = Field(default=5, ge=1, le=50)
    delay_seconds: float = Field(default=0.5, ge=0, le=30)


class LanguageTestRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4_000)
    source_lang: LanguageCode = "hi"
    initial_target_lang: LanguageCode = "hi"
    changed_target_lang: LanguageCode = "en"
    session_a: str | None = Field(default=None, max_length=256)
    session_b: str | None = Field(default=None, max_length=256)

    @field_validator("query")
    @classmethod
    def language_query_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must contain text")
        return value
