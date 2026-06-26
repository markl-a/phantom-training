"""Deterministic Tier 1 eval/judge pipeline scenario bundle."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phantom_training.backend_lifecycle import write_backend_lifecycle_bundle
from phantom_training.demo_loop import write_training_demo_loop


SCHEMA_VERSION = 1

PUBLIC_ARTIFACTS = {
    "audit_summary": "audit-summary.json",
    "eval_report": "eval-report.json",
    "judge_report": "judge-report.json",
    "release_gate": "release-gate.json",
    "reproducibility_report": "reproducibility-report.json",
    "summary": "summary.md",
}


@dataclass(frozen=True)
class EvalJudgeScenarioBundle:
    out_dir: Path
    artifacts: dict[str, str]


def write_eval_judge_scenario(out_dir: str | Path) -> EvalJudgeScenarioBundle:
    """Write a reproducible Tier 1 eval/judge reporting scenario."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    training_demo = write_training_demo_loop(out_path / "training-demo")
    backend_lifecycle = write_backend_lifecycle_bundle(out_path / "backend-lifecycle")

    demo_manifest = _load_json(training_demo.out_dir / "manifest.json")
    run_manifest = _load_json(training_demo.out_dir / "run-manifest.json")
    eval_result = _load_json(training_demo.out_dir / "eval.json")
    judge_result = _load_json(training_demo.out_dir / "judge.json")
    dataset_card = _load_json(training_demo.out_dir / "dataset-card.json")
    lifecycle_manifest = _load_json(backend_lifecycle.out_dir / "manifest.json")
    lifecycle = _load_json(backend_lifecycle.out_dir / "backend-lifecycle.json")
    dataset_validation = _load_json(backend_lifecycle.out_dir / "dataset-card-validation.json")
    run_validation = _load_json(backend_lifecycle.out_dir / "run-manifest-validation.json")

    eval_report = _eval_report(eval_result)
    judge_report = _judge_report(judge_result)
    reproducibility = _reproducibility_report(
        run_manifest,
        dataset_card,
        dataset_validation,
        run_validation,
        lifecycle,
    )
    release_gate = _release_gate(eval_report, judge_report, reproducibility)
    audit_summary = _audit_summary(reproducibility)

    _dump_json(out_path / "eval-report.json", eval_report)
    _dump_json(out_path / "judge-report.json", judge_report)
    _dump_json(out_path / "reproducibility-report.json", reproducibility)
    _dump_json(out_path / "release-gate.json", release_gate)
    _dump_json(out_path / "audit-summary.json", audit_summary)
    (out_path / "summary.md").write_text(
        _summary_md(eval_report, judge_report, release_gate),
        encoding="utf-8",
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "mode": "synthetic_eval_judge_pipeline_scenario",
        "synthetic_only": True,
        "real_training": False,
        "model_artifacts_written": False,
        "external_network": False,
        "gpu_required": False,
        "publish_enabled": False,
        "source_bundles": {
            "backend_lifecycle": "backend-lifecycle/manifest.json",
            "training_demo": "training-demo/manifest.json",
        },
        "source_modes": {
            "backend_lifecycle": lifecycle_manifest.get("mode", ""),
            "training_demo": demo_manifest.get("mode", ""),
        },
        "artifacts": PUBLIC_ARTIFACTS,
    }
    _dump_json(out_path / "manifest.json", manifest)
    return EvalJudgeScenarioBundle(out_dir=out_path, artifacts=dict(PUBLIC_ARTIFACTS))


def _eval_report(eval_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "deterministic_eval_report",
        "metric_kind": "proxy_floor_not_public_benchmark",
        "baseline": eval_result.get("baseline", ""),
        "n_rows": int(eval_result.get("n_rows") or 0),
        "n_train": int(eval_result.get("n_train") or 0),
        "n_holdout": int(eval_result.get("n_holdout") or 0),
        "exact_match": float(eval_result.get("exact_match") or 0.0),
        "token_f1": float(eval_result.get("token_f1") or 0.0),
        "model_inference": False,
        "public_benchmark": False,
    }


