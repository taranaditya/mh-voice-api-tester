"""Reusable full-request execution for benchmarks and language experiments."""

from __future__ import annotations

from dataclasses import dataclass

from .client import VoiceApiClient
from .language import assess_requested_target
from .metrics import RequestMetrics
from .models import VoiceRequest
from .storage import ResultsStore


@dataclass
class RunOutcome:
    request: VoiceRequest
    metrics: RequestMetrics
    response: str
    error_code: str | None
    error_message: str | None

    @property
    def language_observation(self) -> dict[str, object]:
        return assess_requested_target(self.response, self.request.target_lang)

    @property
    def succeeded(self) -> bool:
        return self.error_code is None and self.metrics.status_code is not None and 200 <= self.metrics.status_code < 300

    def public_dict(self) -> dict[str, object]:
        return {
            "scenario": self.request.scenario,
            "query": self.request.query,
            "source_lang": self.request.source_lang,
            "target_lang": self.request.target_lang,
            "status_code": self.metrics.status_code,
            "metrics": self.metrics.as_dict(),
            "response": self.response,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "language_observation": self.language_observation,
        }


async def execute_request(client: VoiceApiClient, request: VoiceRequest) -> RunOutcome:
    response_parts: list[str] = []
    metrics = RequestMetrics()
    error_code: str | None = None
    error_message: str | None = None
    async for event in client.stream_request(request):
        metrics = event.metrics
        if event.kind == "chunk" and event.text:
            response_parts.append(event.text)
        elif event.kind == "error":
            error_code = event.error_code
            error_message = event.error_message
    return RunOutcome(request, metrics, "".join(response_parts), error_code, error_message)


def persist_outcome(store: ResultsStore, outcome: RunOutcome) -> int:
    return store.save_run(
        request=outcome.request,
        metrics=outcome.metrics,
        response=outcome.response,
        error_code=outcome.error_code,
        error_message=outcome.error_message,
        language_observation=outcome.language_observation,
    )
