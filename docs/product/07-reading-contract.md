# 07 - Reading Contract
## 從五步問卷到完整關係解讀的資料合約

> 目的：固定「一位用戶的一次 reading」在產品、計算、KB selector、LLM prompt 之間的共同資料形狀。

Current astrology branch contract:

- one paid `NT$1,280` complete relationship reading
- Western-only runtime payload
- primary API: `POST /api/readings/relationship-result`
- primary response type: `CompleteRelationshipResultViewModel`
- no visible free/paid split or upsell inside the result

Legacy mixed BaZi/free/paid sections in this document are historical context for
the paused BaZi path. They are not the active astrology branch output contract.

---

## No Names Required

**名字不參與八字，也不參與西洋占星計算。V0 不收集名字。**

BaZi calculation needs:
- birth date
- birth time if known
- birth timezone / birthplace handling
- sex or gender field when the calculation rule requires direction or relationship framing
- calendar mode if the user provides lunar date in the future

Western astrology calculation needs:
- birth date
- exact birth time if available
- birthplace / coordinates
- timezone
- house system, zodiac setting, aspect/orb rules

Product language should use role labels:
- `person_a` → `你`
- `person_b` → `對方`

Any future V2 personal label must remain product-copy-only.
It must not enter calculation logic.

If birth time is unknown:
- do not use hour-pillar claims
- mark precision as `date_only`
- avoid overly specific timing language

---

## Reading Input Shape

```json
{
  "reading_id": "example-cold-war-still-love-me",
  "person_a": {
    "birth_date": "1995-11-04",
    "birth_time": "13:00",
    "birth_timezone": "Asia/Taipei",
    "birth_place": "Taipei, Taiwan",
    "gender": "female"
  },
  "person_b": {
    "birth_date": "1993-03-15",
    "birth_time": "10:00",
    "birth_timezone": "Asia/Taipei",
    "birth_place": "Taichung, Taiwan",
    "gender": "male"
  },
  "context": {
    "relationship_stage": "cold-war",
    "main_question": "still-love-me",
    "contact_status": "no-contact",
    "desired_outcome": "reconnect",
    "emotional_risk": "self-blaming",
    "analysis_date": "2026-05-23",
    "who_initiated": "them",
    "relationship_length": "1-3y"
  },
  "calculation": {
    "status": "mock",
    "candidate_signals": {
      "bazi_signals": [
        {"id": "bazi-wuxing-mu-sheng-huo", "strength": 0.96},
        {"id": "bazi-tiangan-ding-huo", "strength": 0.78}
      ],
      "western_signals": [
        {"id": "western-aspects-venus-saturn", "strength": 0.91}
      ],
      "cross_signals": []
    }
  }
}
```

`calculation.status` is `mock` in examples. Production should set it to `calculated`.

---

## Five Runtime Context Fields

These are the fields that control selector and prompt behavior:

| Field | Allowed V0 values | Product use |
|---|---|---|
| `relationship_stage` | `broke-up-recent`, `cold-war`, `broke-up-long`, `crisis` | selects stage article and variant tone |
| `main_question` | `still-love-me`, `any-chance`, `when-to-contact`, `what-did-i-do-wrong`, `stay-or-let-go` | selects question article and direct-answer framing |
| `contact_status` | `still-in-contact`, `occasional-contact`, `no-contact`, `blocked`, `living-or-working-together` | affects timing/action advice |
| `desired_outcome` | `reconnect`, `understand`, `apologize`, `decide`, `move-on` | affects CTA and paid-report strategy |
| `emotional_risk` | `not-collected` by default; future guardrail values may include `desperate`, `unsafe-or-overwhelmed` | safety guardrails only; not used as a core calculation or accuracy input |
| `analysis_date` | `YYYY-MM-DD` | anchors current 流年 / 流月 calculations; runtime should set this in Asia/Taipei |

Additional fields like `who_initiated` and `relationship_length` are useful, but they are secondary context.

---

## Scenario Derived For Selector

The runtime reading input is reduced into a selector scenario:

