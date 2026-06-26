from __future__ import annotations

import json
from pathlib import Path

from phantom_training import cli
from phantom_training.backend_lifecycle import PRIVATE_MARKERS
from phantom_training import eval_judge_scenario


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_eval_judge_scenario_writes_reproducible_report_bundle(
    tmp_path: Path,
    capsys,
) -> None:
    out = tmp_path / "scenario"

    assert eval_judge_scenario.main(["--out", str(out)]) == 0
    manifest_path = Path(capsys.readouterr().out.strip())
    assert manifest_path == out / "manifest.json"

    manifest = _read_json(manifest_path)
    eval_report = _read_json(out / "eval-report.json")
    judge_report = _read_json(out / "judge-report.json")
    reproducibility = _read_json(out / "reproducibility-report.json")
    release_gate = _read_json(out / "release-gate.json")
    audit = _read_json(out / "audit-summary.json")
    summary = (out / "summary.md").read_text(encoding="utf-8")

    assert manifest["schema_version"] == 1
    assert manifest["mode"] == "synthetic_eval_judge_pipeline_scenario"
    assert manifest["synthetic_only"] is True
    assert manifest["real_training"] is False
    assert manifest["model_artifacts_written"] is False
    assert manifest["external_network"] is False
    assert manifest["gpu_required"] is False
    assert manifest["publish_enabled"] is False
    assert manifest["source_bundles"] == {
        "backend_lifecycle": "backend-lifecycle/manifest.json",
        "training_demo": "training-demo/manifest.json",
    }
    assert manifest["artifacts"] == {
        "audit_summary": "audit-summary.json",
        "eval_report": "eval-report.json",
        "judge_report": "judge-report.json",
        "release_gate": "release-gate.json",
        "reproducibility_report": "reproducibility-report.json",
        "summary": "summary.md",
    }

    assert (out / "training-demo" / "manifest.json").exists()
    assert (out / "backend-lifecycle" / "manifest.json").exists()

    assert eval_report["mode"] == "deterministic_eval_report"
    assert eval_report["metric_kind"] == "proxy_floor_not_public_benchmark"
    assert eval_report["n_rows"] == 8
    assert eval_report["n_holdout"] == 2
    assert eval_report["token_f1"] == 0.2353
    assert eval_report["exact_match"] == 0.0

    assert judge_report["mode"] == "hermetic_judge_report"
    assert judge_report["n_total"] == 1
    assert judge_report["n_accepted"] == 1
    assert judge_report["accepted_rate"] == 1.0
    assert judge_report["model_inference"] is False

    assert reproducibility["mode"] == "tier1_reproducibility_report"
    assert reproducibility["dataset_card_valid"] is True
    assert reproducibility["run_manifest_valid"] is True
    assert reproducibility["dataset_rows"] == 8
    assert reproducibility["backend_stage"] == "tier1_disabled"
    assert reproducibility["source_bodies_retained"] is False

    assert release_gate["mode"] == "tier1_release_gate"
    assert release_gate["tier1_demo_ready"] is True
    assert release_gate["real_training_release_ready"] is False
    assert release_gate["publish_enabled"] is False
    assert release_gate["required_before_real_training_release"] == [
        "real_backend_adapter",
        "private_data_policy_review",
        "model_artifact_scan",
        "operator_approval",
    ]

    assert audit["mode"] == "metadata_only_eval_judge_audit"
    assert audit["event_count"] == 5
    assert audit["dataset_rows_retained"] is False
    assert audit["prompt_text_retained"] is False
    assert audit["model_artifacts_retained"] is False
    assert "Eval/judge pipeline scenario" in summary


def test_eval_judge_scenario_is_deterministic_and_public_safe(
    tmp_path: Path,
    capsys,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    assert eval_judge_scenario.main(["--out", str(first)]) == 0
    capsys.readouterr()
    assert eval_judge_scenario.main(["--out", str(second)]) == 0
    capsys.readouterr()

    files = (
        "manifest.json",
        "eval-report.json",
        "judge-report.json",
        "reproducibility-report.json",
        "release-gate.json",
        "audit-summary.json",
        "summary.md",
        "training-demo/eval.json",
        "backend-lifecycle/backend-lifecycle.json",
    )
    for rel in files:
        assert (first / rel).read_text(encoding="utf-8") == (second / rel).read_text(
            encoding="utf-8"
        )

    exported_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in first.rglob("*")
        if path.is_file() and path.suffix != ".db"
    )
    forbidden = (*PRIVATE_MARKERS, "PRIVATE_DATASET", "PRIVATE_PROMPT")
    assert all(term not in exported_text for term in forbidden)


def test_cli_eval_judge_scenario_subcommand_writes_bundle(
    tmp_path: Path,
    capsys,
) -> None:
    out = tmp_path / "scenario"

    rc = cli.main(["eval-judge-scenario", "--out", str(out)])

    assert rc == 0
    assert Path(capsys.readouterr().out.strip()) == out / "manifest.json"
    assert (out / "eval-report.json").exists()
