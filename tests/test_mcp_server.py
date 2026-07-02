"""Tests for the training MCP server: honest disclaimer field."""
from __future__ import annotations

import json
from pathlib import Path

from phantom_training import mcp_server


def test_training_eval_returns_disclaimer_and_metadata(tmp_path):
    path = tmp_path / "test.jsonl"
    path.write_text(
        '{"instruction": "a", "input": "", "output": "1"}\n'
        '{"instruction": "b", "input": "", "output": "2"}\n'
        '{"instruction": "c", "input": "", "output": "3"}\n'
    )
    result = mcp_server.training_eval(path)
    assert result["metric_kind"] == "retrieval-floor"
    assert result["trained_model"] is False
    assert "disclaimer" in result
    assert "retrieval floor" in result["disclaimer"].lower()
    assert "exact_match" in result
    assert "token_f1" in result
    assert result["n_rows"] == 3


def test_training_eval_too_small_still_has_metadata(tmp_path):
    path = tmp_path / "single.jsonl"
    path.write_text('{"instruction": "x", "input": "", "output": "y"}\n')
    result = mcp_server.training_eval(path)
    assert result["metric_kind"] == "retrieval-floor"
    assert result["trained_model"] is False
    assert "disclaimer" in result
    assert "error" in result


def test_training_eval_corrupt_file_still_has_metadata(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("not valid json\n")
    result = mcp_server.training_eval(path)
    assert result["metric_kind"] == "retrieval-floor"
    assert result["trained_model"] is False
    assert "disclaimer" in result
    assert "error" in result


def test_training_eval_empty_file_still_has_metadata(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    result = mcp_server.training_eval(path)
    assert result["metric_kind"] == "retrieval-floor"
    assert result["trained_model"] is False
    assert "disclaimer" in result
    assert "error" in result
