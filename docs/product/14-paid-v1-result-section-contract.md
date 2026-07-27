# 14 - Paid V1 Result Section Contract
## Five-section runtime map for the complete relationship reading

> Status: active implementation contract.
> Updated: 2026-06-10.

## Purpose

The paid `NT$1,280` result is not a free-result expansion and not a generic
wiki article renderer. It is a five-section Western relationship reading built
from calculated chart data, structured KB atoms/rules, source-backed method
claims, reducers, and a controlled readable layer.

This document maps each visible paid section to the runtime fields that must
support it. The UI can change design direction, but it cannot replace these
runtime requirements with static copy, dummy text, or LLM-only interpretation.

## Required Result Sections

The active visible flow is:

1. `星盤定位`
2. `兩個人的關係契合度分析`
3. `核心問題解讀`
4. `時機判讀`
5. `行動方向`

The runtime must expose the same five sections in
`westernRelationshipCaseFile.methodTrace.sections` with section IDs:

```text
profile
fit
question
timing
action
```

Every section must have:

- `status = "covered"`
- non-empty `requiredRuntimeTargets`
- non-empty `requiredSourceIds`
- non-empty `methodClaimIds`
- non-empty `evidenceClusterKeys`
- non-empty live evidence

## 01 星盤定位

Purpose: first understand each person separately before judging the
relationship.

Primary runtime fields:

- `relationshipProfiles.version = "relationship-profiles-v1"`
- `relationshipProfiles.personA`
- `relationshipProfiles.personB`
- `relationshipProfiles.precisionWarnings`
- `westernRelationshipCaseFile.identityLayer`
- `westernRelationshipCaseFile.inputQuality`
- `westernRelationshipCaseFile.evidenceClusters`

Required person cards:

- `Moon` for emotional safety
- `Mercury` for communication and repair
- `Venus` for affection and attraction style
- `Mars` for action, pursuit, and conflict rhythm
- `Saturn` for defense, delay, pressure, and boundaries

Required evidence clusters:

- `birthDataQuality`
- `identityNeeds`
- `planetaryFunctions`
- `planetSignStyle`
- `moonSignEmotionalSafety`
- `mercurySignCommunicationRepair`
- `venusSignAffectionStyle`
- `marsSignPursuitConflict`
- `saturnSignDefenseDelay`
- `functionElementMatrix`
- `functionModalityMatrix`

Visible cards should show:

- each person profile summary
- five function/sign cards per person
- readable purpose, body, stuck pattern, and next-use copy
- precision warnings when birth time or location is limited

Non-negotiable boundaries:

- Do not use Sun-sign-only personality verdicts.
- Do not claim Asc/Desc, houses, or overlays unless the precision gate allows
  them and the runtime has calculated support.
- Do not turn Saturn into permanent rejection, doom, punishment, or secret-love
  proof.

## 02 兩個人的關係契合度分析

Purpose: combine the two charts after each person's profile is understood.

Primary runtime fields:

- `relationshipProfiles.fitSummary`
- `westernRelationshipCaseFile.synastryLayer`
- `westernRelationshipCaseFile.evidenceClusters`
- `readingBlueprint.chapters`

Required evidence clusters:

- `relationshipPotential`
- `elementComparison`
- `luminaryComparison`
- `safetyValidationLanguage`
- `nonfatalSynastrySafety`
- `attraction`
- `emotionalSafety`
- `communication`
- `pressure`
- `repair`
- `aspectPriority`
- `aspectContactModifier`
- `aspectPairContactTemplate`
- `aspectPairPhraseTemplateMethod`
- `aspectFunctionCombination`
- `aspectSynthesisCrossCheck`

Visible cards should show:

- natural fit
- effort areas
- friction and misunderstanding points
- pivotal aspect card when available
- safety-validation language, not compatibility-score-only language

Non-negotiable boundaries:

- Do not dump every aspect.
- Do not make one aspect the whole verdict.
- Do not treat elements as a compatibility yes/no.
- Do not claim composite or Davison relationship-chart meaning until that layer
  is actually calculated.

## 03 核心問題解讀

Purpose: directly answer the user's selected question while keeping the answer
inside calculated evidence and consultation boundaries.

Primary runtime fields:

- `westernRelationshipCaseFile.answerLayer`
- `westernRelationshipCaseFile.answerLayer.evidenceContract`
- `westernRelationshipCaseFile.answerLayer.evidenceContract.contextModifier`
- `readableQuestionAnswer.sections.answer`
- `answerGuidance`
- `includedReadingRows`

