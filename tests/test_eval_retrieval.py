"""Tests for the nearest-instruction retrieval baseline and its determinism.

``_retrieve`` picks the train row with the highest instruction-Jaccard score,
and on an exact tie the loop's strict ``>`` comparison means the first-seen
row keeps its lead. ``evaluate()`` composes ``_split`` + ``_retrieve`` +
``_exact_match``/``_token_f1`` into a single deterministic floor metric —
this pins down real numbers on a hand-built dataset so a future refactor
can't silently change the split, the retrieval tie-break, or the samples
cap/truncation without a test noticing.
"""

from __future__ import annotations

import json

from phantom_training.eval import _retrieve, evaluate


def _write(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def test_retrieve_returns_highest_jaccard_train_row():
    train = [
        {"instruction": "translate this text to french", "output": "no-match-partial"},
        {"instruction": "sum two numbers together", "output": "exact-match"},
    ]

    result = _retrieve("sum two numbers together", train)

    assert result["output"] == "exact-match"


def test_retrieve_first_seen_wins_on_tie():
    train = [
        {"instruction": "same instruction text", "output": "first"},
        {"instruction": "same instruction text", "output": "second"},
        {"instruction": "totally different", "output": "third"},
    ]

    result = _retrieve("same instruction text", train)

    assert result["output"] == "first"


def test_evaluate_hand_built_dataset_is_deterministic_and_caps_samples(tmp_path):
    # 8 rows, holdout_fraction=0.5 -> deterministic interleaved split gives
    # held = rows[0,2,4,6], train = rows[1,3,5,7] (see eval._split).
    long_instruction = "a_kw a_fill1 a_fill2 " + "a_pad " * 15
    rows = [
        {"instruction": long_instruction, "output": "cats and dogs"},          # 0 held (pair A)
        {"instruction": "a_kw a_fill1 a_fill2", "output": "cats and dogs"},    # 1 train (pair A)
        {"instruction": "b_kw b_fill1", "output": "cats and dogs"},            # 2 held (pair B)
        {"instruction": "b_kw b_fill1", "output": "cats and fish"},            # 3 train (pair B)
        {"instruction": "c_kw c_fill1", "output": "apple"},                    # 4 held (pair C)
        {"instruction": "c_kw c_fill1", "output": "banana"},                   # 5 train (pair C)
        {"instruction": "d_kw d_fill1", "output": "same text here"},           # 6 held (pair D)
        {"instruction": "d_kw d_fill1", "output": "same text here"},           # 7 train (pair D)
    ]
    assert len(long_instruction) > 80  # precondition for the truncation assert below

    path = tmp_path / "dataset.jsonl"
    _write(path, rows)

    result = evaluate(path, holdout_fraction=0.5)

    assert "error" not in result
    assert result["n_rows"] == 8
    assert result["n_train"] == 4
    assert result["n_holdout"] == 4

    # pair A: exact output match (em=True, f1=1.0)
    # pair B: partial overlap "cats and dogs" vs "cats and fish" (em=False, f1=2/3)
    # pair C: zero overlap "apple" vs "banana" (em=False, f1=0.0)
    # pair D: exact output match (em=True, f1=1.0), outside the samples cap
    assert result["exact_match"] == 0.5
    assert result["token_f1"] == 0.6667

    samples = result["samples"]
    assert len(samples) == 3  # capped even though n_holdout == 4
    assert samples[0]["exact_match"] is True
    assert samples[0]["token_f1"] == 1.0
    assert samples[1]["exact_match"] is False
    assert samples[1]["token_f1"] == 0.6667
    assert samples[2]["exact_match"] is False
    assert samples[2]["token_f1"] == 0.0

    assert samples[0]["instruction"] == long_instruction[:80]
    assert len(samples[0]["instruction"]) == 80
