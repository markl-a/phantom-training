# Public Demo And Artifact Policy

`phantom-training` 的公開開源 demo 只展示 Tier 1 deterministic pipeline。它用合成軌跡資料完成:

- recipe merge / dry-run plan
- `seed-fixture`
- `build-dataset`
- `eval`
- `judge`

這不是 real training，不會下載模型，不會啟動 GPU fine-tune，不會上傳資料，也不會產生可部署的 LoRA adapter 或 model weights。

## Public Use Case

這個 demo 適合用來驗證一個 post-training 專案在開源狀態下是否具備基本工程骨架:

- 可以把 agent trajectory 轉成 Alpaca-style `dataset.jsonl`
- 可以用 deterministic held-out proxy metric 檢查資料是否有基本可學習訊號
- 可以用 hermetic judge 驗證 code / QA task 的成功與失敗
- 可以證明 real backend 尚未配置時，`--commit` 會安全失敗

它不適合宣稱模型品質、benchmark 成績、實際微調能力或商用品質改善。

## Quickstart

從 repo 根目錄執行:

```powershell
$root = Join-Path $env:TEMP "phantom-training-demo"
Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $root | Out-Null

$db = Join-Path $root "memory.db"
$ds = Join-Path $root "dataset.jsonl"
$tasks = Join-Path $root "tasks.jsonl"

python -m phantom_training.cli --skill rust-coder --base qwen2.5-coder-7b --recipe examples\rust-coder.toml --dry-run --json --db $db
python -m phantom_training.cli seed-fixture --db $db
python -m phantom_training.cli build-dataset --skill rust-coder --db $db --out $ds
python -m phantom_training.cli eval --dataset $ds --json

'{"kind":"qa","prompt":"What command builds the public demo dataset?","answer":"build-dataset","expected":"build-dataset"}' | Set-Content -Encoding UTF8 $tasks
python -m phantom_training.cli judge --tasks $tasks --json
```

Expected artifacts:

- `memory.db`: synthetic fixture trajectory database.
- `dataset.jsonl`: synthetic Alpaca-style rows with `instruction`, `input`, and `output`.
- eval JSON: a lightweight proxy floor, not a public benchmark or model eval.
- judge JSON: deterministic hermetic judge output, not model inference.

## P2 Artifact Bundle

`demo-loop` is the deterministic P2 public artifact path. It writes a complete
training-planning bundle without real training, model downloads, GPU work, or
weight publishing.

```powershell
$bundle = Join-Path $env:TEMP ("phantom-training-loop-" + [guid]::NewGuid().ToString("N"))
python -m phantom_training.cli demo-loop --out $bundle
Get-Content (Join-Path $bundle "manifest.json")
```

After installation, the same path is available as:

```powershell
phantom-training-demo-loop --out <bundle-dir>
```

Bundle artifacts:

- `manifest.json`: schema version, mode, safety flags, and artifact list.
- `dataset.jsonl`: deterministic synthetic Alpaca-style rows.
- `dataset-card.json`: dataset schema, row count, source, curator counts, and
  private-data/model-artifact policy.
- `run-manifest.json`: selected skill/base model/backend, dry-run status,
  LoRA/optimizer plan, eval result, judge result, and artifact list.
- `backend-adapter-contract.json`: Tier 1 dry-run adapter boundary, allowed
  future backends, and `--commit` requirements.
- `eval.json`: deterministic held-out proxy metric.
- `judge.json`: deterministic hermetic judge result.
- `summary.md`: short human-readable summary.

The public manifest must include `real_training=false`,
`model_artifacts_written=false`, `external_network=false`, `gpu_required=false`,
and `synthetic_only=true`.

## P2 Backend Lifecycle Bundle

`backend-lifecycle` validates the public Tier 1 contracts produced by
`demo-loop`: dataset card, run manifest, and backend adapter contract. It does
not train a model, download weights, require a GPU, publish artifacts, or enable
a real backend.

```powershell
$bundle = Join-Path $env:TEMP ("phantom-training-lifecycle-" + [guid]::NewGuid().ToString("N"))
python -m phantom_training.cli backend-lifecycle --out $bundle
Get-Content (Join-Path $bundle "manifest.json")
```

After installation, the same path is available as:

```powershell
phantom-training-backend-lifecycle --out <bundle-dir>
```

Bundle artifacts:

- `manifest.json`: schema version, mode, safety flags, selected stage, and artifact list.
- `backend-lifecycle.json`: Tier 1 dry-run stages and future private backend boundary.
- `dataset-card-validation.json`: required-field, row schema, row count, private-data, and model-artifact checks.
- `run-manifest-validation.json`: dry-run, commit, real-training, network, GPU, and model-artifact checks.
- `audit-log.jsonl`: metadata-only validation events; it must not store dataset rows, prompts, outputs, private data, model weights, or publish credentials.
- `summary.md`: short human-readable summary.

The public manifest must include `real_training=false`,
`model_artifacts_written=false`, `external_network=false`, `gpu_required=false`,
`publish_enabled=false`, and `synthetic_only=true`.

## P3 Eval/Judge Scenario

`eval-judge-scenario` combines the P2 training-planning bundle with the P2
backend lifecycle bundle, then writes a reproducible report for the proxy eval
floor, hermetic judge, reproducibility checks, and release gate.

```powershell
$bundle = Join-Path $env:TEMP ("phantom-training-eval-judge-" + [guid]::NewGuid().ToString("N"))
python -m phantom_training.cli eval-judge-scenario --out $bundle
Get-Content (Join-Path $bundle "manifest.json")
```

After installation, the same path is available as:

```powershell
phantom-train eval-judge-scenario --out <bundle-dir>
phantom-training-eval-judge-scenario --out <bundle-dir>
```

Bundle artifacts:

- `manifest.json`: schema version, mode, safety flags, source bundle references,
  and artifact map.
- `eval-report.json`: deterministic held-out proxy floor metrics.
- `judge-report.json`: deterministic hermetic judge summary.
- `reproducibility-report.json`: dataset-card, run-manifest, backend-stage, and
  public reproducibility status.
- `release-gate.json`: Tier 1 demo readiness and explicit real-training release
  blockers.
- `audit-summary.json`: metadata-only event summary.
- `summary.md`: human-readable summary.

The public manifest must include `real_training=false`,
`model_artifacts_written=false`, `external_network=false`, `gpu_required=false`,
`publish_enabled=false`, and `synthetic_only=true`. The eval report remains a
proxy floor, not a public benchmark or model eval; the judge report remains a
hermetic local check, not model inference.

## Tier 1 Safety Check

`--commit` is intentionally disabled when a real backend is not available. In Tier 1, this command should exit 2:

```powershell
python -m phantom_training.cli --skill rust-coder --base qwen2.5-coder-7b --commit --db $db
```

The expected error explains that the selected backend is not available in Tier 1 and that Tier 2 extras are required.

## Artifact Policy

Public fixtures and examples must remain synthetic and reproducible.

Do not commit:

- private prompts
- private agent trajectories
- private datasets
- private model weights
- private LoRA adapters
- production benchmark claims that cannot be reproduced from public inputs

Any future Tier 2 / Tier 3 backend must keep private data local by default and require explicit user action before publishing artifacts.
