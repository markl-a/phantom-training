> ARCHIVED 2026-06-19 — 內容已併入 docs/phantom-training.md;此為歷史版本。

# 開源生態與方向 — LLM 微調 / 訓練 / 資料集策展 / 評估

> 範圍：phantom-training 在 2026 年開源後訓練（post-training）技術棧中的定位，
> 哪些該**採用 / 包裝 / 參考 / 自建**，以及該避免的過度建構陷阱。
> 狀態的單一真實來源（SSOT）仍為 [`/ROADMAP.md`](../ROADMAP.md)；本文件談方向，不談狀態。
> 星數 / 版本號於 2026 年 6 月透過 GitHub repo 頁面查證；任何
> 未確認者皆標記 **[unverified]**。請勿將數字視為精確值——它們
> 每週都在飄移。最後一次調查：2026-06-19。

---

## 1. 現況（有依據）

phantom-training 目前是 **Tier-1 確定性管線（deterministic plumbing）**，既不是訓練器，也不是
代理人（agent）。權威的已交付 / 規劃清單為 **[`/ROADMAP.md`](../ROADMAP.md)**；
以下摘要僅為其（與 `README.md`）的轉述，提供脈絡之用——它不新增
任何狀態主張：

- 一個 `phantom-train` argparse CLI，會**合併 recipe 預設值並印出
  結構化的微調計畫**（`--dry-run`；`--commit` 依設計以 2 退出——尚未接上
  訓練後端）。
- `seed-fixture` → 示範軌跡 SQLite DB；`build-dataset` → 軌跡 →
  Curator filter → alpaca 風格 JSONL（已去重）；`eval` → 一個無相依套件的
  **token 重疊下限（token-overlap floor）**（確定性切分 + 最近指令檢索
  以精確比對與 token-F1 計分——明確定位為下限，而非基準測試）。
- 一個**真實的密封式評審（hermetic judge）**（`hermetic_judge.py`）：程式碼候選以
  沙箱子行程的單元測試通過率計分；QA 以正規化比對計分；接上
  `is_success`（curator accept）。無模型推論、無 GPU。
- 僅用標準函式庫（stdlib-only）的模組、一套通過的密封式 pytest 測試、ruff 乾淨、push/PR 觸發 CI、
  Apache-2.0、自架 asciinema 示範（精確數字 / commit：見 `ROADMAP.md`）。

**尚未建構的部分**（已規劃，依據 ROADMAP「Planned next」）：任何真實的
訓練器（Unsloth 後端屬 Tier 2）、真實的 Curator HTTP 呼叫、真實的公開
基準測試框架、代理人驅動的超參數搜尋（Tier 3）、跨裝置 GPU
派工，以及 skill-publish 迴圈。

### 要守護的利基

phantom-training **不是**訓練器，也絕不該試圖變成訓練器。它
可防守的利基是**編排（orchestration）+ 來源溯源（provenance）+ 評估誠實性（eval-honesty）**這一層，
這是沒有任何通用框架擁有的：

1. **密封、確定性的評估下限 + 真實評審**（沙箱單元測試
   通過率）——在一台全新機器上可重現，無需 GPU、無需網路、無需模型。
2. **「訓練一個懂你的小模型」**——資料集來自*你自己的*
   phantom-mesh 代理人軌跡（支援的讀取路徑 = `phantom recall --json`，
   並以 `memory.db` fixture 作為後備；`events.sqlite/fts5_events` 是無用的
   殘留鷹架，而非來源），由 Hermes Curator 成功訊號過濾
   （目前為啟發式，真實 HTTP 呼叫屬 Tier 2）——而非公開資料集。
3. **跨裝置、受治理的派工**，跨越個人 mesh（Tier 3）：把
   實際的 GPU 工作路由到擁有該硬體的節點，在 phantom-mesh
   governor + flight-recorder 之下執行。

以下所有內容皆為了**餵養該利基，並避免重建
生態系已經做得更好的部分**而選定。

---

## 2. 生態全景

### 2.1 訓練器 / 微調引擎

