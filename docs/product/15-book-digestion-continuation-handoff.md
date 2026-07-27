# 15 - Book Digestion Continuation Handoff
## Execution brief for continuing the proposed plan

Status: handoff for next Codex session.
Workspace: `/Users/novaos/Documents/valley-of-light-astrology`
Current branch: `codex/result-page-cosmic-v1`
Primary execution brief: `docs/research/20-western-book-digestion-master-plan.md`
Operating matrix: `docs/research/17-western-book-digestion-execution-matrix.md`
Paid V1 section contract: `docs/product/14-paid-v1-result-section-contract.md`

## Continuation Of The Proposed Plan

Continue the proposed plan exactly as an execution brief:

```text
Use docs/research/20-western-book-digestion-master-plan.md as the execution brief.

Goal:
Fully digest the current Western relationship astrology sources into the paid
V1 reading stack. Do not add new books unless a current source is blocked by
extraction quality. Work source-first: raw passage -> coverage row -> method
claim -> atom/rule/selector/guardrail -> runtime usage -> scenario proof ->
visible paid result.

Priority:
1. Reconfirm current source inventory and extraction quality.
2. Expand chapter-level coverage queues for P0/P1 sources.
3. Convert reviewed source sections into source-backed method claims.
4. Deepen function-specific sign templates, aspect pair templates, context
   policies, and timing reducer branches.
5. Wire changes into complete_relationship_result_runtime and readable
   Traditional Chinese output.
6. Add scenario tests proving profile, fit, question, timing, action, precision,
   and contact-status variations.
7. Regenerate coverage/runtime reports and run the paid V1 stack verifier.

Non-negotiables:
- The result remains paid-only Western V1 with five sections:
  星盤定位, 兩個人的關係契合度分析, 核心問題解讀, 時機判讀, 行動方向.
- LLM only writes from selected evidence; it must not invent chart facts.
- No BaZi payload/copy, no free/locked/upsell language, no precise outcome
  timing promises, no mind-reading, no single-aspect verdicts.
- Do not mark a source claim operational unless runtime traces and scenario
  tests prove it is used.
```

## Current Truth

The book digestion is not finished in the deeper sense.

The correct framing is:

- The project has completed an operational V1 digestion pass strong enough to
  power the paid result stack.
- The current books have not been fully exhausted.
- `docs/research/17-western-book-digestion-execution-matrix.md` still says the
  bottleneck is deeper extraction from existing books, not missing books.
- The active frontend/result-page work is Phase 7: making the visible paid
  result reflect already-digested runtime output. It must not replace book
  digestion.

Next sessions should continue from the P0/P1 backlog, especially sections that
make the visible result feel weak, generic, or insufficiently situation-aware.

## Already Done

Do not restart these from zero. Validate them if needed, then continue from the
remaining gaps.

### 1. Product Contract Is Set

The paid result is now a single Western V1 reading, not a free teaser plus
upsell funnel.

Current visible paid flow:

1. `星盤定位`
2. `兩個人的關係契合度分析`
3. `核心問題解讀`
4. `時機判讀`
5. `行動方向`

The active contract is documented in:

- `docs/product/00-current-v1-contract.md`
- `docs/product/14-paid-v1-result-section-contract.md`

The result must stay Western-only:

- no BaZi runtime payload/copy
- no free/locked/upsell language
- no static dummy result content
- no LLM-only answer unsupported by structured evidence

### 2. Backend Direction Is Set

The system direction is already decided:

```text
intake context
  -> Western chart calculation
  -> deterministic selectors and reducers
  -> source-backed structured KB
  -> controlled readable Traditional Chinese renderer
  -> LLM only for final natural-language wording where needed
```

Do not pivot to long wiki articles, vector-first retrieval, or LLM-first book
interpretation. The books are digested into method claims, atoms, rules,
selectors, guardrails, runtime traces, scenario tests, and visible surfaces.

### 3. Source Inventory And Extraction Quality Are Tracked

The current Western/cross-source inventory has already been audited.

Primary docs:

- `docs/research/sources.yml`
- `docs/research/21-western-source-inventory-audit.md`
- `docs/research/17-western-book-digestion-execution-matrix.md`

Current judgment:

- current books are enough to keep building paid V1
- bottleneck is deeper extraction from current sources
- do not add new books unless a current source is genuinely blocked by
  extraction quality or missing method coverage

