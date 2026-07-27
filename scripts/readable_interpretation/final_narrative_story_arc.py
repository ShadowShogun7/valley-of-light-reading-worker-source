"""Five-chapter story allocation for the final relationship reading.

The relationship thesis remains the hidden controller.  This contract decides
which typed facts may become a new visible proposition on each page and which
facts may only route, support, or bound that proposition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


FINAL_NARRATIVE_STORY_ARC_VERSION = "final-narrative-story-arc-v1"

RolePresentation = Literal[
    "visible-claim",
    "visible-boundary",
    "hidden-support",
    "hidden-routing",
]


@dataclass(frozen=True)
class StoryChapter:
    order: int
    section_id: str
    job: str
    depends_on: tuple[str, ...]
    proposition_key: str


STORY_CHAPTERS: dict[str, StoryChapter] = {
    "chart-positioning": StoryChapter(
        order=1,
        section_id="chart-positioning",
        job="establish each person's emotional and communication pattern",
        depends_on=(),
        proposition_key="individual-pattern-premise",
    ),
    "relationship-fit": StoryChapter(
        order=2,
        section_id="relationship-fit",
        job="show what the two chart patterns create together",
        depends_on=("chart-positioning",),
        proposition_key="relationship-interaction",
    ),
    "core-answer": StoryChapter(
        order=3,
        section_id="core-answer",
        job="answer the selected question in the current relationship context",
        depends_on=("chart-positioning", "relationship-fit"),
        proposition_key="question-specific-verdict",
    ),
    "timing-reading": StoryChapter(
        order=4,
        section_id="timing-reading",
        job="identify when the current verdict is more or less workable",
        depends_on=("core-answer",),
        proposition_key="timing-condition",
    ),
    "action-direction": StoryChapter(
        order=5,
        section_id="action-direction",
        job="close with one bounded action, completion point, and stop condition",
        depends_on=("core-answer", "timing-reading"),
        proposition_key="bounded-resolution",
    ),
}


FINAL_NARRATIVE_ROLE_PRESENTATIONS: dict[str, dict[str, RolePresentation]] = {
    "chart-positioning": {
        "user-emotional-need": "visible-claim",
        "user-communication-style": "visible-claim",
        "partner-pressure-response": "visible-claim",
        "precision-mode": "visible-boundary",
    },
    "relationship-fit": {
        "relationship-archetype": "visible-claim",
        "primary-dynamic": "visible-claim",
        "secondary-dynamic": "visible-claim",
        "attraction-signal": "visible-claim",
        "friction-signal": "visible-claim",
        "growth-signal": "visible-claim",
    },
    "core-answer": {
        "question": "visible-claim",
        "relationship-stage": "hidden-routing",
        "contact-status": "hidden-routing",
        "answer-track": "visible-claim",
        "central-dynamic": "hidden-support",
        "partner-relationship-need": "hidden-support",
        "evidence-signal": "visible-claim",
        "observable-sign": "visible-claim",
        "uncertainty-level": "visible-boundary",
    },
    "timing-reading": {
        "question": "hidden-routing",
        "contact-status": "visible-claim",
        "timing-posture": "visible-claim",
        "recommended-action": "visible-claim",
        "timing-band": "visible-claim",
        "contact-posture": "hidden-routing",
        "precise-dates-available": "visible-boundary",
        "timing-window": "visible-claim",
    },
    "action-direction": {
        "question": "visible-claim",
        "contact-status": "hidden-routing",
        "action-purpose": "visible-claim",
        "action-mode": "visible-claim",
        "completion-boundary": "visible-claim",
        "repair-lever": "hidden-support",
        "stop-condition": "visible-boundary",
        "contact-posture": "hidden-support",
        "blocked-action": "hidden-routing",
    },
}

REQUIRED_HIDDEN_STORY_ROLES = {
    ("core-answer", "relationship-stage"),
    ("core-answer", "contact-status"),
    ("core-answer", "central-dynamic"),
    ("core-answer", "partner-relationship-need"),
    ("timing-reading", "question"),
    ("timing-reading", "contact-posture"),
    ("action-direction", "contact-status"),
    ("action-direction", "repair-lever"),
    ("action-direction", "contact-posture"),
    ("action-direction", "blocked-action"),
}

REQUIRED_VISIBLE_CHAPTER_ROLES = {
    ("chart-positioning", "user-emotional-need"),
    ("chart-positioning", "user-communication-style"),
    ("chart-positioning", "partner-pressure-response"),
    ("relationship-fit", "primary-dynamic"),
    ("relationship-fit", "attraction-signal"),
    ("relationship-fit", "friction-signal"),
    ("core-answer", "question"),
    ("core-answer", "evidence-signal"),
    ("core-answer", "observable-sign"),
    ("timing-reading", "contact-status"),
    ("timing-reading", "timing-posture"),
    ("timing-reading", "timing-band"),
    ("action-direction", "action-purpose"),
    ("action-direction", "action-mode"),
    ("action-direction", "completion-boundary"),
}


def is_visible_presentation(value: str) -> bool:
    return value in {"visible-claim", "visible-boundary"}


def visible_roles(section_id: str) -> set[str]:
    return {
        role
        for role, presentation in FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id, {}).items()
        if is_visible_presentation(presentation)
    }


def hidden_roles(section_id: str) -> set[str]:
    return set(FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id, {})) - visible_roles(section_id)


def story_arc_contract_errors(
    fact_policies: Mapping[str, Mapping[str, tuple[str, ...]]],
    semantic_dispositions: Mapping[str, Mapping[str, str]],
    role_presentations: Mapping[str, Mapping[str, str]] = FINAL_NARRATIVE_ROLE_PRESENTATIONS,
    chapters: Mapping[str, StoryChapter] = STORY_CHAPTERS,
) -> list[str]:
    errors: list[str] = []
    expected_sections = set(chapters)
    for label, registry in (
        ("fact policy", fact_policies),
        ("semantic disposition", semantic_dispositions),
        ("role presentation", role_presentations),
    ):
        if set(registry) != expected_sections:
            errors.append(f"story arc {label} sections do not match chapter registry")

    ordered = sorted(chapters.values(), key=lambda item: item.order)
    if [item.order for item in ordered] != list(range(1, len(ordered) + 1)):
        errors.append("story chapter order is not contiguous")
    proposition_owners: dict[str, str] = {}
    seen_sections: set[str] = set()
    for chapter in ordered:
        missing_dependencies = set(chapter.depends_on) - seen_sections
        if missing_dependencies:
            errors.append(
                f"{chapter.section_id}: chapter depends on later or missing pages "
                f"{sorted(missing_dependencies)}"
            )
        previous = proposition_owners.get(chapter.proposition_key)
        if previous:
            errors.append(
                f"visible proposition {chapter.proposition_key} is owned by both "
                f"{previous} and {chapter.section_id}"
            )
        proposition_owners[chapter.proposition_key] = chapter.section_id
        seen_sections.add(chapter.section_id)

    valid_presentations = {
        "visible-claim",
        "visible-boundary",
        "hidden-support",
        "hidden-routing",
    }
    for section_id in expected_sections:
        policy_roles = set((fact_policies.get(section_id) or {}).get("allowedRoles") or ())
        semantic_roles = set(semantic_dispositions.get(section_id) or {})
        presentation_roles = set(role_presentations.get(section_id) or {})
        if policy_roles != semantic_roles or policy_roles != presentation_roles:
            errors.append(
                f"{section_id}: story role registry mismatch: "
                f"policy={sorted(policy_roles)} semantic={sorted(semantic_roles)} "
                f"presentation={sorted(presentation_roles)}"
            )
        invalid = {
            value
            for value in (role_presentations.get(section_id) or {}).values()
            if value not in valid_presentations
        }
        if invalid:
            errors.append(f"{section_id}: unsupported role presentations {sorted(invalid)}")
        if not any(
            value == "visible-claim"
            for value in (role_presentations.get(section_id) or {}).values()
        ):
            errors.append(f"{section_id}: chapter introduces no visible claim")
    for section_id, role in REQUIRED_HIDDEN_STORY_ROLES:
        presentation = str((role_presentations.get(section_id) or {}).get(role) or "")
        if not presentation.startswith("hidden-"):
            errors.append(f"{section_id}:{role}: shared story control became visible")
    for section_id, role in REQUIRED_VISIBLE_CHAPTER_ROLES:
        presentation = str((role_presentations.get(section_id) or {}).get(role) or "")
        if not is_visible_presentation(presentation):
            errors.append(f"{section_id}:{role}: chapter lost its visible proposition")
    return errors


def story_arc_fact_errors(sections: Mapping[str, Any]) -> list[str]:
    """Validate the runtime handoff between shared controls and page claims."""

    errors: list[str] = []
    if set(sections) != set(STORY_CHAPTERS):
        return ["story arc fact section set is incomplete"]

    def role_values(section_id: str, role: str) -> list[str]:
        section = sections.get(section_id) if isinstance(sections.get(section_id), dict) else {}
        return [
            str(item.get("valueKey") or "")
            for item in section.get("facts") or []
            if isinstance(item, dict) and item.get("role") == role
        ]

    for section_id, section in sections.items():
        facts = section.get("facts") if isinstance(section, dict) else []
        for fact in facts or []:
            if not isinstance(fact, dict):
                continue
            role = str(fact.get("role") or "")
            if role not in FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id, {}):
                errors.append(f"{section_id}: fact has no story presentation: {role}")

    action_mode = role_values("action-direction", "action-mode")
    action_purpose = role_values("action-direction", "action-purpose")
    completion = role_values("action-direction", "completion-boundary")
    if action_mode and action_purpose and action_mode[0] != action_purpose[0]:
        errors.append("action purpose is disconnected from the selected action")
    if action_mode and completion and action_mode[0] != completion[0]:
        errors.append("action completion boundary is disconnected from the selected action")
    return errors


__all__ = [
    "FINAL_NARRATIVE_ROLE_PRESENTATIONS",
    "FINAL_NARRATIVE_STORY_ARC_VERSION",
    "REQUIRED_HIDDEN_STORY_ROLES",
    "REQUIRED_VISIBLE_CHAPTER_ROLES",
    "STORY_CHAPTERS",
    "StoryChapter",
    "hidden_roles",
    "is_visible_presentation",
    "story_arc_contract_errors",
    "story_arc_fact_errors",
    "visible_roles",
]
