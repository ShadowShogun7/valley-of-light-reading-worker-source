# 08 - Result Dashboard Design
## 免費結果儀表板視覺與內容規格

> Legacy visual/content reference only.
> This describes the old warm ivory free-result dashboard. Current result pages
> should follow the new paid-only cosmic V1 direction and the active
> `CompleteRelationshipResultViewModel` contract.
> Active contract: `docs/product/00-current-v1-contract.md` and
> `docs/product/09-frontend-flow-view-model.md`.

> 目的：把免費結果頁從「文章型解讀」收斂成可互動、可截圖、可轉換的 mobile-first dashboard。
> 本文件是 V0 前端結果頁的視覺與內容執行規格。

---

## Core Decision

V0 使用「warm ivory quiet celestial dashboard」作為設計核心：

- 米白底、柔和杏金色、細線圖示、輕量卡片
- 品牌感是 intimate / premium / calm，不是浮誇算命、不像泛用 SaaS
- 第一屏直接回答問題，不先鋪命理背景
- 證據用 dashboard cards 呈現，不用長篇文章
- 付費解鎖要延續免費看到的同一組 signals

`04-free-result-page.md` 仍定義免費結果的轉換策略。
本文件定義它在 UI 上如何被使用者感受到。

Current implementation:
- `apps/web/` contains the first Next.js result dashboard prototype.
- `apps/web/src/data/demo-reading.ts` holds the static V0 demo result.
- `apps/web/scripts/smoke-dashboard.mjs` verifies mobile and desktop render paths.

---

## Product Intent

免費結果的順序必須是：

```text
answer first
    ↓
evidence second
    ↓
next action third
    ↓
paid depth fourth
```

使用者在 5 秒內必須知道：

1. 系統有直接回答她問的問題
2. 這個回答不是泛泛而談，而是由八字 + 西洋合盤共同支撐
3. 她現在該做什麼，以及什麼不該做
4. 付費版會解鎖同一段關係更深的原因、時間窗與策略

---

## Visual Language

### Palette

| Token | Use | Color |
|---|---|---|
| `background` | app canvas | `#FBF7EF` |
| `surface` | card background | `#FFFDF8` |
| `surface-soft` | inner panels | `#FCF2E8` |
| `border` | card lines | `#EADBC7` |
| `text` | main copy | `#1A1712` |
| `text-muted` | labels | `#6F665D` |
| `accent` | progress / active tab | `#D99654` |
| `accent-soft` | chips / badges | `#F4DFC6` |
| `ink-soft` | icons / dividers | `#93877B` |
| `safety` | caution copy, not alarm | `#8A6B56` |

Avoid:
- high-saturation purple or blue gradient astrology styling
- red danger states for relationship anxiety
- dense black backgrounds for the default theme
- decorative blobs, orbs, bokeh, or generic mystical backgrounds

### Typography

| Layer | Recommendation | Use |
|---|---|---|
| Brand | `Noto Serif TC`, `Songti TC`, or equivalent serif | `光之谷`, key title moments |
| UI body | `Noto Sans TC`, `PingFang TC`, or equivalent sans | cards, tabs, chips |
| Numbers | `Inter` or tabular sans | score, percentages, day numbers |

Rules:
- Hero-scale type only on the first answer screen.
- Compact panels use smaller, tight headings.
- Letter spacing stays at `0`.
- Chinese copy must wrap cleanly inside buttons and cards.

### Shape And Components

The chosen theme intentionally uses soft mobile wellness cards.
Use:

- Dashboard cards: `16px` radius
- Metric tiles: `12px` radius
- Buttons and compact chips: `8px` radius or pill when semantically a status tag
- 1px borders, low shadow, no heavy glassmorphism
- Lucide-style line icons where possible
- Thin dividers between list rows

Illustrations should be minimal line art with one warm accent color.
They should show relationship state or action, not generic zodiac decoration.

---

## Data Mapping

The dashboard renders the same selected slots from `07-reading-contract.md`.

