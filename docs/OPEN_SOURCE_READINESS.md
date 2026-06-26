# Open Source Readiness

Project: `phantom-training`
Current phase: P3 deterministic eval/judge pipeline scenario verified
Master plan: `../../PHANTOM-SATELLITES-OPEN-SOURCE-MASTER-PLAN.md`

## Shipped Features

- Deterministic Tier 1 training-planning plumbing.
- CLI entrypoint: `phantom-train = phantom_training.cli:main`.
- CLI entrypoint: `phantom-training-demo-loop = phantom_training.demo_loop:main`.
- CLI entrypoint: `phantom-training-backend-lifecycle = phantom_training.backend_lifecycle:main`.
- CLI entrypoint: `phantom-training-eval-judge-scenario = phantom_training.eval_judge_scenario:main`.
- Help surface verified with `python -m phantom_training.cli --help`.
- README explicitly says Tier 1 is deterministic pipeline work, not a real LLM agent and not real training.
- README now contains a source-checkout Quickstart for the public Tier 1 demo.
- Public demo and artifact policy documented in `docs/PUBLIC_DEMO.md`.
- Deterministic public smoke covers plan -> seed-fixture -> build-dataset -> eval -> judge.
- P2 `demo-loop` writes a deterministic bundle with `dataset-card.json`, `run-manifest.json`, `backend-adapter-contract.json`, `eval.json`, `judge.json`, and `summary.md`.
- P2 `backend-lifecycle` writes a deterministic validation bundle with `backend-lifecycle.json`, `dataset-card-validation.json`, `run-manifest-validation.json`, metadata-only `audit-log.jsonl`, and `summary.md`.
- P3 `eval-judge-scenario` writes a deterministic report bundle with `eval-report.json`, `judge-report.json`, `reproducibility-report.json`, `release-gate.json`, `audit-summary.json`, and `summary.md`.
- `--commit` safety boundary is documented and exits 2 when Tier 1 has no real backend.
- Test suite baseline: `python -m pytest -q` exited 0.
- Collect-only baseline after P2: 136 tests collected.

## Planned Or Deferred Features

- Broader model improvement pipeline: dataset cards, run manifests, backend adapter contract, reproducible eval reports.
- Real Unsloth/Axolotl training backends are deferred Tier 2/3 work.
- Automatic benchmark publishing and private model artifact publishing are out of initial release scope.

## Install And Test Commands

```powershell
python -m pip install -e .[dev]
python -m pytest -q
python -m pytest --collect-only -q
python -m phantom_training.cli --help
python -m phantom_training.cli demo-loop --out <bundle-dir>
python -m phantom_training.cli backend-lifecycle --out <bundle-dir>
python -m phantom_training.cli eval-judge-scenario --out <bundle-dir>
```

Observed P0 result on 2026-06-26:

```text
python -m pytest -q: exit 0
python -m pytest --collect-only -q: 130 tests collected
python -m pytest tests/test_open_source_contract.py tests/test_cli.py tests/test_cli_outputs.py tests/test_cli_judge.py tests/test_packaging.py -q: exit 0
```

P2 deterministic training-planning result:

```text
Targeted: 40 passed
Full: python -m pytest -q exited 0
Collect-only: 136 tests collected
CLI smoke: python -m phantom_training.cli demo-loop --out <temp> wrote manifest.json
```

P2 backend lifecycle result:

```text
Targeted: python -m pytest tests/test_backend_lifecycle_contract.py tests/test_demo_loop_contract.py tests/test_open_source_contract.py tests/test_packaging.py tests/test_cli.py tests/test_cli_outputs.py tests/test_cli_judge.py tests/test_eval_robustness.py -q exited 0
Full: python -m pytest -q exited 0
Collect-only: 142 tests collected
Packaging: python -m pip install -e . --dry-run --no-deps would install phantom-training-0.1.0a0
CLI smoke: python -m phantom_training.cli backend-lifecycle --out <temp> wrote manifest.json
```

P3 deterministic eval/judge scenario result:

```text
Targeted: 58 passed
Full: python -m pytest -q exited 0
Collect-only: 147 tests collected
CLI smoke: python -m phantom_training.cli eval-judge-scenario --out <temp> wrote manifest.json
Agy review: NO BLOCKERS
```

## Fixture And Data Policy

