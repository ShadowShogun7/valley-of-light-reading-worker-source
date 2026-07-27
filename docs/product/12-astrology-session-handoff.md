# 12 - Astrology Session Handoff

> Historical handoff.
> This file explains how the Western astrology branch started. Product direction
> has since changed to one paid `NT$1,280` complete result with no free result,
> locked teaser rows, or in-result upsell.
> Active contract: `docs/product/00-current-v1-contract.md`.

## Purpose

This file is the starting point for the new Western astrology session.

The BaZi work should continue separately. The astrology session should use the same visual dashboard direction, but the diagnosis engine, evidence pack, and report structure should be Western-first.

## Workspace Split

Use this split:

```text
/Users/novaos/Documents/valley-of-light-kb
  branch: bazi
  purpose: continue BaZi diagnosis, BaZi interpreter, BaZi result dashboard

/Users/novaos/Documents/valley-of-light-astrology
  branch: astrology
  purpose: Western astrology product spike
```

The `astrology` branch is cloned from the current dashboard UI direction. It hides BaZi from the visible product flow so we can judge whether Western astrology alone can carry a premium relationship reading.

## What To Keep

Keep the current front-end style:

- phone-like result dashboard
- warm cream paper background
- soft proof cards
- technical evidence plus plain-language interpretation
- locked paid report teasers
- intake flow with birth date, birth time, birth city, gender, relationship stage, question, and contact status

Do not redesign the UI before the reading system works.

## What To Build Next

Build a deterministic `WesternRelationshipCaseFile`.

Minimum layers:

1. `identityLayer`
   - each person's Moon, Mercury, Venus, Mars, Saturn
   - Desc / 7th house only when birth time is known

2. `synastryLayer`
   - attraction aspects
   - emotional safety aspects
   - pressure aspects
   - communication aspects
   - aspect type, orb, applying/separating if available

3. `houseOverlayLayer`
   - 5th, 7th, 8th, 12th house overlays only when both birth times are reliable

4. `compositeLayer`
   - relationship Sun, Moon, Mercury, Venus, Mars, Saturn
   - major composite aspects
   - paid-report depth layer, not required for first free-page proof

5. `timingLayer`
   - current transits to natal and relationship-sensitive points
   - Saturn, Venus, Mars, Moon priority
   - exact dates stay paid

6. `answerLayer`
   - only after the above layers are selected
   - answer the selected user question from chart evidence, not from preset question copy

## Free Page Structure

Use this order:

1. Core answer
2. Relationship pattern
3. Your needs / their needs
4. Top 3 synastry evidence cards
5. Pressure and safety explanation
6. Paid unlock preview

The free page should prove:

- why there is attraction
- why it feels blocked
- what emotional safety issue is active
- what condition would make repair possible
- what the paid report will unlock

## Paid Report Structure

Paid report expands:

- full natal relationship needs
- full synastry map
- house overlays
- composite / Davison relationship chart
- timing windows
- message strategy
- trigger words to avoid
- personal blind spot

## Guardrails

- Do not use third-party compatibility scores as product truth.
- Do not show house overlays, Ascendant, Descendant, or house-based claims when birth time is unknown.
- Do not let one strongest aspect become the whole reading.
- Do not let the LLM invent chart facts.
- Do not answer the user question until the case file is assembled.

## Primary Docs

Read in this order:

1. `docs/product/11-western-relationship-reading-framework.md`
2. `docs/research/03-calculation-engine-evaluation.md`
3. `docs/tech/04-calculation-engines.md`
4. `docs/tech/06-llm-prompt-strategy.md`
5. `docs/product/09-frontend-flow-view-model.md`
