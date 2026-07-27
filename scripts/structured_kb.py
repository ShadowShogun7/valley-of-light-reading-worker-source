from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from kb_utils import ROOT, read_text


STRUCTURED_KB_DIR = ROOT / "kb"
ATOM_DIR = STRUCTURED_KB_DIR / "atoms"
RULE_DIR = STRUCTURED_KB_DIR / "rules"
QUESTION_BLUEPRINT_DIR = STRUCTURED_KB_DIR / "question_blueprints"
GUARDRAIL_DIR = STRUCTURED_KB_DIR / "guardrails"

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RULE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppliesTo(StrictModel):
    products: list[str] = Field(default_factory=list)
    stages: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class AtomSelector(StrictModel):
    points_any: list[str] = Field(default_factory=list)
    points_all: list[str] = Field(default_factory=list)
    aspects_any: list[str] = Field(default_factory=list)
    contact_types_any: list[str] = Field(default_factory=list)
    precision_any: list[str] = Field(default_factory=list)
    transit_points_any: list[str] = Field(default_factory=list)
    natal_points_any: list[str] = Field(default_factory=list)
    timing_categories_any: list[str] = Field(default_factory=list)
    window_bands_any: list[str] = Field(default_factory=list)
    relationship_functions_any: list[str] = Field(default_factory=list)


class AtomInterpretation(StrictModel):
    summary_template: str
    empty_summary: str
    interpretation: str
    does_not_prove: str
    confidence_floor: Literal["low", "medium", "high"] = "low"