def _judge_report(judge_result: dict[str, Any]) -> dict[str, Any]:
    total = int(judge_result.get("n_total") or 0)
    accepted = int(judge_result.get("n_accepted") or 0)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "hermetic_judge_report",
        "threshold": float(judge_result.get("threshold") or 0.0),
        "n_total": total,
        "n_accepted": accepted,
        "accepted_rate": accepted / total if total else 0.0,
        "model_inference": False,
        "external_network": False,
        "result_bodies_retained": False,
    }


def _reproducibility_report(
    run_manifest: dict[str, Any],
    dataset_card: dict[str, Any],
    dataset_validation: dict[str, Any],
    run_validation: dict[str, Any],
    lifecycle: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "tier1_reproducibility_report",
        "skill": run_manifest.get("skill", ""),
        "base_model": run_manifest.get("base_model", ""),
        "backend": run_manifest.get("backend", ""),
        "dataset_rows": int(dataset_card.get("row_count") or 0),
        "dataset_source": dataset_card.get("source", ""),
        "dataset_card_valid": dataset_validation.get("valid") is True,
        "run_manifest_valid": run_validation.get("valid") is True,
        "backend_stage": lifecycle.get("selected_stage", ""),
        "real_training": False,
        "model_artifacts_written": False,
        "external_network": False,
        "gpu_required": False,
        "publish_enabled": False,
        "source_bodies_retained": False,
        "prompt_text_retained": False,
    }


def _release_gate(
    eval_report: dict[str, Any],
    judge_report: dict[str, Any],
    reproducibility: dict[str, Any],
) -> dict[str, Any]:
    tier1_ready = (
        eval_report["n_rows"] > 0
        and judge_report["n_total"] > 0
        and reproducibility["dataset_card_valid"] is True
        and reproducibility["run_manifest_valid"] is True
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "tier1_release_gate",
        "tier1_demo_ready": tier1_ready,
        "real_training_release_ready": False,
        "publish_enabled": False,
        "safe_public_default": "dry_run_only",
        "required_before_real_training_release": [
            "real_backend_adapter",
            "private_data_policy_review",
            "model_artifact_scan",
            "operator_approval",
        ],
    }


def _audit_summary(reproducibility: dict[str, Any]) -> dict[str, Any]:
    events = [
        "source_bundles_built",
        "eval_report_built",
        "judge_report_built",
        "reproducibility_checked",
        "release_gate_evaluated",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "metadata_only_eval_judge_audit",
        "event_count": len(events),
        "events": events,
        "dataset_rows": reproducibility["dataset_rows"],
        "dataset_rows_retained": False,
        "prompt_text_retained": False,
        "model_artifacts_retained": False,
        "external_network": False,
        "gpu_required": False,
    }


def _summary_md(
    eval_report: dict[str, Any],
    judge_report: dict[str, Any],
    release_gate: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Eval/judge pipeline scenario",
            "",
            "This bundle proves the Tier 1 deterministic eval and hermetic judge reporting path.",
            "It performs no real training, writes no model artifacts, and publishes nothing.",
            "",
            f"- Eval rows: {eval_report['n_rows']}",
            f"- Eval token_f1: {eval_report['token_f1']}",
            f"- Judge accepted: {judge_report['n_accepted']}/{judge_report['n_total']}",
            f"- Tier 1 demo ready: {release_gate['tier1_demo_ready']}",
            "- Real training release ready: false",
            "",
        ]
    )


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"{path.name} must contain a JSON object")
    return raw


def _dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phantom-training-eval-judge-scenario")
    parser.add_argument("--out", required=True, help="directory to write the scenario bundle")
    args = parser.parse_args(argv)

    try:
        bundle = write_eval_judge_scenario(args.out)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(str(bundle.out_dir / "manifest.json") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
