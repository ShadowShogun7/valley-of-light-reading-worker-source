# 11 - Western Relationship Reading Framework

## Status

> Method reference with obsolete product framing.
> Use this for Western relationship-reading principles, not for the old
> free-result/paid-unlock structure. Active runtime and product contract are now
> `docs/product/00-current-v1-contract.md`,
> `docs/product/09-frontend-flow-view-model.md`, and
> `docs/product/13-western-suskin-method-system.md`.

**Decision date:** 2026-05-25  
**Current phase:** Western-only exploration split into its own astrology branch/session.

The next product spike should prove that Western astrology can produce a clear, premium relationship reading before we reintroduce BaZi.

## Session Split

Use separate branches/sessions from here:

- `bazi`: preserves the BaZi-focused result dashboard and BaZi interpreter work.
- `astrology`: starts from the cloned dashboard layout, but hides BaZi and focuses on Western astrology.
- `/Users/novaos/Documents/valley-of-light-kb`: keep this workspace for BaZi continuation.
- `/Users/novaos/Documents/valley-of-light-astrology`: use this workspace for the new astrology session.

The astrology session should start from this document and should not redesign the front end first. The immediate goal is to build a stronger Western diagnosis layer behind the current dashboard structure.

## Research Summary

Established Western relationship products do not rely on a single strongest aspect.

Common structure across serious tools:

- **Synastry / chart comparison:** compare two natal charts through inter-aspects and house overlays.
- **Natal relationship needs:** read each person first, especially Moon, Mercury, Venus, Mars, Saturn, Descendant/7th house when birth time is reliable.
- **Composite / Davison chart:** read the relationship as its own entity, not only person A affecting person B.
- **Timing:** use transits/progressions to explain why the relationship feels this way now.
- **Score with caution:** scores are attractive for users, but they should be treated as a summary indicator, not the reading itself.

What this means for Valley of Light:

```text
natal needs
  -> synastry contacts
  -> house overlays when time is known
  -> composite relationship story
  -> current timing
  -> user question answer
```

The question answer should come last. It should read like a conclusion from the chart evidence, not a forced response to a selected question.

## Product References

### Astrodienst / Astro.com

Astrodienst frames comparative astrology as broader than romantic matching. It includes synastry, midpoint composite charts, and Davison relationship charts.

Product lesson:

- Use birth data carefully.
- Support multiple relationship methods.
- Treat chart comparison as relationship dynamics, not a yes/no fate answer.

Sources:

- https://www.astro.com/astrowiki/en/Synastry
- https://www.astro.com/astrowiki/en/Comparative_Astrology
- https://www.astro.com/

### Cafe Astrology

Cafe Astrology clearly separates synastry from composite work. Synastry compares two charts point by point; composite reads the couple as a unit.

Product lesson:

- Free output can show strongest synastry evidence.
- Paid report should introduce composite relationship dynamics because that feels like a deeper "relationship story."
- Compatibility scores need caveats, especially with unknown birth times.

Sources:

- https://cafeastrology.com/compositechartvssynastry.html
- https://cafeastrology.com/compatibility-report-scores.html

### Astro-Seek / Astro Charts

These tools emphasize visible calculation proof: chart overlays, aspects, houses, orbs, and technical controls.

Product lesson:

- Users trust visible technical evidence.
- Normal users still need translation after the chart.
- Our UI should show only a few top aspects, not a huge matrix.

Sources:

- https://www.astro-seek.com/
- https://astro-charts.com/tools/new/synastry/

### TimePassages

TimePassages sells relationship work as two methods: compatibility/synastry and relationship/composite. Its report positioning is depth-first: important inter-aspects first, then relationship potential and composite structure.

Product lesson:

- Free page should not expose the full report.
- Paid page should expand from top inter-aspects into the relationship chart itself.
- The report should support romantic and non-romantic modes later, but romantic mode is V0.

Source:

- https://www.astrograph.com/timepassages/relationship-insights.php

### The Pattern / Co-Star

Modern app products de-technicalize the experience: they convert charts into relationship patterns, traits, bonds, romantic transits, and conversation prompts.

Product lesson:

- Normal users do not want an aspect textbook.
- Use technical proof as authority, then give plain relationship meaning.
- "Go deeper" / paid unlock works when each unlocked item names a specific emotional question.

Sources:

- https://www.thepattern.com/
- https://thepattern.zendesk.com/hc/en-us/articles/360046292451-What-are-Bonds
- https://www.costarastrology.com/

## Recommended Valley Structure

### Backend Method Order

After the Rod Suskin P0 source pass, the backend reading order is stricter than the original product sketch:

```text
intake context + precision gate
  -> methodOrder
  -> relationshipPotential
  -> elementComparison
  -> luminaryComparison
  -> synastry aspect clusters
  -> pressure / repair / timing reducers
  -> consultationSafety
  -> question-specific answer
  -> controlled LLM wording
```

The implementation/handoff reference is `docs/product/13-western-suskin-method-system.md`.

Core rule: do not jump straight to "will they come back." Build the Western case file first, then answer the selected question from selected evidence and reducer rules.

