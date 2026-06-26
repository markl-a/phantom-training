from __future__ import annotations

import json
from pathlib import Path

from phantom_training import cli
from phantom_training.demo_loop import PUBLIC_ARTIFACTS, write_training_demo_loop


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_demo_loop_writes_dataset_card_run_manifest_and_backend_contract(tmp_path: Path):
    bundle = write_training_demo_loop(tmp_path / "bundle")

    assert bundle.out_dir == tmp_path / "bundle"
    for name in PUBLIC_ARTIFACTS:
        assert (bundle.out_dir / name).exists(), name

    manifest = _read_json(bundle.out_dir / "manifest.json")
    assert manifest["schema_version"] == 1
    assert manifest["mode"] == "deterministic_training_planning_loop"
    assert manifest["synthetic_only"] is True
    assert manifest["real_training"] is False
    assert manifest["model_artifacts_written"] is False
    assert manifest["external_network"] is False
    assert manifest["gpu_required"] is False
    assert manifest["artifacts"] == PUBLIC_ARTIFACTS

    dataset_card = _read_json(bundle.out_dir / "dataset-card.json")
    assert dataset_card["schema_version"] == 1
    assert dataset_card["dataset_path"] == "dataset.jsonl"
    assert dataset_card["row_schema"] == ["instruction", "input", "output"]
    assert dataset_card["row_count"] == 8
    assert dataset_card["source"] == "synthetic fixture memory.db"
    assert dataset_card["private_data_included"] is False

    run_manifest = _read_json(bundle.out_dir / "run-manifest.json")
    assert run_manifest["schema_version"] == 1
    assert run_manifest["skill"] == "rust-coder"
    assert run_manifest["base_model"] == "qwen2.5-coder-7b"
    assert run_manifest["dry_run"] is True
    assert run_manifest["commit"] is False
    assert run_manifest["backend"] == "unsloth"
    assert run_manifest["dataset"]["rows"] == 8
    assert run_manifest["eval"]["n_rows"] == 8
    assert run_manifest["judge"]["n_accepted"] == 1

    adapter = _read_json(bundle.out_dir / "backend-adapter-contract.json")
    assert adapter["schema_version"] == 1
    assert adapter["adapter"] == "tier1-dry-run"
    assert adapter["real_training_enabled"] is False
    assert adapter["commit_requires_backend"] is True
    assert adapter["allowed_backends"] == ["unsloth", "axolotl"]
    assert adapter["tier1_commit_exit_code"] == 2


def test_demo_loop_dataset_is_alpaca_jsonl_and_synthetic(tmp_path: Path):
    bundle = write_training_demo_loop(tmp_path / "bundle")
    rows = [
        json.loads(line)
        for line in (bundle.out_dir / "dataset.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) == 8
    assert all(set(row) == {"instruction", "input", "output"} for row in rows)
    assert all(row["instruction"] and row["output"] for row in rows)
    assert "TODO" not in {row["output"] for row in rows}


def test_demo_loop_public_artifacts_are_deterministic(tmp_path: Path):
    first = write_training_demo_loop(tmp_path / "first")
    second = write_training_demo_loop(tmp_path / "second")

    for name in PUBLIC_ARTIFACTS:
        assert (first.out_dir / name).read_text(encoding="utf-8") == (
            second.out_dir / name
        ).read_text(encoding="utf-8"), name


def test_cli_demo_loop_subcommand_writes_bundle(tmp_path: Path, capsys):
    out = tmp_path / "bundle"

    rc = cli.main(["demo-loop", "--out", str(out)])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["artifacts"] == PUBLIC_ARTIFACTS
    assert (out / "manifest.json").exists()


def test_cli_backend_lifecycle_subcommand_writes_bundle(tmp_path: Path, capsys):
    out = tmp_path / "lifecycle"

    rc = cli.main(["backend-lifecycle", "--out", str(out)])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["artifacts"] == [
        "manifest.json",
        "backend-lifecycle.json",
        "dataset-card-validation.json",
        "run-manifest-validation.json",
        "audit-log.jsonl",
        "summary.md",
    ]
    assert (out / "manifest.json").exists()
