# 10 - BaZi Reading Interpreter

## Status: On Hold

> Current astrology V1 is Western-only at runtime. BaZi source/docs remain in
> the repo for the separate BaZi branch, but should not drive the active Western
> relationship result.

**Decision date:** 2026-05-25

BaZi relationship reading is paused for the front-end product flow.

Reason:

- The current implementation can calculate pillars and produce a structured BaZi diagnosis, but the reading still does not feel sophisticated enough for a premium product.
- Proper BaZi relationship reading requires a fuller method stack: 月令、日主旺弱、用神/忌神、十神、配偶星、婚姻宮、合沖刑害破、藏干、大運/流年/流月.
- We should not keep optimizing UI or LLM copy around a BaZi evidence pack that is still methodologically immature.

Current product implication:

- Keep the BaZi code, docs, and prior research for later.
- Hide BaZi modules from the front end during the next exploration phase.
- Do not build more BaZi UI until the deterministic diagnosis layer can support a full modular reading without collapsing into one simple signal.

## Purpose

The calculation layer answers: **what did the chart produce?**

The interpreter layer answers: **how should a normal person understand it?**

This layer exists because raw BaZi facts are not a reading. A useful relationship reading needs a repeated grammar:

```text
命理師看到什麼
  ↓
人話意思
  ↓
關係模式
  ↓
不代表什麼
  ↓
先看 / 先做什麼
```

Every free BaZi module must now expose this grammar through `module.reading`.

## Method Hierarchy

The interpreter should use the books as method teachers, not as decorative authority.

- `子平真詮 / 子平真詮評註`: reading order, 月令, 格局, 成敗, whether a signal can actually be used.
- `窮通寶鑑`: climate language, 調候, warmth/coldness/dryness/wetness, easy plain-language translation.
- `淵海子平`: 日主為主, 十神, 六親, spouse-star role mapping.
- `滴天髓闡微`: weighting, subtle judgment, avoiding shallow single-signal readings.
- `三命通會`: encyclopedia and cross-check, not the main product voice.

## Module Reading Contract

```ts
type BaziModuleReading = {
  technicalEvidence: string;     // one concise chart fact
  plainMeaning: string;          // ordinary-language explanation
  relationshipPattern: string;   // how it appears between two people
  doesNotMean: string;           // guardrail against overclaiming
  actionHint: string;            // free-level observation/action direction
  methodSource: string;          // method lineage, not citation prose
};
```

Rules:

- `technicalEvidence` must be concrete: day master, month command, strength, Ten God role, spouse star, palace, branch interaction, or timing trigger.
- `plainMeaning` must not repeat the technical fact. It translates it.
- `relationshipPattern` must describe a human interaction pattern.
- `doesNotMean` must prevent fatalistic or overconfident claims.
- `actionHint` must stay free-level. No exact date, message template, or guaranteed result.

## Free Result Order

The free result should read in this order:

1. `雙方八字分析`
2. `五行匹配`
3. `十神關係`
4. `配偶星`
5. `婚姻宮`
6. `四柱暗線`
7. `時間層`
8. `性格互補`
9. `答案 / 因為 / 所以`

The answer block comes after the modules because it should feel like a conclusion from the reading, not a generic response to the question.

## What This Fixes

Bad pattern:

```text
己土生戌月，乙木生卯月，配偶星藏，亥巳沖，所以先降壓。
```

Good pattern:

```text
命理師看到：你的日主偏旺，對方也偏旺，雙方承壓時都不容易先軟。
人話意思：這不是誰完全沒感覺，而是壓力一高，兩邊都會先守住自己。
關係模式：冷戰時常見的是互相等對方先退一步。
不代表：這不保證復合，也不能只用一次未回覆判斷。
先看：低壓互動下，對方是否能自然回應。
```
