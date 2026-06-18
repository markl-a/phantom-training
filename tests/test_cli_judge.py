from __future__ import annotations

import json
from pathlib import Path

from phantom_training import cli


ADD_TESTS = "from solution import add\ndef test_a():\n    assert add(2,3)==5\n"


def _write_tasks(path: Path, tasks: list[dict[str, str]]) -> None:
    path.write_text("".join(json.dumps(task) + "\n" for task in tasks), encoding="utf-8")


def test_judge_accepts_correct_code_task(tmp_path, capsys):
    tasks = tmp_path / "tasks.jsonl"
    _write_tasks(
        tasks,
        [
            {
                "response": "def add(a,b):\n    return a+b\n",
                "tests": ADD_TESTS,
            }
        ],
    )

    rc = cli.main(["judge", "--tasks", str(tasks)])

    out = capsys.readouterr().out
    assert rc == 0
    assert "ACCEPT" in out


def test_judge_rejects_wrong_code_task(tmp_path, capsys):
    tasks = tmp_path / "tasks.jsonl"
    _write_tasks(
        tasks,
        [
            {
                "response": "def add(a,b):\n    return a-b\n",
                "tests": ADD_TESTS,
            }
        ],
    )

    rc = cli.main(["judge", "--tasks", str(tasks)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "REJECT" in out


def test_judge_accepts_and_rejects_qa_tasks(tmp_path, capsys):
    tasks = tmp_path / "tasks.jsonl"
    _write_tasks(
        tasks,
        [
            {"response": "paris", "reference": "paris"},
            {"response": "berlin", "reference": "paris"},
        ],
    )

    rc = cli.main(["judge", "--tasks", str(tasks)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "task 1: kind=qa" in out
    assert "task 2: kind=qa" in out
    assert "ACCEPT" in out
    assert "REJECT" in out


def test_judge_missing_file_returns_2(tmp_path, capsys):
    rc = cli.main(["judge", "--tasks", str(tmp_path / "missing.jsonl")])

    assert rc == 2
    capsys.readouterr()
