"""Sequential benchmark runner and transparent client-observable aggregation."""

from __future__ import annotations

import asyncio
import math
import statistics
from typing import Iterable

from .client import VoiceApiClient
from .models import VoiceRequest, generate_test_session_id
from .runner import RunOutcome, execute_request, persist_outcome
from .scenarios import Scenario
from .storage import ResultsStore


def _summary(values: Iterable[float | None]) -> dict[str, float | None]:
    usable = sorted(value for value in values if value is not None)
    if not usable:
        return {"min": None, "max": None, "mean": None, "median": None, "p95": None}
    p95_index = max(0, math.ceil(len(usable) * 0.95) - 1)
    return {
        "min": round(usable[0], 4),
        "max": round(usable[-1], 4),
        "mean": round(statistics.mean(usable), 4),
        "median": round(statistics.median(usable), 4),
        "p95": round(usable[p95_index], 4),
    }


def aggregate_outcomes(outcomes: list[RunOutcome]) -> dict[str, object]:
    successes = sum(outcome.succeeded for outcome in outcomes)
    return {
        "runs": len(outcomes),
        "successes": successes,
        "success_rate": round(successes / len(outcomes), 4) if outcomes else 0.0,
        "ttft_seconds": _summary(outcome.metrics.ttft_seconds for outcome in outcomes),
        "total_seconds": _summary(outcome.metrics.total_seconds for outcome in outcomes),
        "http_response_seconds": _summary(outcome.metrics.http_response_seconds for outcome in outcomes),
    }


async def run_benchmark(
    client: VoiceApiClient,
    store: ResultsStore,
    scenario: Scenario,
    repetitions: int,
    delay_seconds: float,
) -> tuple[list[RunOutcome], dict[str, object]]:
    outcomes: list[RunOutcome] = []
    for index in range(repetitions):
        request = VoiceRequest(
            query=scenario.query,
            source_lang=scenario.source_lang,
            target_lang=scenario.target_lang,
            session_id=generate_test_session_id(),
            scenario=f"benchmark:{scenario.id}",
        )
        outcome = await execute_request(client, request)
        persist_outcome(store, outcome)
        outcomes.append(outcome)
        if index < repetitions - 1 and delay_seconds:
            await asyncio.sleep(delay_seconds)
    return outcomes, aggregate_outcomes(outcomes)
