# phantom-training — DESIGN（reframe 2026-06-02）

> 取代「Agent 包一層 fine-tune CLI」的舊定位。核心價值在**訓練閉環**，不是 wrapper。

## 1. 定位（reframed）
**phantom-training = phantom-mesh 的 Agentic Training Ops 層。**
一個讓 coding agent（Claude Code / Codex / Hermes / OpenClaw）驅動的**訓練閉環專案骨架**：

```
你的 phantom 軌跡(FTS5/Hermes trajectory)
  → Dataset Doctor 診斷/清理
  → Hermes Curator 篩成功 case
  → Config Generator 偵測 GPU→產 Axolotl/Unsloth config
  → train（Axolotl/Unsloth，可 dispatch 到 mesh GPU node）
  → Log Watcher 讀 log 自動修錯(OOM/NaN→改 config 重跑)
  → eval（holdout / HumanEval 子集）
  → Report（markdown）
  → Experiment Planner 規劃下一輪
```
**Headline demo**：「從你自己的 Rust session 把 phantom 的 coder agent 練得更強」（P3 進化網 measure-upgrade）。

## 2. 為什麼不是通用 AutoTrain（差異化 / 護城河）
通用「coding agent + Axolotl + MLflow」是紅海（14+ 框架）。phantom-training 唯一的 moat = **長在 phantom-mesh 上**的三個別人沒有的資產：
1. **資料來自你自己的 agent 軌跡**（FTS5 / Hermes trajectory export）——不是公開 dataset。
2. **Hermes Curator 當成功判斷**（軌跡標成功/失敗→preference data）。
3. **跨 mesh GPU node dispatch**（`phantom dispatch` 把訓練丟到有 GPU 的節點）。
→ 對應研究的「組合 C：Hermes/OpenClaw + trajectory export + TRL + DPO」，不是「組合 A 通用微調」。

## 3. 與 phantom 的協同接口
- **讀資料**：phantom FTS5 軌跡。⚠️ 現 `dataset.py` 指向 `~/.phantom-mesh/memory.db`（**此機不存在**）→ 改指部署中的 `events.sqlite/fts5_events`（或 fallback 兩者）。
- **成功判斷**：`judge.py` 接真 Hermes Curator（核心 `experimental-hermes-curator` feature）。
- **訓練調度**：`train` step 可 shell out `phantom dispatch` 路由到 GPU node。
- **operator**：coding agent 讀 `AGENTS.md` + 跑 `Makefile`，不臨時拼指令。

## 4. 本期 MVP（閉環骨架，**不需 GPU/大資料就能 demo**）
保留 / 修 / 加 / 延後：

| 研究note 功能 | 現況 | 本期 |
|---|---|---|
| Dataset Doctor（健檢/清理）| `dataset.py` 種子 | ✅ 做（讀 FTS5 軌跡、查格式/洩漏/token 長度）|
| Hermes judge（成功篩選）| `judge.py` 種子 | ✅ 做（接 Hermes Curator）|
| Config Generator（偵 GPU→config）| ❌ | ✅ 做（不需真訓練）|
| Log Watcher / 自動修錯 | ❌ | ✅ 做（解析 sample log → OOM/NaN 改 config）|
| Report（markdown）| `cli.py` 印 plan | ✅ 做 |
| 實際 fine-tune（Axolotl/Unsloth 真跑）| dry-run plan | 🔮 延後（需 GPU+資料，plug 進 `train`）|
| Ray Tune 調參 / RAG eval / 多框架 / HF push / GGUF / deploy | ❌ | 🔮 延後（避免「支援所有東西」陷阱）|

**MVP Gate**：coding agent 讀 `AGENTS.md`→`make inspect`(Dataset Doctor 出報告)→`make config`(產 config)→`make train`(無 GPU 則 dry-run plan)→`make report`(markdown)。閉環跑通、報告出現，即達標。

**骨架結構（要長出來）**：
```
phantom-training/
  AGENTS.md            # coding agent 的操作說明(讀這個再跑 Makefile)
  Makefile             # inspect/config/train/eval/report/all
  phantom_training/
    dataset.py         # 保留→Dataset Doctor (改 db 指向)
    judge.py           # 保留→Hermes 成功篩選
    cli.py             # 既有(plan)→併入 report
    gen_config.py      # 新：偵 GPU→Axolotl/Unsloth config
    watch_log.py       # 新：log 解析+修錯建議
    report.py          # 新：markdown 報告
  configs/  data/  runs/  reports/
```

## 5. 延後 + 風險
- **延後**：真 fine-tune backend(Unsloth/Axolotl 實跑)、Ray Tune、DPO/preference、cross-device dispatch 實作、RAG eval、HF push、9-Agent benchmark。
- **風險**：① 資料量（FTS5 現 0 列，靠 ai-feed/companion 灌 + 你日常 phantom 使用累積）② GPU（Mac M1 <4B；真訓練要 mesh GPU node）③ tagline 別吹過頭（README 標清 backend 在 roadmap）④ 跟 secure-connector 一樣別變「支援所有框架」。

## 6. README 誠實化（DONE 2026-06-18）
- ✅ tagline 去掉「Tier 1 = LLM agent picks hyperparams today」的過度宣稱；標明
  Tier 1 是 deterministic recipe-merge + token-overlap eval floor，agentic loop
  在 Tier 2/3。
- ✅ 讀資料敘述改成：支援路徑 = `phantom recall --json`（live timeline），
  `memory.db` 是 fixture / Tier-2 Hermes-judged trajectory store 的 fallback
  shape（fresh machine 為空）。`events.sqlite/fts5_events` 是 dead scaffolding
  （見 `dataset.py` docstring）。
- ✅ status block 補上實際已 ship 的 `seed-fixture / build-dataset / eval`
  子指令與 recipe 範圍驗證。