```json
{
  "stage": "cold-war",
  "main_question": "still-love-me",
  "bazi_signals": [
    {"id": "bazi-wuxing-mu-sheng-huo", "strength": 0.96}
  ],
  "western_signals": [
    {"id": "western-aspects-venus-saturn", "strength": 0.91}
  ],
  "cross_signals": []
}
```

The selector chooses:
- `stage`
- `question`
- `bazi_core`
- `western_core`
- optional `timing`
- optional / conditional `safety`

---

## Relationship Case File V1

The selector is no longer the final diagnosis layer.
It is only the retrieval / slot layer.

Before the LLM writes, the calculation pipeline must build a structured
`relationshipCaseFile`.

```json
{
  "version": "relationship-case-file-v1",
  "principle": "先建立完整關係個案，再讓 LLM 寫故事；不可由一個八字訊號加一個相位直接推完整結論。",
  "identityLayer": {
    "personA": {
      "label": "你",
      "bazi": {
        "dayMaster": "己土",
        "dayPillar": "己亥",
        "monthCommand": "戌月令",
        "monthCommandMeaning": "己土日主生於戌月...",
        "strengthLabel": "偏旺",
        "strengthScore": 69,
        "strengthSummary": "己土日主生於戌月，扶身比印約7.40...",
        "balanceElements": ["金", "水", "木"],
        "spouseStarSummary": "正官、七殺藏在...",
        "birthPrecision": "date_time"
      },
      "westernNeeds": [
        {"point": "Moon", "label": "月亮白羊", "meaning": "情緒安全感線索"}
      ]
    },
    "personB": {},
    "crossTenGods": [
      {
        "label": "對方落在你的十神角色",
        "technical": "以你的日主看對方日主...",
        "emotionalMeaning": "對方容易被感受成..."
      }
    ],
    "methodLimits": []
  },
  "dimensions": {
    "coreAttachment": {},
    "emotionalSafety": {},
    "pressure": {},
    "repair": {},
    "timing": {}
  }
}
```

The five dimensions are the product-level reading spine:

| Dimension | Purpose | Required evidence |
|---|---|---|
| `coreAttachment` | Why there is still attraction / attachment | BaZi relationship role + Western attraction or connection signal |
| `emotionalSafety` | Why one side feels cold, unsafe, avoidant, or anxious | spouse palace / partner-star evidence + Moon / Venus / Saturn evidence |
| `pressure` | What blocks expression or repair | branch clash/harm/climate + Saturn or hard interaspect |
| `repair` | What must change before reconnecting works | pressure evidence + relationship stage/context |
| `timing` | Why now is good/bad/neutral | Liu Nian / Liu Yue + Da Yun / Liu Ri + current Western transits; composite / Davison later |

Each dimension must contain:
- `baziEvidence[]`
- `westernEvidence[]`
- `contextEvidence[]`
- `confidence`
- `emotionalMeaning`
- `doesNotProve`

## BaZi Free Diagnosis Interpreter

The free BaZi result now exposes a dedicated `baziCompatibilityDiagnosis`.
This is the deterministic free-page reading layer. It is not the LLM narrative.

Each BaZi module must carry both calculation facts and a plain-language interpreter layer:

```json
{
  "id": "spouse_star",
  "title": "配偶星",
  "score": 89,
  "level": "高",
  "coreFinding": "你有明面與深層關係星；對方的關係反應較不直接",
  "factors": [
    {
      "label": "配偶星",
      "value": "你七殺、正官透藏並見混；對方偏財、正財藏混",
      "meaning": "你有明面與深層關係星；對方的關係反應較不直接"
    }
  ],
  "reading": {
    "technicalEvidence": "你七殺、正官透藏並見混；對方偏財、正財藏混。",
    "plainMeaning": "配偶星看的是感情對象在命盤裡有沒有位置，以及這個位置是明著表達、藏在心裡，還是帶著混雜期待。",
    "relationshipPattern": "這段關係不能只用表面冷淡判斷，也不能只用想念判斷。",
    "doesNotMean": "這不代表他一定還愛，也不代表他一定會主動回來。",
    "actionHint": "先看他是否能把藏著的反應變成穩定行動。",
    "methodSource": "子平真詮/月令格局 + 窮通寶鑑/調候語言 + 淵海子平/十神六親"
  }
}
```

