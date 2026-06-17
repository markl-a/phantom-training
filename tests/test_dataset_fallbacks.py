import sqlite3

from phantom_training import dataset
from phantom_training.dataset import extract_from_fts5


EXPECTED_ROW_KEYS = {
    "id",
    "ts",
    "skill",
    "prompt",
    "response",
    "judged_success",
    "hermes_score",
    "tags",
}


def test_minimal_schema_uses_fallback_query(tmp_path):
    db_path = tmp_path / "memory.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE memory(id INTEGER PRIMARY KEY, skill TEXT, prompt TEXT, response TEXT)"
    )
    conn.executemany(
        "INSERT INTO memory(skill, prompt, response) VALUES (?, ?, ?)",
        [
            ("rust-coder", "prompt 1", "response 1"),
            ("rust-coder", "prompt 2", "response 2"),
            ("other", "prompt 3", "response 3"),
        ],
    )
    conn.commit()
    conn.close()

    rows = extract_from_fts5("rust-coder", db_path)

    assert len(rows) == 2
    assert all(row["skill"] == "rust-coder" for row in rows)
    for row in rows:
        assert set(row) == EXPECTED_ROW_KEYS
        assert row["judged_success"] == 0
        assert row["hermes_score"] is None
        assert row["ts"] is None
        assert row["tags"] is None


def test_full_schema_primary_path(tmp_path):
    db_path = tmp_path / "memory.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE memory(
            id INTEGER PRIMARY KEY,
            ts INTEGER,
            skill TEXT,
            prompt TEXT,
            response TEXT,
            judged_success INTEGER,
            hermes_score REAL,
            tags TEXT
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO memory(
            skill, prompt, response, judged_success, hermes_score, tags, ts
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("rust-coder", "prompt 1", "response 1", 1, 0.9, "rust", 100),
            ("rust-coder", "prompt 2", "response 2", 1, 0.8, "rust", 200),
            ("rust-coder", "prompt 3", "response 3", 1, 0.7, "rust", 300),
            ("rust-coder", "prompt 4", "response 4", 0, 1.0, "rust", 400),
        ],
    )
    conn.commit()
    conn.close()

    rows = extract_from_fts5("rust-coder", db_path)

    assert len(rows) == 3
    assert all(set(row) == EXPECTED_ROW_KEYS for row in rows)
    assert all(row["skill"] == "rust-coder" for row in rows)
    assert all(row["judged_success"] == 1 for row in rows)


def test_corrupt_db_returns_empty_not_raise(tmp_path):
    db_path = tmp_path / "memory.db"
    db_path.write_bytes(b"not a sqlite database")

    assert extract_from_fts5("x", db_path) == []


def test_table_missing_returns_empty(tmp_path):
    db_path = tmp_path / "memory.db"
    conn = sqlite3.connect(db_path)
    conn.close()

    assert extract_from_fts5("x", db_path) == []


def test_limit_is_respected(tmp_path):
    db_path = tmp_path / "memory.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE memory(id INTEGER PRIMARY KEY, skill TEXT, prompt TEXT, response TEXT)"
    )
    conn.executemany(
        "INSERT INTO memory(skill, prompt, response) VALUES (?, ?, ?)",
        [
            ("rust-coder", f"prompt {i}", f"response {i}")
            for i in range(5)
        ],
    )
    conn.commit()
    conn.close()

    rows = extract_from_fts5("rust-coder", db_path, limit=2)

    assert len(rows) == 2


def test_readonly_mode_does_not_create_db(tmp_path):
    db_path = tmp_path / "nope.db"

    assert extract_from_fts5("x", db_path) == []
    assert not db_path.exists()


def test_connect_failure_returns_empty_not_raise(tmp_path, monkeypatch):
    """If sqlite3.connect itself raises (e.g. EMFILE / OS-level open failure
    after the existence check), extract_from_fts5 must degrade to [] rather
    than propagate the error and crash the planner."""
    db_path = tmp_path / "memory.db"
    db_path.write_bytes(b"")  # exists() check passes

    def _boom(*_a, **_k):
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(dataset.sqlite3, "connect", _boom)

    assert extract_from_fts5("x", db_path) == []
