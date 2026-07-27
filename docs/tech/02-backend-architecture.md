# 02 - Backend Architecture
## Western-only astrology branch

> Current state: the astrology branch runtime is a Next.js API route that calls
> Python calculation/build scripts. The active complete relationship reading
> backend is Western astrology only. Legacy BaZi modules remain in the
> repository for the separate BaZi branch and historical reference.

---

## Runtime Flow

```text
apps/web intake UI
  -> POST /api/readings/relationship-result
  -> apps/web/src/app/api/readings/relationship-result/route.ts
  -> scripts/build_relationship_result_from_reading.py
  -> scripts/complete_relationship_result_runtime.py
  -> calculation/western/*
  -> structured KB compile artifacts
  -> westernRelationshipCaseFile
  -> readingBlueprint
  -> deterministic readable result fields
  -> CompleteRelationshipResultViewModel JSON
  -> dashboard
```

The API response must use these primary fields:

- `contractVersion`
- `westernRelationshipCaseFile`
- `relationshipProfiles`
- `readingBlueprint`
- `answerGuidance`
- `timingGuidance`
- `actionGuidance`
- `evidence.western`
- `includedReadingRows`

The active astrology runtime must not emit:

- `relationshipCaseFile`
- `baziCompatibilityDiagnosis`
- `evidence.bazi`
- `debug.baziSlot`

---

## Main Modules

```text
apps/web/
  src/app/api/readings/relationship-result/route.ts  # primary runtime API adapter
  src/app/api/readings/free-result/route.ts          # legacy compatibility route
  src/data/complete-relationship-result.ts                    # frontend TypeScript contract
  scripts/smoke-dashboard.mjs                # end-to-end dashboard/API smoke

calculation/western/
  immanuel_adapter.py                        # chart adapter and precision gates
  signals.py                                 # relationship aspect categorization

kb/
  atoms/western/*.yml                        # executable meaning atoms
  rules/western/*.yml                        # deterministic reducers
  question_blueprints/western/*.yml          # answer shape by user question
  guardrails/western/*.yml                   # blocked claims and safety gates

wiki/western/
  **/*.md                                    # source-backed method articles

scripts/
  complete_relationship_result_runtime.py              # active Western-only view-model builder
  compile_kb.py
  structured_runtime_contract.py
  structured_retrieval_smoke.py
  build_relationship_result_view_models.py            # fixture CLI entrypoint
  build_free_result_view_models.py                    # legacy compatibility fixture shell
  build_relationship_result_from_reading.py
  smoke_western_complete_result_flow.py
  smoke_western_context_matrix.py
  smoke_western_chart_variation_matrix.py
```

---

## Calculation Layer

The Western calculation layer currently provides:

- tropical zodiac chart positions
- relationship points: Moon, Mercury, Venus, Mars, Saturn, Descendant where precision allows
- interchart synastry candidates
- relationship signal categories: attraction, emotional safety, pressure, communication, repair
- current transit snapshot evidence
- precision gates for missing time/place

Birth city is optional. Missing city uses `location_fallback`; the reading still
succeeds. Time/place-sensitive claims are blocked unless reliability is high
enough.

Known prototype limits:

- arbitrary city geocoding/timezone resolution is not production-grade yet
- current transit timing is a snapshot, not a paid timing-window scan
- composite/Davison relationship chart layers are deferred
- unrecognized nonblank city handling should be upgraded before launch

---

## Structured KB Layer

The KB v2 design is not a long-article RAG system. Articles are source evidence;
YAML is execution logic.

```text
Markdown source articles
  -> claims and citations
  -> YAML atoms
  -> YAML rules
  -> question blueprints
  -> guardrails
  -> compiled JSON
  -> runtime selector/reducer
```

Current source-backed Western method families include:

- Suskin relationship method order
- natal relationship potential
- initial element comparison
- interchart aspect priorities
- relationship chart layer limits
- consultation ethics
- Hand symbol foundations
- planetary functions
- sign, element, and modality foundations
- point-specific sign interpretation for Moon, Mercury, Venus, Mars, and Saturn

