from __future__ import annotations

import subprocess

import pytest

from phantom_training.hermetic_judge import _parse_runner_result, judge_task


CODE_TESTS = (
    "from solution import add\n"
    "def test_a():\n"
    "    assert add(2,3)==5\n"
    "def test_b():\n"
    "    assert add(-1,1)==0\n"
)


def test_code_candidate_correct_is_accepted():
    result = judge_task(
        {"tests": CODE_TESTS},
        "def add(a,b):\n    return a+b\n",
    )

    assert result["kind"] == "code"
    assert result["passed"] == 2
    assert result["total"] == 2
    assert result["score"] == 1.0
    assert result["accepted"] is True


def test_code_candidate_wrong_is_rejected():
    result = judge_task(
        {"tests": CODE_TESTS},
        "def add(a,b):\n    return a-b\n",
    )

    assert result["kind"] == "code"
    assert result["score"] < 0.6
    assert result["accepted"] is False


def test_qa_matching_candidate_is_accepted():
    result = judge_task(
        {"reference": "paris is the capital of france"},
        "paris is the capital of france",
    )

    assert result["kind"] == "qa"
    assert result["score"] == 1.0
    assert result["exact_match"] is True
    assert result["accepted"] is True


def test_qa_wrong_candidate_is_rejected():
    result = judge_task(
        {"reference": "paris is the capital of france"},
        "berlin",
    )

    assert result["kind"] == "qa"
    assert result["score"] < 0.6
    assert result["accepted"] is False


def test_code_candidate_timeout_scores_zero():
    result = judge_task(
        {"tests": CODE_TESTS},
        "import time\n"
        "def add(a,b):\n"
        "    time.sleep(30)\n"
        "    return a+b\n",
        timeout=2,
    )

    assert result["kind"] == "code"
    assert result["score"] == 0.0
    assert result["accepted"] is False


def test_judge_task_raises_without_tests_or_reference():
    with pytest.raises(ValueError):
        judge_task({"candidate": "anything"})


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["_runner.py"], returncode=returncode, stdout=stdout, stderr="")


def test_parse_runner_result_nonzero_returncode_scores_zero():
    assert _parse_runner_result(_completed('{"passed": 2, "total": 2}', returncode=1)) == (0, 0)


def test_parse_runner_result_invalid_json_scores_zero():
    assert _parse_runner_result(_completed("not json")) == (0, 0)


def test_parse_runner_result_missing_key_scores_zero():
    assert _parse_runner_result(_completed('{"passed": 2}')) == (0, 0)


def test_parse_runner_result_non_numeric_value_scores_zero():
    assert _parse_runner_result(_completed('{"passed": "x", "total": 2}')) == (0, 0)


def test_parse_runner_result_zero_total_scores_zero():
    assert _parse_runner_result(_completed('{"passed": 0, "total": 0}')) == (0, 0)


def test_parse_runner_result_negative_passed_scores_zero():
    assert _parse_runner_result(_completed('{"passed": -1, "total": 2}')) == (0, 0)


def test_parse_runner_result_passed_exceeds_total_scores_zero():
    assert _parse_runner_result(_completed('{"passed": 5, "total": 2}')) == (0, 0)


def test_parse_runner_result_valid_payload_passes_through():
    assert _parse_runner_result(_completed('{"passed": 2, "total": 3}')) == (2, 3)
