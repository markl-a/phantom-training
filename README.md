# phantom-training

[![CI](https://github.com/markl-a/phantom-training/actions/workflows/ci.yml/badge.svg)](https://github.com/markl-a/phantom-training/actions/workflows/ci.yml)
![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)
[![phantom-mesh ecosystem](https://img.shields.io/badge/ecosystem-phantom--mesh-purple)](https://github.com/markl-a/phantom-mesh)

> **把你自己的 agent 執行軌跡,煉成「懂你的小模型」,再回餵成 phantom skill** —— phantom-mesh 生態上 headless、跨裝置的 post-training 編排器。

**解決的問題:** agent 每天產生大量高價值的執行軌跡,卻通常用完即棄。phantom-training 把這些軌跡收斂成可重現的 fine-tune 資料與評測,讓「用得越久、越懂你」的小模型成為可能。

已出貨的 **Tier 1** 是一條完全確定性、零外部相依(stdlib-only)的資料管線:recipe-merge 規劃 → 從 agent 記憶抽取軌跡 → 建 alpaca 資料集 → held-out eval floor(exact-match + token-F1)→ 沙箱化 hermetic judge。整條管線可重現、可測(**183 個測試全綠**),並以 **MCP server** 形式把 `training_eval` 工具掛進 phantom mesh。真訓練後端(Unsloth/Axolotl)、知識庫累積與 agent 優化循環屬 Tier 2/3 路線圖。

📄 完整文件(定位/快速上手/路線圖/開源方向):見 [docs/phantom-training.md](docs/phantom-training.md)

## Quickstart

Tier 1 public demo 只展示 deterministic plumbing: plan -> seed fixture -> build dataset -> eval -> judge。它是**非真訓練**路徑,不下載模型、不跑 GPU fine-tune、不產生可發布權重。

```powershell
python -m pip install -e .[dev]
python -m pip install -e . --dry-run --no-deps
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

同一個 eval floor 也能以 **MCP server** 形式掛進 phantom mesh,供 mesh 上的 agent 直接呼叫 `training_eval` 工具。MCP transport 是 Tier 1 核心相依,`pip install -e .` 預設就會裝好,無需額外 extra:

```powershell
python -m pip install -e .
phantom-training-mcp   # stdio MCP server,對外暴露 `training_eval`(held-out EM + token-F1)
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

## Status

**Tier 1 已出貨且測試覆蓋(183 個測試全綠,stdlib-only,Apache-2.0)。** 每一項都是真實計算的邏輯,而非佔位:

- **Deterministic planner** — recipe-merge 產出結構化 fine-tune plan;在真實訓練後端就位前,`--commit` 會安全拒絕(exit 2)而非假裝訓練。
- **Trajectory → dataset** — 讀取 agent 記憶(`phantom recall` / `memory.db`),經 Curator 過濾,輸出去重後的 alpaca JSONL。
- **Eval floor** — 確定性 held-out 切分 + token-overlap 檢索基線(exact-match + token-F1);對損毀/過短輸入回報結構化錯誤,不會 crash。
- **Hermetic judge** — 沙箱化子行程評分:程式碼看單元測試通過率,QA 看正規化比對。
- **Reproducible bundles** — `demo-loop` / `backend-lifecycle` / `eval-judge-scenario` 產出 manifest 驗證的成品包,供離線重現與 release gate。
- **MCP server** — `phantom-training-mcp` 以 MCP server 形式對 phantom mesh 暴露 `training_eval` 工具(即上面的 held-out eval floor),讓 mesh 上的 agent 直接取用同一份確定性指標。
- **Packaging / CI** — 5 個 console entry point、contract 測試與 CI 全綠。

**Roadmap(Tier 2/3 方向):** 選配 `--commit` 背後接真實 LoRA 訓練後端(Unsloth/Axolotl);可累積的 recipe knowledge base + agent 優化循環;受治理的跨裝置 GPU dispatch;公開 benchmark(HumanEval/MBPP)評測;以及把煉好的 skill 回發佈進 phantom-mesh。
