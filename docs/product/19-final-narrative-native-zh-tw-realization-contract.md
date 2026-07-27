# Final Narrative Native Traditional Chinese Realization Contract

## Status

- R0 current-output inventory: complete
- R1 native Chinese contract: complete
- R2 prose-free meaning frame: complete
- R3 chart-positioning renderer migration: complete
- R4 relationship-signal renderer migration: complete
- R5 visible renderer unification: complete
- R6 hard Chinese quality gates: complete
- R7 sentence-review workflow: pending
- R8 rebuilt calibration and human acceptance: pending

This document follows the canonical R0-R8 roadmap numbering. Historical report filenames created by
the earlier side task label chart positioning as R2 and relationship fit as R3; those filenames are one
number behind and are retained only to avoid artifact churn.

R0-R2 establish the baseline, contract, and prose-free meaning boundary. R3 is the first production
migration and changes only chart-positioning visible copy without weakening typed facts, evidence
ownership, page ownership, or safety boundaries. R4 applies the same architecture to relationship
signals. R5 moves all five visible pages onto the same typed-frame and approved-catalog boundary while
keeping their visible wording and narrative jobs separate. R6 enforces the native Chinese contract at
the shared final composition boundary and fingerprints that policy into generated calibration artifacts.

## Problem

The current renderer can produce structurally valid but unnatural Chinese because it inserts internal semantic labels into generic sentence templates. Existing checks prove that forms exist, differ, stay within page length, and avoid technical IDs. They do not prove that a Taiwanese reader can understand the sentence naturally.

Examples permanently registered as regressions include:

- `理解彼此原本的親密關係節奏`
- `你希望關係能誠實談方向，也能保留各自的生活。`
- `你先談做法和後果，才相信問題能處理；對方只談感覺時，你們容易各自錯過重點。`
- `集中時，你的靠近和處理衝突的速度一明顯，他的表達好感的方式也會被帶動。`

## Required Pipeline

```text
typed fact
  -> ReaderMeaningFrame
  -> page-owned ReaderParagraphPlan
  -> approved paragraph-role zh-TW catalog
  -> page-owned composition
  -> automated contract gates
  -> human acceptance
```

The `ReaderMeaningFrame` is prose-free. It carries only stable semantic keys:

- page and field ownership
- semantic role and scene key
- source fact, source-binding fingerprint, and evidence IDs
- realization purpose
- certainty level
- person direction
- signal pair and aspect behavior

It cannot contain `text`, `copy`, `headline`, `body`, `advice`, `sentence`, or template fragments.

The `ReaderParagraphPlan` is the required layer between facts and visible Chinese. It chooses one
page conclusion, orders supporting facts by discourse role, and prevents each fact from demanding an
independent visible sentence. Approved catalog entries are written for their paragraph position, such
as opening, evidence, contrast, condition, action, or boundary. Adding transition words in front of an
old standalone sentence is not a valid paragraph realization.

## Visible Chinese Rules

1. Every sentence expresses one reader-facing idea.
2. Every sentence has an understandable person, action, or observable response.
3. Internal planet-function labels never appear directly.
4. Aspect meaning selects a complete sentence family; labels such as `集中` or `易卡` are never inserted into a template.
5. Person direction, uncertainty, chart meaning, and page ownership must be preserved.
6. Missing approved copy fails closed. Generic fallback is forbidden.
7. Runtime LLM generation is forbidden. Runtime wording remains deterministic and reviewable.
8. Headings describe the relationship directly and never explain page scope or navigation.
9. Headings are complete thoughts. Colon-spliced generic tags are forbidden.
10. Guidance and observation fields use complete statements, not `是否` / `會不會` question fragments.
11. One page has one leading conclusion. Other facts may explain, contrast, support, qualify, or bound it;
    they may not introduce competing conclusions.
12. Sentence catalogs are paragraph-role specific. Standalone fact sentences cannot be concatenated or
    wrapped with generic connectors such as `同時`、`但`、`而且` to simulate coherence.

## Versioned Artifacts