### 4. Operational V1 Digestion Pass Exists

The current system has enough digestion to power paid V1 at an operational
level.

Already built:

- book digest YAMLs under `kb/book_digests/western/`
- coverage rows under `kb/book_coverage/western/current-sources-v1.yml`
- structured atoms under `kb/atoms/western/`
- rules under `kb/rules/western/`
- question blueprints under `kb/question_blueprints/western/`
- guardrails under `kb/guardrails/western/`
- runtime builder in `scripts/complete_relationship_result_runtime.py`
- readable interpretation layer under `scripts/readable_interpretation/`
- report and validation scripts under `scripts/`

Already active source lanes:

- Robert Hand, `Horoscope Symbols` for planet/sign/house/aspect grammar
- George/Bloch, `Astrology for Yourself` for natal synthesis method
- Rod Suskin, `Synastry` for relationship-reading method order
- Kevin Burk, `Astrological Relationship Handbook` for relationship needs and
  synastry trigger logic
- Forrest/Forrest, `Skymates` for relationship language and nonfatal synastry
- Robert Hand, `Planets in Transit` for timing climate
- Liz Greene, `Saturn` as a broad pressure/process guardrail only
- OPA ethics and Gottman repair/bids as source-guided situation-handling
  guardrails

### 5. Paid Result Surface Evidence Already Passes At Baseline

The current generated report says paid V1 result surfaces are traceable to live
runtime output:

- `docs/research/18-paid-v1-result-surface-evidence.md`

Important limitation:

- that report was generated before the newest OPA/Gottman action-boundary
  claims were fully wired
- after finishing the current slice, regenerate the report

### 6. Scenario Infrastructure Exists

The project already has scenario tests for:

- complete result flow
- context matrix
- chart variation matrix
- answer rule matrix
- answer layer
- when-to-contact matrix
- timing window matrix
- safety-validation language

The next work should extend these tests. Do not replace them with manual spot
checks.

### 7. Frontend Direction Is Set But Should Follow Runtime

The new result-page visual direction is the cosmic paid-result style from the
new landing/result design direction.

Frontend work is Phase 7 only:

- first deepen runtime evidence and readable output
- then make the visible result page display the live paid V1 sections
- do not use static copy to fake deeper reading quality

## Partially Done Now

The immediate unfinished slice is OPA/Gottman action-boundary digestion for:

- `核心問題解讀`
- `時機判讀`
- `行動方向`

The following source/coverage/digest files have already been started and are
currently uncommitted:

- `raw/cross/opa-ethics-source-note.txt`
- `raw/cross/gottman-bids-source-note.txt`
- `kb/book_digests/western/situation-framework-v1.yml`
- `kb/book_coverage/western/current-sources-v1.yml`

New method claims already added in the digest:

- `gottman-limited-reply-existing-channel-repair`
- `gottman-no-contact-low-stimulation-bid`
- `valley-shared-space-discretion-boundary`
- `valley-context-boundary-trace-not-evidence`

These claims are not complete until they are wired into runtime traces and
scenario tests.

Current repo status when this handoff was written:

```text
modified: kb/book_coverage/western/current-sources-v1.yml
modified: kb/book_digests/western/situation-framework-v1.yml
modified: raw/cross/gottman-bids-source-note.txt
modified: raw/cross/opa-ethics-source-note.txt
added:    docs/product/15-book-digestion-continuation-handoff.md
```

Meaning:

- source notes have been extended
- coverage rows have been moved from `mapped` to `implemented`
- digest claims have been added
- runtime mapping, method trace, scenarios, report regeneration, and validation
  still need to happen

## Immediate Runtime Work

Edit `scripts/complete_relationship_result_runtime.py`.

### 1. Update contact-situation method claim mapping

Set `CONTACT_SITUATION_METHOD_CLAIM_IDS` to include the new claims:

