"""Deterministic Tier 1 training-planning demo bundle."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phantom_training import __version__
from phantom_training import eval as eval_mod
from phantom_training.config import validate_recipe
from phantom_training.dataset import dedupe_instruction_rows, extract_from_fts5, to_instruction_rows
from phantom_training.fixtures import seed_memory_db
from phantom_training.hermetic_judge import judge_task
from phantom_training.judge import filter_success_cases


SKILL = "rust-coder"
BASE_MODEL = "qwen2.5-coder-7b"
RECIPE_PATH = Path(__file__).resolve().parents[1] / "examples" / "rust-coder.toml"

PUBLIC_ARTIFACTS = [
    "manifest.json",
    "dataset.jsonl",
    "dataset-card.json",
    "run-manifest.json",
    "backend-adapter-contract.json",
    "eval.json",
    "judge.json",
    "summary.md",
]


@dataclass(frozen=True)
class DemoLoopBundle:
    out_dir: Path
    artifacts: list[str]


def _dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_recipe() -> dict[str, Any]:
    with RECIPE_PATH.open("rb") as handle:
        recipe = tomllib.load(handle)
    problems = validate_recipe(recipe)
    if problems:
        raise RuntimeError("invalid bundled recipe: " + "; ".join(problems))
    return recipe


def _write_dataset(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _build_instruction_rows(db_path: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    seed_memory_db(db_path, overwrite=True)
    rows = extract_from_fts5(SKILL, db_path)
    kept = list(filter_success_cases(rows))
    paired = to_instruction_rows(kept)
    deduped = dedupe_instruction_rows(paired)
    return deduped, {
        "candidate_rows": len(rows),
        "rows_after_curator": len(kept),
        "paired_rows": len(paired),
        "deduped_rows": len(deduped),
        "duplicates_dropped": len(paired) - len(deduped),
    }


def _dataset_card(rows: list[dict[str, str]], stats: dict[str, int]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dataset_path": "dataset.jsonl",
        "dataset_type": "alpaca_instruction_jsonl",
        "row_schema": ["instruction", "input", "output"],
        "row_count": len(rows),
        "source": "synthetic fixture memory.db",
        "skill": SKILL,
        "curator": {
            "candidate_rows": stats["candidate_rows"],
            "rows_after_curator": stats["rows_after_curator"],
            "duplicates_dropped": stats["duplicates_dropped"],
        },
        "private_data_included": False,
        "model_artifacts_included": False,
        "license": "Apache-2.0 project fixtures; synthetic examples only",
    }


def _backend_adapter_contract(recipe: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "adapter": "tier1-dry-run",
        "real_training_enabled": False,
        "commit_requires_backend": True,
        "tier1_commit_exit_code": 2,
        "allowed_backends": ["unsloth", "axolotl"],
        "selected_backend": recipe.get("backend", "unsloth"),
        "requires_explicit_install_extras": True,
        "no_model_download": True,
        "no_gpu_required": True,
        "no_weight_publish": True,
        "private_data_upload_default": "disabled",
    }


def _judge_result() -> dict[str, Any]:
    task = {
        "kind": "qa",
        "prompt": "What command builds the public demo dataset?",
        "response": "build-dataset",
        "reference": "build-dataset",
    }
    result = judge_task(task)
    return {
        "threshold": 0.6,
        "n_total": 1,
        "n_accepted": 1 if result["accepted"] else 0,
        "results": [result],
    }


def _run_manifest(
    recipe: dict[str, Any],
    dataset_card: dict[str, Any],
    eval_result: dict[str, Any],
    judge_result: dict[str, Any],
    artifacts: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phantom_training_version": __version__,
        "mode": "deterministic_training_planning_loop",
        "skill": SKILL,
        "base_model": BASE_MODEL,
        "backend": recipe.get("backend", "unsloth"),
        "dry_run": True,
        "commit": False,
        "real_training": False,
        "dataset": {
            "path": dataset_card["dataset_path"],
            "rows": dataset_card["row_count"],
            "source": dataset_card["source"],
        },
        "lora": {
            "rank": recipe.get("lora_rank", 16),
            "alpha": recipe.get("lora_alpha", 32),
            "dropout": recipe.get("lora_dropout", 0.05),
        },
        "optimizer": {
            "lr": recipe.get("lr", 2.0e-4),
            "epochs": recipe.get("epochs", 3),
            "batch_size": recipe.get("batch_size", 4),
            "grad_accum": recipe.get("grad_accum", 4),
        },
        "eval": eval_result,
        "judge": {
            "n_total": judge_result["n_total"],
            "n_accepted": judge_result["n_accepted"],
            "threshold": judge_result["threshold"],
        },
        "artifacts": artifacts,
        "external_network": False,
        "gpu_required": False,
        "model_artifacts_written": False,
    }


def write_training_demo_loop(out_dir: str | Path) -> DemoLoopBundle:
    """Write a deterministic P2 training-planning artifact bundle."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    db_path = out_path / "memory.db"
    dataset_path = out_path / "dataset.jsonl"

    recipe = _load_recipe()
    rows, stats = _build_instruction_rows(db_path)
    _write_dataset(dataset_path, rows)

    eval_result = eval_mod.evaluate(dataset_path, holdout_fraction=0.2)
    judge = _judge_result()
    dataset_card = _dataset_card(rows, stats)
    adapter = _backend_adapter_contract(recipe)
    run_manifest = _run_manifest(recipe, dataset_card, eval_result, judge, PUBLIC_ARTIFACTS)
    manifest = {
        "schema_version": 1,
        "mode": "deterministic_training_planning_loop",
        "synthetic_only": True,
        "real_training": False,
        "model_artifacts_written": False,
        "external_network": False,
        "gpu_required": False,
        "local_backend_required": False,
        "artifacts": PUBLIC_ARTIFACTS,
    }

    _dump_json(out_path / "manifest.json", manifest)
    _dump_json(out_path / "dataset-card.json", dataset_card)
    _dump_json(out_path / "eval.json", eval_result)
    _dump_json(out_path / "judge.json", judge)
    _dump_json(out_path / "backend-adapter-contract.json", adapter)
    _dump_json(out_path / "run-manifest.json", run_manifest)
    (out_path / "summary.md").write_text(
        "\n".join(
            [
                "# Deterministic Training-Planning Demo",
                "",
                "This bundle is Tier 1 plumbing only: no real training, no model download, no GPU run, and no weight publishing.",
                "",
                f"- Skill: {SKILL}",
                f"- Base model: {BASE_MODEL}",
                f"- Dataset rows: {dataset_card['row_count']}",
                f"- Eval token_f1: {eval_result.get('token_f1')}",
                f"- Judge accepted: {judge['n_accepted']}/{judge['n_total']}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return DemoLoopBundle(out_dir=out_path, artifacts=list(PUBLIC_ARTIFACTS))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phantom-training-demo-loop")
    parser.add_argument("--out", required=True, help="directory to write the demo bundle")
    args = parser.parse_args(argv)

    try:
        bundle = write_training_demo_loop(args.out)
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
