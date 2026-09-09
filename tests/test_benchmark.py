from app.benchmark import aggregate_outcomes
from app.metrics import RequestMetrics
from app.models import VoiceRequest
from app.runner import RunOutcome


def outcome(ttft: float | None, total: float, status: int | None = 200) -> RunOutcome:
    metrics = RequestMetrics(status_code=status, ttft_seconds=ttft, total_seconds=total)
    return RunOutcome(VoiceRequest(query="test", session_id="tester-id"), metrics, "response", None if status == 200 else "http_error", None)


def test_benchmark_aggregation_uses_success_rate_and_nearest_rank_p95() -> None:
    summary = aggregate_outcomes([
        outcome(0.1, 1.0), outcome(0.2, 2.0), outcome(0.3, 3.0), outcome(0.4, 4.0), outcome(1.0, 10.0),
    ])
    assert summary["runs"] == 5
    assert summary["success_rate"] == 1.0
    assert summary["ttft_seconds"]["mean"] == 0.4
    assert summary["ttft_seconds"]["median"] == 0.3
    assert summary["ttft_seconds"]["p95"] == 1.0


def test_benchmark_excludes_missing_ttft_but_counts_failed_runs() -> None:
    summary = aggregate_outcomes([outcome(None, 1.0), outcome(0.5, 2.0, status=500)])
    assert summary["successes"] == 1
    assert summary["success_rate"] == 0.5
    assert summary["ttft_seconds"]["mean"] == 0.5