Required question inputs:

- `relationship_stage`
- `main_question`
- `contact_status`
- `desired_outcome`
- `emotional_risk`

Supported question families:

- `still-love-me`
- `any-chance`
- `when-to-contact`
- `what-did-i-do-wrong`
- `stay-or-let-go`

Required evidence behavior:

- selected rule must come from the Western relationship result ruleset
- answer must include calculation evidence
- context can modify framing, action scale, tone safety, and timing boundary
- context cannot create synastry conclusions, compatibility claims, timing
  action, or third-party inner-state proof

Visible cards should show:

- short answer
- why this judgment was made
- evidence highlights
- conditions and signals to observe
- what the answer does not prove

Non-negotiable boundaries:

- Do not read the other person's mind.
- Do not guarantee reconciliation.
- Do not say astrology proves love, rejection, or final outcome.
- Do not let user-written context replace chart or transit evidence.

## 04 時機判讀

Purpose: use current transits and timing reducers as relationship climate and
action rhythm, not guaranteed dates.

Primary runtime fields:

- `westernRelationshipCaseFile.timingLayer.currentTransits`
- `westernRelationshipCaseFile.timingLayer.windowScan`
- `westernRelationshipCaseFile.evidenceClusters.timingWindowBand`
- `westernRelationshipCaseFile.evidenceClusters.timingContactReducer`
- `timingGuidance`
- `readableQuestionAnswer.sections.timing`

Required evidence clusters:

- `currentTransits`
- `timingWindowBand`
- `timingMercuryCommunication`
- `timingVenusSoftening`
- `timingMarsActivation`
- `timingSaturnPressure`
- `timingMoonWeather`
- `timingContactReducer`
- `contactSituationPolicy`

Required reducer branches:

- low-pressure Mercury message
- Venus softening
- mixed neutral or observe
- Mars activation caution
- Saturn pressure / avoid push
- missing timing scan / not calculated

Visible cards should show:

- recommended contact rhythm
- current timing climate
- support and caution signals
- precise-date boundary
- whether direct contact is allowed by the real-world contact boundary

Non-negotiable boundaries:

- Do not expose exact dates, raw date windows, `day_summaries`, or day-by-day
  timing internals.
- Do not let timing override blocked-contact or no-contact boundaries.
- Do not use Moon weather as a guarantee.
- Do not promise one best day to contact.

## 05 行動方向

Purpose: turn the evidence into next steps the user can actually follow without
pressure, coercion, or false certainty.

Primary runtime fields:

- `actionGuidance`
- `readableQuestionAnswer.sections.action`
- `readableQuestionAnswer.sections.donts`
- `westernRelationshipCaseFile.answerLayer.answerContract`
- `westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy`
- `westernRelationshipCaseFile.evidenceClusters.timingContactReducer`

Required evidence clusters:

- `consultationSafety`
- `contactStatus`
- `contactSituationPolicy`
- `relationshipStage`
- `emotionalRisk`
- `desiredOutcome`
- `nonfatalSynastrySafety`
- `timingContactReducer`

Visible cards should show:

- next move
- contact posture
- do-not-do boundaries
- pacing or short timeline
- one clear action frame, not a fear-based command

Non-negotiable boundaries:

- Do not advise bypassing a block.
- Do not frame waiting as fate.
- Do not encourage repeated messages, long explanations, emotional
  confrontation, or asking for an answer now when the contact boundary blocks
  it.
- Do not make the user responsible for controlling the other person's feelings.

## Runtime-Wide Forbidden Output

The paid Western V1 output must not emit:

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

Visible output must not contain BaZi method language such as:

```text
bazi
八字
配偶星
日主
四柱
十神
```

## Known V1 Limits

These are intentional current limits, not hidden missing features:

- Composite and Davison relationship-chart layers are reserved for a later
  implementation.
- House overlays remain blocked unless a future engine calculates them under
  reliable birth time and location.
- Current timing is a 90-day climate/reducer layer. It is not an exact-date
  promise layer.
- Real geocoder and timezone resolver are still next-phase infrastructure.
- The LLM narrative layer may polish selected evidence, but it cannot add new
  chart facts, timing promises, or third-party inner-state claims.

## Validation

The executable gate for this contract is:

```bash
.venv/bin/python scripts/validate_paid_v1_result_section_contract.py
```

The validator must pass together with the existing KB, runtime, timing, context,
and frontend checks before result-page work is considered safe.
