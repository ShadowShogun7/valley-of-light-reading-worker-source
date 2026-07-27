---
id: western-precision-birth-data-quality
title: 出生資料精度
title_en: Birth Data Quality
category: western/precision
type: concept

source_primary: Planets in Transit
source_chapter: Introductory Notes / Transit Calculation
source_secondary:
  - Planets in Composite
  - Synastry

confidence: INTERPRETATION

related:
  - western-planets-natal-relationship-needs
  - western-synastry-relationship-framework
  - western-transits-timing-window
  - western-synastry-evidence-clusters
links:
  - target: western-planets-natal-relationship-needs
    type: cautions
    reason: 本命需求中的 Moon、Desc 與宮位必須受出生時間與地點精度限制。
  - target: western-synastry-relationship-framework
    type: requires
    reason: 精度護欄是關係占星框架的一部分，避免報告發明角度點或宮位事實。
  - target: western-transits-timing-window
    type: timing
    reason: timing 精度需要知道哪些行運可用、哪些涉及 Moon 或角度點。
  - target: western-synastry-evidence-clusters
    type: supports
    reason: evidence clusters 需要知道哪些證據可展示、降權或封鎖。

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
  - in_general

created_at: 2026-05-25
updated_at: 2026-05-25
last_reviewed: 2026-05-25
status: published
---

# 出生資料精度

## core

出生城市不應是免費閱讀的硬阻擋：只要生日足夠，行星星座與多數合盤相位仍可計算。但精準出生時間與地點會影響角度點、宮位與部分 timing，因此產品必須把 city 寫成「提高精度」，不是「沒有就不能讀」。(claims: western-precision-birth-data-quality-001)

如果時間不夠準，宮位不能硬算。Hand 在 transit 範例中明確指出時間不夠準不足以支持 house cusps；這直接支持 Valley 的 gate：缺出生時間時，Asc、Desc、house overlays 應封鎖或不展示，Moon 相關證據則降權。(claims: western-precision-birth-data-quality-002)

地點也會影響宮位與角度點。Composite 方法中，house cusps 需要使用關係發生地或居住地的緯度，這支持產品在缺城市或無可靠座標時，不輸出 house / overlay 結論。(claims: western-precision-birth-data-quality-003)

## in_relationship

關係中，如果雙方資料完整，報告可以使用本命需求、合盤相位、timing climate 與後續宮位/overlay 層。若缺城市或時間，免費頁仍可讀核心相位，但必須在 case file 中標記 `location_fallback` 或 `date_only`，並阻擋角度點與宮位說法。(claims: western-precision-birth-data-quality-001, western-precision-birth-data-quality-002, western-precision-birth-data-quality-003)

### 優勢

- 保留低摩擦填表體驗，出生城市可選填。(claims: western-precision-birth-data-quality-001)
- 防止報告在資料不足時發明 Asc、Desc、house overlay 或精準 timing。(claims: western-precision-birth-data-quality-002)

### 弱點

- 精度護欄會讓部分高吸引力文案不能展示。(claims: western-precision-birth-data-quality-002)
- 若 UI 沒說清楚 city 是提高精度，用戶可能以為缺城市代表不能算。(claims: western-precision-birth-data-quality-001)

## in_breakup

分手與冷戰場景最容易要求精準 timing 和對方內心。若出生時間或城市不足，報告應把 certainty 降低：可以說關係氣候與可觀察條件，不可以說對方的下降點、宮位投射、overlay 命中或某天一定聯絡。(claims: western-precision-birth-data-quality-002, western-precision-birth-data-quality-003)

## in_general

V0 backend 應輸出四種精度：`exact_time`、`date_only`、`location_fallback`、`unavailable`。其中 `date_only` 會降權 Moon 並封鎖 Asc/Desc/houses；`location_fallback` 允許行星與非宮位合盤，但封鎖 house overlays。(claims: western-precision-birth-data-quality-001, western-precision-birth-data-quality-002, western-precision-birth-data-quality-003)

## Claims

### western-precision-birth-data-quality-001

**Claim:** 精準 timing 與完整星盤需要 exact time and place，但缺城市不應阻擋非宮位核心合盤。

**Source quote:**
> From `Planets in Transit`:
> "exact time and place of birth"

**Source location:** raw/western/436195408-Planets-in-Transit-Life-Cycles-for-Living-PDFDrive-com.txt:446-448

**Confidence:** INTERPRETATION

**Reasoning:** Hand 將精準 transit calendar 連到 exact time and place of birth；產品上應將缺地點視為精度下降，而不是完全不能讀。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

### western-precision-birth-data-quality-002

**Claim:** 出生時間不夠準時，不應輸出 house cusps、Asc/Desc 或 house overlay 類判斷。

**Source quote:**
> From `Planets in Transit`:
> "not accurate enough to justify a set of house cusps"

**Source location:** raw/western/436195408-Planets-in-Transit-Life-Cycles-for-Living-PDFDrive-com.txt:1708-1709

**Confidence:** INTERPRETATION

**Reasoning:** Hand 的範例明確把時間精度與 house cusps 合法性相連，支持 Valley 在 unknown birth time 下封鎖宮位與角度點輸出。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

### western-precision-birth-data-quality-003

**Claim:** 宮位與 house cusps 需要可靠地點或緯度資料，因此缺城市時 overlay 需要封鎖。

**Source quote:**
> From `Planets in Composite`:
> "using the latitude of the residence"

**Source location:** raw/western/843287714-Planets-in-Composite-Analyzing-Human-Relationships.txt:573-575

**Confidence:** INTERPRETATION

**Reasoning:** Composite house cusp calculation requires latitude. This supports blocking house/overlay claims when the runtime only has fallback or unknown place data.

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

## 典籍出處

### 原文引用
> From `Planets in Transit`:
> "not accurate enough to justify a set of house cusps"

### Supporting quote
> From `Planets in Composite`:
> "using the latitude of the residence"

## 與其他文章的連結

- [[western-planets-natal-relationship-needs]] — Moon、Desc、house 需求必須有精度限制。
- [[western-synastry-relationship-framework]] — 關係占星不可發明出生資料不足的事實。
- [[western-transits-timing-window]] — timing 只能在精度足夠時提高具體度。
- [[western-synastry-evidence-clusters]] — 精度 gate 決定 evidence 可展示、降權或封鎖。

## Source Extraction Log

- raw/western/436195408-Planets-in-Transit-Life-Cycles-for-Living-PDFDrive-com.txt:446-448 → supports `western-precision-birth-data-quality-001`
- raw/western/436195408-Planets-in-Transit-Life-Cycles-for-Living-PDFDrive-com.txt:1708-1709 → supports `western-precision-birth-data-quality-002`
- raw/western/843287714-Planets-in-Composite-Analyzing-Human-Relationships.txt:573-575 → supports `western-precision-birth-data-quality-003`
