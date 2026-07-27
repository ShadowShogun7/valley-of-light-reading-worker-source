#!/usr/bin/env python3
"""Build the deterministic Phase 0 relationship-reading baseline corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload  # noqa: E402
from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
    load_articles,
    load_claims_by_article,
)
from readable_interpretation.section_narrative_spec import (  # noqa: E402
    SECTION_NARRATIVE_IDS,
    SECTION_NARRATIVE_SPEC_VERSION,
)
from relationship_status_answer_policy import STAGE_ORDER, STATUS_POLICIES  # noqa: E402
from structured_runtime import load_structured_kb  # noqa: E402


GENERATOR_VERSION = "reading-production-baseline-v3"
PAIR_CORPUS_SEED_VERSION = "reading-production-baseline-v1"
BASELINE_VERSION = "relationship-reading-baseline-v1"
PHASE2_BASELINE_VERSION = "relationship-reading-baseline-v2"
PHASE3_BASELINE_VERSION = "relationship-reading-baseline-v3"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reading-production-baseline" / "v1"
PHASE2_OUTPUT_DIR = ROOT / "data" / "reading-production-baseline" / "v2"
PHASE3_OUTPUT_DIR = ROOT / "data" / "reading-production-baseline" / "v3"
ANALYSIS_DATE = "2026-07-10"
PROFILE_COUNT = 64
PLACES = (
    "Taipei, Taiwan",
    "New Taipei, Taiwan",
    "Taichung, Taiwan",
    "Tainan, Taiwan",
    "Kaohsiung, Taiwan",
    "Hsinchu, Taiwan",
    "Taoyuan, Taiwan",
)
QUESTIONS = tuple((STATUS_POLICIES[STAGE_ORDER[0]].get("questionRewrites") or {}).keys())
CONTACTS = ("blocked", "no-contact", "occasional-contact", "still-in-contact", "living-or-working-together")
EMOTIONAL_RISKS = ("calm", "anxious", "self-blaming", "desperate")
DESIRED_OUTCOMES = {
    "still-love-me": "reconnect",
    "any-chance": "decide",
    "when-to-contact": "reconnect",
    "what-did-i-do-wrong": "understand",
    "stay-or-let-go": "release",
}
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")
TEXT_NORMALIZER = re.compile(r"[^0-9A-Za-z\u3400-\u9fff]+")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def synthetic_profile(index: int, *, unknown_time: bool = False) -> dict[str, Any]:
    birth_date = date(1988, 1, 1) + timedelta(days=(index * 83 + index * index * 7) % 5113)
    minutes = (index * 97 + 7 * index * index) % (24 * 60)
    birth_time = None if unknown_time else f"{minutes // 60:02d}:{minutes % 60:02d}"
    return {
        "birth_date": birth_date.isoformat(),
        "birth_time": birth_time,
        "birth_timezone": "Asia/Taipei",
        "birth_place": PLACES[index % len(PLACES)],
        "gender": "female" if index % 2 == 0 else "male",
    }


def deterministic_pairs(count: int) -> list[tuple[int, int]]:
    candidates = list(itertools.combinations(range(PROFILE_COUNT), 2))
    candidates.sort(key=lambda pair: stable_hash({"seed": PAIR_CORPUS_SEED_VERSION, "pair": pair}))
    if count > len(candidates):
        raise ValueError(f"Requested {count} pairs but only {len(candidates)} are available")
    output: list[tuple[int, int]] = []
    for index, pair in enumerate(candidates[:count]):
        output.append(pair if index % 2 == 0 else (pair[1], pair[0]))
    return output


def context_for_index(index: int, *, timing_scan_days: int, timing_scan_step_days: int) -> dict[str, Any]:
    stage_index = index % len(STAGE_ORDER)
    question_index = (index // len(STAGE_ORDER)) % len(QUESTIONS)
    contact_index = (index + index // len(CONTACTS)) % len(CONTACTS)
    question = QUESTIONS[question_index]
    return {
        "relationship_stage": STAGE_ORDER[stage_index],
        "main_question": question,
        "contact_status": CONTACTS[contact_index],
        "desired_outcome": DESIRED_OUTCOMES[question],
        "emotional_risk": EMOTIONAL_RISKS[index % len(EMOTIONAL_RISKS)],
        "analysis_date": ANALYSIS_DATE,
        "timing_scan_days": timing_scan_days,
        "timing_scan_step_days": timing_scan_step_days,
    }


def reading_for_pair(
    *,
    reading_id: str,
    pair: tuple[int, int],
    context: dict[str, Any],
    mix_unknown_times: bool,
    record_index: int,
) -> dict[str, Any]:
    return {
        "reading_id": reading_id,
        "person_a": synthetic_profile(pair[0], unknown_time=mix_unknown_times and record_index % 10 == 0),
        "person_b": synthetic_profile(pair[1], unknown_time=mix_unknown_times and record_index % 10 == 5),
        "context": context,
    }


def chart_fingerprint(calculation_payload: dict[str, Any]) -> str:
    western = calculation_payload.get("western") if isinstance(calculation_payload.get("western"), dict) else {}
    people = western.get("people") if isinstance(western.get("people"), dict) else {}
    synastry = western.get("synastry") if isinstance(western.get("synastry"), dict) else {}
    return stable_hash(
        {
            "personA": ((people.get("person_a") or {}).get("objects") or {}),
            "personB": ((people.get("person_b") or {}).get("objects") or {}),
            "synastry": synastry.get("inter_aspects") or [],
        }
    )


def visible_sections(view_model: dict[str, Any]) -> dict[str, dict[str, str]]:
    final = view_model.get("finalInterpretation") if isinstance(view_model.get("finalInterpretation"), dict) else {}
    sections = final.get("sections") if isinstance(final.get("sections"), dict) else {}
    return {
        section_id: {
            field: str(((sections.get(section_id) or {}).get(field)) or "")
            for field in VISIBLE_FIELDS
        }
        for section_id in SECTION_NARRATIVE_IDS
    }


def hidden_model_summary(view_model: dict[str, Any]) -> dict[str, Any]:
    model = view_model.get("relationshipCaseModel") if isinstance(view_model.get("relationshipCaseModel"), dict) else {}
    thesis = view_model.get("relationshipThesis") if isinstance(view_model.get("relationshipThesis"), dict) else {}
    primary = model.get("primaryDynamic") if isinstance(model.get("primaryDynamic"), dict) else {}
    secondaries = [item for item in model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    repair = model.get("repairLever") if isinstance(model.get("repairLever"), dict) else {}
    blocker = model.get("emotionalBlocker") if isinstance(model.get("emotionalBlocker"), dict) else {}
    timing = model.get("timingPosture") if isinstance(model.get("timingPosture"), dict) else {}
    contact = model.get("contactPosture") if isinstance(model.get("contactPosture"), dict) else {}
    risk = model.get("riskPosture") if isinstance(model.get("riskPosture"), dict) else {}
    policy = view_model.get("relationshipStatusAnswerPolicy") if isinstance(view_model.get("relationshipStatusAnswerPolicy"), dict) else {}
    evidence_packet = [item for item in thesis.get("evidencePacket") or [] if isinstance(item, dict)]
    return {
        "version": str(model.get("version") or ""),
        "archetypeTitle": str((view_model.get("relationshipArchetype") or {}).get("title") or ""),
        "primaryDynamic": {"key": str(primary.get("key") or ""), "score": primary.get("score")},
        "secondaryDynamics": [
            {"key": str(item.get("key") or ""), "role": str(item.get("role") or ""), "score": item.get("score")}
            for item in secondaries
        ],
        "repairLeverKey": str(repair.get("key") or ""),
        "emotionalBlockerKey": str(blocker.get("key") or ""),
        "timingPostureKey": str(timing.get("key") or ""),
        "contactPostureKey": str(contact.get("key") or ""),
        "riskPostureKey": str(risk.get("key") or ""),
        "answerTrackKeys": [str(item) for item in policy.get("resolvedTracks") or [] if item],
        "thesisDynamicKey": str(thesis.get("centralDynamicKey") or ""),
        "selectedCandidateId": str(thesis.get("selectedCandidateId") or ""),
        "uncertaintyLevel": str((thesis.get("uncertainty") or {}).get("level") or ""),
        "evidence": [
            {
                "id": str(item.get("id") or ""),
                "domain": str(item.get("domain") or ""),
                "role": str(item.get("role") or ""),
                "confidence": item.get("confidence"),
                "relevance": item.get("relevance"),
                "sourceClaimIds": [str(claim_id) for claim_id in item.get("sourceClaimIds") or [] if claim_id],
                "methodClaimIds": [str(claim_id) for claim_id in item.get("methodClaimIds") or [] if claim_id],
                "evidenceClusterKeys": [str(key) for key in item.get("evidenceClusterKeys") or [] if key],
            }
            for item in evidence_packet
        ],
    }


def calculation_summary(calculation_payload: dict[str, Any]) -> dict[str, Any]:
    western = calculation_payload.get("western") if isinstance(calculation_payload.get("western"), dict) else {}
    people = western.get("people") if isinstance(western.get("people"), dict) else {}
    synastry = western.get("synastry") if isinstance(western.get("synastry"), dict) else {}
    warnings = ((calculation_payload.get("debug") or {}).get("calculation_warnings") or [])
    aspects = [item for item in synastry.get("inter_aspects") or [] if isinstance(item, dict)]
    return {
        "personABirthPrecision": str((people.get("person_a") or {}).get("birth_precision") or ""),
        "personBBirthPrecision": str((people.get("person_b") or {}).get("birth_precision") or ""),
        "interAspectCount": int(synastry.get("inter_aspect_count") or 0),
        "retainedAspectCount": len(aspects),
        "eligibleAspectCount": sum(1 for item in aspects if item.get("eligible_for_signal")),
        "warningCount": len(warnings),
    }


def build_runtime_case(
    reading: dict[str, Any],
    *,
    articles: dict[str, dict[str, Any]],
    claims: dict[str, list[dict[str, Any]]],
    structured_kb: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    calculation_payload = build_payload(reading, include_drafts=True, select=True)
    view_model = build_view_model(calculation_payload, articles, claims, structured_kb)
    return calculation_payload, view_model


def build_golden_record(reading: dict[str, Any], calculation_payload: dict[str, Any], view_model: dict[str, Any]) -> dict[str, Any]:
    hidden = hidden_model_summary(view_model)
    sections = visible_sections(view_model)
    specs = copy.deepcopy(view_model.get("sectionNarrativeSpecs") or {})
    pair_input = {"personA": reading["person_a"], "personB": reading["person_b"]}
    fingerprints = {
        "pairInput": stable_hash(pair_input),
        "context": stable_hash(reading["context"]),
        "chart": chart_fingerprint(calculation_payload),
        "hiddenModel": stable_hash(hidden),
        "visibleSections": stable_hash(sections),
        "sectionSpecs": stable_hash(specs),
    }
    return {
        "id": reading["reading_id"],
        "input": reading,
        "fingerprints": fingerprints,
        "calculation": calculation_summary(calculation_payload),
        "hiddenModel": hidden,
        "sectionSpecs": specs,
        "finalInterpretation": {
            "version": str((view_model.get("finalInterpretation") or {}).get("version") or ""),
            "sections": sections,
        },
    }


def build_distribution_record(reading: dict[str, Any], calculation_payload: dict[str, Any], view_model: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    hidden = hidden_model_summary(view_model)
    sections = visible_sections(view_model)
    specs = ((view_model.get("sectionNarrativeSpecs") or {}).get("sections") or {})
    fit_slots = (specs.get("relationship-fit") or {}).get("semanticSlots") or {}
    core_slots = (specs.get("core-answer") or {}).get("semanticSlots") or {}
    central_signal = core_slots.get("centralEvidenceSignal") if isinstance(core_slots.get("centralEvidenceSignal"), dict) else {}
    pair_input = {"personA": reading["person_a"], "personB": reading["person_b"]}
    record = {
        "id": reading["reading_id"],
        "input": pair_input,
        "pairFingerprint": stable_hash(pair_input),
        "chartFingerprint": chart_fingerprint(calculation_payload),
        "hiddenModelFingerprint": stable_hash(hidden),
        "archetypeTitle": hidden.get("archetypeTitle"),
        "primaryDynamicKey": (hidden.get("primaryDynamic") or {}).get("key"),
        "secondaryDynamicKeys": [item.get("key") for item in hidden.get("secondaryDynamics") or []],
        "fitPrimaryDynamicKey": fit_slots.get("primaryDynamicKey"),
        "fitSecondaryDynamicKeys": fit_slots.get("secondaryDynamicKeys") or [],
        "fitSignature": fit_slots.get("fitSignature"),
        "fitSignalCount": sum(
            len(fit_slots.get(key) or [])
            for key in ("attractionSignals", "frictionSignals", "growthSignals")
        ),
        "coreCentralEvidenceKey": central_signal.get("key"),
        "coreCentralEvidencePair": central_signal.get("pairKey"),
        "calculation": calculation_summary(calculation_payload),
        "sectionHeadlineHashes": {section_id: stable_hash(section["headline"]) for section_id, section in sections.items()},
        "sectionBodyHashes": {section_id: stable_hash(section["body"]) for section_id, section in sections.items()},
    }
    return record, sections


def normalize_text(value: str) -> str:
    return TEXT_NORMALIZER.sub("", value or "").lower()


def ngrams(value: str, size: int = 3) -> set[str]:
    normalized = normalize_text(value)
    if len(normalized) <= size:
        return {normalized} if normalized else set()
    return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}


def jaccard(left: str, right: str) -> float:
    left_grams = ngrams(left)
    right_grams = ngrams(right)
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


def counter_dict(values: Iterable[Any]) -> dict[str, int]:
    return dict(sorted(Counter(str(value or "unknown") for value in values).items()))


def section_metrics(rows: list[dict[str, dict[str, str]]], *, include_near_duplicates: bool) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for section_id in SECTION_NARRATIVE_IDS:
        headlines = [row[section_id]["headline"] for row in rows]
        bodies = [row[section_id]["body"] for row in rows]
        body_counts = Counter(normalize_text(body) for body in bodies)
        near_duplicate_pairs = 0
        if include_near_duplicates:
            for left_index, right_index in itertools.combinations(range(len(bodies)), 2):
                if normalize_text(bodies[left_index]) == normalize_text(bodies[right_index]):
                    continue
                if jaccard(bodies[left_index], bodies[right_index]) >= 0.72:
                    near_duplicate_pairs += 1
        metrics[section_id] = {
            "caseCount": len(rows),
            "uniqueHeadlines": len(set(normalize_text(value) for value in headlines)),
            "uniqueBodies": len(body_counts),
            "maxExactBodyRepeat": max(body_counts.values(), default=0),
            "exactBodyCollisionPairs": sum(count * (count - 1) // 2 for count in body_counts.values()),
            "nearDuplicateBodyPairsAt072": near_duplicate_pairs if include_near_duplicates else None,
        }
    return metrics


def corpus_metrics(
    golden_records: list[dict[str, Any]],
    distribution_records: list[dict[str, Any]],
    distribution_sections: list[dict[str, dict[str, str]]],
    *,
    baseline_version: str,
) -> dict[str, Any]:
    golden_sections = [record["finalInterpretation"]["sections"] for record in golden_records]
    contexts = [record["input"]["context"] for record in golden_records]
    return {
        "version": baseline_version,
        "golden": {
            "caseCount": len(golden_records),
            "uniquePairInputs": len({record["fingerprints"]["pairInput"] for record in golden_records}),
            "uniqueCharts": len({record["fingerprints"]["chart"] for record in golden_records}),
            "uniqueHiddenModels": len({record["fingerprints"]["hiddenModel"] for record in golden_records}),
            "validSectionSpecBundles": sum(
                1
                for record in golden_records
                if ((record.get("sectionSpecs") or {}).get("validation") or {}).get("status") == "valid"
            ),
            "stageCounts": counter_dict(context.get("relationship_stage") for context in contexts),
            "questionCounts": counter_dict(context.get("main_question") for context in contexts),
            "contactCounts": counter_dict(context.get("contact_status") for context in contexts),
            "sectionMetrics": section_metrics(golden_sections, include_near_duplicates=True),
        },
        "distribution": {
            "caseCount": len(distribution_records),
            "uniquePairInputs": len({record["pairFingerprint"] for record in distribution_records}),
            "uniqueCharts": len({record["chartFingerprint"] for record in distribution_records}),
            "uniqueHiddenModels": len({record["hiddenModelFingerprint"] for record in distribution_records}),
            "archetypeCounts": counter_dict(record.get("archetypeTitle") for record in distribution_records),
            "primaryDynamicCounts": counter_dict(record.get("primaryDynamicKey") for record in distribution_records),
            "fitPrimaryDynamicCounts": counter_dict(record.get("fitPrimaryDynamicKey") for record in distribution_records),
            "uniqueFitSignatures": len({record.get("fitSignature") for record in distribution_records}),
            "coreCentralEvidencePairCounts": counter_dict(
                record.get("coreCentralEvidencePair") for record in distribution_records
            ),
            "minimumFitSignalCount": min(
                (int(record.get("fitSignalCount") or 0) for record in distribution_records),
                default=0,
            ),
            "sectionMetrics": section_metrics(distribution_sections, include_near_duplicates=False),
        },
    }


def build_baseline(
    *,
    golden_count: int,
    distribution_count: int,
    golden_timing_days: int,
    golden_timing_step: int,
    progress_every: int,
    baseline_version: str = BASELINE_VERSION,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb()
    pair_count = max(golden_count, distribution_count)
    pairs = deterministic_pairs(pair_count)
    golden_records: list[dict[str, Any]] = []
    distribution_records: list[dict[str, Any]] = []
    distribution_sections: list[dict[str, dict[str, str]]] = []
    engine_versions: dict[str, Any] = {}

    for index, pair in enumerate(pairs[:golden_count]):
        reading = reading_for_pair(
            reading_id=f"golden-{index + 1:03d}",
            pair=pair,
            context=context_for_index(
                index,
                timing_scan_days=golden_timing_days,
                timing_scan_step_days=golden_timing_step,
            ),
            mix_unknown_times=True,
            record_index=index,
        )
        calculation_payload, view_model = build_runtime_case(
            reading,
            articles=articles,
            claims=claims,
            structured_kb=structured_kb,
        )
        if not engine_versions:
            engine_versions = copy.deepcopy((calculation_payload.get("debug") or {}).get("engine_versions") or {})
        golden_records.append(build_golden_record(reading, calculation_payload, view_model))
        if progress_every and (index + 1) % progress_every == 0:
            print(f"golden progress: {index + 1}/{golden_count}", file=sys.stderr, flush=True)

    fixed_distribution_context = {
        "relationship_stage": "cold-war",
        "main_question": "still-love-me",
        "contact_status": "no-contact",
        "desired_outcome": "reconnect",
        "emotional_risk": "calm",
        "analysis_date": ANALYSIS_DATE,
        "timing_scan_days": 0,
        "timing_scan_step_days": 2,
    }
    for index, pair in enumerate(pairs[:distribution_count]):
        reading = reading_for_pair(
            reading_id=f"distribution-{index + 1:03d}",
            pair=pair,
            context=copy.deepcopy(fixed_distribution_context),
            mix_unknown_times=False,
            record_index=index,
        )
        calculation_payload, view_model = build_runtime_case(
            reading,
            articles=articles,
            claims=claims,
            structured_kb=structured_kb,
        )
        record, sections = build_distribution_record(reading, calculation_payload, view_model)
        distribution_records.append(record)
        distribution_sections.append(sections)
        if progress_every and (index + 1) % progress_every == 0:
            print(f"distribution progress: {index + 1}/{distribution_count}", file=sys.stderr, flush=True)

    golden_payload = {"version": baseline_version, "records": golden_records}
    distribution_payload = {
        "version": baseline_version,
        "fixedContext": fixed_distribution_context,
        "records": distribution_records,
    }
    metrics = corpus_metrics(
        golden_records,
        distribution_records,
        distribution_sections,
        baseline_version=baseline_version,
    )
    manifest = {
        "version": baseline_version,
        "generatorVersion": GENERATOR_VERSION,
        "analysisDate": ANALYSIS_DATE,
        "syntheticDataOnly": True,
        "profileCount": PROFILE_COUNT,
        "goldenCaseCount": golden_count,
        "distributionCaseCount": distribution_count,
        "goldenTimingScanDays": golden_timing_days,
        "goldenTimingScanStepDays": golden_timing_step,
        "distributionTimingScanDays": 0,
        "supportedStages": list(STAGE_ORDER),
        "supportedQuestions": list(QUESTIONS),
        "supportedContacts": list(CONTACTS),
        "sectionIds": list(SECTION_NARRATIVE_IDS),
        "sectionSpecVersion": SECTION_NARRATIVE_SPEC_VERSION,
        "engineVersions": engine_versions,
    }
    return manifest, golden_payload, distribution_payload, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Phase 0 production reading baseline.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--baseline-version", default=BASELINE_VERSION)
    parser.add_argument("--golden-count", type=int, default=50)
    parser.add_argument("--distribution-count", type=int, default=500)
    parser.add_argument("--golden-timing-days", type=int, default=90)
    parser.add_argument("--golden-timing-step", type=int, default=2)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--quick", action="store_true", help="Build 5 golden and 20 distribution cases for development.")
    parser.add_argument("--write", action="store_true", help="Write corpus artifacts to the output directory.")
    args = parser.parse_args()

    golden_count = 5 if args.quick else max(1, args.golden_count)
    distribution_count = 20 if args.quick else max(1, args.distribution_count)
    manifest, golden, distribution, metrics = build_baseline(
        golden_count=golden_count,
        distribution_count=distribution_count,
        golden_timing_days=max(0, min(args.golden_timing_days, 90)),
        golden_timing_step=max(1, min(args.golden_timing_step, 7)),
        progress_every=max(0, args.progress_every),
        baseline_version=str(args.baseline_version),
    )

    if args.write:
        output_dir = args.output_dir
        golden_path = output_dir / "golden-cases.json"
        distribution_path = output_dir / "distribution-corpus.json"
        metrics_path = output_dir / "metrics.json"
        manifest_path = output_dir / "manifest.json"
        write_json(golden_path, golden)
        write_json(distribution_path, distribution)
        write_json(metrics_path, metrics)
        manifest["files"] = {
            "golden-cases.json": file_hash(golden_path),
            "distribution-corpus.json": file_hash(distribution_path),
            "metrics.json": file_hash(metrics_path),
        }
        write_json(manifest_path, manifest)
        print(f"Wrote production reading baseline -> {display_path(output_dir)}")
    else:
        print(json.dumps({"manifest": manifest, "metrics": metrics}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