| Project | URL | Stars | Lang | License | 成熟度 | 對 phantom-training 的契合 / 落差 |
|---|---|---:|---|---|---|---|
| **Unsloth** | github.com/unslothai/unsloth | ~66.8k | Python | Apache-2.0 **+ AGPL-3.0**（雙授權） | 成熟、非常活躍 | **首選後端候選。**單 GPU 最佳化的 SFT/RL/GRPO，最高可達「2x 更快、VRAM 少 70%」（GRPO 少 80%）[已查證 README 主張]。可在 macOS/Win/WSL/Linux 上執行——最適合 Mac M 系列 / 消費級 GPU 的 mesh 節點。**落差：**它是 kernels + 一個 `train()` 呼叫，不是編排器。**包裝它；不要重寫。** |
| **Axolotl** | github.com/axolotl-ai-cloud/axolotl | ~12.1k | Python | Apache-2.0 | 成熟（v0.17.0，2026 年 6 月） | **次選 / 多 GPU 後端候選。**以 YAML 設定跨多種模型做 SFT/LoRA/DPO，多 GPU 故事較強。**落差：**由 YAML 驅動，非代理式。當工作需要多於一張 GPU 時是良好的後備。 |
| **LLaMA-Factory** | github.com/hiyouga/LLaMA-Factory | ~72.3k | Python | Apache-2.0 | 成熟（v0.9.5），NVIDIA/Amazon/Aliyun 採用 | 100+ 模型、零程式碼 CLI + Web UI。**落差 / 重疊：**其 Web UI 與「phantom 以無頭方式驅動它」的價值重疊；多半作為 recipe 覆蓋度的**參考**，而非要承接的相依（很重）。 |

### 2.2 函式庫原語（後訓練方法）

| Project | URL | Stars | Lang | License | 成熟度 | 契合 / 落差 |
|---|---|---:|---|---|---|---|
| **HF TRL** | github.com/huggingface/trl | ~18.7k | Python | Apache-2.0 | 成熟（v1.x） | SFT / DPO / GRPO / PPO + 獎勵訓練。當 phantom-training 進入 Post-M3 偏好學習時，**作為 DPO/偏好的參考**。Unsloth/Axolotl 已建構於這些方法之上——目前可能是間接相依，尚非直接相依。 |
| **HF PEFT** | github.com/huggingface/peft | ~21.3k | Python | Apache-2.0 | 成熟 | LoRA/QLoRA `LoraConfig`——正是 Tier-2 計畫已點名者。被 Unsloth 遞移性地拉入。**在計畫 schema 中採用 `LoraConfig` 的形狀**，讓輸出能 1:1 對映其上。 |

### 2.3 資料集策展 / 合成資料

| Project | URL | Stars | Lang | License | 成熟度 | 契合 / 落差 |
|---|---|---:|---|---|---|---|
| **distilabel**（Argilla） | github.com/argilla-io/distilabel | ~3.3k | Python | Apache-2.0 | 活躍、社群維護（[unverified] 原作者已離開） | 合成資料 + AI 回饋的 pipeline。**AI 回饋模式的參考。** **陷阱：**phantom-training 的資料是*你的真實軌跡*，不是合成資料——在此大量採用會稀釋利基。 |
| **Bespoke Curator** | github.com/bespokelabsai/curator | ~1.7k | Python | Apache-2.0 | 成熟中（v0.1.x） | 後訓練用的批次推論 + 結構化策展。日後擴展策展步驟的**參考**；目前的 Curator filter 是 phantom Hermes 訊號，那才是護城河——保留它。 |

### 2.4 評估

| Project | URL | Stars | Lang | License | 成熟度 | 契合 / 落差 |
|---|---|---:|---|---|---|---|
| **lm-evaluation-harness**（EleutherAI） | github.com/EleutherAI/lm-evaluation-harness | ~13k | Python | MIT | 成熟；支撐 HF Open LLM Leaderboard | 60+ 學術基準、多後端。**採用為選用的「公開基準」分支**，讓 publish gate 有實質效力（通用型）。注意 ROADMAP 為 **HumanEval/MBPP 程式碼評估**點名了 `bigcode-evaluation-harness`——那是程式碼專屬的姊妹專案；依 skill 選用（程式碼 → bigcode-eval-harness；通用 → lm-eval-harness）。**讓這些保持選用 / 額外**，使密封下限維持無相依。 |