### Free Result

Free should be sharp, readable, and evidence-backed:

1. **Answer / Core Conclusion**
   - One sentence answering the selected question.
   - Must be generated from the relationship case file, not preset by question.

2. **Relationship Pattern**
   - The main relationship type from the chart:
     - emotional pull
     - pressure bond
     - unstable chemistry
     - slow-burn repair
     - closure lesson

3. **Your Needs / Their Needs**
   - Moon: emotional safety
   - Venus: affection and validation
   - Mars: desire and pursuit style
   - Saturn: fear, delay, responsibility, defense
   - Desc/7th only if birth time is reliable

4. **Top Synastry Evidence**
   - 3 aspects max.
   - Include planet pair, aspect type, orb, direction, and plain meaning.
   - Example shape:

```text
Sun-Mars trine, orb 1.53°
Technical: your Sun aspects their Mars.
Meaning: attraction is active, but fast interaction can become pressure.
```

5. **Pressure And Safety**
   - Saturn, Mars, Pluto, Neptune, hard Moon/Venus contacts.
   - Explain what creates coldness, delay, avoidance, or confusion.

6. **Free Boundary**
   - No exact timing window.
   - No message template.
   - No guaranteed reunion claim.

### Paid Report

Paid should not just add more text. It should add new layers:

1. **Full natal relationship needs**
2. **Full synastry map**
3. **House overlays**
4. **Composite or Davison relationship chart**
5. **Current timing / transits**
6. **Repair conditions**
7. **Personalized action strategy**
8. **Message strategy and trigger words to avoid**

## Western Case File Contract

Build a Western-first case file before LLM writing:

```ts
type WesternRelationshipCaseFile = {
  identityLayer: {
    personA: {
      moon: NeedPoint;
      venus: NeedPoint;
      mars: NeedPoint;
      saturn: NeedPoint;
      desc?: NeedPoint;
    };
    personB: {
      moon: NeedPoint;
      venus: NeedPoint;
      mars: NeedPoint;
      saturn: NeedPoint;
      desc?: NeedPoint;
    };
  };
  synastryLayer: {
    attraction: AspectEvidence[];
    emotionalSafety: AspectEvidence[];
    pressure: AspectEvidence[];
    communication: AspectEvidence[];
  };
  houseOverlayLayer?: {
    fifthHouse: OverlayEvidence[];
    seventhHouse: OverlayEvidence[];
    eighthHouse: OverlayEvidence[];
    twelfthHouse: OverlayEvidence[];
  };
  compositeLayer?: {
    relationshipSun: CompositeEvidence;
    relationshipMoon: CompositeEvidence;
    relationshipVenus: CompositeEvidence;
    relationshipSaturn: CompositeEvidence;
    majorAspects: AspectEvidence[];
  };
  timingLayer: {
    currentTransits: TransitEvidence[];
    repairWindow: TimingEvidence[];
    cautionWindow: TimingEvidence[];
  };
  answerLayer: {
    selectedQuestion: string;
    shortAnswer: string;
    because: string[];
    therefore: string;
    paidUnlock: string[];
  };
};
```

## Ranking Rules

Avoid one global score as the primary selector.

Use slot-based selection:

- **identity:** Moon/Mercury/Venus/Mars/Saturn needs from both charts
- **attraction:** strongest Sun/Moon/Venus/Mars contacts
- **pressure:** strongest Saturn/Mars/Pluto/Neptune hard contacts
- **safety:** Moon/Saturn/Venus contacts and 4th/7th/8th/12th overlays
- **timing:** current transits to natal/composite Moon, Venus, Mars, Saturn
- **question:** only after the above are selected

Tie-breakers:

1. tighter orb
2. personal planet involvement
3. repeats across natal need + synastry + composite
4. relationship-stage relevance
5. birth-time confidence

## Engine Direction

Current best calculation direction remains:

- `immanuel` for structured Western chart data and synastry-style aspects.
- `kerykeion` as a visualization/report candidate if AGPL/commercial usage is handled.
- `flatlib` only as a fallback/reference because it is lower-level and traditional-astrology focused.
- `stellium` remains interesting but not V0 due lower maturity and AGPL path.

Important:

- Do not use third-party relationship scores as product truth.
- Do not show house overlays or Asc/Desc conclusions when birth time is unknown.
- Keep raw calculation data separate from reading claims.

Sources:

- https://github.com/theriftlab/immanuel-python
- https://kerykeion.net/content/docs
- https://github.com/g-battaglia/kerykeion
- https://github.com/flatangle/flatlib

## Next Build Step

Build a Western-only deterministic diagnosis layer:

```text
input birth data
  -> immanuel natal charts
  -> synastry aspects
  -> WesternRelationshipCaseFile
  -> free slots
  -> LLM or template narrative
  -> Western-focused dashboard
```

The immediate goal is not cosmetic polish. The goal is to make every free result visibly answer:

1. Why there is attraction.
2. Why it feels blocked.
3. What emotional safety issue is active.
4. What repair condition must be true.
5. What paid report will unlock.
