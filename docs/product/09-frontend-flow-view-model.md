# 09 - Frontend Flow And View Model
## Western-only complete result contract

> Purpose: keep the dashboard aligned with the real astrology-branch runtime.
> The frontend consumes a curated `CompleteRelationshipResultViewModel`; it does
> not consume raw calculation output directly.

---

## Current Decision

The astrology branch dashboard is Western-only at runtime.

```text
reading intake
  -> apps/web API route
  -> scripts/build_relationship_result_from_reading.py
  -> Western chart calculation
  -> westernRelationshipCaseFile
  -> structured KB selector/reducer
  -> readingBlueprint
  -> deterministic readable result fields
  -> CompleteRelationshipResultViewModel
  -> result dashboard
```

Primary fields for this branch:

- `contractVersion = "complete-relationship-result-v1"`
- `westernRelationshipCaseFile`
- `relationshipProfiles`
- `readingBlueprint`
- `answerGuidance`
- `timingGuidance`
- `actionGuidance`
- `evidence.western`
- `includedReadingRows`

Legacy mixed-system fields are optional only and should not be present in
astrology runtime output:

- `relationshipCaseFile`
- `baziCompatibilityDiagnosis`
- `evidence.bazi`
- `debug.baziSlot`

BaZi code and docs can remain in the repository for the separate BaZi branch,
but they are not frontend runtime dependencies for this branch.

---

## Intake Flow

```text
opening
  -> relationship stage
  -> main question
  -> contact status
  -> user birth data
  -> partner birth data
  -> confirmation
  -> calculation loading
  -> complete relationship result dashboard
```

Current intake fields:

- relationship stage
- main question
- contact status
- desired outcome / safety defaults
- birth date for both people
- birth time if known
- birth city if known
- gender/sex only where framing requires it

Birth city is optional. Missing city uses `location_fallback`; the result should
say that city improves precision, not that it is required. If time/place are not
reliable, house, Ascendant, Descendant, and overlay claims must remain blocked.

Names remain unnecessary for V0.

---

## CompleteRelationshipResultViewModel

Implementation type:

- `apps/web/src/data/complete-relationship-result.ts`

Generated fixture data:

- `apps/web/src/data/generated/relationship-result-scenarios.json`

Runtime API:

- `apps/web/src/app/api/readings/relationship-result/route.ts`

Legacy compatibility API:

- `apps/web/src/app/api/readings/free-result/route.ts`

Active builder:

- `scripts/complete_relationship_result_runtime.py`

Important shape:

```ts
type CompleteRelationshipResultViewModel = {
  contractVersion: "complete-relationship-result-v1";
  id: string;
  label: string;
  context: Record<string, string>;
  brand: {
    title: string;
    subtitle: string;
  };
  westernRelationshipCaseFile: WesternRelationshipCaseFile;
  relationshipProfiles?: RelationshipProfiles;
  readingBlueprint: ReadingBlueprint;
  reading: {
    badge: string;
    question: string;
    stage: string;
    answer: string;
    score: number;
    safety: string;
  };
  metrics: Metric[];
  calculationSteps: CalculationStep[];
  authorityReasons: AuthorityReason[];
  chapterEvidence: {
    thoughts: ChapterEvidence[];
    reasons: ChapterEvidence[];
    chance: ChapterEvidence[];
  };
  insights: Insight[];
  thoughts: string[];
  reasons: ReasonCard[];
  chance: {
    value: number;
    notes: string[];
  };
  timeline: TimelineStep[];
  donts: string[];
  evidence: {
    western: {
      title: string;
      signal: string;
      summary: string;
      visual: WesternVisual;
      points: EvidencePoint[];
      chips: string[];
      aspects: Array<{ label: string; value: string; meaning: string }>;
    };
  };
  includedReadingRows: IncludedReadingItem[];
  sources: string[];
  debug: {
    stageSlot: string | null;
    questionSlot: string | null;
    westernSlot: string | null;
    structuredKbSource?: "local" | "supabase";
    calculationWarnings?: string[];
    engineVersions?: Record<string, string | null>;
  };
};
```

The TypeScript contract still exposes `FreeResultViewModel` as an alias and
allows legacy optional fields such as `freeChapters`, `lockedRows`,
`paidExpansionPlan`, and `lockedQuestions` so old fixtures and separate branch
work can compile. The active astrology dashboard, generated fixtures, API
payloads, and smoke tests must emit and consume the complete-result names above,
not those aliases.

