# phantom-training — Feature Audit (2026-07-03)

> Honest NO-FAKING audit. Verdicts are based on reading function bodies, not docstrings.
> Scope of this repo is deliberately tiered: the project's own SSOT (`docs/phantom-training.md`)
> ships **Tier 1 (deterministic plumbing)** and explicitly marks **Tier 2/3** (real training,
> agentic loop, GPU dispatch) as *vision, not started*. This audit records both so "intended
> vs actual" is fully visible — but it does **not** treat openly-deferred Tier-2/3 vision as a
> broken promise.

## Intended scope (source files)

- `README.md` — Quickstart + Tier-1 vs vision framing.
- `docs/phantom-training.md` — the single main doc: definition (knowledge base + optimization loop),
  locked direction/vision, status roadmap (mermaid), grounded "shipped vs vision" table, Tier S0–S4 plan.
- `pyproject.toml` — 4 console entry points: `phantom-train` (=`cli:main`),
  `phantom-training-demo-loop`, `phantom-training-backend-lifecycle`, `phantom-training-eval-judge-scenario`.
  `cli.py` additionally dispatches 7 subcommands (`build-dataset`, `seed-fixture`, `eval`, `judge`,
  `demo-loop`, `backend-lifecycle`, `eval-judge-scenario`).
- Source package `phantom_training/` (11 modules, stdlib-only): `cli`, `config`, `dataset`, `eval`,
  `fixtures`, `judge`, `hermetic_judge`, `demo_loop`, `backend_lifecycle`, `eval_judge_scenario`, `__init__`.

**MCP tools declared: NONE.** This satellite is **not** an MCP server. There is no `mcp_server.py`,
no `*-mcp` console entry point, no `initialize`/`tools/list` handler anywhere in the tree (grep of the
whole repo excluding `.venv` finds "MCP" only in `PHANTOM-SATELLITES-OPEN-SOURCE-FINAL-SUMMARY.md`, and
there only as the phrase "MCP-style tool call invocation" describing that AI agents can shell out to the
**CLI** — not that a server exists). The intended feature set is therefore
**(documented Tier-1 capabilities) ∪ (CLI subcommands) ∪ (documented Tier-2/3 vision)**, with no MCP surface.

## Feature matrix

