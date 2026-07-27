"""Orchestrate the typed final narrative boundary.

Page grammar and reader-language realization belong to the five renderers in
``final_narrative_pages``.  This module only validates the upstream contracts,
checks routing identity, and dispatches a section's typed facts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .final_narrative_composition import (
    validate_reading_composition,
    validate_section_composition,
)
from .final_narrative_fact_contract import (
    FinalNarrativeFactContractError,
    ValidatedFinalNarrativeFactContract,
)
from .final_narrative_fact_renderer import render_final_narrative_section
from .section_narrative_spec import (
    SECTION_NARRATIVE_IDS,
    SECTION_NARRATIVE_RENDERER_VERSION,
    SECTION_NARRATIVE_SPEC_VERSION,
    unique_strings,
    validate_section_narrative_specs,
)


FINAL_NARRATIVE_COMPOSER_VERSION = "final-narrative-composer-v21"

FINAL_NARRATIVE_SECTION_CONTRACTS: dict[str, dict[str, tuple[str, ...]]] = {
    "chart-positioning": {
        "job": ("individual relationship style", "translation baseline"),
        "avoid": ("復合結論", "下一步行動", "時機判斷"),
    },
    "relationship-fit": {
        "job": ("relationship pattern", "attraction friction repair condition"),
        "avoid": ("訊息範例", "指定時機", "對方內心定論"),
    },
    "core-answer": {
        "job": ("direct answer", "what would change the answer"),
        "avoid": ("完整行動清單", "時機窗口", "星盤術語說明"),
    },
    "timing-reading": {
        "job": ("current pace", "when to slow down or observe"),
        "avoid": ("整段關係重新分析", "復合保證", "長篇行動建議"),
    },
    "action-direction": {
        "job": ("next step", "observable response", "stop line"),
        "avoid": ("重新分析合盤", "關係型態重述", "精準日期"),
    },
}

FINAL_COPY_ABSTRACT_PHRASES = (
    "語氣是否安全",
    "語氣安不安全",
    "繞路",
    "下一步的大小",
    "能接的份量",
    "現實支撐",
    "觀察位置",
    "比較值得調整的是",
)


@dataclass(frozen=True)
class ReaderSectionDraft:
    headline: str
    meaning: str
    body: str
    next_move: str
    caution: str

    def as_rendered(self) -> dict[str, str]:
        return {
            "headline": self.headline,
            "meaning": self.meaning,
            "body": self.body,
            "nextMove": self.next_move,
            "caution": self.caution,
        }


@dataclass(frozen=True)
class FinalNarrativeSemanticInput:
    question_key: str
    stage_key: str
    contact_key: str
    section_specs: dict[str, Any]
    fact_contract: dict[str, Any] | None = None


class SectionNarrativeSpecError(ValueError):
    """Raised when the final renderer receives an invalid contract bundle."""


@dataclass(frozen=True)
class ValidatedSectionNarrativeSpecs:
    bundle: dict[str, Any]
    sections: dict[str, dict[str, Any]]

    @classmethod
    def from_bundle(cls, bundle: dict[str, Any] | None) -> "ValidatedSectionNarrativeSpecs":
        source = bundle if isinstance(bundle, dict) else {}
        errors: list[str] = []
        if source.get("version") != SECTION_NARRATIVE_SPEC_VERSION:
            errors.append(f"wrong bundle version: {source.get('version')}")
        if source.get("rendererConsumesSpecs") is not True:
            errors.append("rendererConsumesSpecs must be true")
        if source.get("rendererVersion") != SECTION_NARRATIVE_RENDERER_VERSION:
            errors.append(f"wrong renderer version: {source.get('rendererVersion')}")
        sections = source.get("sections") if isinstance(source.get("sections"), dict) else {}
        validation = validate_section_narrative_specs(sections)
        if validation.get("status") != "valid":
            errors.extend(str(item) for item in validation.get("errors") or [])
        if set(sections) != set(SECTION_NARRATIVE_IDS):
            errors.append(f"section set mismatch: {sorted(sections)}")
        if errors:
            raise SectionNarrativeSpecError("Invalid SectionNarrativeSpec bundle: " + "; ".join(errors))
        return cls(bundle=source, sections=sections)

    def context(self, section_id: str) -> dict[str, str]:
        section = self.sections.get(section_id) or {}
        context = section.get("context")
        return context if isinstance(context, dict) else {}


@dataclass(frozen=True)
class FinalNarrativeComposer:
    question_key: str
    stage_key: str
    contact_key: str
    specs: ValidatedSectionNarrativeSpecs
    facts: ValidatedFinalNarrativeFactContract

    @classmethod
    def from_semantic_input(cls, semantic_input: FinalNarrativeSemanticInput) -> "FinalNarrativeComposer":
        specs = ValidatedSectionNarrativeSpecs.from_bundle(semantic_input.section_specs)
        fact_source = (
            semantic_input.fact_contract
            if isinstance(semantic_input.fact_contract, dict)
            else specs.bundle.get("finalNarrativeFacts")
        )
        try:
            facts = ValidatedFinalNarrativeFactContract.from_contract(fact_source, specs.sections)
        except FinalNarrativeFactContractError as exc:
            raise SectionNarrativeSpecError(str(exc)) from exc

        for section_id in ("core-answer", "timing-reading", "action-direction"):
            context = specs.context(section_id)
            expected = {
                "questionKey": semantic_input.question_key,
                "stageKey": semantic_input.stage_key,
                "contactKey": semantic_input.contact_key,
            }
            mismatches = [
                key
                for key, value in expected.items()
                if str(context.get(key) or "") != str(value or "")
            ]
            if mismatches:
                raise SectionNarrativeSpecError(
                    f"{section_id} routing context mismatch: {', '.join(mismatches)}"
                )

        return cls(
            question_key=semantic_input.question_key,
            stage_key=semantic_input.stage_key,
            contact_key=semantic_input.contact_key,
            specs=specs,
            facts=facts,
        )

    def fact_values(self, section_id: str, role: str) -> list[str]:
        return unique_strings(item.get("valueKey") for item in self.facts.facts(section_id, role))

    def render_section(self, section_id: str) -> ReaderSectionDraft:
        records = self.facts.facts(section_id)
        fact_identity = [
            {
                "id": str(item.get("id") or ""),
                "qualifiers": [str(value) for value in item.get("qualifiers") or []],
            }
            for item in records
        ]
        seed = "|".join(
            (
                section_id,
                json.dumps(fact_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            )
        )
        rendered = render_final_narrative_section(
            section_id=section_id,
            facts=self.facts,
            seed=seed,
        )
        validate_section_composition(section_id, rendered)
        return ReaderSectionDraft(
            headline=rendered["headline"],
            meaning=rendered["meaning"],
            body=rendered["body"],
            next_move=rendered["nextMove"],
            caution=rendered["caution"],
        )

    def render_all(self) -> dict[str, ReaderSectionDraft]:
        drafts = {
            section_id: self.render_section(section_id)
            for section_id in SECTION_NARRATIVE_IDS
        }
        validate_reading_composition(
            {
                section_id: draft.as_rendered()
                for section_id, draft in drafts.items()
            }
        )
        return drafts


__all__ = [
    "FINAL_COPY_ABSTRACT_PHRASES",
    "FINAL_NARRATIVE_COMPOSER_VERSION",
    "FINAL_NARRATIVE_SECTION_CONTRACTS",
    "FinalNarrativeComposer",
    "FinalNarrativeSemanticInput",
    "ReaderSectionDraft",
    "SectionNarrativeSpecError",
]