The result question must be answered only after the modules:

```json
{
  "questionAnswer": {
    "question": "他現在心裡還有我嗎？",
    "answer": "八字看不是完全無牽動...",
    "because": ["配偶星：...", "婚姻宮：...", "四柱暗線：..."],
    "therefore": "所以現在不適合用追問確認感情...",
    "avoid": ["連續訊息與高壓確認"]
  }
}
```

BaZi strength V1:
- The calculation layer now emits `day_master_strength_profiles`.
- Current method is `v1_weighted_month_branch_visible_hidden`.
- It weights month branch, visible stems, branch main qi, and hidden stems into support vs pressure roles.
- It outputs `strengthLabel`, `strengthScore`, and `balanceElements`.
- This is useful enough for relationship pressure / repair interpretation.
- It is **not** a complete 格局成敗 or formal 用神取法.

BaZi timing V1:
- The calculation layer now emits `bazi.analysis.timing_profile`.
- Current method is `bazi_current_year_month_v1`.
- It calculates 流年 / 流月 / 流日 pillars from `analysis_date`.
- Free result currently uses 流年 / 流月 for trend language only.
- It checks whether the current pillars activate spouse-role energy, day-branch pressure/combination, and day-master balance elements.
- It outputs `window_label`, `technical_summary`, `relationship_meaning`, and method limits.
- It is paired with the separate 大運 / 流日 card below, but it is **not** formal 喜忌 timing.

BaZi luck timing V1:
- The calculation layer now emits `bazi.analysis.luck_timing_profile`.
- Current method is `bazi_da_yun_liu_ri_v1`.
- It uses `lunar_python.getYun()` to calculate 起運 direction, 起運 date, current 大運, and current 流年 within that 大運.
- It also uses the analysis-date 流日 as short-term weather.
- It checks whether current 大運 / 流日 activates spouse-role energy, day-branch pressure/combination, and day-master balance elements.
- It outputs `window_label`, `technical_summary`, `relationship_meaning`, and method limits.
- It is **not** full 格局成敗, formal 喜忌, 神煞-level timing, or precise 擇日.

Western timing V1:
- The calculation layer now emits `western.analysis.timing_profile`.
- Current method is `western_current_transits_v1`.
- It builds an analysis-date noon transit chart and compares it to each person's natal relationship points.
- It currently focuses on Sun / Moon / Venus / Mars / Saturn transits to natal Sun / Moon / Venus / Mars / Saturn.
- It outputs `window_label`, `technical_summary`, `relationship_meaning`, strongest trigger, and method limits.
- Unknown birth time disables natal-Moon timing claims for that person.
- It is **not** composite, Davison, secondary progression, or precise window-search timing.

Important V1 limitation:
`timing` may reach medium/high confidence for directional trend language when
BaZi timing, BaZi luck timing, and Western current transits point to the same
climate, but it remains non-precise until formal 喜忌, progressions,
composite / Davison timing, and proper window search are connected.
The product must not fake a precise day or guaranteed contact window before those layers exist.

---

## Active Astrology Reading Blueprint V1

`westernRelationshipCaseFile` is the diagnosis layer.
`readingBlueprint` is the LLM execution layer.

Before the LLM writes, the pipeline must convert the case file into a strict
three-chapter blueprint:

```json
{
  "version": "reading-blueprint-v1",
  "mainConclusion": "牽動存在，但壓力訊號讓靠近變慢...",
  "suggestedResultTitle": "有牽動，但要先避開高壓靠近",
  "resultTitleSeeds": ["Moon-Saturn", "Venus-Mars", "Mercury repair"],
  "storyArc": "本次解讀先回答核心問題，再說明卡住機制與下一步...",
  "chapterOrder": ["thoughts", "reasons", "chance"],
  "chapters": [
    {
      "id": "thoughts",
      "title": "他現在怎麼想",
      "sourceDimensions": ["identityNeeds", "emotionalSafety"],
      "coreSummary": "one section summary only",
      "technicalFocus": "what the astrology layer must prove",
      "psychologicalFocus": "what the coach layer must translate",
      "evidence": [],
      "forbiddenClaims": []
    }
  ],
  "includedReadingPlan": [],
  "forbiddenClaims": [],
  "styleRules": []
}
```

