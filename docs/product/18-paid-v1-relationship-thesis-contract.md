# 18 - Paid V1 Relationship Thesis Contract

> Status: active implementation contract.
> Created: 2026-06-24.

## Purpose

Paid V1 already has source-backed Western evidence, deterministic reducers, and
native Traditional Chinese copy. The remaining product gap is that visible copy
can still collapse from structured evidence into general relationship advice.

This contract adds a hidden synthesis layer:

```text
WesternRelationshipCaseFile
-> evidence packet
-> candidate relationship dynamics
-> ranked RelationshipThesis
-> RelationshipCaseModel
-> visible readable interpretation
-> thesis/specificity/safety validation
```

The visible result should feel personal because it explains the interaction
mechanism between the two people. It should not become more technical, expose
more astrology jargon, or rely on frontend chart anchors to create specificity.

## Runtime Position

`relationshipThesis.version` must equal:

```text
relationship-thesis-v1
```

`relationshipCaseModel.version` must equal:

```text
relationship-case-model-v1
```

The thesis is produced after:

- `westernRelationshipCaseFile.evidenceClusters`
- `westernRelationshipCaseFile.relationshipInsightLayer`
- `westernRelationshipCaseFile.answerLayer`

and before:

- `answerGuidance`
- `timingGuidance`
- `readableQuestionAnswer`

`relationshipCaseModel` is produced after `answerGuidance`, `timingGuidance`,
and `actionGuidance` exist, because it must combine the thesis with contact,
timing, risk, and action posture. It is then passed into:

- `finalInterpretation`
- `readableQuestionAnswer.sections.finalInterpretation`
- generated frontend scenarios

The thesis remains the primary diagnosis layer. The case model is the canonical
interpretation layer that decides how the thesis should be read in this exact
question/contact/timing context.

The deterministic V1 implementation may build the thesis from existing runtime
fields. If a future LLM stage is added, it must produce the same schema and pass
the same validator.

## Schema

Required top-level fields:

- `questionReframe`: one sentence that reframes the user's question into the
  relationship mechanism being judged.
- `centralThesis`: the main case-specific conclusion.
- `dominantTension`: the two poles of the relationship and the desired shift.
- `interactionLoop`: how one person's trigger and response reinforces the other.
- `currentActivation`: why this dynamic matters in the current relationship
  stage/contact state.
- `secondaryModifier`: one supporting nuance, not a second full thesis.
- `observableSigns`: concrete behaviors the user can observe.
- `changeCondition`: evidence that would strengthen or weaken the reading.
- `decisionBoundary`: when to continue observing and when to step back.
- `uncertainty`: confidence and the main limitation.
- `evidencePacket`: semantic evidence items used to synthesize the thesis.
- `candidateDynamics`: ranked candidate dynamics considered by the thesis layer.
- `selectedCandidateId`: the winning candidate.
- `evidenceMap`: thesis-field-to-evidence references.
- `prohibitedConclusions`: conclusions the visible copy must not make.
- `validation`: deterministic validator result.

Evidence items must be semantic propositions, not raw astrology notation.

```ts
type EvidenceDomain =
  | "userNatal"
  | "partnerNatal"
  | "synastry"
  | "timing"
  | "relationshipContext"
  | "method";

type EvidenceRole = "supports" | "complicates" | "activates" | "limits";
```

## RelationshipCaseModel Contract

The case model prevents the final reading from being assembled by several
separate partial interpreters. It must contain:

- `primaryDynamic`: the selected thesis dynamic and its central conclusion.
- `secondaryDynamics`: ranked modifiers from non-winning candidate dynamics.
- `centralLoop`: the interaction cycle the final reading should explain.
- `emotionalBlocker`: the condition most likely to keep the relationship stuck.
- `repairLever`: the smallest evidence-backed way the dynamic can soften.
- `contactPosture`: what the current contact state allows or forbids.
- `timingPosture`: how timing changes the action size.
- `riskPosture`: emotional-safety handling for the reader.
- `answerStrategy`: how to answer the user's selected question.
- `dynamicInteractionPlan`: the pair-specific grammar for the primary dynamic
  plus the top secondary dynamic.
- `sectionPlans`: five section-level interpretation plans for the final tabs.

Secondary dynamics are not static copy. Each item must include:

- `role`: `amplifier`, `blocker`, `repairLever`, `softener`, or
  `timingActivator`.
- `evidenceIds`: source evidence inherited from candidate dynamics.
- `interactionEffect`: how this secondary dynamic changes the primary reading.
- `whyItMatters`: why this modifier matters for the user's question.

