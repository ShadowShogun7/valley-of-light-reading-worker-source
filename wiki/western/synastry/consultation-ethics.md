---
id: western-consultation-ethics
title: 關係諮詢護欄
title_en: Relationship Consultation Guardrails
category: western/synastry
type: concept

source_primary: "Synastry: Understanding the Astrology of Relationships"
source_chapter: Counseling and Consultations
source_secondary:
  - Astrological Relationship Handbook
  - OPA ethics

confidence: INTERPRETATION

related:
  - western-synastry-method-order
  - western-synastry-method
  - western-synastry-relationship-framework
  - western-precision-birth-data-quality
links:
  - target: western-synastry-method-order
    type: cautions
    reason: 方法順序需要搭配資訊選擇與倫理邊界。
  - target: western-synastry-method
    type: supports
    reason: 不解讀全部資訊與不單點斷語是一組方法護欄。
  - target: western-synastry-relationship-framework
    type: contextualizes
    reason: 關係閱讀要服務當事人的理解，而不是替第三方下判決。
  - target: western-precision-birth-data-quality
    type: cautions
    reason: 隱私與資料精度都影響可說內容。

applicable_products:
  - relationship_compatibility
relationship_stage:
  - all
question_relevance:
  - still-love-me
  - any-chance
  - when-to-contact
  - what-did-i-do-wrong
  - stay-or-let-go

variants:
  - core
  - in_relationship
  - in_breakup

created_at: 2026-05-26
updated_at: 2026-05-26
last_reviewed: 2026-05-26
status: published
---

# 關係諮詢護欄

## core

Suskin 將 synastry consultation 視為比一般本命諮詢更敏感的場景，因為它涉及兩個人的資料、隱私、期待與情緒。Valley 的 runtime 應把 `consultationSafety` 做成獨立 cluster：選擇準確、相關、有用、急迫的資訊，而不是把所有星盤細節都輸出。(claims: western-consultation-ethics-001, western-consultation-ethics-002)

這個護欄也支持 LLM 邊界：不要替未在場的對方編造內心、不要把第三方資料寫成確定心理診斷、不要在高情緒風險時鼓勵追問或越界聯絡。當問題是「他心裡還有我嗎」，答案必須寫成星盤證據、互動傾向與使用者可守住的邊界，不可寫成對方的私人告白或確定內心。現實情境可以改變行動尺度與安全邊界，但不能取代合盤、行運或本命證據來製造占星結論；runtime 必須把這個限制作為可檢查的 evidence boundary 輸出。(claims: western-consultation-ethics-001, western-consultation-ethics-004, western-consultation-ethics-006, western-consultation-ethics-007)

## in_relationship

關係仍在進行時，諮詢護欄要求系統把焦點放在可改善互動的資訊：什麼準確、什麼相關、什麼對使用者最有用、什麼最急迫。這比把所有相位列出來更符合產品安全。(claims: western-consultation-ethics-002)

### 優勢

- 支援 evidence reducer 的選擇邏輯。(claims: western-consultation-ethics-002)
- 支援 privacy 與 third-party interpretation 邊界。(claims: western-consultation-ethics-001)

### 弱點

- 護欄本身不能提供占星結論，只能限制與排序。(claims: western-consultation-ethics-002)
- 法律/隱私語境會因地區不同而不同，產品應使用保守安全語言。(claims: western-consultation-ethics-001)

## in_breakup

分手或斷聯使用者容易處於高情緒風險。`consultationSafety` 應在答案中降低絕對預測、降低追問建議，並把「你該如何保護自己」放進語氣控制。行動建議只能呈現有條件的選項與邊界，不可用恐懼、命定或確定性逼使用者等待、追問、聯絡或切斷。(claims: western-consultation-ethics-003, western-consultation-ethics-005)

## Claims

### western-consultation-ethics-001

**Claim:** Synastry 涉及隱私與第三方資料，產品應避免替未在場者作過度私密或確定性判斷。

**Source quote:**
> From Suskin `Synastry`:
> "The Right to Privacy"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:9401-9445

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 將 relationship analysis 中一方帶來另一方資料列為 privacy issue；產品應把對方心理描述保持為 chart-based pattern，不寫成確定內心。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-consultation-ethics-002

