---
id: bazi-timing-luck-flow
title: 大運與行年
title_en: Major Luck and Annual Flow
category: bazi/timing
type: concept

source_primary: 三命通會
source_chapter: 論大運 / 論小運
source_secondary:
  - 子平真詮評註

confidence: INTERPRETATION

related:
  - bazi-timing-year-month-trigger
  - bazi-geju-month-command-strength
  - bazi-hehun-spouse-star
  - western-transits-timing-window
links:
  - target: bazi-timing-year-month-trigger
    type: timing
    reason: 大運是較長週期，流年流月是較短觸發，兩者必須合看。
  - target: bazi-geju-month-command-strength
    type: requires
    reason: 行運吉凶需要回到命局喜忌、用神與日主強弱判斷。
  - target: bazi-hehun-spouse-star
    type: contextualizes
    reason: 關係 timing 若牽動配偶星，才更適合進入感情閱讀。
  - target: western-transits-timing-window
    type: cross_checks
    reason: 西洋行運可作為另一套時間窗語言，但不能與八字歲運直接等同。

applicable_products:
  - relationship_compatibility
  - personal_bazi
relationship_stage:
  - all
question_relevance:
  - when-to-contact
  - any-chance
  - stay-or-let-go
  - what-did-i-do-wrong

variants:
  - core
  - in_relationship
  - in_breakup
  - in_general

created_at: 2026-05-24
updated_at: 2026-05-24
last_reviewed: 2026-05-24
status: draft
---

# 大運與行年

## core

大運是八字 timing 的長週期層。《三命通會》說大運以一辰十歲，並以出生前後節氣、男女陰陽順逆起運；這代表產品不能把「現在如何」只寫成流年或單日訊號，而要先知道命主目前走在什麼較長氣候裡。(claims: bazi-timing-luck-flow-001)

行年 / 小運則補足年度層，但仍要和大運、柱中用神、日主、旺衰喜忌一起衡量。V1 若使用 `bazi-da-yun-liu-ri-v1`，source-backed 部分是大運與行年框架；若要寫到流日，只能作短期提示，不可包裝成古典定論。(claims: bazi-timing-luck-flow-002)

## in_relationship

在關係閱讀中，大運與行年回答的是「這段時間命主更容易如何承受關係」。若大運或行年扶助喜用，關係議題較有承接力；若逆喜用或壓住配偶星、婚姻宮，則容易變成拖延、防衛、失衡或暫時難以推進。(claims: bazi-timing-luck-flow-002, bazi-timing-luck-flow-003)

### 優勢

- 能讓「為什麼現在這樣」不只停在日主生剋，而有時間背景。(claims: bazi-timing-luck-flow-001)
- 能支援付費報告中的修復條件與等待成本判斷。(claims: bazi-timing-luck-flow-002, bazi-timing-luck-flow-003)

### 弱點

- 大運與行年不能直接等於「某天一定聯絡」。(claims: bazi-timing-luck-flow-002)
- 若未完成完整喜用神判斷，只能用方向性語言，不應給絕對吉凶。(claims: bazi-timing-luck-flow-003)

## in_breakup

分手或冷戰場景中，大運與行年可用來解釋「這段關係為什麼此時卡住」。若歲運同時壓到喜用、配偶星或婚姻宮，產品可寫成現在比較像整理、降壓或等待訊號回穩；但仍不能把它寫成復合保證或結束保證。(claims: bazi-timing-luck-flow-002, bazi-timing-luck-flow-003)

## in_general

大運是十年氣候，行年是年度參照。取運要與看命同法，必須配合四柱、月令、日主、喜忌與用神，不可抽出單一干支直接斷事。(claims: bazi-timing-luck-flow-001, bazi-timing-luck-flow-003)

## Claims

### bazi-timing-luck-flow-001

**Claim:** 大運是十年層級的 timing 框架，起運需依節氣與順逆法，不是任意附會的短期訊號。

**Source quote:**
> 引自《三命通會》論大運：
> 「以大運則一辰十歲」
> 「陽男陰女，大運以生日後未來節氣日時」
> 「陰男陽女，大運以生日前過去節氣日時」

**Source location:** raw/bazi/655261191-三命通會.txt:1659-1675

**Confidence:** DOCTRINE

**Reasoning:** 原文清楚描述大運十年一辰與起運取節氣、順逆的方法，支持產品把大運視為較長週期背景。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

### bazi-timing-luck-flow-002

**Claim:** 小運 / 行年掌年度吉凶，但要和大運、用神、日主、旺衰喜忌一起參看。

**Source quote:**
> 引自《三命通會》論小運：
> 「夫大運司十年之休咎，小運掌一歲之災祥」
> 「亦要與大運及柱中用神日主較量吉凶」
> 「先詳八字衰旺喜忌」

**Source location:** raw/bazi/655261191-三命通會.txt:1691-1703

**Confidence:** DOCTRINE

**Reasoning:** 原文明確把小運 / 行年放在年度層，並要求與大運、用神、日主、衰旺喜忌合看。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

### bazi-timing-luck-flow-003

**Claim:** 行運吉凶必須以全命局與喜用神統觀，不可抽出單一運字斷章取義。

**Source quote:**
> 引自《子平真詮評註》論行運：
> 「配命中干支而統觀之」
> 「看運須十年並論」
> 「不能以一字之喜忌，斷章取義也」

**Source location:** raw/bazi/514192058-子平真詮評注-沈孝瞻原著-徐樂吾評注.txt:2626-2640

**Confidence:** DOCTRINE

**Reasoning:** 徐樂吾要求取運與看命同法，按命中干支與喜忌統觀，支持產品避免用單一流日、流年或大運字直接斷關係結果。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
- in_general

## 典籍出處

### 《三命通會》
> 引自《三命通會》論大運：
> 「以大運則一辰十歲」

### 《子平真詮評註》
> 引自《子平真詮評註》論行運：
> 「看運須十年並論」

## 與其他文章的連結

- [[bazi-timing-year-month-trigger]] — 流年流月是較短觸發，需要放在大運背景中。
- [[bazi-geju-month-command-strength]] — 行運吉凶需回到月令、日主強弱與喜忌。
- [[bazi-hehun-spouse-star]] — 感情 timing 需要看配偶星是否被觸發。
- [[western-transits-timing-window]] — 西洋行運提供跨系統時間窗校驗。

## Source Extraction Log

- raw/bazi/655261191-三命通會.txt:1659-1675 → supports `bazi-timing-luck-flow-001`
- raw/bazi/655261191-三命通會.txt:1691-1703 → supports `bazi-timing-luck-flow-002`
- raw/bazi/514192058-子平真詮評注-沈孝瞻原著-徐樂吾評注.txt:2626-2640 → supports `bazi-timing-luck-flow-003`

