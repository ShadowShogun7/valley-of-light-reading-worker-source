# 13 - Western Suskin Method System

Date: 2026-05-26  
Workspace: `/Users/novaos/Documents/valley-of-light-astrology`  
Branch: `astrology`

## Purpose

Rod Suskin's `Synastry: Understanding the Astrology of Relationships` is now a P0 Western method source for the astrology branch.

This source is not used as broad RAG text. It defines the backend order for relationship readings:

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

The LLM should only phrase the selected evidence. It must not decide the method order or invent astrology facts.

## Source

Raw source:

```text
raw/western/718226037-Synastry-Understanding-the-Astrology-of-Relationships-Rod-Suskin-Z-Library.txt
```

Source manifest entry:

```text
docs/research/sources.yml
source id: western-suskin-synastry
```

Use short claim-level quotes only. Do not pass raw source text to runtime prompts.

## Source-Backed Articles

These articles are the method layer. They should be read before adding new Western relationship atoms or rules:

```text
wiki/western/synastry/method-order.md
wiki/western/planets/natal-relationship-potential.md
wiki/western/synastry/initial-comparison-elements.md
wiki/western/synastry/interchart-aspect-priorities.md
wiki/western/composite/relationship-chart-layer.md
wiki/western/synastry/consultation-ethics.md
```

Their role:

| Article | Runtime Meaning |
| --- | --- |
| `western-synastry-method-order` | The answer comes after natal, comparison, synastry, repair, and timing evidence. |
| `western-natal-relationship-potential` | Each person's relationship pattern is read before synastry. |
| `western-initial-comparison-elements` | Elements describe interaction style, not person-level compatibility verdicts. |
| `western-interchart-aspect-priorities` | Prioritize relevant aspect families, tighter orbs, and directionality. |
| `western-relationship-chart-layer` | Composite/Davison/relationship charts are paid-depth and blocked unless calculated. |
| `western-consultation-ethics` | Select accurate, relevant, useful, urgent evidence; protect privacy and emotional safety. |

## Structured Runtime Additions

New atom file:

```text
kb/atoms/western/suskin-method-v1.yml
```

New categories:

| Category | Layer | Purpose |
| --- | --- | --- |
| `methodOrder` | context | Enforces natal-first, question-last reading order. |
| `relationshipPotential` | identity | Summarizes Sun/Moon/Asc/Mercury/Venus/Mars/Saturn/Desc where allowed. |
| `elementComparison` | synastry | Compares interaction style through elements. |
| `luminaryComparison` | synastry | Prioritizes Sun/Moon core contacts or baseline. |
| `ascendantImpression` | identity | Shows Asc only when birth time and place are reliable. |
| `houseRelationshipFactors` | precision | Shows natal relationship houses only when allowed; overlays stay blocked. |
| `aspectPriority` | synastry | Selects relevant interchart aspects by pair family, orb, and directionality. |
| `relationshipChartLayer` | synastry | Keeps composite/Davison as deferred paid-depth. |
| `consultationSafety` | context | Applies privacy, high-emotion, and boundary safety controls. |

Method guardrails were added to:

```text
kb/guardrails/western/method-v1.yml
```

Important guardrails:

```text
western-guardrail-suskin-method-order
western-guardrail-element-not-person-verdict
western-guardrail-prioritize-relevant-evidence
western-guardrail-relationship-chart-paid-depth
western-guardrail-consultation-privacy
```

## Runtime Contract

`westernRelationshipCaseFile.evidenceClusters` now includes the Suskin method clusters in addition to the existing Western clusters:

```text
methodOrder
relationshipPotential
elementComparison
luminaryComparison
ascendantImpression
houseRelationshipFactors
aspectPriority
relationshipChartLayer
consultationSafety
identityNeeds
attraction
emotionalSafety
pressure
communication
repair
currentTransits
birthDataQuality
relationshipStage
contactStatus
emotionalRisk
desiredOutcome
```

The free reading blueprint now pulls from these clusters before writing the three visible chapters:

| Chapter | Added Suskin Evidence |
| --- | --- |
| `thoughts` | `methodOrder`, `relationshipPotential`, `luminaryComparison` |
| `reasons` | `elementComparison`, `aspectPriority` |
| `chance` | `consultationSafety`, `relationshipChartLayer` |

## Hard Boundaries

Other agents should preserve these boundaries:

- Do not answer the user question before building the Western case file.
- Do not treat elements as a person-level compatibility verdict.
- Do not dump all aspects into the reading.
- Do not generate Composite/Davison/relationship chart claims until those engines are implemented.
- Do not show Asc/Desc/house/overlay claims without reliable birth time and location.
- Do not write certainty about a third party's private inner state.
- Do not suggest bypassing contact boundaries when the user says they are blocked or the emotional risk is high.

## Validation

After editing this system, run:

```bash
.venv/bin/python scripts/compile_kb.py
.venv/bin/python scripts/report_structured_kb_coverage.py
.venv/bin/python scripts/build_relationship_result_view_models.py
.venv/bin/python -m py_compile scripts/build_relationship_result_view_models.py scripts/build_free_result_view_models.py scripts/smoke_western_complete_result_flow.py scripts/structured_runtime.py scripts/structured_runtime_contract.py
.venv/bin/python scripts/structured_runtime_contract.py
.venv/bin/python scripts/smoke_western_complete_result_flow.py
.venv/bin/python scripts/smoke_western_context_matrix.py
.venv/bin/python scripts/structured_retrieval_smoke.py
cd apps/web && npm run typecheck && npm run build
```

If syncing hosted Supabase staging, run dry-run first and never write production without explicit approval.

## Next Best Move

The context matrix and first reducer expansion are now in place. Next, deepen the natal method layer before adding more public copy:

```text
point x sign x element x modality x precision state
```

Start with Moon, Mercury, Venus, Mars, Saturn, and Desc when precision allows. Keep these as compact atoms/rules, not long article-only interpretations.
