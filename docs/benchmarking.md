# Benchmarking guide

## Design

The benchmark runner takes one predefined scenario, a repetition count, and a delay. It runs requests sequentially. Every run gets a new generated `tester-...` session ID, preventing previous conversation history from changing the next run.

This choice intentionally measures independent first-turn requests. Use the session comparison feature separately when history behavior is the subject of the test.

## Statistics

For client-observable HTTP response time, TTFT, and total time, the runner calculates:

- minimum
- maximum
- mean
- median
- p95 using the nearest-rank method
- success rate (`successful 2xx runs / all attempted runs`)

A missing TTFT (for example, an error before text) is excluded from the TTFT statistic but the run remains in the success-rate denominator.

## Reading a result table

| Field | Question it answers |
| --- | --- |
| Runs | How many attempts were made? |
| Success | How many attempts completed with a 2xx response and no client error? |
| Average TTFT | What did the average first visible text time look like? |
| Median TTFT | What did a typical run look like? |
| P95 TTFT | How slow was the upper tail of this small sample? |
| Average total | How long did successful and unsuccessful stream completion take on average? |

## Good practice

- Start with 10-20 repetitions when the endpoint owner permits that volume.
- Use a small delay to avoid accidental bursts.
- Keep query text, language pair, machine, network, and time window recorded when comparing runs.
- Inspect errors and response lengths alongside latency.
- Avoid a strong conclusion from a small sample. A p95 from five runs is only a rough indicator.

## Limits

The runner does not identify the internal bottleneck. A slower document-search candidate is evidence that the complete API path was slower in that sample, not proof that Marqo or the LLM caused it.
