# Final Narrative Fact Contract

## 目的

最終解讀層不能直接依賴上游已經寫好的句子。`FinalNarrativeFactContract v3` 在既有
`SectionNarrativeSpec` 之外建立 fact-only boundary，把「這一頁有哪些可用事實」和
「最後怎麼寫成繁體中文」完全分開。

資料流如下：

```text
KB / calculation / relationship case model
  -> SectionNarrativeSpec（頁面 ownership 與 evidence）
  -> FinalNarrativeFactContract（stable facts only）
  -> locked fact-only section renderer
  -> visible Traditional Chinese copy
```

## Contract 規則

每個 fact 只能包含：

- `id`：穩定 ASCII 識別碼
- `sectionId`：擁有這個 fact 的頁面
- `role`：頁面內的語意角色
- `valueKey`：穩定的分類或訊號 ID
- `sourceSlot`：來源 semantic slot 名稱
- `sourceBindingFingerprint`：把 role、value、qualifiers 和當前來源 slot 值綁在一起
- `evidenceIds`：該頁擁有的 evidence IDs
- `qualifiers`：方向、強度或狀態等結構化修飾

Fact 內禁止出現 `headline`、`body`、`meaning`、`summary`、`advice`、
`text` 等 reader-facing prose 欄位。

## 頁面 Ownership

| Section | 必要 fact roles |
| --- | --- |
| `chart-positioning` | user emotional need, user communication style, partner pressure response, precision mode |
| `relationship-fit` | archetype, primary dynamic, optional secondary dynamic, attraction, friction, growth |
| `core-answer` | question, relationship stage, contact status, answer track, central dynamic, partner relationship need, evidence signal, observable sign, uncertainty |
| `timing-reading` | question, contact status, timing posture, recommended action, timing band, contact posture, date precision |
| `action-direction` | question, contact status, action mode, repair lever, stop condition, contact posture, blocked action |

Fact 不能引用其他頁面的 evidence，也不能把 global storyline 當成所有頁面的共同內容。

## Source Fingerprint

每一頁的 fact contract 都保存 `sourceSpecFingerprint`，每個 fact 另外保存
`sourceBindingFingerprint`。只要 semantic slots、context、concept keys、evidence identity，
或 fact 自己的 role/value/qualifiers 改變，舊 fact contract 就不能進入 composer。

Runtime 最後會執行 deterministic public-copy normalization。Normalization 完成後必須重新
計算 fingerprint；facts 本身不能被改寫。

## Unknown Diagnostics

未知值不能默默變成具體星盤解讀。所有 `unknown`、`unresolved` 或
`not-calculated` fact 都必須列入 `diagnostics.unknownFactIds`。Renderer 必須根據這個
diagnostic 降級內容，不能使用看似個人化的通用句子。

## Fact-Only Mode

目前 renderer mode 已鎖定為：

```text
fact-only
```

五個 visible sections 都只由 fact IDs、`valueKey` 和 qualifiers 生成。Question、stage、contact
等 routing context 必須先變成該頁擁有的 typed facts，renderer 不接受額外 side channel。
`compatibilityProseSlots` 必須永遠是空陣列。上游 legacy prose 即使被整批改寫，也不能改變
任何 reader-facing output。

`verify_final_narrative_phase2_fact_only.py` 會對 11 組代表性 reading 改寫所有 legacy prose，
重新計算來源 fingerprint，並驗證 55 個 visible sections 完全不變。這是防止未來內容更新
重新污染最終文字層的主要 isolation gate。

## 驗證

```bash
.venv/bin/python scripts/smoke_final_narrative_fact_contract.py
.venv/bin/python scripts/verify_final_narrative_phase2_fact_only.py
.venv/bin/python scripts/verify_final_narrative_phase2_page_modules.py
.venv/bin/python scripts/verify_final_narrative_phase3_realization.py
.venv/bin/python scripts/verify_final_narrative_phase4_semantic_coverage.py
.venv/bin/python scripts/verify_final_narrative_phase5_composition.py
.venv/bin/python scripts/verify_final_narrative_phase6_test_engine.py
.venv/bin/python scripts/verify_reading_phase7_calibration.py
.venv/bin/python scripts/smoke_section_narrative_phase2.py
.venv/bin/python scripts/audit_final_narrative_production_readiness.py \
  --corpus data/reading-production-calibration/v2/holdout-corpus.json \
  --contract data/reading-quality-cases/final-layer-production-contract-v3.json \
  --no-write
```

任何 visible prose fact、unowned evidence、stale source fingerprint 或缺少必要 role 都必須
在 reader copy 生成前失敗。
