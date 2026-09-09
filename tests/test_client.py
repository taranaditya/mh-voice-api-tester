import asyncio
from pathlib import Path

import httpx

from app.client import VoiceApiClient
from app.config import Settings
from app.models import VoiceRequest


class ChunkedStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self):  # type: ignore[no-untyped-def]
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


async def collect(client: VoiceApiClient) -> list:
    return [event async for event in client.stream_request(VoiceRequest(query="test", source_lang="en", target_lang="en", session_id="tester-session"))]


def settings(tmp_path: Path, url: str = "https://private.invalid/api/voice/") -> Settings:
    return Settings(url, 5, tmp_path)


def test_raw_stream_is_incremental_and_metrics_are_populated(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/plain; charset=utf-8"},
            stream=ChunkedStream([b"hello ", b"world"]),
            request=request,
        )

    events = asyncio.run(collect(VoiceApiClient(settings(tmp_path), httpx.MockTransport(handler))))
    chunks = [event.text for event in events if event.kind == "chunk"]
    complete = events[-1]
    assert chunks == ["hello ", "world"]
    assert complete.kind == "complete"
    assert complete.metrics.status_code == 200
    assert complete.metrics.chunk_count == 2
    assert complete.metrics.ttft_seconds is not None
    assert complete.metrics.total_seconds is not None


def test_standard_sse_frames_are_parsed_without_synthetic_chunking(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=ChunkedStream([b"data: Hel", b"lo\n\n", b"data: world\n\n"]),
            request=request,
        )

    events = asyncio.run(collect(VoiceApiClient(settings(tmp_path), httpx.MockTransport(handler))))
    assert [event.text for event in events if event.kind == "chunk"] == ["Hello", "world"]


def test_http_error_is_reported(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, content=b"service unavailable", request=request)

    events = asyncio.run(collect(VoiceApiClient(settings(tmp_path), httpx.MockTransport(handler))))
    error = next(event for event in events if event.kind == "error")
    assert error.error_code == "http_error"
    assert "503" in (error.error_message or "")


def test_missing_endpoint_is_a_safe_configuration_error(tmp_path: Path) -> None:
    events = asyncio.run(collect(VoiceApiClient(settings(tmp_path, url=""))))
    error = next(event for event in events if event.kind == "error")
    assert error.error_code == "configuration"
    assert "VOICE_API_URL" in (error.error_message or "")
