from __future__ import annotations

import json
from pathlib import Path

from phantom_training.backend_lifecycle import _dataset_card_validation, _run_manifest_validation


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows),
        encoding="utf-8",
    )


def _valid_card() -> dict:
    return {
        "schema_version": 1,
        "dataset_path": "dataset.jsonl",
        "dataset_type": "alpaca_instruction_jsonl",
        "row_schema": ["instruction", "input", "output"],
        "row_count": 3,
        "source": "test",
        "skill": "test",
        "private_data_included": False,
        "model_artifacts_included": False,
        "license": "MIT",
    }


def _valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "phantom_training_version": "0.1.0a0",
        "mode": "test",
        "skill": "test",
        "base_model": "qwen2.5-coder-7b",
        "backend": "unsloth",
        "dry_run": True,
        "commit": False,
        "real_training": False,
        "dataset": {"path": "dataset.jsonl", "rows": 3},
        "eval": {"n_rows": 3},
        "judge": {"n_total": 1, "n_accepted": 1},
        "external_network": False,
        "gpu_required": False,
        "model_artifacts_written": False,
    }


def test_dataset_card_missing_field(tmp_path: Path):
    source = tmp_path / "s"
    source.mkdir()
    card = _valid_card()
    del card["schema_version"]
    _write_json(source / "dataset-card.json", card)
    _write_jsonl(source / "dataset.jsonl", [{"instruction": "a", "input": "", "output": "b"}])

    result = _dataset_card_validation(source)

    assert result["valid"] is False
    assert "schema_version" in result["missing_fields"]


def test_dataset_card_row_count_mismatch(tmp_path: Path):
    source = tmp_path / "s"
    source.mkdir()
    _write_json(source / "dataset-card.json", _valid_card() | {"row_count": 999})
    _write_jsonl(
        source / "dataset.jsonl",
        [{"instruction": "a", "input": "", "output": "b"} for _ in range(3)],
    )

    result = _dataset_card_validation(source)

    assert result["valid"] is False
    assert result["row_count"] == 999
    assert result["dataset_jsonl_rows"] == 3
    assert result["row_count_matches_dataset"] is False


def test_dataset_card_private_data_included_true(tmp_path: Path):
    source = tmp_path / "s"
    source.mkdir()
    _write_json(source / "dataset-card.json", _valid_card() | {"private_data_included": True})
    _write_jsonl(source / "dataset.jsonl", [{"instruction": "a", "input": "", "output": "b"}])

    result = _dataset_card_validation(source)

    assert result["valid"] is False
    assert result["private_data_included"] is True


def test_dataset_card_model_artifacts_included_true(tmp_path: Path):
    source = tmp_path / "s"
    source.mkdir()
    _write_json(source / "dataset-card.json", _valid_card() | {"model_artifacts_included": True})
    _write_jsonl(source / "dataset.jsonl", [{"instruction": "a", "input": "", "output": "b"}])

    result = _dataset_card_validation(source)

    assert result["valid"] is False
    assert result["model_artifacts_included"] is True


def test_run_manifest_missing_field(tmp_path: Path):
    source = tmp_path / "s"
    source.mkdir()
    manifest = _valid_manifest()
    del manifest["real_training"]
    _write_json(source / "run-manifest.json", manifest)

    result = _run_manifest_validation(source)

    assert result["valid"] is False
    assert "real_training" in result["missing_fields"]


def test_run_manifest_real_training_true(tmp_path: Path):
    source = tmp_path / "s"
    source.mkdir()
    _write_json(source / "run-manifest.json", _valid_manifest() | {"real_training": True})

    result = _run_manifest_validation(source)

    assert result["valid"] is False
    assert result["real_training"] is True


def test_run_manifest_commit_true(tmp_path: Path):
    source = tmp_path / "s"
    source.mkdir()
    _write_json(source / "run-manifest.json", _valid_manifest() | {"commit": True})

    result = _run_manifest_validation(source)

    assert result["valid"] is False
    assert result["commit"] is True


def test_run_manifest_external_network_true(tmp_path: Path):
    source = tmp_path / "s"
    source.mkdir()
    _write_json(source / "run-manifest.json", _valid_manifest() | {"external_network": True})

    result = _run_manifest_validation(source)

    assert result["valid"] is False
    assert result["external_network"] is True
