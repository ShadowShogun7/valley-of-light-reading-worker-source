# 06 - LLM Prompt Strategy
## Western-only astrology branch

> Current rule: **the LLM writes the reading; it does not decide the astrology.**
> Calculation, method order, selectors, reducers, guardrails, and method/precision
> boundaries are deterministic before the model is called.

---

## Current Runtime

The astrology branch complete relationship result is Western-only internally.

```text
intake context
  -> Western chart calculation
  -> westernRelationshipCaseFile
  -> structured KB atoms + rules + guardrails
  -> readingBlueprint
  -> narrative prompt
  -> narrative post-processing
  -> CompleteRelationshipResultViewModel
```

The prompt must not receive or ask for legacy BaZi runtime payloads:

- no `relationshipCaseFile`
- no `baziCompatibilityDiagnosis`
- no `evidence.bazi`
- no BaZi method terms such as 配偶星、日主、四柱、十神

BaZi source code and docs can remain in the repository for the separate BaZi
branch, but they are not part of this branch's relationship reading evidence
pack.

---

## LLM Role

The LLM may:

- rewrite deterministic conclusions into warm Traditional Chinese
- connect the assigned evidence into a clear three-chapter story
- soften sensitive language for breakup context
- preserve method, precision, and safety boundaries

The LLM may not:

- invent chart placements, aspects, houses, timing windows, or psychological facts
- change chapter order or replace assigned evidence
- turn sign placements into mind-reading or proof of love
- make absolute predictions or precise timing guarantees
- claim house, Ascendant, Descendant, or overlay interpretation when precision gates block them

---

## Complete Result Evidence Pack

The narrative prompt receives these primary objects:

```json
{
  "context": "relationship stage, question, contact status, desired outcome, safety/risk flags",
  "westernRelationshipCaseFile": "calculated Western relationship diagnosis",
  "relationshipProfiles": "person A/person B function profiles and fit summary",
  "readingBlueprint": "deterministic execution plan for the narrative",
  "includedReadingRows": "included result sections and preview bullets"
}
```

The active builder that prepares this evidence pack is
`scripts/complete_relationship_result_runtime.py`.

`westernRelationshipCaseFile` is the technical source of truth. It contains:

- `inputQuality`: birth-time/place precision gates for each person
- `identityLayer`: Moon, Mercury, Venus, Mars, Saturn, and Descendant needs where available
- `synastryLayer`: attraction, emotional safety, pressure, communication, and repair aspects
- `timingLayer`: current transit evidence with method limits
- `evidenceClusters`: structured KB-backed clusters selected by the runtime
- `answerLayer`: deterministic answer, because-points, therefore, and included sections

`readingBlueprint` is the narrative source of truth. It contains:

- `suggestedResultTitle` and `resultTitleSeeds`
- `storyArc`
- exactly three `chapters`
- assigned evidence for each chapter
- `includedReadingPlan` and `forbiddenClaims`

---

## Evidence Order

The free reading follows this method order:

1. Natal and method foundation first:
   `methodOrder`, `natalSymbolFoundation`, `planetaryFunctions`,
   `signClassificationFoundation`, `elementStyleFoundation`,
   `modalityResponseFoundation`
2. Individual relationship style:
   `identityNeeds`, `planetSignStyle`, `moonSignEmotionalSafety`,
   `mercurySignCommunicationRepair`, `venusSignAffectionStyle`,
   `marsSignPursuitConflict`, `saturnSignDefenseDelay`
3. Synastry evidence:
   `relationshipPotential`, `elementComparison`, `luminaryComparison`,
   `attraction`, `emotionalSafety`, `communication`, `pressure`, `repair`,
   `aspectPriority`, `aspectInterpretationFoundation`
4. Precision-limited layers:
   `birthDataQuality`, `ascendantImpression`, `houseRelationshipFactors`,
   `angleHouseFramework`, `relationshipChartLayer`
5. Context and action boundary:
   `relationshipStage`, `contactStatus`, `emotionalRisk`, `desiredOutcome`,
   `currentTransits`, `consultationSafety`

The model sees only selected evidence in `readingBlueprint.chapters`. It
should not pull in unused clusters on its own.

---

## Chapter Contract

The complete result answers the user's question through three core narrative
chapters:

```text
thoughts -> "他現在怎麼想"
reasons  -> "你們卡住的原因"
chance   -> "還有沒有機會"
```

Each chapter must:

- use only its assigned `evidence`
- include the assigned `coreSummary`
- keep `technicalReading` grounded in chart facts and claim support
- keep `psychologicalSummary` as an emotional translation of the same evidence
- preserve method and precision limits
- avoid every `forbiddenClaims` item

Post-processing enforces chapter order, titles, result-title fallback, evidence
refs, and missing technical/psychological layers.

---

## Precision Guardrails

Birth city is optional. Missing city uses `location_fallback`; it does not fail
the reading.

The prompt must obey these gates:

- no birth time: Moon confidence may be low, and Asc/Desc/houses are blocked
- no reliable place: house, Ascendant, Descendant, and overlay claims are blocked
- unknown city that cannot be resolved: chart precision must be downgraded or blocked rather than invented
- relationship chart layers remain deferred unless the runtime calculates them
- current timing is trend-level guidance, not a precise guaranteed contact date

The model may explain that city and exact time improve precision, but it must
not pressure the user to provide them as required fields.

---

## Prompt Shape

The runtime prompt should be blueprint-first:

```text
System:
  You are a Western astrology relationship analyst for Valley of Light.
  Use Traditional Chinese. Be warm, precise, and non-fatalistic.
  Do not invent chart facts. Do not use BaZi. Do not promise outcomes.

Context:
  User relationship context and selected question.

Evidence:
  readingBlueprint
  westernRelationshipCaseFile
  relationshipProfiles
  includedReadingRows

Task:
  Write the complete relationship narrative using exactly the blueprint chapters.
  Answer first, explain second, preserve method and precision boundaries.

Output:
  JSON NarrativeLayer:
    mode
    resultTitle
    spine
    emotionalFrame
    chapters[]
```

The model should cite authority through evidence labels, source IDs, and claim
support already attached by the runtime. It should not paste raw source quotes
into the consumer reading unless a product surface explicitly asks for that.

---

## QA And Future Deep Readings

The same principle applies to future Q&A or deeper reading modules:

- deterministic systems prepare the chart state, selected atoms, applicable rules, and guardrails
- LLM is used for question answering and narrative expansion
- retrieval may add extra KB context, but only after deterministic selectors reduce the surface
- richer timing may use a future timing-window scanner; the result must not expose
  precise guaranteed windows until that layer exists

For AI Q&A, the model may answer user-specific follow-up questions, but it must
still stay inside:

- calculated Western facts
- applicable structured atoms/rules
- precision guardrails
- consultation safety rules
- no absolute prediction

---

## Validation Expectations

Prompt changes should be checked with:

```bash
.venv/bin/python scripts/structured_runtime_contract.py
.venv/bin/python scripts/structured_retrieval_smoke.py
.venv/bin/python scripts/smoke_western_complete_result_flow.py
.venv/bin/python scripts/smoke_western_context_matrix.py
.venv/bin/python scripts/smoke_western_chart_variation_matrix.py
.venv/bin/python scripts/smoke_western_answer_layer.py
npm run typecheck
npm run build
```

Dashboard smoke should also fail if the API payload or visible page contains
BaZi runtime payloads or BaZi-facing copy.