| Feature | Intended-from | Status | Evidence file:line | Notes |
|---|---|---|---|---|
| Planner CLI: recipe-merge → structured fine-tune plan; `--commit` refuses (exit 2) | README, doc "shipped", pyproject `phantom-train` | ✅ DONE | `cli.py:72` (`_build_plan`), `cli.py:348-389` (`main`), `cli.py:379-387` (commit→exit 2) | Real dict build; tested by `test_cli.py`, `test_cli_outputs.py`, `test_cli_validation.py` |
| Recipe validation (range checks, never crashes) | doc "recipe 驗證" | ✅ DONE | `config.py:50-106` (`validate_recipe`) | Real per-key range checks; `test_config.py` |
| `seed-fixture`: write real-shaped `memory.db` | README, doc "shipped" | ✅ DONE | `fixtures.py:131-158` (`seed_memory_db`), `cli.py:166-177` | Real SQLite writes, 11 genuine seed rows incl. deliberate fails; idempotent |
| `build-dataset`: trajectory → Curator filter → alpaca JSONL + dedupe | README, doc "shipped" | ✅ DONE | `cli.py:210-246`; `dataset.py:78` (`extract_from_fts5`), `:206` (`to_instruction_rows`), `:225` (`dedupe_instruction_rows`); `judge.py:52` (`filter_success_cases`) | Real sqlite read w/ 3-query fallback; alpaca rows; `test_to_instruction_rows.py`, `test_dataset_fallbacks.py` |
| Live source path: `phantom recall --json` → rows (memory.db fallback) | doc moat #1 | ✅ DONE | `dataset.py:127-174` (`extract_from_recall`) | Real subprocess to `phantom`; degrades to `[]` if binary absent; `test_dataset_recall.py` |
| Eval floor: deterministic held-out split + token-overlap retrieval (EM + token-F1) | README, doc "shipped" | ✅ DONE | `eval.py:116-165` (`evaluate`), `:106` (`_retrieve`), `:84` (`_token_f1`) | Real computed metric; corrupt/short JSONL reported cleanly not crashed; `test_eval_robustness.py`, `test_eval_retrieval.py` |
| Hermetic judge: sandbox subprocess unit-test pass-rate (code) + normalized match (QA) | README, doc "shipped" moat #2 | ✅ DONE | `hermetic_judge.py:21-78` (`score_code`, real subprocess), `:95-99` (`score_qa`), `:106-125` (`judge_task`) | Genuinely spawns `sys.executable` runner in temp dir; `test_hermetic_judge.py`, `test_judge_real.py` |
| `judge` CLI + `is_success` wiring into Curator | doc "shipped" | ✅ DONE | `cli.py:284-345`; `judge.py:29-49` (`is_success` calls hermetic when tests/reference present) | Real wiring; `test_cli_judge.py` |
| P2 `demo-loop` deterministic artifact bundle | README, pyproject | ✅ DONE | `demo_loop.py:181-233` (`write_training_demo_loop`) | Real 8-artifact bundle from live fixture→eval→judge; `test_demo_loop_contract.py` |
| P2 `backend-lifecycle` validation bundle | README, pyproject | ✅ DONE | `backend_lifecycle.py:248-280` | Validates card/manifest/adapter contracts + leak-marker list; `test_backend_lifecycle_contract.py`, `test_backend_lifecycle_validation.py` |
| P3 `eval-judge-scenario` reporting bundle | README, pyproject, `docs/EVAL_JUDGE_SCENARIO.md` | ✅ DONE | `eval_judge_scenario.py:34-94` | Composes the two bundles into eval/judge/repro/release-gate reports; `test_eval_judge_scenario_contract.py` |
| Packaging / entry points / OSS contract / CI | pyproject, doc "shipped" | ✅ DONE | `pyproject.toml:51-55`; `tests/test_packaging.py`, `test_open_source_contract.py`, `test_release_prep_contract.py` | 4 scripts declared; contract tests green |
| **Knowledge base** (structured, growing recipe repository the agent draws from) | doc "這是什麼" / core definition | 🟡 PARTIAL | `examples/rust-coder.toml` + `config.py:50` validation only | Only ONE example recipe + a validator; no repository, no accumulation, no auto-select. Doc itself says this is Tier-2/3 |
| Plan `dispatch` / `public_benchmarks` fields | `cli.py:96-103` plan output | 🟡 STUB | `cli.py:96-103` (static strings `prefer_node`, benchmarks `["HumanEval","MBPP"]`) | Emitted as plan metadata only; no dispatch and no benchmark is actually run |
| **Real training backend** (Unsloth/Axolotl) via `--commit` | doc vision, pyproject optional-extras | ❌ MISSING (Tier 2, by design) | `cli.py:379-387` refuses with exit 2; extras `unsloth`/`axolotl` declared but never imported/used | No `Backend.train()` seam exists yet |
| Real Hermes Curator HTTP call (replace heuristic) | doc moat #2 "Tier-2 規劃" | ❌ MISSING (Tier 2) | `judge.py:29-49` is heuristic + hermetic only; no HTTP client anywhere | — |
| Agent auto-select recipe from KB + optimization/re-propose loop (LaMDAgent/DSPy) | doc "優化循環" vision | ❌ MISSING (Tier 3) | no module; no agent loop in tree | — |
| Cross-device governed GPU dispatch (governor + flight-recorder) | doc moat #3 vision | ❌ MISSING (Tier 3) | only static `dispatch` strings in plan (`cli.py:100-103`) | — |
| Public benchmark eval (HumanEval/MBPP via bigcode-eval) | doc vision | ❌ MISSING (Tier 2) | benchmarks are string labels only; `eval.py` is a proxy floor | — |
| skill-publish loop back into phantom-mesh | doc vision | ❌ MISSING (Tier 3) | no publish code | — |
| DPO/preference (TRL) + model registry | doc "遠期 Post-M3" | ❌ MISSING (Post-M3) | none | — |
| MCP server / declared MCP tools | orchestrator premise ("registered as MCP server") | ❌ MISSING / N/A | no `mcp_server` module, no `*-mcp` entry point, no `initialize`/`tools/list` handler | This repo was never an MCP server; it is a stdlib CLI |

