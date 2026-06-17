from __future__ import annotations

import sqlite3

from phantom_training.eval import _split
from phantom_training.fixtures import seed_memory_db
from phantom_training.judge import DEFAULT_SCORE_THRESHOLD, is_success


def _rows(n: int) -> list[dict[str, str]]:
    return [{"instruction": f"i{i}", "output": f"o{i}"} for i in range(n)]


def _memory_row_count(path) -> int:
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]


def test_split_is_deterministic():
    rows = _rows(10)

    _, held_once = _split(rows, 0.2)
    _, held_twice = _split(rows, 0.2)

    assert [row["instruction"] for row in held_once] == [
        row["instruction"] for row in held_twice
    ]


def test_split_no_overlap_and_covers_all():
    rows = _rows(10)

    train, held = _split(rows, 0.2)

    assert {id(row) for row in train}.isdisjoint({id(row) for row in held})
    assert len(train) + len(held) == 10


def test_split_keeps_at_least_one_train_row():
    for n in [2, 3, 4, 5]:
        train, _ = _split(_rows(n), 0.9)

        assert len(train) >= 1


def test_split_n1_keeps_row_in_train():
    assert _split([{"instruction": "a", "output": "x"}], 0.2) == (
        [{"instruction": "a", "output": "x"}],
        [],
    )


def test_split_held_at_0_2_n10():
    _, held = _split(_rows(10), 0.2)

    assert [row["instruction"] for row in held] == ["i0", "i5"]


def test_seed_creates_parent_dirs_and_inserts(tmp_path):
    path = tmp_path / "sub" / "nested" / "mem.db"

    n = seed_memory_db(path)

    assert n == 11
    assert path.exists()


def test_seed_is_idempotent(tmp_path):
    path = tmp_path / "mem.db"

    assert seed_memory_db(path) == 11
    assert seed_memory_db(path) == 0
    assert _memory_row_count(path) == 11


def test_seed_overwrite_resets(tmp_path):
    path = tmp_path / "mem.db"

    seed_memory_db(path)

    assert seed_memory_db(path, overwrite=True) == 11
    assert _memory_row_count(path) == 11


def test_seeded_rows_have_expected_skills(tmp_path):
    path = tmp_path / "mem.db"
    seed_memory_db(path)

    with sqlite3.connect(path) as conn:
        skills = {
            row[0]
            for row in conn.execute("SELECT DISTINCT skill FROM memory")
        }

    assert "rust-coder" in skills
    assert "sql-expert" in skills


def test_is_success_coerces_judged_success_strings():
    assert is_success({"judged_success": "1"}) is True
    assert is_success({"judged_success": "0"}) is False


def test_is_success_skips_none_judged_success():
    assert is_success({"judged_success": None}) is True


def test_is_success_rejects_non_int_judged_success_string():
    assert is_success({"judged_success": "abc"}) is False


def test_is_success_parses_string_hermes_score():
    assert is_success({"judged_success": 1, "hermes_score": "0.9"}) is True


def test_is_success_is_permissive_for_unparseable_hermes_score():
    assert is_success({"judged_success": 1, "hermes_score": "junk"}) is True


def test_is_success_score_threshold_is_inclusive():
    assert is_success(
        {"judged_success": 1, "hermes_score": DEFAULT_SCORE_THRESHOLD}
    ) is True


def test_is_success_rejects_score_below_default_threshold():
    assert is_success({"judged_success": 1, "hermes_score": 0.59}) is False


def test_is_success_accepts_custom_threshold():
    assert is_success(
        {"judged_success": 1, "hermes_score": 0.5},
        threshold=0.4,
    ) is True
