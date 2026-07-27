# Final Narrative Fact Renderer

## 目的

`FinalNarrativeFactRenderer` 是五個付費結果頁共用的最後一道可讀文字邊界。它只接收已驗證的
`FinalNarrativeFactContract`，不讀取上游 headline、body、summary、advice 或 global storyline
prose。新增 KB、規則或 case-model 資料時，內容會透過新的 facts 進入這一層，但不能直接把
技術句子帶到使用者畫面。

Facade 只負責共用字典、句子組合工具和 dispatch。五頁各有獨立 module：
`final_narrative_pages/chart_positioning_renderer.py`、`relationship_fit_renderer.py`、
`core_answer_renderer.py`、`timing_renderer.py`、`action_direction_renderer.py`。Page renderer
的唯一語意輸入是該頁擁有的 typed facts；不接受 global storyline、上游 prose 或其他頁的
context side channel。

## 頁面責任

| Section | 只回答 |
| --- | --- |
| `chart-positioning` | 兩人的情感需要、溝通習慣和壓力反應 |
| `relationship-fit` | 基礎關係型態、吸引、摩擦和可調整位置 |
| `core-answer` | 使用者所選問題的直接答案與可觀察證據 |
| `timing-reading` | 目前是否適合靠近，以及可用的時間區間 |
| `action-direction` | 只做哪一步、避免什麼、何時停止 |

Global storyline 只能協助上游選擇 facts，不能成為五頁共同段落。每頁 renderer 只能讀取該頁
擁有的 facts；跨頁 evidence、未驗證 prose 和 compatibility slots 都會在生成前失敗。

## 文字規則

- 使用自然繁體中文，優先描述看得見的行動，例如是否回覆、是否主動延續、是否做到約定。
- 一個句子只承擔一個主要判斷；production contract 上限為 70 字。
- 不顯示內部標籤、頁面說明、下一頁預告或「這裡只看」類 meta narration。
- 不把單次回覆、單一星盤線索或較順時段寫成承諾、復合或心意證明。
- 不使用「穩定投入」「互動意願」「現實訊號」「觀察條件」「反應模式」等分析者語彙。
- 聯絡被封鎖、拒絕或有安全風險時，界線優先於任何時機建議。

## 可控變化

Renderer 依據頁面目的明確選擇 direct、situational 或 relational 完整句型，再以該頁擁有的
question、status、contact 或 semantic value 做可重現的 context selection，不使用隨機數或雜湊尾句。
相同 facts 永遠得到相同輸出；變化只能改寫表達方式，不得創造 contract 沒有提供的新判斷。

Core answer 使用 25 組 question x contact families，每組都有 direct、situational、relational 三個
完整句型；relationship stage 只負責選型，不再把 stage、contact 和 question 三段獨立子句串成
一個長句。Relationship-fit 的 known secondary dynamic 必須成為該頁第三個可讀句，不能只當作
選字 index；超過一個 secondary dynamic 會直接失敗。

Action repair 依 `repair-lever` 使用獨立 base-sentence families，再搭配不重疊的 meaning、repair、
next-step 和 stop-condition suffix banks。這避免所有 action pages 只是把同一句話換尾巴。

## Semantic Coverage

`final_narrative_semantic_coverage.py` 是 Phase 4 的 registry。Contract policy 發出的每一個 role
都必須被分類為 reader language、composition control、routing control 或 safety control。
Reader-language role 必須由所屬頁面的 `SectionFactReader` 明確讀取；未知 role、未知有限值、
未讀取 fact 或 stale source binding 都會直接失敗，不能靜默落到通用句。

## Release Gates

```bash
.venv/bin/python scripts/verify_final_narrative_phase2_fact_only.py
.venv/bin/python scripts/verify_final_narrative_phase2_page_modules.py
.venv/bin/python scripts/verify_final_narrative_phase3_realization.py
.venv/bin/python scripts/verify_final_narrative_phase4_semantic_coverage.py
.venv/bin/python scripts/verify_final_narrative_phase5_composition.py
.venv/bin/python scripts/verify_final_narrative_phase6_test_engine.py
.venv/bin/python scripts/verify_reading_phase7_calibration.py
.venv/bin/python scripts/audit_final_narrative_production_readiness.py \
  --corpus data/reading-production-calibration/v2/holdout-corpus.json \
  --contract data/reading-quality-cases/final-layer-production-contract-v3.json \
  --no-write
```

Production gate 同時要求：500 組 status x question x contact x emotional-risk matrix 完整、125 組
one-input comparisons 全部符合 ownership、visible output 全部唯一、已知壞句為零、
抽象語彙為零、頁面 meta narration 為零、超過 70 字的句子為零，以及任何相同完整句子不能
覆蓋超過該頁 10% 的不同 semantic inputs。

Phase 2-7 automated gates 已經完成。Phase 5 在 `render_all()` 邊界檢查欄位責任、句長、頁內重複、
跨頁完整句重複與跨頁相似度；Phase 6 檢查 meaning ownership、invalid cases 和 semantic collapse；
Phase 7 鎖定 split corpus、分布上限與 coverage-driven review queue。任一違規都不能進入可見結果。
Phase 8 human acceptance 仍待真人評分易讀程度、星盤具體度和頁面主題聚焦。
