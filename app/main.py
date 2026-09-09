"""Local dashboard API. It never reveals the configured upstream URL."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse

from .benchmark import run_benchmark
from .client import VoiceApiClient
from .config import Settings
from .language import assess_requested_target
from .metrics import RequestMetrics
from .models import BenchmarkRequest, LanguageTestRequest, VoiceRequest, generate_test_session_id
from .runner import RunOutcome, execute_request, persist_outcome
from .scenarios import get_scenario, list_scenarios
from .storage import ResultsStore


def _sse_event(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _session_label(session_id: str) -> str:
    return f"{session_id[:5]}...{session_id[-4:]}" if len(session_id) > 9 else "redacted"


def create_app(
    settings: Settings | None = None,
    client: VoiceApiClient | None = None,
    store: ResultsStore | None = None,
) -> FastAPI:
    settings = settings or Settings.from_environment()
    store = store or ResultsStore(settings.database_path)
    client = client or VoiceApiClient(settings)
    index_file = Path(__file__).parent / "static" / "index.html"

    app = FastAPI(
        title="MH Voice API Tester",
        description="Local testing dashboard for a separately deployed MH Voice API.",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.client = client
    app.state.store = store

    @app.middleware("http")
    async def no_store_headers(request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    @app.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {"status": "ok", "voice_api_configured": settings.is_configured}

    @app.get("/api/config/status")
    async def configuration_status() -> dict[str, object]:
        return {
            "voice_api_configured": settings.is_configured,
            "request_timeout_seconds": settings.request_timeout_seconds,
            "message": "The endpoint itself is intentionally never returned by this API.",
        }

    @app.get("/api/scenarios")
    async def scenarios() -> dict[str, object]:
        return {"scenarios": list_scenarios()}

    @app.post("/api/stream")
    async def stream_voice_request(payload: VoiceRequest) -> StreamingResponse:
        request = payload.resolved_session()

        async def generate() -> AsyncIterator[str]:
            response_parts: list[str] = []
            metrics = RequestMetrics()
            error_code: str | None = None
            error_message: str | None = None
            yield _sse_event(
                "meta",
                {
                    "session_id": request.session_id or "",
                    "session_label": _session_label(request.session_id or ""),
                    "message": "Streaming begins when the upstream API sends data.",
                },
            )
            async for event in client.stream_request(request):
                metrics = event.metrics
                if event.kind == "meta":
                    yield _sse_event("upstream", {"metrics": metrics.as_dict()})
                elif event.kind == "chunk" and event.text:
                    response_parts.append(event.text)
                    yield _sse_event("chunk", {"text": event.text})
                elif event.kind == "error":
                    error_code = event.error_code
                    error_message = event.error_message
                    yield _sse_event(
                        "error",
                        {"code": error_code or "unknown", "message": error_message or "An unknown error occurred."},
                    )
                elif event.kind == "complete":
                    outcome = RunOutcome(request, metrics, "".join(response_parts), error_code, error_message)
                    record_id = persist_outcome(store, outcome)
                    yield _sse_event(
                        "complete",
                        {
                            "record_id": record_id,
                            "metrics": metrics.as_dict(),
                            "language_observation": outcome.language_observation,
                            "success": outcome.succeeded,
                        },
                    )

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    @app.post("/api/language-test")
    async def language_test(payload: LanguageTestRequest) -> dict[str, object]:
        session_a = payload.session_a or generate_test_session_id()
        session_b = payload.session_b or generate_test_session_id()
        runs = (
            ("A1: initial target in one session", session_a, payload.initial_target_lang),
            ("A2: changed target in the same session", session_a, payload.changed_target_lang),
            ("B: changed target in a new session", session_b, payload.changed_target_lang),
        )
        outcomes: list[tuple[str, RunOutcome, int]] = []
        for label, session_id, target_lang in runs:
            request = VoiceRequest(
                query=payload.query,
                source_lang=payload.source_lang,
                target_lang=target_lang,
                session_id=session_id,
                scenario="language-session-comparison",
            )
            outcome = await execute_request(client, request)
            record_id = persist_outcome(store, outcome)
            outcomes.append((label, outcome, record_id))

        return {
            "method": "Compare the changed target with the same prior session versus a new session. This is evidence collection, not a backend root-cause claim.",
            "session_a_label": _session_label(session_a),
            "session_b_label": _session_label(session_b),
            "runs": [
                {
                    "label": label,
                    "record_id": record_id,
                    "target_lang": outcome.request.target_lang,
                    "status_code": outcome.metrics.status_code,
                    "metrics": outcome.metrics.as_dict(),
                    "response": outcome.response,
                    "error_code": outcome.error_code,
                    "error_message": outcome.error_message,
                    "language_observation": assess_requested_target(outcome.response, outcome.request.target_lang),
                }
                for label, outcome, record_id in outcomes
            ],
        }

    @app.post("/api/benchmark")
    async def benchmark(payload: BenchmarkRequest) -> dict[str, object]:
        try:
            scenario = get_scenario(payload.scenario_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Unknown test scenario") from error
        outcomes, summary = await run_benchmark(
            client=client,
            store=store,
            scenario=scenario,
            repetitions=payload.repetitions,
            delay_seconds=payload.delay_seconds,
        )
        return {
            "scenario": scenario.as_dict(),
            "summary": summary,
            "runs": [
                {
                    "status_code": outcome.metrics.status_code,
                    "ttft_seconds": outcome.metrics.ttft_seconds,
                    "total_seconds": outcome.metrics.total_seconds,
                    "chunk_count": outcome.metrics.chunk_count,
                    "error_code": outcome.error_code,
                }
                for outcome in outcomes
            ],
            "note": "Every benchmark run uses a fresh generated test session to avoid mixing conversation history into the timing comparison.",
        }

    @app.get("/api/history")
    async def history(limit: int = 100) -> dict[str, object]:
        return {"runs": store.list_runs(limit=limit, include_response=False)}

    @app.get("/api/export.json")
    async def export_json() -> Response:
        return Response(
            store.export_json(),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=mh-voice-test-results.json"},
        )

    @app.get("/api/export.csv")
    async def export_csv() -> Response:
        return Response(
            store.export_csv(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=mh-voice-test-results.csv"},
        )

    return app


app = create_app()
