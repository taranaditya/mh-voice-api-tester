"""Local configuration. The upstream endpoint is deliberately never logged."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    voice_api_url: str
    request_timeout_seconds: float
    data_dir: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        timeout = float(os.getenv("VOICE_API_TIMEOUT_SECONDS", "45"))
        if timeout <= 0:
            raise ValueError("VOICE_API_TIMEOUT_SECONDS must be greater than zero")
        data_dir = Path(os.getenv("TESTER_DATA_DIR", "./data")).resolve()
        return cls(
            voice_api_url=os.getenv("VOICE_API_URL", "").strip(),
            request_timeout_seconds=timeout,
            data_dir=data_dir,
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "mh_voice_tester.sqlite3"

    @property
    def is_configured(self) -> bool:
        return bool(self.voice_api_url)
