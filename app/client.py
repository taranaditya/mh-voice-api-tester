"""Safe, incremental client for the configured private MH Voice endpoint."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import AsyncIterator, Literal
from urllib.parse import urlparse

import httpx

from .config import Settings
from .metrics import RequestMetrics
from .models import VoiceRequest
from .streaming import AdaptiveStreamParser


EventKind = Literal["meta", "chunk", "error", "complete"]


@dataclass
class ClientEvent:
    kind: EventKind
    metrics: RequestMetrics
    text: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class VoiceApiClient:
    """Client that deliberately avoids logging URLs, params, headers, and bodies."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    async def stream_request(self, request: VoiceRequest) -> AsyncIterator[ClientEvent]:
        metrics = RequestMetrics()
        started = time.perf_counter()

        configuration_error = self._configuration_error()
        if configuration_error:
            metrics.total_seconds = time.perf_counter() - started
            yield ClientEvent("error", metrics, error_code="configuration", error_message=configuration_error)
            yield ClientEvent("complete", metrics)
            return

        timeout = httpx.Timeout(self.settings.request_timeout_seconds)
        headers = {"Accept": "text/event-stream, text/plain"}
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                transport=self.transport,
            ) as client:
                async with client.stream(
                    "GET",
                    self.settings.voice_api_url,
                    params=request.remote_params(),
                    headers=headers,
                ) as response:
                    metrics.status_code = response.status_code
                    metrics.content_type = response.headers.get("content-type")
                    metrics.http_response_seconds = time.perf_counter() - started
                    yield ClientEvent("meta", metrics)

                    if not 200 <= response.status_code < 300:
                        detail = (await response.aread()).decode("utf-8", errors="replace").strip()
                        message = f"Upstream API returned HTTP {response.status_code}."
                        if detail:
                            message = f"{message} {detail[:500]}"
                        metrics.total_seconds = time.perf_counter() - started
                        yield ClientEvent("error", metrics, error_code="http_error", error_message=message)
                        yield ClientEvent("complete", metrics)
                        return

                    parser = AdaptiveStreamParser(metrics.content_type)
                    async for raw in response.aiter_raw():
                        for text in parser.feed(raw):
                            if text:
                                metrics.observe_chunk(text, time.perf_counter() - started)
                                yield ClientEvent("chunk", metrics, text=text)
                    for text in parser.finalize():
                        if text:
                            metrics.observe_chunk(text, time.perf_counter() - started)
                            yield ClientEvent("chunk", metrics, text=text)
        except httpx.TimeoutException:
            metrics.total_seconds = time.perf_counter() - started
            yield ClientEvent("error", metrics, error_code="timeout", error_message="The upstream API request timed out.")
        except httpx.ConnectError:
            metrics.total_seconds = time.perf_counter() - started
            yield ClientEvent("error", metrics, error_code="connection_failure", error_message="Could not connect to the upstream API.")
        except httpx.HTTPError:
            metrics.total_seconds = time.perf_counter() - started
            yield ClientEvent("error", metrics, error_code="transport_error", error_message="The upstream API stream was interrupted.")
        except UnicodeError:
            metrics.total_seconds = time.perf_counter() - started
            yield ClientEvent("error", metrics, error_code="malformed_response", error_message="The upstream response could not be decoded as text.")
        finally:
            if metrics.total_seconds is None:
                metrics.total_seconds = time.perf_counter() - started

        yield ClientEvent("complete", metrics)

    def _configuration_error(self) -> str | None:
        value = self.settings.voice_api_url
        if not value:
            return "VOICE_API_URL is not configured. Add the private endpoint to your local .env file."
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "VOICE_API_URL must be a valid http or https URL."
        return None