- Contract: `data/reading-quality-cases/final-narrative-native-zh-tw-contract-v1.json`
- Reader regressions: `data/reading-quality-cases/final-narrative-native-zh-tw-regressions-v1.json`
- R0 inventory: `data/reading-production-calibration/native-zh-tw-v1/r0-realization-inventory.json`
- R0/R1 report: `docs/research/37-final-narrative-native-zh-tw-r0-r1.md`
- R3 chart-positioning report (historical filename uses R2): `docs/research/38-final-narrative-native-zh-tw-r2-chart-positioning.md`
- R4 relationship-signal report (historical filename uses R3): `docs/research/39-final-narrative-native-zh-tw-r3-relationship-fit.md`
- Contract implementation: `scripts/readable_interpretation/final_narrative_chinese_contract.py`
- Meaning frame: `scripts/readable_interpretation/final_narrative_chinese_plan.py`
- R3 chart approved catalog: `scripts/readable_interpretation/final_narrative_pages/chart_positioning_zh_tw_catalog.py`
- R3 chart production verifier: `scripts/verify_final_narrative_chart_positioning_native_zh_tw.py`
- R4 relationship approved catalog: `scripts/readable_interpretation/final_narrative_pages/relationship_fit_zh_tw_catalog.py`
- R4 relationship production verifier: `scripts/verify_final_narrative_relationship_fit_native_zh_tw.py`
- R5 shared prose-free signal service: `scripts/readable_interpretation/final_narrative_signal_service.py`
- R5 core-answer catalog: `scripts/readable_interpretation/final_narrative_pages/core_answer_renderer.py`
- R5 timing catalog: `scripts/readable_interpretation/final_narrative_pages/timing_renderer.py`
- R5 action catalog: `scripts/readable_interpretation/final_narrative_pages/action_direction_renderer.py`
- R5 production verifier: `scripts/verify_final_narrative_r5_page_realizers.py`
- Paragraph-plan contract: `scripts/readable_interpretation/final_narrative_paragraph_plan.py`
- Paragraph-plan production verifier: `scripts/verify_final_narrative_paragraph_plans.py`
- Five-chapter story allocation: `scripts/readable_interpretation/final_narrative_story_arc.py`
- Story progression verifier: `scripts/verify_final_narrative_story_arc.py`
- R5 implementation report: `docs/research/40-final-narrative-native-zh-tw-r5-page-unification.md`
- R6 hard-quality implementation: `scripts/readable_interpretation/final_narrative_chinese_quality.py`
- R6 machine contract: `data/reading-quality-cases/final-narrative-native-zh-tw-quality-contract-v1.json`
- R6 production verifier: `scripts/verify_final_narrative_r6_chinese_quality.py`
- R6 implementation report: `docs/research/41-final-narrative-native-zh-tw-r6-hard-gates.md`

## R3 Chart-Positioning Contract

Chart-positioning uses one explicit realization purpose per owned fact:

- `user-emotional-need`: direct emotional need
- `user-communication-style`: communication under disagreement
- `partner-pressure-response`: his response under pressure
- `precision-mode`: chart-data boundary

Moon may change `headline` and `meaning`. Mercury may change only `meaning`. Pressure may change `headline`, `body`, and `nextMove`. Precision may change only `caution`. Question, relationship status, contact status, emotional risk, and arbitrary renderer seeds cannot select chart wording.

Every visible chart sentence must reproduce an approved catalog entry and match the source role and value in the typed fact contract. Known values have no fallback. Unknown values use approved disclosure copy and must be recorded in fallback diagnostics. A missing entry, stale fingerprint, wrong fact ID, missing evidence, duplicate fact, wrong field, wrong purpose, or untraceable sentence fails closed.

## R5 Page-Job Contract

All five pages use typed facts, `ReaderMeaningFrame`, exact sentence traces, and approved native zh-TW
catalogs. `relationshipThesis` and `relationshipCaseModel` remain the shared, prose-free storyline
controller, but they cannot write the same finished explanation onto multiple pages.

All five pages also create exactly one `ReaderParagraphPlan` at runtime. The plan must include every
required page-owned role, preserve source-fact identity, and place each role in a reviewed discourse
position. Missing roles, duplicate facts, cross-page frames, unsupported discourse relations, stale plan
versions, hidden support facts promoted into visible steps, and output that no longer follows the plan
fail closed.