- Public fixtures must be synthetic and reproducible.
- No private datasets, private prompts, private traces, or model artifacts may be committed.
- Dataset JSONL schema, eval result schema, and judge rubric must remain documented as public interfaces.
- Dataset card, run manifest, and backend adapter contract must state that Tier 1 writes no model artifacts and performs no real training.
- Backend lifecycle validation artifacts must not retain dataset row bodies, prompts, outputs, private credentials, model weights, or publish tokens.
- Eval/judge scenario audit summaries must remain metadata-only and must not retain dataset rows, prompt text, outputs, model artifacts, private credentials, or publish tokens.

## Safety And Privacy Risks

- The project name can imply real training; docs must continue to distinguish deterministic plumbing from real training.
- `--commit` or publish-like behavior must remain disabled, gated, or documented as requiring real backend setup.
- Any future backend adapter must avoid uploading private data by default.

## Blockers To Next Phase

- None for P3 deterministic eval/judge scenario. Next slice should harden optional benchmark adapters or backend roadmap documentation without enabling real training by default.

## Evidence

- `pyproject.toml` declares package `phantom-training` and scripts `phantom-train`, `phantom-training-demo-loop`, `phantom-training-backend-lifecycle`, and `phantom-training-eval-judge-scenario`.
- `README.md` points to `docs/phantom-training.md` and states Tier 1 is not real training.
- `README.md` and `docs/PUBLIC_DEMO.md` document the public demo, P2 artifact bundle, backend lifecycle bundle, P3 eval/judge scenario, and artifact policy.
- `docs/EVAL_JUDGE_SCENARIO.md` documents the P3 scenario artifact contract and Tier 1 safety boundary.
- Public smoke on 2026-06-26:
  - dry-run plan JSON used `examples/rust-coder.toml` and reported backend `unsloth`, `dry_run=true`, LoRA rank 32.
  - `seed-fixture` wrote 11 synthetic fixture trajectory rows.
  - `build-dataset` converted 9 candidate rows into 8 Alpaca rows after Curator filtering.
  - `eval --json` returned `n_rows=8`, `n_train=6`, `n_holdout=2`, `token_f1=0.2353`, `exact_match=0.0`.
  - `judge --json` accepted the synthetic QA task.
  - `--commit` without Tier 2 backend exited 2 by design.
- `python -m pytest -q`: exit 0.
- `python -m pytest --collect-only -q`: 136 tests collected.
- `python -m phantom_training.cli --help`: help OK.
- `python -m pytest tests/test_demo_loop_contract.py tests/test_packaging.py tests/test_open_source_contract.py tests/test_cli.py tests/test_cli_outputs.py tests/test_cli_judge.py -q`: 40 passed.
- `python -m phantom_training.cli demo-loop --out <temp>`: wrote schema version 1 manifest with `synthetic_only=true`, `real_training=false`, `model_artifacts_written=false`, `external_network=false`, and `gpu_required=false`.
- P2 backend lifecycle targeted `python -m pytest tests/test_backend_lifecycle_contract.py tests/test_demo_loop_contract.py tests/test_open_source_contract.py tests/test_packaging.py tests/test_cli.py tests/test_cli_outputs.py tests/test_cli_judge.py tests/test_eval_robustness.py -q`: exit 0.
- P2 backend lifecycle final `python -m pytest -q`: exit 0.
- P2 backend lifecycle collect-only `python -m pytest --collect-only -q`: 142 tests collected.
- P2 backend lifecycle packaging `python -m pip install -e . --dry-run --no-deps`: would install `phantom-training-0.1.0a0`.
- `python -m phantom_training.backend_lifecycle --help`: help OK.
- `python -m phantom_training.cli backend-lifecycle --out <temp>`: wrote schema version 1 manifest with `synthetic_only=true`, `real_training=false`, `model_artifacts_written=false`, `external_network=false`, `gpu_required=false`, `publish_enabled=false`, and `selected_stage=tier1_disabled`.
- P3 eval/judge scenario targeted `python -m pytest tests/test_eval_judge_scenario_contract.py tests/test_open_source_contract.py tests/test_backend_lifecycle_contract.py tests/test_demo_loop_contract.py tests/test_packaging.py tests/test_cli.py tests/test_cli_outputs.py tests/test_cli_judge.py tests/test_eval_robustness.py -q`: 58 passed.
- P3 eval/judge scenario final `python -m pytest -q`: exit 0.
- P3 eval/judge scenario collect-only `python -m pytest --collect-only -q`: 147 tests collected.
- `python -m phantom_training.cli eval-judge-scenario --out <temp>`: wrote deterministic scenario manifest with `mode=synthetic_eval_judge_pipeline_scenario`, `real_training=false`, `model_artifacts_written=false`, `external_network=false`, `gpu_required=false`, `publish_enabled=false`, `eval_rows=8`, `token_f1=0.2353`, `judge_accepted=1/1`, `tier1_demo_ready=true`, and `real_training_release_ready=false`.
- `agy` P3 eval/judge scenario reviewer result: `NO BLOCKERS` for real training enablement, model artifact or weight retention, external network/GPU/publish implication, private dataset/prompt/output leakage, false public benchmark/model eval claims, nondeterminism, docs/CLI/script/test mismatch, demo-loop regression, or backend-lifecycle regression.
- `agy` reviewer result: no P2 blockers for real training enablement, model artifacts, network/GPU/backend requirements, private data risk, missing dataset/run/backend contracts, nondeterminism, docs/tests mismatch, or `--commit` Tier 1 gate drift.
- `agy` P2 backend lifecycle reviewer result: `NO BLOCKERS` for real training enablement, model artifacts, GPU/network/backend requirements, publish enablement, private prompt/dataset leakage, docs/CLI/script mismatch, nondeterminism, or `--commit` Tier 1 gate drift.

