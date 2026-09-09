"""A standards-aware parser with a raw-stream fallback for observed deployments."""

from __future__ import annotations

import codecs


class SseParser:
    """Incrementally parse SSE `data:` events without inventing chunks."""

    def __init__(self) -> None:
        self._line_buffer = ""
        self._data_lines: list[str] = []

    def feed(self, text: str) -> list[str]:
        self._line_buffer += text
        messages: list[str] = []
        while "\n" in self._line_buffer:
            line, self._line_buffer = self._line_buffer.split("\n", 1)
            if line.endswith("\r"):
                line = line[:-1]
            message = self._consume_line(line)
            if message is not None:
                messages.append(message)
        return messages

    def finalize(self) -> list[str]:
        messages: list[str] = []
        if self._line_buffer:
            message = self._consume_line(self._line_buffer.rstrip("\r"))
            self._line_buffer = ""
            if message is not None:
                messages.append(message)
        if self._data_lines:
            messages.append("\n".join(self._data_lines))
            self._data_lines.clear()
        return messages

    def _consume_line(self, line: str) -> str | None:
        if not line:
            if not self._data_lines:
                return None
            message = "\n".join(self._data_lines)
            self._data_lines.clear()
            return message
        if line.startswith(":"):
            return None
        if line.startswith("data:"):
            value = line[5:]
            if value.startswith(" "):
                value = value[1:]
            self._data_lines.append(value)
        return None


class AdaptiveStreamParser:
    """Use SSE framing when it is actually present; otherwise pass raw bytes through.

    The MH source marks its response as SSE but yields text deltas directly. A
    proxy may also change the content type. This parser makes neither fact a
    reason to delay or fabricate the user-visible stream.
    """

    _SSE_PREFIXES = ("data:", "event:", "id:", "retry:", ":")

    def __init__(self, content_type: str | None) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._mode = "undecided" if "text/event-stream" in (content_type or "").lower() else "raw"
        self._probe = ""
        self._sse = SseParser()

    def feed(self, raw: bytes) -> list[str]:
        text = self._decoder.decode(raw)
        return self._feed_text(text)

    def finalize(self) -> list[str]:
        tail = self._decoder.decode(b"", final=True)
        messages = self._feed_text(tail)
        if self._mode == "undecided":
            self._mode = "raw"
            if self._probe:
                messages.append(self._probe)
                self._probe = ""
        elif self._mode == "sse":
            messages.extend(self._sse.finalize())
        return messages

    def _feed_text(self, text: str) -> list[str]:
        if not text:
            return []
        if self._mode == "raw":
            return [text]
        if self._mode == "sse":
            return self._sse.feed(text)

        self._probe += text
        candidate = self._probe.lstrip()
        if any(candidate.startswith(prefix) for prefix in self._SSE_PREFIXES):
            self._mode = "sse"
            to_parse, self._probe = self._probe, ""
            return self._sse.feed(to_parse)
        if any(prefix.startswith(candidate) for prefix in self._SSE_PREFIXES):
            return []

        self._mode = "raw"
        raw_text, self._probe = self._probe, ""
        return [raw_text]
