from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_public_demo_contract() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Quickstart" in readme
    assert "docs/PUBLIC_DEMO.md" in readme
    assert "seed-fixture" in readme
    assert "build-dataset" in readme
    assert "demo-loop" in readme
    assert "backend-lifecycle" in readme
    assert "eval-judge-scenario" in readme
    assert "docs/EVAL_JUDGE_SCENARIO.md" in readme
    assert "eval" in readme
    assert "judge" in readme
    assert "非真訓練" in readme or "not real training" in readme


def test_public_demo_documents_artifact_and_safety_boundary() -> None:
    doc = (REPO_ROOT / "docs" / "PUBLIC_DEMO.md").read_text(encoding="utf-8")

    assert "dataset.jsonl" in doc
    assert "memory.db" in doc
    assert "--commit" in doc
    assert "exit 2" in doc
    assert "not a public benchmark" in doc
    assert "private prompts" in doc
    assert "private datasets" in doc
    assert "not model inference" in doc


def test_public_demo_documents_p2_artifact_contract() -> None:
    doc = (REPO_ROOT / "docs" / "PUBLIC_DEMO.md").read_text(encoding="utf-8")

    assert "dataset-card.json" in doc
    assert "run-manifest.json" in doc
    assert "backend-adapter-contract.json" in doc
    assert "backend-lifecycle.json" in doc
    assert "dataset-card-validation.json" in doc
    assert "run-manifest-validation.json" in doc
    assert "real_training=false" in doc
    assert "model_artifacts_written=false" in doc
    assert "external_network=false" in doc


def test_public_demo_documents_p3_eval_judge_scenario_contract() -> None:
    doc = (REPO_ROOT / "docs" / "PUBLIC_DEMO.md").read_text(encoding="utf-8")

    assert "eval-judge-scenario" in doc
    assert "eval-report.json" in doc
    assert "judge-report.json" in doc
    assert "reproducibility-report.json" in doc
    assert "release-gate.json" in doc
    assert "audit-summary.json" in doc
    assert "proxy floor" in doc
    assert "not a public benchmark" in doc
    assert "not model inference" in doc


def test_eval_judge_scenario_doc_documents_safety_boundary() -> None:
    doc = (REPO_ROOT / "docs" / "EVAL_JUDGE_SCENARIO.md").read_text(encoding="utf-8")

    assert "synthetic_eval_judge_pipeline_scenario" in doc
    assert "eval-report.json" in doc
    assert "judge-report.json" in doc
    assert "reproducibility-report.json" in doc
    assert "release-gate.json" in doc
    assert "real_training" in doc
    assert "model_artifacts_written" in doc
    assert "external_network" in doc
    assert "gpu_required" in doc
    assert "publish_enabled" in doc
    assert "not a public benchmark" in doc


def test_pyproject_exposes_backend_lifecycle_and_scenario_entrypoints() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "phantom-training-backend-lifecycle" in pyproject
    assert "phantom_training.backend_lifecycle:main" in pyproject
    assert "phantom-training-eval-judge-scenario" in pyproject
    assert "phantom_training.eval_judge_scenario:main" in pyproject
