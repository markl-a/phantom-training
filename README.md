# phantom-training

> **Agentic post-training orchestrator on phantom-mesh**
> The first self-hosted, cross-device, agentic fine-tuning framework.

**Status:** alpha (Tier 1 stub, M3 W11-12 in roadmap)
**License:** Apache-2.0
**Sibling project:** [phantom-mesh](https://github.com/markl-a/phantom-mesh)

## 一句話定位

「Phantom-mesh 上的 AI agent 自己會訓練 AI 模型 — 看你的使用 pattern,自動挑 base model、調 hyperparams、跑 fine-tune、評估迭代,結果回餵成 phantom 的新 skill。」

## Pitch (for hiring managers at NVIDIA / Anthropic / Modal)

The post-training world in 2026 looks like this:

- **Unsloth** ships 12x-faster MoE kernels.
- **Axolotl** owns YAML-driven multi-GPU configs.
- **LaMDAgent** (paper) shows LLM agents can construct post-training pipelines.
- **DSPy** tunes prompts and few-shots, not weights.
- **HuggingFace AutoTrain** is SaaS-only.

**phantom-training** is the missing piece: a **headless, agentic, local-first orchestrator** that sits on top of Unsloth/Axolotl, uses an LLM agent to choose hyperparameters, pulls training data from the user's own `phantom-mesh` FTS5 memory (filtered by the Hermes Curator), runs fine-tunes on whichever node in the mesh has the right GPU, and publishes the resulting LoRA back into `phantom-mesh` as a new skill.

Think `terraform apply` for fine-tuning, where the planner is an agent and the state lives in your phantom mesh.

### Why this is interesting

- **NVIDIA (training infra):** real cross-device dispatch over a heterogeneous mesh (Mac M-series + Windows + Linux + cloud GPU).
- **Anthropic (post-training research):** an open implementation of LaMDAgent-style automated pipeline construction, with traceable Curator decisions.
- **Modal / Together:** a user-friendly entry point that can transparently spill compute onto serverless GPU when local isn't enough.

## How it fits phantom-mesh

```
User: "make phantom's coder agent better at Rust"
   |
phantom-training agent:
   1. Pull Rust sessions from phantom FTS5 memory.db
   2. Filter to success cases via Hermes Curator judge
   3. Build instruction-tuning dataset
   4. Pick base model (Qwen2.5-Coder-7B, CodeLlama-7B, ...)
   5. Pick LoRA rank / lr / batch via agent proposal
   6. Run Unsloth fine-tune on M-series or a mesh GPU node
   7. Eval on holdout + HumanEval / MBPP
   8. If pass, publish as phantom skill "rust-coder-v2"
   9. If fail, agent proposes new hyperparams and retries (LaMDAgent loop)
```

## Tier 1 scope (this commit)

- `phantom-train` CLI with `--skill / --base / --dry-run / --commit`
- FTS5 dataset extractor against `~/.phantom-mesh/memory.db`
- Curator judge stub (interface only)
- Example training recipe in `examples/rust-coder.toml`
- pytest smoke test

No real training yet — Tier 1 prints a structured plan. Real Unsloth wiring lands in M3.

## Spec

Full design lives in [`02-phantom-training.md`](../../215jseeking/docs/projects/02-phantom-training.md) (local).

## Layout

```
phantom_training/
  cli.py         # argparse + dry-run planner
  dataset.py     # FTS5 -> instruction-tuning rows
  judge.py       # Curator filter (stub)
examples/
  rust-coder.toml
tests/
  test_cli.py
docs/
  2026-05-22-tier1-initial-dev.md
```

## Quick start

```bash
python -m phantom_training.cli --skill rust-coder --base qwen2.5-coder-7b --dry-run
```

## Roadmap

- **Tier 1 (now):** CLI + dataset extractor stub
- **Tier 2 (M2):** Unsloth backend, real LoRA fine-tune on Mac M-series
- **Tier 3 (M3 W11-12):** agent-driven hyperparam search, cross-device dispatch via phantom-mesh, public benchmark eval (HumanEval / MBPP), skill publish loop