### 2.5 鄰近 / 「不要變成」的參考

| Project | URL | Stars | Lang | License | 成熟度 | 為何僅供參考 |
|---|---|---:|---|---|---|---|
| **OpenPipe** | github.com/OpenPipe/OpenPipe | ~2.8k | TypeScript | Apache-2.0 | 活躍、open-core（[unverified] OSS 因專有版合併而暫停） | 「把昂貴的 prompt 變成便宜的微調模型」——最接近的*產品*類比（capture → 微調小模型）。**capture→distill UX 的參考**，但它是 SaaS 形態 / 雲端優先；phantom-training 的 local-first + mesh 溯源是刻意的差異。 |
| **HF AutoTrain** | huggingface.co/autotrain | n/a | Python | (HF) | 成熟 SaaS | phantom-training 明確*不要*成為的那個「SaaS 按鈕」。僅供參考。 |
| **DSPy** | github.com/stanfordnlp/dspy | （[unverified] ~20k+） | Python | MIT | 成熟 | 調整的是 **prompt/few-shot**，而非權重。對 Tier-3 代理人提案迴圈（LaMDAgent 風格）是有用的**參考**，但不是訓練器。 |

---

## 3. 建議方向（adopt / wrap / reference / build）

**ADOPT（作為相依採納，盡量選用 / 額外）：**
- **PEFT `LoraConfig` 形狀**——現在就讓 Tier-2 計畫 schema 1:1 對映其上（便宜、無 GPU）。
- **lm-eval-harness / bigcode-evaluation-harness**——作為*選用額外*的評估分支；絕不放在密封下限路徑上。

**WRAP（薄薄的後端轉接器，絕不重寫其內部）：**
- **Unsloth** 作為預設的 Tier-2 `train(plan, dataset)` 後端（單 GPU / Mac / 消費級 GPU）。
  - ⚠️ **Unsloth 是 Apache-2.0/AGPL-3.0 雙授權。** phantom-training 為 Apache-2.0；把 Unsloth 隔離在子行程 / 選用額外的邊界之後，並在 vendoring 前確認授權交互。**[unverified — Tier-2 上線前需做一次審慎的授權審讀]**
- **Axolotl** 作為次要後端，藏在同一個轉接器介面之後，供需要多 GPU / YAML recipe 的工作使用。

**REFERENCE（研究，不要相依）：**
- distilabel / Bespoke Curator（策展模式）、OpenPipe（capture→distill UX）、
  DSPy / LaMDAgent（代理人提案迴圈）、LLaMA-Factory（recipe 覆蓋度）。

**BUILD（真正的護城河——沒有別人擁有這個）：**
- **軌跡 → Curator(Hermes) → 資料集**的溯源 pipeline（已開始）。
- **密封確定性評估下限 + 真實沙箱評審**（已交付——誠實性差異化）。
- **`train(plan,…)` 後端轉接器接縫** + 跨越 phantom-mesh 的**跨裝置受治理派工**。
- 回饋進 phantom-mesh 的 **skill-publish 迴圈**。

---

## 4. 分階段路徑

- **Phase A（現在 → Tier-2 準備，無 GPU）：**把計畫 schema 鎖定到 PEFT
  `LoraConfig`；定義一個 `Backend` 轉接器介面（`train(plan, dataset) -> adapter_path`），
  附帶一個 no-op/dry-run 實作。便宜、高價值，且讓密封測試維持綠燈。
- **Phase B（Tier-2）：**在該接縫之後實作 **Unsloth** 轉接器
  （選用額外 `phantom-training[unsloth]`），以子行程隔離；在 Mac M 系列目標上做出
  第一個真實 LoRA。加入 **bigcode-eval-harness** 作為選用 gate。
  以真實的 `phantom-mesh serve` HTTP 呼叫取代啟發式 Curator。
- **Phase C（Tier-3）：**代理人驅動的超參數再提案（DSPy/LaMDAgent 風格，
  在評估未過時重新呼叫 CLI）；透過 mesh
  能力派工器，在 governor + flight-recorder 之下做**跨裝置派工**；**skill-publish** 迴圈。
