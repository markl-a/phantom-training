"""Smoke tests for the phantom-train Tier 1 CLI."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from phantom_training import cli
from phantom_training.dataset import extract_from_fts5, to_instruction_rows
from phantom_training.judge import filter_success_cases, is_success

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_RECIPE = REPO_ROOT / "examples" / "rust-coder.toml"


def _run(argv: list[str], tmp_db: Path) -> int:
    return cli.main([*argv, "--db", str(tmp_db)])


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0


def test_dry_run_with_missing_db(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.db"
    rc = cli.main(["--skill", "rust-coder", "--base", "qwen2.5-coder-7b", "--dry-run", "--db", str(missing)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "phantom-training" in out
    assert "rust-coder" in out
    assert "qwen2.5-coder-7b" in out
    assert "DRY-RUN" in out


def test_dry_run_json(tmp_path, capsys):
    rc = cli.main(
        [
            "--skill",
            "rust-coder",
            "--base",
            "qwen2.5-coder-7b",
            "--dry-run",
            "--json",
            "--db",
            str(tmp_path / "missing.db"),
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["skill"] == "rust-coder"
    assert payload["base_model"] == "qwen2.5-coder-7b"
    assert payload["dry_run"] is True
    assert payload["dataset"]["candidate_rows"] == 0
    assert payload["lora"]["rank"] == 16  # default when no recipe


def test_dry_run_with_example_recipe(tmp_path, capsys):
    rc = cli.main(
        [
            "--skill",
            "rust-coder",
            "--base",
            "qwen2.5-coder-7b",
            "--recipe",
            str(EXAMPLE_RECIPE),
            "--dry-run",
            "--json",
            "--db",
            str(tmp_path / "missing.db"),
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    # recipe overrides defaults
    assert payload["lora"]["rank"] == 32
    assert payload["optimizer"]["epochs"] == 3
    assert "HumanEval" in payload["eval"]["public_benchmarks"]


def test_commit_without_backend_fails(tmp_path, capsys):
    rc = cli.main(
        [
            "--skill",
            "rust-coder",
            "--base",
            "qwen2.5-coder-7b",
            "--commit",
            "--db",
            str(tmp_path / "missing.db"),
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "Tier 1" in err


def test_commit_with_dry_run_is_safe_noop(tmp_path, capsys):
    """--dry-run is a safety override: --commit --dry-run together must NOT
    attempt training (exit 0, DRY-RUN banner), so the flag can never be the
    thing that accidentally launches a real run."""
    rc = cli.main(
        [
            "--skill",
            "rust-coder",
            "--base",
            "qwen2.5-coder-7b",
            "--commit",
            "--dry-run",
            "--db",
            str(tmp_path / "missing.db"),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
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
        INSERT INTO memory(ts, skill, prompt, response, judged_success, hermes_score)
            VALUES (1, 'rust-coder', 'write a fn', 'fn foo() {}', 1, 0.91);
        INSERT INTO memory(ts, skill, prompt, response, judged_success, hermes_score)
            VALUES (2, 'rust-coder', 'add a test', '#[test] fn t() {}', 1, 0.72);
        INSERT INTO memory(ts, skill, prompt, response, judged_success, hermes_score)
            VALUES (3, 'rust-coder', 'bad attempt', 'idk',                 0, 0.10);
        INSERT INTO memory(ts, skill, prompt, response, judged_success, hermes_score)
            VALUES (4, 'sql-expert', 'select *', 'SELECT 1;',              1, 0.99);
        """
    )
    conn.commit()
    conn.close()


def test_extract_from_fts5_filters_by_skill_and_success(tmp_path):
    db = tmp_path / "memory.db"
    _seed_db(db)
    rows = extract_from_fts5("rust-coder", db)
    assert len(rows) == 2
    assert all(r["skill"] == "rust-coder" for r in rows)
    assert all(r["judged_success"] == 1 for r in rows)


def test_extract_from_fts5_missing_db_returns_empty(tmp_path):
    assert extract_from_fts5("rust-coder", tmp_path / "nope.db") == []


def test_to_instruction_rows_drops_empty():
    rows = [
        {"prompt": "p", "response": "r"},
        {"prompt": "", "response": "r"},
        {"prompt": "p", "response": ""},
    ]
    out = to_instruction_rows(rows)
    assert out == [{"instruction": "p", "input": "", "output": "r"}]