**Claim:** 關係閱讀必須選擇準確、相關、有用、急迫的資訊，而不是解讀全部星盤資料。

**Source quote:**
> From Suskin `Synastry`:
> "accurate and relevant"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:9636-9663

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 說 relationship reading 資訊量更大，需要判斷哪些資訊準確、相關、有用、急迫，這正是 reducer/blueprint 的依據。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-consultation-ethics-003

**Claim:** 關係閱讀需要額外準備，因為 charts 與互動資訊太多，必須預先決定重要內容。

**Source quote:**
> From Suskin `Synastry`:
> "too many charts"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:9611-9630

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 說 relationship readings 因為圖太多而需要額外準備，支持 Valley 以 case file + reducer 預先選出 evidence，而不是讓 LLM 臨場組合。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-consultation-ethics-004

**Claim:** 第三方或未在場者問題必須以證據與互動傾向回答，不可把推論寫成對方的確定內心、私人告白或心理診斷。

**Source quote:**
> From `OPA ethics`:
> "not exact inner state"

**Source location:** raw/cross/opa-ethics-source-note.txt:7-10

**Confidence:** INTERPRETATION

**Reasoning:** OPA 的第三方與 absent-person 邊界支持把「他是否還愛」寫成 client-centered evidence，而不是替未在場者說出確定心理事實。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-consultation-ethics-005

**Claim:** 行動、時機與 don't 建議必須保留使用者自主性，以有條件的選項與安全邊界呈現，不可使用恐懼、命定或絕對預測來催促行動。

**Source quote:**
> From `OPA ethics`:
> "frame recommendations as bounded options"

**Source location:** raw/cross/opa-ethics-source-note.txt:12-15

**Confidence:** INTERPRETATION

**Reasoning:** OPA 的 client welfare、autonomy 與 probability language 支持 Valley 將行動建議寫成可選擇的方向，而不是命令、威脅或命定結論。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-consultation-ethics-006

**Claim:** 關係階段、聯絡狀態、使用者想要的結果與情緒風險只能修正行動尺度、答案框架與安全邊界，不能在沒有星盤證據時創造合盤、行運或相容性結論。

**Source quote:**
> From `OPA ethics`:
> "cannot create synastry, transit, or compatibility conclusions"

**Source location:** raw/cross/opa-ethics-source-note.txt:37-40

**Confidence:** INTERPRETATION

**Reasoning:** OPA ethics can shape consultation boundaries and client welfare, but it is not a calculation method. Valley should keep context as a modifier, not an evidence substitute.

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-consultation-ethics-007

**Claim:** Runtime 必須明確輸出 context evidence boundary：關係階段、聯絡狀態、想要的結果與情緒風險只能作為行動、框架與語氣修正，不能滿足合盤結論、時機行動、相容性判斷或第三方內心判斷的證據要求。

**Source quote:**
> From `OPA ethics`:
> "they do not provide chart calculation facts"

**Source location:** raw/cross/opa-ethics-source-note.txt:52-55

**Confidence:** INTERPRETATION

**Reasoning:** OPA ethics support consultation boundaries and client welfare, but do not calculate chart facts. The product therefore needs a machine-readable boundary object so context cannot be reused as astrology evidence in result rendering or LLM prompting.

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

## 典籍出處

### 原文引用
> From Suskin `Synastry`:
> "accurate and relevant"

## 與其他文章的連結

- [[western-synastry-method-order]] — 護欄建立在正確方法順序上。
- [[western-synastry-method]] — 既有不單點斷語護欄。

## Source Extraction Log

- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:9401-9445 → supports `western-consultation-ethics-001`
- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:9636-9663 → supports `western-consultation-ethics-002`
- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:9611-9630 → supports `western-consultation-ethics-003`
- raw/cross/opa-ethics-source-note.txt:7-10; raw/cross/opa-ethics-source-note.txt:17-20 → supports `western-consultation-ethics-004`
- raw/cross/opa-ethics-source-note.txt:12-15; raw/cross/opa-ethics-source-note.txt:22-25 → supports `western-consultation-ethics-005`
- raw/cross/opa-ethics-source-note.txt:37-40 → supports `western-consultation-ethics-006`
- raw/cross/opa-ethics-source-note.txt:52-55 → supports `western-consultation-ethics-007`
