from __future__ import annotations

import json
import sqlite3

from phantom_training import cli


def _write_alpaca_dataset(path, n_rows: int) -> None:
    rows = [
        {"instruction": f"task {i}", "input": "", "output": f"answer {i}"}
        for i in range(n_rows)
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_eval_pretty_prints_metrics(tmp_path, capsys):
    ds = tmp_path / "dataset.jsonl"
    _write_alpaca_dataset(ds, 5)

    rc = cli.main(["eval", "--dataset", str(ds)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "held-out proxy metric" in out
    assert "exact_match" in out
    assert "token_f1" in out
    assert "proxy floor" in out


def test_eval_json_success_returns_0(tmp_path, capsys):
    ds = tmp_path / "dataset.jsonl"
    _write_alpaca_dataset(ds, 5)

    rc = cli.main(["eval", "--dataset", str(ds), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "exact_match" in payload
    assert "token_f1" in payload
    assert "error" not in payload


def test_eval_json_error_returns_1(tmp_path, capsys):
    ds1 = tmp_path / "one-row.jsonl"
    _write_alpaca_dataset(ds1, 1)

    rc = cli.main(["eval", "--dataset", str(ds1), "--json"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert "error" in payload


def test_build_dataset_empty_warns_on_stderr(tmp_path, capsys):
    db = tmp_path / "memory.db"
    conn = sqlite3.connect(db)
    try:
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
            """
        )
        conn.execute(
            "INSERT INTO memory(ts, skill, prompt, response, judged_success, hermes_score, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "rust-coder", "p", "r", 0, 0.1, ""),
        )
        conn.execute(
            "INSERT INTO memory(ts, skill, prompt, response, judged_success, hermes_score, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (2, "rust-coder", "p2", "r2", 1, 0.1, ""),
        )
        conn.commit()
    finally:
        conn.close()
    out_jsonl = tmp_path / "ds.jsonl"

    rc = cli.main(["build-dataset", "--skill", "rust-coder", "--db", str(db), "--out", str(out_jsonl)])

    assert rc == 0
    err = capsys.readouterr().err
    assert "dataset empty" in err
    assert out_jsonl.exists()
    assert out_jsonl.read_text(encoding="utf-8").strip() == ""


def test_seed_fixture_already_populated_message(tmp_path, capsys):
    db = tmp_path / "mem.db"
    assert cli.main(["seed-fixture", "--db", str(db)]) == 0
    capsys.readouterr()

    rc = cli.main(["seed-fixture", "--db", str(db)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "already populated" in out


def test_seed_fixture_reports_inserted_count(tmp_path, capsys):
    db = tmp_path / "fresh.db"

    rc = cli.main(["seed-fixture", "--db", str(db)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "seeded" in out
    assert "fixture trajectory rows" in out


def test_build_dataset_falls_back_to_phantom_recall(tmp_path, capsys, monkeypatch):
    """When the memory.db yields no rows, _collect_rows falls back to
    `phantom recall`; the source label must reflect that (cli.py:149)."""
    # FTS5 path returns nothing (missing db) -> recall fallback is consulted.
    recall_rows = [
        {
            "id": "e1",
            "ts": 1,
            "skill": "note",
            "prompt": "",          # observations carry no prompt -> dropped downstream
            "response": "observed something",
            "judged_success": 0,
            "hermes_score": None,
            "tags": "note",
        }
    ]
    monkeypatch.setattr(cli, "extract_from_recall", lambda *a, **k: recall_rows)
    out_jsonl = tmp_path / "ds.jsonl"

    rc = cli.main(
        [
            "build-dataset",
            "--skill",
            "rust-coder",
            "--db",
            str(tmp_path / "missing.db"),
            "--out",
            str(out_jsonl),
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "phantom recall" in out  # the recall source label was selected
    # observations are not instruction pairs -> empty dataset
    assert out_jsonl.read_text(encoding="utf-8").strip() == ""
