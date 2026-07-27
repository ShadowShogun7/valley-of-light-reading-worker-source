# 00 - Current V1 Contract
## Paid-only Western relationship reading

> Status: active source of truth for the current astrology branch.
> Updated: 2026-06-10.

## Product Decision

V1 is one complete paid Western relationship reading at `NT$1,280`.

There is no free preview, no in-result upsell, no locked rows, and no separate
deep reading purchase inside V1. Future deeper readings can be planned later,
but V1 must feel complete on its own.

## Active Result Flow

The result is built around five sections:

1. `星盤定位`
   - Separately explains each person's emotional needs, communication style,
     affection style, action/conflict rhythm, and defense/delay pattern.
2. `兩個人的關係契合度分析`
   - Combines the two charts to show natural fit, effort areas, friction,
     attraction, emotional safety, communication, and pressure points.
3. `核心問題解讀`
   - Directly answers the user's selected question, such as whether the other
     person still cares, whether the relationship has a chance, whether to
     contact now, or whether to keep waiting.
4. `時機判讀`
   - Uses current transits and timing reducers as climate and action rhythm,
     not as guaranteed dates.
5. `行動方向`
   - Turns the evidence into next steps: contact, wait, soften, repair, avoid,
     or return attention to self.

## Runtime Contract

Active API route:

```text
POST /api/readings/relationship-result
```

Legacy compatibility route:

```text
POST /api/readings/free-result
```

The compatibility route must not define product direction. It exists only so
older callers do not break during construction.

Active view-model contract:

```text
contractVersion = "complete-relationship-result-v1"
westernRelationshipCaseFile.version = "western-relationship-case-file-v1"
readingBlueprint.version = "reading-blueprint-v1"
rulesetId = "western-relationship-result-v1"
questionBlueprintId = "western-relationship-result-v1"
```

Primary public fields:

```text
westernRelationshipCaseFile
relationshipProfiles
readingBlueprint.chapters
includedReadingRows
readableQuestionAnswer
timingGuidance
actionGuidance
narrative
evidence.western
methodBoundary
```

The active runtime must not emit:

```text
relationshipCaseFile
baziCompatibilityDiagnosis
evidence.bazi
freeChapters
lockedRows
lockedQuestions
paidExpansionPlan
paidUnlock
paidBoundary
freeSummary
paidDetailLocked
preciseDatesAvailableInFree
```

Some optional legacy TypeScript aliases may remain temporarily so old branch
work compiles, but generated fixtures, API payloads, frontend consumers, and
smoke tests must use the active field names above.

## Reading Method

The system should answer from deterministic evidence first:

```text
birth data + user context
    -> Western chart calculation
    -> relationship case file evidence clusters
    -> structured KB atoms/rules/question blueprint
    -> reducers for fit, question, timing, and action
    -> controlled narrative layer
```

The LLM is only allowed to turn selected evidence into natural language. It must
not invent chart facts, read the other person's mind, guarantee reconciliation,
or create precise timing promises.

## Active Docs

Use these for current implementation:

- `docs/product/00-current-v1-contract.md`
- `docs/product/07-reading-contract.md`
- `docs/product/09-frontend-flow-view-model.md`
- `docs/product/13-western-suskin-method-system.md`
- `docs/product/14-paid-v1-result-section-contract.md`
- `docs/product/20-production-commerce-legal-copy-zh-tw.md`
- `docs/tech/02-backend-architecture.md`
- `docs/tech/06-llm-prompt-strategy.md`
- `docs/tech/09-structured-kb-atoms-rules.md`
- `docs/research/11-western-relationship-method-bible.md`
- `docs/research/15-western-v1-reading-function-coverage.md`
- `docs/research/17-western-book-digestion-execution-matrix.md`

## Legacy Docs

These are historical references only unless rewritten:

- `docs/product/01-product-tiers.md`
- `docs/product/02-landing-page-flow.md`
- `docs/product/03-onboarding-questions.md` for monetization/framing only
- `docs/product/04-free-result-page.md`
- `docs/product/05-paid-report-structure.md`
- `docs/product/06-ritual-system.md`
- `docs/product/08-result-dashboard-design.md`
- `docs/product/12-astrology-session-handoff.md`
- `docs/tech/08-retriever-contract.md`

Any copy about free result pages, locked teasers, `NT$499`, `NT$2,480`, or
in-result upsells is not active for the current Western V1 product.

## Validation Gates

Before a runtime or frontend contract change is considered safe:

```bash
.venv/bin/python scripts/validate.py
.venv/bin/python scripts/compile_kb.py
.venv/bin/python scripts/structured_runtime_contract.py
.venv/bin/python scripts/structured_retrieval_smoke.py
.venv/bin/python scripts/smoke_western_complete_result_flow.py
.venv/bin/python scripts/smoke_western_context_matrix.py
.venv/bin/python scripts/smoke_western_timing_window_matrix.py
.venv/bin/python scripts/validate_paid_v1_result_section_contract.py
.venv/bin/python scripts/validate_book_digestion_execution_matrix.py
.venv/bin/python scripts/validate_method_claim_runtime_usage.py
.venv/bin/python scripts/validate_western_runtime_method_contract.py
cd apps/web && npm run typecheck && npm run build
```

`scripts/validate_supabase_structured_runtime.py` is expected to fail until the
hosted Supabase KB is synced to the current local structured KB contract. See
`docs/research/16-supabase-structured-kb-parity.md` for the latest read-only
parity check and the write command that requires explicit approval.
