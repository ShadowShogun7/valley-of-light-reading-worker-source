#!/usr/bin/env python3
"""Verify R6 hard Traditional-Chinese quality gates for all final pages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_final_narrative_native_zh_tw import native_sentence_trace  # noqa: E402
from readable_interpretation.final_narrative_chinese_quality import (  # noqa: E402
    FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_MODE,
    FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
    FORBIDDEN_VISIBLE_TERMS,
    KNOWN_READER_REGRESSION_PHRASES,
    audit_hard_native_zh_tw_field,
    field_sentences,
    hard_quality_contract_errors,
    hard_quality_contract_fingerprint,
    hard_quality_contract_payload,
)
from readable_interpretation.final_narrative_composition import (  # noqa: E402
    FINAL_NARRATIVE_COMPOSITION_VERSION,
    SECTION_COMPOSITION_RULES,
    FinalNarrativeCompositionError,
    validate_section_composition,
)
from readable_interpretation.final_narrative_page_grammar import VISIBLE_FIELDS  # noqa: E402
from readable_interpretation.final_narrative_story_arc import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
    is_visible_presentation,
)
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    action_catalog_errors,
    action_sentence_traces,
)
from readable_interpretation.final_narrative_pages.chart_positioning_zh_tw_catalog import (  # noqa: E402
    catalog_errors as chart_catalog_errors,
    catalog_sentence_traces,
)
from readable_interpretation.final_narrative_pages.core_answer_renderer import (  # noqa: E402
    core_answer_catalog_errors,
    core_answer_sentence_traces,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    catalog_errors as relationship_fit_catalog_errors,
    relationship_fit_sentence_traces,
)
from readable_interpretation.final_narrative_pages.timing_renderer import (  # noqa: E402
    ASPECT_DOMAIN,
    WINDOW_CATEGORY_COPY,
    WINDOW_TRIGGER_KEYS,
    timing_catalog_errors,
    timing_sentence_trace,
    timing_static_sentence_traces,
    timing_window_sentence,
)


DEFAULT_CONTRACT_PATH = (
    ROOT
    / "data"
    / "reading-quality-cases"
    / "final-narrative-native-zh-tw-quality-contract-v1.json"
)
DEFAULT_CORPUS_PATH = (
    ROOT / "data" / "reading-production-calibration" / "v2" / "holdout-corpus.json"
)
DEFAULT_REPORT_PATH = (
    ROOT / "docs" / "research" / "41-final-narrative-native-zh-tw-r6-hard-gates.md"
)
NATIVE_REGRESSION_PATH = (
    ROOT
    / "data"
    / "reading-quality-cases"
    / "final-narrative-native-zh-tw-regressions-v1.json"
)
PHASE6_REGRESSION_PATH = (
    ROOT / "data" / "reading-quality-cases" / "final-narrative-phase6-regressions.json"
)
HUMAN_FEEDBACK_PATH = (
    ROOT
    / "data"
    / "reading-human-feedback"
    / "phase5-review-v2-regressions.json"
)
PRODUCTION_CONTRACT_PATH = (
    ROOT / "data" / "reading-quality-cases" / "final-layer-production-contract-v3.json"
)
QUALITY_CONTRACT_PATH = (
    ROOT / "data" / "reading-quality-cases" / "relationship-result-quality-v1.json"
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def trace_field(section_id: str, trace: Mapping[str, str]) -> str:
    role = str(trace.get("role") or "")
    purpose = str(trace.get("purpose") or "")
    presentation = str(
        (FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id) or {}).get(role) or ""
    )
    if presentation and not is_visible_presentation(presentation):
        return "__hidden__"
    special = {
        ("chart-positioning", "headline", "composition"): "headline",
        ("chart-positioning", "partner-pressure-response", "action"): "nextMove",
        ("relationship-fit", "fit-boundary", "boundary"): "caution",
    }
    selected = special.get((section_id, role, purpose))
    if selected:
        return selected
    owner = SECTION_COMPOSITION_RULES[section_id].role_owners.get(role)
    return owner.field if owner is not None else ""


def verify_contract_registry(contract_path: Path, *, update: bool) -> None:
    errors = hard_quality_contract_errors()
    require(not errors, f"R6 quality contract is invalid: {errors}")
    if update:
        write_json(contract_path, hard_quality_contract_payload())
    require(contract_path.exists(), "R6 machine-readable quality contract is missing")
    require(
        read_json(contract_path) == hard_quality_contract_payload(),
        "R6 machine-readable quality contract is stale",
    )
    require(
        FINAL_NARRATIVE_COMPOSITION_VERSION == "final-narrative-composition-v4",
        "R6 is not wired into the versioned final composition boundary",
    )


def verify_regression_registry() -> int:
    native = read_json(NATIVE_REGRESSION_PATH)
    phase6 = read_json(PHASE6_REGRESSION_PATH)
    feedback = read_json(HUMAN_FEEDBACK_PATH)
    source_phrases = {
        *(
            str(item.get("text") or "")
            for item in native.get("cases") or []
            if str(item.get("text") or "").strip()
        ),
        *(str(item) for item in phase6.get("forbiddenPhrases") or []),
        *(str(item) for item in feedback.get("forbiddenExactPhrases") or []),
    }
    require(
        source_phrases == set(KNOWN_READER_REGRESSION_PHRASES),
        "R6 compiled reader-regression registry diverged from source registries",
    )
    for phrase in source_phrases:
        issues = audit_hard_native_zh_tw_field("core-answer", "body", phrase)
        require(
            any(issue.id == "known-reader-regression" for issue in issues),
            f"R6 did not recognize reader regression: {phrase}",
        )

    production = read_json(PRODUCTION_CONTRACT_PATH)
    quality = read_json(QUALITY_CONTRACT_PATH)
    required_terms = {
        *(str(item) for item in production.get("forbiddenAbstractPhrases") or []),
        *(str(item) for item in quality.get("technical_terms") or []),
    }
    require(
        required_terms <= set(FORBIDDEN_VISIBLE_TERMS),
        "R6 forbidden-term registry lost a production contract term",
    )
    return len(source_phrases)


def verify_catalogs() -> dict[str, int]:
    catalog_errors = {
        "chart-positioning": chart_catalog_errors(),
        "relationship-fit": relationship_fit_catalog_errors(),
        "core-answer": core_answer_catalog_errors(),
        "timing-reading": timing_catalog_errors(),
        "action-direction": action_catalog_errors(),
    }
    for section_id, errors in catalog_errors.items():
        require(not errors, f"{section_id} catalog failed R6 base quality: {errors[:3]}")

    trace_builders: tuple[tuple[str, Callable[[], Mapping[str, Mapping[str, str]]]], ...] = (
        ("chart-positioning", catalog_sentence_traces),
        ("relationship-fit", relationship_fit_sentence_traces),
        ("core-answer", core_answer_sentence_traces),
        ("timing-reading", timing_static_sentence_traces),
        ("action-direction", action_sentence_traces),
    )
    counts: dict[str, int] = {}
    for section_id, builder in trace_builders:
        traces = builder()
        require(traces, f"{section_id} approved sentence trace registry is empty")
        for sentence, trace in traces.items():
            field = trace_field(section_id, trace)
            require(field, f"{section_id} traced sentence has no field owner: {trace}")
            if field == "__hidden__":
                continue
            issues = audit_hard_native_zh_tw_field(
                section_id,
                field,
                sentence,
                include_base_contract=False,
            )
            require(
                not issues,
                f"{section_id}:{field}: traced sentence failed R6: "
                + ", ".join(item.id for item in issues),
            )
        counts[section_id] = len(traces)

    dynamic_timing_count = 0
    for category in WINDOW_CATEGORY_COPY:
        for trigger in WINDOW_TRIGGER_KEYS:
            for aspect in ASPECT_DOMAIN:
                value_key = f"2026-07-mid|{category}|{trigger}|{aspect}"
                sentence = timing_window_sentence(value_key, 0)
                issues = audit_hard_native_zh_tw_field(
                    "timing-reading",
                    "body",
                    sentence,
                )
                require(
                    not issues,
                    f"timing-reading:body:{value_key}: "
                    + ", ".join(item.id for item in issues),
                )
                trace = timing_sentence_trace(sentence)
                require(
                    trace
                    == {
                        "kind": "fact-realization",
                        "role": "timing-window",
                        "valueKey": value_key,
                        "purpose": "situational",
                    },
                    f"R6 timing trace is stale: {value_key}",
                )
                dynamic_timing_count += 1
    counts["timing-reading"] += dynamic_timing_count
    return counts


def verify_composed_corpus(corpus: Mapping[str, Any]) -> dict[str, int]:
    require(
        corpus.get("compositionVersion") == FINAL_NARRATIVE_COMPOSITION_VERSION,
        "R6 corpus composition version is stale",
    )
    require(
        corpus.get("hardQualityVersion")
        == FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "R6 corpus hard-quality version is stale",
    )
    require(
        corpus.get("hardQualityContractFingerprint")
        == hard_quality_contract_fingerprint(),
        "R6 corpus hard-quality fingerprint is stale",
    )
    cases = [item for item in corpus.get("matrixCases") or [] if isinstance(item, dict)]
    require(len(cases) == 500, f"R6 requires 500 matrix cases, got {len(cases)}")
    field_count = 0
    sentence_count = 0
    trace_count = 0
    maximum_sentence_characters = 0
    maximum_sentence_clauses = 0
    for case in cases:
        case_id = str(case.get("id") or "")
        sections = case.get("sections") if isinstance(case.get("sections"), dict) else {}
        require(
            set(sections) == set(SECTION_COMPOSITION_RULES),
            f"{case_id}: R6 section set is incomplete",
        )
        for section_id, section in sections.items():
            require(isinstance(section, dict), f"{case_id}:{section_id}: invalid section")
            validate_section_composition(section_id, section)
            for field in VISIBLE_FIELDS:
                field_count += 1
                text = str(section.get(field) or "")
                issues = audit_hard_native_zh_tw_field(section_id, field, text)
                require(
                    not issues,
                    f"{case_id}:{section_id}:{field}: "
                    + ", ".join(item.id for item in issues),
                )
                for sentence in field_sentences(text):
                    sentence_count += 1
                    maximum_sentence_characters = max(
                        maximum_sentence_characters,
                        len(sentence),
                    )
                    maximum_sentence_clauses = max(
                        maximum_sentence_clauses,
                        len([item for item in re.split(r"[，；;]", sentence) if item.strip()]),
                    )
                    trace = native_sentence_trace(section_id, sentence)
                    require(
                        trace is not None,
                        f"{case_id}:{section_id}:{field}: untraceable R6 sentence: {sentence}",
                    )
                    require(
                        trace_field(section_id, trace) == field,
                        f"{case_id}:{section_id}:{field}: sentence trace crossed field ownership",
                    )
                    trace_count += 1
    return {
        "caseCount": len(cases),
        "fieldCount": field_count,
        "sentenceCount": sentence_count,
        "traceCount": trace_count,
        "maximumSentenceCharacters": maximum_sentence_characters,
        "maximumSentenceClauses": maximum_sentence_clauses,
    }


def verify_deliberate_invalid_cases(corpus: Mapping[str, Any]) -> int:
    invalid = (
        (
            "stitched-headline",
            "timing-reading",
            "headline",
            "現在先不要急著往前：先看主動性",
            "stitched-headline",
        ),
        (
            "abstract-causal-assembly",
            "timing-reading",
            "body",
            "示好方式會牽動你們靠近的速度。",
            "abstract-causal-assembly",
        ),
        (
            "abstract-initiation-motion",
            "core-answer",
            "nextMove",
            "他再次開口，才表示主動性開始回到雙方之間。",
            "abstract-initiation-motion",
        ),
        (
            "abstract-analysis-noun",
            "core-answer",
            "body",
            "處理問題的速度是這段關係的關鍵變數。",
            "abstract-analysis-noun",
        ),
        (
            "unclear-continuation-subject",
            "action-direction",
            "body",
            "你讓訊息自然停下後，他仍自己延續，才值得保留下一次互動。",
            "unclear-continuation-subject",
        ),
        (
            "unnatural-weight-metaphor",
            "core-answer",
            "body",
            "你們一著急，原本的小事也容易一起變重。",
            "unnatural-weight-metaphor",
        ),
        (
            "answer-as-event",
            "core-answer",
            "body",
            "只要彼此繼續爭執，相同答案就會再次出現。",
            "answer-as-event",
        ),
        (
            "abstract-defense-cover",
            "core-answer",
            "body",
            "真正的問題容易被自我保護蓋過。",
            "abstract-defense-cover",
        ),
        (
            "abstract-self-expression",
            "relationship-fit",
            "body",
            "你自然表現自己時，他會立刻回應。",
            "abstract-self-expression",
        ),
        (
            "question-fragment-as-guidance",
            "core-answer",
            "nextMove",
            "他會不會自己恢復原本的聯絡方式。",
            "question-fragment-as-guidance",
        ),
        (
            "self-referential-pronoun",
            "core-answer",
            "body",
            "他說明自己的想法時，你會立刻想回應你的說法。",
            "self-referential-pronoun",
        ),
        (
            "attraction-defense-splice",
            "core-answer",
            "body",
            "你表達在意時，他更容易覺得自己沒有被尊重，吸引和敏感會一起放大。",
            "attraction-defense-splice",
        ),
        (
            "unnatural-attraction-collocation",
            "relationship-fit",
            "body",
            "你主動靠近時，他容易感到明顯的好感和火花。",
            "unnatural-attraction-collocation",
        ),
        (
            "dangling-routine-action",
            "relationship-fit",
            "nextMove",
            "你們比較容易把這個做法留在日常。",
            "dangling-routine-action",
        ),
        (
            "technical-fit-unknown",
            "relationship-fit",
            "nextMove",
            "現有線索還不足以指定最適合你們的調整方式。",
            "technical-fit-unknown",
        ),
        (
            "repeated-sentence-opening",
            "relationship-fit",
            "body",
            "你表達欣賞時，他感到被看見。你表達欣賞時，他仍覺得不被理解。",
            "repeated-sentence-opening",
        ),
        (
            "technical-term",
            "core-answer",
            "body",
            "你們的副動力需要再觀察。",
            "technical-or-abstract-visible-term",
        ),
        (
            "known-reader-regression",
            "relationship-fit",
            "body",
            "關係有機會透過耐心、規則和實際行動慢慢穩住。",
            "known-reader-regression",
        ),
        (
            "reader-meta-narration",
            "chart-positioning",
            "caution",
            "下一頁再看你們的互動。",
            "reader-meta-narration",
        ),
        (
            "missing-reader-anchor",
            "core-answer",
            "meaning",
            "適度調整之後通常會變得更加明顯。",
            "missing-reader-anchor",
        ),
        (
            "repeated-conjunction",
            "chart-positioning",
            "body",
            "他需要責任和界線和承諾才會安心。",
            "repeated-conjunction-chain",
        ),
        (
            "unmarked-polarity",
            "timing-reading",
            "body",
            "對話比較容易放鬆，雙方容易互相頂住。",
            "unmarked-polarity-shift",
        ),
        (
            "overlong-sentence",
            "core-answer",
            "body",
            "你需要先確認對方是否願意持續回應，也要確認彼此能否在沒有追問的時候自然延續互動，最後再看這段關係是否真的出現新的選擇。",
            "long-native-sentence",
        ),
        (
            "overloaded-sentence",
            "relationship-fit",
            "body",
            "你想靠近，他先退開，彼此開始猜測，對話變得緊繃，最後誰也沒有說清楚。",
            "overloaded-native-sentence",
        ),
        (
            "page-topic-leak",
            "relationship-fit",
            "body",
            "冷戰時你們都在等對方先開口。",
            "page-topic-leak",
        ),
        (
            "abstract-action",
            "action-direction",
            "nextMove",
            "你先適度調整，再看看彼此的反應。",
            "abstract-action-language",
        ),
        (
            "missing-completion-boundary",
            "action-direction",
            "body",
            "他有回覆就可以繼續靠近。",
            "missing-completion-boundary",
        ),
        (
            "missing-concrete-command",
            "action-direction",
            "nextMove",
            "你用更好的方式回應彼此。",
            "missing-concrete-command",
        ),
        (
            "missing-stopping-condition",
            "action-direction",
            "caution",
            "目前要保留自己的界線。",
            "missing-stopping-condition",
        ),
        (
            "timing-missing-pair-subject",
            "timing-reading",
            "body",
            "2026 年 7 月下旬前後，氣氛比較容易放鬆。",
            "timing-window-missing-pair-subject",
        ),
    )
    for label, section_id, field, text, expected_issue in invalid:
        issues = audit_hard_native_zh_tw_field(section_id, field, text)
        require(
            any(issue.id == expected_issue for issue in issues),
            f"R6 deliberate invalid case did not detect {expected_issue}: {label}",
        )

    cases = [item for item in corpus.get("matrixCases") or [] if isinstance(item, dict)]
    baseline = cases[0].get("sections") if cases else {}
    require(isinstance(baseline, dict) and baseline, "R6 mutation baseline is missing")
    for label, section_id, field, text, _expected_issue in invalid:
        mutated = dict(baseline[section_id])
        mutated[field] = text
        try:
            validate_section_composition(section_id, mutated)
        except FinalNarrativeCompositionError:
            continue
        raise AssertionError(f"central composition boundary accepted R6 invalid case: {label}")
    return len(invalid)


def evaluate(contract_path: Path, corpus_path: Path, *, update_contract: bool) -> dict[str, Any]:
    verify_contract_registry(contract_path, update=update_contract)
    complaint_count = verify_regression_registry()
    catalog_counts = verify_catalogs()
    corpus = read_json(corpus_path)
    corpus_metrics = verify_composed_corpus(corpus)
    invalid_count = verify_deliberate_invalid_cases(corpus)
    return {
        "passed": True,
        "version": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "rolloutMode": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_MODE,
        "contractFingerprint": hard_quality_contract_fingerprint(),
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "catalogSentenceCounts": catalog_counts,
        "catalogSentenceCount": sum(catalog_counts.values()),
        "knownReaderRegressionCount": complaint_count,
        "deliberateInvalidCaseCount": invalid_count,
        **corpus_metrics,
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return lines


def render_report(result: Mapping[str, Any]) -> str:
    catalog_rows = [
        [section_id, count]
        for section_id, count in (result.get("catalogSentenceCounts") or {}).items()
    ]
    lines = [
        "# Final Narrative Native Traditional Chinese R6 Hard Gates",
        "",
        "## Verdict",
        "",
        "- R6 implementation: **COMPLETE**",
        "- Hard release gate: **PASS**",
        "- Human sentence review: **PENDING R7**",
        "- Human production acceptance: **PENDING R8**",
        "",
        "R6 moves Chinese quality enforcement from page-local audits to the shared final composition",
        "boundary. Any catalog or future renderer that returns technical, abstract, overloaded, unowned,",
        "or previously rejected wording now fails before visible output can be assembled.",
        "",
        "## Contract",
        "",
        f"- Quality contract: `{result.get('version')}`",
        f"- Contract fingerprint: `{result.get('contractFingerprint')}`",
        f"- Composition boundary: `{result.get('compositionVersion')}`",
        f"- Rollout mode: `{result.get('rolloutMode')}`",
        "- Every R1 warning is a release failure under R6.",
        "- Runtime LLM and generic fallback remain forbidden.",
        "",
        "## Exhaustive Coverage",
        "",
        *markdown_table(["Page", "Approved sentence forms checked"], catalog_rows),
        "",
        f"- Total approved sentence forms checked: {result.get('catalogSentenceCount')}",
        f"- Calibration cases checked: {result.get('caseCount')}",
        f"- Composed fields checked: {result.get('fieldCount')}",
        f"- Composed sentences checked: {result.get('sentenceCount')}",
        f"- Exact sentence traces checked: {result.get('traceCount')}",
        f"- Maximum composed sentence length: {result.get('maximumSentenceCharacters')}",
        f"- Maximum composed sentence clauses: {result.get('maximumSentenceClauses')}",
        "",
        "## Hard Failures",
        "",
        "R6 rejects:",
        "",
        "- internal technical labels and abstract model language",
        "- known reader complaints and page-navigation narration",
        "- sentences without a reader-facing person, interaction, event, or data subject",
        "- unexplained positive/negative clause collisions and repeated conjunction chains",
        "- sentences above the approved load limits",
        "- page-topic leakage",
        "- colon-spliced headlines, abstract sentence assembly, and question fragments used as guidance",
        "- abstract action language, missing observable responses, and missing stopping conditions",
        "- dated timing sentences that do not explicitly identify the pair's interaction",
        "",
        f"Historical reader complaints locked: {result.get('knownReaderRegressionCount')}.",
        f"Deliberate invalid cases rejected at both audit and composition boundaries: {result.get('deliberateInvalidCaseCount')}.",
        "",
        "## Release Boundary",
        "",
        "The paid-stack verifier runs R6 before calibration and web checks. The report is also regenerated",
        "and compared byte-for-byte, so policy, catalog, corpus, or count changes cannot merge with stale",
        "quality evidence.",
        "",
        "R7 is next: build the sentence-review workflow on top of this frozen automated boundary. R8 then",
        "uses reviewed cases to make the final human production-acceptance decision.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--update-contract", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = evaluate(
            args.contract,
            args.corpus,
            update_contract=args.update_contract,
        )
    except (AssertionError, FinalNarrativeCompositionError, KeyError, ValueError) as exc:
        if args.json:
            print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Final narrative R6 Chinese quality verification failed: {exc}")
        return 1

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_report(result), encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print("Final narrative R6 Chinese quality verification passed")
        print(f"- approved sentence forms checked: {result['catalogSentenceCount']}")
        print(f"- composed fields checked: {result['fieldCount']}")
        print(f"- composed sentences checked: {result['sentenceCount']}")
        print(f"- reader complaints locked: {result['knownReaderRegressionCount']}")
        print(f"- deliberate invalid cases rejected: {result['deliberateInvalidCaseCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