The runtime should prefer deterministic selection:

- select relevant clusters
- reduce them by question/stage/contact/risk
- attach `claimSupport`
- pass only the selected evidence to deterministic readable result fields

Vector search can be added later for discovery and AI Q&A, but relationship-result
execution should remain rule-first.

---

## Deterministic Reading Layer

The runtime builds user-facing copy from:

- `westernRelationshipCaseFile`
- `readingBlueprint`
- `relationshipProfiles`
- `answerGuidance`
- `timingGuidance`
- `actionGuidance`
- `includedReadingRows`

The relationship-result API does not call a runtime LLM provider. Copy changes
should be made by improving structured atoms/rules/selectors/readable templates
and the frontend renderer.

The deterministic layer enforces:

- blueprint chapter order
- method and precision boundaries
- no invented chart facts
- no legacy BaZi payload/copy
- no exact-date promises
- no mind-reading claims

---

## Data Stack Direction

Production target:

- hosted Supabase Postgres
- Postgres full-text search as primary KB search
- pgvector as secondary semantic retrieval
- Markdown for source articles
- YAML for atoms, rules, blueprints, and guardrails
- Python + Pydantic-style validation for local and CI checks

Local dev/test:

- compiled JSON artifacts for deterministic runtime
- optional SQLite FTS5 cache only if it speeds local inspection
- no local Supabase or Docker requirement

Production Supabase writes require explicit approval.

---

## API Contract

`POST /api/readings/relationship-result`

`POST /api/readings/free-result` remains as a legacy compatibility route during
the migration, but new consumers should use `/relationship-result`.

Input:

```json
{
  "personA": {
    "birthDate": "1992-06-18",
    "birthTime": "14:30",
    "birthPlace": "台北市"
  },
  "personB": {
    "birthDate": "1990-10-03",
    "birthTime": "09:15",
    "birthPlace": "台北市"
  },
  "context": {
    "relationship_stage": "crisis",
    "main_question": "still-love-me",
    "contact_status": "still-in-contact"
  }
}
```

Output:

```json
{
  "contractVersion": "complete-relationship-result-v1",
  "westernRelationshipCaseFile": {
    "version": "western-relationship-case-file-v1"
  },
  "readingBlueprint": {
    "version": "reading-blueprint-v1",
    "chapters": []
  },
  "relationshipProfiles": {},
  "answerGuidance": {},
  "timingGuidance": {},
  "actionGuidance": {},
  "evidence": {
    "western": {}
  },
  "includedReadingRows": []
}
```

The real response contains more dashboard fields, but these are the contract
anchors the backend must protect.

---

## Validation

High-signal checks for backend contract changes:

```bash
.venv/bin/python scripts/validate.py
.venv/bin/python scripts/compile_kb.py
.venv/bin/python scripts/lint_kb.py
.venv/bin/python scripts/structured_runtime_contract.py
.venv/bin/python scripts/structured_retrieval_smoke.py
.venv/bin/python scripts/build_relationship_result_view_models.py
.venv/bin/python scripts/smoke_western_complete_result_flow.py
.venv/bin/python scripts/smoke_western_context_matrix.py
.venv/bin/python scripts/smoke_western_chart_variation_matrix.py
npm run typecheck
npm run build
git diff --check
```

Dashboard smoke should also be run after API, readable-result, or frontend contract
changes.

---

## Remaining Architecture Debt

The active relationship-result assembly now enters through
`scripts/complete_relationship_result_runtime.py`. The new fixture command is
`scripts/build_relationship_result_view_models.py`; the older
`scripts/build_free_result_view_models.py` remains as a compatibility shell.
The old shell no longer carries the mixed-system helper implementation.

After that, prioritize:

1. hosted geocoder/timezone resolver
2. richer timing-window scanner
3. broader chart-variation fixtures
4. composite/Davison layer
5. Supabase Postgres schema and import pipeline