| Page | One visible job | Must not become |
| --- | --- | --- |
| `chart-positioning` | Explain each person's emotional, communication, and pressure patterns. | A breakup, contact, timing, or relationship-outcome answer. |
| `relationship-fit` | Explain how the two personal patterns attract, clash, and adjust together. | A selected-question answer or contact recommendation. |
| `core-answer` | Directly answer the selected question using status, contact, uncertainty, and relevant chart evidence. | A full recap of every other page. |
| `timing-reading` | Explain when interaction is more or less workable and what the current contact boundary permits. | A relationship-type summary or prediction of guaranteed results. |
| `action-direction` | Give one purpose, one practical next move, its completion boundary, and one stopping condition. | A second core-answer page or abstract relationship theory. |

The five pages form one ordered argument:

1. `chart-positioning` establishes the two personal patterns.
2. `relationship-fit` shows what those patterns create together.
3. `core-answer` gives the verdict for the selected question and current context.
4. `timing-reading` states when that verdict is more or less workable.
5. `action-direction` closes with one bounded resolution.

Every fact has a separate presentation disposition. `visible-claim` and `visible-boundary` facts may
enter paragraph steps. `hidden-support` and `hidden-routing` facts may select or constrain a visible
claim, but cannot receive their own sentence. In particular, `core-answer.central-dynamic`,
`core-answer.partner-relationship-need`, and `action-direction.repair-lever` must remain hidden. A new
fact never earns visible copy merely because it was emitted.

`relationship-fit` and `core-answer` share only the prose-free relationship-signal resolver. They must
use separate page-owned sentence catalogs. The same signal therefore keeps one semantic identity and
evidence direction while producing wording suited to each page's job. Exact visible wording reuse
between those pages is a release failure. Their pair-specific catalogs must also diverge before a
sentence becomes recognizable as the same opening; the automated gate currently allows at most 18
shared leading characters.

Timing windows use explicit pair subjects and reviewed category-by-aspect sentences. The date, interaction
topic, and likely response must form one natural Chinese sentence; semantically unrelated catalog fragments
cannot be joined into visible prose. Vague phrases such as `反應會來得集中`, `會更明顯`, or an unexplained
positive/negative join are forbidden. Action copy must state its purpose, concrete command, completion
boundary, and stopping condition; blocked contact always resolves to a boundary-only action before
realization.

## R6 Hard-Quality Contract

R6 is enforced inside `validate_section_composition()`, after page grammar is checked and before a
finished page can enter the five-page reading. A renderer cannot opt out by omitting its own local
audit. Page grammar and native-language failures are normalized to the shared composition error type.

Every visible field must pass all of these release conditions:

- every warning from the base native Chinese contract is promoted to a hard failure
- internal labels, abstract model terminology, page-navigation narration, and all registered reader
  complaints are forbidden
- non-headline sentences must contain a reader-facing person, interaction, event, or data subject
- unclear positive/negative joins, repeated conjunction chains, excessive sentence load, and page-topic
  leakage are rejected
- colon-spliced headings, abstract initiative movement, weight metaphors such as `小事變重`, and
  question fragments presented as guidance are rejected
- wrong-person pronouns, attraction/defense clauses joined without a natural transition, and adjacent
  relationship-fit sentences that repeat the same opening are rejected
- dated timing sentences must explicitly identify `你們` as the affected pair
- the action page must contain a concrete command, a completion boundary, and a stopping condition

The versioned R6 policy and its contract fingerprint are embedded in both Phase 5 and Phase 7 corpora,
review manifests, and frontend review fixtures. Runtime source hashes include the policy implementation
and machine contract. A policy-only change therefore makes calibration artifacts stale until they are
rebuilt and reverified.

The R6 verifier exhaustively checks approved catalog sentence forms, all 500 Phase 7 matrix readings,
exact sentence traces, historical complaints, and deliberate invalid mutations. It is a required backend
and generated-report step in `verify_paid_v1_reading_stack.py`.

