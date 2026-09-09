# Architecture and API-contract evidence

## Purpose

The tester sits beside the MH Voice backend. It never changes or imports production backend code. Its only remote action is an HTTP GET to the address held in the local `VOICE_API_URL` environment variable.

```text
Browser dashboard
    | POST /api/stream (same local origin)
    v
Local MH Voice API Tester
    | GET with confirmed query parameters; read bytes as they arrive
    v
Configured MH Voice API
    | existing backend behavior
    v
Local browser receives tester SSE events and displays the received chunks
```

The local tester wraps its own browser-facing progress messages as SSE. That does not change the remote response or simulate it; every `chunk` event contains text just received from the remote stream.

## CONFIRMED - MH route contract from `mh-voice-prod`

`main.py` mounts the voice router under `/api`. `app/routers/voice.py` defines `GET /voice/`, making the endpoint path `/api/voice/`.

The `ChatRequest` Pydantic model confirms these parameters:

| Parameter | Required by model | Default in source | Tester handling |
| --- | --- | --- | --- |
| `query` | Yes | none | Required text field |
| `session_id` | No | generated UUID in router | Fresh local test ID unless supplied |
| `source_lang` | No | `mr` | Hindi, Marathi, English selector |
| `target_lang` | No | `mr` | Hindi, Marathi, English selector |
| `user_id` | No | `anonymous` | Advanced optional field; omitted by default |
| `provider` | No | none | Advanced optional `RAYA` / `RINGG` field |
| `process_id` | No | none | Advanced optional field |

The tester sends no other invented query parameters.

## CONFIRMED - backend flow

1. The route resolves a session ID, fetches message history, and returns a FastAPI `StreamingResponse` labeled `text/event-stream`.
2. `stream_voice_message` builds `FarmerContext` with the input and target language, session ID, provider, and process ID.
3. It cleans orphaned tool calls in history, trims history to a configured token budget, then calls Pydantic AI `voice_agent.run_stream`.
4. It loops over `response_stream.stream_text(delta=True)` and yields each text delta.
5. After streaming ends, it saves new messages back to Redis.

The source currently logs a backend-side TTFT at the first yielded delta. The tester cannot read that log; it independently measures receipt time at the client.

## CONFIRMED - session behavior

- History is loaded before each request and persisted after a completed stream.
- Default history TTL is 24 hours.
- The source code names the suffix `_SVA` and interpolates it with an extra underscore. The exact effective cache key should be verified against a live Redis instance before relying on it operationally.
- The client cannot inspect Redis or prove the history used for an individual request.

## CONFIRMED - registered agent tools

The `TOOLS` list currently registers twelve callable tools:

1. terms search
2. document search
3. video search
4. weather forecast
5. historical weather
6. mandi prices
7. warehouse data
8. forward geocoding
9. scheme code lookup
10. scheme information
11. agricultural services
12. agricultural staff contact

Their implementation uses a mix of Marqo, Mapbox, local assets, and Beckn/BAP-style external calls. The agent selects tools itself. The external tester sees only timing, HTTP metadata, output, and failures, not an internal tool trace.

## INFERENCE - why the tester has adaptive stream parsing

The source uses `text/event-stream`, but yields strings without visible `data:` framing. A one-request live probe returned `text/plain` and no `data:` prefix. Therefore the tester first respects genuine SSE frames and otherwise forwards raw decoded pieces as soon as possible. This preserves real observed behavior rather than forcing one protocol interpretation.

## UNKNOWN - needs verification

- Whether any particular deployment sends proper SSE frames, raw chunked text, or a fully buffered response.
- Whether the gateway changes headers or buffers data.
- Exact upstream authorization requirements for the configured private endpoint.
- Which tools and model provider were used for a particular API response.