class InterpretationAtom(StrictModel):
    id: str
    system: Literal["western", "bazi", "context", "cross"]
    layer: Literal["identity", "synastry", "timing", "precision", "context"]
    category: str
    label: str
    source_article_id: str
    claim_ids: list[str] = Field(default_factory=list)
    applies_to: AppliesTo = Field(default_factory=AppliesTo)
    selectors: AtomSelector = Field(default_factory=AtomSelector)
    interpretation: AtomInterpretation

    @field_validator("id", "source_article_id")
    @classmethod
    def validate_kebab_id(cls, value: str) -> str:
        if not ID_RE.fullmatch(value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @field_validator("claim_ids")
    @classmethod
    def validate_claim_ids(cls, value: list[str]) -> list[str]:
        for claim_id in value:
            if not ID_RE.fullmatch(claim_id):
                raise ValueError(f"claim id must be kebab-case ASCII: {claim_id}")
        return value


class AtomFile(StrictModel):
    version: Literal["kb-atoms-v1"]
    atoms: list[InterpretationAtom]

    @model_validator(mode="after")
    def validate_unique_atom_ids(self) -> "AtomFile":
        ids = [atom.id for atom in self.atoms]
        duplicates = sorted(atom_id for atom_id in set(ids) if ids.count(atom_id) > 1)
        if duplicates:
            raise ValueError(f"duplicate atom ids: {', '.join(duplicates)}")
        return self


class RuleCondition(StrictModel):
    cluster: str | None = None
    field: str
    op: Literal["gte", "gt", "lte", "lt", "eq", "neq", "exists", "missing"]
    value: float | int | str | bool | None = None

    @model_validator(mode="after")
    def validate_operator_value(self) -> "RuleCondition":
        if self.op not in {"exists", "missing"} and self.value is None:
            raise ValueError(f"condition `{self.field}` with op `{self.op}` requires value")
        return self


class RuleWhen(StrictModel):
    all: list[RuleCondition] = Field(default_factory=list)
    any: list[RuleCondition] = Field(default_factory=list)


class RuleOutput(StrictModel):
    short_answer: str
    therefore: str
    because_clusters: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"


class ReadingRule(StrictModel):
    id: str
    question: str
    priority: int = 0
    when: RuleWhen = Field(default_factory=RuleWhen)
    output: RuleOutput

    @field_validator("id")
    @classmethod
    def validate_rule_id(cls, value: str) -> str:
        if not RULE_ID_RE.fullmatch(value):
            raise ValueError("must be kebab-case ASCII")
        return value


class RuleFile(StrictModel):
    version: Literal["kb-rules-v1"]
    ruleset_id: str
    applies_to: AppliesTo = Field(default_factory=AppliesTo)
    rules: list[ReadingRule]

    @field_validator("ruleset_id")
    @classmethod
    def validate_ruleset_id(cls, value: str) -> str:
        if not ID_RE.fullmatch(value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @model_validator(mode="after")
    def validate_unique_rule_ids(self) -> "RuleFile":
        ids = [rule.id for rule in self.rules]
        duplicates = sorted(rule_id for rule_id in set(ids) if ids.count(rule_id) > 1)
        if duplicates:
            raise ValueError(f"duplicate rule ids: {', '.join(duplicates)}")
        return self


class BlueprintEvidenceSource(StrictModel):
    source: str
    limit: int = Field(default=1, ge=1)


class QuestionBlueprintChapter(StrictModel):
    id: str
    title: str
    source_dimensions: list[str] = Field(default_factory=list)
    core_summary_source: Literal["shortAnswer", "therefore"] = "shortAnswer"
    chapter_angle: str
    must_answer: list[str] = Field(default_factory=list)
    do_not_repeat: list[str] = Field(default_factory=list)
    technical_focus: str
    psychological_focus: str
    evidence: list[BlueprintEvidenceSource] = Field(default_factory=list)
    evidence_limit: int = Field(default=5, ge=1)
    emotional_direction: str
    paid_boundary: str
    forbidden_claims: list[str] = Field(default_factory=list)
    next_bridge: str

    @field_validator("id")
    @classmethod
    def validate_chapter_id(cls, value: str) -> str:
        if not ID_RE.fullmatch(value):
            raise ValueError("must be kebab-case ASCII")
        return value


class QuestionBlueprintQuestion(StrictModel):
    question: str
    label: str
    source_article_id: str
    claim_ids: list[str] = Field(default_factory=list)
    answer_contract: str
    because_clusters: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)

    @field_validator("question", "source_article_id")
    @classmethod
    def validate_question_ids(cls, value: str) -> str:
        if not ID_RE.fullmatch(value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @field_validator("claim_ids")
    @classmethod
    def validate_question_claim_ids(cls, value: list[str]) -> list[str]:
        for claim_id in value:
            if not ID_RE.fullmatch(claim_id):
                raise ValueError(f"claim id must be kebab-case ASCII: {claim_id}")
        return value


class QuestionBlueprintFile(StrictModel):
    version: Literal["kb-question-blueprints-v1"]
    blueprint_id: str
    applies_to: AppliesTo = Field(default_factory=AppliesTo)
    title_direction: str
    story_arc_template: str
    chapter_order: list[str] = Field(default_factory=list)
    global_forbidden_claims: list[str] = Field(default_factory=list)
    style_rules: list[str] = Field(default_factory=list)
    paid_unlock: list[str] = Field(default_factory=list)
    questions: list[QuestionBlueprintQuestion] = Field(default_factory=list)
    chapters: list[QuestionBlueprintChapter] = Field(default_factory=list)

    @field_validator("blueprint_id")
    @classmethod
    def validate_blueprint_id(cls, value: str) -> str:
        if not ID_RE.fullmatch(value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @field_validator("chapter_order")
    @classmethod
    def validate_chapter_order_ids(cls, value: list[str]) -> list[str]:
        for chapter_id in value:
            if not ID_RE.fullmatch(chapter_id):
                raise ValueError(f"chapter id must be kebab-case ASCII: {chapter_id}")
        return value

    @model_validator(mode="after")
    def validate_blueprint_references(self) -> "QuestionBlueprintFile":
        questions = [question.question for question in self.questions]
        duplicate_questions = sorted(question for question in set(questions) if questions.count(question) > 1)
        if duplicate_questions:
            raise ValueError(f"duplicate question ids: {', '.join(duplicate_questions)}")

        chapter_ids = [chapter.id for chapter in self.chapters]
        duplicate_chapters = sorted(chapter_id for chapter_id in set(chapter_ids) if chapter_ids.count(chapter_id) > 1)
        if duplicate_chapters:
            raise ValueError(f"duplicate chapter ids: {', '.join(duplicate_chapters)}")

        missing_order = [chapter_id for chapter_id in self.chapter_order if chapter_id not in chapter_ids]
        if missing_order:
            raise ValueError(f"chapter_order references missing chapters: {', '.join(missing_order)}")
        return self


class PrecisionGuardrail(StrictModel):
    id: str
    system: Literal["western", "bazi", "context", "cross"]
    category: Literal["precision", "safety", "method"]
    source_article_id: str
    claim_ids: list[str] = Field(default_factory=list)
    applies_to: list[str] = Field(default_factory=list)
    points_any: list[str] = Field(default_factory=list)
    precision_any: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    lowers_confidence: list[str] = Field(default_factory=list)
    display: Literal["allowed", "allowed_with_uncertainty", "blocked", "not_available"]
    reason: str

    @field_validator("id", "source_article_id")
    @classmethod
    def validate_guardrail_ids(cls, value: str) -> str:
        if not ID_RE.fullmatch(value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @field_validator("claim_ids")
    @classmethod
    def validate_guardrail_claim_ids(cls, value: list[str]) -> list[str]:
        for claim_id in value:
            if not ID_RE.fullmatch(claim_id):
                raise ValueError(f"claim id must be kebab-case ASCII: {claim_id}")
        return value


class GuardrailFile(StrictModel):
    version: Literal["kb-guardrails-v1"]
    guardrail_id: str
    applies_to: AppliesTo = Field(default_factory=AppliesTo)
    guardrails: list[PrecisionGuardrail]

    @field_validator("guardrail_id")
    @classmethod
    def validate_guardrail_file_id(cls, value: str) -> str:
        if not ID_RE.fullmatch(value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @model_validator(mode="after")
    def validate_unique_guardrail_ids(self) -> "GuardrailFile":
        ids = [guardrail.id for guardrail in self.guardrails]
        duplicates = sorted(guardrail_id for guardrail_id in set(ids) if ids.count(guardrail_id) > 1)
        if duplicates:
            raise ValueError(f"duplicate guardrail ids: {', '.join(duplicates)}")
        return self


@dataclass
class StructuredCompileResult:
    atom_count: int
    rule_count: int
    question_blueprint_count: int
    guardrail_count: int
    atom_files: int
    rule_files: int
    question_blueprint_files: int
    guardrail_files: int


def structured_yaml_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([*directory.rglob("*.yml"), *directory.rglob("*.yaml")])


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(read_text(path)) or {}
    if not isinstance(payload, dict):
        raise ValueError("YAML root must be a mapping")
    return payload


def load_atom_files() -> list[tuple[Path, AtomFile]]:
    parsed: list[tuple[Path, AtomFile]] = []
    for path in structured_yaml_files(ATOM_DIR):
        try:
            parsed.append((path, AtomFile.model_validate(read_yaml_mapping(path))))
        except (ValidationError, ValueError) as exc:
            raise SystemExit(f"Atom validation failed in {path.relative_to(ROOT)}:\n{exc}") from exc
    return parsed


def load_rule_files() -> list[tuple[Path, RuleFile]]:
    parsed: list[tuple[Path, RuleFile]] = []
    for path in structured_yaml_files(RULE_DIR):
        try:
            parsed.append((path, RuleFile.model_validate(read_yaml_mapping(path))))
        except (ValidationError, ValueError) as exc:
            raise SystemExit(f"Rule validation failed in {path.relative_to(ROOT)}:\n{exc}") from exc
    return parsed


def load_question_blueprint_files() -> list[tuple[Path, QuestionBlueprintFile]]:
    parsed: list[tuple[Path, QuestionBlueprintFile]] = []
    for path in structured_yaml_files(QUESTION_BLUEPRINT_DIR):
        try:
            parsed.append((path, QuestionBlueprintFile.model_validate(read_yaml_mapping(path))))
        except (ValidationError, ValueError) as exc:
            raise SystemExit(f"Question blueprint validation failed in {path.relative_to(ROOT)}:\n{exc}") from exc
    return parsed


def load_guardrail_files() -> list[tuple[Path, GuardrailFile]]:
    parsed: list[tuple[Path, GuardrailFile]] = []
    for path in structured_yaml_files(GUARDRAIL_DIR):
        try:
            parsed.append((path, GuardrailFile.model_validate(read_yaml_mapping(path))))
        except (ValidationError, ValueError) as exc:
            raise SystemExit(f"Guardrail validation failed in {path.relative_to(ROOT)}:\n{exc}") from exc
    return parsed


def validate_cross_references(
    atoms: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    question_blueprints: list[dict[str, Any]],
    guardrails: list[dict[str, Any]],
    article_ids: set[str],
    claim_ids: set[str],
) -> None:
    atom_ids = [str(atom["id"]) for atom in atoms]
    duplicate_atoms = sorted(atom_id for atom_id in set(atom_ids) if atom_ids.count(atom_id) > 1)
    if duplicate_atoms:
        raise SystemExit(f"Duplicate structured atom ids: {', '.join(duplicate_atoms)}")

    categories = {str(atom["category"]) for atom in atoms}
    for atom in atoms:
        source_article_id = str(atom.get("source_article_id") or "")
        if article_ids and source_article_id not in article_ids:
            raise SystemExit(f"Atom `{atom['id']}` references missing article `{source_article_id}`")
        for claim_id in atom.get("claim_ids") or []:
            if claim_ids and claim_id not in claim_ids:
                raise SystemExit(f"Atom `{atom['id']}` references missing claim `{claim_id}`")

    rule_ids = [str(rule["id"]) for rule in rules]
    duplicate_rules = sorted(rule_id for rule_id in set(rule_ids) if rule_ids.count(rule_id) > 1)
    if duplicate_rules:
        raise SystemExit(f"Duplicate structured rule ids: {', '.join(duplicate_rules)}")

    for rule in rules:
        for cluster in rule.get("output", {}).get("because_clusters") or []:
            if cluster not in categories:
                raise SystemExit(f"Rule `{rule['id']}` output references unknown cluster `{cluster}`")
        for group_name in ("all", "any"):
            for condition in rule.get("when", {}).get(group_name) or []:
                cluster = condition.get("cluster")
                if cluster and cluster not in categories:
                    raise SystemExit(f"Rule `{rule['id']}` condition references unknown cluster `{cluster}`")

    blueprint_ids = [str(blueprint["blueprint_id"]) for blueprint in question_blueprints]
    duplicate_blueprints = sorted(
        blueprint_id for blueprint_id in set(blueprint_ids) if blueprint_ids.count(blueprint_id) > 1
    )
    if duplicate_blueprints:
        raise SystemExit(f"Duplicate structured question blueprint ids: {', '.join(duplicate_blueprints)}")

    for blueprint in question_blueprints:
        for question in blueprint.get("questions") or []:
            source_article_id = str(question.get("source_article_id") or "")
            if article_ids and source_article_id not in article_ids:
                raise SystemExit(
                    f"Question blueprint `{blueprint['blueprint_id']}` references missing article `{source_article_id}`"
                )
            for claim_id in question.get("claim_ids") or []:
                if claim_ids and claim_id not in claim_ids:
                    raise SystemExit(
                        f"Question blueprint `{blueprint['blueprint_id']}` references missing claim `{claim_id}`"
                    )
            for cluster in question.get("because_clusters") or []:
                if cluster not in categories:
                    raise SystemExit(
                        f"Question blueprint `{blueprint['blueprint_id']}` references unknown cluster `{cluster}`"
                    )

    guardrail_ids = [str(guardrail["id"]) for guardrail in guardrails]
    duplicate_guardrails = sorted(guardrail_id for guardrail_id in set(guardrail_ids) if guardrail_ids.count(guardrail_id) > 1)
    if duplicate_guardrails:
        raise SystemExit(f"Duplicate structured guardrail ids: {', '.join(duplicate_guardrails)}")

    for guardrail in guardrails:
        source_article_id = str(guardrail.get("source_article_id") or "")
        if article_ids and source_article_id not in article_ids:
            raise SystemExit(f"Guardrail `{guardrail['id']}` references missing article `{source_article_id}`")
        for claim_id in guardrail.get("claim_ids") or []:
            if claim_ids and claim_id not in claim_ids:
                raise SystemExit(f"Guardrail `{guardrail['id']}` references missing claim `{claim_id}`")


def compile_structured_kb(
    out_dir: Path,
    articles: list[dict[str, Any]] | None = None,
    claims: list[dict[str, Any]] | None = None,
) -> StructuredCompileResult:
    atom_files = load_atom_files()
    rule_files = load_rule_files()
    question_blueprint_files = load_question_blueprint_files()
    guardrail_files = load_guardrail_files()

    atoms: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    rulesets: list[dict[str, Any]] = []
    question_blueprints: list[dict[str, Any]] = []
    guardrails: list[dict[str, Any]] = []
    guardrail_sets: list[dict[str, Any]] = []

    for path, atom_file in atom_files:
        for atom in atom_file.atoms:
            atoms.append({**atom.model_dump(mode="json"), "path": str(path.relative_to(ROOT))})

    for path, rule_file in rule_files:
        rule_records = []
        for rule in rule_file.rules:
            record = rule.model_dump(mode="json")
            record["ruleset_id"] = rule_file.ruleset_id
            record["path"] = str(path.relative_to(ROOT))
            rules.append(record)
            rule_records.append(record)
        rulesets.append(
            {
                "version": rule_file.version,
                "ruleset_id": rule_file.ruleset_id,
                "applies_to": rule_file.applies_to.model_dump(mode="json"),
                "rule_ids": [rule["id"] for rule in rule_records],
                "path": str(path.relative_to(ROOT)),
            }
        )

    for path, blueprint_file in question_blueprint_files:
        record = blueprint_file.model_dump(mode="json")
        record["path"] = str(path.relative_to(ROOT))
        question_blueprints.append(record)

    for path, guardrail_file in guardrail_files:
        guardrail_records = []
        for guardrail in guardrail_file.guardrails:
            record = guardrail.model_dump(mode="json")
            record["guardrail_id"] = guardrail_file.guardrail_id
            record["path"] = str(path.relative_to(ROOT))
            guardrails.append(record)
            guardrail_records.append(record)
        guardrail_sets.append(
            {
                "version": guardrail_file.version,
                "guardrail_id": guardrail_file.guardrail_id,
                "applies_to": guardrail_file.applies_to.model_dump(mode="json"),
                "guardrail_ids": [guardrail["id"] for guardrail in guardrail_records],
                "path": str(path.relative_to(ROOT)),
            }
        )

    article_ids = {str(article.get("id")) for article in articles or []}
    claim_ids = {str(claim.get("claim_id")) for claim in claims or []}
    validate_cross_references(atoms, rules, question_blueprints, guardrails, article_ids, claim_ids)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "kb_atoms.json").write_text(
        json.dumps({"version": "kb-atoms-v1", "atoms": atoms}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "kb_rules.json").write_text(
        json.dumps({"version": "kb-rules-v1", "rulesets": rulesets, "rules": rules}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "kb_question_blueprints.json").write_text(
        json.dumps(
            {"version": "kb-question-blueprints-v1", "blueprints": question_blueprints},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "kb_guardrails.json").write_text(
        json.dumps(
            {"version": "kb-guardrails-v1", "guardrail_sets": guardrail_sets, "guardrails": guardrails},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return StructuredCompileResult(
        atom_count=len(atoms),
        rule_count=len(rules),
        question_blueprint_count=len(question_blueprints),
        guardrail_count=len(guardrails),
        atom_files=len(atom_files),
        rule_files=len(rule_files),
        question_blueprint_files=len(question_blueprint_files),
        guardrail_files=len(guardrail_files),
    )
