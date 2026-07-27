"""Page-level discourse plans for coherent reader paragraphs.

Typed facts remain the evidence boundary.  A paragraph plan decides how those
facts form one page-owned argument before any visible Chinese is realized.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Sequence

from .final_narrative_chinese_plan import ReaderMeaningFrame
from .final_narrative_fact_contract import FACT_KEY_PATTERN, fact_id
from .final_narrative_story_arc import (
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
    hidden_roles,
    is_visible_presentation,
)


FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION = "final-narrative-paragraph-plan-v2"

DiscourseRelation = Literal[
    "headline",
    "opening",
    "context",
    "elaboration",
    "contrast",
    "evidence",
    "consequence",
    "condition",
    "action",
    "boundary",
]

DISCOURSE_RELATIONS: tuple[DiscourseRelation, ...] = (
    "headline",
    "opening",
    "context",
    "elaboration",
    "contrast",
    "evidence",
    "consequence",
    "condition",
    "action",
    "boundary",
)

PAGE_BLUEPRINTS: dict[str, tuple[str, ...]] = {
    "chart-positioning": (
        "user-emotional-need",
        "user-communication-style",
        "partner-pressure-response",
        "precision-mode",
    ),
    "relationship-fit": (
        "relationship-archetype",
        "primary-dynamic",
        "attraction-signal",
        "friction-signal",
        "growth-signal",
    ),
    "core-answer": (
        "answer-track",
        "question",
        "relationship-stage",
        "contact-status",
        "central-dynamic",
        "evidence-signal",
        "partner-relationship-need",
        "observable-sign",
        "uncertainty-level",
    ),
    "timing-reading": (
        "question",
        "contact-status",
        "timing-posture",
        "recommended-action",
        "timing-band",
        "contact-posture",
        "precise-dates-available",
    ),
    "action-direction": (
        "question",
        "contact-status",
        "action-purpose",
        "action-mode",
        "completion-boundary",
        "repair-lever",
        "stop-condition",
        "contact-posture",
    ),
}

OPTIONAL_ROLES = {
    "relationship-fit": {"secondary-dynamic"},
    "timing-reading": {"timing-window"},
    "action-direction": {"blocked-action"},
}

REPEATABLE_ROLES = {"blocked-action"}


class ReaderParagraphPlanError(ValueError):
    """Raised when page facts do not form one valid discourse plan."""


class ReaderParagraphOutputError(ValueError):
    """Raised when visible copy no longer follows its validated discourse plan."""


@dataclass(frozen=True)
class ParagraphStep:
    relation: DiscourseRelation
    frame: ReaderMeaningFrame

    def validate(self, section_id: str) -> None:
        if self.relation not in DISCOURSE_RELATIONS:
            raise ReaderParagraphPlanError(
                f"unsupported discourse relation: {self.relation}"
            )
        self.frame.validate()
        if self.frame.section_id != section_id:
            raise ReaderParagraphPlanError(
                f"paragraph step crossed page ownership: "
                f"{section_id}/{self.frame.section_id}"
            )
        presentation = FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id, {}).get(
            self.frame.role
        )
        if not presentation or not is_visible_presentation(presentation):
            raise ReaderParagraphPlanError(
                f"{section_id}: hidden role entered visible paragraph steps: "
                f"{self.frame.role}"
            )


@dataclass(frozen=True)
class ParagraphSupport:
    role: str
    value_key: str
    source_fact_id: str

    def validate(self, section_id: str) -> None:
        for label, value in (
            ("role", self.role),
            ("valueKey", self.value_key),
            ("sourceFactId", self.source_fact_id),
        ):
            if not value or not FACT_KEY_PATTERN.fullmatch(value):
                raise ReaderParagraphPlanError(
                    f"paragraph support {label} must be a stable ASCII key"
                )
        if self.role not in hidden_roles(section_id):
            raise ReaderParagraphPlanError(
                f"{section_id}: visible role entered hidden paragraph support: {self.role}"
            )
        if self.source_fact_id != fact_id(section_id, self.role, self.value_key):
            raise ReaderParagraphPlanError(
                f"{section_id}: paragraph support fact identity is stale"
            )


def support_from_fact(fact: Mapping[str, Any]) -> ParagraphSupport:
    return ParagraphSupport(
        role=str(fact.get("role") or ""),
        value_key=str(fact.get("valueKey") or ""),
        source_fact_id=str(fact.get("id") or ""),
    )


@dataclass(frozen=True)
class ReaderParagraphPlan:
    version: str
    section_id: str
    paragraph_kind: str
    conclusion_key: str
    steps: tuple[ParagraphStep, ...]
    supports: tuple[ParagraphSupport, ...] = ()

    @property
    def roles(self) -> tuple[str, ...]:
        return (
            *(step.frame.role for step in self.steps),
            *(support.role for support in self.supports),
        )

    @property
    def visible_roles(self) -> tuple[str, ...]:
        return tuple(step.frame.role for step in self.steps)

    @property
    def support_roles(self) -> tuple[str, ...]:
        return tuple(support.role for support in self.supports)

    @property
    def source_fact_ids(self) -> tuple[str, ...]:
        return (
            *(step.frame.source_fact_id for step in self.steps),
            *(support.source_fact_id for support in self.supports),
        )

    def validate(self) -> None:
        if self.version != FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION:
            raise ReaderParagraphPlanError("paragraph-plan version is stale")
        if self.section_id not in PAGE_BLUEPRINTS:
            raise ReaderParagraphPlanError(
                f"unsupported paragraph-plan section: {self.section_id}"
            )
        for label, value in (
            ("paragraphKind", self.paragraph_kind),
            ("conclusionKey", self.conclusion_key),
        ):
            if not value or not FACT_KEY_PATTERN.fullmatch(value):
                raise ReaderParagraphPlanError(
                    f"{label} must be a stable ASCII key"
                )
        if not self.steps:
            raise ReaderParagraphPlanError("paragraph plan has no steps")
        for step in self.steps:
            step.validate(self.section_id)
        for support in self.supports:
            support.validate(self.section_id)

        required = set(PAGE_BLUEPRINTS[self.section_id])
        actual = set(self.roles)
        missing = required - actual
        allowed = required | OPTIONAL_ROLES.get(self.section_id, set())
        extra = actual - allowed
        if missing or extra:
            raise ReaderParagraphPlanError(
                f"{self.section_id}: paragraph roles mismatch: "
                f"missing={sorted(missing)} extra={sorted(extra)}"
            )

        seen_roles: set[str] = set()
        for role in self.roles:
            if role in seen_roles and role not in REPEATABLE_ROLES:
                raise ReaderParagraphPlanError(
                    f"{self.section_id}: paragraph repeats role {role}"
                )
            seen_roles.add(role)

        seen_fact_ids: set[str] = set()
        for source_fact_id in self.source_fact_ids:
            if source_fact_id in seen_fact_ids:
                raise ReaderParagraphPlanError(
                    f"{self.section_id}: paragraph repeats fact {source_fact_id}"
                )
            seen_fact_ids.add(source_fact_id)

        visible_relations = {
            "opening",
            "context",
            "elaboration",
            "contrast",
            "evidence",
            "consequence",
            "condition",
            "action",
        }
        first_visible = next(
            (
                step.relation
                for step in self.steps
                if step.relation in visible_relations
            ),
            "",
        )
        if first_visible not in {"opening", "context"}:
            raise ReaderParagraphPlanError(
                f"{self.section_id}: paragraph begins without an opening"
            )


def paragraph_plan(
    *,
    section_id: str,
    paragraph_kind: str,
    conclusion_key: str,
    steps: Iterable[tuple[DiscourseRelation, ReaderMeaningFrame]],
    supports: Iterable[ParagraphSupport] = (),
) -> ReaderParagraphPlan:
    plan = ReaderParagraphPlan(
        version=FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        section_id=section_id,
        paragraph_kind=paragraph_kind,
        conclusion_key=conclusion_key,
        steps=tuple(
            ParagraphStep(relation=relation, frame=frame)
            for relation, frame in steps
        ),
        supports=tuple(supports),
    )
    plan.validate()
    return plan


def ordered_roles(plan: ReaderParagraphPlan, relations: Sequence[str]) -> tuple[str, ...]:
    selected = set(relations)
    return tuple(
        step.frame.role
        for step in plan.steps
        if step.relation in selected
    )


def visible_sentences(value: str) -> tuple[str, ...]:
    return tuple(
        item.strip()
        for item in re.split(r"[。！？!?]+", str(value or ""))
        if item.strip()
    )


def validate_paragraph_output(
    plan: ReaderParagraphPlan,
    rendered: Mapping[str, str],
) -> None:
    plan.validate()
    required_fields = {"headline", "meaning", "body", "nextMove", "caution"}
    if set(rendered) != required_fields:
        raise ReaderParagraphOutputError(
            f"{plan.section_id}: paragraph output field set is incomplete"
        )
    combined = "".join(str(rendered[field] or "") for field in required_fields)
    awkward = (
        "不要接著在",
        "不再繼續",
        "同時，但",
        "另外，但",
        "而且但",
    )
    hits = [item for item in awkward if item in combined]
    if hits:
        raise ReaderParagraphOutputError(
            f"{plan.section_id}: awkward paragraph assembly returned: {hits}"
        )

    meaning = visible_sentences(rendered["meaning"])
    body = visible_sentences(rendered["body"])
    if plan.section_id == "chart-positioning":
        if len(meaning) != 2 or len(body) != 1:
            raise ReaderParagraphOutputError(
                "chart-positioning: expected need, communication habit, and pressure response"
            )
    elif plan.section_id == "relationship-fit":
        expected_body = 3 if "secondary-dynamic" in plan.roles else 2
        if len(meaning) != 1 or len(body) != expected_body:
            raise ReaderParagraphOutputError(
                "relationship-fit: attraction, friction, and optional secondary order changed"
            )
        if body[0].startswith(("但", "另外", "而且")) or not body[1].startswith("但"):
            raise ReaderParagraphOutputError(
                "relationship-fit: attraction must lead and friction must be a clear contrast"
            )
        if expected_body == 3 and not body[2].startswith("另外"):
            raise ReaderParagraphOutputError(
                "relationship-fit: secondary dynamic must remain supporting context"
            )
    elif plan.section_id == "core-answer":
        if len(meaning) != 1 or len(body) != 1:
            raise ReaderParagraphOutputError(
                "core-answer: expected one direct answer plus one question-specific evidence sentence"
            )
    elif plan.section_id == "timing-reading":
        if len(meaning) != 1 or len(body) != 2:
            raise ReaderParagraphOutputError(
                "timing-reading: expected current permission, selected window, and timing band"
            )
        if not body[1].startswith(("那段時間", "即使那段時間")):
            raise ReaderParagraphOutputError(
                "timing-reading: timing band is disconnected from its selected window"
            )
    elif plan.section_id == "action-direction":
        for field in ("meaning", "body", "nextMove", "caution"):
            if len(visible_sentences(rendered[field])) != 1:
                raise ReaderParagraphOutputError(
                    f"action-direction:{field}: expected one practical sentence"
                )
        if "完成" not in rendered["body"]:
            raise ReaderParagraphOutputError(
                "action-direction: completion boundary is missing"
            )


__all__ = [
    "DISCOURSE_RELATIONS",
    "FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION",
    "PAGE_BLUEPRINTS",
    "ParagraphStep",
    "ParagraphSupport",
    "ReaderParagraphPlan",
    "ReaderParagraphPlanError",
    "ReaderParagraphOutputError",
    "ordered_roles",
    "paragraph_plan",
    "support_from_fact",
    "validate_paragraph_output",
    "visible_sentences",
]
