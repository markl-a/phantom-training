# phantom-training

[![CI](https://github.com/markl-a/phantom-training/actions/workflows/ci.yml/badge.svg)](https://github.com/markl-a/phantom-training/actions/workflows/ci.yml)
![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)
[![phantom-mesh ecosystem](https://img.shields.io/badge/ecosystem-phantom--mesh-purple)](https://github.com/markl-a/phantom-mesh)

> phantom-mesh 上的 headless + agentic + 跨裝置 post-training 編排器 —— 把你自己的 agent 軌跡練成「懂你的小模型」,回餵成 phantom skill。Tier 1（已出貨）是確定性管線:recipe-merge plan + build-dataset + token-overlap eval floor + hermetic judge,**非 LLM agent、非真訓練**(那在 Tier 2/3)。

📄 完整文件(定位/快速上手/路線圖/開源方向):見 [docs/phantom-training.md](docs/phantom-training.md)

## Quickstart

Tier 1 public demo 只展示 deterministic plumbing: plan -> seed fixture -> build dataset -> eval -> judge。它是**非真訓練**路徑,不下載模型、不跑 GPU fine-tune、不產生可發布權重。

```powershell
python -m pip install -e .[dev]
python -m pytest -q

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

P2 deterministic artifact bundle:

```powershell
$bundle = Join-Path $env:TEMP ("phantom-training-loop-" + [guid]::NewGuid().ToString("N"))
python -m phantom_training.cli demo-loop --out $bundle
Get-Content (Join-Path $bundle "manifest.json")
Remove-Item -LiteralPath $bundle -Recurse -Force
```

P2 backend lifecycle validation bundle:

```powershell
$bundle = Join-Path $env:TEMP ("phantom-training-lifecycle-" + [guid]::NewGuid().ToString("N"))
python -m phantom_training.cli backend-lifecycle --out $bundle
Get-Content (Join-Path $bundle "manifest.json")
Remove-Item -LiteralPath $bundle -Recurse -Force
```

P3 deterministic eval/judge reporting scenario:

```powershell
$bundle = Join-Path $env:TEMP ("phantom-training-eval-judge-" + [guid]::NewGuid().ToString("N"))
python -m phantom_training.cli eval-judge-scenario --out $bundle
Get-Content (Join-Path $bundle "manifest.json")
Remove-Item -LiteralPath $bundle -Recurse -Force
```

Artifact policy、`--commit` 安全失敗行為與可公開展示邊界見 [docs/PUBLIC_DEMO.md](docs/PUBLIC_DEMO.md)。P3 eval/judge scenario contract 見 [docs/EVAL_JUDGE_SCENARIO.md](docs/EVAL_JUDGE_SCENARIO.md)。
