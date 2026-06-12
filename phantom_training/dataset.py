"""Extract training rows from a phantom-mesh FTS5 memory.db.

The schema in phantom-mesh is roughly::

    CREATE VIRTUAL TABLE memory_fts USING fts5(
        skill, prompt, response, tags, content='memory', content_rowid='id'
    );
    CREATE TABLE memory(
        id INTEGER PRIMARY KEY,
        ts INTEGER NOT NULL,
        skill TEXT,
        prompt TEXT,
        response TEXT,
        judged_success INTEGER DEFAULT 0,
        hermes_score REAL,
        tags TEXT
    );

We're defensive: if the file is missing, the schema differs, or any query
fails, we return ``[]`` rather than crashing the CLI. The fine-tuning agent
is allowed to keep planning even with zero rows — it just produces a "no
data yet, accumulate more sessions" plan.

Public surface:

* ``extract_from_fts5(skill_name, db_path) -> list[dict]``
* ``to_instruction_rows(rows) -> list[dict]``  (Tier 2 will consume this)
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Columns we try to read. If the real schema doesn't have one, the SELECT will
# fail and we'll fall back to a minimal query.
_PRIMARY_QUERY = """
SELECT id, ts, skill, prompt, response, judged_success, hermes_score, tags
FROM memory
WHERE skill = ?
  AND judged_success = 1
ORDER BY hermes_score DESC NULLS LAST, ts DESC
LIMIT ?
"""

# Fallback for older / minimal schemas that haven't grown the Hermes columns.
_FALLBACK_QUERY = """
SELECT rowid AS id, NULL AS ts, skill, prompt, response,
       0 AS judged_success, NULL AS hermes_score, NULL AS tags
FROM memory
WHERE skill = ?
LIMIT ?
"""

# FTS5-driven full-text fallback, useful if skill is fuzzy (e.g. "rust" matching "rust-coder").
_FTS_QUERY = """
SELECT m.id, m.ts, m.skill, m.prompt, m.response,
       COALESCE(m.judged_success, 0) AS judged_success,
       m.hermes_score, m.tags
FROM memory_fts f
JOIN memory m ON m.id = f.rowid
WHERE memory_fts MATCH ?
LIMIT ?
"""


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def extract_from_fts5(
    skill_name: str,
    db_path: Path | str,
    *,
    limit: int = 2000,
) -> list[dict[str, Any]]:
    """Return candidate training rows for ``skill_name``.

    Always returns a list (possibly empty). Never raises on missing DB,
    schema mismatch, or query error — those are logged at debug level so
    the CLI stays usable on a fresh machine with no phantom-mesh history.
    """
    path = Path(db_path)
    if not path.exists():
        log.debug("memory db not found at %s", path)
        return []

    try:
        # read-only URI mode so we never accidentally write to mesh state
        uri = f"file:{path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        log.debug("could not open %s: %s", path, exc)
        return []

    conn.row_factory = sqlite3.Row
    try:
        return _query_with_fallbacks(conn, skill_name, limit)
    finally:
        conn.close()


def _query_with_fallbacks(conn: sqlite3.Connection, skill_name: str, limit: int) -> list[dict[str, Any]]:
    for query, params, label in (
        (_PRIMARY_QUERY, (skill_name, limit), "primary"),
        (_FTS_QUERY, (skill_name, limit), "fts"),
        (_FALLBACK_QUERY, (skill_name, limit), "fallback"),
    ):
        try:
            cur = conn.execute(query, params)
            rows = [_row_to_dict(r) for r in cur.fetchall()]
            log.debug("query=%s returned %d rows", label, len(rows))
            return rows
        except sqlite3.Error as exc:
            log.debug("query=%s failed: %s", label, exc)
            continue
    return []


def extract_from_recall(query: str = "", *, kind: str | None = None, limit: int = 2000) -> list[dict[str, Any]]:
    """Pull events from phantom's real timeline via ``phantom recall --json``.

    This is the supported read path: ``events.sqlite/fts5_events`` is dead
    scaffolding (contentless, never synced); ``phantom recall`` decrypts the
    canonical ``events/<id>/`` store and returns ``{event_id, timestamp, kind,
    summary}``. Empty query → recent listing.

    NOTE: life-node events are *observations* (a single ``summary``), NOT
    prompt/response pairs — so :func:`to_instruction_rows` will skip them. They
    are a corpus signal, not instruction data; real instruction pairs come from
    a ``memory.db`` / Hermes-Curator trajectory store (Tier 2+). Degrades to
    ``[]`` when phantom is unavailable.
    """
    if not shutil.which("phantom"):
        return []
    cmd = ["phantom", "recall", query, "--json", "--limit", str(int(limit))]
    if kind:
        cmd += ["--kind", kind]
    try:
        proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("phantom recall failed: %s", exc)
        return []
    if proc.returncode != 0:
        log.debug("phantom recall rc=%s: %s", proc.returncode, proc.stderr[:200])
        return []
    try:
        events = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return []
    rows: list[dict[str, Any]] = []
    for e in events:
        rows.append({
            "id": e.get("event_id"),
            "ts": e.get("timestamp"),
            "skill": e.get("kind"),
            "prompt": "",  # observations have no prompt/response pair
            "response": e.get("summary", ""),
            "judged_success": 0,
            "hermes_score": None,
            "tags": e.get("kind", ""),
        })
    return rows


def to_instruction_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Convert raw memory rows to instruction-tuning format.

    Output rows look like::

        {"instruction": <prompt>, "input": "", "output": <response>}

    which is the alpaca-style schema Unsloth / TRL / Axolotl all accept.
    """
    out: list[dict[str, str]] = []
    for r in rows:
        prompt = (r.get("prompt") or "").strip()
        response = (r.get("response") or "").strip()
        if not prompt or not response:
            continue
        out.append({"instruction": prompt, "input": "", "output": response})
    return out
