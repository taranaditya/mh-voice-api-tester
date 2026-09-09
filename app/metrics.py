"""Client-observable timing data. These are not phone-call latency measurements."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RequestMetrics:
    status_code: int | None = None
    content_type: str | None = None
    http_response_seconds: float | None = None
    ttft_seconds: float | None = None
    total_seconds: float | None = None
    chunk_count: int = 0
    response_characters: int = 0

    def observe_chunk(self, text: str, elapsed_seconds: float) -> None:
        if text and text.strip() and self.ttft_seconds is None:
            self.ttft_seconds = elapsed_seconds
        if text:
            self.chunk_count += 1
            self.response_characters += len(text)

    def as_dict(self) -> dict[str, object]:
        def rounded(value: float | None) -> float | None:
            return round(value, 4) if value is not None else None

        return {
            "status_code": self.status_code,
            "content_type": self.content_type,
            "http_response_seconds": rounded(self.http_response_seconds),
            "ttft_seconds": rounded(self.ttft_seconds),
            "total_seconds": rounded(self.total_seconds),
            "chunk_count": self.chunk_count,
            "response_characters": self.response_characters,
        }
