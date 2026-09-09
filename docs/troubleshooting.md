# Troubleshooting

## `VOICE_API_URL is not configured`

Copy `.env.example` to `.env`, set the private endpoint locally, and restart Uvicorn. Never paste the real address into source files or commit `.env`.

## Connection failure

The tester could not establish a connection. Check local network access, DNS/VPN requirements, the private endpoint value in `.env`, and whether the deployment is reachable from your machine. The dashboard intentionally does not reveal the configured address, so inspect `.env` locally.

## Timeout

The upstream stream did not complete within `VOICE_API_TIMEOUT_SECONDS`. Increase the local timeout only if authorized, then record that the tester timed out. This does not say which backend component was slow.

## HTTP 400 / 401 / 403 / 404 / 429 / 500+

The tester reports the status and a short response-body excerpt when present.

- 400: check query text and confirmed language values.
- 401/403: the deployed endpoint may require an authorized network path or credentials. Do not add or log tokens in this tester without an explicitly approved design.
- 404: verify the private endpoint path in the local configuration.
- 429: reduce benchmark volume and delay; do not bypass rate limits.
- 500+: save the result and coordinate with backend owners using timestamp, redacted test session label, status, and client timing.

## Response appears at the end rather than incrementally

Check the recorded content type and chunk count.

- The source intends a streaming response, but the path may be buffered by a proxy or gateway.
- The live supplied probe returned plain text in one body. The tester preserves and shows that observation rather than simulating a stream.
- Compare another run and, if needed, inspect authorized server/proxy settings and traces.

## Target language looks unchanged after a session change

Run the built-in A1/A2/B language comparison. Record the outputs and script observations. Do not label it a backend defect without repeatable evidence and backend-side correlation.

## History does not behave as expected

Ensure follow-up requests use exactly the same test session ID and the first stream completed. The source writes history after streaming, so cancelling a request or an interrupted stream may prevent the intended history from being available.

## Tests fail locally

Use the project virtual environment and install development dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest -q
```

The test suite uses mocked HTTP transports. It should never call `VOICE_API_URL`.