- **Phase D（Post-M3）：**經 **TRL** 做 DPO/偏好；模型登錄 / 版本控管；
  週期性基準測試執行。全部嚴格為選用額外。

---

## 5. 誠實的過度建構警示

- **不要寫訓練器。**SFT/LoRA/QLoRA/GRPO kernel 是個已解決、快速演進的
  領域（Unsloth/Axolotl/TRL/PEFT）。包裝才是整個重點——手刻
  訓練器純粹是負債。
- **不要加 Web UI。**LLaMA-Factory 已擁有零程式碼 UI；phantom-training 的
  價值是*無頭 + 代理人驅動*。UI 活在 phantom-mesh，不在這裡。
- **讓密封下限維持無相依。**公開基準（lm-eval /
  bigcode-eval）與訓練器都必須是**選用額外**，好讓 `pip install -e .` +
  `pytest` 在任何機器上維持無 GPU 且確定性。這是最有
  價值的單一性質——不要使其退化。
- **不要製造合成資料。**護城河是*真實*軌跡溯源 +
  Hermes 成功訊號。distilabel/Curator 是參考模式，不是轉向。
- **不要追逐「支援每個框架」。**一個真正能用的已包裝後端
  （Unsloth）勝過六個半接的（DESIGN.md §5 指出的 secure-connector 陷阱）。
- **不要在 README 過度宣稱。**保留 Tier-1 誠實註記：計畫 ≠ 訓練、
  下限 ≠ 基準。每個新後端都在它真正能端到端執行*之後*才出貨。
- **授權紀律。**Unsloth 的 AGPL 分支必須在它成為硬相依之前
  與 Apache-2.0 立場調和。**[unverified — action item]**

---

## 6. 訓練方法知識庫 × Agent（agent 驅動訓練）

> 為何這對 phantom-training 重要：本專案的利基是**編排 + 來源溯源 + 評估誠實性**這一層，
> 而「一個 agent ＋ 一個訓練方法／recipe 知識庫」正是這一層最自然的形狀——
> agent 提出訓練方案、知識庫供其取用 recipe、phantom 在 governor + 手機核可下治理執行。
> 以下盤點此交集的開源；皆標 **候選方向**，未查證數字標 **[unverified]**。最後一次調查：2026-06-19。

### 6.1 Agent 驅動 / 自主 ML 工程（agent 設計、執行並迭代訓練/實驗）

| 專案 | URL | 星數 | 授權 | 成熟度 | 契合度／落差 |
|---|---|---:|---|---|---|
| **RD-Agent**（Microsoft） | github.com/microsoft/RD-Agent | ~13.5k [unverified] | MIT | 成熟、最活躍（MLE-bench 榜首） | **agent-experiment 迴圈的首要參考。**雙 agent（Researcher 出想法、Developer 依錯誤回饋改 code），會**真的執行**訓練/迭代。**落差：**僅支援 Linux + Docker 的受控環境，重量級平台；與 phantom 的 local-first / 跨裝置 mesh 形狀不同。**REFERENCE 其迴圈設計，勿相依整個平台。** |
| **AIDE**（Weco AI） | github.com/WecoAI/aideml | ~1.3k [unverified] | MIT | 活躍（2025 論文，MLE-bench 開創者） | **最乾淨的 agent-experiment 範式參考。**把 ML 工程化為「程式碼空間樹搜尋」：每份 script 是節點、metric 回饋剪枝。會**真的跑**實驗。輕量、單檔可讀。**落差：**它是樹搜尋 agent，不含治理/溯源/手機核可——正是 phantom 要補的那層。**REFERENCE 樹搜尋提案迴圈。** |
| **ML-Master**（SJTU） | github.com/sjtu-sai-agents/ML-Master | ~431 [unverified] | [unverified — 需查證] | 研究級（MLE-bench 2.0 榜首） | 探索 + 推理整合的 AI-for-AI 框架，會真的跑（需 2TB+ 競賽資料）。**研究參考**；重資料、學術導向，非 solo 落地用。 |
| **AutoML-Agent**（DeepAuto-AI） | github.com/DeepAuto-AI/automl-agent | ~142 [unverified] | **CC BY-NC 4.0** | ICML-25 poster | 多 agent 全管線 AutoML（data/model/prompt/operation）。**⚠️ 非商業授權（CC BY-NC 4.0）——與 phantom-training 的 Apache-2.0 不相容，不可採用為相依或 vendoring。** 僅供概念**參考**，且須隔離。 |
| **MLE-bench**（OpenAI） | github.com/openai/mle-bench | ~1.6k [unverified] | 見 repo [unverified] | 成熟（75 個 Kaggle 競賽） | 衡量 ML agent 工程能力的**基準**（非 agent 本身）。日後若要證明「phantom 治理的 agent 真能跑」，是個**選用對標**；非密封下限路徑。 |
| **MLAgentBench / DS-Agent / Agent-K / AutoKaggle / OpenHands-for-ML** | （各自 repo） | [unverified] | 混雜 [unverified] | 研究／混雜 | 同屬 agentic-ML-engineering 群集；多為 Kaggle 導向或研究原型。**統一視為 REFERENCE 的全景**，逐一查證授權後才談任何採用。 |

