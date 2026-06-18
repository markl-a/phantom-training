> ARCHIVED 2026-06-19 — frozen historical snapshot; current status lives in /ROADMAP.md

# 2026-05-22 — phantom-training Tier 1 initial dev

## What's in this commit (alpha scaffold, ~600 LOC)

- `README.md` — pitch (NVIDIA / Anthropic / Modal narrative), 一句話 niche, status, links
- `LICENSE` — Apache-2.0
- `.gitignore` — Python + ML artifacts (`*.bin`, `*.safetensors`, checkpoints, dataset cache)
- `pyproject.toml` — Python 3.11+, no runtime deps in Tier 1 (stdlib only),
  `transformers / peft / datasets / accelerate` declared as optional `[unsloth]` /
  `[axolotl]` extras for Tier 2+
- `phantom_training/`
  - `__init__.py` — version pin
  - `cli.py` — `phantom-train` argparse CLI: `--skill / --base / --recipe / --dry-run / --commit / --json`
  - `dataset.py` — `extract_from_fts5(skill_name, db_path)` against `~/.phantom-mesh/memory.db`
    with three-tier query fallback (primary -> FTS5 -> minimal), read-only SQLite URI,
    plus `to_instruction_rows()` for alpaca-style schema
  - `judge.py` — Curator-style `is_success` / `filter_success_cases` interface,
    Tier-1 permissive heuristic
- `examples/rust-coder.toml` — full LoRA recipe (rank/alpha/lr/epochs, target_modules,
  benchmarks, mesh dispatch preference, publish skill name)
- `tests/test_cli.py` — 11 pytest cases covering: --help, dry-run, JSON output, recipe
  override, commit-without-backend error, FTS5 extraction with seeded SQLite, judge
  thresholds, subprocess `python -m phantom_training.cli` smoke
- `docs/2026-05-22-tier1-initial-dev.md` — this file

## Tier 1 MVP scope (per spec M3 W11-12)

This commit ships the **plumbing and contracts**, not the training itself. The CLI
parses every flag the real tool will need, the dataset extractor talks to the real
phantom-mesh schema with sensible fallbacks, and the judge module exposes the exact
seam where a Hermes Curator call will plug in.

`--commit` deliberately exits 2 with a "Tier 1: no backend wired" error, so anyone
following the README's quick-start can't accidentally believe training happened.

## What this unblocks

- **2-3 months of FTS5 accumulation**: phantom-mesh sessions starting now feed
  directly into the dataset extractor. By M3 W11-12 there should be enough
  Hermes-judged success cases per skill to actually fine-tune.
- **Recipe surface area is locked**: contributors can write `examples/*.toml` for
  other skills (sql-expert, health-coach, ...) without waiting on the backend.
- **Cross-device dispatch contract**: `prefer_node` / `fallback_node` in the
  recipe maps 1:1 to the phantom-mesh capability dispatcher already shipping in
  phantom-mesh's `mesh::dispatcher`.

## What real dev needs next (Tier 2, M2)

The biggest single piece is wiring Unsloth. Concretely:

1. **`phantom_training/backends/unsloth_backend.py`** — implement
   `train(plan, dataset)` that calls `FastLanguageModel.from_pretrained`,
   builds a `peft.LoraConfig` from `plan["lora"]`, runs `SFTTrainer` from
   TRL, and writes a LoRA adapter to `~/.phantom-training/adapters/<skill>-<sha>/`.
2. **Real Hermes Curator call in `judge.py`** — replace the heuristic with an
   HTTP call to `phantom-mesh serve`'s `/curator/judge` endpoint (it already
   exists for the memory-store path; we just reuse it).
3. **Eval harness `phantom_training/eval.py`** — wrap `bigcode-evaluation-harness`
   for HumanEval/MBPP so the publish gate has teeth.
4. **Skill publish** — POST to phantom-mesh's `/skills/publish` with the adapter
   path + eval scores; phantom-mesh then registers it as a new skill version.
5. **Agentic hyperparam loop** — small DSPy program that proposes a new
   `lora_rank / lr / epochs` triple when eval misses `pass_threshold`, then
   re-invokes the CLI in a subprocess (the LaMDAgent kernel).

Estimated Tier 2 size: ~1,200 LOC + Unsloth dep. Single-Mac M-series train of
a 4-7B model in QLoRA is feasible in 4-6 hours per epoch on this hardware.