| Runtime field / slot | UI destination |
|---|---|
| `relationship_stage` | stage pill, stage tab, relationship status copy |
| `main_question` | top question title, active question tab, direct answer |
| `contact_status` | next-step plan and caution cards |
| `desired_outcome` | CTA framing and action plan tone |
| `emotional_risk` | safety card, do-not-do list, conservative timing |
| `stage` slot | result summary and stage explanation |
| `question` slot | direct answer and first tab content |
| `bazi_core` slot | BaZi core card, dual-system evidence panel |
| `western_core` slot | Western core card, dual-system evidence panel |
| `timing` slot | timing ring, 7-day plan, paid timing lock |
| `safety` slot | safety reminder and "不要做" controls |
| claim-backed articles | source chips and evidence snippets |
| calculation output | four-pillar mini table, aspect chips, signal strength |

Names are not required. UI labels should use:

- `你`
- `對方`

Do not introduce personal names into calculation, selector, or source claims.

---

## Screen Architecture

V0 result dashboard is an 8-screen mobile flow.
On web, it can render as a single scroll page with sticky tabs.
For design exploration, each screen can be generated as a separate mobile mock.

### 1. 結果首頁

Purpose:
- answer the user's main question immediately
- create enough emotional trust to continue

Primary components:
- brand header: `光之谷 / Valley of Light`
- small badge: `免費合盤結果`
- question headline
- direct answer card
- relationship stage pill
- relationship signal score
- emotional safety status
- small relationship line illustration

Sample copy:

```text
他現在心裡還有我嗎？

有牽動，但不是輕鬆靠近的狀態。
你們之間還有反應，也有壓力；
現在最重要的不是急著確認答案，而是看清楚這段關係卡在哪裡。

冷戰 / 斷聯中
牽動強度 78 / 100
需要慢一點，不適合衝動聯絡
```

Source data:
- `question`
- `stage`
- strongest `bazi_core` and `western_core` signal strength
- `safety` if active

### 2. 儀表板總覽

Purpose:
- show that the system has structured, multi-axis judgement
- let the user choose what to inspect next

Primary components:
- 2x2 metric tiles
- core insight list rows
- each row opens the relevant tab or detail

Metric tiles:

```text
情感牽動：高
關係壓力：中高
復合可能：有條件
最佳行動：先穩住，再觀察
```

Core insight rows:

```text
八字核心訊號：配偶星仍被啟動
西洋核心訊號：Sun-Mars 強互動
關係階段：冷戰不是結束，而是情緒防衛
安全提醒：不要用追問換聯絡
```

Source data:
- selected slot IDs
- selector `rank_reason`
- article title and one-sentence summary

### 3. 他現在怎麼想

Purpose:
- directly answer the emotional question
- translate signals into human language

Primary components:
- sticky tabs
- calm relationship illustration
- numbered explanation list

Tabs:

```text
他現在怎麼想
你們卡住的原因
還有沒有機會
下一步怎麼做
```

Sample copy:

```text
1. 他不是完全沒感覺，而是在避免再進入高壓互動。
2. 目前比較像觀望與防衛，不代表完全放下。
3. 如果你現在太急著確認，反而容易讓他後退。
```

Source data:
- `question`
- `stage`
- top Western emotional/pressure aspect
- safety guardrails

### 4. 你們卡住的原因

Purpose:
- make the user feel seen without blaming them
- explain pressure, attraction, and avoidance as a pattern

Primary components:
- three reason cards
- percentage/progress bars
- icon per pattern

Sample cards:

```text
吸引仍在，但互動模式容易讓彼此壓力升高。 78%
對方更怕失控或被逼問，而不是完全不在乎。 68%
你越想立刻得到答案，越容易把關係推向防衛。 72%
```

Source data:
- `bazi_core`
- `western_core`
- `stage`
- `emotional_risk`

Rules:
- Do not assign one-sided blame.
- Do not say the partner "一定" feels something.
- Show pressure as a shared pattern.

### 5. 還有沒有機會

Purpose:
- answer hope with boundaries
- make "chance" feel realistic, not manipulative

