from __future__ import annotations

from phantom_training.judge import filter_success_cases, is_success


def test_code_ground_truth_accepts_correct_candidate():
    row = {
        "skill": "py",
        "prompt": "add",
        "response": "def add(a,b):\n    return a+b\n",
        "tests": "from solution import add\ndef test_a():\n    assert add(2,3)==5\n",
    }

    assert is_success(row) is True
    assert list(filter_success_cases([row])) == [row]


def test_code_ground_truth_rejects_wrong_candidate():
    row = {
        "skill": "py",
        "prompt": "add",
        "response": "def add(a,b):\n    return a-b\n",
        "tests": "from solution import add\ndef test_a():\n    assert add(2,3)==5\n",
    }

    assert is_success(row) is False
    assert list(filter_success_cases([row])) == []


def test_qa_ground_truth_accepts_reference_match():
    row = {"response": "paris", "reference": "paris"}

    assert is_success(row) is True
    assert list(filter_success_cases([row])) == [row]


def test_qa_ground_truth_rejects_reference_mismatch():
    row = {"response": "berlin", "reference": "paris"}

    assert is_success(row) is False
    assert list(filter_success_cases([row])) == []


def test_no_ground_truth_fallback_stays_intact():
    assert is_success({"judged_success": 1, "hermes_score": 0.9}) is True
    assert is_success({"judged_success": 0, "hermes_score": 0.9}) is False
