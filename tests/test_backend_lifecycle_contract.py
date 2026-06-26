from __future__ import annotations

import json
from pathlib import Path

from phantom_training.backend_lifecycle import (
    PRIVATE_MARKERS,
    PUBLIC_ARTIFACTS,
    write_backend_lifecycle_bundle,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_backend_lifecycle_bundle_validates_public_contracts(tmp_path: Path):
    bundle = write_backend_lifecycle_bundle(tmp_path / "bundle")

    assert bundle.out_dir == tmp_path / "bundle"
    for name in PUBLIC_ARTIFACTS:
        assert (bundle.out_dir / name).exists(), name

    manifest = _read_json(bundle.out_dir / "manifest.json")
    assert manifest["schema_version"] == 1
    assert manifest["mode"] == "synthetic_backend_lifecycle"
    assert manifest["synthetic_only"] is True
    assert manifest["real_training"] is False
    assert manifest["model_artifacts_written"] is False
    assert manifest["external_network"] is False
    assert manifest["gpu_required"] is False
    assert manifest["publish_enabled"] is False
    assert manifest["artifacts"] == PUBLIC_ARTIFACTS

    lifecycle = _read_json(bundle.out_dir / "backend-lifecycle.json")
    assert lifecycle["selected_stage"] == "tier1_disabled"
    assert lifecycle["real_training_enabled"] is False
    assert lifecycle["commit_exit_code_without_backend"] == 2
    assert lifecycle["allowed_future_backends"] == ["unsloth", "axolotl"]
    assert [stage["id"] for stage in lifecycle["stages"]] == [
        "tier1_plan",
        "tier1_dataset",
        "tier1_eval",
        "tier1_disabled",
        "tier2_private_backend",
    ]
    assert lifecycle["stages"][-1]["public_default"] is False

    dataset_validation = _read_json(bundle.out_dir / "dataset-card-validation.json")
    assert dataset_validation["valid"] is True
    assert dataset_validation["row_count_matches_dataset"] is True
    assert dataset_validation["required_fields_present"] is True
    assert dataset_validation["private_data_included"] is False
    assert dataset_validation["model_artifacts_included"] is False

    run_validation = _read_json(bundle.out_dir / "run-manifest-validation.json")
    assert run_validation["valid"] is True
    assert run_validation["dry_run"] is True
    assert run_validation["commit"] is False
    assert run_validation["real_training"] is False
    assert run_validation["external_network"] is False
    assert run_validation["gpu_required"] is False
    assert run_validation["model_artifacts_written"] is False


def test_backend_lifecycle_audit_log_is_metadata_only(tmp_path: Path):
    bundle = write_backend_lifecycle_bundle(tmp_path / "bundle")

    events = [
        json.loads(line)
        for line in (bundle.out_dir / "audit-log.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert [event["event"] for event in events] == [
        "source_contracts_loaded",
        "dataset_card_validated",
        "run_manifest_validated",
        "backend_lifecycle_evaluated",
        "artifact_written",
    ]
    assert all(event["schema_version"] == 1 for event in events)
    assert all(event["raw_payload_retained"] is False for event in events)
    assert all("instruction" not in event for event in events)
    assert all("prompt" not in event for event in events)
    assert all("output" not in event for event in events)


def test_backend_lifecycle_public_artifacts_do_not_contain_private_markers(
    tmp_path: Path,
):
    bundle = write_backend_lifecycle_bundle(tmp_path / "bundle")

    for name in PUBLIC_ARTIFACTS:
        text = (bundle.out_dir / name).read_text(encoding="utf-8")
        for marker in PRIVATE_MARKERS:
            assert marker not in text, f"{marker!r} leaked in {name}"


def test_backend_lifecycle_bundle_is_deterministic(tmp_path: Path):
    first = write_backend_lifecycle_bundle(tmp_path / "first")
    second = write_backend_lifecycle_bundle(tmp_path / "second")

    for name in PUBLIC_ARTIFACTS:
        assert (first.out_dir / name).read_text(encoding="utf-8") == (
            second.out_dir / name
        ).read_text(encoding="utf-8"), name