### 6.2 訓練方法／recipe 知識庫與登錄（agent 可取用的結構化來源）

| 專案 | URL | 星數 | 授權 | 成熟度 | 契合度／落差 |
|---|---|---:|---|---|---|
| **open-instruct / Tülu recipes**（AllenAI） | github.com/allenai/open-instruct | ~3.8k [unverified] | Apache-2.0 | 成熟（Tülu 3，SFT/DPO/RLVR） | **最高品質的開放後訓練 recipe 集**：`configs/` 內有可重現的訓練設定。**REFERENCE 為 recipe 知識庫的形狀來源**——phantom 的計畫 schema 可對映其 recipe 結構；授權相容（Apache-2.0），可選擇性引用其 config 形狀。 |
| **Axolotl examples / LLaMA-Factory examples** | github.com/axolotl-ai-cloud/axolotl | ~12.1k [unverified] | Apache-2.0 | 成熟 | `examples/` 即一個 YAML recipe zoo（依模型分目錄，full/LoRA/QLoRA/multi-GPU）。已在 §2.1 列為後端候選；此處補一個角色：**作為 recipe 覆蓋度的知識來源**，agent 可據以挑 recipe。**REFERENCE 其 recipe 編目，勿吞下整個工具。** |
| **HF AutoTrain / W&B・MLflow registry** | huggingface.co/autotrain | n/a | 各異 | 成熟 SaaS／平台 | model/training registry 的形狀參考。**⚠️ 勿重建 registry 平台**；phantom 的「登錄」應極薄，附在 skill-publish 迴圈上即可（§3 BUILD）。 |

### 6.3 Agentic 資料策展 / 合成資料管線（資料策略接縫）

| 專案 | URL | 星數 | 授權 | 成熟度 | 契合度／落差 |
|---|---|---:|---|---|---|
| **distilabel**（Argilla） | github.com/argilla-io/distilabel | ~3.3k [unverified] | Apache-2.0 | 活躍 | 合成資料 + AI 回饋的 agentic pipeline。**僅在日後真需要合成資料時 WRAP。⚠️ phantom 的護城河是*真實軌跡*，不是合成——大量採用會稀釋利基。** |
| **Bespoke Curator** | github.com/bespokelabsai/curator | ~1.7k [unverified] | Apache-2.0 | 成熟中 | 後訓練的批次推論 + 結構化策展。**策展步驟擴展的 REFERENCE**；現有 Hermes Curator 訊號才是護城河，保留它。 |
| **Data-Juicer / Argilla** | github.com/modelscope/data-juicer | [unverified] | Apache-2.0 [unverified] | 成熟 | 大規模資料運算子 / 人工策展 UI。**REFERENCE 運算子目錄**；非轉向。 |

### 6.4 最佳化即 agent（hyperparam / 架構搜尋）