Primary components:
- circular chance visualization
- three bullets under the chart
- low / medium / high legend

Sample copy:

```text
67%

有機會，但節奏距離要放慢。
若能降低壓力，仍有重新靠近的空間。
這不是追問的時機，而是觀察回應的時機。
```

Source data:
- stage
- contact status
- selected signal strengths
- safety slot

Interpretation rule:
- The percentage is a product confidence visualization, not fate certainty.
- Keep it tied to conditions: "if pressure lowers", "if response appears", "if timing stabilizes".

### 6. 下一步怎麼做

Purpose:
- give the user one grounded, useful action plan
- prevent anxious behavior that hurts trust and conversion

Primary components:
- next 7 days timeline
- do-not-do controls/cards
- optional timing window if supported

Sample copy:

```text
接下來 7 天

Day 1-2
不主動追問，先讓情緒降下來。

Day 3-5
觀察對方是否有低壓回應。

Day 6-7
若情緒穩定，再用一句輕量訊息測試。
```

Do-not-do cards:

```text
不要連續傳訊息
不要用長文道歉
不要問「你到底還愛不愛我」
```

Source data:
- `timing`
- `safety`
- `contact_status`
- `emotional_risk`

### 7. 雙系統證據

Purpose:
- prove that the answer came from actual BaZi and Western calculation
- keep evidence compact and visual

Primary components:
- East / West cards
- mini four-pillar table
- selected BaZi chips
- Western aspect chips
- simple synastry orbit visual
- source-backed explanation snippets

BaZi card example:

```text
東方八字
日主：辛金
核心訊號：配偶星 / 官星有感應
四柱小表：年柱 / 月柱 / 日柱 / 時柱
五行分布：金 4、木 0、水 1、火 1、土 1
```

Western card example:

```text
西洋合盤
Sun-Mars：強互動
Saturn pressure：中高
attraction-pressure：明顯
balance-pressure：偏緊張
```

Source data:
- calculation fixture
- selected `bazi_core`
- selected `western_core`
- source article claims

Rules:
- This screen is evidence, not the main answer.
- Avoid dense raw chart dumps.
- Show only the pieces that explain the selected reading.

### 8. 深度報告解鎖

Purpose:
- convert by showing specific missing depth
- make paid feel like expansion, not a different product

Primary components:
- locked rows
- primary CTA
- source trust footer

Locked rows:

```text
他真正逃避的是什麼
你們的吸引與壓力來源
最適合聯絡的時間窗
這段關係能不能修復
你該等、該退，還是該放下
```

CTA:

```text
解鎖完整合盤報告
```

Trust footer:

```text
分析依據：
八字合婚 × 西洋合盤 × 光之谷知識庫

《滴天髓闡微》
《子平真詮評註》
Skymates
Synastry
```

Source data:
- selected free slots
- paid expansion contract
- claim source chips

---

## Content Rules

Every visible insight should follow this shape:

```text
plain-language finding
    ↓
why the system sees it
    ↓
what it means for this stage
    ↓
what to do / not do
```

Rules:
- Direct answer: 2-3 sentences.
- Metric card: one phrase + one level.
- Evidence card: one signal + one plain-language meaning.
- Source chips: short labels only.
- No fatalistic certainty.
- No "you caused everything" framing.
- No generic "you are both learning" filler.
- No long doctrinal explanations in the free UI.
- Chinese output should be the default production language.

The dashboard may use English source names in chips where source recognition helps.
The actual interpretation copy should be Chinese.

---

## Paid Conversion Rule

Free and paid must feel continuous:

```text
free selected slots
    ↓
same slots become paid section anchors
    ↓
paid adds depth, timing, psychology, and action strategy
```

Bad paid preview:
- unlocks unrelated astrology facts
- introduces many new signals not seen in free
- feels like a second reading

Good paid preview:
- expands "why he avoids pressure"
- expands "why attraction is still active but hard to stabilize"
- expands "when and how to contact"
- expands "what cannot be repaired"

---

