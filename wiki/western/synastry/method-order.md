---
id: western-synastry-method-order
title: 合盤方法順序
title_en: Synastry Method Order
category: western/synastry
type: concept

source_primary: "Synastry: Understanding the Astrology of Relationships"
source_chapter: "Introduction: What Is Synastry?"
source_secondary:
  - Astrological Relationship Handbook
  - Synastry

confidence: INTERPRETATION

related:
  - western-synastry-relationship-framework
  - western-natal-relationship-potential
  - western-interchart-aspect-priorities
  - western-relationship-chart-layer
  - western-consultation-ethics
links:
  - target: western-synastry-relationship-framework
    type: supports
    reason: Suskin 的方法順序補強 Burk 的「先看個人，再看兩張盤互動」框架。
  - target: western-natal-relationship-potential
    type: requires
    reason: 方法順序第一步是本命關係潛力。
  - target: western-interchart-aspect-priorities
    type: requires
    reason: 完成本命與初步比較後，才進入兩張盤交互相位。
  - target: western-relationship-chart-layer
    type: contextualizes
    reason: 關係盤與 longevity 屬於後段與付費深度層。
  - target: western-consultation-ethics
    type: cautions
    reason: 關係占星需要選擇資訊與諮詢安全邊界。

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

# 合盤方法順序

## core

Rod Suskin 的方法順序適合作為 Valley 西洋關係 runtime 的主幹：先分析兩個人的本命盤與關係需求，再分析兩個人基於本命盤如何互動，接著進入兩張盤的交互相位，最後才處理關係盤、long-term potential 與 timing。(claims: western-synastry-method-order-001, western-synastry-method-order-002)

這個順序會防止產品直接從使用者問題跳到「他會不會回來」。免費頁應先組裝 `westernRelationshipCaseFile`，再用 reducer 回答問題；LLM 只負責把已選證據寫成人話。(claims: western-synastry-method-order-001)

## in_relationship

關係仍在進行時，方法順序應先回答：雙方各自需要什麼、彼此日常互動風格如何、交互相位會把哪些需求放大。這比直接說「合」或「不合」更可操作。(claims: western-synastry-method-order-001)

### 優勢

- 支援 deterministic selector：先本命，再比較，再合盤，再 timing。(claims: western-synastry-method-order-001)
- 讓問題回答成為結論，而不是預設文案。(claims: western-synastry-method-order-002)

### 弱點

- Suskin 是現代實務方法，應標為 `INTERPRETATION`，不可寫成唯一教條。(claims: western-synastry-method-order-001)
- 關係盤與 longevity 層需要更多計算支援，不能在免費 V0 假裝完成。(claims: western-synastry-method-order-002)

## in_breakup

分手、冷戰或斷聯情境中，這個方法順序尤其重要。使用者雖然常問「他還愛不愛」「有沒有機會」，但系統應先判斷個人需求、壓力、互動與 timing 條件，最後才給條件式答案。(claims: western-synastry-method-order-001, western-synastry-method-order-002)

## Claims

### western-synastry-method-order-001

**Claim:** 西洋關係分析應先看本命關係需求，再看兩個人如何互動，之後才進入完整 chart-to-chart synastry。

**Source quote:**
> From Suskin `Synastry`:
> "First, analyze the natal chart thoroughly"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:276-291

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 明確列出 relationship analysis 的 basic strategy，第一步是本命盤，第二步才是基於本命盤分析互動，第三步才是兩張盤互動。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-synastry-method-order-002

**Claim:** 關係盤與 longevity/timing 層應放在本命與合盤之後，不應成為免費頁第一層答案。

**Source quote:**
> From Suskin `Synastry`:
> "Follow with an analysis of charts"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:290-297

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 將 relationship charts 與 longevity 放在完整 chart interaction 之後，支持 Valley 把 composite/Davison/timing 作為後段或 paid-depth 層。

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
> "First, analyze the natal chart thoroughly"

## 與其他文章的連結

- [[western-natal-relationship-potential]] — 方法順序第一層。
- [[western-interchart-aspect-priorities]] — 方法順序第三層。
- [[western-relationship-chart-layer]] — 後段 relationship chart / paid-depth 層。

## Source Extraction Log

- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:276-291 → supports `western-synastry-method-order-001`
- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:290-297 → supports `western-synastry-method-order-002`