## Migration Rule

The page migration is complete. All five visible page realizers are in hard-gate catalog mode. There
is no baseline renderer, upstream prose slot, or global-storyline path allowed to rewrite their copy.

For each migrated page:

1. Build a `ReaderMeaningFrame` from its owned typed facts.
2. Realize every frame through approved full-sentence zh-TW catalogs.
3. Remove access to visible internal labels and generic fragment templates.
4. Promote that page's contract checks from audit findings to hard failures.
5. Rebuild the calibration corpus and human-review queue after every meaning or catalog change.

No new upstream semantic value may reach a migrated page until its meaning frame and visible realization are both covered and approved.

R7-R8 remain required before declaring the entire final Chinese layer human-accepted for production.
R6 completion means the renderer architecture and automated Chinese release boundary are ready; it does
not replace sentence review or human acceptance.

## Future Upgrade Integration Contract

This contract applies to every future change that can alter a paid reading, including:

- calculation methods and settings, including house systems such as Placidus
- new natal, synastry, transit, angle, house, or aspect signals
- KB claims, atoms, rules, retrieval fields, and relationship-model outputs
- onboarding status, question, contact, risk, and precision inputs
- new result sections, semantic roles, values, qualifiers, or safety boundaries

An upstream feature is not complete merely because its calculation or structured output exists. It is
complete only when its supported meaning reaches the correct visible page through this path:

```text
upstream input
  -> normalized source-backed evidence
  -> page-owned typed fact
  -> five-chapter story allocation
  -> visible ReaderMeaningFrame or hidden paragraph support
  -> page-owned ReaderParagraphPlan
  -> approved paragraph-role native zh-TW catalog
  -> deterministic page composition
  -> semantic, ownership, calibration, and human-review gates
```

### Required work for a new semantic family

1. Define stable values, qualifiers, evidence IDs, confidence, and precision requirements upstream.
2. Assign each complete visible proposition to one owning page and field. Shared storyline facts may
   support other pages only through a hidden disposition.
3. Register its typed fact role/value policy and include all relevant inputs in source-binding fingerprints.
4. Map the fact to a prose-free `ReaderMeaningFrame` with an explicit realization purpose.
5. Assign the frame a discourse role in the owning page's `ReaderParagraphPlan`; do not append a new
   visible sentence merely because a new fact exists.
6. Add reviewed, complete Traditional Chinese realizations written for that paragraph role.
7. Add exhaustive value coverage, invalid-value rejection, stale-fingerprint, and unowned-evidence tests.
8. Add one-input metamorphic tests proving the intended page changes and unrelated pages do not change.
9. Rebuild calibration artifacts and add representative and boundary cases to the human-review queue.

If the upgrade reuses an existing role and value without changing its meaning, it may reuse the existing
catalog entry. If it adds or changes meaning, it must introduce an explicit versioned value and approved
realization. Unknown or unsupported values must fail closed. They must never fall back to generic prose,
internal terminology, raw calculation text, or runtime LLM wording.

### House-system requirements

House-system support is an upstream calculation feature and a downstream semantic family. The final
Chinese layer remains house-system agnostic, but every house-derived fact must carry enough provenance to
prevent stale or misleading copy:

- include `houseSystem`, reliable birth-time/location precision, subject direction, house/cusp identity,
  and calculation version in evidence or source-binding fingerprints
- suppress houses, angles, and overlays when required birth data is unavailable or unreliable
- keep natal house meanings in `chart-positioning` and synastry planet-in-house overlays in
  `relationship-fit`, unless a reviewed page contract assigns a narrower downstream conclusion
- do not let raw house numbers or labels become reader-facing sentences
- test a house-system or birth-time change as a one-input mutation and verify only house-owned meanings
  change

### Release invariant

Every future upgrade must satisfy both sides of the contract:

1. Its supported input changes produce a traceable, specific, approved Chinese interpretation.
2. It cannot alter unrelated page topics, bypass page ownership, weaken readability, or reintroduce
   repeated global narrative.

If either condition is unproven, the feature is not connected to the final result layer and is not ready
for release.
