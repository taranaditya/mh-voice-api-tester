"""Small local SQLite store. Plain session IDs are never persisted."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metrics import RequestMetrics
from .models import VoiceRequest


def _session_fingerprint(session_id: str | None) -> str:
    return hashlib.sha256((session_id or "").encode("utf-8")).hexdigest()[:16]


def _redact_session(session_id: str | None) -> str:
    if not session_id:
        return "not-provided"
    if len(session_id) <= 8:
        return "redacted"
    return f"{session_id[:5]}...{session_id[-4:]}"


class ResultsStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS test_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    scenario TEXT,
                    query TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    session_fingerprint TEXT NOT NULL,
                    session_display TEXT NOT NULL,
                    status_code INTEGER,
                    content_type TEXT,
                    http_response_seconds REAL,
                    ttft_seconds REAL,
                    total_seconds REAL,
                    chunk_count INTEGER NOT NULL,
                    response_characters INTEGER NOT NULL,
                    response TEXT NOT NULL,
                    error_code TEXT,
                    error_message TEXT,
                    language_observation TEXT
                )
                """
            )

    def save_run(
        self,
        request: VoiceRequest,
        metrics: RequestMetrics,
        response: str,
        error_code: str | None,
        error_message: str | None,
        language_observation: dict[str, Any],
    ) -> int:
        session_id = request.session_id
        values = (
            datetime.now(timezone.utc).isoformat(),
            request.scenario,
            request.query,
            request.source_lang,
            request.target_lang,
            _session_fingerprint(session_id),
            _redact_session(session_id),
            metrics.status_code,
            metrics.content_type,
            metrics.http_response_seconds,
            metrics.ttft_seconds,
            metrics.total_seconds,
            metrics.chunk_count,
            metrics.response_characters,
            response,
            error_code,
            error_message,
            json.dumps(language_observation, ensure_ascii=False),
        )
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO test_runs (
                    created_at, scenario, query, source_lang, target_lang,
                    session_fingerprint, session_display, status_code, content_type,
                    http_response_seconds, ttft_seconds, total_seconds, chunk_count,
                    response_characters, response, error_code, error_message,
                    language_observation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            return int(cursor.lastrowid)

    def list_runs(self, limit: int = 100, include_response: bool = False) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        response_column = "response" if include_response else "substr(response, 1, 240) AS response_preview"
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, created_at, scenario, query, source_lang, target_lang,
                       session_display, status_code, content_type,
                       http_response_seconds, ttft_seconds, total_seconds,
                       chunk_count, response_characters, error_code, error_message,
                       language_observation, {response_column}
                FROM test_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_dict(row, include_response) for row in rows]

    def export_json(self) -> str:
        return json.dumps(self.list_runs(limit=500, include_response=True), ensure_ascii=False, indent=2)

    def export_csv(self) -> str:
        records = self.list_runs(limit=500, include_response=True)
        columns = [
            "id", "created_at", "scenario", "query", "source_lang", "target_lang",
            "session_display", "status_code", "content_type", "http_response_seconds",
            "ttft_seconds", "total_seconds", "chunk_count", "response_characters",
            "error_code", "error_message", "response", "language_observation",
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        return output.getvalue()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row, include_response: bool) -> dict[str, Any]:
        result = dict(row)
        observation = result.get("language_observation")
        result["language_observation"] = json.loads(observation) if observation else None
        if not include_response:
            result["response"] = result.pop("response_preview", "")
        return result
