"""Seed a small fixture ``memory.db`` of real-shaped agent trajectories.

This stands in for the production trajectory store. In production, rows in
``memory.db`` come from *real captured agent sessions*: phantom-mesh records
each ``(skill, prompt, response)`` turn, the Hermes Curator judges it
(``judged_success`` / ``hermes_score``), and successful turns accumulate here.
On a fresh machine that store is empty, so for a runnable end-to-end demo we
seed a handful of genuine prompt->response coding pairs that match the schema
documented at ``dataset.py:1-28`` exactly.

The pairs below are real, correct Q->A coding examples (not lorem-ipsum),
so the resulting dataset and eval reflect honest data shapes. They are NOT
machine-captured trajectories — see the caveat in the README / task report.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory(
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

# (skill, prompt, response, judged_success, hermes_score, tags)
# Real, correct coding Q->A pairs. A couple of deliberately-failed rows are
# included so the Curator judge has something real to filter out.
_SEED_ROWS: list[tuple[str, str, str, int, float, str]] = [
    (
        "rust-coder",
        "Write a Rust function `add(a: i32, b: i32) -> i32` that returns the sum.",
        "fn add(a: i32, b: i32) -> i32 {\n    a + b\n}",
        1,
        0.93,
        "rust,function",
    ),
    (
        "rust-coder",
        "Write a Rust function `is_even(n: i64) -> bool` returning true for even numbers.",
        "fn is_even(n: i64) -> bool {\n    n % 2 == 0\n}",
        1,
        0.88,
        "rust,bool",
    ),
    (
        "rust-coder",
        "Reverse a string in Rust: `fn reverse(s: &str) -> String`.",
        "fn reverse(s: &str) -> String {\n    s.chars().rev().collect()\n}",
        1,
        0.90,
        "rust,string",
    ),
    (
        "rust-coder",
        "Write a `#[test]` that asserts `add(2, 3) == 5`.",
        "#[test]\nfn test_add() {\n    assert_eq!(add(2, 3), 5);\n}",
        1,
        0.71,
        "rust,test",
    ),
    (
        "rust-coder",
        "Compute the factorial of n in Rust: `fn factorial(n: u64) -> u64`.",
        "fn factorial(n: u64) -> u64 {\n    (1..=n).product()\n}",
        1,
        0.85,
        "rust,recursion",
    ),
    (
        "rust-coder",
        "Find the max element of a slice: `fn max_of(xs: &[i32]) -> Option<i32>`.",
        "fn max_of(xs: &[i32]) -> Option<i32> {\n    xs.iter().copied().max()\n}",
        1,
        0.82,
        "rust,slice",
    ),
    (
        "rust-coder",
        "Count vowels in a string: `fn count_vowels(s: &str) -> usize`.",
        "fn count_vowels(s: &str) -> usize {\n    s.chars().filter(|c| \"aeiouAEIOU\".contains(*c)).count()\n}",
        1,
        0.79,
        "rust,string",
    ),
    (
        "rust-coder",
        "Write `fn fib(n: u32) -> u64` returning the n-th Fibonacci number.",
        "fn fib(n: u32) -> u64 {\n    let (mut a, mut b) = (0u64, 1u64);\n    for _ in 0..n {\n        let t = a + b;\n        a = b;\n        b = t;\n    }\n    a\n}",
        1,
        0.86,
        "rust,iter",
    ),
    # --- rows the Curator should drop (real failures / low score) ---
    (
        "rust-coder",
        "Sort a vector in place.",
        "i'm not sure, maybe use sort?",
        0,
        0.12,
        "rust,fail",
    ),
    (
        "rust-coder",
        "Parse an integer from a string with error handling.",
        "TODO",
        1,
        0.20,
        "rust,fail",
    ),
    # --- a different skill, to prove per-skill filtering works ---
    (
        "sql-expert",
        "Select all rows from users where age > 18.",
        "SELECT * FROM users WHERE age > 18;",
        1,
        0.95,
        "sql,select",
    ),
]


def seed_memory_db(db_path: Path | str, *, overwrite: bool = False) -> int:
    """Create/populate a fixture ``memory.db``. Returns rows inserted.

    Idempotent: if the DB already has rows and ``overwrite`` is False, it is
    left untouched and ``0`` is returned.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.executescript(_SCHEMA)
        existing = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        if existing and not overwrite:
            return 0
        if overwrite:
            conn.execute("DELETE FROM memory")
        ts = 1_700_000_000
        for i, (skill, prompt, response, ok, score, tags) in enumerate(_SEED_ROWS):
            conn.execute(
                "INSERT INTO memory(ts, skill, prompt, response, judged_success, hermes_score, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ts + i, skill, prompt, response, ok, score, tags),
            )
        conn.commit()
        return len(_SEED_ROWS)
    finally:
        conn.close()
