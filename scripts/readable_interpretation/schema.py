"""Shared schema helpers for deterministic readable interpretation payloads."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


SectionNarrativeId = Literal[
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
]


class NarrativeEvidence(TypedDict, total=False):
    id: str
    domain: str
    role: str
    conceptKey: str
    source: str
    proposition: str
    confidence: float
    relevance: float
    sourceClaimIds: list[str]
    methodClaimIds: list[str]
    evidenceClusterKeys: list[str]


class SectionNarrativeContext(TypedDict, total=False):
    stageKey: str
    questionKey: str
    contactKey: str


class SectionNarrativeTrace(TypedDict, total=False):
    evidenceIds: list[str]
    sourceClaimIds: list[str]
    methodClaimIds: list[str]
    evidenceClusterKeys: list[str]


class SectionNarrativeValidation(TypedDict, total=False):
    status: Literal["valid", "invalid"]
    errors: list[str]
    warnings: list[str]


class RelationshipCaseModelTrace(TypedDict, total=False):
    version: str
    caseModelVersion: str
    sectionId: str
    primaryDynamicKey: str
    secondaryDynamicKey: str
    secondaryRole: str
    grammarId: str
    grammarMode: Literal["explicit", "composed"]
    caseEvidenceIds: list[str]


class SectionNarrativeSpec(TypedDict, total=False):
    version: str
    sectionId: SectionNarrativeId
    purpose: str
    context: SectionNarrativeContext
    semanticSlots: dict[str, Any]
    conceptKeys: list[str]
    forbiddenConceptKeys: list[str]
    evidence: list[NarrativeEvidence]
    trace: SectionNarrativeTrace
    caseModelTrace: RelationshipCaseModelTrace
    validation: SectionNarrativeValidation


class FinalNarrativeFact(TypedDict, total=False):
    id: str
    sectionId: SectionNarrativeId
    role: str
    valueKey: str
    sourceSlot: str
    sourceBindingFingerprint: str
    evidenceIds: list[str]
    qualifiers: list[str]


class FinalNarrativeFactDiagnostics(TypedDict, total=False):
    unknownFactIds: list[str]
    compatibilityProseSlots: list[str]


class FinalNarrativeFactSection(TypedDict, total=False):
    sectionId: SectionNarrativeId
    sourceSpecFingerprint: str
    facts: list[FinalNarrativeFact]
    selectedFactIds: list[str]
    diagnostics: FinalNarrativeFactDiagnostics
    validation: SectionNarrativeValidation


class FinalNarrativeFactContract(TypedDict, total=False):
    version: str
    rendererMode: str
    semanticCoverageVersion: str
    storyArcVersion: str
    factsRequired: bool
    visibleProseAllowedInFacts: bool
    sections: dict[str, FinalNarrativeFactSection]
    validation: SectionNarrativeValidation


class ReadableInterpretation(TypedDict, total=False):
    version: str
    module: str
    locale: str
    headline: str
    meaning: str
    body: str
    stuckPattern: str
    nextMove: str
    caution: str
    confidenceNote: str | None
    sourceClaimIds: list[str]
    methodClaimIds: list[str]
    evidenceClusterKeys: list[str]
    caseModelTrace: RelationshipCaseModelTrace
    questionSelector: dict[str, Any]
    debug: dict[str, Any]


class ReadableQuestionAnswer(TypedDict, total=False):
    version: str
    locale: str
    questionKey: str
    questionLabel: str
    sections: dict[str, Any]
