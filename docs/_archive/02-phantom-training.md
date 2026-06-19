> ARCHIVED 2026-06-19 — 內容已併入 docs/phantom-training.md;此為歷史版本。

# ② phantom-training

> **Agentic post-training orchestrator on phantom-mesh**
> 第一個 self-hosted + cross-device + agentic 的 fine-tuning 框架

## 一句話定位

「Phantom-mesh 上的 AI agent 自己會訓練 AI 模型 — 看使用 pattern,自動挑 base model、調 hyperparams、跑 fine-tune、評估迭代,結果回餵成 phantom 的新 skill。」

## 對齊 BIG-GOAL

- **P3 進化網**:Hermes 6-step(judge → extract → store → recall → apply → measure)的 **measure** 升級版 — 不只記錄,還能自動 fine-tune 出新 model
- **P4 加密為先**:training data 不離本機,model weight 加密 at rest

## 競品分析(2026 現況)

| 框架 | 強項 | phantom-training 差異 |
|---|---|---|
| **Unsloth**(2026/2 釋出)| 12× faster MoE,single-GPU 優化 | phantom-training 以 Unsloth 為 backend,加 agent 自動 hyperparam |
| **Axolotl** | YAML config,多 GPU | phantom-training 以 Axolotl 為 backend |
| **LLaMA Factory** | UI-friendly | phantom-training 為 headless agentic,UI 在 phantom 內 |
| **DSPy** | Agent tune prompt + few-shots | phantom-training tune **weights**,不只 prompt |
| **LaMDAgent**(2026 paper)| LLM agent 自動構建 post-training pipeline | phantom-training 為 LaMDAgent 概念的 user-friendly impl |
| **HF AutoTrain** | SaaS,簡單 | phantom-training 為 self-hosted + agentic |

**phantom-training 的 niche**:**第一個跑在 phantom-mesh 上的 agentic post-training orchestrator** — 站在 Unsloth/Axolotl 巨人肩膀,加 phantom 的 agent + cross-device 優勢。

## 核心功能

```
User 講: "把 phantom 的 coder agent 變得更會寫 Rust"
   ↓
phantom-training agent:
   1. 從 phantom FTS5 memory 抓 Rust-related session(訓練資料)
   2. 篩出成功 case(用 Hermes Curator judge)
   3. 自動 build dataset (instruction-tuning format)
   4. 挑 base model (Qwen2.5-Coder-7B or Code-Llama-7B)
   5. 自動 set hyperparams(LoRA rank, lr, batch)
   6. 在 Mac M1 或 cluster 的 GPU node 跑 Unsloth fine-tune
   7. eval on holdout set + benchmark on HumanEval/MBPP
   8. 若 metric 達 baseline,publish 成 phantom skill「rust-coder-v2」
   9. 若不達,自動調 hyperparams 重跑(LaMDAgent 概念)
```

## 招聘 / 副業 / 應用評分

| 維度 | 評分 | 對應 |
|---|---|---|
| **招聘** | ⭐⭐⭐⭐⭐ | NVIDIA(training infra) / Anthropic(post-training research) / Modal / Together / 工研院 / 中研院 |
| **副業** | ⭐⭐⭐⭐ | 線上課程「用 phantom + agent 訓練自己的小模型」+ premium model recipe 包 |
| **個人應用** | ⭐⭐⭐ | 持續優化 phantom agent quality(間接)|

## MVP scope

### Must have(M3 W11-12)
- [ ] CLI: `phantom train --skill <name> --base <model>`
- [ ] 自動從 FTS5 抓 training data(Hermes Curator 篩成功 case)
- [ ] 整合 Unsloth 當 backend(LoRA / QLoRA)
- [ ] 自動 hyperparam search(用 LLM agent 提案)
- [ ] eval pipeline(holdout + 3 個 public benchmark)
- [ ] training history 寫回 FTS5
- [ ] 1 個 demo:`phantom train --skill rust-coder`,跑出可用結果

### Nice to have
- [ ] cross-device dispatch(Mac 小模型,GPU node 大模型)
- [ ] 多輪 RLHF(用 DPO,sample 對話成 preference data)
- [ ] model registry + version control
- [ ] 9-Agent Landscape benchmark 自動定期跑

### NOT doing
- 從零 pretrain(只做 fine-tune / DPO)
- 多模態 train(只 text,圖像 wait v2)
- 雲端 SaaS(local-first 違反)

## 改裝來源

**沒有現成 repo**(新建)。但融合既有:
- phantom-mesh 的 Hermes Curator(已 ship,作為 data filter)
- 9+ AI Coding Agent Landscape Report(2,900 行,作為 benchmark spec)
- Unsloth / Axolotl(套件 dependency)
- DSPy(prompt-side optimization)

## 風險

- **GPU 需求**:Mac M1 16GB 只能 train 4B 以下;大模型需要外接 GPU node
- **dataset 量**:phantom FTS5 累積資料 < 2 月可能不夠 fine-tune
- **eval 信度**:自評 benchmark 容易 overfit,要強制用 public eval set
- **學術競爭**:LaMDAgent 為 paper,本專案為 user-facing impl,若有人先做出來會被吃掉
- **scope 太大**:可能要 cut MVP 到只支援 LoRA + 1 個 base model

## 變現路徑

| 路徑 | 細節 |
|---|---|
| 線上課程 | 「Agentic Fine-Tuning 實戰:用 phantom 訓練自己的 AI」 |
| Premium Model Recipe Pack | LoRA 配方包(rust-coder / sql-expert / health-coach) |
| Sponsor / 顧問 | 中小公司 fine-tune 顧問接案 |
| 學術合作 | 跟工研院 / 中研院 / 學界合作 paper(間接價值) |

## 為什麼放 M3 W11-12(較後做)

- 需要 phantom-mesh 跑 2-3 個月才累積足夠 FTS5 資料
- 需要 Hermes Curator 篩過的 skill bank 才有 fine-tuning material
- 必須先做 ① + ⑥ + ④ 累積基礎

---

*Sanitized public spec. Author: Mark Lai ([@markl-a](https://github.com/markl-a)).*
