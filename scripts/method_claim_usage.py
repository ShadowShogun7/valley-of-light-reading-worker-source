from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from book_coverage import SourceCoverage, flattened_coverages, load_book_coverage_files
from book_digests import BookDigest, MethodClaim, flattened_digests, load_book_digest_files
from kb_utils import ROOT, read_text
from structured_kb import load_atom_files, load_guardrail_files, load_question_blueprint_files, load_rule_files
from complete_relationship_result_runtime import WESTERN_METHOD_TRACE_SECTIONS


RUNTIME_PATH = ROOT / "scripts" / "complete_relationship_result_runtime.py"
READABLE_RENDERER_PATHS = [
    ROOT / "scripts" / "readable_interpretation" / "__init__.py",
    ROOT / "scripts" / "readable_interpretation" / "schema.py",
    ROOT / "scripts" / "readable_interpretation" / "zh_tw.py",
]
FRONTEND_RESULT_PATHS = [
    ROOT / "apps" / "web" / "src" / "components" / "AstrologyResultPage.tsx",
    ROOT / "apps" / "web" / "src" / "data" / "complete-relationship-result.ts",
]

BLOCKED_TARGETS = {"compositeLayer", "relationshipChartLayer", "houseOverlayLayer"}
READABLE_TARGETS = {
    "readableInterpretation",
    "personProfile",
    "relationshipFit",
    "fitSummary",
    "actionDirection",
    "donts",
    "timeline",
}
FRONTEND_TARGETS = {
    "relationshipProfiles",
    "personProfile",
    "relationshipFit",
    "fitSummary",
    "safetyValidationLanguage",
    "answerEvidenceContract",
    "contextModifier",
    "actionBoundary",
    "actionDirection",
    "donts",
    "timeline",
    "includedReadingRows",
    "readingBlueprint",
    "readableInterpretation",
}
TARGET_ALIASES = {
    "personProfile": ["relationshipProfiles", "person_function_sign", "personA", "personB"],
    "natalRelationshipNeeds": ["identityNeeds", "relationshipProfiles", "western_need_points"],
    "relationshipProfiles": ["relationshipProfiles", "western_relationship_profiles"],
    "relationshipFit": ["fitSummary", "fit_summary", "relationshipFit"],
    "fitSummary": ["fitSummary", "fit_summary", "elementComparison", "luminaryComparison"],
    "safetyValidationLanguage": ["safetyValidationLanguage", "MoonVenus", "safety_validation"],
    "readingBlueprint": ["readingBlueprint", "western_relationship_reading_blueprint"],
    "evidenceReducer": ["because_clusters", "aspectPriority", "western_select_answer_rule"],
    "contextReducer": ["relationshipStage", "contactStatus", "emotionalRisk", "desiredOutcome"],
    "answerEvidenceContract": ["evidenceContract", "western_answer_contract_from_evidence"],
    "answerGuidance": ["answerGuidance", "answer_guidance_payload", "answer_guidance_readable_interpretation", "question_answer"],
    "contextModifier": ["contextModifier", "relationshipStage", "contactStatus", "contactSituationPolicy"],
    "contactSituationPolicy": ["contactSituationPolicy", "western-atom-contact-situation-policy", "contactActionScale", "contactActionMode", "timingCanOverrideBoundary", "contact_action_readable_interpretation", "question_action"],
    "nonfatalSynastrySafety": ["nonfatalSynastrySafety", "western-atom-nonfatal-synastry-safety", "modern-synastry-nonfatal"],
    "actionBoundary": ["actionBoundary", "contactStatus", "contactSituationPolicy", "consultationSafety"],
    "actionDirection": ["nextMove", "ActionDirectionPanel", "question_answer_readable_payload", "actionGuidance", "contact_action_readable_interpretation", "question_action"],
    "donts": ["donts", "BoundaryItem"],
    "timeline": ["timeline", "timeline_step_readable_interpretation"],
    "timingGuidance": ["timingGuidance", "timing_guidance_payload", "timing_guidance_readable_interpretation", "question_timing"],
    "timingWindowBand": ["timingWindowBand", "timingGuidance", "question_timing"],
    "timingContactReducer": ["timingContactReducer", "timingGuidance", "question_timing"],
    "relationshipResultRules": ["western-relationship-result-v1", "ruleset_id"],
    "methodGuardrail": ["guardrail", "method"],
    "precisionWarnings": ["birthDataQuality", "precision", "precisionWarnings"],
    "sunMoonAscProfile": ["western_sun_moon_asc_profile_cluster", "western-atom-sun-moon-asc-profile"],
    "timingMercuryMessage": ["timingMercuryCommunication", "message", "Mercury"],
    "includedReadingRows": ["includedReadingRows", "included_reading"],
    "compositeLayer": ["compositeLayer", "relationshipChartLayer"],
    "relationshipChartLayer": ["relationshipChartLayer", "compositeLayer"],
    "houseOverlayLayer": ["houseOverlayLayer", "houseRelationshipFactors"],
}