| 專案 | URL | 星數 | 授權 | 成熟度 | 契合度／落差 |
|---|---|---:|---|---|---|
| **DSPy**（Stanford） | github.com/stanfordnlp/dspy | ~20k+ [unverified] | MIT | 成熟 | 調的是 prompt/few-shot，非權重。已在 §2.5 列為 Tier-3 agent 提案迴圈的參考；此處重申：**REFERENCE 其 optimizer 抽象**，作為「agent 提案訓練超參」的設計樣板。 |
| **Optuna** | github.com/optuna/optuna | [unverified] | MIT | 成熟 | HPO 框架（TPE/random）；DSPy 可呼叫之。**Tier-3 的 ADOPT 候選**：當 agent 提案 `lora_rank/lr/epochs` 失敗時，以 Optuna 做底層搜尋，agent 僅負責提案 + 治理閘。授權相容。 |
| **Ray Tune** | github.com/ray-project/ray | [unverified] | Apache-2.0 | 成熟 | 分散式 HPO 執行。**僅在跨裝置搜尋真的需要時 REFERENCE**；對 solo mesh 多半過重，Optuna + mesh 派工已足。 |

### 對 phantom-training 的方向

最大的方向洞見：**phantom-training 可定位為「受治理的 recipe 知識庫 + 一個提案訓練執行的 agent」**——
agent 從知識庫（open-instruct/axolotl recipe 形狀）取材、提出一次訓練方案，方案由
**governor + 手機核可**閘控後才在擁有 GPU 的 mesh 節點執行，全程進 flight-recorder。
這正落在 §1 利基（編排 + 溯源 + 評估誠實性）上，且沒有任何上述專案同時具備治理 + 真實軌跡 + 跨裝置這三點。

具體呼叫（皆為 **候選方向**）：

- **REFERENCE（研究，不相依）：** RD-Agent / AIDE 的 agent-experiment 迴圈（樹搜尋 / Researcher-Developer 雙 agent）
  作為 Tier-3 提案迴圈的設計樣板；open-instruct / axolotl `examples/` 作為 recipe 知識庫的**結構來源**；
  ML-Master / MLAgentBench 群集作為全景，逐一查證授權後才談採用。
- **ADOPT（授權相容、Tier-3）：** **Optuna**（MIT）作為 agent 提案失敗時的底層 HPO，agent 只負責提案 + 治理閘，
  不自建搜尋器。
- **WRAP（僅在必要時，薄轉接器）：** **distilabel**（Apache-2.0）——*只有*當真的需要合成資料補強時，
  且須明確標示「非真實軌跡」以保護溯源誠實性。
- **BUILD（護城河，沒有別人有）：** 把上述拼成 **「受治理的 recipe-KB + 提案 agent」**——
  agent 提案 → governor/手機核可閘 → mesh GPU 節點執行 → flight-recorder 溯源 → 評估下限/真實評審把關 →
  skill-publish。這是 §1-§3 已點名的接縫的自然延伸，非新平台。

**過度建構 / 倫理警示：**

- **不要重建 AutoML 平台或 ML-engineering agent。** RD-Agent/AIDE 已是成熟研究線；phantom 的價值是**治理 + 溯源那層**，
  不是再寫一個樹搜尋器。重建 = 純負債。
- **授權紀律（硬閘）：** **AutoML-Agent 為 CC BY-NC 4.0（非商業），與 Apache-2.0 不相容——絕不採用為相依或 vendoring。**
  ML-Master / MLAgentBench 等授權**未查證**，採用前一律先查 LICENSE，GPL/AGPL/NC 皆視為汙染。
- **agent 自主訓練必須受閘。** 任何「agent 提案並執行訓練」都必須走 governor + 手機核可 + flight-recorder——
  這正是與所有純 agent-ML 框架的差異點，**不可為了自動化而拿掉**。
- **守住評估誠實性。** agent 提案迴圈的成功判準必須走密封下限 / 真實沙箱評審，不可讓 agent 自評自賣（self-grade）。
- **合成資料不是轉向。** 護城河是真實軌跡溯源；distilabel 僅為條件式工具，預設不啟用。
- **登錄要極薄。** 不要重建 W&B/MLflow 式 registry 平台；登錄掛在既有 skill-publish 迴圈上即可。

---

*作者：phantom-training 方向筆記，依據 ROADMAP.md + 2026 年 6 月 OSS
調查。星數 / 版本號為時間點快照，將會飄移。*
