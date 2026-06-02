"""phantom-train CLI (Tier 1 stub).

Usage::

    phantom-train --skill rust-coder --base qwen2.5-coder-7b --dry-run
    phantom-train --skill rust-coder --base qwen2.5-coder-7b --recipe examples/rust-coder.toml --commit

Tier 1 behaviour: parse args, load optional recipe, query FTS5 for candidate
training rows, apply the Curator judge stub, and print a structured plan.
No actual training is performed. ``--commit`` is reserved for Tier 2+ and is
rejected with exit code 2 if the Unsloth backend isn't available.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from phantom_training import __version__
from phantom_training.dataset import extract_from_fts5, extract_from_recall
from phantom_training.judge import filter_success_cases

DEFAULT_DB_PATH = Path.home() / ".phantom-mesh" / "memory.db"


def _load_recipe(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        print(f"recipe not found: {path}", file=sys.stderr)
        sys.exit(2)
    # tomllib is stdlib on 3.11+
    import tomllib

    with path.open("rb") as fp:
        return tomllib.load(fp)


def _build_plan(args: argparse.Namespace, rows: list[dict[str, Any]], recipe: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "phantom_training_version": __version__,
        "action": "fine_tune",
        "skill": args.skill,
        "base_model": args.base,
        "backend": recipe.get("backend", "unsloth"),
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
        "dataset": {
            "source": source,
            "db_path": str(args.db),
            "candidate_rows": len(rows),
            "rows_after_curator": sum(1 for _ in filter_success_cases(rows)),
        },
        "eval": {
            "holdout_fraction": recipe.get("holdout_fraction", 0.1),
            "public_benchmarks": recipe.get("benchmarks", ["HumanEval", "MBPP"]),
        },
        "dispatch": {
            "prefer_node": recipe.get("prefer_node", "local-mac"),
            "fallback": recipe.get("fallback_node", "mesh-gpu"),
        },
        "dry_run": bool(args.dry_run),
        "commit": bool(args.commit),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="phantom-train",
        description="Agentic post-training orchestrator on phantom-mesh (Tier 1 stub).",
    )
    p.add_argument("--skill", required=True, help="phantom skill name to (re-)train, e.g. rust-coder")
    p.add_argument("--base", required=True, help="base model id, e.g. qwen2.5-coder-7b")
    p.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"phantom-mesh FTS5 sqlite path (default: {DEFAULT_DB_PATH})",
    )
    p.add_argument("--recipe", type=Path, default=None, help="optional TOML training recipe")
    p.add_argument("--dry-run", action="store_true", help="print plan only, do not train (Tier 1 default)")
    p.add_argument("--commit", action="store_true", help="actually run training (requires Tier 2 backends)")
    p.add_argument("--json", action="store_true", help="emit plan as JSON instead of pretty text")
    p.add_argument("--version", action="version", version=f"phantom-training {__version__}")
    return p


def _emit_pretty(plan: dict[str, Any]) -> None:
    print(f"phantom-training v{plan['phantom_training_version']} — fine-tune plan")
    print(f"  skill       : {plan['skill']}")
    print(f"  base model  : {plan['base_model']}")
    print(f"  backend     : {plan['backend']}")
    print(
        f"  lora        : rank={plan['lora']['rank']} alpha={plan['lora']['alpha']} dropout={plan['lora']['dropout']}"
    )
    opt = plan["optimizer"]
    print(
        f"  optimizer   : lr={opt['lr']} epochs={opt['epochs']} batch={opt['batch_size']} grad_accum={opt['grad_accum']}"
    )
    ds = plan["dataset"]
    print(
        f"  dataset     : {ds['candidate_rows']} candidate -> {ds['rows_after_curator']} after Curator "
        f"(db={ds['db_path']})"
    )
    print(
        f"  eval        : holdout={plan['eval']['holdout_fraction']} benchmarks={','.join(plan['eval']['public_benchmarks'])}"
    )
    print(f"  dispatch    : prefer={plan['dispatch']['prefer_node']} fallback={plan['dispatch']['fallback']}")
    mode = "DRY-RUN (no training)" if plan["dry_run"] or not plan["commit"] else "COMMIT"
    print(f"  mode        : {mode}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    recipe = _load_recipe(args.recipe)
    rows = extract_from_fts5(args.skill, args.db)
    source = f"phantom-mesh memory.db ({args.db})"
    if not rows:
        # memory.db absent/empty → fall back to the real event timeline via recall.
        rows = extract_from_recall(args.skill)
        if rows:
            source = "phantom recall (life-node observations — not instruction pairs)"
    plan = _build_plan(args, rows, recipe, source)

    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        _emit_pretty(plan)

    if args.commit and not args.dry_run:
        # Tier 1: real training backend not wired. Refuse loudly.
        backend = plan["backend"]
        print(
            f"\nERROR: --commit requested but backend '{backend}' is not available in Tier 1.\n"
            "       Install Tier 2 extras: pip install 'phantom-training[unsloth]' and re-run.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
