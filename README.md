# phantom-training

[![CI](https://github.com/markl-a/phantom-training/actions/workflows/ci.yml/badge.svg)](https://github.com/markl-a/phantom-training/actions/workflows/ci.yml)

> **An agentic post-training _data_ pipeline for phantom-mesh** — curate agent
> trajectories into an instruction-tuning dataset, score it on a held-out
> split, and emit a LoRA fine-tune **plan** (the `terraform plan` for
> fine-tuning). It does **not** train models yet — the training backend is
> scaffold and `--commit` exits with code 2.

![status: alpha · data pipeline + fine-tune plan](https://img.shields.io/badge/status-alpha%20%C2%B7%20data%20pipeline%20%2B%20plan-orange)
![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)
[![phantom-mesh ecosystem](https://img.shields.io/badge/ecosystem-phantom--mesh-purple)](https://github.com/markl-a/phantom-mesh)

## What this is (and is not)

This repo is the **data + planning** half of a fine-tuning loop:

1. **Curate** — pull `(skill, prompt, response)` trajectory rows from a
   phantom-mesh SQLite store (`memory.db`), or from a synthetic seed fixture
   when no store exists yet.
2. **Filter** — drop unsuccessful rows with a Curator judge. Today the judge is
   a **heuristic** (`judged_success == 1` and `hermes_score >= 0.6`), not an LLM
   call — `judge.py` is the seam where a real Hermes Curator plugs in later.
3. **Build** — emit an alpaca-style instruction-tuning dataset (`{instruction,
   input, output}` JSONL) that Unsloth / TRL / Axolotl can consume.
4. **Eval** — score the dataset on a deterministic **held-out split** using a
   trivial nearest-instruction retrieval baseline (`exact_match`, `token_f1`).
   This is a lightweight proxy floor, **not** a public benchmark and **not** a
   model evaluation — no GPU, no model download.
5. **Plan** — emit a structured LoRA fine-tune **plan** (base model, LoRA
   rank/alpha, optimizer, dataset counts, intended eval/dispatch). This is the
   `terraform plan`: a description of what a fine-tune _would_ do.

It is **not** (yet):

- It does **not** fine-tune or train any model. The training backend
  (Unsloth/Axolotl) is unimplemented; `--commit` prints an error and **exits
  with code 2**.
- The hyperparameters are **read from a TOML recipe with static defaults** —
  there is no agent or LLM that "picks" them. The agent-driven hyperparam
  search is on the roadmap, not in this code.
- The eval is a retrieval baseline over the dataset text, **not** HumanEval /
  MBPP and **not** a trained-model score.

## 30-second demo: the working seed → build → eval path

The end-to-end path that actually runs today produces a real dataset and a
real (proxy) metric from synthetic seed data — no GPU, no network:

```bash
git clone https://github.com/markl-a/phantom-training
cd phantom-training
pip install -e .

# 1. seed a synthetic trajectory store (real-shaped coding Q->A pairs, no PII)
python -m phantom_training.cli seed-fixture --db /tmp/demo-memory.db

# 2. curate + filter -> alpaca-style instruction JSONL
python -m phantom_training.cli build-dataset \
    --skill rust-coder --db /tmp/demo-memory.db --out /tmp/demo.jsonl

# 3. score the dataset on a held-out split (proxy retrieval baseline)
python -m phantom_training.cli eval --dataset /tmp/demo.jsonl

# (optional) emit the LoRA fine-tune *plan* (terraform-plan; no training)
python -m phantom_training.cli \
    --skill rust-coder --base qwen2.5-coder-7b \
    --recipe examples/rust-coder.toml --dry-run

pytest -v
```

`build-dataset` filters the synthetic seed (9 candidate rows for `rust-coder`)
down to 8 after the judge drops the deliberately-failed rows, then `eval`
reports an honest held-out `token_f1` over that JSONL.

There is also an asciinema recording of the **plan** step (`--dry-run`) at
[`docs/demo.cast`](docs/demo.cast):

```sh
asciinema play docs/demo.cast                 # requires asciinema

# or view the captured output without any tooling (asciinema v3 = JSON lines):
jq -rR 'fromjson? | select(type=="array" and .[1]=="o") | .[2]' docs/demo.cast
```

Self-hosted on purpose — no upload to asciinema.org, no third-party tracking.

## Niche

A post-training **data** pipeline that sources its training set from your own
phantom-mesh agent trajectories instead of a public dataset. Unsloth ships
kernels, Axolotl ships YAML, AutoTrain ships SaaS — none of them curate _your
mesh's_ logged agent sessions into a dataset and tell you what a fine-tune
would cost before you run it.

The intended end state is `terraform`-style ergonomics for fine-tuning:
`plan` today (implemented), `apply` later (the training backend, on the
roadmap). The state lives in your phantom mesh.

## Status (2026-06-14)

Implemented and tested today:

- ✅ `phantom-train` CLI with subcommands `seed-fixture`, `build-dataset`,
  `eval`, plus the top-level plan emitter (`--dry-run` / `--json`).
- ✅ Trajectory extractor (`dataset.py`) against a phantom-mesh `memory.db`
  with a three-tier query fallback (primary → FTS5 → minimal), read-only
  SQLite, and a `phantom recall` fallback path. Returns `[]` (never crashes)
  on a missing/empty store.
- ✅ Heuristic Curator judge (`judge.py`) — the plug-in seam for a real
  Hermes Curator.
- ✅ Synthetic seed fixture (`fixtures.py`) of real-shaped coding Q→A pairs so
  the demo runs with zero external state.
- ✅ Held-out proxy eval (`eval.py`) — deterministic split, `exact_match` /
  `token_f1` retrieval baseline.
- ✅ Example LoRA recipe (`examples/rust-coder.toml`) and 16 passing pytest
  cases.

Not implemented (scaffold / roadmap):

- 🚧 Real training backend (Unsloth/Axolotl). `--commit` **exits 2**; there is
  no weight update anywhere in this repo.
- 🚧 Real LLM Curator judge (currently a heuristic).
- 🚧 Real public-benchmark eval (HumanEval / MBPP) and trained-model scoring.
- 🚧 Agent-driven hyperparam search and cross-device GPU dispatch.

## Architecture (roadmap vs. today)

phantom-training is intended as the `measure` arm of phantom-mesh's evolution
loop. The **bold** steps below run today; the rest are roadmap:

```
User: "build a fine-tune dataset for phantom's rust-coder skill"
   |
phantom-training (this repo):
   1. **Pull rust-coder trajectories from a memory.db SQLite store**   [today]
   2. **Filter to success cases via the (heuristic) Curator judge**    [today]
   3. **Build an alpaca-style instruction-tuning dataset (JSONL)**     [today]
   4. **Score it on a held-out split (proxy retrieval baseline)**      [today]
   5. **Emit a LoRA fine-tune plan from a TOML recipe (no agent)**     [today]
   6.   Pick base model / LoRA hyperparams via an agent proposal       [roadmap]
   7.   Dispatch to a Mac M-series or mesh GPU node                    [roadmap]
   8.   Real fine-tune + eval on HumanEval / MBPP                      [roadmap]
   9.   Publish the adapter as a phantom skill; re-propose on failure  [roadmap]
```

Privacy intent: training data is sourced from a local store and is never
uploaded by this pipeline. (Encrypted-at-rest weights belong to the unbuilt
training backend, not this repo.)

## Target users

- **Co-builders**: anyone who wants a self-hosted way to turn logged agent
  sessions into an instruction-tuning dataset + a held-out sanity metric,
  before committing GPU time. The Tier-1 surface is small and fork-friendly
  (~600 LOC, stdlib-only).
- **Recruiters / portfolio**: demonstrates a data-curation + eval pipeline,
  clean CLI design, and honest scope boundaries (the training loop is
  explicitly marked as scaffold). The agent loop, GPU dispatch, and
  public-benchmark eval are roadmap items, not claims about this code.

## Roadmap

Design notes, competitor matrix, and the longer plan live in
`docs/02-phantom-training.md` and `docs/2026-05-22-tier1-initial-dev.md`.
Short version:

1. **Training backend** — wire Unsloth/TRL so `--commit` actually produces a
   LoRA adapter (today it exits 2).
2. **Real judge + eval** — replace the heuristic judge with a Hermes Curator
   call; replace the proxy metric with HumanEval / MBPP.
3. **Agentic loop** — agent-proposed hyperparams, cross-device GPU dispatch,
   and a skill-publish step.

## License

Apache-2.0. © 2026 Mark Lai ([markl-a](https://github.com/markl-a)).
