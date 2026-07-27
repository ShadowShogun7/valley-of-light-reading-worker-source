---
id: western-houses-angles-foundation
title: 角度點與宮位基礎
title_en: Angles and Houses Foundation
category: western/houses
type: concept

source_primary: Horoscope Symbols
source_chapter: "The Horoscope Angles / The Houses: Introduction"
source_secondary:
  - Planets in Composite
  - Planets in Transit

confidence: INTERPRETATION

related:
  - western-horoscope-symbols-foundation
  - western-precision-birth-data-quality
  - western-natal-relationship-potential
  - western-relationship-chart-layer
  - western-sun-moon-asc-profile-george-bloch
links:
  - target: western-horoscope-symbols-foundation
    type: requires
    reason: 角度點與宮位是 Hand 符號系統中的 mundane position 層。
  - target: western-precision-birth-data-quality
    type: cautions
    reason: Asc/Desc/MC/IC 與 house claims 必須受到出生時間與地點精度限制。
  - target: western-natal-relationship-potential
    type: supports
    reason: 角度點與宮位可補充本命關係潛力，但不能在精度不足時使用。
  - target: western-relationship-chart-layer
    type: contextualizes
    reason: 關係盤與 composite/Davison 的宮位層也需要可靠位置與方法邊界。
  - target: western-sun-moon-asc-profile-george-bloch
    type: cross_checks
    reason: George/Bloch 的 Sun/Moon/Asc 與 Desc 說明交叉確認 Asc/Desc 必須受到時間與地點精度限制。

applicable_products:
  - relationship_compatibility
relationship_stage:
  - all
question_relevance:
  - still-love-me
  - any-chance
  - what-did-i-do-wrong
  - stay-or-let-go

variants:
  - core
  - in_relationship
  - in_breakup
  - in_general

created_at: 2026-05-27
updated_at: 2026-05-27
last_reviewed: 2026-05-27
status: published
---

# 角度點與宮位基礎

## core

Hand 將 Ascendant、Descendant、Midheaven、I.C. 定義為四個 principal mundane points。這直接支持 Valley 的出生資料 gate：角度點不是可以憑生日補寫的心理描述，它們依賴時間與地點所決定的地平線/子午線架構。(claims: western-houses-angles-foundation-001)

角度點附近的行星會變得突出，並且可作為敏感點參與相位或 planetary-picture 關係；因此完整資料下，它們很適合支援第一印象、伴侶軸線與關係場域，但缺時間或缺可靠地點時必須封鎖。(claims: western-houses-angles-foundation-002)

宮位則表示行星能量在生活哪些區域浮現。這適合 paid-depth 的 house/overlay 層，但在免費 V0 與缺 birthplace/time 場景中，應只說「未展示」或「精度不足」，不可假裝已計算。(claims: western-houses-angles-foundation-003)

Hand 也區分「角度點」與「中間宮頭」的可靠性：Asc/MC/Desc/IC 可作為較明確的敏感點，houses 則更像 approximate indications of mundane position。Valley runtime 因此必須把 angle/house/overlay 做成 precision-gated contextual layer，而不是讓它在資料不足或未計算時進入核心結論。(claims: western-houses-angles-foundation-004)

## in_relationship

資料完整時，角度點和宮位能讓讀盤更細：Asc/Desc 可以描述初見反應與伴侶軸線，house/overlay 可以描述某種能量落在關係生活的哪個區域。資料不完整時，這一層不應進入 narrative；即使資料完整，house/overlay 也要標明是 contextual layer，不可取代行星功能與合盤相位。(claims: western-houses-angles-foundation-001, western-houses-angles-foundation-002, western-houses-angles-foundation-003, western-houses-angles-foundation-004)

### 優勢

- 能把「誰觸發誰的哪個生活場域」做成更深層關係分析。(claims: western-houses-angles-foundation-003)
- 能為出生時間/地點可靠的付費報告提供精準層。(claims: western-houses-angles-foundation-002)
- 能在 runtime 中明確標出「允許使用」與「已被精度封鎖」的差別。(claims: western-houses-angles-foundation-004)

### 弱點

- 缺時間或缺可靠地點時，Asc/Desc/house/overlay 不可展示。(claims: western-houses-angles-foundation-001)
- 宮位代表生活場域，不是直接保證事件或行動結果。(claims: western-houses-angles-foundation-003)
- 宮位本身仍是 approximate contextual evidence，不能在未計算 overlay/composite 時被寫成已命中的關係證據。(claims: western-houses-angles-foundation-004)