## MCP server operability

- **`.venv/` exists:** yes — `.venv\Scripts\python.exe` = CPython 3.11.9.
- **MCP entrypoint module exists / imports:** **No MCP entrypoint exists.** There is nothing to start
  as an MCP server. The 4 console scripts are plain CLIs, and the package imports cleanly
  (`python -c "import phantom_training, phantom_training.cli, phantom_training.hermetic_judge"` → `import OK 0.1.0a0`).
- **Would an MCP server hang at `initialize`/`tools/list`?** Not applicable — there is no server to hang.
  The "known MCP-startup hang" seen in sibling satellites **cannot occur here** because this project
  exposes no MCP surface at all. If the orchestrator's mesh config lists a `phantom-training` MCP server,
  that config is pointing at a command that does not exist in this repo (the likely real cause of any
  "startup hang/timeout" attributed to this satellite: the launcher waits on a server that never speaks).
- **CLI operability:** confirmed working — `python -m phantom_training.cli --skill rust-coder --base qwen2.5-coder-7b --dry-run`
  prints a valid plan and exits 0. No top-level blocking code; all heavy submodules are imported lazily inside subcommands.

## Test result

- Command: `.venv\Scripts\python -m pytest -q` (Python 3.11.9).
- **180 tests collected, all passed, 0 failed / 0 error** (~61s wall). 21 test files.
- Coverage spans every shipped feature: planner/validation, dataset extraction + fallbacks + recall,
  eval robustness/retrieval, hermetic judge (real subprocess), all three P2/P3 bundles, packaging &
  open-source contract.

## Summary

**12 done / 0 untested / 2 partial / 8 missing of 22 total (≈59% of full documented vision).**

Two honest framings, because this project deliberately tiers its scope:
- **Declared *shipped* scope (Tier 1):** 12 / 12 features are real **and** tested → **100% real**.
  The plumbing is genuine (real SQLite, real subprocess sandbox judge, real computed eval metric,
  real deterministic bundles) — not fake/placeholder. No faking detected.
- **Full product vision (Tier 1 + Tier 2/3):** ≈59% realized. The 2 partial + 8 missing items are
  the orchestration/real-training half of the product (knowledge base that grows, agent proposal loop,
  Unsloth backend, Hermes HTTP, GPU dispatch, skill-publish, DPO/registry) — all of which the project's
  own SSOT openly marks "尚未開工 / not started", so they are deferred-by-design, not silently dropped.
- The **MCP server** the orchestrator expected does not exist here (this satellite is a CLI).

## Top gaps to close

1. **No MCP server exists** — if the mesh expects `phantom-training` to answer MCP `initialize`/`tools/list`,
   that expectation is unmet and is the probable root cause of any startup hang/timeout blamed on this
   satellite. Either (a) add a thin MCP wrapper module exposing the CLI subcommands as tools, or
   (b) remove/point the mesh config away from a non-existent server. (Highest-leverage fix.)
2. **The core product promise ("knowledge base + optimization loop") is only plumbing.** The two things
   that make it more than a dataset/eval CLI — an accumulating recipe **knowledge base** and an **agent
   optimization loop** — are 🟡 stub / ❌ missing. The nearest real Tier-2 step per the roadmap is the
   `Backend.train(plan, dataset) -> adapter_path` seam + PEFT `LoraConfig`-shaped plan schema (still no GPU),
   which would turn `--commit` from "exit 2" into an actual (opt-in) path.

*(Tier-2/3 items are correctly labelled vision in `docs/phantom-training.md`; closing them is roadmap work,
not remediation of a false "done" claim. This audit found no fake/placeholder passing as shipped.)*
