# phantom-training

[![CI](https://github.com/markl-a/phantom-training/actions/workflows/ci.yml/badge.svg)](https://github.com/markl-a/phantom-training/actions/workflows/ci.yml)

> **Agentic post-training orchestrator on phantom-mesh** — 跨裝置、self-hosted、agent 自動挑 base model + hyperparams + 產生 fine-tune plan(Tier 1;真實 fine-tune 在 Tier 2 接 Unsloth),招聘對齊 NVIDIA / Anthropic / Modal。

![status: alpha · Tier 1](https://img.shields.io/badge/status-alpha%20%C2%B7%20Tier%201-orange)
![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)
[![phantom-mesh ecosystem](https://img.shields.io/badge/ecosystem-phantom--mesh-purple)](https://github.com/markl-a/phantom-mesh)

## 30-second demo

[`docs/demo.cast`](docs/demo.cast) — asciinema recording of the Tier 1 `--dry-run` fine-tune plan.

```sh
# play in a terminal (requires asciinema)
asciinema play docs/demo.cast

# or view the captured text without any tooling:
cat docs/demo.cast | jq -r '.[] | select(.[1]=="o") | .[2]'
```

Self-hosted on purpose — no upload to asciinema.org, no third-party tracking.

## 一句話 niche

The **first headless + agentic + cross-device** post-training orchestrator that
sits on top of Unsloth/Axolotl and runs over a personal device mesh. Unsloth
ships kernels, Axolotl ships YAML, AutoTrain ships SaaS — phantom-training is
the missing piece: a planner that pulls a dataset from your own phantom-mesh
trajectory store and emits a deterministic fine-tune plan today, and (Tier 2+)
hands hyperparam selection to an **LLM agent**, dispatches to whichever mesh
node has the right GPU, and publishes the resulting LoRA back as a phantom
skill.

Think `terraform apply` for fine-tuning, where the state lives in your phantom
mesh. **Honesty note:** Tier 1 is deterministic plumbing — recipe-defaults
merge + a token-overlap eval floor, **not** an LLM agent and **not** real
training. The agentic hyperparam loop and the GPU backend are Tier 2/3 (see
Status).

## Status (2026-06-18)

- ✅ **Tier 1 shipped**: `phantom-train` CLI with a planner
  (`--skill / --base / --recipe / --dry-run / --commit / --json`) plus three
  subcommands — `seed-fixture` (write a demo trajectory DB), `build-dataset`
  (trajectories → Curator filter → alpaca JSONL), and `eval` (a dependency-free
  held-out **proxy** metric: nearest-instruction retrieval scored by
  exact-match / token-F1 — a floor, **not** a public benchmark or model eval).
  Dataset read paths: `phantom recall --json` (the supported live timeline) with
  a SQLite `memory.db` fallback for the Hermes-judged trajectory store (the
  fixture/Tier-2 shape; empty on a fresh machine). Recipes are range-validated.
  Curator judge interface stub, example recipe (`examples/rust-coder.toml`),
  pytest suite. **No real training yet** — `--commit` exits 2 by design.
- 🟡 **Tier 2 next** (M2): Unsloth backend wired, real LoRA fine-tune on Mac
  M-series, eval pipeline (HumanEval / MBPP).
- 🟡 **Tier 3** (M3 W11-12, ~2026-08 target full MVP): agent-driven hyperparam
  search (LaMDAgent-style loop), cross-device dispatch via phantom-mesh, skill
  publish loop.

## 30-second quickstart

```bash
git clone https://github.com/markl-a/phantom-training
cd phantom-training
pip install -e .

# 1. print a deterministic fine-tune plan (no training)
python -m phantom_training.cli --skill rust-coder --base qwen2.5-coder-7b --dry-run

# 2. seed a demo trajectory DB, build an alpaca dataset, and run the eval floor
python -m phantom_training.cli seed-fixture --db /tmp/mem.db
python -m phantom_training.cli build-dataset --skill rust-coder --db /tmp/mem.db --out /tmp/ds.jsonl
python -m phantom_training.cli eval --dataset /tmp/ds.jsonl

pytest -q
```

## Architecture (within phantom-mesh ecosystem)

phantom-training is the **P3 進化網 measure-upgrade** layer of phantom-mesh:
the Hermes 6-step loop (judge → extract → store → recall → apply → measure)
gains a real `measure` arm that turns logged sessions into a new fine-tuned
LoRA, not just a metric row.

```
User: "make phantom's coder agent better at Rust"
   |
phantom-training agent (this repo):
   1. Pull Rust sessions from phantom-mesh FTS5 memory.db
   2. Filter to success cases via Hermes Curator judge
   3. Build instruction-tuning dataset
   4. Pick base model (Qwen2.5-Coder-7B / CodeLlama-7B / ...)
   5. Pick LoRA rank / lr / batch via agent proposal
   6. Dispatch to Mac M-series or a mesh GPU node (via phantom-mesh)
   7. Eval on holdout + HumanEval / MBPP
   8. If pass, publish as phantom skill "rust-coder-v2"
   9. If fail, agent re-proposes (LaMDAgent loop)
```

Pillars served: **P3** (進化網 / self-improving), **P4** (加密為先 — training
data never leaves the mesh, weights encrypted at rest).

## Target users (recruiter / co-builder angle)

- **Recruiters**: hits JD keywords for **NVIDIA training infra**, **Anthropic
  post-training research**, **Modal / Together** (serverless GPU spill),
  **工研院 / 中研院** (academic LaMDAgent-style work). Demonstrates Rust+Python
  systems, agent loops, distributed GPU dispatch, public benchmark eval.
- **Co-builders**: anyone who wants `terraform apply` ergonomics for LoRA
  fine-tuning over a personal-device mesh; fork-friendly Tier 1 surface
  (~300 LOC entry points).

## Roadmap (per master plan)

Full design + competitor matrix + risk register lives at
`docs/02-phantom-training.md` (sanitized copy of internal spec). 3-bullet
version:

1. **M2** — Unsloth backend, real LoRA on M-series, eval pipeline.
2. **M3 W11-12** — agent hyperparam search, cross-device dispatch, skill
   publish loop, 1 end-to-end demo (`phantom train --skill rust-coder`).
3. **Post-M3** — DPO / preference learning, model registry, 9-Agent Landscape
   benchmark auto-runs.

## License

Apache-2.0. © 2026 Mark Lai ([markl-a](https://github.com/markl-a)).