---

## WesternRelationshipCaseFile

`westernRelationshipCaseFile.version` must equal:

```text
western-relationship-case-file-v1
```

It is the technical source of truth for the complete result:

- `calculationSettings`: engine, zodiac, house system, aspect policy, timing method
- `inputQuality`: exact time, date-only, location fallback, or unavailable precision
- `identityLayer`: Moon, Mercury, Venus, Mars, Saturn, and Descendant needs where allowed
- `synastryLayer`: attraction, emotional safety, pressure, communication, repair
- `evidenceClusters`: KB-backed clusters used by rules and readable result fields
- `timingLayer`: current transit evidence and method limits
- `answerLayer`: deterministic answer, because, therefore, and included sections
- `methodGaps`: explicitly deferred methods or precision gaps

Current important cluster families:

- method/source: `methodOrder`, `natalSymbolFoundation`, `planetaryFunctions`
- sign foundations: `signClassificationFoundation`, `elementStyleFoundation`, `modalityResponseFoundation`, `planetSignStyle`
- point-specific sign function: `moonSignEmotionalSafety`, `mercurySignCommunicationRepair`, `venusSignAffectionStyle`, `marsSignPursuitConflict`, `saturnSignDefenseDelay`
- synastry: `relationshipPotential`, `elementComparison`, `luminaryComparison`, `attraction`, `emotionalSafety`, `communication`, `pressure`, `repair`
- precision: `birthDataQuality`, `ascendantImpression`, `houseRelationshipFactors`, `angleHouseFramework`, `relationshipChartLayer`
- context/safety: `relationshipStage`, `contactStatus`, `emotionalRisk`, `desiredOutcome`, `consultationSafety`

Each runtime cluster should carry `atomId`, `claimIds`, and `claimSupport`
where source support exists.

---

## ReadingBlueprint

`readingBlueprint.version` remains:

```text
reading-blueprint-v1
```

It is the deterministic reading execution plan. It must contain exactly three active
chapters in `readingBlueprint.chapters`:

- `thoughts`
- `reasons`
- `chance`

Every chapter evidence item must come from Western identity, synastry, pressure,
repair, timing, context, method, or safety layers. No BaZi evidence is allowed in
this branch.

The dashboard and deterministic readable-result layer should enforce:

- chapter order
- chapter titles
- assigned evidence refs
- result-title fallback
- method and precision boundaries
- forbidden claims

---

## Loading Gate

`calculationSteps` render only during the transition after intake and before the
user clicks into the result.

The report page itself must not show loading copy or reveal internal step text.
Loading copy should show categories only, for example:

- birth data precision
- planet positions
- synastry aspects
- current transits
- structured KB rules
- final relationship metrics

It must not reveal readings, personal advice, selected internal IDs, or hidden
debug traces.

---

## What Is Real Now

Real:

- Western natal relationship points from the calculation adapter
- Western synastry aspects from the adapter/signals layer
- birth-time/place precision gates
- current transit snapshot evidence
- `westernRelationshipCaseFile`
- `readingBlueprint`
- structured KB atoms/rules/guardrails/question blueprints
- source-backed `claimSupport` from compiled KB claims
- method clusters from Suskin and Hand
- point-specific Moon/Mercury/Venus/Mars/Saturn sign-function clusters
- deterministic readable result fields for all five paid sections
- dashboard smoke that rejects BaZi API payloads and visible BaZi copy

Prototype / next phase:

- real geocoder and timezone resolver for arbitrary cities
- broader aspect coverage and complete-result fixture coverage
- 90-day timing-window scanner for richer timing guidance
- composite/Davison relationship chart layer
- future deep-reading section generation
- clean Western runtime builder split from legacy mixed builder internals

---

## Scenario Preview

Generated calculation fixtures:

- `broke-up-long-any-chance`
- `broke-up-recent-still-love-me`
- `cold-war-still-love-me`
- `crisis-stay-or-let-go`

Useful commands:

```bash
.venv/bin/python scripts/build_relationship_result_view_models.py
npm run typecheck
npm run build
```

Dashboard smoke should be run against the app when checking the local API/UI
contract.
