"""Hermetic tests for ``extract_from_recall`` — the supported ``phantom recall``
read path (``events.sqlite`` is dead scaffolding per dataset.py docstring).

The real function shells out to the ``phantom`` binary, which may or may not be
installed on the running machine. Every test here monkeypatches both
``shutil.which`` and ``subprocess.run`` so the suite is fully offline,
deterministic, and never invokes a real subprocess — no GPU, no network, no
dependency on phantom being present.
"""

from __future__ import annotations

import json
import subprocess

from phantom_training import dataset
from phantom_training.dataset import (
    extract_from_recall,
    to_instruction_rows,
)
from phantom_training.judge import filter_success_cases


class _FakeProc:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def test_extract_from_recall_no_phantom_returns_empty(monkeypatch):
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: None)
    # subprocess.run must never be reached when the binary is absent
    def _boom(*a, **k):  # pragma: no cover - asserted not called
        raise AssertionError("subprocess.run called despite missing phantom")
    monkeypatch.setattr(dataset.subprocess, "run", _boom)
    assert extract_from_recall("rust-coder") == []


def test_extract_from_recall_maps_events(monkeypatch):
    events = [
        {"event_id": "e1", "timestamp": 111, "kind": "note", "summary": "did a thing"},
        {"event_id": "e2", "timestamp": 222, "kind": "task", "summary": "did another"},
    ]
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: "/usr/bin/phantom")
    monkeypatch.setattr(
        dataset.subprocess, "run",
        lambda *a, **k: _FakeProc(stdout=json.dumps(events), returncode=0),
    )
    rows = extract_from_recall("anything")
    assert len(rows) == 2
    first = rows[0]
    assert set(first) == {
        "id", "ts", "skill", "prompt", "response",
        "judged_success", "hermes_score", "tags",
    }
    assert first["id"] == "e1"
    assert first["ts"] == 111
    assert first["skill"] == "note"          # kind -> skill
    assert first["response"] == "did a thing"  # summary -> response
    assert first["prompt"] == ""             # observations have no prompt
    assert first["judged_success"] == 0
    assert first["hermes_score"] is None


def test_extract_from_recall_nonzero_rc_returns_empty(monkeypatch):
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: "/usr/bin/phantom")
    monkeypatch.setattr(
        dataset.subprocess, "run",
        lambda *a, **k: _FakeProc(stdout="[]", returncode=3, stderr="boom"),
    )
    assert extract_from_recall("x") == []


def test_extract_from_recall_invalid_json_returns_empty(monkeypatch):
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: "/usr/bin/phantom")
    monkeypatch.setattr(
        dataset.subprocess, "run",
        lambda *a, **k: _FakeProc(stdout="not json at all", returncode=0),
    )
    assert extract_from_recall("x") == []


def test_extract_from_recall_subprocess_error_returns_empty(monkeypatch):
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: "/usr/bin/phantom")
    def _raise(*a, **k):
        raise subprocess.TimeoutExpired(cmd="phantom", timeout=20)
    monkeypatch.setattr(dataset.subprocess, "run", _raise)
    assert extract_from_recall("x") == []


def test_extract_from_recall_passes_kind_and_limit(monkeypatch):
    captured = {}
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: "/usr/bin/phantom")

    def _capture(cmd, *a, **k):
        captured["cmd"] = cmd
        return _FakeProc(stdout="[]", returncode=0)

    monkeypatch.setattr(dataset.subprocess, "run", _capture)
    extract_from_recall("rust", kind="note", limit=7)
    cmd = captured["cmd"]
    assert cmd[:2] == ["phantom", "recall"]
    assert "rust" in cmd
    assert "--json" in cmd
    assert "--limit" in cmd and "7" in cmd
    assert "--kind" in cmd and "note" in cmd


def test_extract_from_recall_non_list_json_returns_empty(monkeypatch):
    """A valid JSON object (not a list) must degrade to [] rather than crash
    with AttributeError when the mapper tries ``str.get``."""
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: "/usr/bin/phantom")
    monkeypatch.setattr(
        dataset.subprocess, "run",
        lambda *a, **k: _FakeProc(stdout='{"event_id": "x"}', returncode=0),
    )
    assert extract_from_recall("x") == []


def test_extract_from_recall_skips_non_dict_items(monkeypatch):
    """A list mixing non-dict junk with real dict events must skip the junk
    (no AttributeError) and still map the valid events."""
    payload = ["not-a-dict", 7, None, {"event_id": "ok", "kind": "note", "summary": "s"}]
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: "/usr/bin/phantom")
    monkeypatch.setattr(
        dataset.subprocess, "run",
        lambda *a, **k: _FakeProc(stdout=json.dumps(payload), returncode=0),
    )
    rows = extract_from_recall("x")
    assert len(rows) == 1
    assert rows[0]["id"] == "ok"
    assert rows[0]["response"] == "s"


def test_recall_rows_are_not_instruction_data(monkeypatch):
    """Documented invariant: life-node observations are a corpus signal, not
    instruction pairs — they carry no prompt and judged_success=0, so they are
    dropped both by the Curator judge and by to_instruction_rows."""
    events = [{"event_id": "e1", "timestamp": 1, "kind": "note", "summary": "obs"}]
    monkeypatch.setattr(dataset.shutil, "which", lambda _name: "/usr/bin/phantom")
    monkeypatch.setattr(
        dataset.subprocess, "run",
        lambda *a, **k: _FakeProc(stdout=json.dumps(events), returncode=0),
    )
    rows = extract_from_recall("note")
    assert rows, "sanity: recall returned rows"
    assert to_instruction_rows(rows) == []          # no prompt -> dropped
    assert list(filter_success_cases(rows)) == []   # judged_success=0 -> dropped
