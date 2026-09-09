# Security review

## Scope

This review covers the separate local tester. It does not assess the deployment, the MH backend, or provider infrastructure.

## Controls implemented

| Risk | Control |
| --- | --- |
| Private endpoint committed or displayed | Endpoint exists only in local `VOICE_API_URL`; `.env` is Git-ignored; config-status API returns only a boolean. |
| Credentials/JWTs logged | The tester does not implement header-based credentials and does not log requests, URLs, headers, query parameters, or response bodies. |
| Production session identifier persisted | SQLite stores only a SHA-256-derived fingerprint and a redacted display label. |
| Test result lost | Query, response, status, metrics, errors, and language observation are stored locally and exportable. |
| Local result data accidentally committed | `data/` and common database extensions are Git-ignored. |
| Browser exposing the endpoint | Browser calls the same-origin local tester; the server reads the endpoint from its environment. |
| Cached sensitive response | Local API responses receive `Cache-Control: no-store`. |

## Residual risks and operator responsibilities

- Query and response text are stored in local SQLite by design. They may be sensitive farmer or test data. Protect the local machine and delete local data when it is no longer needed.
- Exports contain full query and response text, although session IDs remain redacted. Share exports only through approved channels.
- The live endpoint may require authorization or network access not represented in this tool. Do not paste access tokens into browser forms, Git, issue comments, screenshots, or documentation.
- The tester cannot independently verify any upstream rate limit. Benchmark conservatively and follow endpoint-owner guidance.
- The tester intentionally does not attempt to bypass authentication, TLS, VPN, throttling, or gateway policies.

## Final checklist before a demo or commit

- [ ] `.env` exists locally but is not tracked.
- [ ] No real endpoint, token, JWT, API key, or production session identifier appears in source or documentation.
- [ ] `git status --ignored` is checked before commit.
- [ ] Automated tests run with mocked HTTP only.
- [ ] Export files are reviewed for sensitive query/response content before sharing.
