from app.language import assess_requested_target
from app.metrics import RequestMetrics
from app.models import VoiceRequest
from app.storage import ResultsStore


def test_storage_redacts_session_ids_before_persistence(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_path = tmp_path / "results.sqlite3"
    store = ResultsStore(database_path)
    raw_session = "tester-sensitive-session-123456"
    request = VoiceRequest(query="weather", session_id=raw_session, source_lang="en", target_lang="en")
    metrics = RequestMetrics(status_code=200, ttft_seconds=0.2, total_seconds=1.1, chunk_count=2, response_characters=8)
    store.save_run(request, metrics, "response", None, None, assess_requested_target("response", "en"))

    stored_bytes = database_path.read_bytes()
    assert raw_session.encode("utf-8") not in stored_bytes
    record = store.list_runs()[0]
    assert record["session_display"].startswith("teste...")
    assert record["session_display"] != raw_session
