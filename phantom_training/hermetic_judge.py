"""Deterministic hermetic judging for code and QA tasks.

Code candidates are written to a temporary ``solution.py`` and run against
pytest-free unit tests in a subprocess, producing a pass-rate score. QA
candidates are scored with normalized exact match or token F1. No model
inference, GPU, or in-process candidate execution is used.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from phantom_training.eval import _exact_match, _token_f1


def score_code(candidate_code: str, tests: str, *, timeout: float = 10.0) -> dict:
    """Run candidate code against pytest-free tests in a temporary subprocess."""
    runner = textwrap.dedent(
        """
        import json

        passed = 0
        total = 0

        try:
            import _tests

            tests = [
                obj
                for name, obj in sorted(vars(_tests).items())
                if name.startswith("test_") and callable(obj)
            ]
            total = len(tests)
            for test in tests:
                try:
                    test()
                except Exception:
                    pass
                else:
                    passed += 1
        except Exception:
            passed = 0

        print(json.dumps({"passed": passed, "total": total}))
        """
    ).strip()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "solution.py").write_text(candidate_code, encoding="utf-8")
        (tmp_path / "_tests.py").write_text(tests, encoding="utf-8")
        (tmp_path / "_runner.py").write_text(runner, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, "_runner.py"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            passed, total = 0, 0
        else:
            passed, total = _parse_runner_result(completed)

    return {
        "kind": "code",
        "passed": passed,
        "total": total,
        "score": passed / total if total else 0.0,
    }


def _parse_runner_result(completed: subprocess.CompletedProcess) -> tuple[int, int]:
    if completed.returncode != 0:
        return 0, 0
    try:
        result = json.loads(completed.stdout.strip())
        passed = int(result["passed"])
        total = int(result["total"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return 0, 0
    if total <= 0 or passed < 0 or passed > total:
        return 0, 0
    return passed, total


def score_qa(candidate: str, reference: str) -> dict:
    """Score a QA candidate by normalized exact match, falling back to token F1."""
    exact_match = _exact_match(candidate, reference)
    score = 1.0 if exact_match else _token_f1(candidate, reference)
    return {"kind": "qa", "score": float(score), "exact_match": exact_match}


def accept(score: float, threshold: float) -> bool:
    return score >= threshold


def judge_task(
    task: dict,
    candidate: str | None = None,
    *,
    threshold: float = 0.6,
    timeout: float = 10.0,
) -> dict:
    if candidate is None:
        candidate = task.get("candidate") or task.get("response") or ""

    if task.get("tests"):
        result = score_code(candidate, task["tests"], timeout=timeout)
    elif "reference" in task:
        result = score_qa(candidate, task["reference"])
    else:
        raise ValueError("task has no ground truth (need tests or reference)")

    result["accepted"] = accept(result["score"], threshold)
    result["threshold"] = threshold
    return result
