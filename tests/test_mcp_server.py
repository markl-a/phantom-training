"""Contract test for the thin MCP wrapper.

Verifies (a) the module imports, (b) the ``training_eval`` tool is registered
with the FastMCP server, and (c) it wraps the existing tested eval capability
and returns the same computed metric as ``phantom_training.eval.evaluate``.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("mcp")

from phantom_training import mcp_server
from phantom_training.eval import evaluate
from phantom_training.mcp_server import training_eval


def _write(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def test_server_name_and_tool_registered():
    assert mcp_server.mcp.name == "phantom-training"
    tools = mcp_server.mcp._tool_manager.list_tools()
    names = {t.name for t in tools}
    assert "training_eval" in names


def test_training_eval_wraps_existing_metric(tmp_path):
    rows = [
        {"instruction": "a_kw a_fill1", "output": "cats and dogs"},
        {"instruction": "a_kw a_fill1", "output": "cats and dogs"},
        {"instruction": "b_kw b_fill1", "output": "apple"},
        {"instruction": "b_kw b_fill1", "output": "banana"},
    ]
    path = tmp_path / "dataset.jsonl"
    _write(path, rows)

    result = training_eval(str(path), holdout_fraction=0.5)

    # Identical to calling the underlying tested function directly.
    assert result == evaluate(str(path), holdout_fraction=0.5)
    assert isinstance(result, dict)
    assert result["n_rows"] == 4
    assert "exact_match" in result
    assert "token_f1" in result


def test_training_eval_reports_bad_dataset_without_crashing(tmp_path):
    path = tmp_path / "tiny.jsonl"
    _write(path, [{"instruction": "only one row", "output": "x"}])

    result = training_eval(str(path))

    assert result["n_rows"] == 1
    assert "error" in result
