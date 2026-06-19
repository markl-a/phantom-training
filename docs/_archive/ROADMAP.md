> ARCHIVED 2026-06-19 — 內容已併入 docs/phantom-training.md;此為歷史版本。

# Roadmap

> **This file is the single source of truth for project status.**
> README and other docs must link here rather than restate status.
> Last updated: 2026-06-19.

phantom-training is the **P3 進化網 measure-upgrade** layer of phantom-mesh: an
agentic post-training orchestrator that turns logged agent trajectories into a
fine-tune plan (today) and, eventually, a real fine-tuned LoRA published back as
a phantom skill. See [`DESIGN.md`](DESIGN.md) for the design spec and
[`docs/02-phantom-training.md`](docs/02-phantom-training.md) for the full
competitor matrix and master-plan tiering.

The work is staged in three tiers. **Tier 1 is deterministic plumbing** —
recipe-defaults merge plus a token-overlap eval floor and a hermetic judge, **not**
an LLM agent and **not** real training.

## Shipped

Tier 1 is shipped. The `phantom-train` CLI and its supporting modules are in
place, hermetic, and covered by a passing pytest suite (~128 tests collected as of
the latest merge `7b60fc0`, ruff-clean).

- **`phantom-train` planner** — top-level argparse CLI
  (`--skill / --base / --recipe / --dry-run / --commit / --json`) that merges
  recipe defaults and prints a structured deterministic fine-tune plan. `--commit`
  exits 2 by design (no training backend wired). (`de9924a`, `f139276`)
- **`seed-fixture` subcommand** — writes a demo trajectory SQLite DB so the rest
  of the loop is runnable on a fresh machine. (`d16b09e`)
- **`build-dataset` subcommand** — trajectories → Curator filter → alpaca-style
  instruction JSONL, with alpaca-row de-duplication. Read paths: `phantom recall
  --json` (the supported live timeline) with a SQLite `memory.db` fallback for the
  fixture / Tier-2 Hermes-judged trajectory store. (`21b8dc0`, `d16b09e`, `5402eb0`)
- **`eval` subcommand** — dependency-free held-out **proxy** metric: deterministic
  train/held-out split, nearest-instruction retrieval baseline scored by
  exact-match and token-F1. A floor, not a public benchmark or model eval.
  Malformed-JSONL lines report cleanly instead of crashing. (`d16b09e`, `0a15dd3`,
  `4499d0f`)
- **`judge` subcommand + real hermetic judge** (`hermetic_judge.py`) — code
  candidates scored by sandboxed-subprocess unit-test pass-rate; QA by normalized
  match. Wired into `is_success` (curator accept). Rows without ground truth keep
  the permissive Tier-1 column-check fallback (additive). No model inference or
  GPU. (`ab991e5`, `7b60fc0`)
- **Recipe validation** (`config.py`) — range-validated training recipes; bad
  holdout fractions rejected. Shipped example recipe (`examples/rust-coder.toml`).
  (`fa1f40b`, `1a0f42b`)
- **Hermetic test suite** — the full suite passes regardless of `PATH` (conftest +
  child-subprocess PATH isolation); `--dry-run` locked as a safety override of
  `--commit`. (`b059536`, `9e38223`, `5775374`)
- **CI** — GitHub Actions pytest workflow on push / PR (`.github/workflows/ci.yml`),
  Python 3.11, `pip install -e ".[dev]"` then `pytest`. (`ade6603`)
- **Self-hosted demo** — `docs/demo.cast` asciinema recording of the Tier-1
  `--dry-run` plan (no upload to asciinema.org). (`0d249bd`)

## In progress

Nothing is actively in progress. Tier 1 has reached its "final form" merge
(`b059536`) plus the real hermetic judge follow-up (`7b60fc0`). The next work is
Tier 2 (see below) and is not yet started.

## Planned next

### Tier 2 (M2) — real training backend

- **Unsloth backend** (`phantom_training/backends/unsloth_backend.py`) —
  `train(plan, dataset)` building a `peft.LoraConfig` from the plan and running
  `SFTTrainer`; write a LoRA adapter to `~/.phantom-training/adapters/<skill>-<sha>/`.
- **Real Hermes Curator call** — replace the heuristic with an HTTP call into
  `phantom-mesh serve`'s curator/judge endpoint.
- **Real eval harness** — wrap `bigcode-evaluation-harness` for HumanEval / MBPP
  so the publish gate has teeth.
- Real LoRA fine-tune on a Mac M-series target.

### Tier 3 (M3 W11-12, ~2026-08 full-MVP target)

- **Agent-driven hyperparam search** — a small DSPy/LaMDAgent-style loop that
  re-proposes `lora_rank / lr / epochs` when eval misses `pass_threshold` and
  re-invokes the CLI.
- **Cross-device dispatch** via phantom-mesh (`prefer_node` / `fallback_node` map
  1:1 to the mesh capability dispatcher).
- **Skill publish loop** — POST adapter + eval scores to phantom-mesh
  `/skills/publish`; one end-to-end demo (`phantom train --skill rust-coder`).

### Post-M3

- DPO / preference learning, model registry + version control, 9-Agent Landscape
  benchmark auto-runs.

## Honesty notes

- Tier 1 produces a fine-tune **plan**; real fine-tune is Tier 2 (Unsloth not yet
  wired). `--commit` exits 2 by design.
- The `eval` number is a deliberate **floor** from a trivial retriever — not a
  public benchmark.
- `events.sqlite` / `fts5_events` is dead scaffolding; the supported live read path
  is `phantom recall --json` with a `memory.db` fixture fallback (see
  `dataset.py` docstring and [`DESIGN.md`](DESIGN.md) §3).