@dataclass(frozen=True)
class MethodClaimRecord:
    digest: BookDigest
    claim: MethodClaim


@dataclass
class UsageEvidence:
    artifact_type: str
    artifact_id: str
    path: str
    target: str = ""
    detail: str = ""


@dataclass
class ClaimUsageRecord:
    claim_id: str
    source_id: str
    digest_id: str
    implementation_status: str
    evidence_level: str
    runtime_targets: list[str]
    usages: list[UsageEvidence] = field(default_factory=list)

    @property
    def artifact_types(self) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for usage in self.usages:
            if usage.artifact_type in seen:
                continue
            seen.add(usage.artifact_type)
            output.append(usage.artifact_type)
        return output


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def as_json_text(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def unique_usages(usages: list[UsageEvidence]) -> list[UsageEvidence]:
    output: list[UsageEvidence] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for usage in usages:
        key = (usage.artifact_type, usage.artifact_id, usage.path, usage.target, usage.detail)
        if key in seen:
            continue
        seen.add(key)
        output.append(usage)
    return output


def target_patterns(target: str) -> set[str]:
    return {target, *TARGET_ALIASES.get(target, [])}


def text_mentions_target(text: str, target: str) -> bool:
    return any(pattern and pattern in text for pattern in target_patterns(target))


def method_claim_records() -> list[MethodClaimRecord]:
    return [
        MethodClaimRecord(digest=digest, claim=claim)
        for digest in flattened_digests(load_book_digest_files())
        for claim in digest.method_claims
    ]


def coverage_by_claim(coverages: list[SourceCoverage]) -> dict[str, list[tuple[SourceCoverage, Any]]]:
    output: dict[str, list[tuple[SourceCoverage, Any]]] = defaultdict(list)
    for coverage in coverages:
        for section in coverage.sections:
            for claim_id in section.digest_claim_ids:
                output[str(claim_id)].append((coverage, section))
    return output


def method_trace_by_claim() -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for section in WESTERN_METHOD_TRACE_SECTIONS:
        for claim_id in section.get("methodClaimIds") or []:
            output[str(claim_id)].append(section)
    return output


def scan_atom_usages(record: MethodClaimRecord) -> list[UsageEvidence]:
    usages: list[UsageEvidence] = []
    for path, atom_file in load_atom_files():
        for atom in atom_file.atoms:
            category = atom.category
            atom_text = as_json_text(atom.model_dump(mode="json"))
            for target in record.claim.runtime_targets:
                if category == target or text_mentions_target(atom_text, target):
                    usages.append(UsageEvidence("atom", atom.id, rel_path(path), target, f"category={category}"))
    return usages


def scan_rule_usages(record: MethodClaimRecord) -> list[UsageEvidence]:
    usages: list[UsageEvidence] = []
    for path, rule_file in load_rule_files():
        for rule in rule_file.rules:
            rule_payload = rule.model_dump(mode="json")
            rule_text = as_json_text(rule_payload)
            clusters: set[str] = set(rule.output.because_clusters)
            for group in (rule.when.all, rule.when.any):
                for condition in group:
                    if condition.cluster:
                        clusters.add(condition.cluster)
            for target in record.claim.runtime_targets:
                if target == "relationshipResultRules" or clusters.intersection(target_patterns(target)) or text_mentions_target(rule_text, target):
                    usages.append(UsageEvidence("rule", rule.id, rel_path(path), target, f"question={rule.question}"))
    return usages


def scan_question_blueprint_usages(record: MethodClaimRecord) -> list[UsageEvidence]:
    usages: list[UsageEvidence] = []
    for path, blueprint_file in load_question_blueprint_files():
        payload = blueprint_file.model_dump(mode="json")
        text = as_json_text(payload)
        evidence_sources = {
            evidence.source
            for chapter in blueprint_file.chapters
            for evidence in chapter.evidence
        }
        question_clusters = {
            cluster
            for question in blueprint_file.questions
            for cluster in question.because_clusters
        }
        for target in record.claim.runtime_targets:
            if (
                target == "readingBlueprint"
                or evidence_sources.intersection(target_patterns(target))
                or question_clusters.intersection(target_patterns(target))
                or text_mentions_target(text, target)
            ):
                usages.append(
                    UsageEvidence("question_blueprint", blueprint_file.blueprint_id, rel_path(path), target)
                )
    return usages


def scan_guardrail_usages(record: MethodClaimRecord) -> list[UsageEvidence]:
    usages: list[UsageEvidence] = []
    for path, guardrail_file in load_guardrail_files():
        for guardrail in guardrail_file.guardrails:
            payload = guardrail.model_dump(mode="json")
            text = as_json_text(payload)
            for target in record.claim.runtime_targets:
                matches_special = (
                    target == "methodGuardrail" and guardrail.category == "method"
                ) or (
                    target == "precisionWarnings" and guardrail.category == "precision"
                ) or (
                    target in {"actionBoundary", "donts"} and guardrail.category in {"method", "safety"}
                )
                if matches_special or text_mentions_target(text, target):
                    usages.append(
                        UsageEvidence("guardrail", guardrail.id, rel_path(path), target, f"category={guardrail.category}")
                    )
    return usages


def scan_text_file_usages(
    record: MethodClaimRecord,
    artifact_type: str,
    paths: list[Path],
    *,
    allowed_targets: set[str] | None = None,
) -> list[UsageEvidence]:
    usages: list[UsageEvidence] = []
    for path in paths:
        if not path.exists():
            continue
        text = read_text(path)
        for target in record.claim.runtime_targets:
            if allowed_targets is not None and target not in allowed_targets:
                continue
            if text_mentions_target(text, target):
                usages.append(UsageEvidence(artifact_type, path.stem, rel_path(path), target))
    return usages


def scan_runtime_trace_usages(record: MethodClaimRecord) -> list[UsageEvidence]:
    return [
        UsageEvidence("runtime_trace", str(section.get("sectionId")), rel_path(RUNTIME_PATH), detail=str(section.get("title") or ""))
        for section in method_trace_by_claim().get(record.claim.id, [])
    ]


def scan_book_coverage_usages(record: MethodClaimRecord, coverage_index: dict[str, list[tuple[SourceCoverage, Any]]]) -> list[UsageEvidence]:
    usages: list[UsageEvidence] = []
    for coverage, section in coverage_index.get(record.claim.id, []):
        usages.append(
            UsageEvidence(
                "book_coverage",
                f"{coverage.source_id}:{section.section_id}",
                "kb/book_coverage",
                detail=f"status={section.status}",
            )
        )
        if section.status == "blocked":
            usages.append(
                UsageEvidence(
                    "blocked_future_layer",
                    f"{coverage.source_id}:{section.section_id}",
                    "kb/book_coverage",
                    detail=section.blocked_reason,
                )
            )
    return usages


def scan_blocked_future_usages(record: MethodClaimRecord) -> list[UsageEvidence]:
    if record.claim.implementation_status != "blocked" and not set(record.claim.runtime_targets).intersection(BLOCKED_TARGETS):
        return []
    return [
        UsageEvidence(
            "blocked_future_layer",
            "runtime-method-gaps",
            rel_path(RUNTIME_PATH),
            target=target,
            detail="not calculated or precision-gated in V1",
        )
        for target in record.claim.runtime_targets
        if record.claim.implementation_status == "blocked" or target in BLOCKED_TARGETS
    ]


def build_method_claim_usage_records() -> list[ClaimUsageRecord]:
    coverages = flattened_coverages(load_book_coverage_files())
    coverage_index = coverage_by_claim(coverages)
    records: list[ClaimUsageRecord] = []
    for record in method_claim_records():
        usages: list[UsageEvidence] = []
        usages.extend(scan_book_coverage_usages(record, coverage_index))
        usages.extend(scan_runtime_trace_usages(record))
        usages.extend(scan_atom_usages(record))
        usages.extend(scan_rule_usages(record))
        usages.extend(scan_question_blueprint_usages(record))
        usages.extend(scan_guardrail_usages(record))
        usages.extend(scan_text_file_usages(record, "runtime_builder", [RUNTIME_PATH]))
        usages.extend(scan_text_file_usages(record, "readable_renderer", READABLE_RENDERER_PATHS, allowed_targets=READABLE_TARGETS))
        usages.extend(scan_text_file_usages(record, "frontend_result", FRONTEND_RESULT_PATHS, allowed_targets=FRONTEND_TARGETS))
        usages.extend(scan_blocked_future_usages(record))
        records.append(
            ClaimUsageRecord(
                claim_id=record.claim.id,
                source_id=record.digest.source_id,
                digest_id=record.digest.id,
                implementation_status=record.claim.implementation_status,
                evidence_level=record.claim.evidence_level,
                runtime_targets=list(record.claim.runtime_targets),
                usages=unique_usages(usages),
            )
        )
    return records


def active_artifact_types(record: ClaimUsageRecord) -> set[str]:
    ignored = {"book_coverage"}
    if record.implementation_status != "blocked":
        ignored.add("blocked_future_layer")
    return {usage.artifact_type for usage in record.usages if usage.artifact_type not in ignored}


def validate_method_claim_usage(records: list[ClaimUsageRecord]) -> list[str]:
    errors: list[str] = []
    for record in records:
        usage_types = {usage.artifact_type for usage in record.usages}
        if "book_coverage" not in usage_types:
            errors.append(f"{record.claim_id}: missing book coverage entry")
        if record.implementation_status == "blocked":
            if "blocked_future_layer" not in usage_types:
                errors.append(f"{record.claim_id}: blocked claim lacks blocked_future_layer usage")
            continue
        active_types = active_artifact_types(record)
        if not active_types:
            errors.append(f"{record.claim_id}: active claim has no runtime artifact usage")
            continue
        if "runtime_builder" not in active_types and "runtime_trace" not in active_types:
            errors.append(f"{record.claim_id}: active claim lacks runtime_builder/runtime_trace usage")
        if record.implementation_status == "implemented" and "runtime_trace" not in active_types:
            errors.append(f"{record.claim_id}: implemented claim is not named in methodTrace")
    return errors


def usage_stats(records: list[ClaimUsageRecord]) -> dict[str, Any]:
    status_counts = Counter(record.implementation_status for record in records)
    artifact_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    target_counts: Counter[str] = Counter()
    for record in records:
        artifact_counts.update(record.artifact_types)
        source_counts[record.source_id] += 1
        target_counts.update(record.runtime_targets)
    errors = validate_method_claim_usage(records)
    return {
        "claim_count": len(records),
        "status_counts": dict(status_counts),
        "artifact_counts": dict(sorted(artifact_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "target_counts": dict(sorted(target_counts.items())),
        "error_count": len(errors),
    }