## Frontend Notes

V0 frontend should be built mobile-first.

Recommended layout:
- mobile: `390px` reference width, single scroll, sticky tab bar after top summary
- desktop: centered phone-width result rail plus optional evidence/CTA rail
- cards: fixed responsive dimensions where possible, no layout shift from percentages or labels
- tabs: horizontal scroll on small screens, active underline
- progress bars: warm accent with soft track
- charts: simple SVG/canvas visuals are fine if they are stable and readable

Use icons for:
- heart / attraction
- pulse / pressure
- sparkle / possibility
- leaf / action
- shield / safety
- lock / paid rows
- bell / account notification if needed

Do not make a landing page for the result route.
The first screen must be the actual result dashboard.

---

## Image Generation Prompt

Use this prompt when exploring visual directions:

```text
Design 8 connected mobile app screens for a premium Chinese relationship astrology result dashboard called "光之谷 / Valley of Light".

Core style: warm ivory background, soft peach-gold accents, near-black text, thin beige borders, elegant line icons, minimal celestial details, calm intimate premium mood, no generic SaaS look, no neon astrology cliches, no purple gradients.

Audience: women checking a relationship or breakup reading. The UI should feel emotionally safe, professional, and accurate, not like cheap fortune telling.

Screens:
1. 結果首頁 - brand header, "免費合盤結果" badge, question headline "他現在心裡還有我嗎？", 2-3 sentence direct answer card, relationship stage pill "冷戰 / 斷聯中", signal strength "78 / 100", emotional safety status, simple line illustration of two people in distance.
2. 儀表板總覽 - 2x2 metric tiles for 情感牽動, 關係壓力, 復合可能, 最佳行動; below that, list rows for 八字核心訊號, 西洋核心訊號, 關係階段, 安全提醒.
3. 他現在怎麼想 - sticky tabs, calm moon/person line illustration, numbered explanation cards with concise Chinese copy.
4. 你們卡住的原因 - three reason cards with icons and warm progress bars, showing attraction, pressure, and anxious-confirmation pattern.
5. 還有沒有機會 - circular chance visualization around 67%, three condition-based bullets, low/medium/high legend.
6. 下一步怎麼做 - next 7 days timeline with Day 1-2, Day 3-5, Day 6-7, and three "不要做" action cards.
7. 雙系統證據 - two compact evidence cards: 東方八字 with four-pillar mini table and five-element bars; 西洋合盤 with Sun-Mars, Saturn pressure, aspect chips, and a simple synastry orbit visual.
8. 深度報告解鎖 - locked rows for deeper paid insights, black premium CTA button "解鎖完整合盤報告", source trust footer with chips for 《滴天髓闡微》, 《子平真詮評註》, Skymates, Synastry.

Component rules: rounded dashboard cards, 1px warm borders, restrained shadows, compact Chinese typography, readable tab labels, stable spacing, no text overlap. Use elegant line-art illustrations and icon buttons. The design should look like a real app screen, not a marketing page.
```

Theme modifiers:

```text
Soft lunar editorial: add pearl white, mist blue, silver lines, and moon-phase details while keeping the same dashboard structure.

Modern Taiwanese luxury: add deep red micro-accents, ink gray text, refined editorial spacing, and warmer paper texture.

Feminine premium app: add rose quartz accents, softer cards, and delicate line illustrations, while keeping result metrics professional.

Dark celestial dashboard: switch to black jade background with warm gold accents, but preserve calm readability and avoid neon.
```

---

## Acceptance Checklist

Before implementing or approving a frontend mock:

- The answer to the user's main question is visible on screen 1.
- The UI feels like a dashboard, not a long article.
- The four required selector slots are visible somewhere in the free experience.
- Timing and safety appear only when supported by context.
- The user can understand the next action without reading the paid report.
- The paid preview expands the same free signals.
- BaZi and Western evidence are visible but not overwhelming.
- Source trust is present, compact, and source-backed.
- No text overlaps at mobile width.
- No fatalistic or emotionally unsafe language appears in free copy.
