"""Deterministic backend lifecycle and public-contract validation bundle."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phantom_training.demo_loop import write_training_demo_loop


PUBLIC_ARTIFACTS = [
    "manifest.json",
    "backend-lifecycle.json",
    "dataset-card-validation.json",
    "run-manifest-validation.json",
    "audit-log.jsonl",
    "summary.md",
]

PRIVATE_MARKERS = (
    "BEGIN PRIVATE KEY",
    "hf_",
    "WANDB_API_KEY",
    "api_key",
    "PRIVATE_DATASET",
    "PRIVATE_PROMPT",
    "model.safetensors",
    "adapter_model.bin",
)

DATASET_CARD_REQUIRED_FIELDS = {
    "schema_version",
    "dataset_path",
    "dataset_type",
    "row_schema",
    "row_count",
    "source",
    "skill",
    "private_data_included",
    "model_artifacts_included",
    "license",
}

RUN_MANIFEST_REQUIRED_FIELDS = {
    "schema_version",
    "phantom_training_version",
    "mode",
    "skill",
    "base_model",
    "backend",
    "dry_run",
    "commit",
    "real_training",
    "dataset",
    "eval",
    "judge",
    "external_network",
    "gpu_required",
    "model_artifacts_written",
}


@dataclass(frozen=True)
class BackendLifecycleBundle:
    out_dir: Path
    artifacts: list[str]


def _dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_jsonl_rows(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _dataset_card_validation(source_dir: Path) -> dict[str, Any]:
    card = _read_json(source_dir / "dataset-card.json")
    row_count = _count_jsonl_rows(source_dir / "dataset.jsonl")
    missing = sorted(DATASET_CARD_REQUIRED_FIELDS.difference(card))
    row_schema_valid = card.get("row_schema") == ["instruction", "input", "output"]
    row_count_matches = card.get("row_count") == row_count
    return {
        "schema_version": 1,
        "valid": not missing
        and row_schema_valid
        and row_count_matches
        and card.get("private_data_included") is False
        and card.get("model_artifacts_included") is False,
        "required_fields_present": not missing,
        "missing_fields": missing,
        "row_schema_valid": row_schema_valid,
        "row_count": card.get("row_count"),
        "dataset_jsonl_rows": row_count,
        "row_count_matches_dataset": row_count_matches,
        "private_data_included": bool(card.get("private_data_included")),
        "model_artifacts_included": bool(card.get("model_artifacts_included")),
        "source": card.get("source"),
    }


def _run_manifest_validation(source_dir: Path) -> dict[str, Any]:
    run = _read_json(source_dir / "run-manifest.json")
    missing = sorted(RUN_MANIFEST_REQUIRED_FIELDS.difference(run))
    return {
        "schema_version": 1,
        "valid": not missing
        and run.get("dry_run") is True
        and run.get("commit") is False
        and run.get("real_training") is False
        and run.get("external_network") is False
        and run.get("gpu_required") is False
        and run.get("model_artifacts_written") is False,
        "required_fields_present": not missing,
        "missing_fields": missing,
        "dry_run": bool(run.get("dry_run")),
        "commit": bool(run.get("commit")),
        "real_training": bool(run.get("real_training")),
        "external_network": bool(run.get("external_network")),
        "gpu_required": bool(run.get("gpu_required")),
        "model_artifacts_written": bool(run.get("model_artifacts_written")),
        "backend": run.get("backend"),
    }


def _backend_lifecycle(source_dir: Path) -> dict[str, Any]:
    contract = _read_json(source_dir / "backend-adapter-contract.json")
    return {
        "schema_version": 1,
        "selected_stage": "tier1_disabled",
        "real_training_enabled": False,
        "commit_exit_code_without_backend": contract.get("tier1_commit_exit_code"),
        "allowed_future_backends": contract.get("allowed_backends", []),
        "private_data_upload_default": contract.get("private_data_upload_default"),
        "stages": [
            {
                "id": "tier1_plan",
                "description": "Build a deterministic dry-run training plan.",
                "public_default": True,
                "writes_model_artifacts": False,
            },
            {
                "id": "tier1_dataset",
                "description": "Build a synthetic Alpaca-style dataset fixture.",
                "public_default": True,
                "writes_model_artifacts": False,
            },
            {
                "id": "tier1_eval",
                "description": "Run deterministic proxy eval and hermetic judge.",
                "public_default": True,
                "writes_model_artifacts": False,
            },
            {
                "id": "tier1_disabled",
                "description": "Reject commit/publish paths because no real backend is shipped.",
                "public_default": True,
                "writes_model_artifacts": False,
            },
            {
                "id": "tier2_private_backend",
                "description": "Future opt-in real backend installed and configured by a private operator.",
                "public_default": False,
                "writes_model_artifacts": True,
            },
        ],
    }


def _audit_events(
    dataset_validation: dict[str, Any],
    run_validation: dict[str, Any],
    lifecycle: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "schema_version": 1,
            "event": "source_contracts_loaded",
            "contracts": ["dataset-card", "run-manifest", "backend-adapter"],
            "raw_payload_retained": False,
        },
        {
            "schema_version": 1,
            "event": "dataset_card_validated",
            "valid": dataset_validation["valid"],
            "row_count": dataset_validation["row_count"],
            "raw_payload_retained": False,
        },
        {
            "schema_version": 1,
            "event": "run_manifest_validated",
            "valid": run_validation["valid"],
            "backend": run_validation["backend"],
            "raw_payload_retained": False,
        },
        {
            "schema_version": 1,
            "event": "backend_lifecycle_evaluated",
            "selected_stage": lifecycle["selected_stage"],
            "real_training_enabled": lifecycle["real_training_enabled"],
            "raw_payload_retained": False,
        },
        {
            "schema_version": 1,
            "event": "artifact_written",
            "artifacts": PUBLIC_ARTIFACTS,
            "raw_payload_retained": False,
        },
    ]


def _write_audit_log(path: Path, events: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )


def _summary_md(manifest: dict[str, Any], dataset_validation: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Backend Lifecycle Validation",
            "",
            "This bundle validates Tier 1 dataset-card, run-manifest, and backend-adapter contracts.",
            "It performs no real training, writes no model artifacts, and enables no publish path.",
            "",
            f"- Dataset card valid: {dataset_validation['valid']}",
            f"- Dataset rows checked: {dataset_validation['dataset_jsonl_rows']}",
            f"- Selected backend stage: {manifest['selected_stage']}",
            "- Public default: dry-run only",
            "",
        ]
    )


def write_backend_lifecycle_bundle(out_dir: str | Path) -> BackendLifecycleBundle:
    """Write a deterministic validation bundle for Tier 1 backend lifecycle."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp:
        source_dir = Path(temp) / "source-demo"
        write_training_demo_loop(source_dir)
        dataset_validation = _dataset_card_validation(source_dir)
        run_validation = _run_manifest_validation(source_dir)
        lifecycle = _backend_lifecycle(source_dir)

    manifest = {
        "schema_version": 1,
        "mode": "synthetic_backend_lifecycle",
        "synthetic_only": True,
        "real_training": False,
        "model_artifacts_written": False,
        "external_network": False,
        "gpu_required": False,
        "publish_enabled": False,
        "selected_stage": lifecycle["selected_stage"],
        "artifacts": PUBLIC_ARTIFACTS,
    }

    _dump_json(out_path / "manifest.json", manifest)
    _dump_json(out_path / "backend-lifecycle.json", lifecycle)
    _dump_json(out_path / "dataset-card-validation.json", dataset_validation)
    _dump_json(out_path / "run-manifest-validation.json", run_validation)
    _write_audit_log(out_path / "audit-log.jsonl", _audit_events(dataset_validation, run_validation, lifecycle))
    (out_path / "summary.md").write_text(_summary_md(manifest, dataset_validation), encoding="utf-8")

    return BackendLifecycleBundle(out_dir=out_path, artifacts=list(PUBLIC_ARTIFACTS))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phantom-training-backend-lifecycle")
    parser.add_argument("--out", required=True, help="directory to write the lifecycle bundle")
    args = parser.parse_args(argv)

    try:
        bundle = write_backend_lifecycle_bundle(args.out)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    sys.stdout.write(
        json.dumps(
            {"out_dir": str(bundle.out_dir), "artifacts": bundle.artifacts},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