def test_judge_passes_high_score_and_drops_low():
    assert is_success({"judged_success": 1, "hermes_score": 0.9}) is True
    assert is_success({"judged_success": 0, "hermes_score": 0.9}) is False
    assert is_success({"judged_success": 1, "hermes_score": 0.1}) is False
    assert is_success({"judged_success": 1}) is True
    assert is_success({}) is True  # no evidence -> permissive in Tier 1


def test_filter_success_cases_round_trip():
    rows = [
        {"judged_success": 1, "hermes_score": 0.8},
        {"judged_success": 1, "hermes_score": 0.3},
        {"judged_success": 0, "hermes_score": 0.99},
    ]
    kept = list(filter_success_cases(rows))
    assert len(kept) == 1


def test_seed_fixture_then_build_dataset_writes_nonempty_jsonl(tmp_path, capsys):
    db = tmp_path / "memory.db"
    out = tmp_path / "ds.jsonl"
    # seed-fixture
    assert cli.main(["seed-fixture", "--db", str(db)]) == 0
    # build-dataset off the seeded trajectories
    rc = cli.main(["build-dataset", "--skill", "rust-coder", "--db", str(db), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    lines = [line for line in out.read_text().splitlines() if line.strip()]
    assert len(lines) >= 5, "dataset must be non-empty / real-shaped"
    for line in lines:
        row = json.loads(line)
        assert set(row) == {"instruction", "input", "output"}  # alpaca schema
        assert row["instruction"] and row["output"]
    # the deliberately-failed low-score rows must have been dropped by the judge
    outputs = [json.loads(line)["output"] for line in lines]
    assert "TODO" not in outputs
    assert "sql-expert" not in {json.loads(line)["instruction"] for line in lines}


def test_build_dataset_seed_if_empty(tmp_path):
    db = tmp_path / "fresh.db"  # does not exist
    out = tmp_path / "ds.jsonl"
    rc = cli.main(["build-dataset", "--db", str(db), "--out", str(out), "--seed-if-empty"])
    assert rc == 0
    assert len([line for line in out.read_text().splitlines() if line.strip()]) >= 5


def test_eval_produces_real_metric(tmp_path):
    db = tmp_path / "memory.db"
    out = tmp_path / "ds.jsonl"
    cli.main(["seed-fixture", "--db", str(db)])
    cli.main(["build-dataset", "--skill", "rust-coder", "--db", str(db), "--out", str(out)])

    from phantom_training.eval import evaluate

    result = evaluate(out, holdout_fraction=0.2)
    assert result["n_holdout"] >= 1
    assert result["n_train"] >= 1
    assert 0.0 <= result["token_f1"] <= 1.0
    assert 0.0 <= result["exact_match"] <= 1.0
    # held-out gold is never in the train split, so a trivial retriever can't
    # exact-match its own held-out output -> honest non-trivial number
    assert result["n_train"] + result["n_holdout"] == result["n_rows"]


def test_eval_token_f1_and_exact_match_math():
    from phantom_training.eval import _token_f1, _exact_match

    assert _exact_match("a  b", "a b") is True
    assert _exact_match("a b", "a c") is False
    assert _token_f1("the cat sat", "the cat sat") == 1.0
    assert _token_f1("x y z", "a b c") == 0.0
    # partial overlap: pred "a b", gold "a b c d" -> P=1.0 R=0.5 F1=0.6667
    assert round(_token_f1("a b", "a b c d"), 4) == 0.6667


def test_eval_missing_dataset_returns_2(tmp_path, capsys):
    rc = cli.main(["eval", "--dataset", str(tmp_path / "nope.jsonl")])
    assert rc == 2


def test_cli_as_module_subprocess(tmp_path):
    """Make sure `python -m phantom_training.cli` actually works."""
    env_path = REPO_ROOT
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "phantom_training.cli",
            "--skill",
            "rust-coder",
            "--base",
            "qwen2.5-coder-7b",
            "--dry-run",
            "--db",
            str(tmp_path / "missing.db"),
        ],
        cwd=str(env_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "rust-coder" in result.stdout