## P4 Release-Prep Slice 1

Status: governance baseline added; this does not mark the project release-ready.

Evidence:
- `CONTRIBUTING.md` defines the contribution workflow, required test command, readiness-doc update rule, and no-private-data/no-credentials boundary.
- `SECURITY.md` defines private vulnerability reporting, supported version scope, 7-day acknowledgement target, and safe report contents.
- `python -m pytest tests/test_release_prep_contract.py -q`: 1 passed.
- `python -m pytest -q`: passed.
- `python -m pytest --collect-only -q`: 148 tests collected.

Remaining P4 work: full release gate, final docs audit, package metadata audit, release notes, tag plan, and maintainer sign-off.

## P4 Release-Prep Slice 2

Status: final release gate checklist added; this does not mark the project release-ready.

Evidence:
- `CHANGELOG.md` records the unreleased governance/release-checklist work and points back to readiness evidence.
- `docs/RELEASE_CHECKLIST.md` documents final tests, dependency/license review, secret/private-data scan, known limitations, and manual maintainer approval.
- `python -m pytest tests/test_release_prep_contract.py -q`: 2 passed.
- `python -m pytest -q`: passed.
- `python -m pytest --collect-only -q`: 149 tests collected.

Remaining P4 work: execute final scans, complete dependency/license review, finalize release notes, and record manual maintainer approval.

## P4 Release-Prep Slice 3

Status: final scan and direct dependency/license audit recorded; not release-ready.

Evidence:
- `docs/FINAL_RELEASE_AUDIT.md` records scan scope, `high_conf_secret_hits=0`, direct dependency/license review, and remaining release blockers.
- Direct release-scope dependency review: no runtime dependencies beyond Python stdlib for Tier 1.
- Optional real-training extras remain outside the Tier 1 default release path and require separate backend/model-artifact review.
- `python -m pytest tests/test_release_prep_contract.py -q`: 3 passed.
- `python -m pytest -q`: passed.
- `python -m pytest --collect-only -q`: 150 tests collected.

Remaining P4 work: release notes finalization, tag plan, final maintainer approval, and separate review for any real training backend publication.

## P4 Release-Prep Slice 4

Status: maintainer approval recorded, conductor sign-off complete, and local tag created; remote publication pending.

Evidence:
- `docs/RELEASE_NOTES.md` records public release-candidate notes, known limitations, and verification pointers.
- `docs/TAG_PLAN.md` records proposed tag `v0.1.0-alpha.0`, required approval-before-tag sequence, and rollback steps.
- `docs/PUBLIC_RELEASE_APPROVAL.md` records `Status: approved` with approver, approval date, and approved tag.
- Conductor root approval packet `PHANTOM-SATELLITES-PUBLIC-RELEASE-APPROVAL.md` records all ten candidate tags as approved.
- `.github/workflows/ci.yml` runs an explicit `release-prep gate` against `tests/test_release_prep_contract.py`.
- `python -m pytest tests/test_release_prep_contract.py -q`: 5 passed.
- `python -m pytest -q`: passed.
- `python -m pytest --collect-only -q`: 152 tests collected.

Remaining publication work: confirm target remote and repository visibility before pushing tags or publishing release pages.
