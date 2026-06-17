"""Robustness tests for the held-out eval against malformed input.

A user can point ``phantom-train eval`` at a hand-edited or partially-written
JSONL file. Before the fix, a single malformed line raised an uncaught
``json.JSONDecodeError`` and the CLI died with a traceback. The eval module
already has a structured ``{"error": ...}`` convention (e.g. the "need >=2
rows" case) — malformed input should use the same clean path.
"""

from __future__ import annotations

import json

import pytest

from phantom_training import cli
from phantom_training.eval import evaluate, load_jsonl


def _write(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_evaluate_malformed_jsonl_returns_error_not_crash(tmp_path):
    p = tmp_path / "bad.jsonl"
    _write(p, [
        json.dumps({"instruction": "a", "input": "", "output": "x"}),
        "this is not json",
        json.dumps({"instruction": "b", "input": "", "output": "y"}),
    ])
    result = evaluate(p)
    assert "error" in result
    assert "2" in result["error"]  # reports the offending (1-based) line number


def test_load_jsonl_reports_line_number(tmp_path):
    p = tmp_path / "bad.jsonl"
    _write(p, [
        json.dumps({"instruction": "a", "input": "", "output": "x"}),
        "{ broken",
    ])
    with pytest.raises(ValueError) as exc:
        load_jsonl(p)
    assert "line 2" in str(exc.value)


def test_cmd_eval_malformed_jsonl_exits_1(tmp_path, capsys):
    p = tmp_path / "bad.jsonl"
    _write(p, [
        json.dumps({"instruction": "a", "input": "", "output": "x"}),
        "<<<corrupt>>>",
    ])
    rc = cli.main(["eval", "--dataset", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "eval:" in err


def test_evaluate_still_ignores_blank_lines(tmp_path):
    """Blank lines remain harmless — only genuinely malformed JSON errors."""
    p = tmp_path / "ok.jsonl"
    p.write_text(
        json.dumps({"instruction": "a", "input": "", "output": "x"}) + "\n"
        "\n"
        + json.dumps({"instruction": "b", "input": "", "output": "y"}) + "\n",
        encoding="utf-8",
    )
    result = evaluate(p)
    assert "error" not in result
    assert result["n_rows"] == 2
