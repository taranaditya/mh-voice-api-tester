# MH Voice API Tester

`MH Voice API Tester` is a separate, local developer dashboard for exercising a deployed MH Voice API without modifying the MH backend. It lets a developer send an agricultural question, watch the remote response arrive, record client-visible timing, compare sessions and languages, benchmark scenarios, and export local results.

It is intentionally a tester, not a copy of the production backend. The private upstream address is read from a local `.env` file and is never printed by the dashboard, written to result records, or included in this repository.

## What it does

- Sends the confirmed Voice API query fields: `query`, `session_id`, `source_lang`, and `target_lang`.
- Supports the confirmed optional fields `user_id`, `provider`, and `process_id` in an advanced section.
- Displays response text as it arrives from the remote API. It supports standards-compliant SSE and raw streamed text; it never pretends a completed answer is streaming.
- Measures request start, HTTP response time, time to first meaningful text (TTFT), total time, chunk count, response length, HTTP status, and received content type.
- Provides scenarios based on agent capabilities confirmed in the `mh-voice-prod` repository. A scenario does **not** claim that a particular tool was invoked.
- Runs a controlled same-session versus new-session language experiment.
- Benchmarks a scenario sequentially with fresh generated test sessions and calculates min, max, mean, median, p95, and success rate.
- Stores results locally in SQLite and exports JSON or CSV. Plain session IDs are not persisted; the store keeps a hash fingerprint plus a redacted label.

## Repository evidence status

### CONFIRMED from `mh-voice-prod`

- The primary route is `GET /api/voice/` under the `/api` prefix.
- The request model contains `query`, `session_id`, `source_lang`, `target_lang`, `user_id`, `provider`, and `process_id`.
- The router creates a `StreamingResponse` with `text/event-stream` media type.
- The service calls `voice_agent.run_stream(...)` and yields text deltas from `stream_text(delta=True)`.
- Conversation history is read and written through Redis, keyed from `session_id`, with a 24-hour TTL. It is fetched before the request, then written after streaming completes.
- The agent is Pydantic AI with configurable OpenAI, Azure OpenAI, or vLLM model providers, `max_tokens=8192`, retries, parallel tool calls, and registered agriculture tools.

### LIVE observation, one supplied Hindi weather probe, 9 September 2026

- The request returned HTTP 200 in approximately 4.98 seconds from this machine.
- The deployed gateway returned `Content-Type: text/plain; charset=utf-8` and one non-framed text body rather than `text/event-stream` / `data:` frames.

This is a single observation, not a performance baseline or a claim about every deployment path. The tester records the response content type on every run so later evidence can be compared.

### INFERENCE

Because the repository yields raw text deltas while labeling the response as SSE, and a live probe returned plain text, a robust tester needs both standards-SSE parsing and raw incremental-text handling. The implementation does that without fabricating chunks.

### UNKNOWN - needs verification

- Which internal tool, if any, ran for an individual response.
- Server-side timing for Redis, model queueing, first LLM token, Marqo retrieval, Beckn/BAP calls, retries, nudge calls, and generation.
- Whether a target-language difference is caused by session history, prompt selection, model behavior, translation, or another deployment layer.

## Quick start (PowerShell)

```powershell
cd C:\Users\taran\Documents\Playground\Kenpath\mh-voice-api-tester
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `.env` locally and replace only the placeholder:

```dotenv
VOICE_API_URL=<PRIVATE_VOICE_API_ENDPOINT>
VOICE_API_TIMEOUT_SECONDS=45
TESTER_DATA_DIR=./data
```

Start the dashboard:

```powershell
uvicorn app.main:app --reload --port 8010
```

Open `http://127.0.0.1:8010`. The dashboard never displays the configured upstream URL.

Run automated tests without calling the remote API:

```powershell
pytest -q
```

## How to use it

1. Generate a new test session before an unrelated test. Reuse it only when testing conversation context.
2. Enter a query and select the language of the input and the desired language of the reply.
3. Click **Send and stream**. Watch text arrive in **Live response** and inspect the metrics after completion.
4. Use predefined scenarios to make repeated tests comparable. They are candidates for capabilities, not tool-call assertions.
5. Use **Session / language comparison** to run A1 (initial language), A2 (same session, changed language), and B (new session, changed language). Compare evidence before calling anything a defect.
6. Run the benchmark when you need a distribution, not a single timing. Each run receives a fresh local test session.
7. Export only when you understand the local test content may contain farmer questions and model responses.

## Metric meanings

| Metric | Meaning | Not a measurement of |
| --- | --- | --- |
| HTTP response | Time until this client receives response headers | Complete model work or phone-call latency |
| TTFT | Time until this client receives first meaningful response text | Pure LLM first-token latency |
| Total | Time until the remote stream ends or errors | STT, TTS, telephony, or a backend component split |
| Chunks | Text pieces observed by this client | Tokens generated by the model |

See [architecture.md](docs/architecture.md), [latency.md](docs/latency.md), [language-testing.md](docs/language-testing.md), [benchmarking.md](docs/benchmarking.md), [troubleshooting.md](docs/troubleshooting.md), and [security-review.md](docs/security-review.md).

## Security boundaries

- `.env`, local virtual environments, and the SQLite data directory are ignored by Git.
- No production endpoint, credential, JWT, authorization header, or API key belongs in source code, documentation, screenshots, exported examples, or commits.
- The server does not log upstream URLs, parameters, request bodies, or response bodies.
- The browser interacts only with this local tester. It never receives the environment variable containing the upstream address.
- Result storage redacts session identifiers before persistence. Queries and responses are intentionally stored locally because testing requires evidence; treat exports as potentially sensitive.

## Project layout

```text
app/
  client.py       # private upstream request and incremental stream reader
  streaming.py    # SSE parser plus raw text fallback
  metrics.py      # client-observable timing model
  runner.py       # reusable full-run execution
  benchmark.py    # sequential benchmark and aggregation
  language.py     # conservative script observation
  storage.py      # local SQLite and exports
  scenarios.py    # confirmed-capability test cases
  main.py         # local dashboard API
  static/         # dashboard UI
tests/            # mocked unit tests only
docs/             # evidence, limits, operations, and security notes
```