```python
CONTACT_SITUATION_METHOD_CLAIM_IDS = {
    "blocked": ["valley-contact-status-action-scale", "valley-blocked-contact-hard-boundary"],
    "no-contact": [
        "valley-contact-status-action-scale",
        "valley-no-contact-lowers-action-speed",
        "gottman-no-contact-low-stimulation-bid",
    ],
    "occasional-contact": [
        "valley-contact-status-action-scale",
        "gottman-contact-as-bid-not-proof",
        "gottman-limited-reply-existing-channel-repair",
    ],
    "still-in-contact": [
        "valley-contact-status-action-scale",
        "gottman-repair-tone-before-content",
        "gottman-limited-reply-existing-channel-repair",
    ],
    "living-or-working-together": [
        "valley-contact-status-action-scale",
        "valley-shared-space-discretion-boundary",
    ],
    "unknown": [
        "valley-context-modifies-action-not-conclusion",
        "valley-context-boundary-trace-not-evidence",
    ],
}
```

### 2. Update method-trace sections

In `WESTERN_METHOD_TRACE_SECTIONS`, add the new claims where they actually
belong.

Question section:

- `valley-context-boundary-trace-not-evidence`

Timing section:

- `gottman-no-contact-low-stimulation-bid`
- `valley-shared-space-discretion-boundary` only if timing trace evidence uses
  shared-space contact pacing.

Action section:

- `valley-shared-space-discretion-boundary`
- `valley-context-boundary-trace-not-evidence`
- `gottman-limited-reply-existing-channel-repair`
- `gottman-no-contact-low-stimulation-bid`

Do not add claims to every section just to inflate coverage. The trace should
prove the claim is relevant to the section.

## Immediate Scenario Work

Edit `scripts/smoke_western_context_matrix.py`.

Update contact-policy expectations so the new method claims are tested:

- `no-contact` must include `gottman-no-contact-low-stimulation-bid`.
- `occasional-contact` must include
  `gottman-limited-reply-existing-channel-repair`.
- `still-in-contact` must include
  `gottman-limited-reply-existing-channel-repair`.
- `living-or-working-together` must include
  `valley-shared-space-discretion-boundary`.
- Add or preserve an assertion that context remains a boundary/framing trace,
  not calculation evidence, when
  `valley-context-boundary-trace-not-evidence` is present.

The test should prove:

- contact status changes action boundaries and tone
- contact status does not create astrology conclusions
- timing cannot override blocked or unsafe contact boundaries
- limited replies are not treated as proof of love or commitment
- no-contact outreach stays one low-stimulation, easy-exit bid when allowed
- shared real-world space blocks public pressure, surveillance, or engineered
  contact

## Still Need To Be Done

### A. Finish The Current OPA/Gottman Slice

This is the next task. Do it before jumping to more book extraction.

Required completion:

1. Wire the four new method claims into
   `scripts/complete_relationship_result_runtime.py`.
2. Add/adjust context matrix assertions in
   `scripts/smoke_western_context_matrix.py`.
3. Regenerate reports.
4. Run validation.
5. Commit locally.

This slice is complete only when the new claims appear in runtime traces and
scenario tests prove they change the correct action/timing boundaries.

### B. Deepen P0 Book Sections

After the current slice, return to P0 rows in
`docs/research/17-western-book-digestion-execution-matrix.md`.

P0 gaps still needing deeper digestion:

- George/Bloch natal synthesis sequence
- George/Bloch Sun/Moon/Asc profile method
- George/Bloch aspect synthesis cross-check
- Robert Hand aspect synthesis foundation
- Suskin initial comparison orientation
- OPA third-party/client-agency boundary depth

Output expected from each deepened section:

```text
source range
  -> coverage row
  -> method claim
  -> atom/rule/selector/guardrail
  -> runtime trace
  -> scenario proof
  -> readable Chinese surface
```

### C. Deepen P1 Book Sections

P1 gaps still needing deeper digestion:

- Burk pair-family templates
- Burk safety/validation language
- Forrest/Forrest pivotal interaspect selection
- Forrest/Forrest Venus/Mars relating styles
- Hand `Planets in Transit` timing branch combinations
- Greene Saturn depth, but only after a better usable extraction is available

Do not unblock composite/Davison or house-overlay claims until calculation and
precision support exists.

### D. Improve The Reading Quality Where It Still Feels Generic

The known weak areas are:

- profile cards can still sound too generic in some planet/sign combinations
- fit summary needs stronger natural/effort/friction language
- question answer needs clearer "why this judgment" evidence ordering
- timing branch examples are still too Saturn-heavy in some example reports
- action guidance needs more situation-specific boundaries and phrasing

Fix these through source digestion and reducers first, then readable Chinese
templates, then frontend layout.

### E. Keep Building Test Coverage For Variations

Future scenario coverage should continue expanding across:

- main question family
- contact status
- emotional risk
- desired outcome
- relationship stage
- missing birth time
- missing or unreliable location
- timing selector branches
- profile function/sign variations
- repeated-theme synastry patterns

The test should prove the result changes for the right reason, not merely that
the API returns data.

## Reports To Regenerate

After runtime and test wiring, regenerate:

```bash
.venv/bin/python scripts/report_book_digestion_execution_matrix.py
.venv/bin/python scripts/report_method_claim_runtime_usage.py
.venv/bin/python scripts/report_paid_v1_result_surface_evidence.py
```

Also run this if coverage/report staleness changes:

```bash
.venv/bin/python scripts/report_structured_kb_coverage.py
```

## Validation Commands

Run these before committing:

```bash
.venv/bin/python scripts/validate_book_digests.py
.venv/bin/python scripts/validate_book_coverage.py
.venv/bin/python scripts/validate_method_claim_runtime_usage.py
.venv/bin/python scripts/smoke_western_context_matrix.py
.venv/bin/python scripts/verify_paid_v1_reading_stack.py --include-web
git diff --check
```

If frontend files are touched, also run:

```bash
cd apps/web
npm run typecheck
npm run build
npm run smoke:dashboard
```

## Commit Guidance

Commit after the validation passes.

Suggested commit message:

```text
Complete action-boundary book digestion wiring
```

Do not push unless the user explicitly asks in the new session.

## Next Book-Digestion Move After This Slice

After the OPA/Gottman action-boundary slice is wired and validated, return to
the execution matrix backlog.

Highest-value next targets:

1. George/Bloch natal synthesis and Sun/Moon/Asc profile method.
   - Goal: make `星盤定位` less generic and more method ordered.
   - Runtime targets: `relationshipProfiles`, `identityNeeds`,
     `functionElementMatrix`, `functionModalityMatrix`, `precisionWarnings`.

2. Robert Hand aspect synthesis foundation.
   - Goal: make `兩個人的關係契合度分析` explain why specific contacts matter
     without dumping aspects.
   - Runtime targets: `aspectFunctionCombination`,
     `aspectContactModifier`, `aspectSynthesisCrossCheck`.

3. Suskin initial comparison orientation.
   - Goal: keep element/luminary comparison as orientation, not verdict.
   - Runtime targets: `elementComparison`, `luminaryComparison`,
     `fitSummary`, `aspectPriority`.

4. Burk/Forrest pair-family templates.
   - Goal: improve attraction, safety, communication, pressure, and repair
     cards with relationship-function language.
   - Runtime targets: `aspectPairContactTemplate`,
     `aspectFunctionCombination`, `safetyValidationLanguage`.

5. Hand `Planets in Transit` timing reducers.
   - Goal: deepen Mercury, Venus, Mars, Saturn, and Moon timing branches while
     keeping exact-date promises blocked.
   - Runtime targets: `timingMercuryCommunication`,
     `timingVenusSoftening`, `timingMarsActivation`,
     `timingSaturnPressure`, `timingMoonWeather`, `timingContactReducer`.

## Rules For Future Sessions

- Do not claim the books are fully digested.
- Do not buy new books before the P0/P1 backlog is much smaller.
- Do not use long wiki articles as the runtime engine.
- Do not use vector search as the primary reading selector.
- Do not let user-written relationship context become evidence of the other
  person's feelings.
- Do not rewrite visible Chinese copy as a substitute for missing reducers.
- When visible output feels weak, deepen the relevant source claim, atom/rule,
  reducer, runtime trace, and scenario test first.

## Completion Criteria For The Full Proposed Plan

The broader book-digestion goal is complete only when:

- Every active P0/P1 source section in
  `docs/research/17-western-book-digestion-execution-matrix.md` is either
  implemented with runtime/scenario proof or explicitly blocked with a real
  reason.
- `docs/research/18-paid-v1-result-surface-evidence.md` proves all five
  visible paid sections are backed by structured runtime output.
- `docs/research/13-western-method-claim-runtime-usage.md` shows no important
  paid-result claims sitting unused.
- Scenario tests prove variation across profile, fit, question, timing, action,
  precision, contact status, emotional risk, and desired outcome.
- The paid result UI shows the five-section flow using live runtime data, with
  no old free funnel, locked-row, upsell, BaZi, dummy, or static result content.