The final renderer should use the case model as the first interpretation source
and use older objects only as evidence/detail providers. Technical keys such as
`primaryDynamic`, `secondaryDynamics`, and `relationshipCaseModel` must not be
shown as visible user-facing labels.

### V4 Pair-Grammar Layer

`dynamicInteractionPlan` is the V4 depth layer inside `relationshipCaseModel`.
It prevents the renderer from treating all secondary dynamics as generic
modifiers. The same primary dynamic must read differently when paired with a
different top secondary dynamic.

Required fields:

- `version`: `dynamic-interaction-plan-v1`.
- `primaryKey`: must equal `primaryDynamic.key`.
- `secondaryKey`: must equal the first ranked `secondaryDynamics[].key`.
- `secondaryRole`: copied from the first ranked secondary dynamic.
- `grammarId`: stable pair-grammar identifier, or `pair-fallback-v1` only when
  the pair has no authored grammar.
- `matchedGrammar`: boolean flag showing whether authored pair grammar was used.
- `dynamicInteraction`: how the two dynamics interact in the relationship.
- `whatThisMeans`: the direct reading implication for the user's question.
- `whatItDoesNotMean`: a boundary against over-reading the pair.
- `repairImplication`: how repair changes when this pair appears.
- `actionBoundary`: what not to do when this pair is active.
- `timingModifier`: how timing posture changes the action size.
- `contactModifier`: how contact state changes the action size.
- `phrasesToAvoid`: phrases this pair must not collapse into.
- `evidenceIds`: merged evidence from the primary and secondary dynamics.

The final renderer should use:

- `dynamicInteraction` in relationship fit.
- `whatThisMeans` and `whatItDoesNotMean` in the core answer.
- `timingModifier` and `contactModifier` in timing.
- `repairImplication` and `actionBoundary` in action direction.

The pair grammar is not a visible label and should never be displayed as schema
language. Its job is to make the visible Traditional Chinese copy sound more
specific, not more technical.

## Personalization Standard

The unit of personalization is the interaction mechanism, not:

- an isolated aspect
- a placement
- a personality trait
- a safety phrase
- a generic action suggestion

Weak:

```text
你需要安全感。
```

Better:

```text
你在關係訊號不明時，會更想確認對方的感覺。
```

Target:

```text
你越感到不確定，就越想確認；但他在互動壓力升高時，
反而更可能降低回應強度。於是你的確認沒有換來安心，
反而可能讓互動更斷續。
```

## Hard Gates

The thesis validator must reject or flag a thesis when:

- fewer than two evidence domains support the thesis
- no context evidence activates the thesis
- the interaction loop is empty or only describes one person
- partner claims have no partner evidence
- observable signs are mind-reading claims instead of behaviors
- the change condition has only confirming evidence and no disconfirming evidence
- the decision boundary does not follow from the thesis
- the central conclusion is stronger than the evidence permits
- prohibited conclusions are missing

## Visible Copy Rules

The visible writer receives the thesis and renders it naturally. It should:

- express `centralThesis` in the core answer
- use `dominantTension` in relationship fit
- use `currentActivation` and `changeCondition` in timing
- use `observableSigns` and `decisionBoundary` in action direction
- preserve uncertainty and prohibited conclusions
- avoid schema names, reducer IDs, selector IDs, source IDs, and internal terms

Visible copy must not:

- claim to know the other person's inner state
- promise reconciliation, rejection, or exact timing
- expose `relationshipThesis`, `evidencePacket`, `candidateDynamics`, or similar
  internal schema names
- replace the thesis with generic advice such as only "observe stability" or
  "do not push"

## Required Verification

Minimum implementation gates:

```bash
.venv/bin/python scripts/smoke_western_relationship_thesis.py
.venv/bin/python scripts/smoke_western_final_interpretation_layer.py
.venv/bin/python scripts/smoke_western_complete_result_flow.py
.venv/bin/python scripts/verify_paid_v1_reading_stack.py --include-web
```

The thesis smoke must include:

- required schema fields
- evidence-domain coverage
- interaction-loop coverage
- observable-sign behavior checks
- change-condition checks
- thesis-swap rejection checks
- contact-status counterfactual sensitivity checks

## Completion Standard

The architecture change is complete only when every generated paid scenario has
a valid `relationshipThesis`, the final visible interpretation uses that thesis,
and the verifier stack proves that the result remains Western-only,
source-bounded, nonfatalistic, and free of internal runtime language.
