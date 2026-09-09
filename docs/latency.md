# Latency investigation guide

## What this tester measures

The tester records a monotonic start time immediately before opening the remote HTTP stream.

| Measurement | How it is captured |
| --- | --- |
| HTTP response time | Response headers become available to the tester |
| TTFT | First non-whitespace text reaches the tester |
| Total time | Stream ends, returns an HTTP error, or client transport fails |
| Chunk count | Number of nonempty text pieces received by the tester |
| Response length | Characters received by the tester |

These are **backend/API path measurements from the tester's perspective**. They are useful for comparing requests over time but are not end-to-end telephone-call latency.

## What cannot be measured from this client alone

The following are **NOT MEASURABLE FROM THIS CLIENT ALONE**:

- network time before or after the tester in a production phone flow
- speech-to-text latency
- telephony provider latency
- text-to-speech latency
- Redis read or write duration
- Pydantic AI orchestration time
- model queue time, model TTFT, or token-generation time
- Marqo retrieval time
- Mapbox geocoding time
- Beckn/BAP/PoCRA call time
- backend retry and backoff time
- nudge/hold-message time

An API TTFT can include one or more of these activities before the first response text reaches the tester. It must not be described as “LLM TTFT” without backend traces.

## CONFIRMED possible latency sources in `mh-voice-prod`

- Session history retrieval and saving via Redis.
- Pydantic AI model call and up to three agent retries.
- Document/video retrieval through Marqo.
- Mapbox geocoding.
- Tool calls to BAP with a 15-second configured search timeout and retry/backoff for empty responses in shared tool code.
- Other external tools such as weather, mandi, warehouses, schemes, agricultural services, and staff contact.
- Remote model generation and stream transport.

“Possible” means the source contains these paths. It does not prove any one request used them.

## A practical investigation sequence

1. Run a simple advice scenario at least 10 times with fresh sessions. Record median and p95 TTFT and total time.
2. Run one candidate scenario category at a time: document knowledge, weather, mandi, schemes, warehouse, and staff contact.
3. Compare distributions, not a single fastest or slowest sample.
4. Note HTTP status, content type, response length, and errors next to timing. A short error response is not equivalent to a successful fast answer.
5. If a scenario is consistently slower, call it “an observed slower scenario.” Do not name the LLM or a tool as the cause without trace evidence.

## Backend instrumentation needed for a causal answer

To split latency reliably, add timestamped spans to the backend, ideally correlated by a safe generated test-run ID rather than farmer identifiers:

- router entered / history read start / history read end
- agent started
- model request opened / first model delta / model completed
- each tool call start / end / retry count / error
- response first byte written / stream completed
- history write start / end

Langfuse tracing already appears in the source and is the most promising place to correlate model and tool spans, if the deployment is configured to export them and access is authorized.