Chapter mapping:

| Chapter | Uses dimensions | Purpose |
|---|---|---|
| `thoughts` / 他現在怎麼想 | `identityNeeds`, `emotionalSafety` | answer whether there is still reaction and why response may be cold/slow |
| `reasons` / 你們卡住的原因 | `pressure` | explain the specific pressure source without repeating attraction |
| `chance` / 還有沒有機會 | `repair`, `timing` | explain conditional opportunity, timing trend, and action boundary |

The LLM consumes `readingBlueprint` as the highest-priority execution plan.
`westernRelationshipCaseFile` remains the source diagnosis.
`relationshipDiagnosis` remains a short UI summary, not the full methodology.
Each `CaseFileEvidence` item may include `claimSupport`, a compact list of
claim ids, article ids, source ids, source locations, confidence, and claim text
from `dist/kb/kb_claims.json`. The LLM should use this only to strengthen the
technicalReading layer; it must not quote raw source passages unless explicitly
provided in a product-safe excerpt.
The result-page title is no longer allowed to come from a fixed question answer:
it must either rewrite `suggestedResultTitle` or include one of
`resultTitleSeeds`, so the first impression carries a real chart-specific
signal.

---

## Complete Answer Output Contract

The complete relationship result should feel specific, paid, and directly useful
without pretending to guarantee an outcome.

```json
{
  "direct_answer": {
    "source_slots": ["question", "stage"],
    "purpose": "Answer the user's selected main_question in 2-3 sentences."
  },
  "person_profiles": {
    "source_slots": ["moon", "mercury", "venus", "mars", "saturn"],
    "purpose": "Explain each person's emotional safety, communication repair, affection style, action rhythm, and defense pattern."
  },
  "fit_summary": {
    "source_slots": ["synastry", "relationshipProfiles"],
    "purpose": "Separate natural fit, effort areas, and friction points."
  },
  "evidence_cards": [
    {
      "slot": "western_relationship_core",
      "purpose": "Explain the strongest Western relationship signal in plain language."
    }
  ],
  "stage_meaning": {
    "source_slots": ["stage"],
    "purpose": "Explain what the selected signals mean in this relationship stage."
  },
  "next_step": {
    "source_slots": ["timing", "safety"],
    "purpose": "Give one action or one restraint, depending on user risk."
  },
  "included_sections": {
    "purpose": "List the concrete sections included in this complete reading."
  }
}
```

The result should build credibility in this order:

1. person A and person B profile
2. relationship fit and friction
3. direct answer to the selected question
4. why the system judged it that way
5. timing and action direction

---

## Future Deep Reading Contract

Future deep-reading modules may expand selected relationship-result signals.
They should not feel like the complete reading was replaced by unrelated
material.

| Selected slot | Future expansion |
|---|---|
| `stage` | opening, tone, safety boundary, closing |
| `question` | section framing and report title |
| `western_relationship_core` | deeper synastry, relationship chart layer, partner psychology |
| `timing` | broader timing windows and contact strategy after the scanner exists |
| `safety` | do-not-do list, repair boundaries, healing close |

---

## Safety Rules

If `emotional_risk` is `desperate` or `unsafe-or-overwhelmed`:
- do not recommend immediate contact
- do not amplify hope with timing windows
- include a grounding next step
- avoid "he still loves you" certainty

If `relationship_stage` is `broke-up-recent`:
- safety slot should be active
- contact advice should be conservative
- free answer should prioritize stabilization before action

If `main_question` is `what-did-i-do-wrong`:
- safety slot is required
- answer must reduce self-blame
- avoid one-sided fault language

---

## Test Harness

```bash
python3 scripts/build_reading_context.py \
  --reading examples/readings/cold-war-still-love-me.json \
  --include-drafts \
  --json
```

Selection-only mode:

```bash
python3 scripts/build_reading_context.py \
  --reading examples/readings/cold-war-still-love-me.json \
  --include-drafts \
  --selection-only \
  --json
```
