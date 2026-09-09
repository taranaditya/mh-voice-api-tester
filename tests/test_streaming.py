from app.streaming import AdaptiveStreamParser, SseParser


def test_sse_parser_handles_fragmented_data_frames() -> None:
    parser = SseParser()
    assert parser.feed("data: Hel") == []
    assert parser.feed("lo\n\n") == ["Hello"]
    assert parser.feed("data: world\n\n") == ["world"]
    assert parser.finalize() == []


def test_adaptive_parser_passes_raw_text_without_fake_sse_frames() -> None:
    parser = AdaptiveStreamParser("text/plain; charset=utf-8")
    assert parser.feed(b"First ") == ["First "]
    assert parser.feed(b"chunk") == ["chunk"]
    assert parser.finalize() == []


def test_event_stream_header_with_raw_text_falls_back_to_raw_incrementally() -> None:
    parser = AdaptiveStreamParser("text/event-stream")
    assert parser.feed(b"Raw") == ["Raw"]
    assert parser.feed(b" text") == [" text"]
    assert parser.finalize() == []
