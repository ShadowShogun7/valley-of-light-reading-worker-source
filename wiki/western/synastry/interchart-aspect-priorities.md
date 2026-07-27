---
id: western-interchart-aspect-priorities
title: 交互相位優先序
title_en: Interchart Aspect Priorities
category: western/synastry
type: concept

source_primary: "Synastry: Understanding the Astrology of Relationships"
source_chapter: Basic Chart Comparison / Planets in Aspect in Synastry
source_secondary:
  - Synastry
  - Astrological Relationship Handbook
  - Skymates

confidence: INTERPRETATION

related:
  - western-synastry-method-order
  - western-initial-comparison-elements
  - western-synastry-evidence-clusters
  - western-synastry-method
links:
  - target: western-synastry-method-order
    type: requires
    reason: 交互相位應在本命與初步比較之後。
  - target: western-initial-comparison-elements
    type: contextualizes
    reason: 元素比較提供背景，交互相位提供具體互動證據。
  - target: western-synastry-evidence-clusters
    type: supports
    reason: 現有 attraction/safety/pressure/communication/repair clusters 需要更清楚的優先序。
  - target: western-synastry-method
    type: supports
    reason: 優先序補強既有合盤方法護欄。

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

# 交互相位優先序

## core

Suskin 將 synastry 描述為使用本命占星工具的 chart comparison：看一方行星落入另一方盤的位置，並測量兩張盤之間的相位。這支持 Valley 的 backend 將 interchart aspects 作為結構化證據，而不是讓 LLM 自行搜尋文章。(claims: western-interchart-aspect-priorities-001)

交互相位需要優先序。不是所有相位都同等重要；系統應先選關係問題最相關的 pair family、orb、directionality 與 contact type，再交給 reducer。(claims: western-interchart-aspect-priorities-002, western-interchart-aspect-priorities-004)

Skymates 進一步補強「不要列完整相位表」的方法：先重視兩張本命盤中突出的行星，再依 contact type 的強度順序縮小範圍；當資訊開始讓解讀失焦時，應減少 interaspects、收緊 orb，只保留真正能解釋關係問題的 pivotal contacts。(claims: western-interchart-aspect-priorities-005, western-interchart-aspect-priorities-006)

## in_relationship

關係仍在進行時，優先看 luminaries、Venus/Mars、Mercury、Saturn 以及 Moon/Venus/Mars 的情緒與行動觸發。方向性也重要：A 的行星觸發 B 的某個點，和 B 的行星觸發 A 的同一點，產品語言不能寫成完全相同。(claims: western-interchart-aspect-priorities-001, western-interchart-aspect-priorities-002)

### 優勢

- 支援 aspectPriority cluster 選出最 relevant 的相位。(claims: western-interchart-aspect-priorities-004)
- 支援 synastry orb policy，避免過寬相位污染免費頁。(claims: western-interchart-aspect-priorities-003)
- 支援 result card 只展示 3-4 個 pivotal contacts，不把所有合盤相位塞進使用者頁面。(claims: western-interchart-aspect-priorities-005, western-interchart-aspect-priorities-006)

### 弱點

- 房位 overlay 需要可靠出生時間與地點，免費 V0 只能 precision-gate。(claims: western-interchart-aspect-priorities-001)
- 優先序仍是方法選擇，應標 `INTERPRETATION`。(claims: western-interchart-aspect-priorities-004)

## in_breakup

分手情境中，優先序可以避免「看到很多相位就什麼都寫」。免費頁應只展示最能回答問題的 few evidence items：牽動、情緒安全、壓力、溝通與修復入口。(claims: western-interchart-aspect-priorities-004)

## Claims

### western-interchart-aspect-priorities-001

**Claim:** Synastry 的基本比較方法是看行星落入對方盤的位置，以及兩張盤之間的相位。

**Source quote:**
> From Suskin `Synastry`:
> "two basic principles"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:3416-3435

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 說明 chart comparison 的兩個基本原則，支持 Valley 將 house overlay 與 interchart aspects 分層處理。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-interchart-aspect-priorities-002

**Claim:** Interchart aspect 具有方向性；A 的月亮對 B 的太陽，和 A 的太陽對 B 的月亮不是同一件事。

**Source quote:**
> From Suskin `Synastry`:
> "an altogether different situation"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:3713-3739

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 說明 synastry grid 與 natal aspectarian 不同，跨盤相位方向不同時意義也不同；這支持保留 personAPoint/personBPoint。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-interchart-aspect-priorities-003

**Claim:** Synastry orb 通常應比 natal orb 更保守，免費頁應優先採用較緊密相位。

**Source quote:**
> From Suskin `Synastry`:
> "half the orb"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:3741-3748

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 提到 synastry 常使用 natal orb 的一半，支持 aspectPriority cluster 將 tight orb 作為排序條件。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-interchart-aspect-priorities-004

**Claim:** 關係閱讀需要建立相位與行星 pair 的優先序，而不是試圖解讀全部資訊。

**Source quote:**
> From Suskin `Synastry`:
> "establish a set of priorities"

**Source location:** raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:3759-3769

**Confidence:** INTERPRETATION

**Reasoning:** Suskin 提醒過多資訊不能幫助 client 清楚理解，因此產品應選出最 relevant 的 pair families 與 reducer evidence。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-interchart-aspect-priorities-005

**Claim:** Pivotal interaspect selection should prioritize prominent natal planets and stronger contact types before weaker background contacts.

**Source quote:**
> From `Skymates`:
> "conjunctions first"

**Source location:** raw/western/739983674-Steven-Forrest-Skymates-Steven-Forrest-Jodie-Forrest-Z-Library.txt:9635-9644

**Confidence:** INTERPRETATION

**Reasoning:** Skymates gives a practical priority rule: prominent natal planets matter more, then contact types are considered in descending importance. Product use should preserve major luminaries/personal planets and stronger contact types before weaker background contacts.

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-interchart-aspect-priorities-006

**Claim:** The visible result should reduce the number of interaspects and tighten orbs rather than display an aspect dump.

**Source quote:**
> From `Skymates`:
> "truly pivotal interaspects"

**Source location:** raw/western/739983674-Steven-Forrest-Skymates-Steven-Forrest-Jodie-Forrest-Z-Library.txt:9652-9667

**Confidence:** INTERPRETATION

**Reasoning:** Skymates explicitly recommends reducing the interaspects being used and narrowing orbs when the reading becomes strained. Product use should cap visible aspect rows and show only the strongest contacts that explain the question.

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
> "establish a set of priorities"

### Supporting quote
> From `Skymates`:
> "truly pivotal interaspects"

## 與其他文章的連結

- [[western-synastry-evidence-clusters]] — 現有 evidence cluster 分類。
- [[western-synastry-method]] — 既有合盤方法護欄。

## Source Extraction Log

- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:3416-3435 → supports `western-interchart-aspect-priorities-001`
- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:3713-3739 → supports `western-interchart-aspect-priorities-002`
- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:3741-3748 → supports `western-interchart-aspect-priorities-003`
- raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt:3759-3769 → supports `western-interchart-aspect-priorities-004`
- raw/western/739983674-Steven-Forrest-Skymates-Steven-Forrest-Jodie-Forrest-Z-Library.txt:9635-9644 → supports `western-interchart-aspect-priorities-005`
- raw/western/739983674-Steven-Forrest-Skymates-Steven-Forrest-Jodie-Forrest-Z-Library.txt:9652-9667 → supports `western-interchart-aspect-priorities-006`
