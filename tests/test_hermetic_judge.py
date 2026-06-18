from __future__ import annotations

from phantom_training.hermetic_judge import judge_task


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