## in_breakup

分手情境中，角度點與宮位很容易被過度使用來說「他把你看成什麼」。產品應只在計算精度可靠時才使用這一層；否則更安全的做法是回到行星功能、合盤相位與現實聯絡狀態。(claims: western-houses-angles-foundation-001, western-houses-angles-foundation-002, western-houses-angles-foundation-003)

## in_general

V0 runtime 應繼續把 house/overlay 與 angle claims 放在 exact-time/location gate 後面。`location_fallback` 可以保留行星與非宮位相位，但應封鎖 house overlays；`date_only` 則同時封鎖 Asc/Desc/house，並對 Moon 證據降權。case file 必須保留機器可讀的 precision gate，讓 narrative 與前端都知道這一層是 allowed、blocked，還是 not calculated。(claims: western-houses-angles-foundation-001, western-houses-angles-foundation-003, western-houses-angles-foundation-004)

## Claims

### western-houses-angles-foundation-001

**Claim:** Ascendant、Descendant、Midheaven、I.C. 是四個 horoscope angles，屬於地平線/子午線的 mundane points。

**Source quote:**
> From Hand `Horoscope Symbols`:
> "Ascendant, Descendant, Midheaven, and I.C."

**Source location:** raw/western/horoscope-symbols-robert-hand-extracted.txt:949-961

**Confidence:** INTERPRETATION

**Reasoning:** Hand 將角度點直接連到 horizon/meridian，支持 runtime 在缺時間或地點時封鎖 Asc/Desc/MC/IC claims。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

### western-houses-angles-foundation-002

**Claim:** 靠近角度點的行星可成為顯著主題，但只能在角度點精度可靠時展示。

**Source quote:**
> From Hand `Horoscope Symbols`:
> "dominant theme in a person’s life"

**Source location:** raw/western/horoscope-symbols-robert-hand-extracted.txt:1003-1013

**Confidence:** INTERPRETATION

**Reasoning:** Hand 說角度點能增強行星強度與質性效果，支持完整資料報告使用 angle emphasis，也支持缺精度時不要補寫。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

### western-houses-angles-foundation-003

**Claim:** Houses 表示行星能量浮現的生活區域，不應被寫成具體事件保證。

**Source quote:**
> From Hand `Horoscope Symbols`:
> "where energies will surface"

**Source location:** raw/western/horoscope-symbols-robert-hand-extracted.txt:1088-1102

**Confidence:** INTERPRETATION

**Reasoning:** Hand 將 houses 定義為 areas/compartments/orientation，支持將 house/overlay 作為場域證據，而不是事件或復合保證。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

### western-houses-angles-foundation-004

**Claim:** Angle/house/overlay interpretation must remain a precision-gated contextual layer, not a substitute for calculated synastry or timing evidence.

**Source quote:**
> From Hand `Horoscope Symbols`:
> "approximate indications of mundane position"

**Source location:** raw/western/horoscope-symbols-robert-hand-extracted.txt:1074-1089

**Confidence:** INTERPRETATION

**Reasoning:** Hand treats angles as definite points while houses are approximate indications of mundane position. This supports runtime traces that separate allowed angles/natal houses, blocked precision cases, and unavailable overlay calculations.

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
> From Hand `Horoscope Symbols`:
> "where energies will surface"

### Supporting quote
> From Hand `Horoscope Symbols`:
> "approximate indications of mundane position"

## 與其他文章的連結

- [[western-horoscope-symbols-foundation]] — 宮位與角度點的符號系統位置。
- [[western-precision-birth-data-quality]] — 出生時間/地點精度 gate。
- [[western-natal-relationship-potential]] — 本命關係潛力的深度補充。
- [[western-relationship-chart-layer]] — paid-depth 關係盤/Composite/Davison 層。

## Source Extraction Log

- raw/western/horoscope-symbols-robert-hand-extracted.txt:949-961 → supports `western-houses-angles-foundation-001`
- raw/western/horoscope-symbols-robert-hand-extracted.txt:1003-1013 → supports `western-houses-angles-foundation-002`
- raw/western/horoscope-symbols-robert-hand-extracted.txt:1088-1102 → supports `western-houses-angles-foundation-003`
- raw/western/horoscope-symbols-robert-hand-extracted.txt:1074-1089 → supports `western-houses-angles-foundation-004`
