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
from phantom_training import eval as eval_mod
from phantom_training import fixtures
from phantom_training.dataset import extract_from_fts5, extract_from_recall, to_instruction_rows
from phantom_training.judge import filter_success_cases

DEFAULT_DB_PATH = Path.home() / ".phantom-mesh" / "memory.db"
SUBCOMMANDS = {"build-dataset", "eval", "seed-fixture"}


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


def _collect_rows(skill: str, db: Path) -> tuple[list[dict[str, Any]], str]:
    """Shared trajectory-collection path used by build-dataset and the planner."""
    rows = extract_from_fts5(skill, db)
    source = f"phantom-mesh memory.db ({db})"
    if not rows:
        rows = extract_from_recall(skill)
        if rows:
            source = "phantom recall (life-node observations — not instruction pairs)"
    return rows, source


def cmd_seed_fixture(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="phantom-train seed-fixture")
    p.add_argument("--db", type=Path, default=DEFAULT_DB_PATH,
                   help=f"path to write the fixture memory.db (default: {DEFAULT_DB_PATH})")
    p.add_argument("--overwrite", action="store_true", help="replace existing rows")
    a = p.parse_args(argv)
    inserted = fixtures.seed_memory_db(a.db, overwrite=a.overwrite)
    if inserted:
        print(f"seeded {inserted} fixture trajectory rows -> {a.db}")
    else:
        print(f"{a.db} already populated (use --overwrite to reseed)")
    return 0


def cmd_build_dataset(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="phantom-train build-dataset")
    p.add_argument("--skill", default="rust-coder", help="phantom skill to build a dataset for")
    p.add_argument("--db", type=Path, default=DEFAULT_DB_PATH,
                   help=f"phantom-mesh memory.db (default: {DEFAULT_DB_PATH})")
    p.add_argument("--out", type=Path, required=True, help="output JSONL path")
    p.add_argument("--seed-if-empty", action="store_true",
                   help="seed a fixture memory.db if no trajectories are found (demo convenience)")
    a = p.parse_args(argv)

    rows, source = _collect_rows(a.skill, a.db)
    if not rows and a.seed_if_empty:
        fixtures.seed_memory_db(a.db)
        rows, source = _collect_rows(a.skill, a.db)
        source += " [seeded fixture]"

    kept = list(filter_success_cases(rows))
    instruction_rows = to_instruction_rows(kept)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as fp:
        for row in instruction_rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        f"build-dataset: skill={a.skill} source={source}\n"
        f"  {len(rows)} candidate -> {len(kept)} after Curator -> "
        f"{len(instruction_rows)} alpaca rows\n"
        f"  wrote {len(instruction_rows)} rows to {a.out}"
    )
    if not instruction_rows:
        print("  (dataset empty: no successful prompt/response pairs; "
              "try --seed-if-empty for a demo fixture)", file=sys.stderr)
    return 0


def cmd_eval(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="phantom-train eval")
    p.add_argument("--dataset", type=Path, required=True, help="alpaca JSONL to evaluate")
    p.add_argument("--holdout-fraction", type=float, default=0.2, help="held-out split fraction")
    p.add_argument("--json", action="store_true", help="emit metrics as JSON")
    a = p.parse_args(argv)

    if not a.dataset.exists():
        print(f"dataset not found: {a.dataset}", file=sys.stderr)
        return 2

    result = eval_mod.evaluate(a.dataset, holdout_fraction=a.holdout_fraction)
    if a.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if "error" not in result else 1

    if "error" in result:
        print(f"eval: {result['error']} (n_rows={result['n_rows']})", file=sys.stderr)
        return 1
    print("phantom-train eval — held-out proxy metric (trivial retrieval baseline)")
    print(f"  rows        : {result['n_rows']} (train={result['n_train']} holdout={result['n_holdout']})")
    print(f"  baseline    : {result['baseline']}")
    print(f"  exact_match : {result['exact_match']}")
    print(f"  token_f1    : {result['token_f1']}")
    print("  NOTE: lightweight proxy floor, not a public benchmark or model eval.")
    return 0


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] in SUBCOMMANDS:
        sub, rest = raw[0], raw[1:]
        if sub == "build-dataset":
            return cmd_build_dataset(rest)
        if sub == "eval":
            return cmd_eval(rest)
        if sub == "seed-fixture":
            return cmd_seed_fixture(rest)

    parser = build_parser()
    args = parser.parse_args(argv)

    recipe = _load_recipe(args.recipe)
    rows, source = _collect_rows(args.skill, args.db)
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
