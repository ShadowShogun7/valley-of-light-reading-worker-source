---
id: western-horoscope-symbols-foundation
title: 占星符號基礎
title_en: Horoscope Symbols Foundation
category: western/synastry
type: concept

source_primary: Horoscope Symbols
source_chapter: Preface / The Symbol Systems of Astrology / The Planets
source_secondary:
  - "Synastry: Understanding the Astrology of Relationships"

confidence: INTERPRETATION

related:
  - western-planets-planetary-functions-hand
  - western-sign-element-modality-foundation
  - western-individual-sign-meanings-hand
  - western-houses-angles-foundation
  - western-aspect-interpretation-foundation
links:
  - target: western-planets-planetary-functions-hand
    type: supports
    reason: 行星功能是 Hand 符號系統的第一層，支援本命關係需求與合盤觸發。
  - target: western-sign-element-modality-foundation
    type: supports
    reason: 星座元素與三模式是 Hand 符號系統中 signs 層的內部結構。
  - target: western-individual-sign-meanings-hand
    type: supports
    reason: 十二星座核心語義讓 planet-in-sign placement 可以進入 runtime evidence。
  - target: western-houses-angles-foundation
    type: supports
    reason: 宮位與角度點是 Hand 符號系統的 mundane position 層。
  - target: western-aspect-interpretation-foundation
    type: supports
    reason: 相位是 Hand 符號系統中的 angular relationship 層。

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

created_at: 2026-05-27
updated_at: 2026-05-27
last_reviewed: 2026-05-27
status: published
---

# 占星符號基礎

## core

Hand 的方法很適合作為 Valley 西洋 KB 的底層：完整讀盤不是先寫結論，而是先掌握各個符號的核心意義，再把它們組合成一個一致的閱讀。這支持我們把長文章拆成可驗證的 atoms/rules，而不是讓 LLM 憑感覺合成整段故事。(claims: western-horoscope-symbols-foundation-001)

Hand 把常用占星符號分成 planets、horoscope angles、aspects、houses、signs。對 Valley 來說，這正好對應 backend 的可計算層：本命行星與星座、角度點與宮位、合盤相位，以及精度 guardrails。(claims: western-horoscope-symbols-foundation-002)

其中 planets 是最基礎的動態符號。這代表讀關係時，不能只問「這個星座合不合」，而要先知道 Sun/Moon/Mercury/Venus/Mars/Saturn 等行星各自代表什麼心理功能，再看合盤如何讓它們互相牽動。(claims: western-horoscope-symbols-foundation-003)

Signs 層要接到 [[western-sign-element-modality-foundation]]：星座不是單一人格標籤，而是由元素、三模式、極性等結構修飾行星功能。

個別 planet-in-sign placement 則接到 [[western-individual-sign-meanings-hand]]，讓 Sun/Moon/Venus/Mars/Saturn 等功能能用具體星座語氣表達。

## in_relationship

在關係仍有互動時，符號基礎層讓系統先分清楚「需求」「表達」「吸引」「壓力」「宮位場域」各自屬於哪一種證據。這樣免費頁可以講清楚一個互動模式，而不是把所有星盤資料混成一句「很有緣」或「不適合」。(claims: western-horoscope-symbols-foundation-001, western-horoscope-symbols-foundation-002)

### 優勢

- 能把 reading 拆成穩定、可測試的符號層。(claims: western-horoscope-symbols-foundation-002)
- 能避免用單一星座、單一相位或單一宮位替整段關係下結論。(claims: western-horoscope-symbols-foundation-001)

### 弱點

- Hand 是基礎符號書，不是專門關係合盤書；關係問題仍要接 Suskin、Burk、Davison 等方法源。(claims: western-horoscope-symbols-foundation-001)
- 符號基礎只定義證據語法，不直接判斷對方是否回頭。(claims: western-horoscope-symbols-foundation-003)

## in_breakup

分手、冷戰或斷聯情境中，符號基礎層最重要的功能是降低讀心與預言衝動。系統應先確認哪些符號可計算、哪些需要精度、哪些只代表能量/功能，再用 question reducer 回答「他還愛不愛」「還有沒有機會」。(claims: western-horoscope-symbols-foundation-001, western-horoscope-symbols-foundation-002, western-horoscope-symbols-foundation-003)

## Claims

### western-horoscope-symbols-foundation-001

**Claim:** 讀盤合成前需要先理解每個獨立符號的基本意義，否則不應直接產生整體結論。

**Source quote:**
> From Hand `Horoscope Symbols`:
> "understanding of each of its separate symbols"

**Source location:** raw/western/horoscope-symbols-robert-hand-extracted.txt:202-207

**Confidence:** INTERPRETATION

**Reasoning:** Hand 將 coherent reading 建立在 separate symbols 的理解上，支持 Valley 以 source-backed atoms 先建立可組合符號，再進行敘事合成。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-horoscope-symbols-foundation-002

**Claim:** 西洋占星讀盤至少要區分 planets、angles、aspects、houses、signs 等符號系統。

**Source quote:**
> From Hand `Horoscope Symbols`:
> "the planets, horoscope angles, aspects, houses, and signs"

**Source location:** raw/western/horoscope-symbols-robert-hand-extracted.txt:527-531

**Confidence:** INTERPRETATION

**Reasoning:** Hand 明確列出最常用的符號系統，支持 KB v2 將本命、宮位/角度點、相位與星座分層建模。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

### western-horoscope-symbols-foundation-003

**Claim:** Planets 是最基礎的占星符號，應作為本命需求與合盤觸發的主要語法層。

**Source quote:**
> From Hand `Horoscope Symbols`:
> "Planets are the most basic astrological symbols"

**Source location:** raw/western/horoscope-symbols-robert-hand-extracted.txt:608-615

**Confidence:** INTERPRETATION

**Reasoning:** Hand 將 planets 定義為 personality energies 與 living energies，支持 runtime 先用行星功能標記需求、吸引、壓力與修復入口。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup

## 典籍出處

### 原文引用
> From Hand `Horoscope Symbols`:
> "understanding of each of its separate symbols"

## 與其他文章的連結

- [[western-planets-planetary-functions-hand]] — 行星功能層。
- [[western-sign-element-modality-foundation]] — 星座元素與三模式層。
- [[western-individual-sign-meanings-hand]] — 十二星座核心語義層。
- [[western-houses-angles-foundation]] — 宮位與角度點層。
- [[western-aspect-interpretation-foundation]] — 相位解讀層。

## Source Extraction Log

- raw/western/horoscope-symbols-robert-hand-extracted.txt:202-207 → supports `western-horoscope-symbols-foundation-001`
- raw/western/horoscope-symbols-robert-hand-extracted.txt:527-531 → supports `western-horoscope-symbols-foundation-002`
- raw/western/horoscope-symbols-robert-hand-extracted.txt:608-615 → supports `western-horoscope-symbols-foundation-003`
