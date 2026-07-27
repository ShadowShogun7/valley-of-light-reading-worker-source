#!/usr/bin/env python3
"""Western-only complete relationship result runtime builder.

This module is the active astrology-branch contract boundary. The old
build_free_result_view_models.py entrypoint is now a compatibility wrapper; this
module owns the complete relationship-result assembly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from kb_utils import ROOT
from readable_interpretation.final_narrative_fact_contract import refresh_fact_contracts_in_payload
from readable_interpretation import (
    FUNCTION_SIGN_STYLES as READABLE_FUNCTION_SIGN_STYLES,
    FUNCTION_SIGN_TENSIONS as READABLE_FUNCTION_SIGN_TENSIONS,
    answer_guidance_payload,
    chance_readable_interpretation,
    final_reading_interpretation_payload,
    fit_item_readable_interpretation,
    fit_summary_readable_interpretation,
    person_function_sign_readable_interpretation,
    question_answer_readable_payload,
    reason_card_readable_interpretation,
    role_adjusted_relationship_text as readable_role_adjusted_relationship_text,
    timing_guidance_payload,
    timeline_step_readable_interpretation,
)
from relationship_status_answer_policy import (
    relationship_status_policy_section_title,
    resolve_relationship_status_answer_policy,
)
from structured_runtime import load_structured_kb

DEFAULT_CALCULATION_DIR = ROOT / "examples" / "calculations"


DEFAULT_ARTICLES_PATH = ROOT / "dist" / "kb" / "kb_articles.json"


DEFAULT_CLAIMS_PATH = ROOT / "dist" / "kb" / "kb_claims.json"


DEFAULT_OUTPUT_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"


SCENARIO_ORDER = [
    "cold-war-still-love-me",
    "broke-up-long-any-chance",
    "cold-war-when-to-contact",
    "broke-up-recent-what-did-i-do-wrong",
    "crisis-stay-or-let-go",
]

WESTERN_RELATIONSHIP_RESULT_ID = "western-relationship-result-v1"
LEGACY_WESTERN_FREE_RELATIONSHIP_ID = "western-free-relationship-v1"

PUBLIC_COPY_REPLACEMENTS = {
    "免費精準日期": "精準聯絡日期",
    "免費閱讀": "這份解讀",
    "免費結果": "這份解讀",
    "免費頁": "這份解讀",
    "免費版": "這份解讀",
    "免費 V0": "此版本",
    "V1 這份解讀": "此版本",
    "付費報告": "完整解讀",
    "付費層": "完整解讀",
    "付費深度層": "後續深度層",
    "完整報告": "完整解讀",
    "paid-depth": "後續深度層",
    "paid depth": "後續深度層",
    "paid report": "完整解讀",
    "paid 報告": "完整解讀",
    "paid expansion plan": "方法邊界",
    "free page": "this reading",
    "free result": "this reading",
    "free Western V0": "this version",
    "paid timing": "精細時機",
    "paid V1": "此版本",
    "精準日期與內容策略留到完整解讀": "這份解讀只會說哪種時段比較能承受互動，不承諾哪一天一定成功",
    "精準日期留到完整解讀": "不指定哪一天，只保留比較適合或需要避開的狀態",
    "精準日期": "指定日期",
    "精準日": "指定日期",
    "低刺激": "短、輕、能自然停下",
    "低壓": "壓力較輕",
    "低壓靠近入口": "壓力較輕的靠近方式",
    "壓力較輕靠近入口": "壓力較輕的靠近方式",
    "可不回": "對方可以先不回",
    "不保證對方會回來": "不能當成對方會回來的證明",
    "保證對方會回來": "當成對方會回來的證明",
    "不保證會回來": "不能當成會回來的證明",
    "保證會回來": "當成會回來的證明",
    "窗口": "時段",
    "Moon/Venus": "月亮與金星",
    "Moon 的": "月亮的",
    "Venus 的": "金星的",
    "月亮與金星在乎和需要被照顧的方式": "月亮與金星代表的安全感和被重視感",
    "需求語言": "在乎和需要被照顧的方式",
    "安全感語言": "需要安全感的方式",
    "被重視語言": "需要被重視的方式",
    "安全感與被重視的橋接": "安全感和被重視的感覺怎麼接上",
    "安全感與被重視的接得上的地方": "安全感和被重視的感覺怎麼接上",
    "把安全感和被重視的感覺怎麼接上說清楚": "說清楚你們在哪些地方能讓彼此安心、覺得被重視",
    "交叉橋接": "能互相接上的地方",
    "橋接": "接得上的地方",
    "有橋": "有能接上的地方",
    "讓這個橋變得可用": "讓這個連結真的用得上",
    "控速、降刺激": "先把動作收小、不要再加壓",
    "降速、降刺激": "把步調收小、不要再加壓",
    "降低刺激": "降低壓力",
    "降刺激": "不要再加壓",
    "控速": "把步調收小",
    "推進速度與衝突反應重複出現": "一靠近就容易變急或起衝突",
    "推進速度和衝突反應": "靠近時變急或起衝突的反應",
    "推進速度與衝突反應": "靠近時變急或起衝突的反應",
    "責任與長期承接入口": "能把責任放進日常互動的地方",
    "責任與長期承接位置": "能把責任放進日常互動的地方",
    "長期承接位置": "可以穩定負責的地方",
    "安全感和壓力層承接": "安全感和壓力狀態能不能穩住",
    "由安全感與壓力層判斷能否承接": "看安全感和壓力能不能穩住",
    "安全感與壓力層判斷能不能接住": "安全感和壓力能不能穩住",
    "壓力層是否能承接": "壓力能不能被處理",
    "壓力層判斷能否承接": "壓力能不能被處理",
    "壓力層承接": "壓力能不能被處理",
    "現實回應承接": "穩定的現實回應",
    "情緒承接位置": "情緒比較容易被接住的位置",
    "情緒承接": "情緒比較容易被接住",
    "可預期承接": "可預期回應",
    "成熟承接": "成熟回應",
    "可承接的熱度": "比較接得住的熱度",
    "承接更清楚的互動": "接住更清楚的互動",
    "主動承接": "主動接住",
    "被安全承接": "被安全地接住",
    "被承接": "被接住",
    "可承接": "比較接得住",
    "是否能承接": "能不能接住",
    "能否承接": "能不能接住",
    "能承接": "能接住",
    "穩定承接": "穩定接住",
    "需要翻譯": "需要說清楚",
    "先翻譯成": "先說成",
    "修復槓桿": "可以怎麼修",
    "行動尺度": "接下來適合做到哪一步",
    "開口門檻": "開口前先看什麼",
    "精準證據": "主要依據",
    "orb 約": "角度差約",
    "orb 未標示": "角度差未標示",
    "先降壓": "先讓壓力降下來",
    "降壓": "讓壓力降下來",
    "Saturn-in-sign": "土星落星座",
    "Saturn timing": "土星時機訊號",
    "Saturn pressure": "土星壓力",
    "降低 certainty": "降低確定語氣",
    "降 certainty": "改用保守語氣",
    "fatal verdict": "命定結論",
    "Hard contact": "緊張相位",
    "hard contact": "緊張相位",
    "Soft contact": "柔和相位",
    "soft contact": "柔和相位",
    "這裡應": "要",
    "Asc/Desc、宮位與 overlay": "上升、下降與宮位",
    "Asc/Desc": "上升、下降",
    "靠近的入口": "靠近的位置",
    "修復入口": "修復位置",
    "協調入口": "協調位置",
    "入口": "位置",
    "完整星盤證據鏈": "完整星盤依據",
    "證據鏈": "星盤依據",
    "壓力訊號": "緊繃感",
    "互動機制": "相處方式",
    "節奏校準": "步調調整",
    "關係容器": "相處空間",
    "行動邊界": "行動尺度",
    "需要慢一點": "需要把動作放小",
    "短、輕、可退場": "短、輕、能自然停下",
    "壓力比較小": "壓力較輕",
    "先放慢": "先把步調收小",
    "速度要先放慢": "動作要先收小",
    "把速度放慢": "把動作收小",
    "速度放慢": "動作收小",
    "放慢": "收小",
    "不要急著": "先不用",
    "不急著": "先不",
    "先先不用": "先不用",
    "先先不": "先不",
    "先觀察": "先看",
    "攤牌": "把關係題一次攤開",
    "另一條線索": "旁邊這個提醒",
    "行運土星觸發個人關係點時，不是直接代表沒有感覺，而是責任、距離和界線會讓回應變得比較保守。": "行運土星觸發個人關係點時，責任、距離和界線會讓回應變得比較保守；有在意也可能先退回安全距離。",
}


def western_public_copy(value: Any) -> str:
    text = str(value or "")
    for old, new in PUBLIC_COPY_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return text


def western_public_copy_list(values: Any) -> list[str]:
    return [western_public_copy(item) for item in values or [] if western_public_copy(item)]


def western_public_payload(value: Any, path: tuple[str, ...] = ()) -> Any:
    if isinstance(value, str):
        return western_public_copy(value)
    if isinstance(value, list):
        return [western_public_payload(item, (*path, str(index))) for index, item in enumerate(value)]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, child in value.items():
            child_path = (*path, str(key))
            if key == "sections" and path[-1:] == ("finalInterpretation",):
                # FinalNarrativeFactRenderer is the last visible-copy boundary.
                # Legacy public-copy replacements may still clean upstream
                # diagnostics, but must never rewrite its controlled output.
                output[key] = child
            else:
                output[key] = western_public_payload(child, child_path)
        return output
    return value


def exact_timing_policy(reason: str = "短期時機只能以趨勢、可用範圍與限制呈現，不作精準日期承諾。") -> dict[str, Any]:
    return {
        "precision": "trend_only",
        "preciseDatesAvailable": False,
        "reason": reason,
    }


GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS = [
    "western-aspects-saturn-pressure-001",
    "western-aspects-saturn-pressure-003",
]
GREENE_SATURN_PROCESS_METHOD_CLAIM_IDS = [
    "greene-saturn-defense-not-permanent-rejection",
]
HAND_FUNCTION_SPECIFIC_METHOD_CLAIM_IDS = [
    "hand-planet-pair-function-fields",
    "hand-moon-emotional-containment-belonging",
    "hand-mercury-communication-translation-map",
    "hand-venus-voluntary-attraction-harmony",
    "hand-mars-individuality-action-conflict",
    "hand-saturn-limits-reality-structure",
]
GEORGE_BLOCH_FUNCTION_ELEMENT_METHOD_CLAIM_IDS = [
    "george-bloch-function-elements-moon-through-saturn",
]
PAIR_FAMILY_METHOD_CLAIM_IDS = {
    "western-aspects-venus-mars": [
        "skymates-venus-mars-attraction-pursuit-polarity",
    ],
    "western-aspects-moon-venus": [
        "burk-moon-venus-safety-validation-alignment",
        "skymates-moon-venus-nurture-trust-bond",
    ],
    "western-aspects-sun-moon": [
        "skymates-sun-moon-core-rhythm-interaspect",
    ],
    "western-aspects-moon-saturn": [
        "burk-saturn-to-moon-venus-need-blocks",
        "skymates-moon-saturn-practical-emotional-translation",
    ],
    "western-aspects-venus-saturn": [
        "burk-saturn-to-moon-venus-need-blocks",
        "skymates-venus-saturn-commitment-and-blockage",
    ],
    "western-aspects-mars-saturn": [
        "skymates-mars-saturn-action-boundary-pressure",
    ],
}
PAIR_FAMILY_METHOD_CLAIM_IDS_ALL = [
    "burk-moon-venus-safety-validation-alignment",
    "burk-saturn-to-moon-venus-need-blocks",
    "skymates-sun-moon-core-rhythm-interaspect",
    "skymates-moon-venus-nurture-trust-bond",
    "skymates-moon-saturn-practical-emotional-translation",
    "skymates-venus-mars-attraction-pursuit-polarity",
    "skymates-venus-saturn-commitment-and-blockage",
    "skymates-mars-saturn-action-boundary-pressure",
]
FUNCTION_SIGN_METHOD_CLAIM_IDS = {
    "Moon": [
        "hand-moon-emotional-containment-belonging",
        "george-bloch-function-elements-moon-through-saturn",
    ],
    "Mercury": [
        "hand-mercury-communication-translation-map",
        "george-bloch-function-elements-moon-through-saturn",
    ],
    "Venus": [
        "hand-venus-voluntary-attraction-harmony",
        "george-bloch-function-elements-moon-through-saturn",
    ],
    "Mars": [
        "hand-mars-individuality-action-conflict",
        "george-bloch-function-elements-moon-through-saturn",
    ],
    "Saturn": [
        "hand-saturn-limits-reality-structure",
        "george-bloch-function-elements-moon-through-saturn",
    ],
}


def saturn_nonfatal_process_boundary(scope: str, evidence_keys: list[Any] | None = None) -> dict[str, Any]:
    return {
        "version": "saturn-nonfatal-process-boundary-v1",
        "scope": scope,
        "role": "pressure_process_not_fate",
        "source": "western-greene-saturn",
        "allowedUses": [
            "name_pressure",
            "slow_action",
            "describe_boundary",
            "frame_maturity_process",
        ],
        "cannotClaim": [
            "permanent_rejection",
            "doomed_relationship",
            "fated_waiting",
            "secret_love_proof",
            "punishment_or_karmic_sentence",
        ],
        "canCreatePermanentOutcome": False,
        "canProveInnerState": False,
        "requiresContextualEvidence": True,
        "sourceClaimIds": GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS,
        "methodClaimIds": GREENE_SATURN_PROCESS_METHOD_CLAIM_IDS,
        "evidenceKeys": unique([str(key) for key in evidence_keys or [] if key]),
    }


WESTERN_METHOD_TRACE_SECTIONS = [
    {
        "sectionId": "profile",
        "title": "星盤定位",
        "requiredRuntimeTargets": [
            "personProfile",
            "relationshipProfiles",
            "sunMoonAscProfile",
            "identityNeeds",
            "planetSignStyle",
            "planetaryFunctions",
            "moonSignEmotionalSafety",
            "mercurySignCommunicationRepair",
            "venusSignAffectionStyle",
            "marsSignPursuitConflict",
            "saturnSignDefenseDelay",
            "precisionWarnings",
        ],
        "requiredSourceIds": [
            "western-hand-horoscope-symbols",
            "western-george-bloch-astrology-for-yourself",
            "western-burk-relationship-handbook",
            "western-forrest-skymates",
        ],
        "methodClaimIds": [
            "hand-symbol-grammar-planet-function-sign-style",
            *HAND_FUNCTION_SPECIFIC_METHOD_CLAIM_IDS,
            "hand-symbol-grammar-house-angle-gate",
            "george-bloch-natal-synthesis-before-answer",
            *GEORGE_BLOCH_FUNCTION_ELEMENT_METHOD_CLAIM_IDS,
            "george-bloch-sun-moon-asc-profile-layer",
            "george-bloch-synthesis-salient-themes-first",
            "burk-moon-safety-survival-connection-boundaries",
            "skymates-individuals-before-interactions",
            "skymates-keep-planet-functions-distinct",
            "skymates-sun-sign-only-is-not-enough",
            "skymates-venus-mars-relating-styles-context-bound",
        ],
        "evidenceClusterKeys": [
            "birthDataQuality",
            "sunMoonAscProfile",
            "identityNeeds",
            "planetaryFunctions",
            "planetSignStyle",
            "moonSignEmotionalSafety",
            "mercurySignCommunicationRepair",
            "venusSignAffectionStyle",
            "marsSignPursuitConflict",
            "saturnSignDefenseDelay",
            "functionElementMatrix",
            "functionModalityMatrix",
            "angleHouseFramework",
        ],
    },
    {
        "sectionId": "fit",
        "title": "兩個人的關係契合度分析",
        "requiredRuntimeTargets": [
            "relationshipFit",
            "fitSummary",
            "relationshipArchetype",
            "attractionDynamics",
            "conflictDynamics",
            "growthDynamics",
            "safetyValidationLanguage",
            "attraction",
            "emotionalSafety",
            "communication",
            "pressure",
            "repair",
            "aspectPriority",
            "aspectFunctionCombination",
        ],
        "requiredSourceIds": [
            "western-hand-horoscope-symbols",
            "western-suskin-synastry",
            "western-george-bloch-astrology-for-yourself",
            "western-burk-relationship-handbook",
            "western-greene-saturn",
            "western-forrest-skymates",
        ],
        "methodClaimIds": [
            "suskin-method-order-natal-before-synastry",
            "suskin-method-order-comparison-is-orientation",
            "suskin-method-order-aspects-after-foundation",
            "george-bloch-relationship-comparison-wants-needs",
            "george-bloch-synthesis-salient-themes-first",
            "burk-relationship-astrology-people-before-charts",
            "burk-safety-validation-needs-before-compatibility",
            "burk-moon-safety-survival-connection-boundaries",
            "burk-synastry-as-persistent-trigger",
            "burk-personal-planet-connections-attraction-and-sparks",
            "burk-repeated-themes-outweigh-single-contacts",
            *PAIR_FAMILY_METHOD_CLAIM_IDS_ALL,
            "hand-symbol-grammar-aspect-synthesis",
            "george-bloch-aspect-synthesis-cross-check",
            "greene-saturn-defense-not-permanent-rejection",
            "skymates-no-generic-love-needs",
            "skymates-pivotal-interaspects-over-aspect-dump",
            "skymates-interaspect-selection-priority-procedure",
            "skymates-venus-mars-relating-styles-context-bound",
            "skymates-modern-nonfatal-synastry",
        ],
        "evidenceClusterKeys": [
            "relationshipPotential",
            "elementComparison",
            "safetyValidationLanguage",
            "nonfatalSynastrySafety",
            "luminaryComparison",
            "attraction",
            "emotionalSafety",
            "communication",
            "pressure",
            "repair",
            "aspectPriority",
            "aspectContactModifier",
            "aspectPairContactTemplate",
            "aspectFunctionCombination",
            "relationshipArchetype",
            "attractionDynamics",
            "conflictDynamics",
            "growthDynamics",
            "aspectSynthesisCrossCheck",
        ],
    },
    {
        "sectionId": "question",
        "title": "核心問題解讀",
        "requiredRuntimeTargets": [
            "answerEvidenceContract",
            "evidenceReducer",
            "contextModifier",
            "nonfatalSynastrySafety",
            "consultationSafety",
            "safetyValidationLanguage",
            "contactSituationPolicy",
            "partnerNeeds",
        ],
        "requiredSourceIds": [
            "western-burk-relationship-handbook",
            "western-forrest-skymates",
            "consulting-opa-ethics",
            "relationship-gottman-bids-repair",
        ],
        "methodClaimIds": [
            "burk-relationship-astrology-people-before-charts",
            "burk-safety-validation-needs-before-compatibility",
            "burk-outer-to-personal-pressure-needs-context",
            "burk-repeated-themes-outweigh-single-contacts",
            "skymates-no-generic-love-needs",
            "skymates-modern-nonfatal-synastry",
            "skymates-readable-language-for-dialogue",
            "opa-third-party-boundary",
            "valley-context-modifies-action-not-conclusion",
            "valley-context-boundary-trace-not-evidence",
            "valley-contact-status-action-scale",
            "gottman-contact-as-bid-not-proof",
            "valley-question-still-love-evidence-selector",
            "valley-question-any-chance-conditional-selector",
            "valley-question-when-to-contact-timing-selector",
            "valley-question-self-blame-interaction-cycle-selector",
            "valley-question-stay-let-go-boundary-selector",
        ],
        "evidenceClusterKeys": [
            "identityNeeds",
            "safetyValidationLanguage",
            "attraction",
            "emotionalSafety",
            "pressure",
            "communication",
            "repair",
            "nonfatalSynastrySafety",
            "consultationSafety",
            "relationshipStage",
            "contactStatus",
            "contactSituationPolicy",
            "partnerNeeds",
            "emotionalRisk",
            "desiredOutcome",
        ],
    },
    {
        "sectionId": "timing",
        "title": "時機判讀",
        "requiredRuntimeTargets": [
            "currentTransits",
            "timingWindowBand",
            "timingContactReducer",
            "timingMercuryCommunication",
            "timingVenusSoftening",
            "timingMarsActivation",
            "timingSaturnPressure",
            "timingMoonWeather",
            "contactSituationPolicy",
            "relationshipTurningWindows",
        ],
        "requiredSourceIds": [
            "western-hand-transits",
            "western-greene-saturn",
            "consulting-opa-ethics",
            "relationship-gottman-bids-repair",
        ],
        "methodClaimIds": [
            "hand-transits-timing-climate-not-guarantee",
            "hand-transits-mercury-communication-window",
            "hand-transits-venus-softening-window",
            "hand-transits-mars-activation-caution",
            "hand-transits-saturn-boundary-pressure",
            "hand-transits-moon-weather-secondary",
            "hand-transits-easy-difficult-neutrality",
            "hand-transits-inner-planet-reinforcement-timing",
            "greene-saturn-defense-not-permanent-rejection",
            "valley-contact-status-action-scale",
            "gottman-no-contact-low-stimulation-bid",
            "valley-shared-space-discretion-boundary",
        ],
        "evidenceClusterKeys": [
            "currentTransits",
            "timingWindowBand",
            "timingMercuryCommunication",
            "timingVenusSoftening",
            "timingMarsActivation",
            "timingSaturnPressure",
            "timingMoonWeather",
            "timingContactReducer",
            "relationshipTurningWindows",
            "contactSituationPolicy",
        ],
    },
    {
        "sectionId": "action",
        "title": "行動方向",
        "requiredRuntimeTargets": [
            "actionBoundary",
            "actionDirection",
            "donts",
            "contactStatus",
            "contactSituationPolicy",
            "nonfatalSynastrySafety",
            "timingContactReducer",
            "fightLandmines",
            "survivalGuide",
        ],
        "requiredSourceIds": [
            "consulting-opa-ethics",
            "relationship-gottman-bids-repair",
            "western-hand-transits",
            "western-forrest-skymates",
        ],
        "methodClaimIds": [
            "opa-client-agency-action-boundary",
            "valley-context-modifies-action-not-conclusion",
            "valley-context-boundary-trace-not-evidence",
            "valley-blocked-contact-hard-boundary",
            "valley-no-contact-lowers-action-speed",
            "valley-contact-status-action-scale",
            "gottman-contact-as-bid-not-proof",
            "gottman-repair-tone-before-content",
            "gottman-limited-reply-existing-channel-repair",
            "gottman-no-contact-low-stimulation-bid",
            "valley-shared-space-discretion-boundary",
            "hand-transits-timing-climate-not-guarantee",
            "hand-transits-mercury-communication-window",
            "hand-transits-venus-softening-window",
            "hand-transits-mars-activation-caution",
            "hand-transits-saturn-boundary-pressure",
            "hand-transits-easy-difficult-neutrality",
            "hand-transits-inner-planet-reinforcement-timing",
            "skymates-modern-nonfatal-synastry",
            "skymates-readable-language-for-dialogue",
            "skymates-venus-mars-relating-styles-context-bound",
        ],
        "evidenceClusterKeys": [
            "consultationSafety",
            "nonfatalSynastrySafety",
            "contactStatus",
            "contactSituationPolicy",
            "relationshipStage",
            "emotionalRisk",
            "desiredOutcome",
            "currentTransits",
            "timingWindowBand",
            "timingMercuryCommunication",
            "timingVenusSoftening",
            "timingMarsActivation",
            "timingSaturnPressure",
            "timingMoonWeather",
            "timingContactReducer",
            "fightLandmines",
            "survivalGuide",
        ],
    },
]


BRAND = {"title": "光之谷", "subtitle": "Valley of Light"}


STAGE_LABELS = {
    "cold-war": "冷戰 / 斷聯中",
    "broke-up-recent": "剛分手 / 情緒未穩",
    "broke-up-long": "分手已久 / 距離拉開",
    "crisis": "關係危機 / 還在拉扯",
    "ambiguous": "曖昧 / 尚未定義",
}


STAGE_TITLES = {
    "cold-war": "冷戰不是結束，而是情緒防衛",
    "broke-up-recent": "剛分手先看穩定，不急著定論",
    "broke-up-long": "距離拉長後，機會取決於重新靠近的方式",
    "crisis": "危機期要先看互動能不能變輕",
    "ambiguous": "曖昧期先看能否被穩定定義",
}


STAGE_BODIES = {
    "cold-war": "目前重點不是證明誰還愛誰，而是避免把對方推到只能繼續退開的位置。",
    "broke-up-recent": "剛分手時情緒還在震盪，太快追問會讓反應變得更防衛。",
    "broke-up-long": "分開久了仍有線索不代表可以直接追回，而是要用更輕、比較不逼迫的方式重新建立回應。",
    "crisis": "你們還在同一段關係裡拉扯，關鍵不是誰贏，而是互動是否還能恢復穩定。",
    "ambiguous": "曖昧期的重點不是直接套用分手或復合語言，而是看互動能不能穩定、清楚地被定義。",
}


QUESTION_TITLES = {
    "still-love-me": "他現在心裡還有我嗎？",
    "any-chance": "我們還有機會嗎？",
    "when-to-contact": "什麼時候適合聯絡？",
    "what-did-i-do-wrong": "是不是我做錯了什麼？",
    "stay-or-let-go": "我該繼續等，還是放下？",
}


QUESTION_SELECTOR_METHOD_CLAIM_IDS = {
    "still-love-me": ["valley-question-still-love-evidence-selector"],
    "any-chance": ["valley-question-any-chance-conditional-selector"],
    "when-to-contact": ["valley-question-when-to-contact-timing-selector"],
    "what-did-i-do-wrong": ["valley-question-self-blame-interaction-cycle-selector"],
    "stay-or-let-go": ["valley-question-stay-let-go-boundary-selector"],
}


QUESTION_SELECTOR_EVIDENCE_CLUSTER_KEYS = {
    "still-love-me": ["attraction", "emotionalSafety", "pressure", "contactSituationPolicy", "consultationSafety"],
    "any-chance": ["repair", "pressure", "attraction", "timingContactReducer", "contactSituationPolicy"],
    "when-to-contact": ["timingContactReducer", "timingWindowBand", "contactSituationPolicy", "pressure", "consultationSafety"],
    "what-did-i-do-wrong": ["communication", "pressure", "emotionalSafety", "emotionalRisk", "consultationSafety"],
    "stay-or-let-go": ["pressure", "repair", "emotionalSafety", "contactSituationPolicy", "consultationSafety"],
}


def question_selector_method_claim_ids(question_key: str) -> list[str]:
    return [str(item) for item in QUESTION_SELECTOR_METHOD_CLAIM_IDS.get(question_key, []) if item]


def question_selector_evidence_cluster_keys(question_key: str, selected_keys: list[str] | None = None) -> list[str]:
    return unique([
        *[str(item) for item in selected_keys or [] if item],
        *[str(item) for item in QUESTION_SELECTOR_EVIDENCE_CLUSTER_KEYS.get(question_key, []) if item],
    ])


def question_selector_trace(
    question_key: str,
    evidence_cluster_keys: list[str] | None = None,
    status_answer_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = status_answer_policy if isinstance(status_answer_policy, dict) else {}
    return {
        "version": "western-question-selector-v1",
        "questionKey": question_key,
        "methodClaimIds": question_selector_method_claim_ids(question_key),
        "evidenceClusterKeys": question_selector_evidence_cluster_keys(question_key, evidence_cluster_keys),
        "role": "evidence_weighting_policy",
        "statusPolicyVersion": policy.get("version"),
        "statusResolvedTracks": [str(item) for item in policy.get("resolvedTracks") or [] if item],
    }


CONTACT_STATUS_LABELS = {
    "no-contact": "完全沒有聯絡",
    "occasional-contact": "偶爾回覆",
    "still-in-contact": "還會聊天但很冷",
    "living-or-working-together": "有見面或共同場域",
    "blocked": "對方封鎖或消失",
}


CONTACT_STATUS_STATE_CLAIM_IDS = {
    "blocked": ["context-contact-status-004"],
    "no-contact": ["context-contact-status-005"],
    "occasional-contact": ["context-contact-status-006"],
    "still-in-contact": ["context-contact-status-007"],
    "living-or-working-together": ["context-contact-status-008"],
}

CONTACT_STATUS_STATE_CLAIM_ID_SET = {
    claim_id
    for claim_ids in CONTACT_STATUS_STATE_CLAIM_IDS.values()
    for claim_id in claim_ids
}


CONTACT_SITUATION_METHOD_CLAIM_IDS = {
    "blocked": ["valley-contact-status-action-scale", "valley-blocked-contact-hard-boundary"],
    "no-contact": [
        "valley-contact-status-action-scale",
        "valley-no-contact-lowers-action-speed",
        "gottman-no-contact-low-stimulation-bid",
    ],
    "occasional-contact": [
        "valley-contact-status-action-scale",
        "gottman-contact-as-bid-not-proof",
        "gottman-limited-reply-existing-channel-repair",
    ],
    "still-in-contact": [
        "valley-contact-status-action-scale",
        "gottman-repair-tone-before-content",
        "gottman-limited-reply-existing-channel-repair",
    ],
    "living-or-working-together": [
        "valley-contact-status-action-scale",
        "valley-shared-space-discretion-boundary",
    ],
    "unknown": [
        "valley-context-modifies-action-not-conclusion",
        "valley-context-boundary-trace-not-evidence",
    ],
}


CONTACT_SITUATION_POLICIES = {
    "blocked": {
        "contactAccess": "blocked",
        "actionScale": 0,
        "actionMode": "boundary_only",
        "boundaryStrength": 0.96,
        "canSuggestDirectContact": False,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": False,
        "requiresCalculationSupport": True,
        "timingCanOverrideBoundary": False,
        "allowedAction": "不突破封鎖，也不繞路施壓；只保留自我整理、必要現實安全邊界，等待對方自願打開通道。",
        "blockedActions": ["alternate_account_contact", "repeated_messages", "third_party_pressure", "emotional_confrontation"],
        "contactInstruction": "任何好相位或好時機都先讓位給聯絡邊界；先守住界線。",
    },
    "no-contact": {
        "contactAccess": "none",
        "actionScale": 1,
        "actionMode": "observe_or_single_low_stimulation_test",
        "boundaryStrength": 0.84,
        "canSuggestDirectContact": True,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": False,
        "requiresCalculationSupport": True,
        "timingCanOverrideBoundary": False,
        "allowedAction": "斷聯會把行動降到很低；只有在星盤修復線索與壓力較小的時機同時支持時，才可寫成一次短、輕、可退場的測試。",
        "blockedActions": ["repeated_messages", "long_explanation", "asking_for_answer_now", "emotional_confrontation"],
        "contactInstruction": "先觀察氣氛是否變輕；若要動，也只能是短、輕、可退場的一次測試。",
    },
    "occasional-contact": {
        "contactAccess": "limited",
        "actionScale": 2,
        "actionMode": "small_bid_response_led",
        "boundaryStrength": 0.66,
        "canSuggestDirectContact": True,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": False,
        "requiresCalculationSupport": True,
        "timingCanOverrideBoundary": False,
        "allowedAction": "偶爾回覆代表有很小的現實窗口，但行動要跟著對方回應走；適合短句、輕量、可停下的互動。",
        "blockedActions": ["turning_reply_into_commitment", "rapid_escalation", "relationship_definition_push"],
        "contactInstruction": "把回覆當互動訊號，不當承諾；回應越少，越要短、輕、慢。",
    },
    "still-in-contact": {
        "contactAccess": "live_cold",
        "actionScale": 3,
        "actionMode": "tone_repair_in_existing_channel",
        "boundaryStrength": 0.58,
        "canSuggestDirectContact": True,
        "requiresEasyExit": False,
        "requiresSharedSpaceBoundary": False,
        "requiresCalculationSupport": True,
        "timingCanOverrideBoundary": False,
        "allowedAction": "仍有聊天時，可以在原本通道裡放輕語氣、修復語氣；重點是讓對話變輕，不是要求立刻定義關係。",
        "blockedActions": ["forcing_relationship_definition", "long_pressure_message", "testing_loyalty"],
        "contactInstruction": "用既有通道微調語氣與節奏；先看對方能不能自然接住。",
    },
    "living-or-working-together": {
        "contactAccess": "shared_space",
        "actionScale": 2,
        "actionMode": "shared_space_boundary",
        "boundaryStrength": 0.72,
        "canSuggestDirectContact": True,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": True,
        "requiresCalculationSupport": True,
        "timingCanOverrideBoundary": False,
        "allowedAction": "有共同生活或工作場域時，行動要先保護場合與界線；適合保持自然、普通、低刺激的互動，不適合把共同場域變成攤牌現場。",
        "blockedActions": ["public_confrontation", "using_shared_space_as_pressure", "relationship_definition_push"],
        "contactInstruction": "把共同場域當邊界，先維持普通、自然、可退場。",
    },
    "unknown": {
        "contactAccess": "unknown",
        "actionScale": 1,
        "actionMode": "context_missing_conservative",
        "boundaryStrength": 0.46,
        "canSuggestDirectContact": False,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": False,
        "requiresCalculationSupport": True,
        "timingCanOverrideBoundary": False,
        "allowedAction": "聯絡情境不清楚時，行動建議要保守；不能把 timing 直接寫成應該主動聯絡。",
        "blockedActions": ["precise_contact_instruction", "guaranteed_response", "pressure_without_context"],
        "contactInstruction": "先補足現實聯絡情境，再判斷接下來適合做到哪一步。",
    },
}


RELATIONSHIP_CONTEXT_STORYLINE_VERSION = "relationship-context-storyline-v1"
RELATIONSHIP_CONTEXT_STORYLINE_KEY = "relationshipContextStoryline"
RELATIONSHIP_CONTEXT_SECTION_IDS = (
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
)

CONTEXT_STORY_STAGE_FRAMES: dict[str, dict[str, str]] = {
    "cold-war": {
        "short": "冷戰裡先看沉默會不會變軟",
        "premise": "你們現在不是單純沒感覺，而是話一重就容易退回沉默。",
        "focus": "沉默後能不能回到比較普通的說話方式",
        "proof": "不用誰先低頭，也能出現一點自然的小互動",
        "avoid": "不要把冷著不說直接當成結局",
        "chart": "冷戰裡各自怎麼保護自己",
        "fit": "沉默能不能慢慢變回可以說話",
        "timing": "現在能不能讓氣氛先軟一點",
    },
    "broke-up-recent": {
        "short": "剛分開先讓情緒降下來",
        "premise": "剛分開時每個回應都容易被放大，太快追答案會讓彼此更累。",
        "focus": "情緒退一點後，對方是否還願意自然接話",
        "proof": "不是被逼出來的回應，而是情緒淡一點後仍有下一次互動",
        "avoid": "不要用分手後第一波情緒替整段關係定論",
        "chart": "剛分開時誰需要安定、誰會先收起來",
        "fit": "分開初期能不能停掉舊的拉扯方式",
        "timing": "先等情緒不要那麼滿",
    },
    "broke-up-long": {
        "short": "分開久了要看新的靠近方式",
        "premise": "時間拉長後，重點不再是回到以前，而是有沒有新的互動方法。",
        "focus": "舊關係外面，還能不能長出新的自然聯絡",
        "proof": "對方不是只回憶過去，而是願意在現在多走一小步",
        "avoid": "不要把回憶或懷念直接當成復合條件",
        "chart": "分開久了還會牽動彼此的地方",
        "fit": "舊模式能不能換成新的靠近方法",
        "timing": "現在只看能不能自然重開一點點",
    },
    "crisis": {
        "short": "還在一起先把傷害降下來",
        "premise": "你們還在關係裡，但現在不適合把所有問題一次攤開。",
        "focus": "同一段關係裡，互動能不能先停止變傷人",
        "proof": "衝突出現時，有人願意把話放輕，而不是繼續撐輸贏",
        "avoid": "不要把一次爭執當成最後答案",
        "chart": "危機裡誰會急、誰會縮回去",
        "fit": "還在一起時能不能把傷害降下來",
        "timing": "先避開會讓關係更緊的時候",
    },
    "ambiguous": {
        "short": "曖昧先看能不能慢慢變清楚",
        "premise": "曖昧期不能直接套分手或復合語言，重點是對方有沒有把互動變穩。",
        "focus": "不急著定義時，對方會不會自然把關係往清楚一點帶",
        "proof": "不是只有一時熱絡，而是他也會主動延續話題或安排下一次",
        "avoid": "不要把火花直接翻成關係承諾",
        "chart": "曖昧裡誰靠近、誰保留",
        "fit": "火花能不能慢慢變成穩定互動",
        "timing": "現在先不要急著逼關係名稱",
    },
}

CONTEXT_STORY_QUESTION_FRAMES: dict[str, dict[str, str]] = {
    "still-love-me": {
        "short": "看在意有沒有放進行動",
        "premise": "這題不只猜他心裡，重點是他有沒有把在意放進實際反應。",
        "focus": "他有沒有在沒被追問時也自然接住你",
        "proof": "他會不會自己延續、自己靠近一點，而不是只被動回一句",
        "avoid": "不要用一句回覆判定他愛或不愛",
        "headline": "他還有沒有把在意放進行動",
        "action": "先看他會不會自己接下一步",
    },
    "any-chance": {
        "short": "看舊循環有沒有變小",
        "premise": "機會不是回到以前，而是你們能不能用新的方式相處。",
        "focus": "同樣問題出現時，舊的拉扯有沒有少一點",
        "proof": "你們不再只靠追問、退開或翻舊帳維持互動",
        "avoid": "不要把一時熱絡直接當成機會已經打開",
        "headline": "機會要看舊循環有沒有鬆開",
        "action": "先做一件不會把舊問題推回來的事",
    },
    "when-to-contact": {
        "short": "看現在能不能承受一句輕的話",
        "premise": "這題不是找必勝時間，而是判斷現在能不能承受一個小動作。",
        "focus": "現在最多能說到多輕、多短、多不需要對方立刻回答",
        "proof": "一句普通的話能被接住，而不是立刻讓氣氛變緊",
        "avoid": "不要把時機解讀成一定要主動聯絡",
        "headline": "現在先看能不能輕輕靠近",
        "action": "只留一句短而清楚的話",
    },
    "what-did-i-do-wrong": {
        "short": "把自責拆回一段互動",
        "premise": "這題先保護你不要把整段關係都怪到自己身上。",
        "focus": "哪一段互動可以調整，而不是誰應該承擔全部責任",
        "proof": "你能改一個說法或步調，對方也要有比較清楚的回應",
        "avoid": "不要用自責逼自己補救全部問題",
        "headline": "先分清楚責任和自責",
        "action": "只修一個你真的能調整的地方",
    },
    "stay-or-let-go": {
        "short": "分清楚值得等和只是消耗",
        "premise": "這題不是逼你立刻放下，而是看等待有沒有現實支撐。",
        "focus": "這段互動是讓你慢慢更穩，還是讓你一直更累",
        "proof": "對方有連續、尊重界線的行動，而不是只在你撐不住時短暫出現",
        "avoid": "不要把捨不得誤認成值得繼續等",
        "headline": "要不要等，看你有沒有變穩",
        "action": "先把自己的步調拿回來",
    },
}

CONTEXT_STORY_CONTACT_FRAMES: dict[str, dict[str, str]] = {
    "blocked": {
        "short": "通道關上時先守界線",
        "premise": "對方已經把聯絡關上時，任何牽動都不能變成繞路靠近。",
        "focus": "先尊重界線，等對方自己把通道打開",
        "proof": "只有對方自願恢復正常聯絡，這段關係才有新的互動資料",
        "avoid": "不要換方式、換帳號或找人傳話",
        "headline": "先不要突破界線",
        "action": "下一步先停在不打擾",
        "timing": "時機不能越過已經關上的通道",
    },
    "no-contact": {
        "short": "沒有聯絡時先留空間",
        "premise": "目前沒有自然對話時，主動加碼越多，越容易讓沉默變得更硬。",
        "focus": "對方會不會自己露出一點可以接話的空間",
        "proof": "不是你連續推進，而是他也自然回到一點互動裡",
        "avoid": "不要用第二段、第三段訊息補空白",
        "headline": "沒有聯絡時先看空間",
        "action": "最多只保留一次很輕的開口",
        "timing": "沒有自然對話時，時機也要很保守",
    },
    "occasional-contact": {
        "short": "偶爾回覆先看能不能延續",
        "premise": "偶爾回覆代表還有一點互動，但還不能直接當成穩定靠近。",
        "focus": "回覆後有沒有下一次自然延續",
        "proof": "他不是只接住你丟出的題目，而是也願意把話多往前帶一點",
        "avoid": "不要把一次回覆立刻推成承諾",
        "headline": "偶爾回覆先看後面有沒有接上",
        "action": "回得少，你也說少一點",
        "timing": "有回覆時也先看後面接不接得上",
    },
    "still-in-contact": {
        "short": "還能聊天時看自然延續",
        "premise": "你們還能說話，所以重點不是開新局，而是在原本對話裡把壓力放輕。",
        "focus": "他會不會在原本對話裡也主動多接一點",
        "proof": "對話不是只靠你維持，而是他也會自然接下去",
        "avoid": "不要把聊天變成關係審問",
        "headline": "還能聊天，就看他會不會也接話",
        "action": "在原本對話裡放輕就好",
        "timing": "還能聊天時，先看話題能承受多重",
    },
    "living-or-working-together": {
        "short": "共同場域先保護自然感",
        "premise": "你們還會見面或共處，所以任何行動都要先保護日常場合。",
        "focus": "相遇時能不能維持普通、自然和有退路",
        "proof": "共同場域沒有被感情問題弄得更尷尬，互動仍能保持基本自然",
        "avoid": "不要把共同場域變成逼答案的地方",
        "headline": "有共同場域，先保護日常相處",
        "action": "保持普通、自然、可停下",
        "timing": "見得到面時，更要避免讓場合變重",
    },
}


EMOTIONAL_RISK_LABELS = {
    "calm": "相對冷靜",
    "anxious": "焦慮想確認",
    "self-blaming": "容易自責",
    "desperate": "很急、很痛、很想立刻有答案",
    "unsafe-or-overwhelmed": "安全感高度失衡",
    "not-collected": "尚未收集",
}


DESIRED_OUTCOME_LABELS = {
    "reconnect": "想重新靠近",
    "decide": "想決定去留",
    "understand": "想理解原因",
    "release": "想慢慢放下",
    "stabilize": "想先穩住自己",
}


SIGNAL_TITLES = {
    "western-aspects-sun-mars": "Sun-Mars 強互動",
    "western-aspects-venus-mars": "Venus-Mars 吸引",
    "western-aspects-sun-venus": "Sun-Venus 欣賞好感",
    "western-aspects-moon-moon": "Moon-Moon 情緒節奏",
    "western-aspects-moon-mars": "Moon-Mars 情緒點火",
    "western-aspects-venus-venus": "Venus-Venus 喜歡語言",
    "western-aspects-mars-mars": "Mars-Mars 行動節奏",
    "western-aspects-mercury-sun": "Mercury-Sun 理解與自尊",
    "western-aspects-mercury-jupiter": "Mercury-Jupiter 開闊對話",
    "western-aspects-mars-saturn": "火星-土星壓力",
    "western-aspects-moon-saturn": "月亮-土星防衛",
    "western-aspects-moon-venus": "Moon-Venus 情緒好感",
    "western-aspects-venus-saturn": "金星-土星慢熱防衛",
    "western-aspects-sun-moon": "Sun-Moon 情緒連結",
    "western-aspects-saturn-pressure": "土星壓力中高",
    "western-aspects-mercury-contacts": "Mercury 溝通相位",
    "western-aspects-outer-planet-intensity-families": "外行星強度相位",
}


WESTERN_CHIP_LABELS = {
    "western-aspects-sun-mars": "Sun-Mars",
    "western-aspects-venus-mars": "Venus-Mars",
    "western-aspects-sun-venus": "Sun-Venus",
    "western-aspects-moon-moon": "Moon-Moon",
    "western-aspects-moon-mars": "Moon-Mars",
    "western-aspects-venus-venus": "Venus-Venus",
    "western-aspects-mars-mars": "Mars-Mars",
    "western-aspects-mercury-sun": "Mercury-Sun",
    "western-aspects-mercury-jupiter": "Mercury-Jupiter",
    "western-aspects-mars-saturn": "火星-土星",
    "western-aspects-moon-saturn": "月亮-土星",
    "western-aspects-moon-venus": "Moon-Venus",
    "western-aspects-venus-saturn": "金星-土星",
    "western-aspects-sun-saturn": "太陽-土星",
    "western-aspects-sun-moon": "Sun-Moon",
    "western-aspects-saturn-pressure": "土星壓力",
    "western-aspects-mercury-contacts": "Mercury contacts",
    "western-aspects-outer-planet-intensity-families": "Outer planet intensity",
}


POINT_LABELS = {
    "Sun": "太陽",
    "Moon": "月亮",
    "Mercury": "水星",
    "Venus": "金星",
    "Mars": "火星",
    "Jupiter": "木星",
    "Saturn": "土星",
    "Uranus": "天王星",
    "Neptune": "海王星",
    "Pluto": "冥王星",
    "Asc": "上升",
    "Desc": "下降",
}


POINT_TRAITS = {
    "Sun": "自我 · 希望被看見",
    "Moon": "敏感 · 需要安全感",
    "Mercury": "溝通 · 需要被理解",
    "Venus": "喜歡 · 需要被珍惜",
    "Mars": "行動 · 想推進",
    "Jupiter": "擴張 · 容易放大期待",
    "Saturn": "壓力 · 變慢變保守",
    "Uranus": "自由 · 容易忽冷忽熱",
    "Neptune": "理想化 · 需要界線",
    "Pluto": "強度 · 權力與投射",
    "Asc": "外在反應 · 第一印象",
    "Desc": "關係投射 · 期待對方",
}


ASPECT_LABELS = {
    "Conjunction": "合相",
    "Sextile": "六合",
    "Square": "四分相",
    "Trine": "三分相",
    "Opposition": "對分相",
    "Quincunx": "梅花相",
}


SIGN_LABELS = {
    "Aries": "白羊",
    "Taurus": "金牛",
    "Gemini": "雙子",
    "Cancer": "巨蟹",
    "Leo": "獅子",
    "Virgo": "處女",
    "Libra": "天秤",
    "Scorpio": "天蠍",
    "Sagittarius": "射手",
    "Capricorn": "摩羯",
    "Aquarius": "水瓶",
    "Pisces": "雙魚",
}


WESTERN_ELEMENT_LABELS = {
    "Fire": "火象",
    "Earth": "土象",
    "Air": "風象",
    "Water": "水象",
}


WESTERN_MODALITY_LABELS = {
    "Cardinal": "開創",
    "Fixed": "固定",
    "Mutable": "變動",
}


SIGN_ELEMENTS = {
    "Aries": "Fire",
    "Taurus": "Earth",
    "Gemini": "Air",
    "Cancer": "Water",
    "Leo": "Fire",
    "Virgo": "Earth",
    "Libra": "Air",
    "Scorpio": "Water",
    "Sagittarius": "Fire",
    "Capricorn": "Earth",
    "Aquarius": "Air",
    "Pisces": "Water",
}


SIGN_MODALITIES = {
    "Aries": "Cardinal",
    "Taurus": "Fixed",
    "Gemini": "Mutable",
    "Cancer": "Cardinal",
    "Leo": "Fixed",
    "Virgo": "Mutable",
    "Libra": "Cardinal",
    "Scorpio": "Fixed",
    "Sagittarius": "Mutable",
    "Capricorn": "Cardinal",
    "Aquarius": "Fixed",
    "Pisces": "Mutable",
}


ELEMENT_CLAIM_IDS = {
    "Fire": "western-function-element-templates-002",
    "Air": "western-function-element-templates-003",
    "Earth": "western-function-element-templates-004",
    "Water": "western-function-element-templates-005",
}


MODALITY_CLAIM_IDS = {
    "Cardinal": "western-function-modality-templates-002",
    "Fixed": "western-function-modality-templates-003",
    "Mutable": "western-function-modality-templates-004",
}


SIGN_CLAIM_IDS = {
    "Aries": "western-individual-sign-meanings-hand-001",
    "Taurus": "western-individual-sign-meanings-hand-002",
    "Gemini": "western-individual-sign-meanings-hand-003",
    "Cancer": "western-individual-sign-meanings-hand-004",
    "Leo": "western-individual-sign-meanings-hand-005",
    "Virgo": "western-individual-sign-meanings-hand-006",
    "Libra": "western-individual-sign-meanings-hand-007",
    "Scorpio": "western-individual-sign-meanings-hand-008",
    "Sagittarius": "western-individual-sign-meanings-hand-009",
    "Capricorn": "western-individual-sign-meanings-hand-010",
    "Aquarius": "western-individual-sign-meanings-hand-011",
    "Pisces": "western-individual-sign-meanings-hand-012",
}


SIGN_RUNTIME_STYLES = {
    "Aries": "開端、快速推進與直接自我表達",
    "Taurus": "穩定、持續、感官與現實回應",
    "Gemini": "速度、好奇、對話與心理連結",
    "Cancer": "情緒安全、滋養、歸屬與保護",
    "Leo": "自我表達、被看見、認可與真實感",
    "Virgo": "精準、分析、效能、秩序與服務",
    "Libra": "一對一對話、互相定義、平衡與美感",
    "Scorpio": "轉化、強烈情感、深度與非表層經驗",
    "Sagittarius": "自由、原則、探索、社會意義與大圖像",
    "Capricorn": "現實效能、責任、界線、權威與長期建構",
    "Aquarius": "群體、友情、社會理想、距離感與集體視角",
    "Pisces": "同理、想像、敏感、接收與自我超越",
}


FUNCTION_ELEMENT_STYLES = {
    "Moon": {
        "Fire": "情緒安全需要直接熱度、快速確認與明確反應",
        "Earth": "情緒安全需要穩定節奏、可預期行動與生活裡的穩定回應",
        "Air": "情緒安全需要能說開、交換資訊與保留心理空間",
        "Water": "情緒安全需要同理接住、情緒歸屬與柔軟回應",
    },
    "Mercury": {
        "Fire": "溝通傾向直說重點，修復時需要快速清楚而不繞圈",
        "Earth": "溝通傾向具體可落地，修復時需要步驟和可驗證承諾",
        "Air": "溝通傾向討論、提問與換位理解，修復靠對話流動",
        "Water": "溝通先接收語氣和感受，修復需要情緒被承認",
    },
    "Venus": {
        "Fire": "喜歡方式偏直接熱烈，吸引需要明亮互動與追逐感",
        "Earth": "喜歡方式偏穩定陪伴，吸引透過實際照顧慢慢建立",
        "Air": "喜歡方式偏聊天、好奇與輕盈交換，吸引需要心理連結",
        "Water": "喜歡方式偏情感靠近、照顧與被感受理解",
    },
    "Mars": {
        "Fire": "靠近和衝突反應偏直接快速，容易先行動再調整",
        "Earth": "靠近和衝突反應偏慢而持續，會回到現實可行性",
        "Air": "靠近和衝突反應偏語言、策略與辯論，需要心理空間",
        "Water": "靠近和衝突反應帶情緒記憶，受威脅時先保護或後退",
    },
    "Saturn": {
        "Fire": "防衛來自主動性受阻或怕衝動失控，延遲常卡在出手",
        "Earth": "防衛來自穩定、責任與資源壓力，改變需要實際安全感",
        "Air": "防衛來自溝通失衡或失去客觀距離，容易理性化延遲",
        "Water": "防衛來自情緒暴露、界線模糊或被感受淹沒",
    },
}


FUNCTION_MODALITY_STYLES = {
    "Moon": {
        "Cardinal": "情緒反應會先啟動，需要主動確認安全感",
        "Fixed": "情緒反應會維持較久，需要時間建立信任再鬆動",
        "Mutable": "情緒反應會隨情境調整，需要能轉換語氣和空間",
    },
    "Mercury": {
        "Cardinal": "溝通節奏偏先開口、先定義、先推動問題",
        "Fixed": "溝通節奏偏維持立場，需要足夠證據才改變說法",
        "Mutable": "溝通節奏偏調整、轉換角度與連接不同資訊",
    },
    "Venus": {
        "Cardinal": "喜歡表達偏主動啟動，需要關係有回應方向",
        "Fixed": "喜歡表達偏穩定持續，升溫慢但不容易快速切換",
        "Mutable": "喜歡表達偏彈性互動，需要新鮮感與可調整距離",
    },
    "Mars": {
        "Cardinal": "推進或衝突偏先動作，壓力來時容易先出手",
        "Fixed": "推進或衝突偏持續用力，卡住時容易僵持",
        "Mutable": "推進或衝突偏轉向與試探，容易在多種反應間切換",
    },
    "Saturn": {
        "Cardinal": "防衛偏先設界線或先控制局面，怕失去主導權",
        "Fixed": "防衛偏維持原狀與慢慢鬆動，壓力下不易快速改變",
        "Mutable": "防衛偏迴避、分散或調整規則，需要更清楚的邊界",
    },
}


FUNCTION_SIGN_CLUSTER_CONFIG = {
    "Moon": {
        "category": "moonSignEmotionalSafety",
        "default_label": "月亮落星座安全感語氣",
        "dominant_contact_type": "emotional_safety_style",
        "evidence_id": "hand-moon-sign-emotional-safety",
        "interpretation": "Moon-in-sign 只說情緒安全與調節方式；出生時間未知時必須低信心處理。",
        "does_not_prove": "月亮星座用來看情緒安全與調節方式，下一步仍要看實際互動是否穩定。",
    },
    "Mercury": {
        "category": "mercurySignCommunicationRepair",
        "default_label": "水星落星座溝通與修復語氣",
        "dominant_contact_type": "communication_repair_style",
        "evidence_id": "hand-mercury-sign-communication-repair",
        "interpretation": "Mercury-in-sign 說明思考、訊息接收、語氣選擇與修復對話風格；它應用來拆溝通循環與訊息節奏。",
        "does_not_prove": "水星星座不能單獨證明對方會聯絡、應該說哪一句話、是否有感情或關係會復合。",
    },
    "Venus": {
        "category": "venusSignAffectionStyle",
        "default_label": "金星落星座喜歡方式",
        "dominant_contact_type": "affection_style",
        "evidence_id": "hand-venus-sign-affection-style",
        "interpretation": "Venus-in-sign 說明喜歡、吸引與被珍惜的語氣；它只能描述 affection style，不能升級成承諾。",
        "does_not_prove": "金星星座不能單獨證明對方愛你、願意承諾、會主動聯絡或會復合。",
    },
    "Mars": {
        "category": "marsSignPursuitConflict",
        "default_label": "火星落星座推進與衝突節奏",
        "dominant_contact_type": "pursuit_conflict_style",
        "evidence_id": "hand-mars-sign-pursuit-conflict",
        "interpretation": "Mars-in-sign 說明靠近、推進、自主與衝突反應節奏；它應用來拆互動循環，不用來指責任何一方。",
        "does_not_prove": "火星星座不能單獨證明誰錯、誰攻擊、是否有性吸引或關係會不會復合。",
    },
    "Saturn": {
        "category": "saturnSignDefenseDelay",
        "default_label": "土星落星座防衛與延遲模式",
        "dominant_contact_type": "defense_delay_style",
        "evidence_id": "hand-saturn-sign-defense-delay",
        "interpretation": "土星落星座說明界線、害怕、責任與延遲如何呈現；它是壓力語法，不是拒絕或命運判決。",
        "does_not_prove": "土星星座不能單獨證明對方不愛、永遠不會回來、或你必須無限等待。",
    },
}


WESTERN_ELEMENT_NATURAL_PAIRS = {
    frozenset(("Fire", "Air")),
    frozenset(("Earth", "Water")),
}


WESTERN_ELEMENT_FRICTION_PAIRS = {
    frozenset(("Fire", "Water")),
    frozenset(("Earth", "Air")),
}


WESTERN_NEED_POINTS = {
    "Moon": "情緒安全感",
    "Mercury": "溝通與被理解的方式",
    "Venus": "喜歡與被珍惜的方式",
    "Mars": "推進與慾望反應",
    "Saturn": "防衛、責任與延遲",
    "Desc": "關係投射與伴侶期待",
}


PERSON_LABELS = {
    "person_a": "你",
    "person_b": "對方",
}


ATTRACTION_SIGNAL_IDS = {
    "western-aspects-sun-mars",
    "western-aspects-venus-mars",
    "western-aspects-sun-venus",
    "western-aspects-moon-mars",
    "western-aspects-venus-venus",
    "western-aspects-mars-mars",
    "western-aspects-moon-venus",
    "western-aspects-sun-moon",
}


EMOTIONAL_SAFETY_SIGNAL_IDS = {
    "western-aspects-moon-moon",
    "western-aspects-moon-mars",
    "western-aspects-moon-saturn",
    "western-aspects-moon-venus",
    "western-aspects-venus-saturn",
    "western-aspects-sun-moon",
}


WESTERN_ASPECT_ARTICLE_BY_PAIR = {
    frozenset(("Sun", "Mars")): "western-aspects-sun-mars",
    frozenset(("Venus", "Mars")): "western-aspects-venus-mars",
    frozenset(("Sun", "Venus")): "western-aspects-sun-venus",
    frozenset(("Moon", "Moon")): "western-aspects-moon-moon",
    frozenset(("Moon", "Mars")): "western-aspects-moon-mars",
    frozenset(("Venus", "Venus")): "western-aspects-venus-venus",
    frozenset(("Mars", "Mars")): "western-aspects-mars-mars",
    frozenset(("Mercury", "Sun")): "western-aspects-mercury-sun",
    frozenset(("Mercury", "Jupiter")): "western-aspects-mercury-jupiter",
    frozenset(("Mars", "Saturn")): "western-aspects-mars-saturn",
    frozenset(("Moon", "Saturn")): "western-aspects-moon-saturn",
    frozenset(("Moon", "Venus")): "western-aspects-moon-venus",
    frozenset(("Venus", "Saturn")): "western-aspects-venus-saturn",
    frozenset(("Sun", "Saturn")): "western-aspects-sun-saturn",
    frozenset(("Sun", "Moon")): "western-aspects-sun-moon",
    frozenset(("Mercury", "Mercury")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Moon")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Venus")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Mars")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Saturn")): "western-aspects-mercury-contacts",
}


ASPECT_FUNCTION_COMBINATION_CONFIG = {
    "western-aspects-sun-mars": {
        "pairKey": "Sun-Mars",
        "label": "Sun-Mars 自我與行動點火",
        "sourceClaimId": "western-aspects-sun-mars-001",
        "relationshipFunction": "self_activation_pursuit",
        "soft": "自我感和行動力較容易互相帶動；有火花，但仍不能把主動性寫成承諾。",
        "hard": "自我感和行動衝動容易互相刺激；修復時要避開挑釁、試探和速度太快。",
        "conjunction": "自我感與行動衝動直接疊合，火花明顯，也容易一靠近就變急。",
        "instruction": "先讀 Sun 的自我感，再讀 Mars 的推進節奏；hard contact 優先降低刺激和對抗。",
    },
    "western-aspects-venus-mars": {
        "pairKey": "Venus-Mars",
        "label": "Venus-Mars 吸引與追逐",
        "sourceClaimId": "western-aspects-venus-mars-001",
        "relationshipFunction": "attraction_desire_pursuit",
        "soft": "吸引和靠近節奏較自然流動；可寫成化學反應入口，但不是復合保證。",
        "hard": "吸引與追逐感同時升高，容易推太快、誤讀或把火花當成關係安全。",
        "conjunction": "喜歡方式和慾望反應直接疊合，吸引強，但仍要看壓力能不能下降、修復條件能不能成立。",
        "instruction": "先讀 Venus 的喜歡方式，再讀 Mars 的慾望與推進；不可把 chemistry 寫成 commitment。",
    },
    "western-aspects-moon-venus": {
        "pairKey": "Moon-Venus",
        "label": "Moon-Venus 情緒好感",
        "sourceClaimId": "western-aspects-moon-venus-001",
        "relationshipFunction": "emotional_affection_validation",
        "soft": "情緒安撫和好感較容易被接收到；可作低壓修復入口之一。",
        "hard": "安全感和被珍惜語言容易錯位；不能把需求落差寫成不愛或單方責任。",
        "conjunction": "安全感與被喜歡、被珍惜的需求直接相連，柔軟感強，但不能替代現實回應。",
        "instruction": "先讀 Moon 的安全感，再讀 Venus 的喜歡與 validation；soft 給柔軟入口，hard 標記需求錯位。",
    },
    "western-aspects-sun-moon": {
        "pairKey": "Sun-Moon",
        "label": "Sun-Moon 核心情緒連結",
        "sourceClaimId": "western-aspects-sun-moon-001",
        "relationshipFunction": "core_identity_emotional_rhythm",
        "soft": "自我表達與情緒反應較容易互相看見；深層熟悉感比較容易被接住。",
        "hard": "自我方向和情緒本能容易互相刺激；深刻牽動也可能帶來敏感摩擦。",
        "conjunction": "生命感和情緒本能直接互相觸動，熟悉感強，但不是命定保證。",
        "instruction": "先讀 Sun 的生命方向，再讀 Moon 的情緒本能；不可把深刻觸動寫成必然復合。",
    },
    "western-aspects-sun-venus": {
        "pairKey": "Sun-Venus",
        "label": "Sun-Venus 欣賞與被喜歡",
        "sourceClaimId": "western-aspects-sun-venus-001",
        "relationshipFunction": "affection_appreciation_validation",
        "soft": "欣賞和好感較容易自然流動；可作低壓靠近入口，但不能直接升級成承諾。",
        "hard": "好感仍可能存在，但容易混入自尊、期待落差、支配感或停滯感。",
        "conjunction": "欣賞、好感與被看見需求直接疊合；柔性吸引明顯，但仍要看修復條件能不能成立。",
        "instruction": "先讀 Sun 的被看見需求，再讀 Venus 的喜歡方式；不可把 affection 寫成 commitment。",
    },
    "western-aspects-moon-mars": {
        "pairKey": "Moon-Mars",
        "label": "Moon-Mars 情緒與行動點火",
        "sourceClaimId": "western-aspects-moon-mars-001",
        "relationshipFunction": "emotional_activation_trigger",
        "soft": "情緒和行動較容易互相帶動；有反應，但仍不是關係安全保證。",
        "hard": "情緒按鈕和行動衝動容易互相刺激；吸引與刺激可能同時升高。",
        "conjunction": "情緒、本能與行動衝動直接點火；反應強，也需要控速。",
        "instruction": "先讀 Moon 的情緒安全，再讀 Mars 的行動衝動；hard contact 優先降速、降刺激。",
    },
    "western-aspects-venus-venus": {
        "pairKey": "Venus-Venus",
        "label": "Venus-Venus 喜歡語言",
        "sourceClaimId": "western-aspects-venus-venus-001",
        "relationshipFunction": "affection_style_compatibility",
        "soft": "喜歡語言和相處舒服感較容易同頻；可作低壓互動入口。",
        "hard": "喜歡語言有牽動也有落差，容易用舒服感迴避真正問題。",
        "conjunction": "喜歡語言、愉悅方式與 validation 需求直接疊合；舒服感明顯，但不等於修復能力。",
        "instruction": "先讀雙方 Venus 的喜歡語言；舒服感只能作入口，不能替代壓力和修復層判斷。",
    },
    "western-aspects-moon-moon": {
        "pairKey": "Moon-Moon",
        "label": "Moon-Moon 情緒節奏",
        "sourceClaimId": "western-aspects-moon-moon-001",
        "relationshipFunction": "emotional_rhythm_safety",
        "soft": "情緒節奏較容易互相理解，是安全感入口，但仍需看現實互動。",
        "hard": "本能安全感節奏容易不同步，親近時可能更快觸發不安或退縮。",
        "conjunction": "私密安全感與生活節奏直接疊合；熟悉感強，但出生時間不明時要降權。",
        "instruction": "先讀雙方 Moon 的安全感節奏；出生時間不明時保守處理，不替對方寫內心台詞。",
    },
    "western-aspects-mars-mars": {
        "pairKey": "Mars-Mars",
        "label": "Mars-Mars 行動與衝突節奏",
        "sourceClaimId": "western-aspects-mars-mars-001",
        "relationshipFunction": "action_conflict_rhythm",
        "soft": "推進節奏較容易互相帶動，適合短、明確、低壓的行動。",
        "hard": "推進節奏容易硬碰硬，熱度可能變成競爭、急躁或權力拉扯。",
        "conjunction": "推進、欲望與衝突速度直接疊合；熱度高，也更需要邊界和控速。",
        "instruction": "先讀雙方 Mars 的行動速度與衝突節奏；hard contact 避免硬碰硬。",
    },
    "western-aspects-mercury-sun": {
        "pairKey": "Mercury-Sun",
        "label": "Mercury-Sun 溝通與自我感",
        "sourceClaimId": "western-aspects-mercury-sun-001",
        "relationshipFunction": "communication_self_respect",
        "soft": "溝通有機會讓對方覺得被理解；仍要避免把理解入口升級成承諾。",
        "hard": "溝通容易碰到自尊與意志之爭；修復時要降低說服、糾正和逼對方承認的壓力。",
        "conjunction": "話語直接碰到自我感，容易被聽見，也容易被放大。",
        "instruction": "先讀 Mercury 的說法，再讀 Sun 的自我感；hard contact 優先降 ego pressure。",
    },
    "western-aspects-mercury-jupiter": {
        "pairKey": "Mercury-Jupiter",
        "label": "Mercury-Jupiter 開闊對話",
        "sourceClaimId": "western-aspects-mercury-jupiter-001",
        "relationshipFunction": "communication_perspective_repair",
        "soft": "對話有機會被幽默、鼓勵或更大的視角打開；仍不能把樂觀寫成承諾。",
        "hard": "對話容易放大成說教、過度解釋或 false hope；修復時要短、實際、可退場。",
        "conjunction": "視角與說法直接放大，能鼓勵，也可能一次講太大。",
        "instruction": "先讀 Mercury 的訊息方式，再讀 Jupiter 的放大與信念；supportive contact 給低壓入口，hard contact 降低承諾與說教。",
    },
    "western-aspects-moon-saturn": {
        "pairKey": "Moon-Saturn",
        "label": "月亮-土星情緒與責任語氣",
        "sourceClaimId": "western-aspect-function-combination-reducers-002",
        "relationshipFunction": "emotional_responsibility_language",
        "soft": "情緒安全和負責任的行動有機會互補，但仍需要耐心和可預期行動。",
        "hard": "一方需要被安撫，另一方先拿出規則、責任或沉默；不是沒有感覺，而是情緒和責任的語氣接不上。",
        "conjunction": "情緒安全和責任感直接疊合，會帶來穩定需求，也會放大怕受傷。",
        "instruction": "先讀月亮的安全感，再讀土星的防衛與責任；避免把冷淡寫成不愛。",
    },
    "western-aspects-venus-saturn": {
        "pairKey": "Venus-Saturn",
        "label": "金星-土星好感與承諾壓力",
        "sourceClaimId": "western-aspect-function-combination-reducers-003",
        "relationshipFunction": "affection_commitment_pressure",
        "soft": "好感有機會透過穩定、耐心和實際行動慢慢落地，但不能保證等待就會自然變好。",
        "hard": "有好感也容易先縮回責任、害怕、控制或延遲裡；越逼承諾，表達越可能變慢。",
        "conjunction": "好感和責任直接疊合，關係有重量，也容易不輕鬆。",
        "instruction": "先讀金星的喜歡方式，再讀土星的防衛；同時保留承諾可能與阻滯風險。",
    },
    "western-aspects-mars-saturn": {
        "pairKey": "Mars-Saturn",
        "label": "火星-土星推進與煞車",
        "sourceClaimId": "western-aspect-function-combination-reducers-004",
        "relationshipFunction": "pursuit_boundary_pressure",
        "soft": "行動力有機會被土星穩住方向，但需要尊重節奏和界線。",
        "hard": "一方想推進，一方踩煞車；壓抑太久容易形成控制、冷距離和爆發循環。",
        "conjunction": "行動力和限制直接疊合，既有耐力，也容易覺得被卡住。",
        "instruction": "先讀火星的推進和衝突節奏，再讀土星的界線；避免硬碰硬。",
    },
    "western-aspects-sun-saturn": {
        "pairKey": "Sun-Saturn",
        "label": "太陽-土星自我與責任壓力",
        "sourceClaimId": "western-aspects-sun-saturn-001",
        "relationshipFunction": "identity_responsibility_pressure",
        "soft": "彼此比較有機會把責任放進日常互動裡，但仍不能把穩定感寫成無限等待。",
        "hard": "自我表達容易被規則、批評或責任壓住；越逼確認，越容易讓對方更慢開口。",
        "conjunction": "自我感和責任壓力直接疊合，關係有重量，也容易變成一直被檢查、被要求。",
        "instruction": "先讀太陽的自我感，再讀土星的防衛與責任；保留成熟可能，同時標出壓抑風險。",
    },
    "western-aspects-outer-planet-intensity-families": {
        "pairKey": "Outer-planet intensity",
        "label": "外行星強度與界線",
        "sourceClaimId": "western-aspects-outer-planet-intensity-families-001",
        "relationshipFunction": "intensity_projection_boundary",
        "soft": "外行星強度可以帶來吸引、靈感或轉化感，但仍要落回現實界線。",
        "hard": "外行星強度容易變成忽遠忽近、投射、理想化或權力拉扯；不能寫成命定保證。",
        "conjunction": "外行星與個人點直接疊合，強度高，但也需要更保守的界線語氣。",
        "instruction": "只把 Uranus/Neptune/Pluto 寫成 guarded intensity、自由/投射/界線課題；不可診斷、恐嚇或保證復合。",
    },
}


MERCURY_CONTACT_FUNCTION_CONFIG = {
    frozenset(("Mercury", "Moon")): {
        "pairKey": "Mercury-Moon",
        "label": "Mercury-Moon 感受與語言",
        "sourceClaimId": "western-aspects-mercury-contacts-002",
        "relationshipFunction": "communication_emotional_translation",
        "soft": "感受比較容易被翻成可聽懂的話；適合低壓澄清，而不是追問答案。",
        "hard": "感受和解釋方式容易錯頻；一方在說感覺，另一方可能用道理回應。",
        "conjunction": "感受和語言直接碰在一起，容易說出心情，也容易把一句話聽成情緒訊號。",
        "instruction": "先讀 Moon 的情緒訊號，再讀 Mercury 的理解方式；hard contact 優先降低辯解與糾正。",
    },
    frozenset(("Mercury", "Venus")): {
        "pairKey": "Mercury-Venus",
        "label": "Mercury-Venus 好感語言",
        "sourceClaimId": "western-aspects-mercury-contacts-005",
        "relationshipFunction": "communication_affection_softening",
        "soft": "話語較容易被柔和接住；適合釋放善意，但不能包裝成情緒施壓。",
        "hard": "好感和說法可能不在同一節奏；善意也容易被聽成要求或評價。",
        "conjunction": "說話方式和好感表達直接疊合；甜度與可接收度明顯，但仍要看壓力。",
        "instruction": "先讀 Mercury 的說法，再讀 Venus 的接收與好感；不可把好聊寫成承諾。",
    },
    frozenset(("Mercury", "Mars")): {
        "pairKey": "Mercury-Mars",
        "label": "Mercury-Mars 話語與衝動",
        "sourceClaimId": "western-aspects-mercury-contacts-003",
        "relationshipFunction": "communication_activation_conflict",
        "soft": "反應快、能把話推進；用得好是清楚，用太滿仍會像催促。",
        "hard": "話語容易挑起防衛、反擊或急著辯清楚；短訊息也可能變得像對抗。",
        "conjunction": "語言和行動衝動直接點火；對話有速度，也容易一講就急。",
        "instruction": "先讀 Mercury 的訊息，再讀 Mars 的衝動和防衛；hard contact 優先縮短、降速、降刺激。",
    },
    frozenset(("Mercury", "Saturn")): {
        "pairKey": "Mercury-Saturn",
        "label": "Mercury-Saturn 謹慎溝通",
        "sourceClaimId": "western-aspects-mercury-contacts-004",
        "relationshipFunction": "communication_boundary_delay",
        "soft": "較能把話落到現實與責任；適合清楚、短、可執行的修復語氣。",
        "hard": "說話容易被審核、延遲或壓住；越逼對方表態，越可能讓溝通變慢。",
        "conjunction": "語言和審慎、責任、怕說錯直接疊合；能談現實，也容易沉重。",
        "instruction": "先讀 Mercury 的說法，再讀 Saturn 的審慎與防衛；不可把沉默寫成愛或不愛。",
    },
    frozenset(("Mercury", "Mercury")): {
        "pairKey": "Mercury-Mercury",
        "label": "Mercury-Mercury 思路互通",
        "sourceClaimId": "western-aspects-mercury-contacts-001",
        "relationshipFunction": "communication_mental_compatibility",
        "soft": "比較容易聽懂彼此的邏輯；適合用簡短、具體、少指責的方式確認事實。",
        "hard": "兩人的理解路線容易交錯；不是沒話說，而是同一句話可能被拆成不同意思。",
        "conjunction": "思路和表達方式直接疊合；容易快速懂彼此，也容易卡在同一種說法裡。",
        "instruction": "先讀雙方 Mercury 的理解路線；不可把能聊寫成一定有機會，也不可用長篇解釋施壓。",
    },
}


def western_aspect_function_config(aspect: dict[str, Any], article_id: str) -> dict[str, str] | None:
    if article_id == "western-aspects-mercury-contacts":
        points = frozenset(
            [
                str(aspect.get("person_a_point") or ""),
                str(aspect.get("person_b_point") or ""),
            ]
        )
        return MERCURY_CONTACT_FUNCTION_CONFIG.get(points)
    return ASPECT_FUNCTION_COMBINATION_CONFIG.get(article_id)


WESTERN_OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}


WESTERN_PERSONAL_RELATIONSHIP_POINTS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter"}


REPEATED_THEME_REDUCER_METHOD_CLAIM_IDS = ["burk-repeated-themes-outweigh-single-contacts"]


REPEATED_THEME_REDUCER_CONFIG = {
    "saturn_pressure": {
        "label": "責任與防衛重複出現",
        "priority": 60,
        "interpretation": "同一種卡住感不是只來自一個相位；Saturn 或壓力主題重複時，答案要優先看防衛、責任感、怕受傷與慢下來的機制。",
        "instruction": "先降低推進壓力，確認對方接得住再談答案；不要把慢、冷或有距離直接寫成不愛。",
    },
    "emotional_safety": {
        "label": "安全感與被安撫反覆被觸發",
        "priority": 50,
        "interpretation": "安全感主題重複時，關係卡點通常不是只有喜不喜歡，而是脆弱、需要被接住與被珍惜的方式能不能對上。",
        "instruction": "回答核心問題前先說清楚雙方需要安全感的方式；不要只用吸引或單次互動下結論。",
    },
    "communication_repair": {
        "label": "溝通與理解方式反覆成為關鍵",
        "priority": 45,
        "interpretation": "溝通主題重複時，重點不是多解釋，而是訊息會不會碰到自尊、說服感、糾正感或被迫表態的壓力。",
        "instruction": "把行動建議寫成短、輕、可退場的對話節奏；避免連續追問、辯論或一次講太滿。",
    },
    "attraction_pursuit": {
        "label": "吸引與靠近感反覆出現",
        "priority": 40,
        "interpretation": "吸引、好感或追逐主題重複時，代表牽動感明顯；但仍要看安全感、壓力和現實回應能不能穩住，不能直接等同承諾。",
        "instruction": "可以把吸引寫成低壓靠近入口，但必須同時檢查壓力點與修復條件。",
    },
    "action_conflict": {
        "label": "一靠近就容易變急或起衝突",
        "priority": 35,
        "interpretation": "行動和衝突主題重複時，關係容易在靠近速度、主動性、被逼迫感或硬碰硬裡升溫。",
        "instruction": "先把步調放慢、不要再加壓，再處理真正想說的問題；不要用衝動行動測試關係。",
    },
    "identity_rhythm": {
        "label": "自我感與情緒節奏重複被碰到",
        "priority": 30,
        "interpretation": "自我感和情緒節奏重複時，雙方容易在被看見、被尊重、被理解和生活節奏上互相牽動。",
        "instruction": "把判斷寫成互動節奏和自尊感的翻譯，聚焦可觀察的回應與行動。",
    },
    "outer_intensity": {
        "label": "強烈牽動與界線感重複出現",
        "priority": 25,
        "interpretation": "外行星強度重複時，吸引、投射、理想化或忽遠忽近感可能被放大；需要更保守地處理界線。",
        "instruction": "只寫強度、投射與界線課題；不可寫成命定、控制、診斷或保證復合。",
    },
}


WESTERN_ASPECT_CATEGORY_LABELS = {
    "attraction": "合盤吸引群組",
    "emotionalSafety": "合盤情緒安全群組",
    "pressure": "合盤壓力群組",
    "repair": "合盤修復潛力",
    "communication": "合盤溝通摩擦",
    "aspectContactModifier": "相位接觸修飾",
    "aspectPairContactTemplate": "planet-pair 接觸模板",
}


TIMING_BAND_LABELS = {
    "better": "較適合低壓靠近",
    "neutral": "觀察為主",
    "avoid": "先避開高壓推進",
}


TIMING_CATEGORY_LABELS = {
    "communication_window": "水星溝通窗口",
    "communication_pressure": "水星溝通壓力",
    "softening": "金星緩和窗口",
    "relationship_focus": "關係感受前台",
    "activation_pressure": "火星啟動刺激",
    "pressure": "土星邊界壓力",
    "emotional_weather": "月亮短期情緒天氣",
    "background": "整體節奏",
}


TIMING_CONTACT_REDUCER_SOURCE = "western-contact-timing-action-reducers"


TIMING_CONTACT_REDUCER_CONFIG = {
    "communication_window": {
        "label": "Mercury 低壓溝通",
        "sourceClaimId": "western-contact-timing-action-reducers-002",
        "polarity": "support",
        "relationshipFunction": "message_clarity",
        "instruction": "可作為短句、低要求、可退場的訊息窗口；不保證回覆。",
    },
    "communication_pressure": {
        "label": "Mercury 溝通壓力",
        "sourceClaimId": "western-contact-timing-action-reducers-002",
        "polarity": "caution",
        "relationshipFunction": "message_pressure",
        "instruction": "先修語氣，避免辯論、糾正、連續補充或逼對方承認。",
    },
    "softening": {
        "label": "Venus 緩和",
        "sourceClaimId": "western-contact-timing-action-reducers-003",
        "polarity": "support",
        "relationshipFunction": "soft_reentry",
        "instruction": "可支援溫和釋放善意，但不代表長期承諾或復合。",
    },
    "relationship_focus": {
        "label": "Venus 關係感受前台",
        "sourceClaimId": "western-contact-timing-action-reducers-003",
        "polarity": "support",
        "relationshipFunction": "relationship_focus",
        "instruction": "關係感受較容易被帶到前台，仍應保持低壓與不索取答案。",
    },
    "activation_pressure": {
        "label": "Mars 啟動刺激",
        "sourceClaimId": "western-contact-timing-action-reducers-004",
        "polarity": "caution",
        "relationshipFunction": "activation_pressure",
        "instruction": "避免急、長、硬碰硬；先控速，不把焦急當成行動指令。",
    },
    "pressure": {
        "label": "土星邊界壓力",
        "sourceClaimId": "western-contact-timing-action-reducers-005",
        "polarity": "caution",
        "relationshipFunction": "boundary_pressure",
        "instruction": "降低聯絡的確定語氣，先尊重限制、責任、距離與對方界線。",
    },
}


WESTERN_HARD_ASPECTS = {"Square", "Opposition", "Quincunx"}


WESTERN_SOFT_ASPECTS = {"Trine", "Sextile"}


WESTERN_CONTACT_MODIFIER_SOURCE = "western-aspect-contact-type-modifiers"


WESTERN_PAIR_CONTACT_TEMPLATE_SOURCE = "western-aspect-pair-contact-phrase-templates"


WESTERN_CONTACT_MODIFIER_DEFAULTS = {
    "conjunction": {
        "label": "conjunction 強度疊合",
        "claim_ids": [
            "western-aspect-contact-type-modifiers-001",
            "western-aspect-contact-type-modifiers-004",
            "western-aspect-contact-type-modifiers-005",
        ],
        "interpretation": "Conjunction 讓兩個功能直接疊合與放大，必須回到 planet pair 判斷是吸引、安全、溝通還是壓力。",
        "does_not_prove": "Conjunction 不等於命定、承諾、復合保證，也不能自動當成 soft 或 hard。",
        "reducer_instruction": "把 conjunction 寫成高強度融合或直接牽動，避免寫成單純好壞。",
    },
    "soft": {
        "label": "soft contact 協調入口",
        "claim_ids": [
            "western-aspect-contact-type-modifiers-001",
            "western-aspect-contact-type-modifiers-002",
            "western-aspect-contact-type-modifiers-005",
        ],
        "interpretation": "Soft contact 讓互動比較容易流動，可作為低壓修復入口或協調條件。",
        "does_not_prove": "Soft contact 不保證對方回覆、承諾、復合或精準時間點。",
        "reducer_instruction": "把 soft contact 寫成條件式開口或較可協調，不寫成保證。",
    },
    "hard": {
        "label": "hard contact 張力調整",
        "claim_ids": [
            "western-aspect-contact-type-modifiers-001",
            "western-aspect-contact-type-modifiers-003",
            "western-aspect-contact-type-modifiers-005",
        ],
        "interpretation": "緊張相位讓互動帶張力、摩擦或需要調整，適合拆卡住機制與防衛反應。",
        "does_not_prove": "緊張相位不等於沒有愛、必定分開、誰錯，或關係不可修復。",
        "reducer_instruction": "把緊張相位寫成需要處理的張力與保守語氣訊號，不寫成命定結論。",
    },
    "minor": {
        "label": "minor contact 背景提示",
        "claim_ids": [
            "western-aspect-contact-type-modifiers-001",
            "western-aspect-contact-type-modifiers-005",
        ],
        "interpretation": "Minor contact 只能作為背景提示，不能替代主要相位證據。",
        "does_not_prove": "Minor contact 不足以支撐核心關係結論。",
        "reducer_instruction": "只在缺少主要相位時作背景，不升級成主判斷。",
    },
    "other": {
        "label": "other contact 背景提示",
        "claim_ids": [
            "western-aspect-contact-type-modifiers-001",
            "western-aspect-contact-type-modifiers-005",
        ],
        "interpretation": "未分類 contact type 只能作背景，需要主要相位與 orb 支持。",
        "does_not_prove": "未分類 contact type 不足以支撐核心關係結論。",
        "reducer_instruction": "只作背景提示，不升級成主判斷。",
    },
}


WESTERN_CLUSTER_SOURCE = "western-synastry-evidence-clusters"


WESTERN_REPAIR_SOURCE = "western-synastry-repair-conditions"


WESTERN_PRECISION_SOURCE = "western-precision-birth-data-quality"


HOUSE_ANGLE_GATE_CLAIM_IDS = [
    "western-houses-angles-foundation-001",
    "western-houses-angles-foundation-002",
    "western-houses-angles-foundation-003",
    "western-houses-angles-foundation-004",
]


HOUSE_ANGLE_PRECISION_CLAIM_IDS = [
    *HOUSE_ANGLE_GATE_CLAIM_IDS,
    "western-precision-birth-data-quality-001",
    "western-precision-birth-data-quality-002",
    "western-precision-birth-data-quality-003",
]


CLAIM_SOURCE_ALIASES = {
    "timing-method-gap": "western-composite-composite-chart",
    "western-calculation": "western-synastry-method",
    "western-current-transits-v1": "western-transits-timing-window",
    "western-evidence-clusters": WESTERN_CLUSTER_SOURCE,
    "western-emotional-safety": "western-planets-natal-relationship-needs",
    "western-house-overlays": WESTERN_PRECISION_SOURCE,
    "western-repair-conditions": WESTERN_REPAIR_SOURCE,
    "western-saturn-pressure": "western-aspects-saturn-pressure",
    "western-synastry": "western-synastry-method",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_articles(path: Path) -> dict[str, dict[str, Any]]:
    return {article["id"]: article for article in read_json(path)}


def load_claims_by_article(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    claims_by_article: dict[str, list[dict[str, Any]]] = {}
    for claim in read_json(path):
        article_id = str(claim.get("article_id") or "")
        if not article_id:
            continue
        claims_by_article.setdefault(article_id, []).append(claim)
    return claims_by_article


def western_atom_for_category(structured_kb: dict[str, Any] | None, category: str) -> dict[str, Any]:
    if not structured_kb:
        return {}
    atom = (structured_kb.get("atomsByCategory") or {}).get(category)
    return atom if isinstance(atom, dict) else {}


def western_atom_for_source_article(structured_kb: dict[str, Any] | None, source_article_id: str) -> dict[str, Any]:
    if not structured_kb or not source_article_id:
        return {}
    atom = (structured_kb.get("atomsBySourceArticle") or {}).get(source_article_id)
    return atom if isinstance(atom, dict) else {}


def canonical_western_relationship_id(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    if text == LEGACY_WESTERN_FREE_RELATIONSHIP_ID:
        return WESTERN_RELATIONSHIP_RESULT_ID
    return text


def canonical_western_relationship_record(record: Any, id_key: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    canonical_id = canonical_western_relationship_id(record.get(id_key))
    if not canonical_id or canonical_id == record.get(id_key):
        return record
    return {**record, id_key: canonical_id}


def western_relationship_result_question_blueprint(structured_kb: dict[str, Any] | None) -> dict[str, Any]:
    if not structured_kb:
        return {}
    by_id = structured_kb.get("questionBlueprintsById") or {}
    blueprint = by_id.get(WESTERN_RELATIONSHIP_RESULT_ID) or by_id.get(LEGACY_WESTERN_FREE_RELATIONSHIP_ID)
    if isinstance(blueprint, dict):
        return canonical_western_relationship_record(blueprint, "blueprint_id")
    blueprints = structured_kb.get("questionBlueprints") or []
    return canonical_western_relationship_record(blueprints[0], "blueprint_id") if blueprints and isinstance(blueprints[0], dict) else {}


def western_question_blueprint(structured_kb: dict[str, Any] | None, question_key: str) -> dict[str, Any]:
    if not structured_kb or not question_key:
        return {}
    question = (structured_kb.get("questionBlueprintByQuestion") or {}).get(question_key)
    return question if isinstance(question, dict) else {}


def western_question_label(structured_kb: dict[str, Any] | None, question_key: str) -> str:
    question = western_question_blueprint(structured_kb, question_key)
    return str(question.get("label") or QUESTION_TITLES.get(question_key, question_key))


def western_guardrail(structured_kb: dict[str, Any] | None, guardrail_id: str) -> dict[str, Any]:
    if not structured_kb or not guardrail_id:
        return {}
    guardrail = (structured_kb.get("guardrailsById") or {}).get(guardrail_id)
    return guardrail if isinstance(guardrail, dict) else {}


def western_guardrail_reason(structured_kb: dict[str, Any] | None, guardrail_id: str, fallback: str) -> str:
    guardrail = western_guardrail(structured_kb, guardrail_id)
    return str(guardrail.get("reason") or fallback)


def western_condition_value(condition: dict[str, Any], evidence_clusters: dict[str, dict[str, Any]]) -> Any:
    cluster_name = str(condition.get("cluster") or "")
    field = str(condition.get("field") or "")
    if not cluster_name or not field:
        return None
    return (evidence_clusters.get(cluster_name) or {}).get(field)


def western_condition_matches(condition: dict[str, Any], evidence_clusters: dict[str, dict[str, Any]]) -> bool:
    actual = western_condition_value(condition, evidence_clusters)
    op = str(condition.get("op") or "")
    expected = condition.get("value")
    if op == "exists":
        return actual not in (None, "", [], {})
    if op == "missing":
        return actual in (None, "", [], {})
    if op in {"gte", "gt", "lte", "lt"}:
        try:
            actual_float = float(actual or 0)
            expected_float = float(expected or 0)
        except (TypeError, ValueError):
            return False
        if op == "gte":
            return actual_float >= expected_float
        if op == "gt":
            return actual_float > expected_float
        if op == "lte":
            return actual_float <= expected_float
        return actual_float < expected_float
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    return False


def western_rule_matches(rule: dict[str, Any], evidence_clusters: dict[str, dict[str, Any]]) -> bool:
    when = rule.get("when") or {}
    all_conditions = [item for item in when.get("all") or [] if isinstance(item, dict)]
    any_conditions = [item for item in when.get("any") or [] if isinstance(item, dict)]
    if all_conditions and not all(western_condition_matches(condition, evidence_clusters) for condition in all_conditions):
        return False
    if any_conditions and not any(western_condition_matches(condition, evidence_clusters) for condition in any_conditions):
        return False
    return True


def western_select_answer_rule(
    context: dict[str, str],
    evidence_clusters: dict[str, dict[str, Any]],
    structured_kb: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not structured_kb:
        return None
    question = context.get("main_question", "")
    for rule in (structured_kb.get("rulesByQuestion") or {}).get(question, []):
        if isinstance(rule, dict) and western_rule_matches(rule, evidence_clusters):
            return rule
    return None


def claim_source_candidates(source: str) -> list[str]:
    candidates = [source]
    alias = CLAIM_SOURCE_ALIASES.get(source)
    if alias:
        candidates.append(alias)
    if source.startswith("western-identity-"):
        candidates.append("western-planets-natal-relationship-needs")
    if source.startswith("western-cluster-"):
        candidates.append(WESTERN_CLUSTER_SOURCE)
    if source.startswith("western-precision-"):
        candidates.append(WESTERN_PRECISION_SOURCE)
    return unique([candidate for candidate in candidates if candidate])


def claim_support_for(
    source: str,
    claims_by_article: dict[str, list[dict[str, Any]]],
    product_use: str = "free",
    limit: int = 2,
    claim_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    confidence_rank = {"DOCTRINE": 0, "INTERPRETATION": 1, "SPECULATIVE": 2}
    claims: list[dict[str, Any]] = []
    for article_id in claim_source_candidates(source):
        claims.extend(claims_by_article.get(article_id) or [])

    allowed_claim_ids = {str(claim_id) for claim_id in claim_ids or [] if claim_id}
    filtered = [
        claim
        for claim in claims
        if (
            not allowed_claim_ids
            or str(claim.get("claim_id") or "") in allowed_claim_ids
        )
        and (
            product_use in (claim.get("product_use") or [])
            or (product_use != "free" and "full" in (claim.get("product_use") or []))
        )
    ]
    filtered.sort(
        key=lambda claim: (
            confidence_rank.get(str(claim.get("confidence") or ""), 9),
            str(claim.get("claim_id") or ""),
        )
    )

    support: list[dict[str, Any]] = []
    seen: set[str] = set()
    for claim in filtered:
        claim_id = str(claim.get("claim_id") or "")
        if not claim_id or claim_id in seen:
            continue
        seen.add(claim_id)
        support.append(
            {
                "claimId": claim_id,
                "articleId": claim.get("article_id"),
                "claim": claim.get("claim"),
                "confidence": claim.get("confidence"),
                "sourceId": claim.get("source_id"),
                "sourceLocation": claim.get("source_location"),
            }
        )
        if len(support) >= limit:
            break
    return support


def article_title(article_id: str | None, articles: dict[str, dict[str, Any]]) -> str:
    if not article_id:
        return "資料不足"
    return SIGNAL_TITLES.get(article_id) or articles.get(article_id, {}).get("title") or article_id


def western_missing_title() -> str:
    return "西洋合盤資料不足"


def western_unavailable_reason(fixture: dict[str, Any]) -> str:
    western = fixture.get("western") or {}
    people = western.get("people") or {}
    skipped_people = [
        role
        for role, chart in people.items()
        if isinstance(chart, dict) and chart.get("status") == "skipped"
    ]
    warnings = [str(item) for item in fixture.get("debug", {}).get("calculation_warnings") or []]
    if skipped_people:
        place_warning = next((warning for warning in warnings if "Unknown birth_place coordinates" in warning), "")
        if place_warning:
            return "出生城市暫時無法定位，西洋合盤未能完整計算。"
        return "其中一方西洋星盤未能完整計算。"
    if any("birth_time unknown" in warning for warning in warnings):
        return "有一方出生時間未知，月亮、上升與宮位相關訊號已保守降權。"
    return "本次沒有產生足夠強的可展示西洋合盤訊號。"


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def western_object(fixture: dict[str, Any], person: str, point: str) -> dict[str, Any] | None:
    key = point.lower()
    chart = fixture.get("western", {}).get("people", {}).get(person, {})
    objects = chart.get("objects") or {}
    value = objects.get(key)
    return value if isinstance(value, dict) else None


def western_chart(fixture: dict[str, Any], person: str) -> dict[str, Any]:
    chart = fixture.get("western", {}).get("people", {}).get(person, {})
    return chart if isinstance(chart, dict) else {}


def western_time_known(fixture: dict[str, Any], person: str) -> bool:
    return western_chart(fixture, person).get("birth_precision") == "date_time"


def western_location_known(fixture: dict[str, Any], person: str) -> bool:
    return western_chart(fixture, person).get("location_precision", "known") == "known"


def western_houses_allowed(fixture: dict[str, Any], person: str) -> bool:
    return western_time_known(fixture, person) and western_location_known(fixture, person)


def western_house_angle_precision_gate_from_states(people: list[dict[str, Any]]) -> dict[str, Any]:
    missing_time_count = sum(1 for person in people if not person.get("hasReliableBirthTime"))
    missing_location_count = sum(1 for person in people if not person.get("hasReliableLocation"))
    houses_allowed_count = sum(1 for person in people if person.get("housesAllowed"))
    if missing_time_count:
        status = "blocked_by_birth_time"
        blocked_claims = ["Asc", "Desc", "houses", "house_overlays"]
    elif missing_location_count:
        status = "blocked_by_location"
        blocked_claims = ["Asc", "Desc", "houses", "house_overlays"]
    elif houses_allowed_count == len(people):
        status = "allowed_by_precision"
        blocked_claims = []
    else:
        status = "unavailable"
        blocked_claims = ["Asc", "Desc", "houses", "house_overlays"]
    return {
        "version": "house-angle-precision-gate-v1",
        "status": status,
        "role": "precision_context_layer",
        "requiresReliableBirthTime": True,
        "requiresReliableLocation": True,
        "allowsAngles": status == "allowed_by_precision",
        "allowsNatalHouses": status == "allowed_by_precision",
        "allowsHouseOverlaysByPrecision": status == "allowed_by_precision",
        "canCreateAstrologyConclusion": False,
        "requiresCalculatedHouseOrAngleEvidence": True,
        "contextLayerOnly": True,
        "blockedClaims": blocked_claims,
        "missingBirthTimeCount": missing_time_count,
        "missingLocationCount": missing_location_count,
        "housesAllowedCount": houses_allowed_count,
        "people": people,
        "sourceArticleIds": ["western-houses-angles-foundation", WESTERN_PRECISION_SOURCE],
        "sourceClaimIds": HOUSE_ANGLE_PRECISION_CLAIM_IDS,
    }


def western_house_angle_precision_gate(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    people = []
    for person, label in (("person_a", "你"), ("person_b", "對方")):
        has_time = western_time_known(fixture, person)
        has_location = western_location_known(fixture, person)
        people.append(
            {
                "role": person,
                "label": label,
                "hasReliableBirthTime": has_time,
                "hasReliableLocation": has_location,
                "housesAllowed": has_time and has_location,
            }
        )
    return western_house_angle_precision_gate_from_states(people)


def western_house_angle_precision_gate_from_input_quality(
    input_quality: dict[str, Any],
) -> dict[str, Any]:
    people = []
    for person_key, role, label in (("personA", "person_a", "你"), ("personB", "person_b", "對方")):
        person = input_quality.get(person_key) or {}
        precision = str(person.get("precision") or "unavailable")
        houses_allowed = bool(person.get("housesAllowed"))
        people.append(
            {
                "role": role,
                "label": str(person.get("label") or label),
                "precision": precision,
                "hasReliableBirthTime": precision in {"exact_time", "location_fallback"} and precision != "unavailable",
                "hasReliableLocation": precision not in {"location_fallback", "unavailable"},
                "housesAllowed": houses_allowed,
            }
        )
    return western_house_angle_precision_gate_from_states(people)


def western_moon_confidence(fixture: dict[str, Any], person: str) -> str:
    return "high" if western_time_known(fixture, person) else "low"


def western_need_precision_note(
    fixture: dict[str, Any],
    person: str,
    point: str,
    structured_kb: dict[str, Any] | None = None,
) -> str:
    if point == "Desc" and not western_houses_allowed(fixture, person):
        return western_guardrail_reason(
            structured_kb,
            "western-guardrail-need-desc-block",
            "下降與第七宮需要可靠出生時間與出生地點；本次不作為可展示判斷。",
        )
    if point == "Moon" and not western_time_known(fixture, person):
        return western_guardrail_reason(
            structured_kb,
            "western-guardrail-need-moon-uncertain",
            "出生時間未知，月亮位置以中午盤保守估算，只作可能線索。",
        )
    if not western_location_known(fixture, person):
        return western_guardrail_reason(
            structured_kb,
            "western-guardrail-need-location-fallback",
            "出生城市未提供，宮位與上升/下降相關內容已降權。",
        )
    return western_guardrail_reason(
        structured_kb,
        "western-guardrail-need-default-allowed",
        "可用於本次西洋關係需求判斷。",
    )


def western_need_points(
    fixture: dict[str, Any],
    person: str,
    structured_kb: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for point, meaning in WESTERN_NEED_POINTS.items():
        if point == "Desc" and not western_houses_allowed(fixture, person):
            continue
        obj = western_object(fixture, person, point)
        if not obj:
            continue
        sign = str(obj.get("sign") or "")
        house = obj.get("house")
        sign_label = SIGN_LABELS.get(sign, sign or "未知星座")
        label = POINT_LABELS.get(point, point)
        points.append(
            {
                "point": point,
                "label": f"{label}{sign_label}",
                "sign": sign_label,
                "house": house if isinstance(house, int) and western_houses_allowed(fixture, person) else None,
                "meaning": f"{label}落在{sign_label}，先作為{meaning}的本命需求線索。",
                "confidence": western_moon_confidence(fixture, person) if point == "Moon" else "high",
                "precisionNote": western_need_precision_note(fixture, person, point, structured_kb),
            }
        )
    return points


def western_synastry_aspects(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    aspects = fixture.get("western", {}).get("synastry", {}).get("inter_aspects") or []
    return [aspect for aspect in aspects if isinstance(aspect, dict)]


def western_aspect_article_id(aspect: dict[str, Any]) -> str:
    point_a = str(aspect.get("person_a_point") or "")
    point_b = str(aspect.get("person_b_point") or "")
    article_id = WESTERN_ASPECT_ARTICLE_BY_PAIR.get(frozenset((point_a, point_b)))
    if article_id:
        return article_id
    points = {point_a, point_b}
    if points.intersection(WESTERN_OUTER_PLANETS) and points.intersection(WESTERN_PERSONAL_RELATIONSHIP_POINTS):
        return "western-aspects-outer-planet-intensity-families"
    if "Saturn" in {point_a, point_b}:
        return "western-aspects-saturn-pressure"
    return "western-synastry"


def western_aspect_strength(aspect: dict[str, Any]) -> float:
    try:
        orb = float(aspect.get("orb") or 0)
        max_orb = float(aspect.get("max_orb") or 10)
    except (TypeError, ValueError):
        return 0.3
    if max_orb <= 0:
        return 0.3
    exactness = max(0.0, min(1.0, 1 - (orb / max_orb)))
    if aspect.get("applying"):
        exactness += 0.04
    return max(0.0, min(1.0, exactness))


def western_aspect_sort_key(aspect: dict[str, Any]) -> tuple[float, float]:
    return (western_aspect_strength(aspect), -float(aspect.get("orb") or 99))


def western_aspect_sentence(aspect: dict[str, Any]) -> str:
    point_a = POINT_LABELS.get(str(aspect.get("person_a_point")), str(aspect.get("person_a_point") or "行星"))
    point_b = POINT_LABELS.get(str(aspect.get("person_b_point")), str(aspect.get("person_b_point") or "行星"))
    aspect_label = ASPECT_LABELS.get(str(aspect.get("aspect")), str(aspect.get("aspect") or "相位"))
    orb = aspect.get("orb")
    orb_text = f"，角度差約 {float(orb):.2f}°" if isinstance(orb, (int, float)) else ""
    applying = "，正在靠近" if aspect.get("applying") else "，正在分離"
    return f"你的{point_a}與對方{point_b}形成{aspect_label}{orb_text}{applying}"


def western_aspect_contact_type(aspect: dict[str, Any]) -> str:
    aspect_type = str(aspect.get("aspect") or "")
    if aspect_type in WESTERN_SOFT_ASPECTS:
        return "soft"
    if aspect_type in WESTERN_HARD_ASPECTS:
        return "hard"
    if aspect_type == "Conjunction":
        return "conjunction"
    if aspect_type in {"Semisextile", "Quintile"}:
        return "minor"
    return "other"


def western_aspect_contact_modifier_atom(
    structured_kb: dict[str, Any] | None,
    contact_type: str,
    aspect_type: str,
) -> dict[str, Any]:
    if not structured_kb:
        return {}
    for atom in structured_kb.get("atoms") or []:
        if not isinstance(atom, dict) or atom.get("category") != "aspectContactModifier":
            continue
        selectors = atom.get("selectors") or {}
        contact_types = {str(item) for item in selectors.get("contact_types_any") or []}
        aspects = {str(item) for item in selectors.get("aspects_any") or []}
        if contact_type in contact_types or aspect_type in aspects:
            return atom
    return {}


def western_aspect_contact_modifier(
    aspect: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    aspect_type = str(aspect.get("aspect") or "")
    contact_type = western_aspect_contact_type(aspect)
    defaults = WESTERN_CONTACT_MODIFIER_DEFAULTS.get(contact_type) or WESTERN_CONTACT_MODIFIER_DEFAULTS["other"]
    atom = western_aspect_contact_modifier_atom(structured_kb, contact_type, aspect_type)
    interpretation_atom = atom.get("interpretation") or {}
    claim_ids = [str(claim_id) for claim_id in (atom.get("claim_ids") or defaults["claim_ids"]) if claim_id]
    return {
        "type": contact_type,
        "aspect": aspect_type,
        "label": str(atom.get("label") or defaults["label"]),
        "source": str(atom.get("source_article_id") or WESTERN_CONTACT_MODIFIER_SOURCE),
        "atomId": atom.get("id"),
        "claimIds": claim_ids,
        "interpretation": str(interpretation_atom.get("interpretation") or defaults["interpretation"]),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or defaults["does_not_prove"]),
        "reducerInstruction": str(defaults["reducer_instruction"]),
    }


def western_aspect_pair_contact_template_atom(
    structured_kb: dict[str, Any] | None,
    aspect: dict[str, Any],
    contact_type: str,
) -> dict[str, Any]:
    if not structured_kb:
        return {}
    aspect_points = sorted(
        [
            str(aspect.get("person_a_point") or ""),
            str(aspect.get("person_b_point") or ""),
        ]
    )
    for atom in structured_kb.get("atoms") or []:
        if not isinstance(atom, dict) or atom.get("category") != "aspectPairContactTemplate":
            continue
        selectors = atom.get("selectors") or {}
        selector_points = [str(item) for item in selectors.get("points_all") or [] if item]
        selector_contact_types = {str(item) for item in selectors.get("contact_types_any") or []}
        if sorted(selector_points) == aspect_points and contact_type in selector_contact_types:
            return atom
    return {}


def western_aspect_pair_contact_template(
    aspect: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    contact_type = western_aspect_contact_type(aspect)
    atom = western_aspect_pair_contact_template_atom(structured_kb, aspect, contact_type)
    if not atom:
        return None
    interpretation_atom = atom.get("interpretation") or {}
    article_id = str(atom.get("source_article_id") or "")
    method_claim_ids = [str(claim_id) for claim_id in PAIR_FAMILY_METHOD_CLAIM_IDS.get(article_id, []) if claim_id]
    return {
        "id": atom.get("id"),
        "label": str(atom.get("label") or ""),
        "source": article_id or WESTERN_PAIR_CONTACT_TEMPLATE_SOURCE,
        "atomId": atom.get("id"),
        "claimIds": [str(claim_id) for claim_id in atom.get("claim_ids") or [] if claim_id],
        "methodClaimIds": method_claim_ids,
        "contactType": contact_type,
        "interpretation": str(interpretation_atom.get("interpretation") or ""),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or ""),
    }


def western_aspect_reading_role(aspect: dict[str, Any], category: str) -> str:
    contact_type = western_aspect_contact_type(aspect)
    source = western_aspect_article_id(aspect)
    if source == "western-aspects-sun-venus":
        if contact_type == "hard":
            return "有欣賞與好感，但也可能混入自尊、支配感或期待落差。"
        return "欣賞、柔性好感與被對方吸引的線索較清楚，但仍要看壓力能不能被處理。"
    if source == "western-aspects-moon-moon":
        if contact_type == "hard":
            return "情緒節奏容易在本能層面互相觸發，需要保守判讀。"
        return "私密安全感與生活節奏比較容易互相理解。"
    if source == "western-aspects-moon-mars":
        if contact_type == "hard":
            return "情緒與行動會快速點火，容易把牽動變成刺激、防衛或爭執。"
        return "情緒與行動互相喚起，代表有反應，但仍需降低衝動。"
    if source == "western-aspects-venus-venus":
        if contact_type == "hard":
            return "喜歡語言與愉悅方式有共鳴也有落差，可能迴避真正衝突。"
        return "共同品味、affection style 與相處舒服感較容易成立。"
    if source == "western-aspects-mars-mars":
        if contact_type == "hard":
            return "行動節奏容易不同步，熱度可能轉成競爭、急躁或權力拉扯。"
        return "推進力與共同目標較容易互相點燃。"
    if source == "western-aspects-mercury-sun":
        if contact_type == "hard":
            return "溝通容易碰到自尊與意志之爭，修復時要降低說服壓力。"
        return "理解、被聽見與把話說到對方自我感上的入口較清楚。"
    if source == "western-aspects-mercury-jupiter":
        if contact_type == "hard":
            return "對話容易放大成說教、挑剔或過度承諾，需要避免 false hope。"
        return "幽默、鼓勵與開闊視角可作為低壓修復入口。"
    if source == "western-aspects-outer-planet-intensity-families":
        if "Uranus" in {str(aspect.get("person_a_point") or ""), str(aspect.get("person_b_point") or "")}:
            return "電流感與不穩定並存，只能寫成自由/距離課題。"
        if "Neptune" in {str(aspect.get("person_a_point") or ""), str(aspect.get("person_b_point") or "")}:
            return "理想化、投射與界線模糊需要被標示，不能寫成靈魂伴侶保證。"
        if "Pluto" in {str(aspect.get("person_a_point") or ""), str(aspect.get("person_b_point") or "")}:
            return "強烈吸引與權力/恐懼課題需要創傷知情語氣，不可診斷或恐嚇。"
        return "外行星只作為 guarded intensity evidence，不作為結局保證。"
    if category == "attraction":
        if contact_type == "hard":
            return "有牽動也容易刺激彼此反應，不能直接等同穩定承諾。"
        if contact_type == "soft":
            return "自然好感與靠近入口較容易被看見，但仍要看壓力能不能被處理。"
        return "牽動感明顯，適合回答是否仍有互動反應。"
    if category == "emotionalSafety":
        if contact_type == "hard":
            return "情緒安全需求容易被觸發，需要保守判讀對方的防衛。"
        if contact_type == "soft":
            return "情緒比較容易被接住，可作為安全感線索。"
        return "用來判斷彼此是否能讓對方感到被接住。"
    if category == "pressure":
        if contact_type == "soft":
            return "壓力仍存在，但比較像需要成熟處理的責任感。"
        return "容易讓互動變慢、變重、變防衛，是卡住機制的主要候選。"
    if category == "communication":
        if contact_type == "hard":
            return "容易在訊息、解讀或節奏上互相誤會。"
        return "提供重新說清楚的入口，但不保證對方會立刻回應。"
    if category == "repair":
        return "只代表有協調入口，仍要看壓力是否下降與行動是否穩定。"
    return "作為本次西洋合盤證據之一。"


def western_aspect_categories(aspect: dict[str, Any]) -> set[str]:
    points = {str(aspect.get("person_a_point") or ""), str(aspect.get("person_b_point") or "")}
    aspect_type = str(aspect.get("aspect") or "")
    contact_type = western_aspect_contact_type(aspect)
    categories: set[str] = set()
    article_id = western_aspect_article_id(aspect)
    attraction_pairs = (
        frozenset(("Sun", "Venus")),
        frozenset(("Venus", "Mars")),
        frozenset(("Sun", "Mars")),
        frozenset(("Moon", "Mars")),
        frozenset(("Venus", "Venus")),
        frozenset(("Mars", "Mars")),
        frozenset(("Moon", "Venus")),
        frozenset(("Sun", "Moon")),
    )
    if article_id in ATTRACTION_SIGNAL_IDS or frozenset(points) in attraction_pairs:
        categories.add("attraction")
    if "Moon" in points or article_id in EMOTIONAL_SAFETY_SIGNAL_IDS:
        categories.add("emotionalSafety")
    if "Saturn" in points or points.intersection(WESTERN_OUTER_PLANETS) or aspect_type in WESTERN_HARD_ASPECTS:
        categories.add("pressure")
    if "Mercury" in points:
        categories.add("communication")
    if contact_type == "soft":
        categories.add("repair")
    return categories


def western_aspects_for_category(fixture: dict[str, Any], category: str) -> list[dict[str, Any]]:
    matches = [
        aspect
        for aspect in western_synastry_aspects(fixture)
        if aspect.get("eligible_for_signal", True) and category in western_aspect_categories(aspect)
    ]
    return sorted(matches, key=western_aspect_sort_key, reverse=True)


def western_category_emotional_meaning(category: str) -> str:
    if category == "attraction":
        return "這層回答為什麼兩人仍容易被彼此點到、牽動或重新有反應。"
    if category == "emotionalSafety":
        return "這層回答冷淡、想確認、怕受傷或忽遠忽近是否來自情緒安全需求。"
    if category == "pressure":
        return "這層回答為什麼有吸引卻難以自然推進，常表現為變慢、變冷、拉開距離或責任壓力。"
    if category == "repair":
        return "這層回答關係是否還有協調入口，但不等於可以直接復合。"
    if category == "communication":
        return "這層回答彼此是否容易誤解、說不清或在訊息裡失焦。"
    return "這層提供合盤互動功能分類。"


def western_category_does_not_prove(category: str) -> str:
    if category == "attraction":
        return "吸引用來看靠近動力，承諾與回來要看後續穩定行動。"
    if category == "emotionalSafety":
        return "情緒安全訊號用來看親近時是否接得住，以及壓力來時會怎麼防衛。"
    if category == "pressure":
        return "壓力高不等於沒有感覺，也不等於關係必定結束。"
    if category == "repair":
        return "修復潛力不是復合保證，仍要看壓力與時間窗。"
    if category == "communication":
        return "溝通摩擦不等於誰對誰錯，也不代表不能修復。"
    return "合盤分類不能單獨斷結局。"


def western_transit_aspect_sentence(aspect: dict[str, Any]) -> str:
    transit = POINT_LABELS.get(str(aspect.get("transit_point")), str(aspect.get("transit_point") or "行運點"))
    natal = POINT_LABELS.get(str(aspect.get("natal_point")), str(aspect.get("natal_point") or "本命點"))
    aspect_label = ASPECT_LABELS.get(str(aspect.get("aspect")), str(aspect.get("aspect") or "相位"))
    orb = aspect.get("orb")
    orb_text = f"，角度差約 {float(orb):.2f}°" if isinstance(orb, (int, float)) else ""
    return f"行運{transit}與本命{natal}形成{aspect_label}{orb_text}"


def slot_map(selection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    slots: dict[str, dict[str, Any]] = {}
    for assignment in selection.get("slot_assignments") or []:
        slot = assignment.get("slot")
        if slot and slot not in slots:
            slots[str(slot)] = assignment
    return slots


def slot_article_id(slots: dict[str, dict[str, Any]], slot: str) -> str | None:
    assignment = slots.get(slot) or {}
    value = assignment.get("article_id")
    return str(value) if value else None


def level_from_score(score: int) -> str:
    if score >= 78:
        return "高"
    if score >= 66:
        return "中高"
    if score >= 52:
        return "中"
    return "低"


def clamp_score(value: float, low: int = 45, high: int = 86) -> int:
    return max(low, min(high, round(value)))


def western_timing_profile(fixture: dict[str, Any]) -> dict[str, Any]:
    return fixture.get("western", {}).get("analysis", {}).get("timing_profile") or {}


def western_signal(fixture: dict[str, Any], article_id: str | None) -> dict[str, Any] | None:
    for signal in fixture.get("candidate_signals", {}).get("western_signals") or []:
        if signal.get("id") == article_id:
            return signal
    return None


def strongest_pressure_signal(fixture: dict[str, Any]) -> dict[str, Any] | None:
    signals = fixture.get("candidate_signals", {}).get("western_signals") or []
    pressure = [
        signal
        for signal in signals
        if any(token in str(signal.get("id", "")) for token in ("saturn", "moon-saturn", "sun-saturn"))
    ]
    if not pressure:
        return None
    return max(pressure, key=lambda signal: float(signal.get("strength", 0)))


def aspect_evidence_sentence(signal: dict[str, Any] | None) -> str:
    if not signal:
        return "本次沒有足夠可展示的西洋合盤相位，不能硬把缺失資料寫成判斷。"
    evidence = (signal.get("evidence") or [{}])[0] or {}
    point_a = POINT_LABELS.get(str(evidence.get("person_a_point")), str(evidence.get("person_a_point") or "行星"))
    point_b = POINT_LABELS.get(str(evidence.get("person_b_point")), str(evidence.get("person_b_point") or "行星"))
    aspect = ASPECT_LABELS.get(str(evidence.get("aspect")), str(evidence.get("aspect") or "相位"))
    orb = evidence.get("orb")
    orb_text = f"，角度差約 {float(orb):.2f}°" if isinstance(orb, (int, float)) else ""
    return f"合盤裡，你的{point_a}與對方的{point_b}形成{aspect}{orb_text}。"


def western_therefore(article_id: str | None) -> str:
    if not article_id:
        return "所以這次不能把單一相位當成主判斷，應先回到本命需求、關係階段與實際互動。"
    if article_id == "western-aspects-sun-mars":
        return "所以火花存在時，更要把互動速度放慢，避免一靠近就變成衝動或試探。"
    if article_id == "western-aspects-venus-mars":
        return "所以吸引力會讓人想重新靠近，但它不能直接代表關係已經穩定。"
    if article_id == "western-aspects-sun-venus":
        return "所以好感與欣賞可能仍在，但它需要安全感、溝通與壓力層一起支持才可能往前。"
    if article_id == "western-aspects-moon-moon":
        return "所以你們的情緒節奏會互相牽動；缺時間或 hard contact 時，要先保守看安全感而不是急著下結論。"
    if article_id == "western-aspects-moon-mars":
        return "所以感覺一被點燃就容易變急、變刺；先降溫，互動才比較接得住。"
    if article_id == "western-aspects-venus-venus":
        return "所以相處舒服或喜歡語言同頻可能存在，但不能用舒服感取代真正的修復能力。"
    if article_id == "western-aspects-mars-mars":
        return "所以你們容易互相點燃行動，也容易硬碰硬；重新靠近時必須降低競爭與逼迫感。"
    if article_id == "western-aspects-mercury-sun":
        return "所以修復入口在於怎麼說才不刺到自尊，而不是用辯論逼對方承認。"
    if article_id == "western-aspects-mercury-jupiter":
        return "所以對話有機會被拉開視角，但要避免過度承諾、說教或灌 false hope。"
    if article_id == "western-aspects-mars-saturn":
        return "所以一方越想推進，另一方越可能感到被限制，短期內不適合硬碰硬。"
    if article_id == "western-aspects-venus-saturn":
        return "所以感情反應會慢、會縮，越要求承諾越容易讓對方防衛。"
    if article_id == "western-aspects-sun-saturn":
        return "所以關係裡有責任感與牽制感並存，越急著確認，越容易讓表達變慢。"
    if article_id == "western-aspects-sun-moon":
        return "所以你們能互相牽動，但情緒需求與自我節奏也容易互相摩擦。"
    if article_id == "western-aspects-moon-saturn":
        return "所以情緒不是消失，而是被壓住；這時逼對方表態通常只會更冷。"
    if article_id == "western-aspects-moon-venus":
        return "所以你們之間有柔軟的情緒好感，但越想確認就越需要避免把好感變成壓力。"
    if article_id == "western-aspects-mercury-contacts":
        return "所以問題不一定是沒感覺，而是訊息、語氣或理解方式需要先放輕，再重新對上。"
    if article_id == "western-aspects-outer-planet-intensity-families":
        return "所以這只能支持強度、投射或界線課題，不能寫成命中注定、診斷或復合保證。"
    return "所以這個訊號只能支持互動傾向，不能被說成絕對結果。"


def western_evidence_meaning(article_id: str | None) -> str:
    if not article_id:
        return "西洋合盤資料不足，不能把缺失資料寫成相位結論。"
    if article_id == "western-aspects-sun-mars":
        return "有火花，也容易一靠近就變急。"
    if article_id == "western-aspects-venus-mars":
        return "吸引力明顯，但穩定度要另外看。"
    if article_id == "western-aspects-sun-venus":
        return "有欣賞與好感，但承諾和修復要另外看。"
    if article_id == "western-aspects-moon-moon":
        return "情緒節奏會互相牽動，需要看角度精度，也要看安全感能不能接住。"
    if article_id == "western-aspects-moon-mars":
        return "情緒和行動互相點火，有反應也容易刺激。"
    if article_id == "western-aspects-venus-venus":
        return "喜歡語言與相處品味有同頻線索。"
    if article_id == "western-aspects-mars-mars":
        return "行動節奏有熱度，也可能硬碰硬。"
    if article_id == "western-aspects-mercury-sun":
        return "溝通會碰到理解、自尊與說服方式。"
    if article_id == "western-aspects-mercury-jupiter":
        return "對話能被拉開視角，但要防止誇大承諾。"
    if article_id == "western-aspects-mars-saturn":
        return "想推進時容易碰到對方的界線和壓力感。"
    if article_id == "western-aspects-venus-saturn":
        return "喜歡不一定消失，但表達會變慢、變保守。"
    if article_id == "western-aspects-sun-saturn":
        return "責任感與壓力同時存在，容易變成誰都不輕鬆。"
    if article_id == "western-aspects-sun-moon":
        return "彼此牽動很深，但情緒需求不一定同步。"
    if article_id == "western-aspects-moon-saturn":
        return "情緒被壓住時，對方會先防衛再回應。"
    if article_id == "western-aspects-moon-venus":
        return "有柔軟好感，也容易因安全感不足而反覆確認。"
    if article_id == "western-aspects-saturn-pressure":
        return "關係不是沒感覺，而是壓力正在蓋過反應。"
    if article_id == "western-aspects-mercury-contacts":
        return "訊息與理解方式是主要關卡，適合先看如何降低誤會與防衛。"
    if article_id == "western-aspects-outer-planet-intensity-families":
        return "強度、投射、界線或自由課題明顯，但不能當成命定結果。"
    return "這是可參考的互動線索，不代表單一結論。"


def avoid_from_context(context: dict[str, str], western_id: str | None) -> str:
    stage = context.get("relationship_stage", "")
    risk = context.get("emotional_risk", "")
    if risk in {"desperate", "unsafe-or-overwhelmed"}:
        return "先避開立刻攤牌、崩潰訊息、逼對方承諾。"
    if western_id and "saturn" in western_id:
        return "先避開追問、長文道歉、要求對方馬上給答案。"
    if western_id == "western-aspects-mercury-contacts":
        return "先避開辯解、反覆補充、把一則訊息寫成完整審判。"
    if stage == "broke-up-long":
        return "先避開翻舊帳或一開口就談復合。"
    if stage == "crisis":
        return "先避開在情緒最高點談分開或承諾。"
    return "先避開連續訊息與高壓確認。"


def western_evidence_summary(
    fixture: dict[str, Any],
    western_id: str | None,
) -> str:
    if not western_id:
        return western_unavailable_reason(fixture)
    selected = western_signal(fixture, western_id)
    pressure = strongest_pressure_signal(fixture)
    selected_sentence = aspect_evidence_sentence(selected)
    pressure_sentence = aspect_evidence_sentence(pressure)
    if pressure and pressure.get("id") != western_id:
        return f"西洋合盤這裡看你們靠近時的吸引與壓力。{selected_sentence} 同時，{pressure_sentence}"
    return f"西洋合盤這裡看你們靠近時，情緒、吸引與防衛會怎麼互相觸發。{selected_sentence}"


def western_evidence_points(
    fixture: dict[str, Any],
    context: dict[str, str],
    western_id: str | None,
) -> list[dict[str, str]]:
    if not western_id:
        return [
            {
                "label": "資料完整度",
                "title": "西洋合盤暫不作主判斷",
                "body": western_unavailable_reason(fixture),
            },
            {
                "label": "目前用法",
                "title": "先以出生資料完整度判斷",
                "body": "目前資料不足時，先用出生資料完整度、關係階段與現實互動做保守判斷。",
            },
            {
                "label": "提醒",
                "title": "補足資料後再看相位",
                "body": "若補上可定位城市與出生時間，這份解讀可以納入相位、宮位與時間窗的可用部分。",
            },
        ]
    pressure = strongest_pressure_signal(fixture)
    pressure_id = str(pressure.get("id")) if pressure else western_id
    return [
        {
            "label": "牽動",
            "title": article_title(western_id, {}),
            "body": western_therefore(western_id),
        },
        {
            "label": "壓力",
            "title": WESTERN_CHIP_LABELS.get(pressure_id, "Saturn pressure"),
            "body": western_evidence_meaning(pressure_id),
        },
        {
            "label": "用法",
            "title": "先看能不能放輕",
            "body": avoid_from_context(context, pressure_id),
        },
    ]


def western_visual(fixture: dict[str, Any], western_id: str | None) -> dict[str, str | dict[str, str]]:
    selected = western_signal(fixture, western_id)
    if not selected:
        return {
            "title": "西洋合盤資料不足",
            "personA": {
                "point": "Moon",
                "label": "你：星盤資料",
                "caption": "可計算本命盤",
            },
            "personB": {
                "point": "Sun",
                "label": "對方：星盤資料",
                "caption": "需補足定位或時間",
            },
            "aspect": "暫不判斷",
            "orb": "未計算",
            "summary": western_unavailable_reason(fixture),
            "climateTitle": "合盤資料狀態",
            "climateHeadline": "先不硬判斷",
            "climateSummary": "目前不把缺失的西洋相位寫成關係結論。",
            "disclaimer": "西洋合盤需要可定位出生城市；月亮、上升、宮位也會受出生時間影響。",
        }
    evidence = (selected.get("evidence") if selected else None) or [{}]
    primary = evidence[0] or {}
    point_a = str(primary.get("person_a_point") or "Moon")
    point_b = str(primary.get("person_b_point") or "Sun")
    aspect = str(primary.get("aspect") or "Square")
    orb = primary.get("orb")
    orb_text = f"角度差約 {float(orb):.2f}°" if isinstance(orb, (int, float)) else "角度差未標示"
    aspect_label = ASPECT_LABELS.get(aspect, aspect)
    signal_title = article_title(western_id, {})
    therefore = western_therefore(western_id)
    summary = therefore[2:] if therefore.startswith("所以") else therefore

    return {
        "title": signal_title,
        "personA": {
            "point": point_a,
            "label": f"你：{POINT_LABELS.get(point_a, point_a)}",
            "caption": POINT_TRAITS.get(point_a, "需要放回本命盤判斷"),
        },
        "personB": {
            "point": point_b,
            "label": f"對方：{POINT_LABELS.get(point_b, point_b)}",
            "caption": POINT_TRAITS.get(point_b, "需要放回本命盤判斷"),
        },
        "aspect": aspect_label,
        "orb": orb_text,
        "summary": summary,
        "climateTitle": "關係壓力氣候",
        "climateHeadline": "有牽動，也有壓力",
        "climateSummary": "不是沒感覺，而是壓力讓表達變慢、變保守。",
        "disclaimer": "這是合盤相位快速摘要；這份解讀會一起看宮位可用性、容許度、行運時間窗與雙方本命盤背景。",
    }


def strongest_western_relationship_signal_id(fixture: dict[str, Any], fallback_id: str | None) -> str | None:
    signals = fixture.get("candidate_signals", {}).get("western_signals") or []
    if signals:
        return str(max(signals, key=lambda signal: float(signal.get("strength", 0))).get("id"))
    return fallback_id


def normalized_case_confidence(value: Any, fallback: str = "medium") -> str:
    text = str(value or fallback)
    return text if text in {"low", "medium", "high"} else fallback


def western_only_text(value: Any) -> str:
    return (
        str(value or "")
        .replace("八字時間層", "本命需求與合盤主訊號")
        .replace("八字", "星盤")
        .replace("日主", "本命盤")
        .replace("四柱", "基礎盤")
        .replace("配偶星", "關係指標")
    )


def western_birth_data_quality(fixture: dict[str, Any], person: str) -> dict[str, Any]:
    chart = western_chart(fixture, person)
    label = PERSON_LABELS.get(person, person)
    status = str(chart.get("status") or "skipped")
    time_known = western_time_known(fixture, person)
    location_known = western_location_known(fixture, person)
    houses_allowed = western_houses_allowed(fixture, person)
    if status != "calculated":
        precision = "unavailable"
    elif not time_known:
        precision = "date_only"
    elif not location_known:
        precision = "location_fallback"
    else:
        precision = "exact_time"
    return {
        "role": person,
        "label": label,
        "precision": precision,
        "timeKnown": time_known,
        "locationKnown": location_known,
        "housesAllowed": houses_allowed,
        "moonConfidence": western_moon_confidence(fixture, person),
        "warnings": [str(item) for item in chart.get("warnings") or []],
    }


def western_overall_input_quality(person_a: dict[str, Any], person_b: dict[str, Any]) -> str:
    precisions = {person_a.get("precision"), person_b.get("precision")}
    if "unavailable" in precisions:
        return "low"
    if precisions == {"exact_time"}:
        return "high"
    return "medium"


def western_calculation_settings(fixture: dict[str, Any], context: dict[str, str]) -> dict[str, Any]:
    engine_versions = fixture.get("debug", {}).get("engine_versions") or {}
    transits = fixture.get("western", {}).get("transits", {}) or {}
    analysis_date = context.get("analysis_date") or transits.get("target_date")
    analysis_time = transits.get("target_time")
    analysis_timezone = context.get("analysis_timezone") or transits.get("timezone")
    return {
        "engine": "immanuel",
        "engineVersion": engine_versions.get("immanuel"),
        "zodiac": "tropical",
        "houseSystem": "placidus",
        "aspectPolicy": "relationship-v1",
        "timingMethod": "western-current-transits-v1",
        "analysisDate": analysis_date,
        "analysisDateTime": context.get("analysis_datetime") or (f"{analysis_date}T{analysis_time}" if analysis_date and analysis_time else None),
        "analysisTimezone": analysis_timezone,
        "timingPrecision": transits.get("datetime_precision") or ("analysis_datetime" if context.get("analysis_datetime") else "analysis_date_noon_fallback"),
    }


def western_precision_gate_for_points(
    fixture: dict[str, Any],
    point_a: str,
    point_b: str,
    eligible: bool = True,
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    points = {point_a, point_b}
    requires_birth_time = bool(points.intersection({"Moon", "Asc", "Desc"}))
    requires_known_place = bool(points.intersection({"Asc", "Desc"}))
    if not eligible:
        display = "blocked"
        reason = western_guardrail_reason(
            structured_kb,
            "western-guardrail-aspect-ineligible",
            "此相位涉及出生時間或角度點，資料精度不足，不能作為本次判斷核心。",
        )
    elif requires_known_place and not all(western_houses_allowed(fixture, person) for person in ("person_a", "person_b")):
        display = "blocked"
        reason = western_guardrail_reason(
            structured_kb,
            "western-guardrail-aspect-angle-place-block",
            "上升/下降與宮位需要雙方可靠出生時間與出生城市。",
        )
    elif requires_birth_time and not all(western_time_known(fixture, person) for person in ("person_a", "person_b")):
        display = "allowed_with_uncertainty"
        reason = western_guardrail_reason(
            structured_kb,
            "western-guardrail-aspect-moon-time-uncertain",
            "月亮相關訊號受出生時間影響，本次需保守判讀。",
        )
    else:
        display = "allowed"
        reason = western_guardrail_reason(
            structured_kb,
            "western-guardrail-aspect-default-allowed",
            "資料精度足以作為本次西洋合盤證據。",
        )
    return {
        "requiresBirthTime": requires_birth_time,
        "requiresKnownPlace": requires_known_place,
        "display": display,
        "reason": reason,
    }


def western_aspect_evidence_items(
    fixture: dict[str, Any],
    category: str,
    structured_kb: dict[str, Any] | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, aspect in enumerate(western_aspects_for_category(fixture, category)[:limit]):
        point_a = str(aspect.get("person_a_point") or "")
        point_b = str(aspect.get("person_b_point") or "")
        aspect_type = str(aspect.get("aspect") or "")
        strength = western_aspect_strength(aspect)
        contact_type = western_aspect_contact_type(aspect)
        reading_role = western_aspect_reading_role(aspect, category)
        source = western_aspect_article_id(aspect)
        aspect_atom = western_atom_for_source_article(structured_kb, source)
        contact_modifier = western_aspect_contact_modifier(aspect, structured_kb)
        pair_contact_template = western_aspect_pair_contact_template(aspect, structured_kb)
        items.append(
            {
                "id": f"{category}-{index + 1}",
                "atomId": aspect_atom.get("id"),
                "claimIds": aspect_atom.get("claim_ids") or [],
                "category": category,
                "personAPoint": point_a,
                "personBPoint": point_b,
                "aspect": aspect_type,
                "aspectLabel": ASPECT_LABELS.get(aspect_type, aspect_type),
                "orb": aspect.get("orb"),
                "maxOrb": aspect.get("max_orb"),
                "applying": bool(aspect.get("applying")),
                "strength": round(strength, 3),
                "clusterWeight": round(strength + (0.05 if bool(aspect.get("applying")) else 0), 3),
                "contactType": contact_type,
                "contactModifier": contact_modifier,
                "contactModifierLabel": contact_modifier.get("label"),
                "contactModifierMeaning": contact_modifier.get("interpretation"),
                "pairContactTemplate": pair_contact_template,
                "pairContactTemplateLabel": (pair_contact_template or {}).get("label"),
                "pairContactTemplateMeaning": (pair_contact_template or {}).get("interpretation"),
                "readingRole": reading_role,
                "technical": western_aspect_sentence(aspect),
                "emotionalMeaning": " ".join(
                    [
                        western_category_emotional_meaning(category),
                        str(contact_modifier.get("interpretation") or ""),
                        str((pair_contact_template or {}).get("interpretation") or ""),
                        reading_role,
                    ]
                ).strip(),
                "doesNotProve": western_category_does_not_prove(category),
                "confidence": "high" if strength >= 0.72 else "medium",
                "source": source,
                "precision": western_precision_gate_for_points(
                    fixture,
                    point_a,
                    point_b,
                    bool(aspect.get("eligible_for_signal", True)),
                    structured_kb,
                ),
            }
        )
    return items


def western_house_overlay_layer_status(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    precision_gate = western_house_angle_precision_gate(fixture)
    if not all(western_time_known(fixture, person) for person in ("person_a", "person_b")):
        return {
            "status": "blocked_by_birth_time",
            "reason": western_guardrail_reason(
                structured_kb,
                "western-guardrail-house-overlay-time-block",
                "house overlays require reliable birth times for both people.",
            ),
            "source": WESTERN_PRECISION_SOURCE,
            "claimIds": HOUSE_ANGLE_PRECISION_CLAIM_IDS,
            "precisionGate": precision_gate,
        }
    if not all(western_location_known(fixture, person) for person in ("person_a", "person_b")):
        return {
            "status": "blocked_by_location",
            "reason": western_guardrail_reason(
                structured_kb,
                "western-guardrail-house-overlay-location-block",
                "house overlays require reliable birth cities/coordinates for both people.",
            ),
            "source": WESTERN_PRECISION_SOURCE,
            "claimIds": HOUSE_ANGLE_PRECISION_CLAIM_IDS,
            "precisionGate": precision_gate,
        }
    return {
        "status": "not_available",
        "reason": western_guardrail_reason(
            structured_kb,
            "western-guardrail-house-overlay-not-available",
            "house overlay calculation is not wired into the Western case file yet.",
        ),
        "source": WESTERN_PRECISION_SOURCE,
        "claimIds": HOUSE_ANGLE_PRECISION_CLAIM_IDS,
        "precisionGate": {
            **precision_gate,
            "houseOverlayCalculationAvailable": False,
        },
    }


def western_transit_precision_gate(
    trigger: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    natal_point = str(trigger.get("natal_point") or "")
    requires_birth_time = natal_point == "Moon"
    eligible = bool(trigger.get("eligible_for_timing", True))
    if not eligible:
        display = "blocked"
        reason = western_guardrail_reason(
            structured_kb,
            "western-guardrail-transit-moon-block",
            "此行運觸發需要更可靠出生時間，不能作為本次 timing 判斷。",
        )
    elif requires_birth_time:
        display = "allowed"
        reason = western_guardrail_reason(
            structured_kb,
            "western-guardrail-transit-moon-allowed",
            "月亮 timing 已通過出生時間精度檢查。",
        )
    else:
        display = "allowed"
        reason = western_guardrail_reason(
            structured_kb,
            "western-guardrail-transit-default-allowed",
            "此行運觸發不依賴宮位或上升/下降。",
        )
    return {
        "requiresBirthTime": requires_birth_time,
        "requiresKnownPlace": False,
        "display": display,
        "reason": reason,
    }


def western_transit_evidence_items(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    profile = western_timing_profile(fixture)
    triggers = profile.get("relationship_triggers") or []
    confidence = normalized_case_confidence(profile.get("confidence"), "low")
    items: list[dict[str, Any]] = []
    for index, trigger in enumerate(triggers[:limit]):
        if not isinstance(trigger, dict):
            continue
        person = str(trigger.get("person") or "")
        transit_point = str(trigger.get("transit_point") or "")
        natal_point = str(trigger.get("natal_point") or "")
        aspect_type = str(trigger.get("aspect") or "")
        person_label = PERSON_LABELS.get(person, person)
        category_label = str(trigger.get("category_label") or "行運觸發")
        if category_label == "背景行運":
            category_label = "整體節奏"
        items.append(
            {
                "id": f"current-transit-{index + 1}",
                "person": person,
                "label": f"{person_label}的{category_label}",
                "transitPoint": transit_point,
                "natalPoint": natal_point,
                "aspect": aspect_type,
                "orb": trigger.get("orb"),
                "category": trigger.get("category"),
                "technical": western_only_text(trigger.get("technical_summary") or western_transit_aspect_sentence(trigger)),
                "emotionalMeaning": western_only_text(trigger.get("emotional_meaning") or profile.get("relationship_meaning") or ""),
                "doesNotProve": "行運只支援行動窗口與心理天氣，不保證某天一定聯絡或復合。",
                "confidence": confidence,
                "source": "western-current-transits-v1",
                "precision": western_transit_precision_gate(trigger, structured_kb),
            }
        )
    return items


def western_confidence_strength(confidence: Any) -> float:
    return {"high": 0.82, "medium": 0.62, "low": 0.36}.get(normalized_case_confidence(confidence, "low"), 0.36)


def western_evidence_cluster(
    category: str,
    items: list[dict[str, Any]],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or WESTERN_ASPECT_CATEGORY_LABELS.get(category, "合盤證據群組"))
    source = str(atom.get("source_article_id") or (WESTERN_REPAIR_SOURCE if category == "repair" else WESTERN_CLUSTER_SOURCE))
    valid_items = [item for item in items if isinstance(item, dict)]
    if not valid_items:
        return {
            "category": category,
            "label": label,
            "atomId": atom.get("id"),
            "claimIds": atom.get("claim_ids") or [],
            "itemCount": 0,
            "strongestStrength": 0,
            "averageStrength": 0,
            "dominantContactType": "none",
            "dominantContactModifier": None,
            "contactModifierSummary": "",
            "strongestEvidenceId": None,
            "summary": str(interpretation_atom.get("empty_summary") or f"本次沒有足夠可展示的{label}證據。"),
            "interpretation": str(interpretation_atom.get("interpretation") or f"{label}不能作為本次主判斷，敘事需要改用其他西洋證據層。"),
            "doesNotProve": str(interpretation_atom.get("does_not_prove") or western_category_does_not_prove(category)),
            "confidence": "low",
            "source": source,
        }

    sorted_items = sorted(valid_items, key=lambda item: float(item.get("clusterWeight") or item.get("strength") or 0), reverse=True)
    strongest = sorted_items[0]
    strongest_modifier = strongest.get("contactModifier") if isinstance(strongest.get("contactModifier"), dict) else None
    strengths = [float(item.get("strength") or 0) for item in sorted_items]
    strongest_strength = max(strengths or [0])
    average_strength = sum(strengths) / max(1, len(strengths))
    contact_counts: dict[str, float] = {}
    for item in sorted_items:
        contact_type = str(item.get("contactType") or "other")
        contact_counts[contact_type] = contact_counts.get(contact_type, 0) + float(item.get("clusterWeight") or item.get("strength") or 0.1)
    dominant_contact_type = max(contact_counts, key=contact_counts.get) if contact_counts else "other"
    technical = str(strongest.get("technical") or "")
    count_text = f"{len(sorted_items)} 個可展示相位"
    if interpretation_atom.get("interpretation"):
        interpretation = str(interpretation_atom["interpretation"])
    elif category == "attraction":
        interpretation = "牽動存在，但仍需由情緒安全與壓力群組判斷是否能穩定表達。"
    elif category == "emotionalSafety":
        interpretation = "此群組用來判斷親近時能否被接住，以及冷淡是否可能來自安全感防衛。"
    elif category == "pressure":
        interpretation = "此群組是卡住機制的主要來源；壓力高不等於沒感覺，但會影響回應速度。"
    elif category == "communication":
        interpretation = "此群組用來判斷訊息、語氣與理解方式是否容易讓雙方失焦。"
    elif category == "repair":
        interpretation = "此群組只代表有協調入口；是否能修復仍要看壓力下降與 timing 氣候。"
    else:
        interpretation = "此群組提供本次合盤的互動功能分類。"
    if dominant_contact_type == "hard" and category in {"pressure", "emotionalSafety", "communication"}:
        interpretation = f"{interpretation} 本次 hard contact 較明顯，敘事需要降低 certainty。"
    elif dominant_contact_type == "soft" and category == "repair":
        interpretation = f"{interpretation} soft contact 可作為條件式機會，不可寫成保證。"
    confidence = "high" if strongest_strength >= 0.72 else "medium"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": len(sorted_items),
        "strongestStrength": round(strongest_strength, 3),
        "averageStrength": round(average_strength, 3),
        "dominantContactType": dominant_contact_type,
        "dominantContactModifier": strongest_modifier,
        "contactModifierSummary": str((strongest_modifier or {}).get("interpretation") or ""),
        "strongestEvidenceId": strongest.get("id"),
        "summary": str(interpretation_atom.get("summary_template") or "{label}有{item_count}個可展示相位；主訊號是：{technical}。").format(
            label=label,
            item_count=len(sorted_items),
            technical=technical,
            count_text=count_text,
        ),
        "interpretation": interpretation,
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or western_category_does_not_prove(category)),
        "confidence": confidence,
        "source": source,
    }


def western_flat_synastry_items(synastry_layer: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category_items in synastry_layer.values():
        if not isinstance(category_items, list):
            continue
        for item in category_items:
            if not isinstance(item, dict):
                continue
            key = "|".join(
                str(item.get(field) or "")
                for field in ("personAPoint", "personBPoint", "aspect", "orb", "source")
            )
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    return sorted(items, key=lambda item: float(item.get("clusterWeight") or item.get("strength") or 0), reverse=True)


def western_aspect_contact_modifier_cluster(
    synastry_layer: dict[str, list[dict[str, Any]]],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "aspectContactModifier"
    fallback_atom = western_atom_for_category(structured_kb, category)
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for item in western_flat_synastry_items(synastry_layer):
        modifier = item.get("contactModifier")
        if isinstance(modifier, dict) and modifier.get("type"):
            rows.append((item, modifier))

    if not rows:
        return {
            "category": category,
            "label": WESTERN_ASPECT_CATEGORY_LABELS[category],
            "atomId": fallback_atom.get("id"),
            "claimIds": fallback_atom.get("claim_ids") or [],
            "itemCount": 0,
            "strongestStrength": 0,
            "averageStrength": 0,
            "dominantContactType": "none",
            "summary": "本次沒有可展示的相位接觸修飾。",
            "interpretation": "contact modifier 只在有可展示合盤相位時使用，不能單獨產生關係結論。",
            "doesNotProve": "沒有 contact modifier 不代表沒有感情，也不能補寫未計算相位。",
            "confidence": "low",
            "source": str(fallback_atom.get("source_article_id") or WESTERN_CONTACT_MODIFIER_SOURCE),
        }

    type_counts: dict[str, int] = {}
    type_weights: dict[str, float] = {}
    strengths: list[float] = []
    for item, modifier in rows:
        contact_type = str(modifier.get("type") or "other")
        weight = float(item.get("clusterWeight") or item.get("strength") or 0.1)
        type_counts[contact_type] = type_counts.get(contact_type, 0) + 1
        type_weights[contact_type] = type_weights.get(contact_type, 0) + weight
        strengths.append(float(item.get("strength") or 0))

    strongest_item, strongest_modifier = rows[0]
    dominant_type = max(type_weights, key=type_weights.get)
    count_summary = "、".join(
        f"{contact_type} {type_counts[contact_type]} 個"
        for contact_type in ("hard", "soft", "conjunction", "minor", "other")
        if type_counts.get(contact_type)
    )
    selected_modifiers = []
    for item, modifier in rows[:3]:
        selected_modifiers.append(
            {
                "type": modifier.get("type"),
                "aspect": modifier.get("aspect"),
                "label": modifier.get("label"),
                "source": modifier.get("source"),
                "atomId": modifier.get("atomId"),
                "claimIds": modifier.get("claimIds") or [],
                "interpretation": modifier.get("interpretation"),
                "doesNotProve": modifier.get("doesNotProve"),
                "reducerInstruction": modifier.get("reducerInstruction"),
                "evidenceId": item.get("id"),
                "technical": item.get("technical"),
                "strength": item.get("strength"),
            }
        )

    return {
        "category": category,
        "label": WESTERN_ASPECT_CATEGORY_LABELS[category],
        "atomId": strongest_modifier.get("atomId") or fallback_atom.get("id"),
        "claimIds": strongest_modifier.get("claimIds") or fallback_atom.get("claim_ids") or [],
        "itemCount": len(rows),
        "strongestStrength": round(max(strengths or [0]), 3),
        "averageStrength": round(sum(strengths) / max(1, len(strengths)), 3),
        "dominantContactType": dominant_type,
        "strongestEvidenceId": strongest_item.get("id"),
        "selectedModifiers": selected_modifiers,
        "hasHardContactModifier": type_counts.get("hard", 0) > 0,
        "hasSoftContactModifier": type_counts.get("soft", 0) > 0,
        "hasConjunctionModifier": type_counts.get("conjunction", 0) > 0,
        "hasHardOrConjunctionContact": type_counts.get("hard", 0) + type_counts.get("conjunction", 0) > 0,
        "hasSoftRepairContact": type_counts.get("soft", 0) > 0,
        "summary": f"{WESTERN_ASPECT_CATEGORY_LABELS[category]}：{count_summary or '背景修飾'}；主訊號是：{strongest_item.get('technical') or strongest_modifier.get('label')}。",
        "interpretation": str(strongest_modifier.get("interpretation") or "contact modifier 用來把相位寫成 conjunction/soft/hard 的功能差異。"),
        "doesNotProve": str(strongest_modifier.get("doesNotProve") or "contact modifier 不能單獨證明復合、承諾或結果。"),
        "confidence": "medium" if strengths else "low",
        "source": str(strongest_modifier.get("source") or WESTERN_CONTACT_MODIFIER_SOURCE),
    }


def western_aspect_pair_contact_template_cluster(
    synastry_layer: dict[str, list[dict[str, Any]]],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "aspectPairContactTemplate"
    fallback_atom = western_atom_for_category(structured_kb, category)
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for item in western_flat_synastry_items(synastry_layer):
        template = item.get("pairContactTemplate")
        if isinstance(template, dict) and template.get("label"):
            rows.append((item, template))

    if not rows:
        return {
            "category": category,
            "label": WESTERN_ASPECT_CATEGORY_LABELS[category],
            "atomId": fallback_atom.get("id"),
            "claimIds": fallback_atom.get("claim_ids") or [],
            "itemCount": 0,
            "strongestStrength": 0,
            "averageStrength": 0,
            "dominantContactType": "none",
            "summary": "本次沒有可展示的 planet-pair 接觸模板。",
            "interpretation": "pair-contact template 只在可辨識 planet pair 與 contact type 時使用，不能補寫不存在的相位。",
            "doesNotProve": "沒有 pair template 不代表沒有關係牽動，也不能用模板替代實際合盤證據。",
            "confidence": "low",
            "source": str(fallback_atom.get("source_article_id") or WESTERN_PAIR_CONTACT_TEMPLATE_SOURCE),
        }

    type_counts: dict[str, int] = {}
    strengths: list[float] = []
    selected_templates = []
    for item, template in rows:
        contact_type = str(template.get("contactType") or item.get("contactType") or "other")
        type_counts[contact_type] = type_counts.get(contact_type, 0) + 1
        strengths.append(float(item.get("strength") or 0))
        points = sorted([str(item.get("personAPoint") or ""), str(item.get("personBPoint") or "")])
        selected_templates.append(
            {
                "id": template.get("id"),
                "label": template.get("label"),
                "source": template.get("source"),
                "atomId": template.get("atomId"),
                "claimIds": template.get("claimIds") or [],
                "contactType": contact_type,
                "pairKey": "-".join(point for point in points if point),
                "interpretation": template.get("interpretation"),
                "doesNotProve": template.get("doesNotProve"),
                "evidenceId": item.get("id"),
                "technical": item.get("technical"),
                "strength": item.get("strength"),
            }
        )

    strongest_item, strongest_template = rows[0]
    points = {str(strongest_item.get("personAPoint") or ""), str(strongest_item.get("personBPoint") or "")}
    dominant_type = max(type_counts, key=type_counts.get)
    return {
        "category": category,
        "label": WESTERN_ASPECT_CATEGORY_LABELS[category],
        "atomId": strongest_template.get("atomId") or fallback_atom.get("id"),
        "claimIds": strongest_template.get("claimIds") or fallback_atom.get("claim_ids") or [],
        "itemCount": len(rows),
        "strongestStrength": round(max(strengths or [0]), 3),
        "averageStrength": round(sum(strengths) / max(1, len(strengths)), 3),
        "dominantContactType": dominant_type,
        "strongestEvidenceId": strongest_item.get("id"),
        "dominantPairKey": "-".join(sorted(point for point in points if point)),
        "selectedTemplates": selected_templates[:3],
        "hasPairTemplate": True,
        "hasHardPairTemplate": type_counts.get("hard", 0) > 0,
        "hasSoftPairTemplate": type_counts.get("soft", 0) > 0,
        "hasConjunctionPairTemplate": type_counts.get("conjunction", 0) > 0,
        "hasSaturnPairTemplate": "Saturn" in points,
        "hasMercuryPairTemplate": "Mercury" in points,
        "hasMoonPairTemplate": "Moon" in points,
        "summary": f"{WESTERN_ASPECT_CATEGORY_LABELS[category]}：{strongest_template.get('label') or '可展示模板'}；{strongest_item.get('technical') or ''}。",
        "interpretation": str(strongest_template.get("interpretation") or "pair-contact template 用來把相位翻成關係功能，不替代整體判斷。"),
        "doesNotProve": str(strongest_template.get("doesNotProve") or "pair-contact template 不保證對方回覆、承諾或復合。"),
        "confidence": "medium" if strengths else "low",
        "source": str(strongest_template.get("source") or WESTERN_PAIR_CONTACT_TEMPLATE_SOURCE),
    }


def western_current_transits_cluster(
    timing_items: list[dict[str, Any]],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "currentTransits"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "當下行運氣候")
    source = str(atom.get("source_article_id") or "western-transits-timing-window")
    valid_items = [item for item in timing_items if isinstance(item, dict)]
    allowed_items = [item for item in valid_items if (item.get("precision") or {}).get("display") != "blocked"]
    blocked_items = [item for item in valid_items if (item.get("precision") or {}).get("display") == "blocked"]

    if not valid_items:
        return {
            "category": category,
            "label": label,
            "atomId": atom.get("id"),
            "claimIds": atom.get("claim_ids") or [],
            "itemCount": 0,
            "allowedCount": 0,
            "blockedCount": 0,
            "strongestStrength": 0,
            "averageStrength": 0,
            "dominantContactType": "none",
            "strongestEvidenceId": None,
            "hasAllowedTiming": False,
            "summary": str(interpretation_atom.get("empty_summary") or "本次沒有足夠可展示的當下行運觸發。"),
            "interpretation": str(interpretation_atom.get("interpretation") or "行運只支援當下氣候與行動節奏，不提供事件保證。"),
            "doesNotProve": str(interpretation_atom.get("does_not_prove") or "行運不保證某天一定聯絡或復合。"),
            "confidence": "low",
            "source": source,
        }

    scored_items = sorted(
        valid_items,
        key=lambda item: western_confidence_strength(item.get("confidence")) * (0.35 if (item.get("precision") or {}).get("display") == "blocked" else 1),
        reverse=True,
    )
    strongest = scored_items[0]
    strengths = [
        western_confidence_strength(item.get("confidence")) * (0.35 if (item.get("precision") or {}).get("display") == "blocked" else 1)
        for item in valid_items
    ]
    strongest_strength = max(strengths or [0])
    average_strength = sum(strengths) / max(1, len(strengths))
    technical = str(strongest.get("technical") or "")
    confidence = "high" if strongest_strength >= 0.75 else "medium" if strongest_strength >= 0.5 else "low"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": len(valid_items),
        "allowedCount": len(allowed_items),
        "blockedCount": len(blocked_items),
        "strongestStrength": round(strongest_strength, 3),
        "averageStrength": round(average_strength, 3),
        "dominantContactType": str(strongest.get("category") or "timing"),
        "strongestEvidenceId": strongest.get("id"),
        "hasAllowedTiming": bool(allowed_items),
        "summary": render_zh_summary(
            str(interpretation_atom.get("summary_template") or "{label}有{item_count}個可展示行運觸發；主訊號是：{technical}。"),
            label=label,
            item_count=len(valid_items),
            technical=technical,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "行運只支援當下氣候與行動節奏，不提供事件保證。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "行運不保證某天一定聯絡或復合。"),
        "confidence": confidence,
        "source": source,
    }


def western_timing_window_scan(fixture: dict[str, Any]) -> dict[str, Any]:
    scan = fixture.get("western", {}).get("analysis", {}).get("timing_window_scan") or {}
    return scan if isinstance(scan, dict) else {}


def western_public_timing_summary(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "本次尚未產生短期行動氣候。"
    replacements = {
        "30-60 天 timing band": "未來三個月行動氣候",
        "better / neutral / avoid timing band": "短期行動氣候",
        "Timing band": "短期行動氣候",
        "timing band": "短期行動氣候",
        "未來掃描偏向": "短期氣候偏向",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"；(?:better|avoid|neutral) 樣本 \d+ 個", "", text)
    text = re.sub(r"better=(\d+)、avoid=(\d+)、neutral=(\d+)", r"低壓窗口 \1、需避開窗口 \2、觀察窗口 \3", text)
    return text


def western_timing_window_scan_public(fixture: dict[str, Any]) -> dict[str, Any]:
    scan = western_timing_window_scan(fixture)
    sample_count = int(scan.get("sample_count") or 0)
    status = str(scan.get("status") or ("calculated" if sample_count else "not_calculated"))
    top_band = str(scan.get("top_band") or "neutral")
    band_counts = {
        "better": int(scan.get("better_count") or 0),
        "neutral": int(scan.get("neutral_count") or 0),
        "avoid": int(scan.get("avoid_count") or 0),
    }
    return {
        "method": str(scan.get("method") or "western-transit-window-scan-v1"),
        "status": status,
        "scanDays": int(scan.get("scan_days") or 0),
        "granularityDays": int(scan.get("granularity_days") or 0),
        "sampleCount": sample_count,
        "topBand": top_band,
        "topBandLabel": TIMING_BAND_LABELS.get(top_band, top_band),
        "bandCounts": band_counts,
        "betterWindowCount": int(scan.get("better_window_count") or 0),
        "avoidWindowCount": int(scan.get("avoid_window_count") or 0),
        "categoryCounts": scan.get("category_counts") if isinstance(scan.get("category_counts"), dict) else {},
        "exactTimingPolicy": exact_timing_policy(),
        "preciseDatesAvailable": False,
        "timingSummary": western_public_timing_summary(scan.get("timing_summary") or scan.get("free_summary")),
    }


def western_timing_summary_float(summary: dict[str, Any], key: str) -> float:
    try:
        return float(summary.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def western_timing_selector_matches(summary: dict[str, Any], atom: dict[str, Any], fallback_categories: set[str]) -> bool:
    selectors = atom.get("selectors") if isinstance(atom.get("selectors"), dict) else {}
    allowed_categories = set(str(item) for item in selectors.get("timing_categories_any") or fallback_categories)
    allowed_bands = set(str(item) for item in selectors.get("window_bands_any") or [])
    allowed_transit_points = set(str(item) for item in selectors.get("transit_points_any") or [])
    allowed_natal_points = set(str(item) for item in selectors.get("natal_points_any") or [])
    profile = summary.get("profile") if isinstance(summary.get("profile"), dict) else {}
    category = str(summary.get("strongest_category") or "")
    band = str(summary.get("band") or "")
    transit_point = str(profile.get("strongest_transit_point") or "")
    natal_point = str(profile.get("strongest_natal_point") or "")
    if allowed_categories and category not in allowed_categories:
        return False
    if allowed_bands and band not in allowed_bands:
        return False
    if allowed_transit_points and transit_point not in allowed_transit_points:
        return False
    if allowed_natal_points and natal_point not in allowed_natal_points:
        return False
    return True


def western_timing_window_count(day_summaries: list[dict[str, Any]], atom: dict[str, Any], fallback_categories: set[str]) -> int:
    count = 0
    previous_matched = False
    for summary in day_summaries:
        matched = western_timing_selector_matches(summary, atom, fallback_categories)
        if matched and not previous_matched:
            count += 1
        previous_matched = matched
    return count


def western_timing_category_window_count(day_summaries: list[dict[str, Any]], categories: set[str]) -> int:
    count = 0
    previous_matched = False
    for summary in day_summaries:
        matched = str(summary.get("strongest_category") or "") in categories
        if matched and not previous_matched:
            count += 1
        previous_matched = matched
    return count


def western_timing_contact_reducer_action(
    *,
    sample_count: int,
    better_count: int,
    avoid_count: int,
    support_signal_count: int,
    caution_signal_count: int,
    has_communication_window: bool,
    has_venus_softening: bool,
) -> tuple[str, str, str, str]:
    if not sample_count:
        return (
            "not_calculated",
            "尚未計算",
            "observe_only",
            "本次沒有足夠未來三個月 timing scan；這份解讀會改用當下行運氣候與合盤壓力回答。",
        )
    if caution_signal_count and (avoid_count >= better_count or caution_signal_count >= support_signal_count):
        return (
            "avoid_push",
            "先避開推進",
            "do_not_push",
            "先不要用長文、追問、攤牌或連續訊息推進；等壓力下降後再看低壓窗口。",
        )
    if support_signal_count and better_count > 0 and support_signal_count > caution_signal_count:
        contact_mode = "short_low_pressure"
        if has_communication_window and has_venus_softening:
            instruction = "可考慮短句、低要求、帶善意的訊息；只測試互動是否能自然接住，不索取答案。"
        elif has_communication_window:
            instruction = "可考慮短句、清楚、可退場的訊息；避免辯論和一次講完所有情緒。"
        else:
            instruction = "可用柔和、不索取承諾的方式釋放善意；不要把好氣氛當成復合保證。"
        return ("low_pressure_message", "低壓短訊息", contact_mode, instruction)
    if support_signal_count:
        return (
            "observe_for_soft_window",
            "先觀察低壓窗口",
            "observe_then_short",
            "有些柔和訊號，但仍不夠乾淨；先觀察對方自然回應，再考慮短訊息。",
        )
    return (
        "observe_only",
        "觀察為主",
        "observe_only",
        "目前 timing 不支持主動推進；先把重點放在讓壓力下降與穩住自己。",
    )


def western_timing_contact_reducer_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "timingContactReducer"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "聯絡 timing 行動 reducer")
    source = str(atom.get("source_article_id") or TIMING_CONTACT_REDUCER_SOURCE)
    scan = western_timing_window_scan(fixture)
    public_scan = western_timing_window_scan_public(fixture)
    day_summaries = [item for item in scan.get("day_summaries") or [] if isinstance(item, dict)]
    category_counts = public_scan.get("categoryCounts") if isinstance(public_scan.get("categoryCounts"), dict) else {}
    band_counts = public_scan.get("bandCounts") if isinstance(public_scan.get("bandCounts"), dict) else {}
    sample_count = int(public_scan.get("sampleCount") or 0)
    better_count = int(band_counts.get("better") or 0)
    avoid_count = int(band_counts.get("avoid") or 0)
    neutral_count = int(band_counts.get("neutral") or 0)

    selected_reducers: list[dict[str, Any]] = []
    selected_claim_ids = [str(claim_id) for claim_id in atom.get("claim_ids") or [] if claim_id]
    for timing_category, config in TIMING_CONTACT_REDUCER_CONFIG.items():
        reducer_sample_count = int(category_counts.get(timing_category) or 0)
        reducer_window_count = western_timing_category_window_count(day_summaries, {timing_category})
        if not reducer_sample_count and not reducer_window_count:
            continue
        source_claim_id = str(config.get("sourceClaimId") or "")
        if source_claim_id:
            selected_claim_ids.append(source_claim_id)
        selected_reducers.append(
            {
                "id": f"timing-contact-reducer-{timing_category}",
                "category": timing_category,
                "label": str(config.get("label") or TIMING_CATEGORY_LABELS.get(timing_category, timing_category)),
                "source": source,
                "sourceClaimId": source_claim_id,
                "polarity": str(config.get("polarity") or "support"),
                "relationshipFunction": str(config.get("relationshipFunction") or ""),
                "sampleCount": reducer_sample_count,
                "windowCount": reducer_window_count,
                "instruction": str(config.get("instruction") or ""),
                "preciseDatesAvailable": False,
            }
        )

    support_signal_count = sum(int(item.get("sampleCount") or 0) for item in selected_reducers if item.get("polarity") == "support")
    caution_signal_count = sum(int(item.get("sampleCount") or 0) for item in selected_reducers if item.get("polarity") == "caution")
    has_communication_window = any(item.get("category") == "communication_window" for item in selected_reducers)
    has_communication_pressure = any(item.get("category") == "communication_pressure" for item in selected_reducers)
    has_venus_softening = any(item.get("category") in {"softening", "relationship_focus"} for item in selected_reducers)
    has_mars_activation_risk = any(item.get("category") == "activation_pressure" for item in selected_reducers)
    has_saturn_boundary_risk = any(item.get("category") == "pressure" for item in selected_reducers)
    action, action_label, contact_mode, contact_instruction = western_timing_contact_reducer_action(
        sample_count=sample_count,
        better_count=better_count,
        avoid_count=avoid_count,
        support_signal_count=support_signal_count,
        caution_signal_count=caution_signal_count,
        has_communication_window=has_communication_window,
        has_venus_softening=has_venus_softening,
    )

    sorted_reducers = sorted(
        selected_reducers,
        key=lambda item: (int(item.get("sampleCount") or 0), int(item.get("windowCount") or 0)),
        reverse=True,
    )
    dominant = sorted_reducers[0] if sorted_reducers else {}
    dominant_category = str(dominant.get("category") or "none")
    dominant_window = (
        f"{TIMING_CATEGORY_LABELS.get(dominant_category, dominant_category)} / {public_scan.get('topBandLabel') or TIMING_BAND_LABELS.get(str(public_scan.get('topBand') or 'neutral'), '觀察為主')}"
        if dominant
        else "無可展示 timing reducer"
    )
    strengths = [
        min(0.92, max(0.24, int(item.get("sampleCount") or 0) / max(sample_count, 1)))
        for item in selected_reducers
    ]
    summary_template = str(
        interpretation_atom.get("summary_template")
        or "{label}建議：{action_label}；主軸是{dominant_window}，支持訊號{support_signal_count}、高壓訊號{caution_signal_count}。"
    )
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": unique(selected_claim_ids),
        "itemCount": len(selected_reducers),
        "sampleCount": sample_count,
        "windowCount": sum(int(item.get("windowCount") or 0) for item in selected_reducers),
        "strongestStrength": round(max(strengths), 3) if strengths else 0,
        "averageStrength": round(sum(strengths) / max(len(strengths), 1), 3),
        "dominantContactType": action,
        "dominantTimingCategory": dominant_category,
        "dominantWindow": dominant_window,
        "recommendedAction": action,
        "recommendedActionLabel": action_label,
        "contactMode": contact_mode,
        "contactInstruction": contact_instruction,
        "avoidInstruction": "避開長文、攤牌、追問、測試、連續訊息與要求立即承諾。",
        "lowPressureInstruction": "若要聯絡，只能短句、低要求、可退場，且不把一次回應當成承諾。",
        "topBand": str(public_scan.get("topBand") or "neutral"),
        "topBandLabel": str(public_scan.get("topBandLabel") or TIMING_BAND_LABELS.get(str(public_scan.get("topBand") or "neutral"), "觀察為主")),
        "betterCount": better_count,
        "neutralCount": neutral_count,
        "avoidCount": avoid_count,
        "supportSignalCount": support_signal_count,
        "cautionSignalCount": caution_signal_count,
        "hasLowPressureContactWindow": action in {"low_pressure_message", "observe_for_soft_window"},
        "hasAvoidPressureWindow": action == "avoid_push",
        "hasMercuryCommunicationWindow": has_communication_window,
        "hasMercuryCommunicationPressure": has_communication_pressure,
        "hasVenusSofteningWindow": has_venus_softening,
        "hasMarsActivationRisk": has_mars_activation_risk,
        "hasSaturnBoundaryRisk": has_saturn_boundary_risk,
        "selectedTimingReducers": sorted_reducers,
        "strongestEvidenceId": str(dominant.get("id") or "") or None,
        "hasAllowedTiming": bool(sample_count),
        "exactTimingPolicy": exact_timing_policy(),
        "preciseDatesAvailable": False,
        "summary": summary_template.format(
            label=label,
            action_label=action_label,
            dominant_window=dominant_window,
            support_signal_count=support_signal_count,
            caution_signal_count=caution_signal_count,
            item_count=len(selected_reducers),
        ),
        "interpretation": western_public_copy(
            interpretation_atom.get("interpretation")
            or "把 Mercury/Venus/Mars/Saturn timing selector 壓成低壓聯絡、觀察、或避開推進；這份解讀不把時機寫成精準承諾日期。"
        ),
        "doesNotProve": str(
            interpretation_atom.get("does_not_prove")
            or "聯絡 timing reducer 不保證回覆、承諾、復合或某日成功，也不能取代訊息內容策略。"
        ),
        "confidence": "medium" if selected_reducers else "low",
        "source": source,
    }


def western_timing_selector_cluster(
    fixture: dict[str, Any],
    category: str,
    fallback_categories: set[str],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or category)
    source = str(atom.get("source_article_id") or "western-transits-timing-selector-windows")
    scan = western_timing_window_scan(fixture)
    day_summaries = [item for item in scan.get("day_summaries") or [] if isinstance(item, dict)]
    matched = [
        summary
        for summary in day_summaries
        if western_timing_selector_matches(summary, atom, fallback_categories)
    ]
    window_count = western_timing_window_count(day_summaries, atom, fallback_categories)
    claim_ids = [str(claim_id) for claim_id in atom.get("claim_ids") or [] if claim_id]
    saturn_boundary = saturn_nonfatal_process_boundary(
        "timing_saturn_pressure",
        evidence_keys=[summary.get("strongest_category") or "pressure" for summary in matched],
    ) if category == "timingSaturnPressure" else None
    if saturn_boundary:
        claim_ids = unique([*claim_ids, *GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS])

    if not matched:
        payload = {
            "category": category,
            "label": label,
            "atomId": atom.get("id"),
            "claimIds": claim_ids,
            "itemCount": 0,
            "windowCount": 0,
            "sampleCount": len(day_summaries),
            "strongestStrength": 0,
            "averageStrength": 0,
            "dominantContactType": "none",
            "dominantTimingCategory": "none",
            "dominantWindow": "",
            "strongestEvidenceId": None,
            "hasAllowedTiming": False,
            "exactTimingPolicy": exact_timing_policy(),
            "preciseDatesAvailable": False,
            "summary": str(interpretation_atom.get("empty_summary") or f"未來三個月掃描內沒有可展示的{label}。"),
            "interpretation": str(interpretation_atom.get("interpretation") or "此 timing cluster 僅支援趨勢，不提供精準日期。"),
            "doesNotProve": str(interpretation_atom.get("does_not_prove") or "Timing 不保證聯絡、承諾或復合。"),
            "confidence": "low",
            "source": source,
        }
        if saturn_boundary:
            payload["saturnProcessBoundary"] = saturn_boundary
            payload["sourceClaimIds"] = GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS
            payload["methodClaimIds"] = GREENE_SATURN_PROCESS_METHOD_CLAIM_IDS
        return payload

    category_counts: dict[str, int] = {}
    band_counts = {"better": 0, "neutral": 0, "avoid": 0}
    strengths: list[float] = []
    for summary in matched:
        timing_category = str(summary.get("strongest_category") or "background")
        band = str(summary.get("band") or "neutral")
        category_counts[timing_category] = category_counts.get(timing_category, 0) + 1
        if band in band_counts:
            band_counts[band] += 1
        strengths.append(min(0.92, max(0.24, abs(western_timing_summary_float(summary, "score")))))

    dominant_category = max(category_counts, key=category_counts.get)
    dominant_band = max(band_counts, key=band_counts.get)
    dominant_window = f"{TIMING_CATEGORY_LABELS.get(dominant_category, dominant_category)} / {TIMING_BAND_LABELS.get(dominant_band, dominant_band)}"
    strongest_strength = max(strengths or [0])
    average_strength = sum(strengths) / max(1, len(strengths))
    summary_template = str(interpretation_atom.get("summary_template") or "{label}掃描到{window_count}個 timing 訊號；主軸是：{dominant_window}。")
    payload = {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": claim_ids,
        "itemCount": len(matched),
        "windowCount": window_count,
        "sampleCount": len(day_summaries),
        "strongestStrength": round(strongest_strength, 3),
        "averageStrength": round(average_strength, 3),
        "dominantContactType": dominant_category,
        "dominantTimingCategory": dominant_category,
        "dominantWindow": dominant_window,
        "topBand": dominant_band,
        "topBandLabel": TIMING_BAND_LABELS.get(dominant_band, dominant_band),
        "bandCounts": band_counts,
        "categoryCounts": dict(sorted(category_counts.items())),
        "strongestEvidenceId": f"{category}-{dominant_category}",
        "hasAllowedTiming": True,
        "exactTimingPolicy": exact_timing_policy(),
        "preciseDatesAvailable": False,
        "summary": summary_template.format(
            label=label,
            window_count=window_count,
            dominant_window=dominant_window,
            item_count=len(matched),
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "此 timing cluster 僅支援趨勢，不提供精準日期。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "Timing 不保證聯絡、承諾或復合。"),
        "confidence": "medium" if category != "timingMoonWeather" and window_count else "low",
        "source": source,
    }
    if saturn_boundary:
        payload["saturnProcessBoundary"] = saturn_boundary
        payload["sourceClaimIds"] = GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS
        payload["methodClaimIds"] = GREENE_SATURN_PROCESS_METHOD_CLAIM_IDS
    return payload


def western_timing_window_band_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "timingWindowBand"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "未來三個月行動氣候")
    source = str(atom.get("source_article_id") or "western-transits-timing-selector-windows")
    public_scan = western_timing_window_scan_public(fixture)
    band_counts = public_scan.get("bandCounts") if isinstance(public_scan.get("bandCounts"), dict) else {}
    sample_count = int(public_scan.get("sampleCount") or 0)
    top_band = str(public_scan.get("topBand") or "neutral")
    top_band_label = str(public_scan.get("topBandLabel") or TIMING_BAND_LABELS.get(top_band, top_band))
    better_count = int(band_counts.get("better") or 0)
    neutral_count = int(band_counts.get("neutral") or 0)
    avoid_count = int(band_counts.get("avoid") or 0)

    if not sample_count:
        return {
            "category": category,
            "label": label,
            "atomId": atom.get("id"),
            "claimIds": atom.get("claim_ids") or [],
            "itemCount": 0,
            "sampleCount": 0,
            "strongestStrength": 0,
            "averageStrength": 0,
            "dominantContactType": "neutral",
            "topBand": "neutral",
            "topBandLabel": TIMING_BAND_LABELS["neutral"],
            "betterCount": 0,
            "neutralCount": 0,
            "avoidCount": 0,
            "betterWindowCount": 0,
            "avoidWindowCount": 0,
            "hasBetterWindow": False,
            "hasAvoidWindow": False,
            "strongestEvidenceId": None,
            "exactTimingPolicy": exact_timing_policy(),
            "preciseDatesAvailable": False,
            "summary": western_public_timing_summary(interpretation_atom.get("empty_summary")),
            "interpretation": str(interpretation_atom.get("interpretation") or "短期行動氣候只提供趨勢，不提供精準日期。"),
            "doesNotProve": str(interpretation_atom.get("does_not_prove") or "短期行動氣候不保證聯絡、承諾或復合。"),
            "confidence": "low",
            "source": source,
        }

    dominant_count = max(better_count, neutral_count, avoid_count)
    strength = max(0.24, min(0.88, dominant_count / max(1, sample_count)))
    summary_template = str(interpretation_atom.get("summary_template") or "{label}：{top_band_label}；低壓窗口 {better_count}、需避開窗口 {avoid_count}、觀察窗口 {neutral_count}。")
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": sample_count,
        "sampleCount": sample_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": top_band,
        "topBand": top_band,
        "topBandLabel": top_band_label,
        "betterCount": better_count,
        "neutralCount": neutral_count,
        "avoidCount": avoid_count,
        "betterWindowCount": int(public_scan.get("betterWindowCount") or 0),
        "avoidWindowCount": int(public_scan.get("avoidWindowCount") or 0),
        "hasBetterWindow": bool(public_scan.get("betterWindowCount")),
        "hasAvoidWindow": bool(public_scan.get("avoidWindowCount")),
        "bandCounts": band_counts,
        "categoryCounts": public_scan.get("categoryCounts") or {},
        "strongestEvidenceId": f"timing-window-band-{top_band}",
        "exactTimingPolicy": exact_timing_policy(),
        "preciseDatesAvailable": False,
        "summary": western_public_timing_summary(summary_template.format(
            label=label,
            top_band_label=top_band_label,
            better_count=better_count,
            avoid_count=avoid_count,
            neutral_count=neutral_count,
            item_count=sample_count,
        )),
        "interpretation": str(interpretation_atom.get("interpretation") or "短期行動氣候只提供趨勢，不提供精準日期。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "短期行動氣候不保證聯絡、承諾或復合。"),
        "confidence": "medium",
        "source": source,
    }


def western_birth_data_quality_cluster(
    input_quality: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "birthDataQuality"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "出生資料精度")
    source = str(atom.get("source_article_id") or WESTERN_PRECISION_SOURCE)
    people = [input_quality.get("personA") or {}, input_quality.get("personB") or {}]
    precisions = [str(person.get("precision") or "unavailable") for person in people]
    exact_time_count = sum(1 for precision in precisions if precision == "exact_time")
    date_only_count = sum(1 for precision in precisions if precision == "date_only")
    location_fallback_count = sum(1 for precision in precisions if precision == "location_fallback")
    unavailable_count = sum(1 for precision in precisions if precision == "unavailable")
    houses_allowed_count = sum(1 for person in people if person.get("housesAllowed"))
    low_moon_count = sum(1 for person in people if person.get("moonConfidence") == "low")
    overall = str(input_quality.get("overall") or "low")
    has_precision_limit = overall != "high"
    precision_risk = {"high": 0.0, "medium": 0.55, "low": 0.9}.get(overall, 0.9)
    confidence = "high" if overall == "high" else "medium" if overall == "medium" else "low"
    precision_labels = {
        "exact_time": "出生時間與城市完整",
        "date_only": "缺出生時間",
        "location_fallback": "缺出生城市",
        "unavailable": "無法計算",
    }
    technical = "；".join(
        f"{person.get('label') or person.get('role')}：{precision_labels.get(str(person.get('precision') or 'unavailable'), '無法計算')}"
        for person in people
    )
    summary_template = str(interpretation_atom.get("summary_template") or "{label}：{technical}。")
    precision_gate = western_house_angle_precision_gate_from_input_quality(input_quality)
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": len(people),
        "strongestStrength": round(precision_risk, 3),
        "averageStrength": round(precision_risk, 3),
        "dominantContactType": "precision_limit" if has_precision_limit else "exact_time",
        "strongestEvidenceId": "input-quality",
        "overallQuality": overall,
        "hasPrecisionLimit": has_precision_limit,
        "exactTimeCount": exact_time_count,
        "dateOnlyCount": date_only_count,
        "locationFallbackCount": location_fallback_count,
        "unavailableCount": unavailable_count,
        "housesAllowedCount": houses_allowed_count,
        "lowMoonConfidenceCount": low_moon_count,
        "houseAnglePrecisionGate": precision_gate,
        "summary": summary_template.format(label=label, technical=technical, item_count=len(people)),
        "interpretation": str(interpretation_atom.get("interpretation") or "缺出生時間或城市時，Moon、Asc/Desc、houses 與 overlays 必須降權或封鎖。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "資料不足不能被補寫成角度點、宮位、overlay 或精準 timing 結論。"),
        "confidence": confidence,
        "source": source,
    }


def western_identity_needs_cluster(
    identity_layer: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "identityNeeds"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "本命關係需求")
    source = str(atom.get("source_article_id") or "western-planets-natal-relationship-needs")
    person_layers = [identity_layer.get("personA") or {}, identity_layer.get("personB") or {}]
    all_needs: list[dict[str, Any]] = []
    for person in person_layers:
        role = str(person.get("role") or "")
        role_label = str(person.get("label") or role or "person")
        for need in person.get("needs") or []:
            if not isinstance(need, dict):
                continue
            all_needs.append({**need, "role": role, "roleLabel": role_label})

    if not all_needs:
        return {
            "category": category,
            "label": label,
            "atomId": atom.get("id"),
            "claimIds": atom.get("claim_ids") or [],
            "itemCount": 0,
            "personACount": 0,
            "personBCount": 0,
            "lowConfidenceCount": 0,
            "strongestStrength": 0,
            "averageStrength": 0,
            "dominantContactType": "none",
            "strongestEvidenceId": None,
            "hasBothPeopleNeeds": False,
            "summary": str(interpretation_atom.get("empty_summary") or "本次沒有足夠可展示的本命關係需求。"),
            "interpretation": str(interpretation_atom.get("interpretation") or "先看各自的情緒安全、喜歡方式、行動節奏與防衛方式，避免把合盤相位孤立解讀。"),
            "doesNotProve": str(interpretation_atom.get("does_not_prove") or "本命需求用來看兩人各自需要什麼條件，下一步仍回到實際回應與合盤互動。"),
            "confidence": "low",
            "source": source,
        }

    person_a_count = sum(1 for need in all_needs if need.get("role") == "person_a")
    person_b_count = sum(1 for need in all_needs if need.get("role") == "person_b")
    low_confidence_count = sum(1 for need in all_needs if need.get("confidence") == "low")
    point_counts = {}
    for need in all_needs:
        point = str(need.get("point") or "need")
        point_counts[point] = point_counts.get(point, 0) + 1
    dominant_point = max(point_counts, key=point_counts.get) if point_counts else "need"
    strengths = [western_confidence_strength(need.get("confidence")) for need in all_needs]
    strongest_strength = max(strengths or [0])
    average_strength = sum(strengths) / max(1, len(strengths))
    def needs_for(role: str, limit: int = 2) -> list[str]:
        return [
            str(need.get("label"))
            for need in all_needs
            if need.get("role") == role and need.get("label")
        ][:limit]

    person_a_labels = "、".join(needs_for("person_a")) or "本命需求不足"
    person_b_labels = "、".join(needs_for("person_b")) or "本命需求不足"
    remaining_count = max(0, len(all_needs) - len(needs_for("person_a")) - len(needs_for("person_b")))
    technical = f"你：{person_a_labels}；對方：{person_b_labels}"
    if remaining_count:
        technical = f"{technical}；另有 {remaining_count} 個需求點"
    confidence = "high" if low_confidence_count == 0 and person_a_count and person_b_count else "medium" if all_needs else "low"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": len(all_needs),
        "personACount": person_a_count,
        "personBCount": person_b_count,
        "lowConfidenceCount": low_confidence_count,
        "strongestStrength": round(strongest_strength, 3),
        "averageStrength": round(average_strength, 3),
        "dominantContactType": dominant_point,
        "strongestEvidenceId": f"identity-need-{dominant_point}",
        "hasBothPeopleNeeds": bool(person_a_count and person_b_count),
        "summary": str(interpretation_atom.get("summary_template") or "{label}有{item_count}個可展示本命點；主訊號是：{technical}。").format(
            label=label,
            item_count=len(all_needs),
            technical=technical,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "先看各自的情緒安全、喜歡方式、行動節奏與防衛方式，避免把合盤相位孤立解讀。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "本命需求用來看兩人各自需要什麼條件，下一步仍回到實際回應與合盤互動。"),
        "confidence": confidence,
        "source": source,
    }


def western_method_order_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "methodOrder"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "西洋關係閱讀順序")
    source = str(atom.get("source_article_id") or "western-synastry-method-order")
    technical = "本命關係潛力 -> 初步比較 -> 交互相位 -> 壓力/修復/timing -> 問題答案"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": 5,
        "strongestStrength": 0.92,
        "averageStrength": 0.92,
        "dominantContactType": "method_order",
        "strongestEvidenceId": "suskin-method-order",
        "hasNatalBeforeSynastry": True,
        "hasQuestionLast": True,
        "hasRelationshipChartDeferred": True,
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=5,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "問題答案必須由 case file 推導。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "方法順序不能保證事件。"),
        "confidence": "high",
        "source": source,
    }


def western_static_atom_cluster(
    category: str,
    *,
    default_label: str,
    default_technical: str,
    default_interpretation: str,
    default_does_not_prove: str,
    default_confidence: str = "medium",
    item_count: int = 1,
    dominant_contact_type: str = "method",
    strongest_evidence_id: str | None = None,
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or default_label)
    source = str(atom.get("source_article_id") or category)
    summary_template = str(interpretation_atom.get("summary_template") or "{label}：{technical}。")
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": item_count,
        "strongestStrength": 0.82,
        "averageStrength": 0.82,
        "dominantContactType": dominant_contact_type,
        "strongestEvidenceId": strongest_evidence_id or category,
        "summary": summary_template.format(
            label=label,
            technical=default_technical,
            item_count=item_count,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or default_interpretation),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or default_does_not_prove),
        "confidence": default_confidence,
        "source": source,
    }


def western_natal_symbol_foundation_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return western_static_atom_cluster(
        "natalSymbolFoundation",
        default_label="占星符號基礎",
        default_technical="Hand 符號系統先區分 planets、angles、aspects、houses、signs，再合成關係答案",
        default_interpretation="先理解可計算符號與證據層，再把關係問題轉成可觀察互動、壓力和時機判斷。",
        default_does_not_prove="符號基礎不能替代實際合盤、精度與現實互動資料。",
        item_count=5,
        dominant_contact_type="symbol_foundation",
        strongest_evidence_id="hand-symbol-foundation",
        structured_kb=structured_kb,
    )


def western_planetary_functions_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return western_static_atom_cluster(
        "planetaryFunctions",
        default_label="行星功能基礎",
        default_technical="Sun/Moon/Mercury/Venus/Mars/Saturn 分別支援自我、安全感、溝通、喜歡、行動與界線壓力",
        default_interpretation="行星代表心理功能與能量，不是具體人物、事件保證或第三方內心。",
        default_does_not_prove="任何單一行星功能都不能單獨證明愛、不愛、承諾或復合。",
        item_count=6,
        dominant_contact_type="planetary_function",
        strongest_evidence_id="hand-planetary-functions",
        structured_kb=structured_kb,
    )


def western_sign_classification_foundation_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return western_static_atom_cluster(
        "signClassificationFoundation",
        default_label="星座結構基礎",
        default_technical="signs 由 element、modality/cross、polarity 等結構組合，先修飾行星功能再進入合盤",
        default_interpretation="星座不是單一人格標籤；它用元素、三模式與其他分類修飾行星功能，幫助建立可組合的關係語義。",
        default_does_not_prove="星座結構不能單獨證明相容、承諾、聯絡或復合。",
        item_count=3,
        dominant_contact_type="sign_structure",
        strongest_evidence_id="hand-sign-classification-foundation",
        structured_kb=structured_kb,
    )


def western_element_style_foundation_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return western_static_atom_cluster(
        "elementStyleFoundation",
        default_label="元素風格基礎",
        default_technical="fire/earth/air/water 描述行動、穩定、思考/社交與情緒共感等經驗風格",
        default_interpretation="元素是行為與經驗方式，不是相容 verdict；它應作為早期風格層，不能壓過行星、相位與現實互動。",
        default_does_not_prove="元素風格不能單獨證明兩人合不合、誰愛誰、或關係會不會回來。",
        item_count=5,
        dominant_contact_type="element_style",
        strongest_evidence_id="hand-element-style-foundation",
        structured_kb=structured_kb,
    )


def western_modality_response_foundation_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return western_static_atom_cluster(
        "modalityResponseFoundation",
        default_label="三模式反應基礎",
        default_technical="cardinal/fixed/mutable 分別描述啟動、維持、調整，以及壓力下的反制、抵抗、間接轉向",
        default_interpretation="三模式說明關係裡的啟動、維持與調整節奏；適合拆互動循環，不適合下好壞判決。",
        default_does_not_prove="三模式不能單獨證明責任歸屬、承諾或關係結局。",
        item_count=2,
        dominant_contact_type="modality_response",
        strongest_evidence_id="hand-modality-response-foundation",
        structured_kb=structured_kb,
    )


def western_planet_sign_style_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "planetSignStyle"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "行星落星座語氣")
    source = str(atom.get("source_article_id") or "western-individual-sign-meanings-hand")
    points = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn"]
    details: list[str] = []
    selected_signs: list[str] = []
    selected_claim_ids: list[str] = []
    low_confidence_count = 0
    for person, role_label in (("person_a", "你"), ("person_b", "對方")):
        for point in points:
            obj = western_object(fixture, person, point)
            if not obj:
                continue
            sign = str(obj.get("sign") or "")
            sign_label = SIGN_LABELS.get(sign, sign or "未知星座")
            sign_style = SIGN_RUNTIME_STYLES.get(sign, "需要放回本命盤與行星功能判斷")
            point_label = POINT_LABELS.get(point, point)
            details.append(f"{role_label}{point_label}{sign_label}：{sign_style}")
            if sign:
                selected_signs.append(sign)
            claim_id = SIGN_CLAIM_IDS.get(sign)
            if claim_id:
                selected_claim_ids.append(claim_id)
            if point == "Moon" and western_moon_confidence(fixture, person) == "low":
                low_confidence_count += 1
    selected_claim_ids = unique(selected_claim_ids)
    item_count = len(details)
    technical = "；".join(details[:6]) if details else "行星落星座資料不足"
    strength = 0.76 if item_count >= 8 else 0.62 if item_count >= 4 else 0.32
    summary_template = str(interpretation_atom.get("summary_template") or "{label}：{technical}。")
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": selected_claim_ids or atom.get("claim_ids") or [],
        "itemCount": item_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": "planet_sign_style",
        "strongestEvidenceId": "hand-planet-sign-style" if item_count else None,
        "selectedSigns": unique(selected_signs),
        "lowConfidenceCount": low_confidence_count,
        "summary": summary_template.format(label=label, technical=technical, item_count=item_count),
        "interpretation": str(
            interpretation_atom.get("interpretation")
            or "行星落星座描述某個行星功能用哪種星座風格表達；應綁定 planet function 使用。"
        ),
        "doesNotProve": str(
            interpretation_atom.get("does_not_prove")
            or "行星落星座不能單獨證明對方愛不愛、會不會聯絡、是否承諾或關係結局。"
        ),
        "confidence": "low" if not item_count or low_confidence_count else "medium",
        "source": source,
    }


FUNCTION_MATRIX_POINTS = ("Moon", "Mercury", "Venus", "Mars", "Saturn")
FUNCTION_MATRIX_PEOPLE = (("person_a", "你"), ("person_b", "對方"))

RELATIONSHIP_PROFILE_POINT_CONFIG = {
    "Moon": {
        "key": "emotionalSafety",
        "title": "安全感模式",
        "relationship_use": "先看壓力下需要怎樣的回應才會放鬆。",
        "does_not_fit": "不適合長時間冷處理、忽略情緒反應，或用沉默測試安全感。",
    },
    "Mercury": {
        "key": "communicationRepair",
        "title": "溝通方式",
        "relationship_use": "先看用什麼語氣比較容易被聽見。",
        "does_not_fit": "不適合一次丟出長篇追問、諷刺，或讓話題失去清楚邊界。",
    },
    "Venus": {
        "key": "affectionAttraction",
        "title": "好感表達",
        "relationship_use": "先看什麼靠近方式會被感覺成好感。",
        "does_not_fit": "不適合把好感直接升級成承諾要求，或用占有感測試愛意。",
    },
    "Mars": {
        "key": "pursuitConflict",
        "title": "行動節奏",
        "relationship_use": "先看靠近、爭執和主動節奏怎麼被觸發。",
        "does_not_fit": "不適合在壓力中硬碰硬、逼對方同速前進，或把急迫當成行動力。",
    },
    "Saturn": {
        "key": "defenseDelay",
        "title": "界線與壓力",
        "relationship_use": "先看害怕、界線和變慢的原因。",
        "does_not_fit": "不適合用最後通牒、命定等待，或把退縮直接解讀成永久拒絕。",
    },
}


ZH_SENTENCE_ENDINGS = "。！？"
ZH_NUMERALS = {
    0: "零",
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
}


def zh_clause(text: Any) -> str:
    return str(text or "").strip().rstrip(ZH_SENTENCE_ENDINGS).strip()


def normalize_zh_text(text: Any) -> str:
    value = str(text or "").strip()
    replacements = {
        "。。": "。",
        "！！": "！",
        "？？": "？",
        "；；": "；",
        "。；": "；",
        "！；": "；",
        "？；": "；",
        "；。": "。",
    }
    previous = None
    while previous != value:
        previous = value
        for old, new in replacements.items():
            value = value.replace(old, new)
    return value


def relationship_context_storyline_payload(
    *,
    context: dict[str, str],
    relationship_case_model: dict[str, Any],
    relationship_thesis: dict[str, Any],
    contact_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    status_answer_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_key = str(context.get("relationship_stage") or "")
    question_key = str(context.get("main_question") or "")
    contact_key = str(context.get("contact_status") or "")
    stage = CONTEXT_STORY_STAGE_FRAMES.get(stage_key) or {
        "short": "先把目前狀態看清楚",
        "premise": "關係狀態不清楚時，先不要把單一反應放大成全部答案。",
        "focus": "現在的互動能不能自然變穩",
        "proof": "對方有沒有用實際反應把關係往前帶一點",
        "avoid": "不要用猜測替整段關係下結論",
        "chart": "目前狀態下各自怎麼靠近",
        "fit": "互動能不能自然變穩",
        "timing": "現在適合靠近、觀察，還是先停",
    }
    question = CONTEXT_STORY_QUESTION_FRAMES.get(question_key) or {
        "short": "看現實反應能不能回答你的問題",
        "premise": "這題要放回實際互動裡看，不靠單一句話定論。",
        "focus": "對方是否有連續、清楚、尊重界線的反應",
        "proof": "互動不是只靠你撐住，而是對方也多走一點",
        "avoid": "不要把一次回應放大成全部答案",
        "headline": "先把答案放回實際反應",
        "action": "只做一件能自然停下的小事",
    }
    contact = CONTEXT_STORY_CONTACT_FRAMES.get(contact_key) or {
        "short": "先看目前聯絡狀態",
        "premise": "聯絡狀態會決定行動大小，不能只用星盤牽動推動下一步。",
        "focus": "目前互動能承受多大的靠近",
        "proof": "對方是否在自然情況下接住或延續",
        "avoid": "不要把聯絡情境看漏",
        "headline": "先看現在能不能自然接上",
        "action": "把下一步縮到目前狀態接得住",
        "timing": "時機要放回目前聯絡狀態裡看",
    }
    status_policy = status_answer_policy if isinstance(status_answer_policy, dict) else {}
    policy_page_rules = status_policy.get("pageTopicRules") if isinstance(status_policy.get("pageTopicRules"), dict) else {}
    policy_final = status_policy.get("finalNarrative") if isinstance(status_policy.get("finalNarrative"), dict) else {}
    policy_boundaries = [str(item) for item in status_policy.get("requiredBoundaries") or [] if item]
    policy_tracks = [str(item) for item in status_policy.get("resolvedTrackLabels") or [] if item]
    primary_track = policy_tracks[0] if policy_tracks else question["headline"]
    stage_label = STAGE_LABELS.get(stage_key, stage_key or "目前狀態")
    question_label = str(status_policy.get("questionRewrite") or QUESTION_TITLES.get(question_key, question_key or "你的問題"))
    question_label_clean = zh_clause(question_label)
    contact_label = CONTACT_STATUS_LABELS.get(contact_key, contact_key or "聯絡狀態未提供")
    stage_premise = zh_clause(stage["premise"])
    question_premise = zh_clause(question["premise"])
    contact_premise = zh_clause(contact["premise"])
    combo_key = f"{stage_key or 'unknown-stage'}|{question_key or 'unknown-question'}|{contact_key or 'unknown-contact'}"
    title = normalize_zh_text(f"{stage['short']}，先看{primary_track}，{contact['short']}")
    premise = normalize_zh_text(f"{status_policy.get('stagePremise') or stage_premise}；{question_premise}；{contact_premise}。")
    focus = normalize_zh_text(f"這次解讀會優先回答{primary_track}；聯絡上先看{contact['focus']}。")
    proof = normalize_zh_text(f"{question['proof']}；{contact['proof']}。")
    boundary_text = "；".join(policy_boundaries[:2]) if policy_boundaries else stage["avoid"]
    avoid = normalize_zh_text(f"{boundary_text}；{question['avoid']}；{contact['avoid']}。")
    action = normalize_zh_text(f"{question['action']}；{contact['action']}。")
    stage_context = zh_clause(stage["short"])
    question_context = zh_clause(question["short"])
    contact_context = {
        "blocked": "聯絡被擋住時",
        "no-contact": "沒有聯絡時",
        "occasional-contact": "偶爾回覆時",
        "still-in-contact": "還能聊天時",
        "living-or-working-together": "還會見面或共處時",
    }.get(contact_key, "目前聯絡狀態下")
    contact_condition = {
        "blocked": "界線先放前面",
        "no-contact": "沉默先當現況",
        "occasional-contact": "回覆不穩先保守",
        "still-in-contact": "對話先別加重",
        "living-or-working-together": "日常先保平穩",
    }.get(contact_key, "聯絡狀態先當背景")
    timing_headline = {
        "still-love-me": "在意能不能變成行動",
        "any-chance": "舊循環有沒有鬆開",
        "when-to-contact": "現在能不能輕輕靠近",
        "what-did-i-do-wrong": "責任和自責要分開",
        "stay-or-let-go": "等待還有沒有現實支撐",
    }.get(question_key, "現在的靠近節奏")
    action_headline = {
        "still-love-me": "等他自己接下一次互動",
        "any-chance": "做一件不推回舊問題的事",
        "when-to-contact": "只留一句短而清楚的話",
        "what-did-i-do-wrong": "只修一個你能調整的地方",
        "stay-or-let-go": "把自己的步調拿回來",
    }.get(question_key, primary_track)
    section_directives = {
        "chart-positioning": {
            "headline": normalize_zh_text(str(policy_page_rules.get("chart-positioning") or f"先看{stage['chart']}")),
            "meaning": normalize_zh_text("兩個人的底層習慣，會反映各自的需要、說法和壓力反應。"),
            "bridge": normalize_zh_text("需要沒有被說清楚時，保護自己的反應很容易被誤讀。"),
            "nextMove": normalize_zh_text("留意你的表達方式是否剛好碰到他保護自己的反應。"),
            "caution": normalize_zh_text(f"{contact_context}只當成背景，不直接拿它下結論。"),
        },
        "relationship-fit": {
            "headline": normalize_zh_text(str(policy_final.get("fitHeadline") or "關係型態先看基本相處")),
            "meaning": normalize_zh_text("你們的基本關係型態，會顯示吸引、摩擦、互補和相處節奏。"),
            "bridge": normalize_zh_text("合盤底圖能說明關係怎麼運作，但不能替現實互動下結論。"),
            "nextMove": normalize_zh_text("最值得調整的是一靠近就容易失衡的相處節奏。"),
            "caution": normalize_zh_text("不要只用關係型態替整段關係下最後結論，也不要把一次互動放大。"),
        },
        "core-answer": {
            "headline": normalize_zh_text(primary_track),
            "meaning": normalize_zh_text(f"先回答「{question_label_clean}」，再放回{contact_context}的現實限制裡看。"),
            "bridge": normalize_zh_text(f"先把重點放在{primary_track}，其他問題先不要一次攤開。"),
            "nextMove": normalize_zh_text(f"接下來只看：{question['proof']}。"),
            "caution": normalize_zh_text(boundary_text),
        },
        "timing-reading": {
            "headline": normalize_zh_text(timing_headline),
            "meaning": normalize_zh_text(str(policy_page_rules.get("timing-reading") or f"現在的步調也要照顧{contact_context}的現實限制。")),
            "bridge": normalize_zh_text(f"{stage['timing']}；{contact['timing']}。"),
            "nextMove": normalize_zh_text("先判斷現在適合靠近、觀察，還是先停在清楚界線內。"),
            "caution": normalize_zh_text("聯絡狀態只能幫你決定現在要多輕，不能保證結果。"),
        },
        "action-direction": {
            "headline": normalize_zh_text(action_headline),
            "meaning": normalize_zh_text(str(policy_page_rules.get("action-direction") or f"下一步要放在{contact_context}能承受的位置。")),
            "bridge": normalize_zh_text(f"下一步是：{action}"),
            "nextMove": normalize_zh_text(f"做完只看{contact['proof']}，沒有就先停。"),
            "caution": normalize_zh_text(f"做到這一步就停；{contact['avoid']}"),
        },
    }
    source_claim_ids = unique([
        *[str(item) for item in contact_policy.get("claimIds") or [] if item],
        *[str(item) for item in relationship_case_model.get("sourceClaimIds") or [] if item],
        *[str(item) for item in relationship_thesis.get("sourceClaimIds") or [] if item],
    ])
    method_claim_ids = unique([
        *[str(item) for item in contact_policy.get("methodClaimIds") or [] if item],
        *[str(item) for item in timing_guidance.get("methodClaimIds") or [] if item],
        *[str(item) for item in relationship_case_model.get("methodClaimIds") or [] if item],
    ])
    return {
        "version": RELATIONSHIP_CONTEXT_STORYLINE_VERSION,
        "comboKey": combo_key,
        "stageKey": stage_key,
        "questionKey": question_key,
        "contactKey": contact_key,
        "stageLabel": stage_label,
        "questionLabel": question_label,
        "contactLabel": contact_label,
        "storyTitle": title,
        "storyPremise": premise,
        "storyFocus": focus,
        "whatMustBeProven": proof,
        "wrongReadingToAvoid": avoid,
        "nextActionFrame": action,
        "sectionDirectives": section_directives,
        "statusAnswerPolicy": {
            "version": status_policy.get("version"),
            "resolvedTracks": [str(item) for item in status_policy.get("resolvedTracks") or [] if item],
            "resolvedTrackLabels": policy_tracks,
            "suppressedTracks": [str(item) for item in status_policy.get("suppressedTracks") or [] if item],
            "questionRewrite": question_label,
            "requiredBoundaries": policy_boundaries,
            "forbiddenVisibleEmphasis": [str(item) for item in status_policy.get("forbiddenVisibleEmphasis") or [] if item],
        },
        "evidenceClusterKeys": unique([
            RELATIONSHIP_CONTEXT_STORYLINE_KEY,
            "relationshipStatusAnswerPolicy",
            "relationshipStage",
            "contactStatus",
            "contactSituationPolicy",
            "relationshipCaseModel",
            "relationshipThesis",
        ]),
        "sourceClaimIds": source_claim_ids,
        "methodClaimIds": method_claim_ids,
    }


def relationship_context_storyline_cluster(storyline: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": RELATIONSHIP_CONTEXT_STORYLINE_KEY,
        "label": "關係情境故事線",
        "claimIds": [str(item) for item in storyline.get("sourceClaimIds") or [] if item],
        "itemCount": 3,
        "strongestStrength": 1.0,
        "averageStrength": 1.0,
        "dominantContactType": "stage_question_contact_combo",
        "strongestEvidenceId": str(storyline.get("comboKey") or ""),
        "summary": normalize_zh_text(storyline.get("storyTitle") or ""),
        "interpretation": "故事線由關係階段、核心問題和聯絡狀態共同決定，用來限制每頁的閱讀角度。",
        "doesNotProve": normalize_zh_text(storyline.get("wrongReadingToAvoid") or ""),
        "confidence": "medium",
        "source": RELATIONSHIP_CONTEXT_STORYLINE_VERSION,
    }


def relationship_status_answer_policy_cluster(policy: dict[str, Any]) -> dict[str, Any]:
    track_labels = [str(item) for item in policy.get("resolvedTrackLabels") or [] if item]
    boundaries = [str(item) for item in policy.get("requiredBoundaries") or [] if item]
    return {
        "category": "relationshipStatusAnswerPolicy",
        "label": "關係狀態答案策略",
        "claimIds": [],
        "itemCount": max(1, len(track_labels)),
        "strongestStrength": 1.0,
        "averageStrength": 1.0,
        "dominantContactType": "status_answer_policy",
        "strongestEvidenceId": str(policy.get("stageKey") or ""),
        "summary": normalize_zh_text(policy.get("questionRewrite") or "依關係狀態決定答案主題"),
        "interpretation": normalize_zh_text("；".join(track_labels[:3]) or "依關係狀態決定答案主題。"),
        "technical": f"status={policy.get('stageKey')}; tracks={','.join([str(item) for item in policy.get('resolvedTracks') or []])}",
        "doesNotProve": "這個策略只決定答案主題和語氣，不單獨證明星盤結論。",
        "confidence": "high",
        "source": "relationship-status-answer-policy-v1",
        "policyBoundary": normalize_zh_text("；".join(boundaries[:2])),
        "canCreateAstrologyConclusion": False,
    }


def zh_count(value: int) -> str:
    return ZH_NUMERALS.get(value, str(value))


def join_zh_clauses(parts: list[Any]) -> str:
    return "；".join(part for part in (zh_clause(item) for item in parts) if part)


def render_zh_summary(template: str, **kwargs: Any) -> str:
    clean_kwargs = {
        key: zh_clause(value) if isinstance(value, str) else value
        for key, value in kwargs.items()
    }
    return normalize_zh_text(template.format(**clean_kwargs))


def role_adjusted_relationship_text(text: Any, role_label: str) -> str:
    value = normalize_zh_text(text)
    if role_label == "你":
        return value
    target_swaps = [
        ("你需要對方", "__SUBJECT_NEEDS_YOU__"),
        ("對方有沒有", "__YOU_HAVE_OR_NOT__"),
        ("讓對方", "__MAKES_YOU__"),
        ("對方覺得", "__YOU_FEEL__"),
        ("對方聽成", "__YOU_HEAR_AS__"),
        ("對方此刻", "__YOU_RIGHT_NOW__"),
        ("對方懂", "__YOU_UNDERSTAND__"),
        ("對方不真誠", "__YOU_NOT_SINCERE__"),
    ]
    for old, placeholder in target_swaps:
        value = value.replace(old, placeholder)
    replacements = [
        ("對你很重要", "這點對對方很重要"),
        ("讓你", "讓對方"),
        ("你的", "對方的"),
        ("你會", "對方會"),
        ("你需要", "對方需要"),
        ("你習慣", "對方習慣"),
        ("你很", "對方很"),
        ("你比較", "對方比較"),
        ("你常", "對方常"),
        ("你容易", "對方容易"),
        ("你喜歡", "對方喜歡"),
        ("你最怕", "對方最怕"),
        ("你行動", "對方行動"),
        ("你反應", "對方反應"),
        ("你推進", "對方推進"),
        ("你不會", "對方不會"),
        ("你不喜歡", "對方不喜歡"),
        ("你不太", "對方不太"),
        ("你可能", "對方可能"),
    ]
    for old, new in replacements:
        value = value.replace(old, new)
    target_outputs = {
        "__SUBJECT_NEEDS_YOU__": "對方需要你",
        "__YOU_HAVE_OR_NOT__": "你有沒有",
        "__MAKES_YOU__": "讓你",
        "__YOU_FEEL__": "你覺得",
        "__YOU_HEAR_AS__": "你聽成",
        "__YOU_RIGHT_NOW__": "你此刻",
        "__YOU_UNDERSTAND__": "你懂",
        "__YOU_NOT_SINCERE__": "你不真誠",
    }
    for placeholder, output in target_outputs.items():
        value = value.replace(placeholder, output)
    return normalize_zh_text(value)


def western_function_style_entry(fixture: dict[str, Any], person: str, role_label: str, point: str) -> dict[str, Any] | None:
    obj = western_object(fixture, person, point)
    if not obj:
        return None
    sign = str(obj.get("sign") or "")
    sign_label = SIGN_LABELS.get(sign, sign or "未知星座")
    element = str(obj.get("sign_element") or SIGN_ELEMENTS.get(sign) or "")
    element_label = WESTERN_ELEMENT_LABELS.get(element, element or "未知元素")
    modality = SIGN_MODALITIES.get(sign, "")
    modality_label = WESTERN_MODALITY_LABELS.get(modality, modality or "未知模式")
    raw_style = (READABLE_FUNCTION_SIGN_STYLES.get(point) or {}).get(
        sign,
        f"{SIGN_RUNTIME_STYLES.get(sign, '需要放回本命盤判斷')}，需綁定{POINT_LABELS.get(point, point)}功能使用",
    )
    style = readable_role_adjusted_relationship_text(raw_style, role_label)
    element_style = (FUNCTION_ELEMENT_STYLES.get(point) or {}).get(
        element,
        f"{element_label}只描述{POINT_LABELS.get(point, point)}功能的表達材料，不能單獨下結論",
    )
    modality_style = (FUNCTION_MODALITY_STYLES.get(point) or {}).get(
        modality,
        f"{modality_label}只描述{POINT_LABELS.get(point, point)}功能的反應節奏，不能單獨下結論",
    )
    claim_ids = [
        claim_id
        for claim_id in (
            SIGN_CLAIM_IDS.get(sign),
            ELEMENT_CLAIM_IDS.get(element),
            MODALITY_CLAIM_IDS.get(modality),
        )
        if claim_id
    ]
    return {
        "person": person,
        "roleLabel": role_label,
        "point": point,
        "sign": sign,
        "signLabel": sign_label,
        "element": element,
        "elementLabel": element_label,
        "elementStyle": element_style,
        "modality": modality,
        "modalityLabel": modality_label,
        "modalityStyle": modality_style,
        "style": style,
        "claimIds": claim_ids,
        "confidence": western_moon_confidence(fixture, person) if point == "Moon" else "high",
    }


def western_function_sign_style_cluster(
    fixture: dict[str, Any],
    point: str,
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = FUNCTION_SIGN_CLUSTER_CONFIG[point]
    category = str(config["category"])
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or config["default_label"])
    source = str(atom.get("source_article_id") or "western-individual-sign-meanings-hand")
    details: list[str] = []
    selected_signs: list[str] = []
    selected_elements: list[str] = []
    selected_modalities: list[str] = []
    selected_claim_ids: list[str] = []
    person_styles: list[dict[str, Any]] = []
    low_confidence_count = 0

    for person, role_label in FUNCTION_MATRIX_PEOPLE:
        entry = western_function_style_entry(fixture, person, role_label, point)
        if not entry:
            continue
        sign = str(entry.get("sign") or "")
        element = str(entry.get("element") or "")
        modality = str(entry.get("modality") or "")
        confidence = str(entry.get("confidence") or "medium")
        if confidence == "low":
            low_confidence_count += 1
        detail = (
            f"{entry['roleLabel']}{POINT_LABELS.get(point, point)}{entry['signLabel']}"
            f"（{entry['elementLabel']}／{entry['modalityLabel']}）：{entry['style']}"
        )
        details.append(detail)
        if sign:
            selected_signs.append(sign)
        if element:
            selected_elements.append(element)
        if modality:
            selected_modalities.append(modality)
        claim_id = SIGN_CLAIM_IDS.get(sign)
        if claim_id:
            selected_claim_ids.append(claim_id)
        element_claim_id = ELEMENT_CLAIM_IDS.get(element)
        if element_claim_id:
            selected_claim_ids.append(element_claim_id)
        modality_claim_id = MODALITY_CLAIM_IDS.get(modality)
        if modality_claim_id:
            selected_claim_ids.append(modality_claim_id)
        person_styles.append(entry)

    item_count = len(details)
    technical = join_zh_clauses(details) if details else f"{POINT_LABELS.get(point, point)}星座資料不足"
    if item_count >= 2:
        strength = 0.72
    elif item_count == 1:
        strength = 0.52
    else:
        strength = 0.24
    confidence = "low" if not item_count or low_confidence_count else "medium"
    summary_template = str(interpretation_atom.get("summary_template") or "{label}：{technical}。")
    function_claim_ids = [str(claim_id) for claim_id in atom.get("claim_ids") or []]
    claim_ids = unique([*function_claim_ids, *selected_claim_ids])
    method_claim_ids = list(FUNCTION_SIGN_METHOD_CLAIM_IDS.get(point, []))
    saturn_boundary = saturn_nonfatal_process_boundary(
        "natal_saturn_sign_defense_delay",
        evidence_keys=[f"{style.get('roleLabel')}-{style.get('point')}-{style.get('sign')}" for style in person_styles],
    ) if point == "Saturn" else None
    if saturn_boundary:
        claim_ids = unique([*claim_ids, *GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS])
        method_claim_ids = unique([*method_claim_ids, *GREENE_SATURN_PROCESS_METHOD_CLAIM_IDS])
    payload = {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": claim_ids,
        "methodClaimIds": method_claim_ids,
        "point": point,
        "itemCount": item_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": str(config["dominant_contact_type"]),
        "strongestEvidenceId": str(config["evidence_id"]) if item_count else None,
        "selectedSigns": unique(selected_signs),
        "selectedElements": unique(selected_elements),
        "selectedModalities": unique(selected_modalities),
        "personStyles": person_styles,
        "hasBothPeopleStyle": item_count >= 2,
        "lowConfidenceCount": low_confidence_count,
        "summary": render_zh_summary(summary_template, label=label, technical=technical, item_count=item_count),
        "interpretation": str(interpretation_atom.get("interpretation") or config["interpretation"]),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or config["does_not_prove"]),
        "confidence": confidence,
        "source": source,
    }
    if saturn_boundary:
        payload["saturnProcessBoundary"] = saturn_boundary
        payload["sourceClaimIds"] = GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS
    return payload


def western_function_matrix_entries(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for point in FUNCTION_MATRIX_POINTS:
        for person, role_label in FUNCTION_MATRIX_PEOPLE:
            entry = western_function_style_entry(fixture, person, role_label, point)
            if entry:
                entries.append(entry)
    return entries


def western_function_element_matrix_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "functionElementMatrix"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "行星功能元素矩陣")
    source = str(atom.get("source_article_id") or "western-function-element-templates")
    entries = western_function_matrix_entries(fixture)
    element_counts = {element: 0 for element in WESTERN_ELEMENT_LABELS}
    low_confidence_count = 0
    selected_claim_ids: list[str] = []
    details: list[str] = []
    for entry in entries:
        element = str(entry.get("element") or "")
        if element in element_counts:
            element_counts[element] += 1
        if entry.get("confidence") == "low":
            low_confidence_count += 1
        claim_id = ELEMENT_CLAIM_IDS.get(element)
        if claim_id:
            selected_claim_ids.append(claim_id)
        details.append(f"{entry['roleLabel']}{POINT_LABELS.get(str(entry['point']), str(entry['point']))}{entry['elementLabel']}：{entry['elementStyle']}")
    item_count = len(entries)
    dominant_element = max(element_counts, key=lambda key: element_counts[key]) if item_count else ""
    dominant_element_label = WESTERN_ELEMENT_LABELS.get(dominant_element, "未知")
    technical = "；".join(details[:5]) if details else "行星功能元素資料不足"
    summary_template = str(interpretation_atom.get("summary_template") or "{label}統整{item_count}個關係功能點；主元素是{dominant_element_label}：{technical}。")
    claim_ids = unique([*(atom.get("claim_ids") or []), *selected_claim_ids])
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": claim_ids,
        "methodClaimIds": GEORGE_BLOCH_FUNCTION_ELEMENT_METHOD_CLAIM_IDS,
        "itemCount": item_count,
        "strongestStrength": 0.68 if item_count else 0.2,
        "averageStrength": round(item_count / max(len(FUNCTION_MATRIX_POINTS) * len(FUNCTION_MATRIX_PEOPLE), 1), 3),
        "dominantContactType": f"dominant_{dominant_element.lower()}" if dominant_element else "none",
        "strongestEvidenceId": f"function-element-{dominant_element.lower()}" if dominant_element else None,
        "selectedElements": [element for element, count in element_counts.items() if count],
        "dominantElement": dominant_element,
        "dominantElementLabel": dominant_element_label,
        "fireCount": element_counts["Fire"],
        "earthCount": element_counts["Earth"],
        "airCount": element_counts["Air"],
        "waterCount": element_counts["Water"],
        "hasFireMarsOrVenus": any(entry.get("point") in {"Mars", "Venus"} and entry.get("element") == "Fire" for entry in entries),
        "hasWaterMoonOrVenus": any(entry.get("point") in {"Moon", "Venus"} and entry.get("element") == "Water" for entry in entries),
        "hasEarthMoonOrSaturn": any(entry.get("point") in {"Moon", "Saturn"} and entry.get("element") == "Earth" for entry in entries),
        "hasAirMercuryOrMars": any(entry.get("point") in {"Mercury", "Mars"} and entry.get("element") == "Air" for entry in entries),
        "personStyles": entries,
        "lowConfidenceCount": low_confidence_count,
        "summary": summary_template.format(
            label=label,
            item_count=item_count,
            dominant_element_label=dominant_element_label,
            technical=technical,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "元素用來修飾 Moon/Mercury/Venus/Mars/Saturn 的關係功能。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "元素矩陣不能單獨證明關係結果。"),
        "confidence": "low" if not item_count or low_confidence_count else "medium",
        "source": source,
    }


def western_function_modality_matrix_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "functionModalityMatrix"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "行星功能三模式矩陣")
    source = str(atom.get("source_article_id") or "western-function-modality-templates")
    entries = western_function_matrix_entries(fixture)
    modality_counts = {modality: 0 for modality in WESTERN_MODALITY_LABELS}
    low_confidence_count = 0
    selected_claim_ids: list[str] = []
    details: list[str] = []
    for entry in entries:
        modality = str(entry.get("modality") or "")
        if modality in modality_counts:
            modality_counts[modality] += 1
        if entry.get("confidence") == "low":
            low_confidence_count += 1
        claim_id = MODALITY_CLAIM_IDS.get(modality)
        if claim_id:
            selected_claim_ids.append(claim_id)
        details.append(f"{entry['roleLabel']}{POINT_LABELS.get(str(entry['point']), str(entry['point']))}{entry['modalityLabel']}：{entry['modalityStyle']}")
    item_count = len(entries)
    dominant_modality = max(modality_counts, key=lambda key: modality_counts[key]) if item_count else ""
    dominant_modality_label = WESTERN_MODALITY_LABELS.get(dominant_modality, "未知")
    technical = "；".join(details[:5]) if details else "行星功能三模式資料不足"
    summary_template = str(interpretation_atom.get("summary_template") or "{label}統整{item_count}個關係功能點；主模式是{dominant_modality_label}：{technical}。")
    claim_ids = unique([*(atom.get("claim_ids") or []), *selected_claim_ids])
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": claim_ids,
        "itemCount": item_count,
        "strongestStrength": 0.66 if item_count else 0.2,
        "averageStrength": round(item_count / max(len(FUNCTION_MATRIX_POINTS) * len(FUNCTION_MATRIX_PEOPLE), 1), 3),
        "dominantContactType": f"dominant_{dominant_modality.lower()}" if dominant_modality else "none",
        "strongestEvidenceId": f"function-modality-{dominant_modality.lower()}" if dominant_modality else None,
        "selectedModalities": [modality for modality, count in modality_counts.items() if count],
        "dominantModality": dominant_modality,
        "dominantModalityLabel": dominant_modality_label,
        "cardinalCount": modality_counts["Cardinal"],
        "fixedCount": modality_counts["Fixed"],
        "mutableCount": modality_counts["Mutable"],
        "hasCardinalMarsOrVenus": any(entry.get("point") in {"Mars", "Venus"} and entry.get("modality") == "Cardinal" for entry in entries),
        "hasFixedMoonOrSaturn": any(entry.get("point") in {"Moon", "Saturn"} and entry.get("modality") == "Fixed" for entry in entries),
        "hasMutableMercuryOrMars": any(entry.get("point") in {"Mercury", "Mars"} and entry.get("modality") == "Mutable" for entry in entries),
        "personStyles": entries,
        "lowConfidenceCount": low_confidence_count,
        "summary": summary_template.format(
            label=label,
            item_count=item_count,
            dominant_modality_label=dominant_modality_label,
            technical=technical,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "三模式用來修飾 Moon/Mercury/Venus/Mars/Saturn 的反應節奏。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "三模式矩陣不能單獨證明關係結果。"),
        "confidence": "low" if not item_count or low_confidence_count else "medium",
        "source": source,
    }


def western_angle_house_framework_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    allowed_count = sum(1 for person in ("person_a", "person_b") if western_houses_allowed(fixture, person))
    precision_gate = western_house_angle_precision_gate(fixture)
    technical = (
        "出生時間與地點足夠時，Asc/Desc/MC/IC 與 houses 可進入深度層"
        if allowed_count
        else "出生時間或地點不足時，角度點、宮位與 overlay 不展示"
    )
    cluster = western_static_atom_cluster(
        "angleHouseFramework",
        default_label="角度點與宮位基礎",
        default_technical=technical,
        default_interpretation="角度點與宮位是時間/地點敏感層；完整資料才可用來補充第一印象、伴侶軸線與生活場域。",
        default_does_not_prove="角度點與宮位不能在缺時間或缺地點時被補寫，也不能保證事件結果。",
        default_confidence="low" if not allowed_count else "medium",
        item_count=allowed_count,
        dominant_contact_type="precision_gate" if not allowed_count else "angle_house",
        strongest_evidence_id="hand-angle-house-framework",
        structured_kb=structured_kb,
    )
    cluster["hasReliableAngles"] = allowed_count == 2
    cluster["blockedByPrecision"] = allowed_count < 2
    cluster["houseAnglePrecisionGate"] = precision_gate
    cluster["sourceClaimIds"] = HOUSE_ANGLE_PRECISION_CLAIM_IDS
    return cluster


def western_aspect_interpretation_foundation_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return western_static_atom_cluster(
        "aspectInterpretationFoundation",
        default_label="相位解讀基礎",
        default_technical="相位需保留 aspect type、orb、方向性與 hard/soft 語義；tight orb 優先，hard aspect 是動態張力",
        default_interpretation="相位表示兩種行星功能如何互動；它說明牽動、摩擦或修復入口，不直接判斷關係終局。",
        default_does_not_prove="相位不能單獨證明承諾、聯絡、復合或關係終局。",
        item_count=4,
        dominant_contact_type="aspect_foundation",
        strongest_evidence_id="hand-aspect-foundation",
        structured_kb=structured_kb,
    )


def western_aspect_pair_phrase_template_method_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return western_static_atom_cluster(
        "aspectPairPhraseTemplateMethod",
        default_label="pair-contact 句型方法",
        default_technical="pair-contact template 先保留 planet pair 的功能，再套入 conjunction/soft/hard 語氣",
        default_interpretation="模板只把已計算的 planet pair、contact type、orb 與精度限制翻成可控語言；不可新增星盤事實。",
        default_does_not_prove="pair-contact 句型不能單獨證明承諾、復合、聯絡或對方內心。",
        item_count=4,
        dominant_contact_type="pair_phrase_method",
        strongest_evidence_id="pair-contact-phrase-template-method",
        structured_kb=structured_kb,
    )


def western_aspect_synthesis_cross_check_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return western_static_atom_cluster(
        "aspectSynthesisCrossCheck",
        default_label="相位合成交叉檢查",
        default_technical="相位需拆成 planet pair、contact type、orb、精度與問題脈絡後再合成",
        default_interpretation="hard aspect 可以表示挑戰與需要整合的互動，不應被寫成永久負面判決或命運結論。",
        default_does_not_prove="相位合成交叉檢查不能補寫未被 selector 選出的 chart facts，也不能保證結果。",
        item_count=3,
        dominant_contact_type="aspect_synthesis",
        strongest_evidence_id="george-bloch-aspect-synthesis",
        structured_kb=structured_kb,
    )


def western_relationship_potential_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "relationshipPotential"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "本命關係潛力")
    source = str(atom.get("source_article_id") or "western-houses-angles-foundation")
    points = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn", "Asc", "Desc"]
    displayed: list[str] = []
    blocked = 0
    low_confidence = 0
    for person, role_label in (("person_a", "你"), ("person_b", "對方")):
        for point in points:
            if point in {"Asc", "Desc"} and not western_houses_allowed(fixture, person):
                blocked += 1
                continue
            obj = western_object(fixture, person, point)
            if not obj:
                continue
            sign = SIGN_LABELS.get(str(obj.get("sign") or ""), str(obj.get("sign") or "未知星座"))
            displayed.append(f"{role_label}{POINT_LABELS.get(point, point)}{sign}")
            if point == "Moon" and western_moon_confidence(fixture, person) == "low":
                low_confidence += 1
    item_count = len(displayed)
    strength = 0.72 if item_count >= 8 else 0.55 if item_count else 0.25
    technical = "；".join(displayed[:8]) if displayed else "本命點不足"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": item_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": "natal_relationship_potential",
        "strongestEvidenceId": "suskin-natal-relationship-potential" if item_count else None,
        "blockedCount": blocked,
        "lowConfidenceCount": low_confidence,
        "hasBothPeopleNeeds": item_count >= 2,
        "summary": str(interpretation_atom.get("summary_template") or "{label}有{item_count}個可展示本命點；主訊號是：{technical}。").format(
            label=label,
            item_count=item_count,
            technical=technical,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "先看雙方本命關係潛力，再看合盤觸發。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "本命潛力不能單獨證明復合。"),
        "confidence": "medium" if item_count else "low",
        "source": source,
    }


def western_sun_moon_asc_profile_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "sunMoonAscProfile"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "太陽月亮上升主輪廓")
    source = str(atom.get("source_article_id") or "western-sun-moon-asc-profile-george-bloch")
    points = ["Sun", "Moon", "Asc"]
    profile_points: list[dict[str, Any]] = []
    blocked_points: list[dict[str, str]] = []
    low_moon_confidence = 0

    for person, person_key, role_label in (("person_a", "personA", "你"), ("person_b", "personB", "對方")):
        for point in points:
            if point == "Asc" and not western_houses_allowed(fixture, person):
                blocked_points.append(
                    {
                        "person": person_key,
                        "roleLabel": role_label,
                        "point": point,
                        "reason": "birth_time_and_location_required",
                    }
                )
                continue
            obj = western_object(fixture, person, point)
            if not obj:
                continue
            sign = str(obj.get("sign") or "")
            element = str(obj.get("sign_element") or "")
            modality = str(obj.get("sign_modality") or "")
            confidence = "low" if point == "Moon" and western_moon_confidence(fixture, person) == "low" else "high"
            if confidence == "low":
                low_moon_confidence += 1
            profile_points.append(
                {
                    "person": person_key,
                    "roleLabel": role_label,
                    "point": point,
                    "pointLabel": POINT_LABELS.get(point, point),
                    "sign": sign,
                    "signLabel": SIGN_LABELS.get(sign, sign or "未知星座"),
                    "element": element,
                    "elementLabel": WESTERN_ELEMENT_LABELS.get(element, element or "未知元素"),
                    "modality": modality,
                    "modalityLabel": WESTERN_MODALITY_LABELS.get(modality, modality or "未知模式"),
                    "confidence": confidence,
                }
            )

    item_count = len(profile_points)
    point_index = {(item.get("person"), item.get("point")) for item in profile_points}
    has_sun_moon_profile = all(
        (person_key, "Sun") in point_index and (person_key, "Moon") in point_index
        for person_key in ("personA", "personB")
    )
    has_ascendant_profile = all((person_key, "Asc") in point_index for person_key in ("personA", "personB"))
    has_reliable_ascendant = all(western_houses_allowed(fixture, person) for person in ("person_a", "person_b"))
    details = [
        f"{item['roleLabel']}{item['pointLabel']}{item['signLabel']}"
        for item in profile_points
    ]
    technical = "；".join(details) if details else "太陽月亮上升資料不足"
    strength = 0.78 if has_sun_moon_profile and has_ascendant_profile else 0.62 if has_sun_moon_profile else 0.32

    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": item_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": "natal_profile_trinity" if has_ascendant_profile else "natal_profile_without_angles",
        "strongestEvidenceId": "western-sun-moon-asc-profile-george-bloch" if item_count else None,
        "blockedCount": len(blocked_points),
        "lowMoonConfidenceCount": low_moon_confidence,
        "hasSunMoonProfile": has_sun_moon_profile,
        "hasAscendantProfile": has_ascendant_profile,
        "hasReliableAscendant": has_reliable_ascendant,
        "hasBothPeopleProfile": any(item.get("person") == "personA" for item in profile_points)
        and any(item.get("person") == "personB" for item in profile_points),
        "profilePoints": profile_points,
        "blockedPoints": blocked_points,
        "summary": str(interpretation_atom.get("summary_template") or "{label}讀出{item_count}個可用主輪廓點；主訊號是：{technical}。").format(
            label=label,
            item_count=item_count,
            technical=technical,
        ),
        "interpretation": str(
            interpretation_atom.get("interpretation")
            or "太陽、月亮與上升可作為人格輪廓基礎；上升必須有可靠時間與地點才可展示。"
        ),
        "doesNotProve": str(
            interpretation_atom.get("does_not_prove")
            or "太陽月亮上升不能單獨證明愛、不愛、復合、承諾或對方內心。"
        ),
        "confidence": "low" if not item_count or blocked_points or low_moon_confidence else "medium",
        "source": source,
    }


def western_element_relation(element_a: str, element_b: str) -> str:
    if not element_a or not element_b:
        return "unknown"
    if element_a == element_b or frozenset((element_a, element_b)) in WESTERN_ELEMENT_NATURAL_PAIRS:
        return "natural"
    if frozenset((element_a, element_b)) in WESTERN_ELEMENT_FRICTION_PAIRS:
        return "friction"
    return "effort"


def western_element_comparison_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "elementComparison"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "初步元素比較")
    source = str(atom.get("source_article_id") or "western-initial-comparison-elements")
    points = ["Sun", "Moon", "Mercury", "Venus", "Mars"]
    if western_houses_allowed(fixture, "person_a") and western_houses_allowed(fixture, "person_b"):
        points.append("Asc")
    counts = {"natural": 0, "effort": 0, "friction": 0, "unknown": 0}
    details: list[str] = []
    for point in points:
        obj_a = western_object(fixture, "person_a", point) or {}
        obj_b = western_object(fixture, "person_b", point) or {}
        element_a = str(obj_a.get("sign_element") or "")
        element_b = str(obj_b.get("sign_element") or "")
        relation = western_element_relation(element_a, element_b)
        counts[relation] += 1
        if relation != "unknown":
            details.append(
                f"{POINT_LABELS.get(point, point)}：{WESTERN_ELEMENT_LABELS.get(element_a, element_a)} / {WESTERN_ELEMENT_LABELS.get(element_b, element_b)} = {relation}"
            )
    item_count = sum(value for key, value in counts.items() if key != "unknown")
    dominant = max(("natural", "effort", "friction"), key=lambda key: counts[key]) if item_count else "unknown"
    strength = {
        "natural": 0.68,
        "effort": 0.52,
        "friction": 0.62,
        "unknown": 0.25,
    }[dominant]
    technical = "；".join(details[:4]) if details else "元素資料不足"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": item_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round((counts["natural"] + counts["effort"] * 0.7 + counts["friction"] * 0.8) / max(item_count, 1), 3),
        "dominantContactType": dominant,
        "strongestEvidenceId": f"element-comparison-{dominant}" if item_count else None,
        "naturalElementCount": counts["natural"],
        "effortElementCount": counts["effort"],
        "frictionElementCount": counts["friction"],
        "summary": str(interpretation_atom.get("summary_template") or "{label}有{item_count}組可比較點位；主訊號是：{technical}。").format(
            label=label,
            item_count=item_count,
            technical=technical,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "元素只描述互動風格。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "元素不能單獨判斷關係成敗。"),
        "confidence": "medium" if item_count else "low",
        "source": source,
    }


SAFETY_VALIDATION_PAIR_CONFIGS = [
    {
        "id": "moon-moon",
        "title": "彼此的安全感",
        "person_a_point": "Moon",
        "person_b_point": "Moon",
        "meaning": "兩個人遇到脆弱、冷淡或壓力時，是否容易用對方聽得懂的方式安撫彼此。",
    },
    {
        "id": "venus-venus",
        "title": "彼此覺得被重視的方式",
        "person_a_point": "Venus",
        "person_b_point": "Venus",
        "meaning": "兩個人表達喜歡、欣賞與靠近時，是否容易讓彼此感到被珍惜。",
    },
    {
        "id": "a-moon-b-venus",
        "title": "你的安全感 × 對方的喜歡方式",
        "person_a_point": "Moon",
        "person_b_point": "Venus",
        "meaning": "對方表達喜歡的方式，能不能自然安撫你的安全感需求。",
    },
    {
        "id": "a-venus-b-moon",
        "title": "你的喜歡方式 × 對方的安全感",
        "person_a_point": "Venus",
        "person_b_point": "Moon",
        "meaning": "你表達喜歡的方式，能不能自然讓對方比較安心。",
    },
]


SAFETY_VALIDATION_RELATION_LABELS = {
    "natural": "容易被接住",
    "effort": "需要講明白",
    "friction": "容易誤會成壓力",
    "unknown": "資料不足",
}


def safety_validation_possessive(role_label: str) -> str:
    if role_label == "你":
        return "你的"
    if role_label == "對方":
        return "對方的"
    return f"{role_label}的"


def safety_validation_language_label(entry: dict[str, Any]) -> str:
    role = safety_validation_possessive(str(entry.get("roleLabel") or ""))
    point = POINT_LABELS.get(str(entry.get("point") or ""), str(entry.get("point") or ""))
    sign = str(entry.get("signLabel") or "未知星座")
    element = str(entry.get("elementLabel") or "未知元素")
    return f"{role}{point}{sign}（{element}）"


def safety_validation_pair_body(relation: str, person_a_label: str, person_b_label: str) -> str:
    if relation == "natural":
        return (
            f"{person_a_label}遇到{person_b_label}時，比較容易把對方的靠近感受成安撫或重視，"
            "不用先解釋很多，也比較不容易一開始就防衛。"
        )
    if relation == "friction":
        return (
            f"{person_a_label}遇到{person_b_label}時，容易把好意聽成壓力。"
            "一方想靠近，另一方可能先感到被催、被冷落，或覺得自己的需要沒有被理解。"
        )
    if relation == "unknown":
        return "這一組目前資料不足，不能硬寫成契合或摩擦。"
    return (
        f"{person_a_label}遇到{person_b_label}時，不是不合，而是表達方式不會自動對上。"
        "安全感或喜歡需要講得更明白，才不會各自以為自己已經表達了。"
    )


def safety_validation_count_sentence(cluster: dict[str, Any]) -> str:
    total = int(cluster.get("itemCount") or 0)
    if not total:
        return "目前月亮與金星資料不足，不能判斷安全感與被重視的互動。"
    parts = []
    natural = int(cluster.get("naturalLanguageCount") or 0)
    effort = int(cluster.get("effortLanguageCount") or 0)
    friction = int(cluster.get("frictionLanguageCount") or 0)
    if natural:
        parts.append(f"{zh_count(natural)}組容易被接住")
    if effort:
        parts.append(f"{zh_count(effort)}組需要講明白")
    if friction:
        parts.append(f"{zh_count(friction)}組容易誤會成壓力")
    return f"{zh_count(total)}組月亮與金星互動裡，" + "、".join(parts) + "。"


def safety_validation_fit_body(
    cluster: dict[str, Any],
    strongest_pair: dict[str, Any],
    relation: str,
) -> str:
    count_text = safety_validation_count_sentence(cluster)
    title = str(strongest_pair.get("title") or "安全感與被重視")
    pair_body = str(strongest_pair.get("body") or cluster.get("interpretation") or "")
    if relation == "natural" and (
        int(cluster.get("frictionLanguageCount") or 0) or int(cluster.get("effortLanguageCount") or 0)
    ):
        bridge = "這代表不是每個反應都順，但你們有一條可以先靠近的通道。"
    elif relation == "natural":
        bridge = "這代表你們在安心和被重視這一層，比較容易用對方收得到的方式靠近。"
    elif relation == "friction":
        bridge = "這代表關係最容易卡住的點，不一定是沒有在意，而是靠近時容易讓對方感到壓力。"
    else:
        bridge = "這代表你們要把自己的需求說得更具體，不能只靠默契或猜測。"
    return f"{count_text}{bridge}最值得先看的是「{title}」：{pair_body}"


def safety_validation_next_move(cluster: dict[str, Any], relation: str) -> str:
    if relation == "natural" and int(cluster.get("frictionLanguageCount") or 0):
        return "先用比較舒服的那條通道靠近，訊息短一點、具體一點；不要因為有連結感，就立刻把話推到承諾或答案。"
    if relation == "natural":
        return "可以從輕、自然、讓對方舒服的互動開始；重點是維持安全感，不是急著把舒服感推成關係結論。"
    if relation == "friction":
        return "先不要用追問、試探或反覆確認來要安全感。把話縮短，只說一件具體事，並留給對方回應空間。"
    return "下一步不是多說一大段，而是把需求縮成一個對方做得到的小動作，再觀察對方能不能接住。"


def western_safety_validation_language_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "safetyValidationLanguage"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "安全感與被重視語言")
    source = str(atom.get("source_article_id") or "western-safety-validation-language")
    details: list[str] = []
    pairs: list[dict[str, Any]] = []
    counts = {"natural": 0, "effort": 0, "friction": 0, "unknown": 0}
    low_confidence_count = 0
    selected_claim_ids: list[str] = [str(claim_id) for claim_id in atom.get("claim_ids") or [] if claim_id]

    for config in SAFETY_VALIDATION_PAIR_CONFIGS:
        entry_a = western_function_style_entry(fixture, "person_a", "你", str(config["person_a_point"]))
        entry_b = western_function_style_entry(fixture, "person_b", "對方", str(config["person_b_point"]))
        if not entry_a or not entry_b:
            counts["unknown"] += 1
            continue
        element_a = str(entry_a.get("element") or "")
        element_b = str(entry_b.get("element") or "")
        relation = western_element_relation(element_a, element_b)
        counts[relation] += 1
        if entry_a.get("confidence") == "low" or entry_b.get("confidence") == "low":
            low_confidence_count += 1
        person_a_label = safety_validation_language_label(entry_a)
        person_b_label = safety_validation_language_label(entry_b)
        pair_claim_ids = unique([
            *[str(claim_id) for claim_id in entry_a.get("claimIds") or []],
            *[str(claim_id) for claim_id in entry_b.get("claimIds") or []],
        ])
        selected_claim_ids.extend(pair_claim_ids)
        pair = {
            "id": config["id"],
            "title": config["title"],
            "meaning": config["meaning"],
            "relation": relation,
            "relationLabel": SAFETY_VALIDATION_RELATION_LABELS.get(relation, "需要觀察"),
            "personAPoint": str(config["person_a_point"]),
            "personBPoint": str(config["person_b_point"]),
            "personA": person_a_label,
            "personB": person_b_label,
            "personASign": entry_a.get("sign"),
            "personBSign": entry_b.get("sign"),
            "personAElement": entry_a.get("element"),
            "personBElement": entry_b.get("element"),
            "body": safety_validation_pair_body(relation, person_a_label, person_b_label),
            "claimIds": pair_claim_ids,
            "confidence": "low" if entry_a.get("confidence") == "low" or entry_b.get("confidence") == "low" else "medium",
        }
        pairs.append(pair)
        details.append(f"{pair['title']}：{pair['personA']}遇到{pair['personB']}，{pair['relationLabel']}")

    item_count = len(pairs)
    dominant = max(("natural", "effort", "friction"), key=lambda key: counts[key]) if item_count else "unknown"
    strength = {
        "natural": 0.68,
        "effort": 0.56,
        "friction": 0.64,
        "unknown": 0.24,
    }[dominant]
    technical = "；".join(details[:4]) if details else "月亮與金星資料不足"
    summary_template = str(interpretation_atom.get("summary_template") or "{label}檢查{item_count}組月亮與金星互動；主訊號是：{technical}。")
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": unique(selected_claim_ids),
        "itemCount": item_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round((counts["natural"] + counts["effort"] * 0.75 + counts["friction"] * 0.85) / max(item_count, 1), 3),
        "dominantContactType": dominant,
        "strongestEvidenceId": f"safety-validation-language-{dominant}" if item_count else None,
        "naturalLanguageCount": counts["natural"],
        "effortLanguageCount": counts["effort"],
        "frictionLanguageCount": counts["friction"],
        "hasNaturalNeedBridge": counts["natural"] > 0,
        "hasSafetyValidationObstacle": counts["friction"] >= 2 and counts["friction"] >= counts["natural"],
        "pairs": pairs,
        "lowConfidenceCount": low_confidence_count,
        "summary": summary_template.format(label=label, item_count=zh_count(item_count), technical=technical),
        "interpretation": str(interpretation_atom.get("interpretation") or "月亮與金星互動用來判斷安全感與被重視方式能不能互相接住。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "Moon/Venus 語言不能單獨證明關係結果。"),
        "confidence": "low" if not item_count or low_confidence_count else "medium",
        "source": source,
    }


def western_relationship_profile_card(
    fixture: dict[str, Any],
    person: str,
    role_label: str,
    point: str,
) -> dict[str, Any] | None:
    entry = western_function_style_entry(fixture, person, role_label, point)
    if not entry:
        return None
    config = RELATIONSHIP_PROFILE_POINT_CONFIG[point]
    point_label = POINT_LABELS.get(point, point)
    placement = f"{point_label}{entry.get('signLabel') or ''}"
    sign = str(entry.get("sign") or "")
    natural_response = str(entry.get("style") or "")
    tension_pattern = readable_role_adjusted_relationship_text((READABLE_FUNCTION_SIGN_TENSIONS.get(point) or {}).get(
        sign,
        str(entry.get("modalityStyle") or config["relationship_use"]),
    ), role_label)
    readable = person_function_sign_readable_interpretation(
        point=point,
        sign=sign,
        sign_label=str(entry.get("signLabel") or ""),
        role_label=role_label,
        placement=placement,
        fallback_body=natural_response,
        fallback_stuck_pattern=tension_pattern,
        confidence=str(entry.get("confidence") or "medium"),
        source_claim_ids=[str(claim_id) for claim_id in entry.get("claimIds") or []],
    )
    natural_response = str(readable.get("body") or natural_response)
    tension_pattern = str(readable.get("stuckPattern") or tension_pattern)
    return {
        "key": config["key"],
        "point": point,
        "title": config["title"],
        "placement": placement,
        "sign": entry.get("sign"),
        "signLabel": entry.get("signLabel"),
        "element": entry.get("element"),
        "elementLabel": entry.get("elementLabel"),
        "modality": entry.get("modality"),
        "modalityLabel": entry.get("modalityLabel"),
        "style": entry.get("style"),
        "suitableFor": natural_response,
        "doesNotFit": tension_pattern,
        "naturalResponse": natural_response,
        "tensionPattern": tension_pattern,
        "relationshipUse": config["relationship_use"],
        "elementStyle": entry.get("elementStyle"),
        "modalityStyle": entry.get("modalityStyle"),
        "readableInterpretation": readable,
        "confidence": entry.get("confidence") or "medium",
    }


def profile_baseline_card_text(card: dict[str, Any], *, field: str = "naturalResponse") -> str:
    readable = card.get("readableInterpretation") if isinstance(card.get("readableInterpretation"), dict) else {}
    if field == "stuck":
        value = readable.get("stuckPattern") or card.get("tensionPattern") or card.get("doesNotFit")
    else:
        value = readable.get("body") or card.get("naturalResponse") or card.get("suitableFor") or card.get("style")
    return normalize_zh_text(value)


def profile_baseline_sentence(card: dict[str, Any], fallback: str, *, field: str = "naturalResponse") -> str:
    placement = str(card.get("placement") or "")
    body = profile_baseline_card_text(card, field=field)
    if placement and body:
        return normalize_zh_text(f"{placement}：{body}")
    return normalize_zh_text(body or fallback)


def western_profile_translation_baseline(cards_by_point: dict[str, dict[str, Any]], role_label: str) -> dict[str, str]:
    moon = cards_by_point.get("Moon") or {}
    mercury = cards_by_point.get("Mercury") or {}
    venus = cards_by_point.get("Venus") or {}
    mars = cards_by_point.get("Mars") or {}
    saturn = cards_by_point.get("Saturn") or {}
    subject = "你" if role_label == "你" else "他"
    emotional_need = profile_baseline_sentence(
        moon,
        f"{subject}需要先感覺關係是安全、穩定、可以被回應的。",
    )
    love_language = profile_baseline_sentence(
        venus,
        f"{subject}比較容易透過日常裡可感受到的善意確認被喜歡。",
    )
    communication_style = profile_baseline_sentence(
        mercury,
        f"{subject}需要把話說到能理解、能接住的位置。",
    )
    conflict_response = profile_baseline_sentence(
        mars or saturn,
        f"{subject}在緊張時會先用自己的速度保護自己。",
        field="stuck",
    )
    commitment_rhythm = profile_baseline_sentence(
        saturn,
        f"{subject}需要看見關係能不能落到可持續的現實行動。",
    )
    withdrawal_trigger = profile_baseline_sentence(
        saturn or moon,
        f"{subject}在被催促、被審問或感覺沒有退路時，會比較難自然回應。",
        field="stuck",
    )
    closeness_trigger = profile_baseline_sentence(
        venus or moon,
        f"{subject}在感覺被尊重、被理解、沒有被逼著表態時，比較容易靠近。",
    )
    misunderstanding_risk = normalize_zh_text(
        f"{subject}的反應如果變慢，未必能直接讀成沒感覺；更需要看後續是否有穩定、自然、可延續的行動。"
    )
    return {
        "roleLabel": role_label,
        "emotionalNeed": emotional_need,
        "loveLanguage": love_language,
        "communicationStyle": communication_style,
        "conflictResponse": conflict_response,
        "commitmentRhythm": commitment_rhythm,
        "closenessTrigger": closeness_trigger,
        "withdrawalTrigger": withdrawal_trigger,
        "misunderstandingRisk": misunderstanding_risk,
        "summary": normalize_zh_text(f"{emotional_need}；{communication_style}；{conflict_response}"),
    }


def western_relationship_profile_for_person(
    fixture: dict[str, Any],
    case_file: dict[str, Any],
    person: str,
) -> dict[str, Any]:
    person_key = "personA" if person == "person_a" else "personB"
    role_label = PERSON_LABELS.get(person, person)
    identity_person = ((case_file.get("identityLayer") or {}).get(person_key) or {})
    quality = ((case_file.get("inputQuality") or {}).get(person_key) or {})
    cards = [
        card
        for point in FUNCTION_MATRIX_POINTS
        if (card := western_relationship_profile_card(fixture, person, role_label, point))
    ]
    cards_by_point = {str(card.get("point")): card for card in cards}
    moon = cards_by_point.get("Moon") or {}
    venus = cards_by_point.get("Venus") or {}
    mercury = cards_by_point.get("Mercury") or {}
    saturn = cards_by_point.get("Saturn") or {}
    headline_bits = [str(moon.get("placement") or ""), str(venus.get("placement") or "")]
    headline_detail = " + ".join(bit for bit in headline_bits if bit) or "本命關係功能"
    summary_parts = [
        f"安全感：{moon.get('naturalResponse')}" if moon.get("naturalResponse") else "",
        f"溝通：{mercury.get('naturalResponse')}" if mercury.get("naturalResponse") else "",
        f"防衛：{saturn.get('naturalResponse')}" if saturn.get("naturalResponse") else "",
    ]
    partner_expectation = next(
        (
            {
                "point": need.get("point"),
                "placement": need.get("label"),
                "style": need.get("meaning"),
                "confidence": need.get("confidence") or "medium",
                "precisionNote": need.get("precisionNote"),
            }
            for need in identity_person.get("needs") or []
            if isinstance(need, dict) and need.get("point") == "Desc"
        ),
        None,
    )
    precision_warnings = [
        str(item)
        for item in quality.get("warnings") or []
        if item
    ]
    if quality.get("moonConfidence") == "low":
        precision_warnings.append("Moon 相關安全感語氣已降為低信心。")
    if quality and not quality.get("housesAllowed"):
        precision_warnings.append("Asc/Desc、宮位與 overlay 不作為本次人格或關係結論。")
    confidence = "low" if any(card.get("confidence") == "low" for card in cards) else "high" if cards else "low"
    return {
        "role": person,
        "label": role_label,
        "headline": f"{role_label}的關係風格：{headline_detail}",
        "summary": join_zh_clauses(summary_parts) or "本次可用本命關係功能不足，需保守解讀。",
        "precision": quality.get("precision"),
        "confidence": confidence,
        "cards": cards,
        "translationBaseline": western_profile_translation_baseline(cards_by_point, role_label),
        "suitableFor": [
            str(card.get("suitableFor"))
            for card in cards
            if card.get("point") in {"Moon", "Mercury", "Venus"} and card.get("suitableFor")
        ][:3],
        "doesNotFit": [
            str(card.get("doesNotFit"))
            for card in cards
            if card.get("point") in {"Moon", "Mercury", "Saturn"} and card.get("doesNotFit")
        ][:3],
        "partnerExpectation": partner_expectation,
        "precisionWarnings": unique(precision_warnings),
    }


def western_profile_fit_item(fixture: dict[str, Any], point: str) -> dict[str, Any] | None:
    style_a = western_function_style_entry(fixture, "person_a", "你", point)
    style_b = western_function_style_entry(fixture, "person_b", "對方", point)
    if not style_a or not style_b:
        return None
    element_a = str(style_a.get("element") or "")
    element_b = str(style_b.get("element") or "")
    relation = western_element_relation(element_a, element_b)
    if relation == "unknown":
        return None
    point_label = POINT_LABELS.get(point, point)
    relation_label = {
        "natural": "比較容易懂彼此",
        "effort": "需要慢慢對齊",
        "friction": "容易摩擦",
    }.get(relation, "需要觀察")
    confidence = "low" if style_a.get("confidence") == "low" or style_b.get("confidence") == "low" else "medium"
    source_claim_ids = unique([
        *[str(claim_id) for claim_id in style_a.get("claimIds") or []],
        *[str(claim_id) for claim_id in style_b.get("claimIds") or []],
    ])
    readable = fit_item_readable_interpretation(
        point=point,
        relation=relation,
        relation_label=relation_label,
        title=point_label,
        person_a_element=element_a,
        person_a_element_label=str(style_a.get("elementLabel") or ""),
        person_b_element=element_b,
        person_b_element_label=str(style_b.get("elementLabel") or ""),
        confidence=confidence,
        source_claim_ids=source_claim_ids,
    )
    return {
        "point": point,
        "title": f"{point_label}：{relation_label}",
        "relation": relation,
        "relationLabel": relation_label,
        "personA": f"{style_a.get('signLabel')} / {style_a.get('elementLabel')} / {style_a.get('modalityLabel')}",
        "personB": f"{style_b.get('signLabel')} / {style_b.get('elementLabel')} / {style_b.get('modalityLabel')}",
        "body": str(readable.get("body") or ""),
        "nextMove": readable.get("nextMove"),
        "readableInterpretation": readable,
        "source": "western-initial-comparison-elements",
        "confidence": confidence,
    }


def western_safety_validation_fit_item(cluster: dict[str, Any]) -> dict[str, Any] | None:
    if not cluster or not cluster.get("itemCount"):
        return None
    relation = str(cluster.get("dominantContactType") or "effort")
    if relation not in {"natural", "effort", "friction"}:
        relation = "effort"
    relation_label = SAFETY_VALIDATION_RELATION_LABELS[relation]
    pairs = [pair for pair in cluster.get("pairs") or [] if isinstance(pair, dict)]
    strongest_pair = next((pair for pair in pairs if pair.get("relation") == relation), pairs[0] if pairs else {})
    body = safety_validation_fit_body(cluster, strongest_pair, relation)
    next_move = safety_validation_next_move(cluster, relation)
    readable = {
        "version": "readable-interpretation-v1",
        "module": "fit_summary_item",
        "locale": "zh-TW",
        "headline": f"安全感與被重視：{relation_label}",
        "meaning": "這一項看月亮代表的安心需求，和金星代表的喜歡、欣賞、被放在心上的方式；重點不是判斷愛不愛，而是看靠近時能不能讓彼此真的舒服。",
        "body": normalize_zh_text(body),
        "nextMove": normalize_zh_text(next_move),
        "confidenceNote": "因為有人的出生時間不完整，月亮位置可能跨星座；這一項只能保守參考。" if cluster.get("lowConfidenceCount") else None,
        "sourceClaimIds": [str(claim_id) for claim_id in cluster.get("claimIds") or []],
        "debug": {
            "relation": relation,
            "naturalLanguageCount": cluster.get("naturalLanguageCount"),
            "effortLanguageCount": cluster.get("effortLanguageCount"),
            "frictionLanguageCount": cluster.get("frictionLanguageCount"),
        },
    }
    return {
        "point": "MoonVenus",
        "title": f"安全感與被重視：{relation_label}",
        "relation": relation,
        "relationLabel": relation_label,
        "personA": str(strongest_pair.get("personA") or "你的 Moon/Venus 語言"),
        "personB": str(strongest_pair.get("personB") or "對方的 Moon/Venus 語言"),
        "body": normalize_zh_text(body),
        "nextMove": readable.get("nextMove"),
        "readableInterpretation": readable,
        "source": str(cluster.get("source") or "western-safety-validation-language"),
        "confidence": str(cluster.get("confidence") or "medium"),
    }


PIVOTAL_ASPECT_RELATION_LABELS = {
    "natural": "可以先靠近的入口",
    "effort": "有牽動但要慢慢接住",
    "friction": "最容易被觸發的卡點",
}


def pivotal_aspect_relation(contact_type: str) -> str:
    if contact_type == "soft":
        return "natural"
    if contact_type == "hard":
        return "friction"
    return "effort"


def pivotal_aspect_fit_body(item: dict[str, Any], relation: str) -> str:
    synthesis = str(item.get("functionSynthesis") or item.get("contactText") or "")
    label = str(item.get("label") or item.get("pairKey") or "這個相位")
    pair_template = item.get("pairContactTemplate") or {}
    pair_interpretation = zh_clause(pair_template.get("interpretation"))
    pair_guardrail = zh_clause(pair_template.get("doesNotProve"))
    pair_sentence = f" 這組行星互動會被讀成：{pair_interpretation}。" if pair_interpretation else ""
    guardrail_sentence = f" 但它的邊界是：{pair_guardrail}。" if pair_guardrail else ""
    reinforced_labels = [str(label) for label in item.get("reinforcedThemeLabels") or [] if label]
    reinforced_sentence = ""
    if reinforced_labels:
        reinforced_sentence = (
            f" 這個訊號同時落在「{'、'.join(reinforced_labels[:2])}」這類重複主題裡，"
            "解讀會先看這個模式如何反覆影響你們互動。"
        )
    if relation == "natural":
        return (
            f"這個重點相位會被放進結果，是因為「{label}」比較像你們能接上彼此的入口。"
            f"{synthesis}{pair_sentence}{reinforced_sentence} 這代表有可以放輕靠近的地方，但不能直接當成承諾或復合保證。"
            f"{guardrail_sentence}"
        )
    if relation == "friction":
        return (
            f"這個重點相位會被放進結果，是因為「{label}」很容易反覆觸發你們卡住的地方。"
            f"{synthesis}{pair_sentence}{reinforced_sentence} 重點不是判誰錯，而是看哪一種刺激需要先降下來。"
            f"{guardrail_sentence}"
        )
    return (
        f"這個重點相位會被放進結果，是因為「{label}」有明顯牽動，但不一定會自然變順。"
        f"{synthesis}{pair_sentence}{reinforced_sentence} 它需要慢慢接住，不能只靠感覺或一次對話解決。"
        f"{guardrail_sentence}"
    )


def pivotal_aspect_next_move(relation: str) -> str:
    if relation == "natural":
        return "可以把它當作低壓靠近的入口，但訊息仍要短、輕、可退場。"
    if relation == "friction":
        return "先處理容易被觸發的語氣、速度或防衛，不要急著逼出答案。"
    return "先讓互動變穩，再談更深的關係問題；不要把牽動直接推成承諾。"


def western_pivotal_aspect_fit_item(cluster: dict[str, Any]) -> dict[str, Any] | None:
    selected = [item for item in cluster.get("selectedCombinations") or [] if isinstance(item, dict)]
    if not selected:
        return None
    item = selected[0]
    contact_type = str(item.get("contactType") or "")
    relation = pivotal_aspect_relation(contact_type)
    relation_label = PIVOTAL_ASPECT_RELATION_LABELS[relation]
    body = normalize_zh_text(pivotal_aspect_fit_body(item, relation))
    next_move = normalize_zh_text(pivotal_aspect_next_move(relation))
    pair_template = item.get("pairContactTemplate") or {}
    claim_ids = unique([
        *[str(claim_id) for claim_id in cluster.get("claimIds") or []],
        *[str(claim_id) for claim_id in item.get("claimIds") or []],
    ])
    readable = {
        "version": "readable-interpretation-v1",
        "module": "fit_summary_item",
        "locale": "zh-TW",
        "headline": f"關鍵合盤相位：{relation_label}",
        "meaning": "這一項只展示最能解釋你們互動的關鍵合盤相位；它不是完整相位清單，也不是命運判決。",
        "body": body,
        "nextMove": next_move,
        "sourceClaimIds": claim_ids,
        "debug": {
            "pairKey": item.get("pairKey"),
            "contactType": contact_type,
            "strength": item.get("strength"),
            "selectedCount": cluster.get("itemCount"),
            "pairContactTemplateId": pair_template.get("atomId") or pair_template.get("id"),
        },
    }
    return {
        "point": "PivotalAspect",
        "title": f"關鍵合盤相位：{relation_label}",
        "relation": relation,
        "relationLabel": relation_label,
        "personA": str(item.get("personAPoint") or ""),
        "personB": str(item.get("personBPoint") or ""),
        "body": body,
        "nextMove": next_move,
        "readableInterpretation": readable,
        "pairContactTemplate": pair_template,
        "pairContactTemplateMeaning": str(pair_template.get("interpretation") or ""),
        "pairContactTemplateGuardrail": str(pair_template.get("doesNotProve") or ""),
        "source": str(item.get("aspectSource") or cluster.get("source") or "western-aspect-function-combination-reducers"),
        "confidence": str(cluster.get("confidence") or "medium"),
    }


def western_relationship_profiles(
    fixture: dict[str, Any],
    case_file: dict[str, Any],
) -> dict[str, Any]:
    clusters = case_file.get("evidenceClusters") or {}
    input_quality = case_file.get("inputQuality") or {}
    safety_validation_cluster = clusters.get("safetyValidationLanguage") or {}
    aspect_function_cluster = clusters.get("aspectFunctionCombination") or {}
    fit_items = [
        item
        for point in FUNCTION_MATRIX_POINTS
        if (item := western_profile_fit_item(fixture, point))
    ]
    if pivotal_aspect_item := western_pivotal_aspect_fit_item(aspect_function_cluster):
        fit_items.insert(0, pivotal_aspect_item)
    if safety_validation_item := western_safety_validation_fit_item(safety_validation_cluster):
        fit_items.append(safety_validation_item)
    natural = [item for item in fit_items if item.get("relation") == "natural"]
    effort = [item for item in fit_items if item.get("relation") == "effort"]
    friction = [item for item in fit_items if item.get("relation") == "friction"]
    element_cluster = clusters.get("elementComparison") or {}
    fit_readable = fit_summary_readable_interpretation(
        natural_count=len(natural),
        effort_count=len(effort),
        friction_count=len(friction),
        source_claim_ids=[str(claim_id) for claim_id in element_cluster.get("claimIds") or []],
    )
    fit_headline = str(fit_readable.get("headline") or "關係風格需要更多翻譯")
    person_a_profile = western_relationship_profile_for_person(fixture, case_file, "person_a")
    person_b_profile = western_relationship_profile_for_person(fixture, case_file, "person_b")
    precision_warnings: list[str] = []
    for person_key in ("personA", "personB"):
        quality = (input_quality.get(person_key) or {})
        precision_warnings.extend(str(item) for item in quality.get("warnings") or [] if item)
        if quality and not quality.get("housesAllowed"):
            precision_warnings.append(f"{quality.get('label') or person_key}缺少可靠時間或城市，Asc/Desc、宮位與 overlay 已封鎖。")
    return {
        "version": "relationship-profiles-v1",
        "principle": "先看兩個人的本命關係操作方式，再看哪些地方比較容易懂彼此、哪些地方需要慢慢對齊，最後才回答用戶問題。",
        "personA": person_a_profile,
        "personB": person_b_profile,
        "translationBaseline": {
            "version": "relationship-translation-baseline-v1",
            "personA": person_a_profile.get("translationBaseline") or {},
            "personB": person_b_profile.get("translationBaseline") or {},
            "principle": "後續四頁必須從這裡取用你和他的關係使用說明，再加入合盤、問題與時機；不能直接把所有頁面寫成同一個行動建議。",
        },
        "fitSummary": {
            "headline": fit_headline,
            "summary": f"比較容易懂彼此 {len(natural)} 項、需要慢慢對齊 {len(effort)} 項、容易摩擦 {len(friction)} 項；這是回答問題前的關係底層結構。",
            "natural": natural,
            "effort": effort,
            "friction": friction,
            "safetyValidationLanguage": safety_validation_cluster,
            "readableInterpretation": fit_readable,
            "doesNotProve": str(element_cluster.get("doesNotProve") or "契合或摩擦不能單獨判斷關係成敗。"),
            "source": str(element_cluster.get("source") or "western-initial-comparison-elements"),
            "atomId": element_cluster.get("atomId"),
            "pivotalAspect": pivotal_aspect_item,
            "claimIds": unique([*(element_cluster.get("claimIds") or []), *(safety_validation_cluster.get("claimIds") or []), *(aspect_function_cluster.get("claimIds") or [])]),
            "claimSupport": [*(element_cluster.get("claimSupport") or []), *(safety_validation_cluster.get("claimSupport") or []), *(aspect_function_cluster.get("claimSupport") or [])],
        },
        "precisionWarnings": unique(precision_warnings),
        "answerBridge": "這一層先建立雙方的關係風格、自然靠近方式與容易誤會的互動條件；後面的問題答案才加入合盤相位、壓力、修復與行運判斷。",
        "sourceClusters": [
            "identityNeeds",
            "moonSignEmotionalSafety",
            "mercurySignCommunicationRepair",
            "venusSignAffectionStyle",
            "marsSignPursuitConflict",
            "saturnSignDefenseDelay",
            "functionElementMatrix",
            "functionModalityMatrix",
            "elementComparison",
            "safetyValidationLanguage",
            "aspectFunctionCombination",
        ],
    }


def western_luminary_comparison_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "luminaryComparison"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "日月核心比較")
    source = str(atom.get("source_article_id") or "western-interchart-aspect-priorities")
    luminary_aspects = [
        aspect
        for aspect in western_synastry_aspects(fixture)
        if {str(aspect.get("person_a_point") or ""), str(aspect.get("person_b_point") or "")}.issubset({"Sun", "Moon"})
    ]
    luminary_aspects = sorted(luminary_aspects, key=western_aspect_sort_key, reverse=True)
    best = luminary_aspects[0] if luminary_aspects else {}
    if best:
        technical = western_aspect_sentence(best)
        strength = western_aspect_strength(best)
    else:
        pairs = []
        for point in ("Sun", "Moon"):
            obj_a = western_object(fixture, "person_a", point) or {}
            obj_b = western_object(fixture, "person_b", point) or {}
            if obj_a and obj_b:
                pairs.append(
                    f"{POINT_LABELS[point]}元素：{WESTERN_ELEMENT_LABELS.get(str(obj_a.get('sign_element') or ''), '未知')} / {WESTERN_ELEMENT_LABELS.get(str(obj_b.get('sign_element') or ''), '未知')}"
                )
        technical = "；".join(pairs) if pairs else "日月資料不足"
        strength = 0.45 if pairs else 0.2
    points = {str(best.get("person_a_point") or ""), str(best.get("person_b_point") or "")}
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": len(luminary_aspects),
        "strongestStrength": round(strength, 3),
        "averageStrength": round(sum(western_aspect_strength(aspect) for aspect in luminary_aspects) / max(len(luminary_aspects), 1), 3),
        "dominantContactType": western_aspect_contact_type(best) if best else "element_baseline",
        "strongestEvidenceId": "luminary-" + "-".join(sorted(points)) if best else None,
        "hasSunMoonContact": points == {"Sun", "Moon"},
        "hasSunSunContact": points == {"Sun"},
        "hasMoonMoonContact": points == {"Moon"},
        "summary": str(interpretation_atom.get("summary_template") or "{label}有{item_count}個可展示日月訊號；主訊號是：{technical}。").format(
            label=label,
            item_count=len(luminary_aspects),
            technical=technical,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "日月比較用來判斷核心與情緒是否能互相看見。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "日月訊號不能保證承諾。"),
        "confidence": "medium" if best else "low",
        "source": source,
    }


def western_ascendant_impression_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "ascendantImpression"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "上升第一印象")
    source = str(atom.get("source_article_id") or "western-natal-relationship-potential")
    allowed = western_houses_allowed(fixture, "person_a") and western_houses_allowed(fixture, "person_b")
    asc_a = western_object(fixture, "person_a", "Asc") if allowed else None
    asc_b = western_object(fixture, "person_b", "Asc") if allowed else None
    if asc_a and asc_b:
        sign_a = SIGN_LABELS.get(str(asc_a.get("sign") or ""), str(asc_a.get("sign") or "未知"))
        sign_b = SIGN_LABELS.get(str(asc_b.get("sign") or ""), str(asc_b.get("sign") or "未知"))
        technical = f"你上升{sign_a}；對方上升{sign_b}"
        item_count = 2
        strength = 0.56
        display = "allowed"
    else:
        technical = "出生時間或地點不足，上升/第一印象層封鎖"
        item_count = 0
        strength = 0.18
        display = "blocked"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": item_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": display,
        "strongestEvidenceId": "ascendant-impression" if item_count else None,
        "allowedCount": item_count,
        "blockedCount": 0 if item_count else 1,
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=item_count,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "上升只在精度可靠時補充初見反應。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "上升不能單獨證明感情深度。"),
        "confidence": "medium" if item_count else "low",
        "source": source,
    }


def western_house_relationship_factors_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "houseRelationshipFactors"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "關係宮位因素")
    source = str(atom.get("source_article_id") or "western-natal-relationship-potential")
    precision_gate = western_house_angle_precision_gate(fixture)
    allowed_people = [person for person in ("person_a", "person_b") if western_houses_allowed(fixture, person)]
    relationship_points = ["Venus", "Mars", "Saturn", "Desc"]
    details: list[str] = []
    for person, role_label in (("person_a", "你"), ("person_b", "對方")):
        if person not in allowed_people:
            continue
        for point in relationship_points:
            obj = western_object(fixture, person, point) or {}
            house = obj.get("house")
            if isinstance(house, int):
                details.append(f"{role_label}{POINT_LABELS.get(point, point)}{house}宮")
    item_count = len(details)
    if item_count:
        technical = "；".join(details[:6]) + "；overlay/composite 尚未計算"
        strength = 0.5
        status = "natal_houses_only"
    else:
        technical = "出生時間/地點不足，或 house/overlay engine 尚未開放"
        strength = 0.16
        status = "blocked_or_not_available"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": item_count,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": status,
        "strongestEvidenceId": "house-relationship-factors" if item_count else None,
        "allowedCount": item_count,
        "blockedCount": 0 if item_count else 1,
        "houseAnglePrecisionGate": precision_gate,
        "sourceClaimIds": HOUSE_ANGLE_PRECISION_CLAIM_IDS,
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=item_count,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "宮位與 overlay 必須精度可靠後才展示。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "缺時間或缺地點不可補寫宮位。"),
        "confidence": "low",
        "source": source,
    }


def western_aspect_priority_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "aspectPriority"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "交互相位優先序")
    source = str(atom.get("source_article_id") or "western-interchart-aspect-priorities")
    priority_pairs = [
        frozenset(("Sun", "Moon")),
        frozenset(("Moon", "Moon")),
        frozenset(("Sun", "Sun")),
        frozenset(("Sun", "Venus")),
        frozenset(("Venus", "Mars")),
        frozenset(("Moon", "Venus")),
        frozenset(("Moon", "Mars")),
        frozenset(("Venus", "Venus")),
        frozenset(("Mars", "Mars")),
        frozenset(("Mercury", "Mercury")),
        frozenset(("Mercury", "Sun")),
        frozenset(("Mercury", "Jupiter")),
        frozenset(("Mercury", "Moon")),
        frozenset(("Mercury", "Mars")),
        frozenset(("Venus", "Saturn")),
        frozenset(("Moon", "Saturn")),
        frozenset(("Mars", "Saturn")),
    ]

    def priority_score(aspect: dict[str, Any]) -> tuple[int, float]:
        pair = frozenset((str(aspect.get("person_a_point") or ""), str(aspect.get("person_b_point") or "")))
        rank = priority_pairs.index(pair) if pair in priority_pairs else len(priority_pairs)
        return (-rank, western_aspect_strength(aspect))

    selected = sorted(
        [aspect for aspect in western_synastry_aspects(fixture) if aspect.get("eligible_for_signal", True)],
        key=priority_score,
        reverse=True,
    )[:3]
    best = selected[0] if selected else {}
    best_modifier = western_aspect_contact_modifier(best, structured_kb) if best else None
    technical = "；".join(western_aspect_sentence(aspect) for aspect in selected) if selected else "沒有足夠優先相位"
    tight_orbs = [float(aspect.get("orb") or 99) for aspect in selected]
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": len(selected),
        "strongestStrength": round(western_aspect_strength(best), 3) if best else 0.0,
        "averageStrength": round(sum(western_aspect_strength(aspect) for aspect in selected) / max(len(selected), 1), 3),
        "dominantContactType": western_aspect_contact_type(best) if best else "none",
        "dominantContactModifier": best_modifier,
        "contactModifierSummary": str((best_modifier or {}).get("interpretation") or ""),
        "selectedContactModifiers": [western_aspect_contact_modifier(aspect, structured_kb) for aspect in selected],
        "strongestEvidenceId": f"aspect-priority-{best.get('person_a_point')}-{best.get('person_b_point')}" if best else None,
        "hasDirectionality": bool(best),
        "tightestOrb": round(min(tight_orbs), 3) if tight_orbs else None,
        "hasTightOrb": bool(tight_orbs and min(tight_orbs) <= 3.0),
        "summary": str(interpretation_atom.get("summary_template") or "{label}選出{item_count}個優先相位；主訊號是：{technical}。").format(
            label=label,
            item_count=len(selected),
            technical=technical,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "先選最相關、orb 較緊、方向性清楚的相位。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "優先相位不能保證復合。"),
        "confidence": "medium" if selected else "low",
        "source": source,
    }


def western_aspect_function_style_claim_ids(style: dict[str, Any] | None) -> list[str]:
    if not style:
        return []
    claim_ids: list[str] = []
    sign = str(style.get("sign") or "")
    element = str(style.get("element") or "")
    modality = str(style.get("modality") or "")
    if SIGN_CLAIM_IDS.get(sign):
        claim_ids.append(str(SIGN_CLAIM_IDS[sign]))
    if ELEMENT_CLAIM_IDS.get(element):
        claim_ids.append(str(ELEMENT_CLAIM_IDS[element]))
    if MODALITY_CLAIM_IDS.get(modality):
        claim_ids.append(str(MODALITY_CLAIM_IDS[modality]))
    return claim_ids


def western_aspect_function_synthesis(
    aspect: dict[str, Any],
    point_styles: list[dict[str, Any]],
    contact_text: str,
) -> str:
    parts: list[str] = []
    for style in point_styles:
        point = str(style.get("point") or "")
        parts.append(
            f"{style.get('roleLabel')}{POINT_LABELS.get(point, point)}{style.get('signLabel')}"
            f"（{style.get('elementLabel')}／{style.get('modalityLabel')}）：{style.get('style')}"
        )
    technical = western_aspect_sentence(aspect)
    return join_zh_clauses([technical, *parts, contact_text])


def western_aspect_repeated_theme_keys(
    *,
    pair_key: str,
    relationship_function: str,
    aspect_source: str,
    person_a_point: str,
    person_b_point: str,
) -> list[str]:
    points = {person_a_point, person_b_point}
    pair_points = set(pair_key.split("-"))
    function = relationship_function.lower()
    theme_keys: list[str] = []
    has_outer_intensity = aspect_source == "western-aspects-outer-planet-intensity-families" or bool(points.intersection(WESTERN_OUTER_PLANETS))

    if not has_outer_intensity and (
        "Saturn" in pair_points or "pressure" in function or "boundary" in function or "responsibility" in function
    ):
        theme_keys.append("saturn_pressure")
    if "Moon" in pair_points or "emotional" in function or "safety" in function or "validation" in function:
        theme_keys.append("emotional_safety")
    if "Mercury" in pair_points or "communication" in function or "repair" in function:
        theme_keys.append("communication_repair")
    if (
        pair_key in {"Venus-Mars", "Sun-Venus", "Moon-Venus", "Venus-Venus", "Sun-Mars"}
        or "attraction" in function
        or "affection" in function
        or "desire" in function
        or "pursuit" in function
    ):
        theme_keys.append("attraction_pursuit")
    if "Mars" in pair_points or "action" in function or "conflict" in function or "activation" in function:
        theme_keys.append("action_conflict")
    if (
        "Sun" in pair_points
        or pair_key in {"Sun-Moon", "Moon-Moon"}
        or "identity" in function
        or "self" in function
        or "core" in function
    ):
        theme_keys.append("identity_rhythm")
    if has_outer_intensity:
        theme_keys.append("outer_intensity")

    return unique(theme_keys)


def western_repeated_theme_label(theme_key: str) -> str:
    return str((REPEATED_THEME_REDUCER_CONFIG.get(theme_key) or {}).get("label") or theme_key)


def western_repeated_theme_analysis(
    detected_pairs: list[dict[str, Any]],
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_theme_keys: list[str] = []
    for item in selected:
        theme_keys = western_aspect_repeated_theme_keys(
            pair_key=str(item.get("pairKey") or ""),
            relationship_function=str(item.get("relationshipFunction") or ""),
            aspect_source=str(item.get("aspectSource") or ""),
            person_a_point=str(item.get("personAPoint") or ""),
            person_b_point=str(item.get("personBPoint") or ""),
        )
        item["themeKeys"] = theme_keys
        item["themeLabels"] = [western_repeated_theme_label(theme_key) for theme_key in theme_keys]
        selected_theme_keys.extend(theme_keys)

    theme_entries: dict[str, dict[str, Any]] = {}
    for detected in detected_pairs:
        theme_keys = western_aspect_repeated_theme_keys(
            pair_key=str(detected.get("pairKey") or ""),
            relationship_function=str(detected.get("relationshipFunction") or ""),
            aspect_source=str(detected.get("aspectSource") or ""),
            person_a_point=str(detected.get("personAPoint") or ""),
            person_b_point=str(detected.get("personBPoint") or ""),
        )
        for theme_key in theme_keys:
            config = REPEATED_THEME_REDUCER_CONFIG.get(theme_key) or {}
            entry = theme_entries.setdefault(
                theme_key,
                {
                    "themeKey": theme_key,
                    "label": str(config.get("label") or theme_key),
                    "count": 0,
                    "selectedCount": 0,
                    "contactTypes": [],
                    "pairKeys": [],
                    "relationshipFunctions": [],
                    "selectedEvidenceIds": [],
                    "maxStrength": 0.0,
                    "averageStrength": 0.0,
                    "interpretation": str(config.get("interpretation") or ""),
                    "reducerInstruction": str(config.get("instruction") or ""),
                    "doesNotProve": "重複主題只能提高解讀優先序，不能證明愛、不愛、聯絡、承諾或復合結果。",
                },
            )
            strength = float(detected.get("strength") or 0)
            entry["count"] = int(entry.get("count") or 0) + 1
            entry["_strengthTotal"] = float(entry.get("_strengthTotal") or 0) + strength
            entry["maxStrength"] = max(float(entry.get("maxStrength") or 0), strength)
            entry["contactTypes"] = unique([*entry.get("contactTypes", []), str(detected.get("contactType") or "")])
            entry["pairKeys"] = unique([*entry.get("pairKeys", []), str(detected.get("pairKey") or "")])
            entry["relationshipFunctions"] = unique(
                [*entry.get("relationshipFunctions", []), str(detected.get("relationshipFunction") or "")]
            )
            selected_evidence_id = str(detected.get("selectedEvidenceId") or "")
            if selected_evidence_id:
                entry["selectedEvidenceIds"] = unique([*entry.get("selectedEvidenceIds", []), selected_evidence_id])

    repeated_themes = []
    for entry in theme_entries.values():
        if int(entry.get("count") or 0) < 2:
            continue
        count = max(int(entry.get("count") or 0), 1)
        entry["selectedCount"] = len(entry.get("selectedEvidenceIds") or [])
        entry["averageStrength"] = round(float(entry.pop("_strengthTotal", 0.0)) / count, 3)
        entry["maxStrength"] = round(float(entry.get("maxStrength") or 0), 3)
        repeated_themes.append(entry)

    repeated_themes = sorted(
        repeated_themes,
        key=lambda entry: (
            int(entry.get("count") or 0),
            int(entry.get("selectedCount") or 0),
            int((REPEATED_THEME_REDUCER_CONFIG.get(str(entry.get("themeKey") or "")) or {}).get("priority") or 0),
            float(entry.get("maxStrength") or 0),
        ),
        reverse=True,
    )
    reinforced_theme_keys = [str(entry.get("themeKey") or "") for entry in repeated_themes]
    for item in selected:
        reinforced_keys = [theme_key for theme_key in item.get("themeKeys") or [] if theme_key in reinforced_theme_keys]
        item["reinforcedThemeKeys"] = reinforced_keys
        item["reinforcedThemeLabels"] = [western_repeated_theme_label(theme_key) for theme_key in reinforced_keys]

    dominant = repeated_themes[0] if repeated_themes else None
    dominant_label = str((dominant or {}).get("label") or "")
    if dominant:
        summary = f"本次合盤有 {len(repeated_themes)} 組重複主題；最需要優先讀的是「{dominant_label}」。"
    else:
        summary = "本次合盤沒有足夠重複的相位主題；仍以最關鍵的單一合盤相位做保守解讀。"
    return {
        "version": "repeated-theme-reducer-v1",
        "source": "burk-repeated-themes-outweigh-single-contacts",
        "methodClaimIds": REPEATED_THEME_REDUCER_METHOD_CLAIM_IDS,
        "selectedThemeKeys": unique(selected_theme_keys),
        "repeatedThemes": repeated_themes,
        "reinforcedThemeKeys": reinforced_theme_keys,
        "reinforcedThemeCount": len(repeated_themes),
        "dominantRepeatedTheme": dominant,
        "dominantRepeatedThemeKey": str((dominant or {}).get("themeKey") or ""),
        "dominantRepeatedThemeLabel": dominant_label,
        "summary": summary,
        "reducerInstruction": "當同一種關係主題反覆出現時，核心問題、時機判讀與行動方向要先處理這個重複主題，再解釋單一相位；不可用單一相位直接判斷結果。",
        "doesNotProve": "重複主題只代表解讀優先序提高，不代表對方一定還愛、一定會回來或一定不能修復。",
        "hasRepeatedThemeEvidence": bool(repeated_themes),
        "hasRepeatedSaturnPressure": "saturn_pressure" in reinforced_theme_keys,
        "hasRepeatedEmotionalSafety": "emotional_safety" in reinforced_theme_keys,
        "hasRepeatedCommunicationRepair": "communication_repair" in reinforced_theme_keys,
        "hasRepeatedAttractionPursuit": "attraction_pursuit" in reinforced_theme_keys,
        "hasRepeatedActionConflict": "action_conflict" in reinforced_theme_keys,
        "hasRepeatedIdentityRhythm": "identity_rhythm" in reinforced_theme_keys,
        "hasRepeatedOuterIntensity": "outer_intensity" in reinforced_theme_keys,
    }


def western_aspect_function_combination_cluster(
    fixture: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "aspectFunctionCombination"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "相位功能組合")
    source = str(atom.get("source_article_id") or "western-aspect-function-combination-reducers")
    selected: list[dict[str, Any]] = []
    selected_claim_ids: list[str] = [str(claim_id) for claim_id in atom.get("claim_ids") or [] if claim_id]
    selected_method_claim_ids: list[str] = []
    detected_pairs: list[dict[str, Any]] = []

    for index, aspect in enumerate(
        sorted(
            [item for item in western_synastry_aspects(fixture) if item.get("eligible_for_signal", True)],
            key=western_aspect_sort_key,
            reverse=True,
        )
    ):
        article_id = western_aspect_article_id(aspect)
        config = western_aspect_function_config(aspect, article_id)
        if not config:
            continue
        contact_type = western_aspect_contact_type(aspect)
        contact_text = str(config.get(contact_type) or "")
        if not contact_text:
            continue

        point_a = str(aspect.get("person_a_point") or "")
        point_b = str(aspect.get("person_b_point") or "")
        strength = western_aspect_strength(aspect)
        detected_candidate = {
            "pairKey": str(config.get("pairKey") or ""),
            "aspectSource": article_id,
            "contactType": contact_type,
            "relationshipFunction": str(config.get("relationshipFunction") or ""),
            "personAPoint": point_a,
            "personBPoint": point_b,
            "aspect": str(aspect.get("aspect") or ""),
            "orb": aspect.get("orb"),
            "applying": bool(aspect.get("applying")),
            "strength": round(strength, 3),
        }
        detected_pairs.append(detected_candidate)
        if len(selected) >= 4:
            continue

        style_a = western_function_style_entry(fixture, "person_a", "你", point_a)
        style_b = western_function_style_entry(fixture, "person_b", "對方", point_b)
        point_styles = [style for style in (style_a, style_b) if style]
        aspect_atom = western_atom_for_source_article(structured_kb, article_id)
        aspect_claim_ids = [str(claim_id) for claim_id in aspect_atom.get("claim_ids") or [] if claim_id]
        source_claim_id = str(config.get("sourceClaimId") or "")
        pair_method_claim_ids = [str(claim_id) for claim_id in PAIR_FAMILY_METHOD_CLAIM_IDS.get(article_id, []) if claim_id]
        contact_modifier = western_aspect_contact_modifier(aspect, structured_kb)
        pair_contact_template = western_aspect_pair_contact_template(aspect, structured_kb)
        item_claim_ids = unique(
            [
                source_claim_id,
                *aspect_claim_ids,
                *[str(claim_id) for claim_id in contact_modifier.get("claimIds") or []],
                *[str(claim_id) for claim_id in (pair_contact_template or {}).get("claimIds") or []],
                *western_aspect_function_style_claim_ids(style_a),
                *western_aspect_function_style_claim_ids(style_b),
            ]
        )
        selected_claim_ids.extend(item_claim_ids)
        selected_method_claim_ids.extend(pair_method_claim_ids)
        function_synthesis = western_aspect_function_synthesis(aspect, point_styles, contact_text)
        selected_item = {
            "id": f"aspect-function-combination-{len(selected) + 1}",
            "pairKey": str(config.get("pairKey") or ""),
            "label": str(config.get("label") or ""),
            "source": source,
            "sourceClaimId": source_claim_id,
            "methodClaimIds": pair_method_claim_ids,
            "aspectAtomId": aspect_atom.get("id"),
            "aspectSource": article_id,
            "aspectClaimIds": aspect_claim_ids,
            "claimIds": item_claim_ids,
            "personAPoint": point_a,
            "personBPoint": point_b,
            "aspect": str(aspect.get("aspect") or ""),
            "aspectLabel": ASPECT_LABELS.get(str(aspect.get("aspect") or ""), str(aspect.get("aspect") or "相位")),
            "orb": aspect.get("orb"),
            "applying": bool(aspect.get("applying")),
            "strength": round(strength, 3),
            "contactType": contact_type,
            "relationshipFunction": str(config.get("relationshipFunction") or ""),
            "technical": western_aspect_sentence(aspect),
            "functionSynthesis": function_synthesis,
            "contactText": contact_text,
            "reducerInstruction": str(config.get("instruction") or ""),
            "pointStyles": point_styles,
            "contactModifier": contact_modifier,
            "pairContactTemplate": pair_contact_template,
            "precision": western_precision_gate_for_points(
                fixture,
                point_a,
                point_b,
                bool(aspect.get("eligible_for_signal", True)),
                structured_kb,
            ),
        }
        detected_candidate["selectedEvidenceId"] = selected_item["id"]
        selected.append(selected_item)

    item_count = len(selected)
    repeated_theme_reducer = western_repeated_theme_analysis(detected_pairs, selected)
    best = selected[0] if selected else {}
    strengths = [float(item.get("strength") or 0) for item in selected]
    hard_pairs = {str(item.get("pairKey") or "") for item in selected if item.get("contactType") == "hard"}
    saturn_pressure_pairs = {
        str(item.get("pairKey") or "")
        for item in selected
        if "Saturn" in str(item.get("pairKey") or "") and item.get("contactType") in {"hard", "conjunction"}
    }
    saturn_boundary = saturn_nonfatal_process_boundary(
        "synastry_saturn_pressure",
        evidence_keys=sorted(saturn_pressure_pairs),
    ) if saturn_pressure_pairs else None
    if saturn_boundary:
        selected_claim_ids.extend(GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS)
        selected_method_claim_ids.extend(GREENE_SATURN_PROCESS_METHOD_CLAIM_IDS)
    detected_hard_pairs = {str(item.get("pairKey") or "") for item in detected_pairs if item.get("contactType") == "hard"}
    detected_supportive_pairs = {
        str(item.get("pairKey") or "")
        for item in detected_pairs
        if item.get("contactType") in {"soft", "conjunction"}
    }
    detected_sources = unique([str(item.get("aspectSource") or "") for item in detected_pairs])
    selected_sources = unique([str(item.get("aspectSource") or "") for item in selected])
    has_outer_planet_intensity = "western-aspects-outer-planet-intensity-families" in detected_sources
    has_outer_planet_hard_intensity = any(
        item.get("aspectSource") == "western-aspects-outer-planet-intensity-families"
        and item.get("contactType") in {"hard", "conjunction"}
        for item in detected_pairs
    )
    technical = str(best.get("functionSynthesis") or interpretation_atom.get("empty_summary") or "本次沒有可展示的相位功能組合。")
    payload = {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": unique(selected_claim_ids),
        "itemCount": item_count,
        "strongestStrength": round(max(strengths), 3) if strengths else 0.0,
        "averageStrength": round(sum(strengths) / max(len(strengths), 1), 3),
        "dominantContactType": str(best.get("contactType") or "none"),
        "dominantPairKey": str(best.get("pairKey") or ""),
        "strongestEvidenceId": best.get("id"),
        "selectedPairs": unique([str(item.get("pairKey") or "") for item in selected]),
        "selectedSources": selected_sources,
        "detectedPairs": unique([str(item.get("pairKey") or "") for item in detected_pairs]),
        "detectedSources": detected_sources,
        "detectedPairDetails": detected_pairs,
        "selectedCombinations": selected,
        "repeatedThemeReducer": repeated_theme_reducer,
        "repeatedThemes": repeated_theme_reducer.get("repeatedThemes") or [],
        "repeatedThemeSummary": repeated_theme_reducer.get("summary"),
        "dominantRepeatedTheme": repeated_theme_reducer.get("dominantRepeatedTheme"),
        "dominantRepeatedThemeKey": repeated_theme_reducer.get("dominantRepeatedThemeKey"),
        "dominantRepeatedThemeLabel": repeated_theme_reducer.get("dominantRepeatedThemeLabel"),
        "repeatedThemeMethodClaimIds": repeated_theme_reducer.get("methodClaimIds") or [],
        "hasRepeatedThemeEvidence": repeated_theme_reducer.get("hasRepeatedThemeEvidence"),
        "hasRepeatedSaturnPressure": repeated_theme_reducer.get("hasRepeatedSaturnPressure"),
        "hasRepeatedEmotionalSafety": repeated_theme_reducer.get("hasRepeatedEmotionalSafety"),
        "hasRepeatedCommunicationRepair": repeated_theme_reducer.get("hasRepeatedCommunicationRepair"),
        "hasRepeatedAttractionPursuit": repeated_theme_reducer.get("hasRepeatedAttractionPursuit"),
        "hasRepeatedActionConflict": repeated_theme_reducer.get("hasRepeatedActionConflict"),
        "hasRepeatedIdentityRhythm": repeated_theme_reducer.get("hasRepeatedIdentityRhythm"),
        "hasRepeatedOuterIntensity": repeated_theme_reducer.get("hasRepeatedOuterIntensity"),
        "hasMercurySunHard": "Mercury-Sun" in hard_pairs,
        "hasMercuryJupiterSupport": "Mercury-Jupiter" in detected_supportive_pairs,
        "hasMercuryJupiterHard": "Mercury-Jupiter" in detected_hard_pairs,
        "hasMoonSaturnPressure": "Moon-Saturn" in saturn_pressure_pairs,
        "hasVenusSaturnPressure": "Venus-Saturn" in saturn_pressure_pairs,
        "hasMarsSaturnPressure": "Mars-Saturn" in saturn_pressure_pairs,
        "hasSaturnFunctionPressure": bool(saturn_pressure_pairs),
        "hasOuterPlanetIntensity": has_outer_planet_intensity,
        "hasOuterPlanetHardIntensity": has_outer_planet_hard_intensity,
        "hasHardFunctionCombination": bool(hard_pairs),
        "summary": render_zh_summary(
            str(interpretation_atom.get("summary_template") or "{label}選出{item_count}個組合；主訊號是：{technical}。"),
            label=label,
            item_count=item_count,
            technical=technical,
        ),
        "interpretation": str(
            interpretation_atom.get("interpretation")
            or "先把 pair family、contact type、被觸發點位的元素/三模式語氣組合起來，再交給問題 reducer。"
        ),
        "doesNotProve": str(
            interpretation_atom.get("does_not_prove")
            or "相位功能組合用來分清吸引、壓力、溝通與修復入口，再回到具體互動做判斷。"
        ),
        "confidence": "medium" if selected else "low",
        "source": source,
    }
    method_claim_ids = unique(selected_method_claim_ids)
    if method_claim_ids:
        payload["methodClaimIds"] = method_claim_ids
    if saturn_boundary:
        payload["saturnProcessBoundary"] = saturn_boundary
        payload["sourceClaimIds"] = GREENE_SATURN_PROCESS_SOURCE_CLAIM_IDS
    return payload


def western_relationship_chart_layer_cluster(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "relationshipChartLayer"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "關係盤深度層")
    source = str(atom.get("source_article_id") or "western-relationship-chart-layer")
    technical = "Composite/Davison/relationship chart 此版本未計算；保留為後續深度層"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": 0,
        "strongestStrength": 0.0,
        "averageStrength": 0.0,
        "dominantContactType": "not_calculated",
        "strongestEvidenceId": None,
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=0,
        ),
        "interpretation": western_public_copy(interpretation_atom.get("interpretation") or "關係盤屬於後續深度層。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "未計算時不能補寫關係盤故事。"),
        "confidence": "low",
        "source": source,
    }


def western_composite_layer_status(
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cluster = western_relationship_chart_layer_cluster(structured_kb)
    return {
        "status": "not_calculated",
        "reason": "relationship chart / composite / Davison is reserved for a later implementation after natal potential, comparison, and synastry proof are stable.",
        "source": cluster.get("source") or "western-relationship-chart-layer",
        "atomId": cluster.get("atomId"),
        "claimIds": cluster.get("claimIds") or [],
        "methodClaimIds": [
            "suskin-method-order-relationship-chart-later",
            "davison-reserve-do-not-pretend-calculated",
        ],
        "canCreateAstrologyConclusion": False,
        "requiresCalculatedRelationshipChart": True,
    }


def western_consultation_safety_cluster(
    context: dict[str, str],
    input_quality: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "consultationSafety"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "關係諮詢安全")
    source = str(atom.get("source_article_id") or "western-consultation-ethics")
    risk_key = str(context.get("emotional_risk") or "not-collected")
    contact_status = str(context.get("contact_status") or "unknown")
    precision_limit = input_quality.get("overall") != "high"
    restrictions = []
    if risk_key in {"self-blaming", "desperate", "unsafe-or-overwhelmed"}:
        restrictions.append("soft_tone")
    if contact_status == "blocked":
        restrictions.append("no_boundary_bypass")
    if precision_limit:
        restrictions.append("precision_caution")
    if not restrictions:
        restrictions.append("select_relevant_evidence")
    strength = 0.82 if len(restrictions) > 1 else 0.62
    technical = "、".join(restrictions)
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": len(restrictions),
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": restrictions[0],
        "strongestEvidenceId": f"consultation-safety-{restrictions[0]}",
        "hasPrivacyBoundary": True,
        "limitsThirdPartyInnerState": True,
        "preservesClientAgency": True,
        "blocksAbsolutePrediction": True,
        "hasUnsafeContactBlock": contact_status == "blocked",
        "requiresSoftTone": "soft_tone" in restrictions,
        "blockedInterpretationClaims": [
            "third_party_inner_state_certainty",
            "private_psychological_diagnosis",
            "absent_person_confession",
        ],
        "blockedActionClaims": [
            "fear_based_instruction",
            "fated_waiting_or_chasing",
            "coercive_contact_advice",
            "absolute_prediction",
        ],
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=len(restrictions),
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "只選準確、相關、有用、急迫的資訊。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "諮詢安全不是占星結論。"),
        "confidence": "high",
        "source": source,
    }


def western_nonfatal_synastry_safety_cluster(
    context: dict[str, str],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "nonfatalSynastrySafety"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "合盤非命運判決")
    source = str(atom.get("source_article_id") or "western-modern-nonfatal-synastry")
    desired_outcome = str(context.get("desired_outcome") or "understand")
    contact_status = str(context.get("contact_status") or "unknown")
    risk_flags = ["no_guaranteed_outcome", "pressure_is_condition_not_verdict", "dialogue_required_for_repair"]
    if desired_outcome == "reconnect":
        risk_flags.append("reconnect_must_stay_conditional")
    if contact_status in {"blocked", "no-contact"}:
        risk_flags.append("no_contact_cannot_be_predicted_as_inner_state")
    strength = 0.9 if len(risk_flags) >= 4 else 0.78
    technical = "、".join(risk_flags)
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": len(risk_flags),
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": "conditional_outcome",
        "strongestEvidenceId": "nonfatal-synastry-conditional-outcome",
        "hasNoGuaranteedOutcome": True,
        "hardAspectsArePressureNotVerdict": True,
        "requiresConditionalConclusion": True,
        "requiresCommunicationAndGrowthContext": True,
        "blockedOutcomeClaims": [
            "guaranteed_reunion",
            "guaranteed_breakup",
            "chart_configuration_success_failure_verdict",
            "hard_aspect_total_verdict",
            "timing_as_guaranteed_contact_success",
        ],
        "visibleActionConstraint": "把復合、分開與聯絡時機都寫成條件式；先看壓力是否下降、溝通能不能被接住、現實回應是否穩定。",
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=len(risk_flags),
        ),
        "interpretation": str(
            interpretation_atom.get("interpretation")
            or "任何合盤配置都不能保證關係成敗；壓力相位要被寫成需要溝通、成長與穩定現實回應的條件。"
        ),
        "doesNotProve": str(
            interpretation_atom.get("does_not_prove")
            or "合盤壓力、吸引或時機訊號都不能單獨證明一定復合、一定分開或永久沒有機會。"
        ),
        "confidence": "high",
        "source": source,
    }


def western_relationship_stage_cluster(
    context: dict[str, str],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "relationshipStage"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "關係階段")
    source = str(atom.get("source_article_id") or "context-relationship-stage")
    stage_key = str(context.get("relationship_stage") or "unknown")
    stage_label = STAGE_LABELS.get(stage_key, stage_key)
    if stage_key in {"crisis", "ambiguous"}:
        stage_group = "in_relationship"
    elif stage_key in {"cold-war", "broke-up-recent", "broke-up-long"}:
        stage_group = "in_breakup"
    else:
        stage_group = "unknown"
    strength_by_stage = {
        "broke-up-recent": 0.78,
        "cold-war": 0.72,
        "broke-up-long": 0.86,
        "crisis": 0.82,
        "ambiguous": 0.68,
    }
    strength = strength_by_stage.get(stage_key, 0.45)
    technical = f"{stage_label}；stage_group={stage_group}"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": 1 if stage_key != "unknown" else 0,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": stage_key,
        "strongestEvidenceId": f"context-stage-{stage_key}" if stage_key != "unknown" else None,
        "stageKey": stage_key,
        "stageGroup": stage_group,
        "isBreakupStage": stage_group == "in_breakup",
        "isActiveStage": stage_group == "in_relationship",
        "isAmbiguousStage": stage_key == "ambiguous",
        "isRecentBreakup": stage_key == "broke-up-recent",
        "isLongSeparation": stage_key == "broke-up-long",
        "requiresDefinition": stage_key == "ambiguous",
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=1,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "關係階段決定答案框架。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "關係階段用來決定答案框架，還要搭配星盤證據和現實回應。"),
        "confidence": "medium" if stage_key != "unknown" else "low",
        "source": source,
    }


def western_contact_status_claim_ids(atom: dict[str, Any], status_key: str) -> list[str]:
    base_claim_ids = [
        str(claim_id)
        for claim_id in atom.get("claim_ids") or []
        if claim_id and str(claim_id) not in CONTACT_STATUS_STATE_CLAIM_ID_SET
    ]
    state_claim_ids = CONTACT_STATUS_STATE_CLAIM_IDS.get(status_key) or []
    return unique([*base_claim_ids, *state_claim_ids])


def western_contact_status_cluster(
    context: dict[str, str],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "contactStatus"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "聯絡狀態")
    source = str(atom.get("source_article_id") or "context-contact-status")
    status_key = str(context.get("contact_status") or "unknown")
    status_label = CONTACT_STATUS_LABELS.get(status_key, status_key)
    if status_key == "blocked":
        access = "blocked"
        strength = 0.92
    elif status_key == "no-contact":
        access = "none"
        strength = 0.82
    elif status_key == "occasional-contact":
        access = "limited"
        strength = 0.58
    elif status_key in {"still-in-contact", "living-or-working-together"}:
        access = "live"
        strength = 0.62
    else:
        access = "unknown"
        strength = 0.4
    technical = f"{status_label}；contact_access={access}"
    claim_ids = western_contact_status_claim_ids(atom, status_key)
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": claim_ids,
        "itemCount": 1 if status_key != "unknown" else 0,
        "strongestStrength": round(strength, 3),
        "averageStrength": round(strength, 3),
        "dominantContactType": status_key,
        "strongestEvidenceId": f"context-contact-{status_key}" if status_key != "unknown" else None,
        "statusKey": status_key,
        "contactAccess": access,
        "isBlocked": status_key == "blocked",
        "isNoContact": status_key == "no-contact",
        "hasLimitedContact": status_key == "occasional-contact",
        "hasLiveContact": access == "live",
        "hasContactFriction": status_key in {"still-in-contact", "living-or-working-together"},
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=1,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "聯絡狀態決定能否建議低壓互動。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "聯絡狀態不等於愛或不愛。"),
        "confidence": "medium" if status_key != "unknown" else "low",
        "source": source,
    }


def western_contact_situation_policy_cluster(
    context: dict[str, str],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "contactSituationPolicy"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "聯絡情境行動建議")
    source = str(atom.get("source_article_id") or "context-contact-status")
    status_key = str(context.get("contact_status") or "unknown")
    status_label = CONTACT_STATUS_LABELS.get(status_key, status_key)
    policy = CONTACT_SITUATION_POLICIES.get(status_key) or CONTACT_SITUATION_POLICIES["unknown"]
    action_scale = int(policy.get("actionScale") or 0)
    boundary_strength = float(policy.get("boundaryStrength") or 0.4)
    blocked_actions = [str(action) for action in policy.get("blockedActions") or []]
    technical = f"{status_label}；action_scale={action_scale}；action_mode={policy.get('actionMode')}"
    claim_ids = western_contact_status_claim_ids(atom, status_key)
    method_claim_ids = CONTACT_SITUATION_METHOD_CLAIM_IDS.get(status_key) or CONTACT_SITUATION_METHOD_CLAIM_IDS["unknown"]
    contact_action_boundary = {
        "version": "contact-action-boundary-v1",
        "statusKey": status_key,
        "contactAccess": str(policy.get("contactAccess") or "unknown"),
        "actionScale": action_scale,
        "actionMode": str(policy.get("actionMode") or "context_missing_conservative"),
        "canSuggestDirectContact": bool(policy.get("canSuggestDirectContact")),
        "requiresCalculationSupport": bool(policy.get("requiresCalculationSupport")),
        "requiresEasyExit": bool(policy.get("requiresEasyExit")),
        "requiresSharedSpaceBoundary": bool(policy.get("requiresSharedSpaceBoundary")),
        "timingCanOverrideBoundary": bool(policy.get("timingCanOverrideBoundary")),
        "isHardBoundary": action_scale == 0,
        "isLowStimulationOnly": action_scale <= 2,
        "blockedActions": blocked_actions,
        "allowedAction": str(policy.get("allowedAction") or ""),
        "contactInstruction": str(policy.get("contactInstruction") or ""),
        "canCreateAstrologyConclusion": False,
        "canOverrideRealWorldBoundary": False,
        "sourceClaimIds": claim_ids,
        "methodClaimIds": method_claim_ids,
    }
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": claim_ids,
        "sourceClaimIds": claim_ids,
        "methodClaimIds": method_claim_ids,
        "itemCount": 1 if status_key != "unknown" else 0,
        "strongestStrength": round(boundary_strength, 3),
        "averageStrength": round(boundary_strength, 3),
        "dominantContactType": str(policy.get("actionMode") or "context_missing_conservative"),
        "strongestEvidenceId": f"context-contact-policy-{status_key}" if status_key != "unknown" else None,
        "statusKey": status_key,
        "statusLabel": status_label,
        "contactAccess": str(policy.get("contactAccess") or "unknown"),
        "actionScale": action_scale,
        "actionMode": str(policy.get("actionMode") or "context_missing_conservative"),
        "canSuggestDirectContact": bool(policy.get("canSuggestDirectContact")),
        "requiresEasyExit": bool(policy.get("requiresEasyExit")),
        "requiresSharedSpaceBoundary": bool(policy.get("requiresSharedSpaceBoundary")),
        "requiresCalculationSupport": bool(policy.get("requiresCalculationSupport")),
        "timingCanOverrideBoundary": bool(policy.get("timingCanOverrideBoundary")),
        "allowedAction": str(policy.get("allowedAction") or ""),
        "blockedActions": blocked_actions,
        "contactInstruction": str(policy.get("contactInstruction") or ""),
        "isHardBoundary": action_scale == 0,
        "isLowStimulationOnly": action_scale <= 2,
        "contactActionBoundary": contact_action_boundary,
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=1,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "聯絡情境會調整接下來適合做到哪一步。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "聯絡情境尺度不能證明愛或不愛。"),
        "confidence": "medium" if status_key != "unknown" else "low",
        "source": source,
    }


def western_emotional_risk_cluster(
    context: dict[str, str],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "emotionalRisk"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "情緒風險")
    source = str(atom.get("source_article_id") or "context-emotional-risk")
    risk_key = str(context.get("emotional_risk") or "not-collected")
    risk_label = EMOTIONAL_RISK_LABELS.get(risk_key, risk_key)
    risk_level = {
        "calm": 0.22,
        "not-collected": 0.38,
        "anxious": 0.62,
        "self-blaming": 0.68,
        "desperate": 0.86,
        "unsafe-or-overwhelmed": 0.92,
    }.get(risk_key, 0.42)
    technical = f"{risk_label}；risk_level={risk_level:.2f}"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": 1 if risk_key != "not-collected" else 0,
        "strongestStrength": round(risk_level, 3),
        "averageStrength": round(risk_level, 3),
        "dominantContactType": risk_key,
        "strongestEvidenceId": f"context-risk-{risk_key}",
        "riskKey": risk_key,
        "riskLevel": round(risk_level, 3),
        "isHighRisk": risk_level >= 0.75,
        "isSelfBlaming": risk_key == "self-blaming",
        "needsSoftTone": risk_level >= 0.6,
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=1,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "情緒風險用來調整語氣與安全邊界。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "情緒風險不是星盤事實。"),
        "confidence": "medium" if risk_key != "not-collected" else "low",
        "source": source,
    }


def western_desired_outcome_cluster(
    context: dict[str, str],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = "desiredOutcome"
    atom = western_atom_for_category(structured_kb, category)
    interpretation_atom = atom.get("interpretation") or {}
    label = str(atom.get("label") or "用戶想要的結果")
    source = str(atom.get("source_article_id") or "context-desired-outcome")
    outcome_key = str(context.get("desired_outcome") or "understand")
    outcome_label = DESIRED_OUTCOME_LABELS.get(outcome_key, outcome_key)
    action_pressure = {
        "reconnect": 0.78,
        "decide": 0.62,
        "understand": 0.38,
        "release": 0.32,
        "stabilize": 0.28,
    }.get(outcome_key, 0.4)
    technical = f"{outcome_label}；action_pressure={action_pressure:.2f}"
    return {
        "category": category,
        "label": label,
        "atomId": atom.get("id"),
        "claimIds": atom.get("claim_ids") or [],
        "itemCount": 1 if outcome_key else 0,
        "strongestStrength": round(action_pressure, 3),
        "averageStrength": round(action_pressure, 3),
        "dominantContactType": outcome_key,
        "strongestEvidenceId": f"context-outcome-{outcome_key}" if outcome_key else None,
        "outcomeKey": outcome_key,
        "actionPressure": round(action_pressure, 3),
        "wantsReconnect": outcome_key == "reconnect",
        "wantsDecide": outcome_key == "decide",
        "wantsUnderstand": outcome_key == "understand",
        "wantsRelease": outcome_key == "release",
        "wantsStabilize": outcome_key == "stabilize",
        "summary": str(interpretation_atom.get("summary_template") or "{label}：{technical}。").format(
            label=label,
            technical=technical,
            item_count=1,
        ),
        "interpretation": str(interpretation_atom.get("interpretation") or "desired outcome 決定答案框架，但不能覆蓋證據。"),
        "doesNotProve": str(interpretation_atom.get("does_not_prove") or "想復合不代表會復合。"),
        "confidence": "medium" if outcome_key else "low",
        "source": source,
    }


def western_evidence_cluster_layer(
    fixture: dict[str, Any],
    context: dict[str, str],
    identity_layer: dict[str, Any],
    synastry_layer: dict[str, list[dict[str, Any]]],
    timing_items: list[dict[str, Any]],
    input_quality: dict[str, Any],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    clusters = {
        category: western_evidence_cluster(category, synastry_layer.get(category) or [], structured_kb)
        for category in ("attraction", "emotionalSafety", "pressure", "communication", "repair")
    }
    clusters["currentTransits"] = western_current_transits_cluster(timing_items, structured_kb)
    clusters["timingWindowBand"] = western_timing_window_band_cluster(fixture, structured_kb)
    clusters["timingMercuryCommunication"] = western_timing_selector_cluster(
        fixture,
        "timingMercuryCommunication",
        {"communication_window", "communication_pressure"},
        structured_kb,
    )
    clusters["timingVenusSoftening"] = western_timing_selector_cluster(
        fixture,
        "timingVenusSoftening",
        {"softening", "relationship_focus"},
        structured_kb,
    )
    clusters["timingMarsActivation"] = western_timing_selector_cluster(
        fixture,
        "timingMarsActivation",
        {"activation_pressure"},
        structured_kb,
    )
    clusters["timingSaturnPressure"] = western_timing_selector_cluster(
        fixture,
        "timingSaturnPressure",
        {"pressure"},
        structured_kb,
    )
    clusters["timingMoonWeather"] = western_timing_selector_cluster(
        fixture,
        "timingMoonWeather",
        {"emotional_weather"},
        structured_kb,
    )
    clusters["timingContactReducer"] = western_timing_contact_reducer_cluster(fixture, structured_kb)
    clusters["birthDataQuality"] = western_birth_data_quality_cluster(input_quality, structured_kb)
    clusters["identityNeeds"] = western_identity_needs_cluster(identity_layer, structured_kb)
    clusters["methodOrder"] = western_method_order_cluster(structured_kb)
    clusters["natalSymbolFoundation"] = western_natal_symbol_foundation_cluster(structured_kb)
    clusters["planetaryFunctions"] = western_planetary_functions_cluster(structured_kb)
    clusters["signClassificationFoundation"] = western_sign_classification_foundation_cluster(structured_kb)
    clusters["elementStyleFoundation"] = western_element_style_foundation_cluster(structured_kb)
    clusters["modalityResponseFoundation"] = western_modality_response_foundation_cluster(structured_kb)
    clusters["planetSignStyle"] = western_planet_sign_style_cluster(fixture, structured_kb)
    clusters["moonSignEmotionalSafety"] = western_function_sign_style_cluster(fixture, "Moon", structured_kb)
    clusters["mercurySignCommunicationRepair"] = western_function_sign_style_cluster(fixture, "Mercury", structured_kb)
    clusters["venusSignAffectionStyle"] = western_function_sign_style_cluster(fixture, "Venus", structured_kb)
    clusters["marsSignPursuitConflict"] = western_function_sign_style_cluster(fixture, "Mars", structured_kb)
    clusters["saturnSignDefenseDelay"] = western_function_sign_style_cluster(fixture, "Saturn", structured_kb)
    clusters["functionElementMatrix"] = western_function_element_matrix_cluster(fixture, structured_kb)
    clusters["functionModalityMatrix"] = western_function_modality_matrix_cluster(fixture, structured_kb)
    clusters["relationshipPotential"] = western_relationship_potential_cluster(fixture, structured_kb)
    clusters["sunMoonAscProfile"] = western_sun_moon_asc_profile_cluster(fixture, structured_kb)
    clusters["elementComparison"] = western_element_comparison_cluster(fixture, structured_kb)
    clusters["safetyValidationLanguage"] = western_safety_validation_language_cluster(fixture, structured_kb)
    clusters["luminaryComparison"] = western_luminary_comparison_cluster(fixture, structured_kb)
    clusters["ascendantImpression"] = western_ascendant_impression_cluster(fixture, structured_kb)
    clusters["houseRelationshipFactors"] = western_house_relationship_factors_cluster(fixture, structured_kb)
    clusters["angleHouseFramework"] = western_angle_house_framework_cluster(fixture, structured_kb)
    clusters["aspectPriority"] = western_aspect_priority_cluster(fixture, structured_kb)
    clusters["aspectContactModifier"] = western_aspect_contact_modifier_cluster(synastry_layer, structured_kb)
    clusters["aspectPairContactTemplate"] = western_aspect_pair_contact_template_cluster(synastry_layer, structured_kb)
    clusters["aspectPairPhraseTemplateMethod"] = western_aspect_pair_phrase_template_method_cluster(structured_kb)
    clusters["aspectFunctionCombination"] = western_aspect_function_combination_cluster(fixture, structured_kb)
    clusters["aspectInterpretationFoundation"] = western_aspect_interpretation_foundation_cluster(structured_kb)
    clusters["aspectSynthesisCrossCheck"] = western_aspect_synthesis_cross_check_cluster(structured_kb)
    clusters["relationshipChartLayer"] = western_relationship_chart_layer_cluster(structured_kb)
    clusters["consultationSafety"] = western_consultation_safety_cluster(context, input_quality, structured_kb)
    clusters["nonfatalSynastrySafety"] = western_nonfatal_synastry_safety_cluster(context, structured_kb)
    clusters["relationshipStage"] = western_relationship_stage_cluster(context, structured_kb)
    clusters["contactStatus"] = western_contact_status_cluster(context, structured_kb)
    clusters["contactSituationPolicy"] = western_contact_situation_policy_cluster(context, structured_kb)
    clusters["emotionalRisk"] = western_emotional_risk_cluster(context, structured_kb)
    clusters["desiredOutcome"] = western_desired_outcome_cluster(context, structured_kb)
    return clusters


def western_cluster_fact(cluster: dict[str, Any]) -> str:
    if not cluster:
        return ""
    return first_clause(str(cluster.get("summary") or cluster.get("interpretation") or ""), 96)


REPEATED_THEME_RESULT_CONTEXT_COPY = {
    "saturn_pressure": {
        "answerFocus": "這題要先看防衛、責任感和界線為什麼反覆把表達變慢，不能只問對方還愛不愛。",
        "actionFocus": "下一步先減壓：少追問、少逼確認，讓對方不用立刻承擔關係答案。",
        "timingFocus": "即使短期時機有柔和窗口，也只能輕一點靠近；壓力主題重複時，不適合用好日子推進關係。",
    },
    "emotional_safety": {
        "answerFocus": "這題要先看安全感能不能被接住，而不是只看吸引或單次回應。",
        "actionFocus": "下一步要把訊息說得具體、安穩、可退場，避免讓對方覺得情緒被一次倒滿。",
        "timingFocus": "適合開口的時間必須同時符合低壓和可安撫，不能只看短期氣氛變柔和。",
    },
    "communication_repair": {
        "answerFocus": "這題要先看你們的話會不會碰到自尊、說服感或被迫表態，而不是只增加解釋。",
        "actionFocus": "下一步只適合短、清楚、沒有追問的一句話；重點是讓對話能回來，不是一次講完。",
        "timingFocus": "時機再好，也要配合不逼答案的溝通；不適合長文、辯論或連續補充。",
    },
    "attraction_pursuit": {
        "answerFocus": "吸引或靠近感不是單點出現，但它只能說明有反應，還不能直接等同承諾。",
        "actionFocus": "下一步可以從比較自然的好感開始，但不能用火花去加速關係；仍要先看對方能不能自然接住。",
        "timingFocus": "有吸引主題時，時機判讀要防止把熱度誤用成推進理由；輕一點比速度重要。",
    },
    "action_conflict": {
        "answerFocus": "這題要先看靠近後為什麼容易變急、變重，甚至起衝突；重點是看這個循環能不能停下來。",
        "actionFocus": "下一步先放慢、不要再加壓，不用立刻表態、攤牌或測試對方反應。",
        "timingFocus": "短期時機若有火星刺激，必須更保守；重點是避開衝動開口。",
    },
    "identity_rhythm": {
        "answerFocus": "這題要先看被看見、被尊重和情緒節奏怎麼互相牽動，再回到可觀察回應判斷方向。",
        "actionFocus": "下一步先用尊重自我感的方式開口，不要把對方逼到要立刻證明或承認。",
        "timingFocus": "時機判讀要保留自尊與情緒節奏，不適合在對方壓力高時逼出定位。",
    },
    "outer_intensity": {
        "answerFocus": "強烈牽動可能很明顯，但要把強度、投射和穩定愛意分開，不寫成命定。",
        "actionFocus": "下一步先守界線，不用強烈情緒、猜測或控制感去換答案。",
        "timingFocus": "即使有短期窗口，也不能把強度當成成功保證；需要更保守的界線感。",
    },
}


def western_repeated_theme_result_context(evidence_clusters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    aspect_cluster = evidence_clusters.get("aspectFunctionCombination") or {}
    reducer = aspect_cluster.get("repeatedThemeReducer") or {}
    dominant = reducer.get("dominantRepeatedTheme") or {}
    theme_key = str(dominant.get("themeKey") or reducer.get("dominantRepeatedThemeKey") or "")
    if not theme_key:
        return {}
    copy = REPEATED_THEME_RESULT_CONTEXT_COPY.get(theme_key) or {}
    label = str(dominant.get("label") or reducer.get("dominantRepeatedThemeLabel") or theme_key)
    return {
        "version": "repeated-theme-result-context-v1",
        "themeKey": theme_key,
        "label": label,
        "count": int(dominant.get("count") or 0),
        "selectedCount": int(dominant.get("selectedCount") or 0),
        "pairKeys": [str(item) for item in dominant.get("pairKeys") or [] if item],
        "selectedEvidenceIds": [str(item) for item in dominant.get("selectedEvidenceIds") or [] if item],
        "answerFocus": str(copy.get("answerFocus") or dominant.get("interpretation") or ""),
        "actionFocus": str(copy.get("actionFocus") or dominant.get("reducerInstruction") or ""),
        "timingFocus": str(copy.get("timingFocus") or dominant.get("reducerInstruction") or ""),
        "source": str(reducer.get("source") or "burk-repeated-themes-outweigh-single-contacts"),
        "methodClaimIds": [str(item) for item in reducer.get("methodClaimIds") or [] if item],
        "doesNotProve": str(reducer.get("doesNotProve") or "重複主題只提高解讀優先序，不保證聯絡、承諾或復合。"),
    }


def append_repeated_theme_sentence(text: str, sentence: str) -> str:
    base = str(text or "").strip()
    extra = str(sentence or "").strip()
    if not extra or extra in base:
        return base
    if not base:
        return extra
    return f"{base} {extra}"


def western_apply_repeated_theme_to_answer(
    *,
    question_key: str,
    short_answer: str,
    therefore: str,
    repeated_theme_context: dict[str, Any],
) -> tuple[str, str]:
    if not repeated_theme_context:
        return short_answer, therefore
    answer_focus = str(repeated_theme_context.get("answerFocus") or "")
    action_focus = str(repeated_theme_context.get("actionFocus") or "")
    timing_focus = str(repeated_theme_context.get("timingFocus") or "")
    if question_key == "when-to-contact":
        return (
            append_repeated_theme_sentence(short_answer, timing_focus),
            append_repeated_theme_sentence(therefore, action_focus),
        )
    if question_key in {"any-chance", "still-love-me", "stay-or-let-go"}:
        return (
            append_repeated_theme_sentence(short_answer, answer_focus),
            append_repeated_theme_sentence(therefore, action_focus),
        )
    return (
        append_repeated_theme_sentence(short_answer, answer_focus),
        append_repeated_theme_sentence(therefore, action_focus),
    )


RELATIONSHIP_INSIGHT_VERSION = "relationship-insight-layer-v1"
RELATIONSHIP_INSIGHT_SOURCE = "western-relationship-insight-reducers"
RELATIONSHIP_INSIGHT_METHOD_CLAIM_IDS = [
    "suskin-method-order-natal-before-synastry",
    "burk-synastry-as-persistent-trigger",
    "burk-repeated-themes-outweigh-single-contacts",
    "skymates-pivotal-interaspects-over-aspect-dump",
    "skymates-modern-nonfatal-synastry",
]

ATTRACTION_DYNAMICS_PAIRS = {
    "Venus-Mars",
    "Sun-Moon",
    "Moon-Moon",
    "Moon-Venus",
    "Sun-Venus",
    "Sun-Mars",
    "Venus-Venus",
}

CONFLICT_DYNAMICS_PAIRS = {
    "Mercury-Mars",
    "Mars-Mars",
    "Moon-Mars",
    "Mercury-Saturn",
    "Moon-Saturn",
    "Venus-Saturn",
    "Mars-Saturn",
    "Sun-Saturn",
}

GROWTH_DYNAMICS_PAIRS = {
    "Mercury-Jupiter",
    "Sun-Saturn",
    "Moon-Saturn",
    "Venus-Saturn",
    "Mars-Saturn",
}

ARCHETYPE_TITLES = (
    "前世因緣感型",
    "命中貴人型",
    "溝通修復型",
    "彼此牽動型",
    "靈魂伴侶型",
    "磨合成長型",
    "歡喜冤家型",
    "高吸引高摩擦型",
    "自然吸引型",
    "慢熱安全感型",
)

ARCHETYPE_SUBTITLES = {
    "前世因緣感型": "牽引感很強，但需要把命定感和現實互動分開。",
    "命中貴人型": "彼此容易打開視野，但支持感仍需要落到實際行動。",
    "溝通修復型": "關係不是沒話可說，而是要換一種比較接得住的說法。",
    "彼此牽動型": "彼此很容易受對方影響，重點是把靠近的節奏穩住。",
    "靈魂伴侶型": "熟悉感和情緒牽動較明顯，但仍不能跳過現實回應。",
    "磨合成長型": "關係有重量，需要用成熟、耐心和界線慢慢磨合。",
    "歡喜冤家型": "容易互相點燃，也容易一靠近就變急。",
    "高吸引高摩擦型": "有吸引，也容易在一靠近時變得緊繃。",
    "自然吸引型": "彼此有明顯好感或靠近入口，但穩定度要另外判斷。",
    "慢熱安全感型": "這段關係要先看安全感和可預期回應，不能只看一時牽動。",
}

ARCHETYPE_THEME_TO_TITLE = {
    "outer_intensity": "前世因緣感型",
    "communication_repair": "溝通修復型",
    "identity_rhythm": "彼此牽動型",
    "emotional_safety": "靈魂伴侶型",
    "saturn_pressure": "磨合成長型",
    "action_conflict": "歡喜冤家型",
    "attraction_pursuit": "自然吸引型",
}

ARCHETYPE_REPEATED_THEME_FLAGS = {
    "hasRepeatedOuterIntensity": "outer_intensity",
    "hasRepeatedCommunicationRepair": "communication_repair",
    "hasRepeatedIdentityRhythm": "identity_rhythm",
    "hasRepeatedEmotionalSafety": "emotional_safety",
    "hasRepeatedSaturnPressure": "saturn_pressure",
    "hasRepeatedActionConflict": "action_conflict",
    "hasRepeatedAttractionPursuit": "attraction_pursuit",
}

ARCHETYPE_ACTION_CONFLICT_PAIRS = {"Mercury-Mars", "Mars-Mars", "Moon-Mars", "Sun-Mars"}
ARCHETYPE_SATURN_PRESSURE_PAIRS = {"Mercury-Saturn", "Moon-Saturn", "Venus-Saturn", "Mars-Saturn", "Sun-Saturn"}
ARCHETYPE_IDENTITY_PAIRS = {"Sun-Moon", "Moon-Moon", "Sun-Sun"}
ARCHETYPE_EMOTIONAL_SAFETY_PAIRS = {"Sun-Moon", "Moon-Moon", "Moon-Venus", "Mercury-Moon"}
ARCHETYPE_COMMUNICATION_PAIRS = {
    "Mercury-Mercury",
    "Mercury-Moon",
    "Mercury-Venus",
    "Mercury-Sun",
    "Mercury-Mars",
    "Mercury-Saturn",
    "Mercury-Jupiter",
}
ARCHETYPE_JUPITER_SUPPORT_PAIRS = {"Mercury-Jupiter", "Sun-Jupiter", "Moon-Jupiter", "Venus-Jupiter", "Mars-Jupiter"}

RELATIONSHIP_THESIS_METHOD_CLAIM_IDS = [
    "george-bloch-synthesis-salient-themes-first",
    "burk-repeated-themes-outweigh-single-contacts",
    "skymates-individuals-before-interactions",
    "skymates-no-generic-love-needs",
]

RELATIONSHIP_THESIS_HARD_REQUIREMENTS = [
    "minimumEvidenceDomains:2",
    "requiresContextEvidence:true",
    "requiresInteractionMechanism:true",
    "requiresPartnerEvidenceForPartnerClaim:true",
    "minimumObservableSigns:2",
    "requiresChangeCondition:true",
    "prohibitsUnqualifiedMindReading:true",
    "prohibitsExactOutcomePredictionWithoutTimingSupport:true",
]

THESIS_DOMAIN_BY_CLUSTER = {
    "identityNeeds": "userNatal",
    "relationshipProfiles": "userNatal",
    "partnerNeeds": "partnerNatal",
    "attraction": "synastry",
    "emotionalSafety": "synastry",
    "pressure": "synastry",
    "communication": "synastry",
    "repair": "synastry",
    "aspectFunctionCombination": "synastry",
    "relationshipArchetype": "synastry",
    "attractionDynamics": "synastry",
    "conflictDynamics": "synastry",
    "growthDynamics": "synastry",
    "timingWindowBand": "timing",
    "timingContactReducer": "timing",
    "relationshipTurningWindows": "timing",
    "relationshipStage": "relationshipContext",
    "contactStatus": "relationshipContext",
    "contactSituationPolicy": "relationshipContext",
    "emotionalRisk": "relationshipContext",
    "desiredOutcome": "relationshipContext",
    "consultationSafety": "method",
    "nonfatalSynastrySafety": "method",
}

THESIS_DYNAMIC_TEMPLATES = {
    "saturn_pressure": {
        "dynamic": "靠近需求與界線壓力互相放大",
        "questionReframe": "重點不是他是否完全沒有感覺，而是靠近時的壓力能不能被拆小，讓回應不再只剩防衛。",
        "centralThesis": "這段關係目前卡住的不是單純沒有牽引，而是越靠近越容易碰到責任、界線或承擔壓力；壓力一升高，回應就會變慢、變短或變保守。",
        "poleA": "想把關係說清楚、確認是否還有位置",
        "poleB": "一感到要承擔或表態，就先收緊界線",
        "currentPattern": "靠近後很快變沉重，互動從想理解變成怕被要求",
        "desiredShift": "把關係問題拆成小而可回答的互動，先不索取完整結論",
        "userTrigger": "關係訊號變慢、變冷或沒有明確答案",
        "userResponse": "更想確認承諾、責任或下一步",
        "partnerTrigger": "感到需要立刻承接關係壓力",
        "partnerResponse": "先延後、縮短或降低回應密度",
        "reinforcingEffect": "你更不安，他更有壓力，互動就更容易斷續",
        "secondaryModifier": "如果同時有吸引線索，吸引只能說明還有牽動，不能抵消界線壓力。",
    },
    "emotional_safety": {
        "dynamic": "確認需求與安全感退縮互相放大",
        "questionReframe": "重點不是單次回覆代表什麼，而是這段互動能不能從不安確認變成穩定被接住。",
        "centralThesis": "這段關係的核心不是只有喜不喜歡，而是安全感一被觸發，雙方就容易把小反應放大成整段關係的答案。",
        "poleA": "想透過回應確認自己還被重視",
        "poleB": "情緒壓力升高時先收起感受或降低刺激",
        "currentPattern": "越想確認越敏感，對方越容易只給有限回應",
        "desiredShift": "讓互動回到具體、安穩、能延續的小回應",
        "userTrigger": "對方回覆不穩、語氣變淡或沒有主動延續",
        "userResponse": "更注意細節，想從回應裡找安全感",
        "partnerTrigger": "感到情緒需要被立刻安撫或解釋",
        "partnerResponse": "先變慢、變短，或只回到安全距離",
        "reinforcingEffect": "他的保守回應會讓你更不安，你的確認也會讓互動更緊",
        "secondaryModifier": "這個判讀需要現實互動驗證；穩定接話比一句情緒表態更重要。",
    },
    "communication_repair": {
        "dynamic": "想說清楚與被推著回答互相放大",
        "questionReframe": "重點不是話要不要說更多，而是現在的說法能不能讓對話重新可承接。",
        "centralThesis": "這段關係容易卡在溝通形式：你越想一次說清楚，對方越可能只感覺被要求回答，於是對話從修復變成壓力。",
        "poleA": "想把誤會、責任或心意一次講完整",
        "poleB": "被大量訊息或追問時先降低回應",
        "currentPattern": "越解釋越緊，越想修復越像在要求答案",
        "desiredShift": "把長篇解釋縮成一句具體、對方可以晚點回的話",
        "userTrigger": "覺得不說清楚就會失去機會",
        "userResponse": "補充更多細節、道歉或追問",
        "partnerTrigger": "覺得同一句話裡有太多問題需要承接",
        "partnerResponse": "延後回覆、只回一小段或避開核心問題",
        "reinforcingEffect": "你越想補完整，他越接不住，誤會反而更難打開",
        "secondaryModifier": "修復入口仍在，但要靠短、清楚、沒有追問的訊號重開。",
    },
    "attraction_pursuit": {
        "dynamic": "吸引出現但還需要持續行動",
        "questionReframe": "重點不是有沒有火花，而是火花後面有沒有可延續的行動。",
        "centralThesis": "這段關係看得到靠近感或吸引，但現在真正要判斷的是吸引能不能落到穩定回應，而不是只在短暫互動裡反覆出現。",
        "poleA": "被好感、曖昧或熟悉感重新牽動",
        "poleB": "吸引之後沒有穩定承接，容易又回到不確定",
        "currentPattern": "短暫靠近後，延續性不足",
        "desiredShift": "從一時熱絡變成對方也會自然把話題和行動往前帶",
        "userTrigger": "對方有一點反應或氣氛變近",
        "userResponse": "容易把火花放大成關係正在進展",
        "partnerTrigger": "互動被快速推向關係定位或復合期待",
        "partnerResponse": "先停在輕互動，不一定接到承諾或行動",
        "reinforcingEffect": "火花越被放大，越容易讓後續落差變成新的不安",
        "secondaryModifier": "吸引是入口，不是結論；穩定度要看後續行動。",
    },
    "action_conflict": {
        "dynamic": "推進速度與防衛反應互相升溫",
        "questionReframe": "重點不是誰比較有理，而是互動速度一升高時，雙方能不能避免進入對抗。",
        "centralThesis": "這段關係容易一靠近就升溫：一方想快點處理，另一方感到被推著走，於是原本的在意變成硬碰硬。",
        "poleA": "想快點行動、談清楚或測反應",
        "poleB": "感到被逼近時用更硬的方式保護自己",
        "currentPattern": "想修復的動作變成刺激，對話容易變對抗",
        "desiredShift": "下一步要小到對方不用立刻表態",
        "userTrigger": "不確定感累積，想快點知道答案",
        "userResponse": "攤牌、測試或直接推進",
        "partnerTrigger": "感覺節奏被拉得太快",
        "partnerResponse": "反應變硬、變急或直接退開",
        "reinforcingEffect": "越快處理，越像對抗；越對抗，你越想再確認",
        "secondaryModifier": "先降速不是放棄，而是避免讓可談的事變成衝突。",
    },
    "identity_rhythm": {
        "dynamic": "想被確認與自尊保護互相牽動",
        "questionReframe": "重點不是逼出承認，而是這段互動能不能保留彼此被尊重的位置。",
        "centralThesis": "這段關係卡住時，很容易碰到自尊與被看見的議題；越要求對方承認或表態，對方越可能先保護面子與距離。",
        "poleA": "想被明確看見、承認或選擇",
        "poleB": "被逼承認時先保護自尊和退路",
        "currentPattern": "想確認位置，卻讓對方覺得沒有台階",
        "desiredShift": "保留彼此台階，再看是否能自然靠近",
        "userTrigger": "覺得自己沒有被放在重要位置",
        "userResponse": "要求對方說清楚或證明在乎",
        "partnerTrigger": "感覺自己被審判、比較或逼著低頭",
        "partnerResponse": "先守住面子，減少承認或靠近",
        "reinforcingEffect": "越想要承認，越得不到自然回應",
        "secondaryModifier": "尊重感和台階比說服更能打開後續互動。",
    },
    "outer_intensity": {
        "dynamic": "強烈牽引與現實線索不足互相混淆",
        "questionReframe": "重點不是感覺有多強，而是強烈牽引能不能被現實行動驗證。",
        "centralThesis": "這段關係的牽引感可能很強，但強度容易讓人用想像補足空白；現在要回到可觀察行動，分清楚牽動、投射與持續行動。",
        "poleA": "被強烈感受、回憶或氣氛牽動",
        "poleB": "現實回應不足以承接這份強度",
        "currentPattern": "感覺很重，但行動證據不夠連續",
        "desiredShift": "對方有沒有穩定行動，不要只靠猜測下結論",
        "userTrigger": "某個回應、回憶或巧合讓感覺被放大",
        "userResponse": "想把強烈感受解讀成命運或答案",
        "partnerTrigger": "感受到情緒強度或控制感變高",
        "partnerResponse": "先保持距離或只給模糊反應",
        "reinforcingEffect": "距離越模糊，想像越容易補空白，現實判斷越不穩",
        "secondaryModifier": "越強烈，越需要回到可觀察訊號。",
    },
}

THESIS_FALLBACK_TEMPLATE = {
    "dynamic": "吸引、壓力與現實狀態需要一起判斷",
    "questionReframe": "重點不是用單一反應下結論，而是看星盤證據、現實狀態和短期互動是否指向同一個方向。",
    "centralThesis": "這段關係需要保守判斷：星盤提供部分牽動與卡點，但真正能改變結論的是後續互動是否更穩、更自然。",
    "poleA": "想從現有線索得到清楚答案",
    "poleB": "證據仍不足以支持確定結論",
    "currentPattern": "容易把單次反應放大成整段關係答案",
    "desiredShift": "用多次、穩定、自然的互動累積判斷",
    "userTrigger": "關係訊號不明確",
    "userResponse": "想從一次回覆判斷全部",
    "partnerTrigger": "被快速推向表態",
    "partnerResponse": "只給有限或保守回應",
    "reinforcingEffect": "有限回應會讓不確定感繼續放大",
    "secondaryModifier": "資料保守時，行動也要保守。",
}


def thesis_confidence_value(value: Any) -> float:
    normalized = normalized_case_confidence(value, "medium")
    return {"high": 0.86, "medium": 0.66, "low": 0.42}.get(normalized, 0.66)


def thesis_public_text(value: Any) -> str:
    return western_public_copy(str(value or "")).strip()


def thesis_cluster_claim_ids(*clusters: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        ids.extend(str(item) for item in cluster.get("claimIds") or [] if item)
        ids.extend(str(item) for item in cluster.get("sourceClaimIds") or [] if item)
    return unique(ids)


def thesis_cluster_method_claim_ids(*clusters: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        ids.extend(str(item) for item in cluster.get("methodClaimIds") or [] if item)
    return unique(ids)


def thesis_evidence_ref(
    *,
    evidence_id: str,
    domain: str,
    proposition: str,
    role: str,
    relevance: float,
    confidence: float,
    source: str,
    evidence_cluster_keys: list[str],
    source_claim_ids: list[str] | None = None,
    method_claim_ids: list[str] | None = None,
    allowed_inference: list[str] | None = None,
    prohibited_inference: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": evidence_id,
        "domain": domain,
        "proposition": thesis_public_text(proposition),
        "role": role,
        "relevance": round(max(min(relevance, 1.0), 0.0), 3),
        "confidence": round(max(min(confidence, 1.0), 0.0), 3),
        "source": source,
        "evidenceClusterKeys": unique([str(item) for item in evidence_cluster_keys if item]),
        "sourceClaimIds": unique([str(item) for item in source_claim_ids or [] if item]),
        "methodClaimIds": unique([str(item) for item in method_claim_ids or [] if item]),
        "allowedInference": [thesis_public_text(item) for item in allowed_inference or [] if thesis_public_text(item)],
        "prohibitedInference": [thesis_public_text(item) for item in prohibited_inference or [] if thesis_public_text(item)],
    }


def first_need_point(identity_layer: dict[str, Any], person_key: str, preferred: list[str]) -> dict[str, Any]:
    needs = ((identity_layer.get(person_key) or {}).get("needs") or [])
    for point in preferred:
        for item in needs:
            if str(item.get("point") or "") == point:
                return item
    return needs[0] if needs else {}


def strongest_synastry_item(synastry_layer: dict[str, list[dict[str, Any]]], categories: list[str]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for category in categories:
        items.extend(item for item in synastry_layer.get(category) or [] if isinstance(item, dict))
    if not items:
        return {}
    return sorted(items, key=lambda item: float(item.get("strength") or 0), reverse=True)[0]


def relationship_thesis_evidence_packet(
    *,
    context: dict[str, str],
    identity_layer: dict[str, Any],
    synastry_layer: dict[str, list[dict[str, Any]]],
    evidence_clusters: dict[str, dict[str, Any]],
    relationship_insights: dict[str, Any],
    answer_layer: dict[str, Any],
    timing_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    packet: list[dict[str, Any]] = []
    user_need = first_need_point(identity_layer, "personA", ["Moon", "Mercury", "Venus"])
    partner_need = first_need_point(identity_layer, "personB", ["Saturn", "Mars", "Moon", "Mercury"])
    identity_cluster = evidence_clusters.get("identityNeeds") or {}
    partner_block = relationship_insights.get("partnerNeeds") or {}
    partner_cluster = evidence_clusters.get("partnerNeeds") or {}
    synastry_item = strongest_synastry_item(synastry_layer, ["attraction", "emotionalSafety", "pressure", "communication", "repair"])
    aspect_cluster = evidence_clusters.get("aspectFunctionCombination") or {}
    theme_context = answer_layer.get("repeatedThemeContext") or {}
    contact_cluster = evidence_clusters.get("contactSituationPolicy") or {}
    stage_cluster = evidence_clusters.get("relationshipStage") or {}
    timing_cluster = evidence_clusters.get("timingContactReducer") or {}
    timing_window = evidence_clusters.get("timingWindowBand") or {}
    method_cluster = evidence_clusters.get("nonfatalSynastrySafety") or evidence_clusters.get("consultationSafety") or {}

    if user_need:
        point = str(user_need.get("point") or "Moon")
        packet.append(
            thesis_evidence_ref(
                evidence_id="E-user-need",
                domain="userNatal",
                proposition=user_need.get("meaning")
                or f"使用者的 {point} 線索顯示，關係不明確時需要可理解、可安放的互動。",
                role="supports",
                relevance=0.82,
                confidence=thesis_confidence_value(user_need.get("confidence")),
                source=str(identity_cluster.get("source") or "western-natal-relationship-needs"),
                evidence_cluster_keys=["identityNeeds", f"{point.lower()}Sign"],
                source_claim_ids=thesis_cluster_claim_ids(identity_cluster),
                method_claim_ids=thesis_cluster_method_claim_ids(identity_cluster),
                allowed_inference=["可說明使用者比較容易被哪種互動安定或觸發"],
                prohibited_inference=["不能把使用者的反應寫成錯誤或責任全歸使用者"],
            )
        )
    if partner_need or partner_block:
        partner_profile = partner_block.get("profile") if isinstance(partner_block.get("profile"), dict) else {}
        proposition = (
            partner_profile.get("conflictDefense")
            or partner_profile.get("relationshipStyleWanted")
            or partner_need.get("meaning")
            or "對方在壓力升高時需要較清楚、可退回、不要立刻被定義的互動。"
        )
        packet.append(
            thesis_evidence_ref(
                evidence_id="E-partner-need",
                domain="partnerNatal",
                proposition=proposition,
                role="supports",
                relevance=0.8,
                confidence=thesis_confidence_value(partner_need.get("confidence") or "medium"),
                source=str(partner_cluster.get("source") or "western-natal-relationship-needs"),
                evidence_cluster_keys=["partnerNeeds", "identityNeeds"],
                source_claim_ids=thesis_cluster_claim_ids(partner_cluster, identity_cluster),
                method_claim_ids=thesis_cluster_method_claim_ids(partner_cluster, identity_cluster),
                allowed_inference=["可描述對方比較接得住或接不住的互動條件"],
                prohibited_inference=["不能宣稱知道對方內心一定還愛或一定不愛"],
            )
        )
    if synastry_item or theme_context:
        proposition = (
            theme_context.get("answerFocus")
            or synastry_item.get("emotionalMeaning")
            or synastry_item.get("technical")
            or "合盤線索顯示吸引、壓力或修復主題需要一起判斷。"
        )
        packet.append(
            thesis_evidence_ref(
                evidence_id="E-synastry-theme",
                domain="synastry",
                proposition=proposition,
                role="supports",
                relevance=0.9,
                confidence=thesis_confidence_value(synastry_item.get("confidence") or "medium"),
                source=str(theme_context.get("source") or synastry_item.get("source") or aspect_cluster.get("source") or "western-synastry"),
                evidence_cluster_keys=["aspectFunctionCombination", "relationshipArchetype"],
                source_claim_ids=thesis_cluster_claim_ids(aspect_cluster),
                method_claim_ids=unique([*thesis_cluster_method_claim_ids(aspect_cluster), *list(theme_context.get("methodClaimIds") or [])]),
                allowed_inference=["可判斷關係中反覆出現的互動主題"],
                prohibited_inference=["不能把合盤主題寫成復合或分開的保證"],
            )
        )
    if timing_items or timing_cluster or timing_window:
        timing_item = timing_items[0] if timing_items else {}
        packet.append(
            thesis_evidence_ref(
                evidence_id="E-timing-activation",
                domain="timing",
                proposition=timing_cluster.get("emotionalMeaning")
                or timing_window.get("emotionalMeaning")
                or timing_item.get("emotionalMeaning")
                or "短期時機只能說明互動承受度與關係氣候，不能指定保證日期。",
                role="activates",
                relevance=0.72,
                confidence=thesis_confidence_value(timing_cluster.get("confidence") or timing_window.get("confidence") or timing_item.get("confidence") or "medium"),
                source=str(timing_cluster.get("source") or timing_window.get("source") or timing_item.get("source") or "western-current-transits-v1"),
                evidence_cluster_keys=["timingContactReducer", "timingWindowBand"],
                source_claim_ids=thesis_cluster_claim_ids(timing_cluster, timing_window),
                method_claim_ids=thesis_cluster_method_claim_ids(timing_cluster, timing_window),
                allowed_inference=["可調整此刻應該觀察、等待或縮小行動"],
                prohibited_inference=["不能承諾精準聯絡日或必然結果"],
            )
        )
    stage_label = STAGE_LABELS.get(context.get("relationship_stage", ""), context.get("relationship_stage", "") or "未提供")
    contact_label = CONTACT_STATUS_LABELS.get(context.get("contact_status", ""), context.get("contact_status", "") or "未提供")
    packet.append(
        thesis_evidence_ref(
            evidence_id="E-context-state",
            domain="relationshipContext",
            proposition=f"目前關係階段是「{stage_label}」，聯絡狀態是「{contact_label}」；現實狀態只能啟動與限制行動，不能單獨創造星盤結論。",
            role="activates",
            relevance=0.96,
            confidence=0.86,
            source=str(contact_cluster.get("source") or stage_cluster.get("source") or "relationship-context"),
            evidence_cluster_keys=["relationshipStage", "contactStatus", "contactSituationPolicy"],
            source_claim_ids=thesis_cluster_claim_ids(contact_cluster, stage_cluster),
            method_claim_ids=thesis_cluster_method_claim_ids(contact_cluster, stage_cluster),
            allowed_inference=["可判斷這個動態為什麼現在被啟動"],
            prohibited_inference=["不能用現實狀態替代合盤或本命證據"],
        )
    )
    if method_cluster:
        packet.append(
            thesis_evidence_ref(
                evidence_id="E-method-boundary",
                domain="method",
                proposition=method_cluster.get("emotionalMeaning")
                or method_cluster.get("technical")
                or "占星與諮詢邊界要求把結論寫成條件式，不做讀心或絕對預測。",
                role="limits",
                relevance=0.76,
                confidence=0.82,
                source=str(method_cluster.get("source") or "western-method-boundary"),
                evidence_cluster_keys=["nonfatalSynastrySafety", "consultationSafety"],
                source_claim_ids=thesis_cluster_claim_ids(method_cluster),
                method_claim_ids=thesis_cluster_method_claim_ids(method_cluster),
                allowed_inference=["可限制語氣與結論強度"],
                prohibited_inference=["不能下絕對預言、讀心或保證復合"],
            )
        )
    return packet


def thesis_question_relevance(dynamic_key: str, question_key: str) -> float:
    relevance = {
        "still-love-me": {
            "emotional_safety": 0.96,
            "saturn_pressure": 0.9,
            "attraction_pursuit": 0.86,
            "outer_intensity": 0.78,
        },
        "any-chance": {
            "attraction_pursuit": 0.94,
            "communication_repair": 0.9,
            "saturn_pressure": 0.84,
            "action_conflict": 0.82,
        },
        "when-to-contact": {
            "communication_repair": 0.96,
            "saturn_pressure": 0.9,
            "action_conflict": 0.88,
            "emotional_safety": 0.82,
        },
        "what-did-i-do-wrong": {
            "communication_repair": 0.96,
            "action_conflict": 0.92,
            "emotional_safety": 0.84,
            "identity_rhythm": 0.82,
        },
        "stay-or-let-go": {
            "saturn_pressure": 0.94,
            "outer_intensity": 0.88,
            "emotional_safety": 0.84,
            "attraction_pursuit": 0.78,
        },
    }
    return float((relevance.get(question_key) or {}).get(dynamic_key, 0.72))


def thesis_current_activation_score(context: dict[str, str]) -> float:
    stage = context.get("relationship_stage", "")
    contact_status = context.get("contact_status", "")
    risk = context.get("emotional_risk", "")
    score = 0.68
    if stage in {"broke-up-recent", "cold-war", "crisis"}:
        score += 0.12
    if contact_status in {"limited-reply", "no-contact", "blocked", "intermittent-contact", "still-in-contact"}:
        score += 0.12
    if risk in {"anxious", "self-blaming", "desperate", "unsafe-or-overwhelmed"}:
        score += 0.08
    return min(score, 0.98)


def evidence_ids_by_domain(packet: list[dict[str, Any]], *domains: str) -> list[str]:
    return [str(item.get("id") or "") for item in packet if item.get("domain") in domains and item.get("id")]


def evidence_strength(packet: list[dict[str, Any]], evidence_ids: list[str]) -> float:
    relevant = [item for item in packet if item.get("id") in set(evidence_ids)]
    if not relevant:
        return 0.0
    scores = [float(item.get("relevance") or 0.0) * float(item.get("confidence") or 0.0) for item in relevant]
    return sum(scores) / len(scores)


def relationship_thesis_candidate_dynamics(
    *,
    context: dict[str, str],
    evidence_packet: list[dict[str, Any]],
    repeated_theme_context: dict[str, Any],
    evidence_clusters: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    question_key = context.get("main_question", "")
    theme_key = str(repeated_theme_context.get("themeKey") or "")
    candidate_keys = [theme_key] if theme_key else []
    evidence_backed_keys = {theme_key} if theme_key else set()
    aspect_cluster = evidence_clusters.get("aspectFunctionCombination") or {}
    if aspect_cluster.get("hasRepeatedEmotionalSafety"):
        candidate_keys.append("emotional_safety")
        evidence_backed_keys.add("emotional_safety")
    if aspect_cluster.get("hasRepeatedSaturnPressure"):
        candidate_keys.append("saturn_pressure")
        evidence_backed_keys.add("saturn_pressure")
    if aspect_cluster.get("hasRepeatedCommunicationRepair"):
        candidate_keys.append("communication_repair")
        evidence_backed_keys.add("communication_repair")
    if aspect_cluster.get("hasRepeatedAttractionPursuit"):
        candidate_keys.append("attraction_pursuit")
        evidence_backed_keys.add("attraction_pursuit")
    if aspect_cluster.get("hasRepeatedActionConflict"):
        candidate_keys.append("action_conflict")
        evidence_backed_keys.add("action_conflict")
    if aspect_cluster.get("hasRepeatedIdentityRhythm"):
        candidate_keys.append("identity_rhythm")
        evidence_backed_keys.add("identity_rhythm")
    if aspect_cluster.get("hasRepeatedOuterIntensity"):
        candidate_keys.append("outer_intensity")
        evidence_backed_keys.add("outer_intensity")
    if question_key == "when-to-contact":
        candidate_keys.extend(["communication_repair", "saturn_pressure"])
    elif question_key == "what-did-i-do-wrong":
        candidate_keys.extend(["communication_repair", "action_conflict"])
    elif question_key == "still-love-me":
        candidate_keys.extend(["emotional_safety", "attraction_pursuit"])
    elif question_key == "stay-or-let-go":
        candidate_keys.extend(["saturn_pressure", "outer_intensity"])
    else:
        candidate_keys.extend(["attraction_pursuit", "emotional_safety"])
    candidate_keys = unique([key for key in candidate_keys if key in THESIS_DYNAMIC_TEMPLATES])
    if not candidate_keys:
        candidate_keys = ["fallback"]

    base_evidence_ids = evidence_ids_by_domain(evidence_packet, "userNatal", "partnerNatal", "synastry", "relationshipContext")
    candidates: list[dict[str, Any]] = []
    for index, key in enumerate(candidate_keys[:4]):
        template = THESIS_DYNAMIC_TEMPLATES.get(key) or THESIS_FALLBACK_TEMPLATE
        evidence_ids = unique([*base_evidence_ids, *evidence_ids_by_domain(evidence_packet, "timing", "method")])
        factors = {
            "questionRelevance": thesis_question_relevance(key, question_key) if key != "fallback" else 0.62,
            "currentActivation": thesis_current_activation_score(context),
            "evidenceStrength": evidence_strength(evidence_packet, evidence_ids),
            "crossLayerSupport": min(len({item.get("domain") for item in evidence_packet if item.get("id") in set(evidence_ids)}) / 5, 1.0),
            "caseDistinctiveness": 1.0
            if key == theme_key and key
            else 0.68
            if key in evidence_backed_keys
            else 0.42
            if key != "fallback"
            else 0.48,
            "overreachPenalty": 0.08 if key == "outer_intensity" and context.get("emotional_risk") in {"desperate", "unsafe-or-overwhelmed"} else 0.02,
        }
        score = (
            factors["questionRelevance"] * 0.2
            + factors["currentActivation"] * 0.2
            + factors["evidenceStrength"] * 0.2
            + factors["crossLayerSupport"] * 0.16
            + factors["caseDistinctiveness"] * 0.24
            - factors["overreachPenalty"]
        )
        candidates.append(
            {
                "id": f"C{index + 1}",
                "dynamicKey": key,
                "dynamic": template["dynamic"],
                "evidenceIds": evidence_ids,
                "score": round(score, 3),
                "rankingFactors": {factor_key: round(float(value), 3) for factor_key, value in factors.items()},
            }
        )
    return sorted(candidates, key=lambda item: float(item.get("score") or 0), reverse=True)


def relationship_thesis_current_activation(context: dict[str, str], template: dict[str, str]) -> str:
    stage = STAGE_LABELS.get(context.get("relationship_stage", ""), context.get("relationship_stage", "") or "目前狀態")
    contact = CONTACT_STATUS_LABELS.get(context.get("contact_status", ""), context.get("contact_status", "") or "聯絡狀態未提供")
    risk = EMOTIONAL_RISK_LABELS.get(context.get("emotional_risk", ""), context.get("emotional_risk", "") or "情緒狀態未提供")
    return f"現在是「{stage}」且聯絡狀態為「{contact}」，{risk}會讓「{template['currentPattern']}」更容易被放大；因此判讀要看互動是否真的往「{template['desiredShift']}」移動。"


def relationship_thesis_contextual_pattern(context: dict[str, str], template: dict[str, str]) -> str:
    status = context.get("contact_status", "")
    base = template["currentPattern"]
    if status == "blocked":
        return f"{base}，而且目前聯絡被擋住，不能把任何行動寫成直接推進。"
    if status == "no-contact":
        return f"{base}，目前還缺少自然互動，需要先看是否有比較接得住的小回應。"
    if status == "occasional-contact":
        return f"{base}，偶爾回覆只表示還有零星聯絡，不能直接當成關係已經變穩。"
    if status == "still-in-contact":
        return f"{base}，雖然還能聊天，但延續性與主動性才是判斷重點。"
    if status == "living-or-working-together":
        return f"{base}，共同場域會放大尷尬與壓力，行動需要保留退路。"
    return base


def relationship_thesis_contextual_shift(context: dict[str, str], template: dict[str, str]) -> str:
    status = context.get("contact_status", "")
    base = template["desiredShift"]
    if status == "blocked":
        return f"{base}；如果對方已經不讓你聯絡，現在先不要繞路找他，先把自己穩住。"
    if status == "no-contact":
        return f"{base}；先看是否出現不要求立刻回答、也能自然停下的小開口。"
    if status == "still-in-contact":
        return f"{base}；重點是他是否也會主動把互動往前帶。"
    if status == "living-or-working-together":
        return f"{base}；不要把共同場域變成攤牌現場。"
    return base


def relationship_thesis_central_thesis(dynamic_key: str, context: dict[str, str], template: dict[str, str]) -> str:
    dynamic_clause = {
        "saturn_pressure": "這段關係目前不是沒有牽引，而是靠近一變成責任、界線或承擔，回應就容易收緊。",
        "emotional_safety": "這段關係的核心不是單純喜不喜歡，而是安全感被觸發後，小反應很容易被放大。",
        "communication_repair": "這段關係卡在說法和承接量：越想一次講清楚，對方越容易只感到被推著回答。",
        "attraction_pursuit": "這段關係看得到吸引和靠近感，但火花後面還要有持續行動，才算真的往前。",
        "action_conflict": "這段關係容易在靠近速度上升溫：越想快點處理，氣氛越容易變硬。",
        "identity_rhythm": "這段關係卡住時會碰到自尊、被看見和被尊重的位置。",
        "outer_intensity": "這段關係的牽引感可能很強，但強度也容易讓人用想像補足現實空白。",
    }.get(dynamic_key, template["centralThesis"])
    question_clause = {
        "still-love-me": "所以答案要看他是否有不被追問也會延續的回應，而不是只看當下有沒有一句表態。",
        "any-chance": "修復空間要看這個循環能不能變小，而不是只看還有沒有感覺。",
        "when-to-contact": "時機判斷要看現在能不能承受短、輕、可退場的互動。",
        "what-did-i-do-wrong": "你要看的不是把錯全攬回自己，而是哪個互動環節可以調小。",
        "stay-or-let-go": "是否繼續等待，要看現實回應有沒有讓你更穩，而不是更耗。",
    }.get(context.get("main_question", ""), "")
    contact_clause = {
        "blocked": "目前通道受阻，任何判讀都必須先尊重界線。",
        "no-contact": "目前沒有自然通道，先觀察是否出現不用你連續推動的小回應。",
        "occasional-contact": "偶爾回覆只表示還有零星聯絡，不能直接當成關係已經變穩。",
        "still-in-contact": "既然還有聯絡，重點變成他是否也會主動延續，而不是只被動接話。",
        "living-or-working-together": "共同場域會放大尷尬和壓力，先保護日常承受度。",
    }.get(context.get("contact_status", ""), "")
    return " ".join(part for part in (dynamic_clause, question_clause, contact_clause) if part)


def relationship_thesis_observable_signs(dynamic_key: str) -> list[dict[str, Any]]:
    common_supportive = {
        "key": "partner-continues-without-prompt",
        "behavior": "他是否在沒有被追問時，也會主動把話題接下去",
        "interpretation": "這代表互動開始從被動回覆變成可延續",
        "valence": "supportive",
        "evidenceIds": ["E-synastry-theme", "E-context-state"],
    }
    common_caution = {
        "key": "reply-only-after-user-prompt",
        "behavior": "回應是否只在你主動後短暫出現，之後又回到沉默或很短",
        "interpretation": "這代表牽動還沒有變成持續行動",
        "valence": "caution",
        "evidenceIds": ["E-context-state", "E-partner-need"],
    }
    by_key = {
        "communication_repair": [
            {
                "key": "short-specific-message-is-easier",
                "behavior": "你只傳一件具體小事時，他是否比較容易回到對話",
                "interpretation": "這代表卡點主要在說法和承接量，而不是完全不能修復",
                "valence": "supportive",
                "evidenceIds": ["E-user-need", "E-partner-need", "E-synastry-theme"],
            },
            {
                "key": "long-explanation-shrinks-reply",
                "behavior": "長篇解釋或補訊息後，他是否回得更慢、更短",
                "interpretation": "這代表說清楚的方式正在變成壓力",
                "valence": "caution",
                "evidenceIds": ["E-partner-need", "E-context-state"],
            },
        ],
        "saturn_pressure": [
            {
                "key": "small-concrete-topic-lowers-defense",
                "behavior": "話題縮小到一件具體小事時，他是否比較不防衛",
                "interpretation": "這代表界線壓力有下降，互動承受度變高",
                "valence": "supportive",
                "evidenceIds": ["E-partner-need", "E-timing-activation"],
            },
            {
                "key": "commitment-topic-shrinks-reply",
                "behavior": "一談承諾、責任或關係定位，他是否立刻延後或縮短回應",
                "interpretation": "這代表壓力仍然主導互動",
                "valence": "caution",
                "evidenceIds": ["E-synastry-theme", "E-context-state"],
            },
        ],
        "action_conflict": [
            {
                "key": "smaller-action-lowers-conflict",
                "behavior": "你把行動變小後，互動是否比較少爭辯或比較能平穩結束",
                "interpretation": "這代表降速能降低對抗",
                "valence": "supportive",
                "evidenceIds": ["E-synastry-theme", "E-context-state"],
            },
            {
                "key": "confrontation-hardens-tone",
                "behavior": "一攤牌或測試反應，語氣是否很快變硬",
                "interpretation": "這代表推進速度仍在引發防衛",
                "valence": "caution",
                "evidenceIds": ["E-partner-need", "E-synastry-theme"],
            },
        ],
        "outer_intensity": [
            {
                "key": "intensity-has-continuous-action",
                "behavior": "除了情緒強烈之外，是否有連續、清楚、可看見的行動",
                "interpretation": "這能分辨牽引感和真實投入",
                "valence": "ambiguous",
                "evidenceIds": ["E-synastry-theme", "E-context-state"],
            },
            {
                "key": "interaction-relies-on-guessing",
                "behavior": "互動是否主要靠猜測、回憶或氣氛撐住",
                "interpretation": "這代表現實證據不足，判讀要保守",
                "valence": "caution",
                "evidenceIds": ["E-method-boundary", "E-context-state"],
            },
        ],
    }
    return by_key.get(dynamic_key, [common_supportive, common_caution])


def relationship_thesis_contextual_observable_signs(
    dynamic_key: str,
    context: dict[str, str],
) -> list[dict[str, Any]]:
    signs = relationship_thesis_observable_signs(dynamic_key)
    status = context.get("contact_status", "")
    if status == "blocked":
        contextual = {
            "key": "permitted-channel-respected",
            "behavior": "是否仍有被允許、尊重界線的既有通道，而不是繞路逼近",
            "interpretation": "通道受阻時，界線比測反應更重要",
            "valence": "caution",
            "evidenceIds": ["E-context-state", "E-method-boundary"],
        }
    elif status == "no-contact":
        contextual = {
            "key": "unforced-channel-appears",
            "behavior": "是否出現不需要你連續推動的自然小通道",
            "interpretation": "沒有自然通道時，主動加碼容易讓壓力更高",
            "valence": "ambiguous",
            "evidenceIds": ["E-context-state", "E-timing-activation"],
        }
    elif status == "still-in-contact":
        contextual = {
            "key": "partner-initiates-continuation",
            "behavior": "聊天是否由他主動延續，而不是每次都只回你丟出的題目",
            "interpretation": "還有聯絡時，主動延續比單次回覆更能說明關係是否往前",
            "valence": "supportive",
            "evidenceIds": ["E-context-state", "E-synastry-theme"],
        }
    elif status == "living-or-working-together":
        contextual = {
            "key": "shared-space-stays-civil",
            "behavior": "共同場域裡是否能維持禮貌、自然、不逼談關係",
            "interpretation": "共同場域需要先保護日常承受度",
            "valence": "ambiguous",
            "evidenceIds": ["E-context-state", "E-method-boundary"],
        }
    else:
        contextual = {
            "key": "spontaneous-next-interaction",
            "behavior": "是否有不靠你追問也能延續的下一次互動",
            "interpretation": "自然延續是判斷關係能否往前的核心線索",
            "valence": "supportive",
            "evidenceIds": ["E-context-state", "E-synastry-theme"],
        }
    return unique_relationship_signs([contextual, *signs])


def unique_relationship_signs(signs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sign in signs:
        behavior = str(sign.get("behavior") or "")
        if not behavior or behavior in seen:
            continue
        seen.add(behavior)
        output.append(sign)
    return output[:4]


def relationship_thesis_change_condition(dynamic_key: str) -> dict[str, list[str]]:
    if dynamic_key == "communication_repair":
        return {
            "strengthensReadingWhen": ["短訊息比長篇更容易被接住", "對方在沒有被追問時願意延續一點對話"],
            "weakensReadingWhen": ["即使訊息很短且不追問，對方仍長期完全不回", "對方主動清楚說明不想互動"],
        }
    if dynamic_key == "saturn_pressure":
        return {
            "strengthensReadingWhen": ["談責任或定位時回應明顯變慢", "把話題拆小後互動比較能維持"],
            "weakensReadingWhen": ["對方開始穩定承接具體安排", "界線變清楚但語氣不再防衛"],
        }
    if dynamic_key == "attraction_pursuit":
        return {
            "strengthensReadingWhen": ["有熱絡但缺少後續一致行動", "對方只在輕鬆氣氛裡靠近，談到關係就退開"],
            "weakensReadingWhen": ["對方主動延續話題並安排下一步", "好感開始變成穩定、可預期的行動"],
        }
    if dynamic_key == "action_conflict":
        return {
            "strengthensReadingWhen": ["一推進就升溫或變成爭辯", "放小動作後互動反而比較平穩"],
            "weakensReadingWhen": ["雙方能談一件具體小事而不對抗", "對方能在壓力下仍保持清楚回應"],
        }
    return {
        "strengthensReadingWhen": ["互動仍然忽近忽遠，且主要靠你主動維持", "對方回應缺少自然延續"],
        "weakensReadingWhen": ["對方開始主動接話並穩定延續", "互動後你更安心，而不是更累"],
    }


def relationship_thesis_decision_boundary(dynamic_key: str) -> dict[str, str]:
    if dynamic_key == "saturn_pressure":
        return {
            "continueWhen": "只有在壓力變小、話題能被具體承接、對方回應不再只剩防衛時，才繼續觀察。",
            "stepBackWhen": "只要一談關係就延後、縮短或冷掉，先不要把偶爾回應當成進展。",
        }
    if dynamic_key == "communication_repair":
        return {
            "continueWhen": "短、清楚、沒有追問的訊息能被自然接住時，才慢慢延續。",
            "stepBackWhen": "如果你越解釋他越退，先停在保護自己的位置，不要再補第二段或把整段關係一次講完。",
        }
    if dynamic_key == "attraction_pursuit":
        return {
            "continueWhen": "熱絡後仍有穩定接話、主動回到互動或具體行動時，才把它視為進展。",
            "stepBackWhen": "如果只有一時火花，後續仍全靠你維持，就不適合繼續加碼。",
        }
    if dynamic_key == "action_conflict":
        return {
            "continueWhen": "互動可以降速且不變成對抗時，才談下一步。",
            "stepBackWhen": "一測試或攤牌就升溫時，先停止推進，把下一步改回小而可退的互動。",
        }
    return {
        "continueWhen": "對方有可觀察、可延續、不是被逼出來的回應時，才繼續觀察。",
        "stepBackWhen": "如果回應始終短暫、模糊，且互動後你更累，就先把重心收回自己。",
    }


def relationship_thesis_contextual_decision_boundary(
    dynamic_key: str,
    context: dict[str, str],
) -> dict[str, str]:
    boundary = relationship_thesis_decision_boundary(dynamic_key)
    status = context.get("contact_status", "")
    if status == "blocked":
        return {
            "continueWhen": "只有在對方重新開放正常通道、且互動不需要你繞路推進時，才重新觀察。",
            "stepBackWhen": "通道仍被封鎖或對方明確不接觸時，不要把占星牽動當成可以越界的理由。",
        }
    if status == "no-contact":
        return {
            "continueWhen": f"先出現自然小通道，再套用這條界線：{boundary['continueWhen']}",
            "stepBackWhen": f"沒有自然通道時先不加碼；{boundary['stepBackWhen']}",
        }
    if status == "still-in-contact":
        return {
            "continueWhen": f"既有聊天中如果他也會主動延續，再套用這條界線：{boundary['continueWhen']}",
            "stepBackWhen": f"如果每次都只靠你維持話題，{boundary['stepBackWhen']}",
        }
    if status == "living-or-working-together":
        return {
            "continueWhen": "共同場域能維持禮貌、穩定、不逼談關係時，才慢慢觀察是否有自然靠近。",
            "stepBackWhen": "共同場域一變成攤牌、尷尬或壓力來源，就先保護日常界線。",
        }
    return boundary


def relationship_thesis_uncertainty(
    input_quality: dict[str, Any],
    evidence_packet: list[dict[str, Any]],
    selected_candidate: dict[str, Any],
) -> dict[str, str]:
    domains = {str(item.get("domain") or "") for item in evidence_packet if item.get("domain")}
    quality = normalized_case_confidence(input_quality.get("overall"), "medium")
    score = float(selected_candidate.get("score") or 0)
    if quality == "high" and len(domains) >= 5 and score >= 0.72:
        level = "low"
        reason = "本命、合盤、情境與時機證據都有支撐，因此主要不確定性在後續現實互動。"
    elif quality == "low" or len(domains) < 4:
        level = "high"
        reason = "出生資料或證據層不足，判讀要保守，不能把單次回應寫成結論。"
    else:
        level = "medium"
        reason = "證據足以形成互動假設，但仍需要後續回應驗證。"
    return {
        "level": level,
        "reason": reason,
        "alternativeReading": "如果對方開始穩定主動延續互動，這會削弱目前對斷續或防衛循環的判斷。",
    }


def relationship_thesis_validation(thesis: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    packet = thesis.get("evidencePacket") or []
    domains = {str(item.get("domain") or "") for item in packet if item.get("domain")}
    if len(domains) < 2:
        failures.append("minimumEvidenceDomains")
    if "relationshipContext" not in domains:
        failures.append("requiresContextEvidence")
    loop = thesis.get("interactionLoop") or {}
    if not all(loop.get(key) for key in ("userTrigger", "userResponse", "partnerTrigger", "partnerResponse", "reinforcingEffect")):
        failures.append("requiresInteractionMechanism")
    if "partnerNatal" not in domains and any("他" in str(value) or "對方" in str(value) for value in loop.values()):
        failures.append("requiresPartnerEvidenceForPartnerClaim")
    observable = thesis.get("observableSigns") or []
    if len(observable) < 2:
        failures.append("minimumObservableSigns")
    mind_reading_terms = ("愛你", "不愛你", "在乎你", "心裡", "想復合", "想放下")
    for item in observable:
        behavior = str((item or {}).get("behavior") or "")
        if any(term in behavior for term in mind_reading_terms):
            failures.append("observableSignsMustBeBehavioral")
            break
    change = thesis.get("changeCondition") or {}
    if not change.get("strengthensReadingWhen") or not change.get("weakensReadingWhen"):
        failures.append("requiresChangeCondition")
    boundary = thesis.get("decisionBoundary") or {}
    if not boundary.get("continueWhen") or not boundary.get("stepBackWhen"):
        failures.append("requiresDecisionBoundary")
    if not thesis.get("prohibitedConclusions"):
        failures.append("requiresProhibitedConclusions")
    evidence_map = thesis.get("evidenceMap") or []
    mapped_fields = {str(item.get("thesisField") or "") for item in evidence_map}
    for required in ("centralThesis", "interactionLoop", "observableSigns", "decisionBoundary"):
        if required not in mapped_fields:
            failures.append(f"evidenceMapMissing:{required}")
    if thesis.get("selectedCandidateId") and not thesis.get("candidateDynamics"):
        failures.append("candidateDynamicsMissing")
    if len(packet) < 4:
        warnings.append("thinEvidencePacket")
    return {
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        "hardRequirements": RELATIONSHIP_THESIS_HARD_REQUIREMENTS,
    }


def relationship_thesis_payload(
    *,
    context: dict[str, str],
    identity_layer: dict[str, Any],
    synastry_layer: dict[str, list[dict[str, Any]]],
    timing_items: list[dict[str, Any]],
    input_quality: dict[str, Any],
    evidence_clusters: dict[str, dict[str, Any]],
    relationship_insights: dict[str, Any],
    answer_layer: dict[str, Any],
) -> dict[str, Any]:
    question_key = context.get("main_question", "")
    evidence_packet = relationship_thesis_evidence_packet(
        context=context,
        identity_layer=identity_layer,
        synastry_layer=synastry_layer,
        evidence_clusters=evidence_clusters,
        relationship_insights=relationship_insights,
        answer_layer=answer_layer,
        timing_items=timing_items,
    )
    candidates = relationship_thesis_candidate_dynamics(
        context=context,
        evidence_packet=evidence_packet,
        repeated_theme_context=answer_layer.get("repeatedThemeContext") or {},
        evidence_clusters=evidence_clusters,
    )
    selected = candidates[0] if candidates else {
        "id": "C1",
        "dynamicKey": "fallback",
        "dynamic": THESIS_FALLBACK_TEMPLATE["dynamic"],
        "evidenceIds": [str(item.get("id") or "") for item in evidence_packet if item.get("id")],
        "score": 0.5,
        "rankingFactors": {
            "questionRelevance": 0.5,
            "currentActivation": 0.5,
            "evidenceStrength": 0.5,
            "crossLayerSupport": 0.5,
            "caseDistinctiveness": 0.4,
            "overreachPenalty": 0.1,
        },
    }
    dynamic_key = str(selected.get("dynamicKey") or "fallback")
    template = THESIS_DYNAMIC_TEMPLATES.get(dynamic_key) or THESIS_FALLBACK_TEMPLATE
    evidence_ids = [str(item.get("id") or "") for item in evidence_packet if item.get("id")]
    thesis = {
        "version": "relationship-thesis-v1",
        "questionKey": question_key,
        "questionReframe": template["questionReframe"],
        "centralThesis": relationship_thesis_central_thesis(dynamic_key, context, template),
        "dominantTension": {
            "poleA": template["poleA"],
            "poleB": template["poleB"],
            "currentPattern": relationship_thesis_contextual_pattern(context, template),
            "desiredShift": relationship_thesis_contextual_shift(context, template),
        },
        "interactionLoop": {
            "userTrigger": template["userTrigger"],
            "userResponse": template["userResponse"],
            "partnerTrigger": template["partnerTrigger"],
            "partnerResponse": template["partnerResponse"],
            "reinforcingEffect": template["reinforcingEffect"],
        },
        "currentActivation": relationship_thesis_current_activation(context, template),
        "centralDynamicKey": dynamic_key,
        "secondaryModifier": template.get("secondaryModifier") or "",
        "observableSigns": relationship_thesis_contextual_observable_signs(dynamic_key, context),
        "changeCondition": relationship_thesis_change_condition(dynamic_key),
        "decisionBoundary": relationship_thesis_contextual_decision_boundary(dynamic_key, context),
        "uncertainty": relationship_thesis_uncertainty(input_quality, evidence_packet, selected),
        "evidencePacket": evidence_packet,
        "candidateDynamics": candidates,
        "selectedCandidateId": str(selected.get("id") or "C1"),
        "evidenceMap": [
            {"thesisField": "centralThesis", "evidenceIds": unique(["E-user-need", "E-partner-need", "E-synastry-theme", "E-context-state"])},
            {"thesisField": "dominantTension", "evidenceIds": unique(["E-user-need", "E-partner-need", "E-synastry-theme"])},
            {"thesisField": "interactionLoop", "evidenceIds": unique(["E-user-need", "E-partner-need", "E-synastry-theme", "E-context-state"])},
            {"thesisField": "currentActivation", "evidenceIds": unique(["E-context-state", "E-timing-activation"])},
            {"thesisField": "observableSigns", "evidenceIds": unique(["E-synastry-theme", "E-context-state", "E-partner-need"])},
            {"thesisField": "decisionBoundary", "evidenceIds": unique(["E-context-state", "E-method-boundary", "E-timing-activation"])},
        ],
        "prohibitedConclusions": [
            "不能說他一定還愛你或一定不愛你",
            "不能保證復合、斷聯結束或聯絡成功",
            "不能用單次回覆當作最終關係答案",
            "不能把現實聯絡狀態單獨當成星盤結論",
            "不能指定精準成功日期",
        ],
        "sourceClaimIds": unique([claim_id for item in evidence_packet for claim_id in item.get("sourceClaimIds") or []]),
        "methodClaimIds": unique([*RELATIONSHIP_THESIS_METHOD_CLAIM_IDS, *[claim_id for item in evidence_packet for claim_id in item.get("methodClaimIds") or []]]),
        "evidenceClusterKeys": unique([key for item in evidence_packet for key in item.get("evidenceClusterKeys") or []]),
    }
    thesis["validation"] = relationship_thesis_validation(thesis)
    return thesis


def relationship_thesis_cluster(thesis: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": "western-evidence-cluster-v1",
        "category": "relationshipThesis",
        "label": "Relationship thesis",
        "technical": thesis.get("centralThesis") or "",
        "emotionalMeaning": thesis.get("questionReframe") or thesis.get("centralThesis") or "",
        "doesNotProve": "Relationship thesis is an evidence-linked interaction hypothesis, not a guaranteed outcome.",
        "confidence": (thesis.get("uncertainty") or {}).get("level") or "medium",
        "source": "relationship-thesis-v1",
        "claimIds": thesis.get("sourceClaimIds") or [],
        "methodClaimIds": thesis.get("methodClaimIds") or [],
        "strongestStrength": max([float(item.get("score") or 0) for item in thesis.get("candidateDynamics") or []] or [0.0]),
        "evidence": thesis.get("evidencePacket") or [],
    }


RELATIONSHIP_CASE_MODEL_VERSION = "relationship-case-model-v1"

RELATIONSHIP_CASE_MODEL_SECTION_IDS = (
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
)

RELATIONSHIP_CASE_MODEL_DYNAMIC_ROLES = {"amplifier", "blocker", "repairLever", "softener", "timingActivator"}

RELATIONSHIP_CASE_MODEL_ROLE_LABELS = {
    "amplifier": "會放大主題的另一條線索",
    "blocker": "目前最容易卡住的另一條線索",
    "repairLever": "比較能打開修復的另一條線索",
    "softener": "可以讓語氣變柔和的另一條線索",
    "timingActivator": "會讓時機變敏感的另一條線索",
}

RELATIONSHIP_CASE_MODEL_ROLE_COPY = {
    "attraction_pursuit": {
        "amplifier": "吸引感會讓你更想靠近，但它只放大期待，還不能直接證明對方會有持續行動。",
        "blocker": "如果只剩曖昧熱度，後續沒有穩定行動，這份吸引會變成新的不安來源。",
        "repairLever": "輕鬆、可退場的靠近感可以當作開口，但不能一開始就要求關係定位。",
        "softener": "保留一點自然好感，會比直接要求答案更容易讓對話不僵住。",
        "timingActivator": "時機稍微變柔和時，可以觀察吸引是否變成主動延續，而不是只看一時熱絡。",
    },
    "saturn_pressure": {
        "amplifier": "責任與界線會把原本的小問題變重，讓每一次靠近都像需要立刻承擔。",
        "blocker": "真正卡住的地方通常是壓力承受度；一旦話題太像承諾檢查，回應就容易收緊。",
        "repairLever": "修復要先降低責任感，不把一次對話變成關係審判。",
        "softener": "把期待說得更具體、更少壓力，會比要求完整表態更容易被接住。",
        "timingActivator": "現在若同時有土星式壓力，時機判讀要保守，先看壓力能否下降。",
    },
    "communication_repair": {
        "amplifier": "說法會放大主題：同一份在意，如果寫成追問，就會變成壓力。",
        "blocker": "卡點不是沒有話可說，而是話量和問題密度讓對方覺得接不住。",
        "repairLever": "最可用的修復入口是短、清楚、只處理一件事的訊號。",
        "softener": "把解釋縮短、保留退路，能讓對話比較不像逼答案。",
        "timingActivator": "時機稍微打開時，重點不是多說，而是用更小的訊息測承接度。",
    },
    "emotional_safety": {
        "amplifier": "安全感議題會讓小反應被放大；你越在意細節，越需要把判讀拉回多次互動。",
        "blocker": "真正阻礙不是一句冷淡，而是安全感被觸發後，雙方都更難自然回應。",
        "repairLever": "修復要先讓互動變穩，讓對方在沒有被追問時也能自然接話。",
        "softener": "先照顧安全感，語氣就比較不會從確認變成壓迫。",
        "timingActivator": "當情緒安全感被觸發時，時機要看互動能否變安定，而不是只看有沒有回覆。",
    },
    "action_conflict": {
        "amplifier": "行動速度會放大衝突；越急著處理，越容易讓對方只感到被推近。",
        "blocker": "現在最容易卡在節奏：動作一大，對方就比較可能用硬反應保護自己。",
        "repairLever": "修復不是不行動，而是把行動縮到不需要對方立刻表態的一步。",
        "softener": "先降速能保留對話空間，避免原本可談的事變成攻防。",
        "timingActivator": "這條線索會讓時機更敏感；需要避開攤牌、測試和連續補訊息。",
    },
    "identity_rhythm": {
        "amplifier": "被看見與被尊重的需求會放大反應；一旦像在比誰低頭，對方更容易守住面子。",
        "blocker": "真正卡住的是自尊位置，要求承認或證明在乎時，對方可能先保護退路。",
        "repairLever": "修復要保留台階，讓對方可以在不被審判的位置重新靠近。",
        "softener": "尊重感會讓對話沒那麼緊，比說服對方承認更能打開後續互動。",
        "timingActivator": "共同場域或敏感時段裡，面子與台階會影響對方願不願意自然回應。",
    },
    "outer_intensity": {
        "amplifier": "強烈牽引會放大想像；感覺越重，越要回頭看對方有沒有清楚行動。",
        "blocker": "如果現實行動不足，強度本身會變成誤讀來源，讓你更難判斷對方真正投入多少。",
        "repairLever": "修復不能靠命定感推進，而要回到對方是否有清楚、連續、可觀察的行動。",
        "softener": "先承認感覺很強，再把結論放慢，能避免用想像補足現實空白。",
        "timingActivator": "強度高的時候，時機判讀要更重視界線與可觀察行動。",
    },
}

RELATIONSHIP_CASE_MODEL_PAIR_GRAMMAR = {
    ("saturn_pressure", "attraction_pursuit"): {
        "grammarId": "pair-saturn-pressure-attraction-pursuit-v1",
        "dynamicInteraction": "這組動力的關鍵是：吸引沒有消失，但一靠近就會碰到責任、界線或承擔感。",
        "whatThisMeans": "有火花不等於可以直接推進；吸引只能說明還有牽動，真正要看的是對方能不能在壓力不升高時持續回應。",
        "whatItDoesNotMean": "這不代表他一定不在意，也不代表一次熱絡就能抵消界線壓力。",
        "repairImplication": "修復要先把關係題目變小，讓吸引留在輕鬆互動裡，而不是立刻變成承諾檢查。",
        "actionBoundary": "如果一談定位、責任或下一步就變慢變短，先不要把好感當成可以加碼的理由。",
        "phrasesToAvoid": ["他其實一定還喜歡你", "有吸引就有機會", "只要主動一點就能打開"],
    },
    ("action_conflict", "attraction_pursuit"): {
        "grammarId": "pair-action-conflict-attraction-pursuit-v1",
        "dynamicInteraction": "這組動力是火花推高行動衝動：越感覺有吸引，越容易想立刻測反應。",
        "whatThisMeans": "吸引會讓你更想快點確認，但這段關係真正卡住的是速度；推得越快，對方越可能只感到被逼近。",
        "whatItDoesNotMean": "這不代表吸引是假的，而是吸引不能直接變成行動許可。",
        "repairImplication": "有用的做法不是壓住感覺，而是把動作縮小到不需要對方立刻表態的一步。",
        "actionBoundary": "只要你發現自己想測試、攤牌或連續補訊息，就先停在一個可退場的小互動。",
        "phrasesToAvoid": ["火花強就要趁熱打鐵", "直接問清楚最快", "越快處理越好"],
    },
    ("action_conflict", "emotional_safety"): {
        "grammarId": "pair-action-conflict-emotional-safety-v1",
        "dynamicInteraction": "這組動力是不安把靠近的步調推快：越想快點安心，越容易讓對話變成逼答案。",
        "whatThisMeans": "你問的不是誰比較有理，而是確認安全感的方式會不會太急；一急，對方感受到的可能不是你的需要，而是必須立刻回答的壓力。",
        "whatItDoesNotMean": "這不代表你不能表達不安，也不代表沉默就比較成熟。",
        "repairImplication": "修復要先把安全感需求說小一點，只處理一個具體感受，不要求對方一次把關係說滿。",
        "actionBoundary": "如果你準備用攤牌、追問或測試來換安心，這一步就太大，先退回可以自然收尾的短互動。",
        "phrasesToAvoid": ["直接問清楚才安全", "現在不說就沒機會", "用測試確認他還在不在乎"],
    },
    ("emotional_safety", "attraction_pursuit"): {
        "grammarId": "pair-emotional-safety-attraction-pursuit-v1",
        "dynamicInteraction": "這組動力是吸引放大不安：火花可能還在，但它會讓你更急著確認安全感。",
        "whatThisMeans": "吸引可以說明你們還有牽動，卻不能證明安全感已經恢復；真正要看的是熱度之後有沒有穩定、自然、可延續的回應。",
        "whatItDoesNotMean": "這不代表對方一句熱絡就等於還想回來，也不代表冷一下就完全沒有感覺。",
        "repairImplication": "修復要先讓互動變安定，不要用火花逼出保證，先觀察對方是否在沒有被追問時也會接住。",
        "actionBoundary": "如果吸引之後你更焦慮、更想查證或更想連續確認，就先把行動放小。",
        "phrasesToAvoid": ["有火花就安全了", "他一定還愛你", "只要再靠近一點就會穩"],
    },
    ("attraction_pursuit", "action_conflict"): {
        "grammarId": "pair-attraction-pursuit-action-conflict-v1",
        "dynamicInteraction": "這條主線是吸引帶來靠近感，但一急著推進，就容易讓靠近變成對抗。",
        "whatThisMeans": "關係不是沒有吸引，而是吸引之後的下一步太快時，對方容易從有反應轉成退開。",
        "whatItDoesNotMean": "這不代表你要完全不動，也不代表每一次熱絡都能被解讀成關係已經變穩。",
        "repairImplication": "修復不是只看有沒有曖昧，而是看能不能變成壓力小、能接下去的小互動。",
        "actionBoundary": "只要下一步需要對方立刻定義關係、承諾或回答立場，就先不要做。",
        "phrasesToAvoid": ["有曖昧就能推進", "趁他有反應時逼出答案", "熱絡就是進展"],
    },
    ("identity_rhythm", "emotional_safety"): {
        "grammarId": "pair-identity-rhythm-emotional-safety-v1",
        "dynamicInteraction": "這組動力是自尊位置和安全感互相反應：越想被看見，越容易把細節讀成自己不重要。",
        "whatThisMeans": "核心不是逼對方承認，而是讓彼此都保有台階；安全感要靠穩定回應累積，不是靠一次證明。",
        "whatItDoesNotMean": "這不代表你要委屈自己，也不代表對方退一步就一定是否定你。",
        "repairImplication": "修復要先保留尊重感，用不審判、不比較的語氣讓對方有空間自然靠近。",
        "actionBoundary": "如果你正在要求他證明在乎、承認錯誤或立刻給你位置，先把問題縮回可回答的小事。",
        "phrasesToAvoid": ["逼他承認才算有答案", "他不表態就是否定你", "一定要爭回位置"],
    },
    ("communication_repair", "saturn_pressure"): {
        "grammarId": "pair-communication-repair-saturn-pressure-v1",
        "dynamicInteraction": "這組動力是想說清楚碰到承擔壓力：話越完整，對方越可能覺得要立刻負責。",
        "whatThisMeans": "修復不是多解釋，而是降低承接量；越像關係審判，越會讓對方退回保守位置。",
        "whatItDoesNotMean": "這不代表不能溝通，而是不適合用長文、追問或一次性總結處理。",
        "repairImplication": "最有用的是一件事、一個語氣、一個對方可以先不回的短訊號。",
        "actionBoundary": "如果訊息裡同時有道歉、追問、定位和期待，先分開處理，只留下最小的一件事。",
        "phrasesToAvoid": ["一次說清楚就會好", "多解釋他就會懂", "把完整心情全部傳出去"],
    },
    ("communication_repair", "action_conflict"): {
        "grammarId": "pair-communication-repair-action-conflict-v1",
        "dynamicInteraction": "這組動力是修復意圖被行動速度帶歪：原本想說清楚，最後像是在推對方回答。",
        "whatThisMeans": "你要調整的不是誠意，而是節奏；同樣一句話，如果帶著測試或急迫感，就會變成對抗。",
        "whatItDoesNotMean": "這不代表錯都在你，也不代表沉默就是唯一選項。",
        "repairImplication": "修復要把語氣從追答案改成交代一件具體小事，說完就停。",
        "actionBoundary": "如果你期待對方立刻安撫、立刻表態或立刻回到原狀，這一步就太大。",
        "phrasesToAvoid": ["只要講清楚就能馬上修復", "測一下他的反應", "再補一段他就會懂"],
    },
    ("emotional_safety", "saturn_pressure"): {
        "grammarId": "pair-emotional-safety-saturn-pressure-v1",
        "dynamicInteraction": "這組動力是安全感需求碰到責任壓力：越需要確認，對方越容易覺得要承擔。",
        "whatThisMeans": "核心不是有沒有感覺，而是安全感一被觸發，關係題目就變重；對方可能先慢下來保護界線。",
        "whatItDoesNotMean": "這不等於他完全沒感覺，也不等於你只能一直等待。",
        "repairImplication": "修復要先讓壓力變輕，用可觀察的小回應累積安全感，不用一次要完整答案。",
        "actionBoundary": "如果你的問題會讓對方必須立刻承諾、解釋或負責，先不要送出。",
        "phrasesToAvoid": ["慢回就是不愛", "只要確認一次就安心", "逼出承諾才安全"],
    },
    ("action_conflict", "communication_repair"): {
        "grammarId": "pair-action-conflict-communication-repair-v1",
        "dynamicInteraction": "這組動力是衝突速度裡還有修復入口：不是不能談，而是不能用急的方式談。",
        "whatThisMeans": "真正有用的不是更大動作，而是把話縮小到對方能接住的範圍；修復入口存在，但會被速度破壞。",
        "whatItDoesNotMean": "這不代表你要完全吞下來，也不代表立刻攤牌才算有處理。",
        "repairImplication": "先選一件最具體、壓力最小的事說，避免把過去所有問題放進同一段訊息。",
        "actionBoundary": "如果對話已經開始辯輸贏、翻舊帳或測忠誠，就先停，不要再補第二段。",
        "phrasesToAvoid": ["現在就把所有問題講完", "不講完就沒機會", "爭出誰對誰錯"],
    },
    ("outer_intensity", "saturn_pressure"): {
        "grammarId": "pair-outer-intensity-saturn-pressure-v1",
        "dynamicInteraction": "這組動力是強烈牽引碰到現實界線：感覺越重，越不能跳過對方的承受度。",
        "whatThisMeans": "強度只能說明這段關係對你很有重量，不能取代現實行動；界線存在時，尊重界線比證明命定更重要。",
        "whatItDoesNotMean": "這不代表感覺是假的，也不代表可以用強烈感受合理化越界。",
        "repairImplication": "修復要回到清楚、連續、被允許的回應，而不是靠回憶、巧合或想像補足。",
        "actionBoundary": "如果通道受阻、對方明確退開或互動只能靠你繞路推進，就先停止行動。",
        "phrasesToAvoid": ["這麼強一定有命定", "感覺強就可以越過界線", "只要再證明一次"],
    },
}


DOMINANT_NARRATIVE_ANGLE_VERSION = "dominant-narrative-angle-v1"

DOMINANT_NARRATIVE_ANGLE_TEMPLATES: dict[str, dict[str, Any]] = {
    "action_conflict": {
        "title": "速度和火花線",
        "humanThesis": "你們不是沒有火花，只是每次急著把問題處理好，對話就容易變硬，最後像在吵誰對誰錯。",
        "emotionalStakes": "真正敏感的是誰先推進、誰被推著走；越急著把答案弄清楚，越容易讓對方只感到被逼近。",
        "coreMisread": "不要把對方反應變硬直接看成沒感覺；它也可能是被速度和行動壓力觸發。",
        "repairPrinciple": "修復要先把動作縮小，讓火花留在可停下、可回應的小互動裡，不用一次推到關係結論。",
        "stopLine": "一旦你想攤牌、測反應或連續補訊息，就先停，因為這正是這條線最容易失控的地方。",
        "concreteBehaviorMarkers": ["行動", "推進", "速度", "火花", "對抗", "升溫", "急"],
    },
    "attraction_pursuit": {
        "title": "吸引延續線",
        "humanThesis": "這段關係看得到吸引和靠近感，但真正要看的不是一時火花，而是熱絡之後能不能穩定延續。",
        "emotionalStakes": "吸引會讓人想靠近，也容易讓人把一次反應放大成答案；這裡要把曖昧、熱絡和穩定行動分開。",
        "coreMisread": "不要把有反應直接看成承諾，也不要把一時變冷就看成完全沒有感覺。",
        "repairPrinciple": "修復要讓靠近變輕，先看火花後面有沒有自然接續，而不是用吸引去推進關係定義。",
        "stopLine": "如果互動只有曖昧感，沒有後續清楚行動，就先不要把它當成關係已經往前。",
        "concreteBehaviorMarkers": ["吸引", "火花", "曖昧", "靠近", "熱絡", "反應"],
    },
    "communication_repair": {
        "title": "說法修復線",
        "humanThesis": "你們卡住的核心常在說法和承接量：想說清楚是好的，但訊息、長文或補充太多時，對方容易只聽見壓力。",
        "emotionalStakes": "真正敏感的是話一出口會不會被聽成追問、說服或逼表態；溝通要能讓對方接話，而不是逼他立刻回答。",
        "coreMisread": "不要把「講更多」當成修復，也不要把對方一時接不住全部解讀成你表達錯了。",
        "repairPrinciple": "修復要把表達拆短：一則訊息只處理一件具體小事，說清楚後要有停點。",
        "stopLine": "如果你準備發長文、連續補充或同時道歉又追問，就先刪到只剩一件事。",
        "concreteBehaviorMarkers": ["說清楚", "溝通", "訊息", "長文", "接話", "表達"],
    },
    "emotional_safety": {
        "title": "安全感承接線",
        "humanThesis": "這段關係的核心不是單純喜不喜歡，而是情緒和不安被碰到時，彼此能不能穩定接住。",
        "emotionalStakes": "安全感一被觸發，小回覆、小沉默都容易被放大；越想確認，越需要讓表達變具體、安定。",
        "coreMisread": "不要把一次冷淡當成全部答案，也不要把偶爾溫柔當成安全感已經恢復。",
        "repairPrinciple": "修復要先建立可預期的小回應，讓情緒不用每次都靠追問重新確認。",
        "stopLine": "如果你正在用反覆確認換安心，先回到一個具體感受，不把全部不安一次交給對方。",
        "concreteBehaviorMarkers": ["安全感", "情緒", "安定", "被接住", "溫柔", "不安"],
    },
    "identity_rhythm": {
        "title": "自尊和步調線",
        "humanThesis": "你們卡住的不是單純沒有感覺，而是自尊、被看見和主導權很容易被碰到；誰先低頭、誰失去步調，都會讓互動變硬。",
        "emotionalStakes": "真正敏感的是尊重感和自由感：一旦像在比較誰比較在乎、誰該承認，對方就容易守住面子和退路。",
        "coreMisread": "不要把對方不立刻表態看成否定你；有時他是在保護主導權、自尊和自己的節奏。",
        "repairPrinciple": "修復要先留台階，用不比較、不審判的方式讓彼此都能保有被看見和被尊重的感覺。",
        "stopLine": "只要對話變成逼他低頭、逼他承認或搶回主導權，就先退回尊重感，不再加碼。",
        "concreteBehaviorMarkers": ["自尊", "節奏", "自由", "被看見", "步調", "主導權"],
    },
    "outer_intensity": {
        "title": "強烈拉扯線",
        "humanThesis": "這段關係的強度可能很真，但強烈、拉扯和執著也會放大想像，讓判斷被失控感帶走。",
        "emotionalStakes": "真正敏感的是你會不會把強度當成答案；感覺越重，越要回到現實行動、界線和可觀察證據。",
        "coreMisread": "不要把命定感、巧合或氣氛直接看成持續行動；強烈牽引不是關係承諾。",
        "repairPrinciple": "修復要把強烈感放回現實驗證，只看日常裡是否有清楚回覆、自然開口、連續且被允許的行動。",
        "stopLine": "如果互動主要靠猜測、回憶、執著或繞路維持，就先停止加碼，回到自己的界線。",
        "concreteBehaviorMarkers": ["強烈", "失控", "拉扯", "執著", "強度", "放大"],
    },
    "saturn_pressure": {
        "title": "責任和界線線",
        "humanThesis": "這段關係目前不是沒有牽引，而是靠近一變成責任、承諾、現實或界線，回應就容易收緊。",
        "emotionalStakes": "真正敏感的是距離和壓力：話題越像要對方立刻承擔，他越可能先退回安全位置。",
        "coreMisread": "不要把慢、冷或延後直接看成沒感覺；它也可能是責任壓力讓對方先保守。",
        "repairPrinciple": "修復要先降低承擔感，把關係題目拆成具體、可做到的小行動。",
        "stopLine": "一談責任、承諾或定位就變慢變短時，不要再用更多解釋加壓。",
        "concreteBehaviorMarkers": ["責任", "承諾", "壓力", "現實", "界線", "距離"],
    },
}

DOMINANT_NARRATIVE_SECTION_DIRECTIVES: dict[str, dict[str, dict[str, str]]] = {
    "chart-positioning": {
        "default": {
            "meaning": "安全感、說話方式、喜歡方式、行動節奏和緊張時的反應，構成兩個人的關係底色。",
            "bridge": "需要、習慣和緊張時保護自己的方式，很容易在靠近時被彼此誤讀。",
            "nextMove": "分清眼前的反應是需要、習慣，還是緊張時保護自己的方式。",
        }
    },
    "relationship-fit": {
        "default": {
            "meaning": "用「{title}」看你們的相處：吸引力在哪裡、卡住的地方是什麼、能不能繼續要靠哪個條件。",
            "bridge": "先抓主線：{humanThesis}",
            "nextMove": "下一次互動只調整「{title}」裡最容易失衡的一小步，不把整段關係一次重談。",
            "caution": "{coreMisread}",
        }
    },
    "core-answer": {
        "default": {
            "meaning": "核心問題先回答你真正想問的事，再分開看星盤能支持什麼、現實還要確認什麼。",
            "bridge": "這一題先不要被單一句話帶走，重點是看現實互動有沒有跟著變清楚。",
            "nextMove": "接下來只看兩件事：他會不會自然接話，以及行動有沒有比以前更清楚。",
            "caution": "不要用某一次回覆替整段關係下結論；要看後面是否真的連續出現。",
        }
    },
    "timing-reading": {
        "default": {
            "meaning": "目前適合靠近、觀察，還是先不要動，要由聯絡狀態和壓力決定。",
            "bridge": "放到時機裡，重點不是哪一天最神準，而是現在能不能承受一個小動作。",
            "nextMove": "能讓互動變穩才靠近；只要會讓氣氛更緊，就先把動作縮小。",
            "caution": "不是指定日期，也不是保證對方會回，而是幫你判斷現在適合多大動作。",
        }
    },
    "action-direction": {
        "default": {
            "meaning": "下一步要同時包含怎麼說、先避開什麼、做到哪裡要停，以及不要怎麼自我解讀。",
            "bridge": "{repairPrinciple}",
            "nextMove": "下一步只做一件小事，做完就看現實回應，不連續加碼。",
            "caution": "{stopLine}",
        }
    },
}


def dominant_narrative_text(template: str, angle: dict[str, Any]) -> str:
    try:
        return normalize_zh_text(template.format(**{key: str(value or "") for key, value in angle.items()}))
    except KeyError:
        return normalize_zh_text(template)


def dominant_narrative_section_directives(angle: dict[str, Any]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for section_id, directives in DOMINANT_NARRATIVE_SECTION_DIRECTIVES.items():
        selected = directives.get(str(angle.get("primaryDynamicKey") or "")) or directives.get("default") or {}
        output[section_id] = {
            key: dominant_narrative_text(value, angle)
            for key, value in selected.items()
            if value
        }
    return output


def dominant_narrative_angle_payload(
    *,
    context: dict[str, str],
    relationship_case_model: dict[str, Any],
    relationship_thesis: dict[str, Any],
) -> dict[str, Any]:
    primary_dynamic = relationship_case_model.get("primaryDynamic") if isinstance(relationship_case_model.get("primaryDynamic"), dict) else {}
    secondary_dynamics = [item for item in relationship_case_model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    dynamic_interaction = relationship_case_model.get("dynamicInteractionPlan") if isinstance(relationship_case_model.get("dynamicInteractionPlan"), dict) else {}
    primary_key = str(primary_dynamic.get("key") or relationship_thesis.get("centralDynamicKey") or "saturn_pressure")
    template = DOMINANT_NARRATIVE_ANGLE_TEMPLATES.get(primary_key) or DOMINANT_NARRATIVE_ANGLE_TEMPLATES["saturn_pressure"]
    angle: dict[str, Any] = {
        "version": DOMINANT_NARRATIVE_ANGLE_VERSION,
        "primaryDynamicKey": primary_key,
        "primaryDynamicLabel": str(primary_dynamic.get("label") or template.get("title") or primary_key),
        "secondaryDynamicKeys": [str(item.get("key") or "") for item in secondary_dynamics if item.get("key")],
        "questionKey": context.get("main_question", ""),
        "stageKey": context.get("relationship_stage", ""),
        "contactKey": context.get("contact_status", ""),
        "stageLabel": STAGE_LABELS.get(context.get("relationship_stage", ""), context.get("relationship_stage", "") or "目前狀態"),
        "contactLabel": CONTACT_STATUS_LABELS.get(context.get("contact_status", ""), context.get("contact_status", "") or "聯絡狀態未提供"),
        "title": template["title"],
        "humanThesis": template["humanThesis"],
        "emotionalStakes": template["emotionalStakes"],
        "coreMisread": template["coreMisread"],
        "repairPrinciple": template["repairPrinciple"],
        "stopLine": template["stopLine"],
        "concreteBehaviorMarkers": list(template.get("concreteBehaviorMarkers") or []),
        "evidenceClusterKeys": unique(["dominantNarrativeAngle", "relationshipCaseModel", "relationshipThesis"]),
        "sourceClaimIds": unique([
            *[str(item) for item in relationship_case_model.get("sourceClaimIds") or [] if item],
            *[str(item) for item in relationship_thesis.get("sourceClaimIds") or [] if item],
        ]),
        "methodClaimIds": unique([
            *[str(item) for item in relationship_case_model.get("methodClaimIds") or [] if item],
            *[str(item) for item in relationship_thesis.get("methodClaimIds") or [] if item],
        ]),
        "trace": {
            "source": "relationshipCaseModel.primaryDynamic",
            "dynamicInteractionGrammarId": str(dynamic_interaction.get("grammarId") or ""),
            "primaryCandidateId": str(primary_dynamic.get("candidateId") or ""),
        },
    }
    angle["sectionDirectives"] = dominant_narrative_section_directives(angle)
    return angle


def relationship_case_model_primary_dynamic(thesis: dict[str, Any]) -> dict[str, Any]:
    dynamic_key = str(thesis.get("centralDynamicKey") or "fallback")
    selected_id = str(thesis.get("selectedCandidateId") or "")
    candidates = [item for item in thesis.get("candidateDynamics") or [] if isinstance(item, dict)]
    selected = next((item for item in candidates if str(item.get("id") or "") == selected_id), candidates[0] if candidates else {})
    template = THESIS_DYNAMIC_TEMPLATES.get(dynamic_key) or THESIS_FALLBACK_TEMPLATE
    return {
        "key": dynamic_key,
        "label": selected.get("dynamic") or template.get("dynamic") or "關係主軸",
        "score": round(float(selected.get("score") or 0.0), 3),
        "candidateId": str(selected.get("id") or selected_id or "C1"),
        "evidenceIds": unique([str(item) for item in selected.get("evidenceIds") or [] if item]),
        "centralThesis": thesis.get("centralThesis") or template.get("centralThesis") or "",
        "readerMeaning": relationship_case_model_primary_meaning(dynamic_key, thesis),
    }


def relationship_case_model_primary_meaning(dynamic_key: str, thesis: dict[str, Any]) -> str:
    tension = thesis.get("dominantTension") if isinstance(thesis.get("dominantTension"), dict) else {}
    current = str(tension.get("currentPattern") or "")
    shift = str(tension.get("desiredShift") or "")
    if current and shift:
        return normalize_zh_text(f"主軸是「{current}」，真正要看的轉向是「{shift}」。")
    template = THESIS_DYNAMIC_TEMPLATES.get(dynamic_key) or THESIS_FALLBACK_TEMPLATE
    return normalize_zh_text(str(template.get("questionReframe") or template.get("centralThesis") or ""))


def relationship_case_model_secondary_role(
    *,
    primary_key: str,
    secondary_key: str,
    context: dict[str, str],
    timing_guidance: dict[str, Any],
) -> str:
    timing_action = str(timing_guidance.get("recommendedAction") or "")
    question_key = context.get("main_question", "")
    if timing_action == "avoid_push" and secondary_key in {"saturn_pressure", "action_conflict", "outer_intensity"}:
        return "timingActivator"
    if secondary_key in {"saturn_pressure", "action_conflict", "outer_intensity"}:
        return "blocker"
    if secondary_key == "communication_repair":
        return "repairLever"
    if secondary_key == "attraction_pursuit":
        return "amplifier"
    if secondary_key == "emotional_safety":
        return "repairLever" if primary_key in {"saturn_pressure", "action_conflict", "communication_repair"} else "softener"
    if secondary_key == "identity_rhythm":
        return "softener" if question_key != "stay-or-let-go" else "blocker"
    return "softener"


def relationship_case_model_secondary_dynamic(
    *,
    primary_key: str,
    candidate: dict[str, Any],
    context: dict[str, str],
    timing_guidance: dict[str, Any],
) -> dict[str, Any]:
    secondary_key = str(candidate.get("dynamicKey") or "")
    role = relationship_case_model_secondary_role(
        primary_key=primary_key,
        secondary_key=secondary_key,
        context=context,
        timing_guidance=timing_guidance,
    )
    role_copy = RELATIONSHIP_CASE_MODEL_ROLE_COPY.get(secondary_key) or {}
    template = THESIS_DYNAMIC_TEMPLATES.get(secondary_key) or THESIS_FALLBACK_TEMPLATE
    interaction_effect = role_copy.get(role) or template.get("secondaryModifier") or template.get("questionReframe") or ""
    why_it_matters = relationship_case_model_secondary_why_it_matters(
        primary_key=primary_key,
        secondary_key=secondary_key,
        role=role,
        context=context,
    )
    return {
        "key": secondary_key,
        "label": candidate.get("dynamic") or template.get("dynamic") or secondary_key,
        "role": role,
        "roleLabel": RELATIONSHIP_CASE_MODEL_ROLE_LABELS.get(role, role),
        "score": round(float(candidate.get("score") or 0.0), 3),
        "candidateId": str(candidate.get("id") or ""),
        "evidenceIds": unique([str(item) for item in candidate.get("evidenceIds") or [] if item]),
        "interactionEffect": normalize_zh_text(interaction_effect),
        "whyItMatters": normalize_zh_text(why_it_matters),
    }


def relationship_case_model_secondary_why_it_matters(
    *,
    primary_key: str,
    secondary_key: str,
    role: str,
    context: dict[str, str],
) -> str:
    question = {
        "still-love-me": "你問的是對方還有沒有感覺，所以另一條線索要幫你分辨牽動和穩定回應。",
        "any-chance": "你問的是還有沒有機會，所以另一條線索要幫你看修復位置和現實阻力。",
        "when-to-contact": "你問的是何時聯絡，所以另一條線索要幫你決定動作要多小、語氣要多輕。",
        "what-did-i-do-wrong": "你問的是自己哪裡做錯，所以另一條線索要避免把全部責任推回你身上。",
        "stay-or-let-go": "你問的是要不要繼續，所以另一條線索要幫你分辨關係是在變好，還是在繼續消耗你。",
    }.get(context.get("main_question", ""), "另一條線索會改變同一個主題在現實互動裡的表現。")
    if role == "repairLever":
        return f"{question}它提供比較可操作的修復位置，但不能蓋過這一題真正要看的主線。"
    if role == "blocker":
        return f"{question}它是目前比較容易讓互動卡住的條件，不能被吸引或在意感抵消。"
    if role == "timingActivator":
        return f"{question}它會讓現在的時機更敏感，因此行動要更小、更可退場。"
    if role == "amplifier":
        return f"{question}它會放大感受與期待，但還不能單獨變成關係結論。"
    return f"{question}它讓語氣和台階變重要，修復不是靠說服，而是先讓對話沒那麼緊。"


def relationship_case_model_secondary_dynamics(
    *,
    context: dict[str, str],
    thesis: dict[str, Any],
    timing_guidance: dict[str, Any],
) -> list[dict[str, Any]]:
    primary_key = str(thesis.get("centralDynamicKey") or "")
    candidates = [item for item in thesis.get("candidateDynamics") or [] if isinstance(item, dict)]
    secondary_candidates = [
        item
        for item in candidates
        if str(item.get("dynamicKey") or "") and str(item.get("dynamicKey") or "") != primary_key
    ]
    secondary: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for candidate in secondary_candidates:
        key = str(candidate.get("dynamicKey") or "")
        if key in seen_keys:
            continue
        seen_keys.add(key)
        secondary.append(
            relationship_case_model_secondary_dynamic(
                primary_key=primary_key,
                candidate=candidate,
                context=context,
                timing_guidance=timing_guidance,
            )
        )
    return secondary[:3]


def relationship_case_model_pair_timing_modifier(
    *,
    timing_posture: dict[str, Any],
    primary_key: str,
    secondary_key: str,
) -> str:
    timing_key = str(timing_posture.get("key") or "")
    if timing_key == "avoid_push":
        return "放到時機上，這組動力不適合加重關係題目；先讓壓力下降，再看是否有自然延續。"
    if timing_key == "low_pressure_message":
        return "放到時機上，只能用短、輕、低要求的方式測承接度，不能一次談完整關係。"
    if timing_key == "observe_for_soft_window":
        return "放到時機上，先等互動出現比較柔和的縫隙，再決定要不要靠近。"
    if timing_key == "observe_only":
        return "放到時機上，現在先看互動是否自行變穩，不用單次回覆判斷整段關係。"
    if timing_key == "not_calculated":
        return "放到時機上，資料不足時更要保守，回到現實行動和聯絡界線驗證。"
    return f"放到時機上，要同時看「{primary_key}」和「{secondary_key}」是否被現實互動接住。"


def relationship_case_model_pair_contact_modifier(contact_posture: dict[str, Any]) -> str:
    contact_key = str(contact_posture.get("key") or "")
    if contact_key == "boundary_first":
        return "聯絡狀態上，界線優先；沒有被允許的通道時，不把星盤牽動寫成行動理由。"
    if contact_key == "observe_channel":
        return "聯絡狀態上，先看自然通道是否出現；沒有通道時，主動加碼會讓判讀失真。"
    if contact_key == "test_low_pressure":
        return "聯絡狀態上，偶爾回覆只適合測壓力比較小的互動，還不能直接當成關係已經變穩。"
    if contact_key == "watch_initiation":
        return "聯絡狀態上，重點是他是否也會主動延續，而不是只被動接住你的題目。"
    if contact_key == "protect_shared_space":
        return "聯絡狀態上，共同場域要先保護日常承受度，不把相遇變成關係攤牌。"
    return str(contact_posture.get("implication") or "聯絡狀態要先決定行動大小。")


def relationship_case_model_composed_pair_grammar(
    *,
    primary_dynamic: dict[str, Any],
    secondary: dict[str, Any],
) -> dict[str, Any]:
    primary_key = str(primary_dynamic.get("key") or "unknown")
    secondary_key = str(secondary.get("key") or "unknown")
    role = str(secondary.get("role") or "softener")
    primary_label = str(primary_dynamic.get("label") or "主要互動模式")
    secondary_label = str(secondary.get("label") or "另一個重要線索")
    role_bridge = {
        "amplifier": "會放大這條主線的感受和期待",
        "blocker": "是目前讓這條主線更難推進的阻力",
        "repairLever": "提供了一個比較可用的修復入口",
        "softener": "可以讓這條主線沒那麼緊繃",
        "timingActivator": "會讓這條主線在目前時機下更敏感",
    }.get(role, "會改變這條主線在現實互動裡的表現")
    does_not_mean = {
        "amplifier": "感受被放大，不代表關係已經往前，也不能用一次熱絡替後續行動下結論。",
        "blocker": "出現阻力不等於完全沒有感覺，但也不能只靠好感忽略現實卡點。",
        "repairLever": "找到修復入口不代表問題已經解決，仍要看對方是否願意一起回應。",
        "softener": "氣氛變柔和不等於關係已經穩定，也不代表你需要無限等待。",
        "timingActivator": "時機敏感不等於永遠沒有機會，只代表現在不適合把動作做大。",
    }.get(role, "這不代表可以用單一反應或單次訊息替整段關係下結論。")
    repair_implication = {
        "amplifier": f"先把「{secondary_label}」帶來的期待放慢，再看「{primary_label}」有沒有被持續行動接住。",
        "blocker": f"先降低「{secondary_label}」造成的阻力，再處理「{primary_label}」真正卡住的地方。",
        "repairLever": f"先從「{secondary_label}」能做到的小修復開始，但每次只處理「{primary_label}」裡的一件事。",
        "softener": f"先用「{secondary_label}」保留台階，讓「{primary_label}」可以在壓力較小的位置被重新理解。",
        "timingActivator": f"先等「{secondary_label}」帶來的敏感度下降，再決定要不要碰「{primary_label}」這條主線。",
    }.get(role, "先把下一步縮成一件看得到回應的小事，不把整段關係壓在同一次對話。")
    action_boundary = {
        "amplifier": "有反應只能先當作一次訊號；沒有後續行動時，不要因此連續加碼。",
        "blocker": "只要下一步需要對方立刻回答、安撫或承諾，就先把動作縮小。",
        "repairLever": "一次只做一件對方容易回應的小事；說完就停，不把修復變成追問。",
        "softener": "保留台階不等於無限等待；如果一直只有你在維持互動，就先停下來。",
        "timingActivator": "現在只適合做能自然停下的小動作；需要立刻得到答案的事先不要做。",
    }.get(role, "如果下一步需要對方立刻表態，就先把動作再縮小。")
    interaction_effect = normalize_zh_text(secondary.get("interactionEffect") or "")
    why_it_matters = normalize_zh_text(secondary.get("whyItMatters") or primary_dynamic.get("readerMeaning") or "")
    return {
        "grammarId": f"pair-composed-{primary_key}-{secondary_key}-{role}-v1",
        "dynamicInteraction": normalize_zh_text(
            f"「{primary_label}」是主線；「{secondary_label}」{role_bridge}。{interaction_effect}"
        ),
        "whatThisMeans": why_it_matters,
        "whatItDoesNotMean": does_not_mean,
        "repairImplication": repair_implication,
        "actionBoundary": action_boundary,
        "phrasesToAvoid": ["單一反應就是答案", "只要照做就會成功", "這一定代表關係會往前"],
    }


def relationship_case_model_dynamic_interaction_plan(
    *,
    context: dict[str, str],
    primary_dynamic: dict[str, Any],
    secondary_dynamics: list[dict[str, Any]],
    timing_posture: dict[str, Any],
    contact_posture: dict[str, Any],
) -> dict[str, Any]:
    secondary = secondary_dynamics[0] if secondary_dynamics else {}
    primary_key = str(primary_dynamic.get("key") or "")
    secondary_key = str(secondary.get("key") or "")
    role = str(secondary.get("role") or "")
    grammar = RELATIONSHIP_CASE_MODEL_PAIR_GRAMMAR.get((primary_key, secondary_key))
    grammar_mode = "explicit" if grammar else "composed"
    if not grammar:
        grammar = relationship_case_model_composed_pair_grammar(
            primary_dynamic=primary_dynamic,
            secondary=secondary,
        )
    evidence_ids = unique(
        [
            *[str(item) for item in primary_dynamic.get("evidenceIds") or [] if item],
            *[str(item) for item in secondary.get("evidenceIds") or [] if item],
        ]
    )
    return {
        "version": "dynamic-interaction-plan-v1",
        "grammarId": str(grammar.get("grammarId") or ""),
        "grammarMode": grammar_mode,
        "matchedGrammar": True,
        "primaryKey": primary_key,
        "secondaryKey": secondary_key,
        "secondaryRole": role,
        "questionKey": context.get("main_question", ""),
        "dynamicInteraction": normalize_zh_text(grammar.get("dynamicInteraction") or ""),
        "whatThisMeans": normalize_zh_text(grammar.get("whatThisMeans") or ""),
        "whatItDoesNotMean": normalize_zh_text(grammar.get("whatItDoesNotMean") or ""),
        "repairImplication": normalize_zh_text(grammar.get("repairImplication") or ""),
        "actionBoundary": normalize_zh_text(grammar.get("actionBoundary") or ""),
        "timingModifier": normalize_zh_text(
            relationship_case_model_pair_timing_modifier(
                timing_posture=timing_posture,
                primary_key=primary_key,
                secondary_key=secondary_key,
            )
        ),
        "contactModifier": normalize_zh_text(relationship_case_model_pair_contact_modifier(contact_posture)),
        "phrasesToAvoid": [normalize_zh_text(item) for item in grammar.get("phrasesToAvoid") or [] if item],
        "evidenceIds": evidence_ids,
    }


def relationship_case_model_emotional_blocker(
    *,
    primary_dynamic: dict[str, Any],
    secondary_dynamics: list[dict[str, Any]],
    thesis: dict[str, Any],
) -> dict[str, Any]:
    blocker = next((item for item in secondary_dynamics if item.get("role") in {"blocker", "timingActivator"}), {})
    tension = thesis.get("dominantTension") if isinstance(thesis.get("dominantTension"), dict) else {}
    key = str(blocker.get("key") or primary_dynamic.get("key") or "fallback")
    source = blocker or primary_dynamic
    return {
        "key": key,
        "label": source.get("label") or "目前阻力",
        "summary": normalize_zh_text(
            blocker.get("interactionEffect")
            or tension.get("currentPattern")
            or "現在比較大的阻力，是互動一變重就容易失去自然承接。"
        ),
        "evidenceIds": unique([str(item) for item in source.get("evidenceIds") or [] if item]),
    }


def relationship_case_model_repair_lever(
    *,
    primary_dynamic: dict[str, Any],
    secondary_dynamics: list[dict[str, Any]],
    thesis: dict[str, Any],
) -> dict[str, Any]:
    repair = next((item for item in secondary_dynamics if item.get("role") == "repairLever"), {})
    boundary = thesis.get("decisionBoundary") if isinstance(thesis.get("decisionBoundary"), dict) else {}
    tension = thesis.get("dominantTension") if isinstance(thesis.get("dominantTension"), dict) else {}
    source = repair or primary_dynamic
    return {
        "key": str(source.get("key") or primary_dynamic.get("key") or "fallback"),
        "label": source.get("label") or "修復入口",
        "summary": normalize_zh_text(
            repair.get("interactionEffect")
            or tension.get("desiredShift")
            or boundary.get("continueWhen")
            or "把下一步縮小到對方能自然接住的位置。"
        ),
        "evidenceIds": unique([str(item) for item in source.get("evidenceIds") or [] if item]),
    }


def relationship_case_model_contact_posture(
    *,
    context: dict[str, str],
    contact_policy: dict[str, Any],
    action_guidance: dict[str, Any],
) -> dict[str, Any]:
    status = context.get("contact_status", "")
    label = str(contact_policy.get("statusLabel") or CONTACT_STATUS_LABELS.get(status, status or "聯絡狀態未提供"))
    posture_by_status = {
        "blocked": ("boundary_first", "先尊重聯絡界線，不把任何繞路接觸寫成建議。"),
        "no-contact": ("observe_channel", "先看是否出現自然小開口，沒有小開口時不連續加碼。"),
        "occasional-contact": ("test_low_pressure", "可以看壓力比較小的互動是否被接住，但偶爾回覆還不能直接當成關係已經變穩。"),
        "still-in-contact": ("watch_initiation", "重點是對方是否也會主動延續，而不是只被動回你。"),
        "living-or-working-together": ("protect_shared_space", "共同場域先保護日常承受度，不把場域變成攤牌現場。"),
    }
    key, implication = posture_by_status.get(status, ("contextual", "依照現有互動承受度決定行動大小。"))
    return {
        "key": key,
        "statusKey": status,
        "label": label,
        "implication": normalize_zh_text(action_guidance.get("nextMove") or implication),
        "evidenceClusterKeys": unique(["contactSituationPolicy", "actionGuidance"]),
    }


def relationship_case_model_timing_posture(timing_guidance: dict[str, Any]) -> dict[str, Any]:
    action = str(timing_guidance.get("recommendedAction") or "not_calculated")
    label = str(timing_guidance.get("recommendedActionLabel") or timing_guidance.get("headline") or action)
    interpretation_by_action = {
        "avoid_push": "時機不適合加重關係題目，重點是讓壓力下降，避免連續推進。",
        "low_pressure_message": "時機可以容納很小、低要求、可退場的訊息，但不適合一次談完整關係。",
        "observe_for_soft_window": "現在先觀察柔和訊號，等互動比較能承接時再決定是否靠近。",
        "observe_only": "目前以觀察為主，不把單次回覆當成趨勢。",
        "not_calculated": "時機資料不足時，行動要保守，回到現實互動驗證。",
    }
    return {
        "key": action,
        "label": label,
        "interpretation": normalize_zh_text(timing_guidance.get("body") or interpretation_by_action.get(action, "先用互動承受度決定行動大小。")),
        "nextMove": normalize_zh_text(timing_guidance.get("nextMove") or interpretation_by_action.get(action, "")),
        "evidenceClusterKeys": unique(["timingGuidance", "timingContactReducer", "timingWindowBand"]),
    }


def relationship_case_model_risk_posture(context: dict[str, str]) -> dict[str, str]:
    risk = context.get("emotional_risk", "")
    copy_by_risk = {
        "self-blaming": ("self_blame_guard", "不要把整段關係的卡住都解讀成你做錯；重點是找出可調整的互動環節。"),
        "anxious": ("anxiety_guard", "焦慮會放大細節，判讀要看連續互動，不只看單次回覆。"),
        "desperate": ("stability_first", "情緒很急時，先穩住自己，再決定是否行動。"),
        "unsafe-or-overwhelmed": ("safety_first", "安全感和界線優先於修復，不把占星牽動當成越界理由。"),
        "calm": ("standard", "情緒相對穩定時，可以更清楚分辨現實回應和想像。"),
    }
    key, guidance = copy_by_risk.get(risk, ("standard", "先把判讀放回可觀察互動，避免用單次反應下結論。"))
    return {
        "key": key,
        "riskKey": risk,
        "label": EMOTIONAL_RISK_LABELS.get(risk, risk or "情緒狀態未提供"),
        "guidance": guidance,
    }


def relationship_case_model_answer_strategy(
    *,
    context: dict[str, str],
    question_label: str,
    normal_user_answer: dict[str, Any],
    answer_guidance: dict[str, Any],
    primary_dynamic: dict[str, Any],
    secondary_dynamics: list[dict[str, Any]],
) -> dict[str, Any]:
    secondary = secondary_dynamics[0] if secondary_dynamics else {}
    direct = str(normal_user_answer.get("directAnswer") or answer_guidance.get("shortAnswer") or primary_dynamic.get("centralThesis") or "")
    return {
        "questionKey": context.get("main_question", ""),
        "questionLabel": question_label,
        "headline": str(normal_user_answer.get("headline") or (answer_guidance.get("readableInterpretation") or {}).get("headline") or "把答案放回互動條件"),
        "directAnswer": direct,
        "principle": normalize_zh_text(
            f"先用「{primary_dynamic.get('label') or '關係主軸'}」回答核心問題，再用「{secondary.get('label') or '另一條線索'}」判斷現實互動要放大、放慢還是改用修復位置。"
        ),
        "watchFor": [str(item) for item in normal_user_answer.get("whatToWatch") or [] if item],
        "stopLine": str(normal_user_answer.get("stopLine") or ""),
    }


def relationship_case_model_section_plans(
    *,
    primary_dynamic: dict[str, Any],
    secondary_dynamics: list[dict[str, Any]],
    emotional_blocker: dict[str, Any],
    repair_lever: dict[str, Any],
    contact_posture: dict[str, Any],
    timing_posture: dict[str, Any],
    answer_strategy: dict[str, Any],
    dynamic_interaction_plan: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    secondary = secondary_dynamics[0] if secondary_dynamics else {}
    base_keys = ["relationshipCaseModel", "relationshipThesis"]
    return {
        "chart-positioning": {
            "interpretiveJob": "把兩個人的本命需求讀成後面所有關係判斷的翻譯表。",
            "caseBridge": primary_dynamic.get("readerMeaning") or "",
            "mustUse": [primary_dynamic.get("label") or ""],
            "avoid": ["不要在星盤定位頁直接下復合或分手結論。"],
            "evidenceClusterKeys": unique([*base_keys, "relationshipProfiles"]),
        },
        "relationship-fit": {
            "interpretiveJob": "說明主線和另一條線索怎麼一起形成關係循環。",
            "caseBridge": dynamic_interaction_plan.get("dynamicInteraction") or secondary.get("interactionEffect") or primary_dynamic.get("readerMeaning") or "",
            "mustUse": [primary_dynamic.get("label") or "", secondary.get("label") or ""],
            "avoid": ["不要只寫合不合，要寫出循環如何被放大或修復。"],
            "evidenceClusterKeys": unique([*base_keys, "relationshipArchetype", "attractionDynamics", "conflictDynamics", "growthDynamics"]),
        },
        "core-answer": {
            "interpretiveJob": "直接回答讀者問題，但把答案綁回可觀察條件。",
            "caseBridge": dynamic_interaction_plan.get("whatThisMeans") or answer_strategy.get("principle") or "",
            "mustUse": [answer_strategy.get("directAnswer") or "", emotional_blocker.get("summary") or ""],
            "avoid": ["不要替對方讀心，不用單次回覆當結論。"],
            "evidenceClusterKeys": unique([*base_keys, "answerGuidance", "partnerNeeds", "contactSituationPolicy"]),
        },
        "timing-reading": {
            "interpretiveJob": "把關係動力翻成現在適合的行動尺度。",
            "caseBridge": dynamic_interaction_plan.get("timingModifier") or timing_posture.get("interpretation") or "",
            "mustUse": [timing_posture.get("label") or "", contact_posture.get("label") or ""],
            "avoid": ["不給精準成功日期，不把時機寫成保證。"],
            "evidenceClusterKeys": unique([*base_keys, "timingGuidance", "timingContactReducer", "timingWindowBand"]),
        },
        "action-direction": {
            "interpretiveJob": "只給下一步和停損界線，讓行動服從主線與另一條線索。",
            "caseBridge": dynamic_interaction_plan.get("repairImplication") or secondary.get("interactionEffect") or repair_lever.get("summary") or contact_posture.get("implication") or "",
            "mustUse": [repair_lever.get("summary") or "", contact_posture.get("implication") or ""],
            "avoid": ["不要把感覺強度寫成行動許可。"],
            "evidenceClusterKeys": unique([*base_keys, "actionGuidance", "fightLandmines", "survivalGuide"]),
        },
    }


def relationship_case_model_validation(model: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    primary = model.get("primaryDynamic") if isinstance(model.get("primaryDynamic"), dict) else {}
    secondary = [item for item in model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    if not primary.get("key") or not primary.get("evidenceIds"):
        failures.append("primaryDynamicRequiresEvidence")
    if not secondary:
        failures.append("requiresAtLeastOneSecondaryDynamic")
    for item in secondary:
        if item.get("role") not in RELATIONSHIP_CASE_MODEL_DYNAMIC_ROLES:
            failures.append(f"invalidSecondaryRole:{item.get('role')}")
        if not item.get("evidenceIds"):
            failures.append(f"secondaryDynamicMissingEvidence:{item.get('key')}")
        if not item.get("interactionEffect") or not item.get("whyItMatters"):
            failures.append(f"secondaryDynamicMissingInterpretation:{item.get('key')}")
    for field in ("emotionalBlocker", "repairLever", "contactPosture", "timingPosture", "riskPosture", "answerStrategy", "dynamicInteractionPlan"):
        value = model.get(field)
        if not isinstance(value, dict) or not value:
            failures.append(f"missing:{field}")
    interaction_plan = model.get("dynamicInteractionPlan") if isinstance(model.get("dynamicInteractionPlan"), dict) else {}
    for field in ("dynamicInteraction", "whatThisMeans", "whatItDoesNotMean", "repairImplication", "actionBoundary", "timingModifier", "contactModifier"):
        if not interaction_plan.get(field):
            failures.append(f"dynamicInteractionPlanMissing:{field}")
    if not interaction_plan.get("evidenceIds"):
        failures.append("dynamicInteractionPlanMissingEvidence")
    section_plans = model.get("sectionPlans") if isinstance(model.get("sectionPlans"), dict) else {}
    if set(section_plans) != set(RELATIONSHIP_CASE_MODEL_SECTION_IDS):
        failures.append("sectionPlansMismatch")
    for section_id in RELATIONSHIP_CASE_MODEL_SECTION_IDS:
        plan = section_plans.get(section_id) or {}
        if not plan.get("interpretiveJob") or not plan.get("caseBridge"):
            failures.append(f"thinSectionPlan:{section_id}")
        keys = set(plan.get("evidenceClusterKeys") or [])
        if "relationshipCaseModel" not in keys or "relationshipThesis" not in keys:
            failures.append(f"sectionPlanMissingCaseEvidence:{section_id}")
    return {
        "passed": not failures,
        "failures": unique(failures),
    }


def relationship_case_model_payload(
    *,
    context: dict[str, str],
    question_label: str,
    relationship_thesis: dict[str, Any],
    answer_guidance: dict[str, Any],
    normal_user_answer: dict[str, Any],
    timing_guidance: dict[str, Any],
    action_guidance: dict[str, Any],
    contact_policy: dict[str, Any],
    relationship_theme: dict[str, Any],
) -> dict[str, Any]:
    primary_dynamic = relationship_case_model_primary_dynamic(relationship_thesis)
    secondary_dynamics = relationship_case_model_secondary_dynamics(
        context=context,
        thesis=relationship_thesis,
        timing_guidance=timing_guidance,
    )
    emotional_blocker = relationship_case_model_emotional_blocker(
        primary_dynamic=primary_dynamic,
        secondary_dynamics=secondary_dynamics,
        thesis=relationship_thesis,
    )
    repair_lever = relationship_case_model_repair_lever(
        primary_dynamic=primary_dynamic,
        secondary_dynamics=secondary_dynamics,
        thesis=relationship_thesis,
    )
    contact_posture = relationship_case_model_contact_posture(
        context=context,
        contact_policy=contact_policy,
        action_guidance=action_guidance,
    )
    timing_posture = relationship_case_model_timing_posture(timing_guidance)
    risk_posture = relationship_case_model_risk_posture(context)
    dynamic_interaction_plan = relationship_case_model_dynamic_interaction_plan(
        context=context,
        primary_dynamic=primary_dynamic,
        secondary_dynamics=secondary_dynamics,
        timing_posture=timing_posture,
        contact_posture=contact_posture,
    )
    answer_strategy = relationship_case_model_answer_strategy(
        context=context,
        question_label=question_label,
        normal_user_answer=normal_user_answer,
        answer_guidance=answer_guidance,
        primary_dynamic=primary_dynamic,
        secondary_dynamics=secondary_dynamics,
    )
    section_plans = relationship_case_model_section_plans(
        primary_dynamic=primary_dynamic,
        secondary_dynamics=secondary_dynamics,
        emotional_blocker=emotional_blocker,
        repair_lever=repair_lever,
        contact_posture=contact_posture,
        timing_posture=timing_posture,
        answer_strategy=answer_strategy,
        dynamic_interaction_plan=dynamic_interaction_plan,
    )
    model = {
        "version": RELATIONSHIP_CASE_MODEL_VERSION,
        "questionKey": context.get("main_question", ""),
        "stageKey": context.get("relationship_stage", ""),
        "sourceThesisVersion": relationship_thesis.get("version") or "",
        "primaryDynamic": primary_dynamic,
        "secondaryDynamics": secondary_dynamics,
        "centralLoop": {
            "summary": normalize_zh_text(
                f"{primary_dynamic.get('readerMeaning') or ''}"
                f"{' ' + secondary_dynamics[0].get('interactionEffect') if secondary_dynamics else ''}"
            ),
            "steps": relationship_thesis.get("interactionLoop") or {},
            "evidenceIds": unique([str(item) for item in primary_dynamic.get("evidenceIds") or [] if item]),
        },
        "emotionalBlocker": emotional_blocker,
        "repairLever": repair_lever,
        "contactPosture": contact_posture,
        "timingPosture": timing_posture,
        "riskPosture": risk_posture,
        "answerStrategy": answer_strategy,
        "dynamicInteractionPlan": dynamic_interaction_plan,
        "evidenceMap": [
            {
                "caseField": "primaryDynamic",
                "source": "relationshipThesis.candidateDynamics[selectedCandidateId]",
                "evidenceIds": primary_dynamic.get("evidenceIds") or [],
            },
            {
                "caseField": "secondaryDynamics",
                "source": "relationshipThesis.candidateDynamics",
                "evidenceIds": unique([evidence_id for item in secondary_dynamics for evidence_id in item.get("evidenceIds") or []]),
            },
            {
                "caseField": "timingPosture",
                "source": "timingGuidance",
                "evidenceClusterKeys": timing_posture.get("evidenceClusterKeys") or [],
            },
            {
                "caseField": "contactPosture",
                "source": "contactSituationPolicy + actionGuidance",
                "evidenceClusterKeys": contact_posture.get("evidenceClusterKeys") or [],
            },
            {
                "caseField": "dynamicInteractionPlan",
                "source": "relationshipCaseModel.pairGrammar + timing/contact posture",
                "evidenceIds": dynamic_interaction_plan.get("evidenceIds") or [],
            },
        ],
        "sectionPlans": section_plans,
        "sourceClaimIds": unique([
            *[str(item) for item in relationship_thesis.get("sourceClaimIds") or [] if item],
            *[str(item) for item in answer_guidance.get("sourceClaimIds") or [] if item],
        ]),
        "methodClaimIds": unique([
            *[str(item) for item in relationship_thesis.get("methodClaimIds") or [] if item],
            *[str(item) for item in relationship_theme.get("methodClaimIds") or [] if item],
            *[str(item) for item in timing_guidance.get("methodClaimIds") or [] if item],
            *[str(item) for item in action_guidance.get("methodClaimIds") or [] if item],
        ]),
        "evidenceClusterKeys": unique([
            "relationshipCaseModel",
            "relationshipThesis",
            *[str(item) for item in relationship_thesis.get("evidenceClusterKeys") or [] if item],
            *[str(item) for item in contact_posture.get("evidenceClusterKeys") or [] if item],
            *[str(item) for item in timing_posture.get("evidenceClusterKeys") or [] if item],
        ]),
    }
    model["validation"] = relationship_case_model_validation(model)
    return model


def relationship_insight_source_claim_ids(items: list[dict[str, Any]]) -> list[str]:
    claim_ids: list[str] = []
    for item in items:
        claim_ids.extend(str(claim_id) for claim_id in item.get("sourceClaimIds") or [] if claim_id)
        claim_ids.extend(str(claim_id) for claim_id in item.get("claimIds") or [] if claim_id)
    return unique(claim_ids)


def relationship_insight_method_claim_ids(items: list[dict[str, Any]]) -> list[str]:
    claim_ids: list[str] = []
    for item in items:
        claim_ids.extend(str(claim_id) for claim_id in item.get("methodClaimIds") or [] if claim_id)
    return unique([*RELATIONSHIP_INSIGHT_METHOD_CLAIM_IDS, *claim_ids])


def aspect_config_for_pair_key(pair_key: str) -> dict[str, Any]:
    for config in ASPECT_FUNCTION_COMBINATION_CONFIG.values():
        if str(config.get("pairKey") or "") == pair_key:
            return config
    for config in MERCURY_CONTACT_FUNCTION_CONFIG.values():
        if str(config.get("pairKey") or "") == pair_key:
            return config
    return {}


def aspect_detail_key(item: dict[str, Any]) -> str:
    return "|".join(
        [
            str(item.get("pairKey") or ""),
            str(item.get("personAPoint") or ""),
            str(item.get("personBPoint") or ""),
            str(item.get("aspect") or ""),
            str(item.get("orb") or ""),
        ]
    )


def relationship_aspect_details(evidence_clusters: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cluster = evidence_clusters.get("aspectFunctionCombination") or {}
    selected = [item for item in cluster.get("selectedCombinations") or [] if isinstance(item, dict)]
    detected = [item for item in cluster.get("detectedPairDetails") or [] if isinstance(item, dict)]
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*selected, *detected]:
        pair_key = str(item.get("pairKey") or "")
        if not pair_key:
            continue
        key = aspect_detail_key(item)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def display_sign_label(sign_label: str) -> str:
    return "牡羊" if sign_label == "白羊" else sign_label


def pair_key_label(pair_key: str) -> str:
    parts = [part for part in str(pair_key or "").split("-") if part]
    if not parts:
        return "關鍵相位"
    return "-".join(POINT_LABELS.get(part, part) for part in parts)


def format_pair_key_list(pair_keys: list[str]) -> str:
    return "、".join(pair_key_label(pair_key) for pair_key in pair_keys if pair_key)


def relationship_aspect_public_item(item: dict[str, Any], *, role: str, index: int) -> dict[str, Any]:
    pair_key = str(item.get("pairKey") or "")
    source = str(item.get("aspectSource") or item.get("source") or "")
    config = ASPECT_FUNCTION_COMBINATION_CONFIG.get(source) or aspect_config_for_pair_key(pair_key)
    contact_type = str(item.get("contactType") or "")
    contact_text = str(item.get("contactText") or config.get(contact_type) or "")
    aspect = str(item.get("aspect") or "")
    aspect_label = str(item.get("aspectLabel") or ASPECT_LABELS.get(aspect, aspect or "相位"))
    point_a = str(item.get("personAPoint") or "")
    point_b = str(item.get("personBPoint") or "")
    source_claim_id = str(item.get("sourceClaimId") or config.get("sourceClaimId") or "")
    method_claim_ids = [
        str(claim_id)
        for claim_id in (item.get("methodClaimIds") or PAIR_FAMILY_METHOD_CLAIM_IDS.get(source, []))
        if claim_id
    ]
    title = str(config.get("label") or item.get("label") or pair_key or "關鍵相位")
    technical = str(item.get("technical") or "")
    if not technical and point_a and point_b:
        pseudo_aspect = {
            "person_a_point": point_a,
            "person_b_point": point_b,
            "aspect": aspect,
            "orb": item.get("orb"),
            "applying": bool(item.get("applying")),
        }
        technical = western_aspect_sentence(pseudo_aspect)
    meaning = contact_text or str(item.get("functionSynthesis") or "這是本次合盤裡需要優先閱讀的互動訊號。")
    return {
        "id": f"{role}-{index + 1}",
        "pairKey": pair_key,
        "title": title,
        "personAPoint": point_a,
        "personBPoint": point_b,
        "aspect": aspect,
        "aspectLabel": aspect_label,
        "orb": item.get("orb"),
        "contactType": contact_type or "other",
        "strength": round(float(item.get("strength") or 0), 3),
        "technical": technical,
        "meaning": western_public_copy(meaning),
        "everydaySignal": relationship_aspect_everyday_signal(pair_key, role, contact_type),
        "advice": relationship_aspect_advice(pair_key, role, contact_type),
        "doesNotProve": relationship_aspect_does_not_prove(role),
        "source": source or RELATIONSHIP_INSIGHT_SOURCE,
        "sourceClaimIds": unique([source_claim_id, *[str(claim_id) for claim_id in item.get("claimIds") or [] if claim_id]]),
        "methodClaimIds": method_claim_ids,
        "evidenceClusterKeys": ["aspectFunctionCombination", role],
    }


ATTRACTION_EVERYDAY_SIGNAL_BY_PAIR = {
    "Venus-Mars": "一方的好感和另一方的行動感會互相點燃，容易有想靠近、想試探反應的火花。",
    "Sun-Moon": "一方的存在感會碰到另一方的情緒節奏，所以容易有熟悉、被理解或被牽動的感覺。",
    "Moon-Moon": "兩個人的情緒節奏容易互相感應，舒服時很貼近，不安時也容易一起被帶動。",
    "Moon-Venus": "情緒需求和被珍惜的感覺容易接上，被對方溫柔對待時會特別有感。",
    "Sun-Venus": "被看見、被欣賞的感覺容易被啟動，所以好感會先從在意和吸引開始。",
    "Sun-Mars": "一方的存在感會激起另一方想靠近或採取行動的衝動，火花來得快，也容易急著測反應。",
    "Venus-Venus": "喜歡的方式比較容易互相理解，舒服的陪伴和美感共鳴會拉近距離。",
}

CONFLICT_EVERYDAY_SIGNAL_BY_PAIR = {
    "Mercury-Mars": "一想把話說清楚，就容易變成辯論、反駁或語氣太快。",
    "Mars-Mars": "兩個人的行動速度一不合，就容易變成誰要照誰的節奏。",
    "Moon-Mars": "情緒被點到時，反應會很快，容易從在乎變成刺激。",
    "Mercury-Saturn": "一想把話講清楚，就容易碰到標準、責任或被糾正的壓力，對話會變慢。",
    "Moon-Saturn": "情緒需要被接住時，另一方可能先冷靜、保留或拉開距離，讓安撫變難。",
    "Venus-Saturn": "想確認被珍惜時，容易碰到現實限制、承諾壓力或對方保留，甜的感覺會變重。",
    "Mars-Saturn": "一方想推進，另一方像踩剎車；速度差會讓行動卡住，甚至像被擋下來。",
    "Sun-Saturn": "想被肯定或自然做自己時，容易碰到標準、責任或被審核的感覺，靠近會變拘謹。",
}

GROWTH_EVERYDAY_SIGNAL_BY_PAIR = {
    "Mercury-Jupiter": "修復點在於把話說開但不誇大；用更大的視角談一件具體小事。",
    "Sun-Saturn": "修復點在於把欣賞落成可做到的支持，不用一次要求完整承諾。",
    "Moon-Saturn": "修復點在於穩定安撫和固定回應，讓情緒不用每次都重新猜。",
    "Venus-Saturn": "修復點在於小而穩定的在意感；說到做到，比一次大表態更有用。",
    "Mars-Saturn": "修復點在於先約好節奏，讓行動不再一個催、一個退。",
}


def relationship_aspect_everyday_signal(pair_key: str, role: str, contact_type: str) -> str:
    if role == "attractionDynamics":
        return ATTRACTION_EVERYDAY_SIGNAL_BY_PAIR.get(
            pair_key,
            "吸引不是只有想像中的好感，而是互動裡真的有會被彼此帶動的地方。",
        )
    if role == "conflictDynamics":
        return CONFLICT_EVERYDAY_SIGNAL_BY_PAIR.get(
            pair_key,
            "衝突不是單純誰錯，而是某個互動按鈕容易被按下。",
        )
    if role == "growthDynamics":
        return GROWTH_EVERYDAY_SIGNAL_BY_PAIR.get(
            pair_key,
            "這個線索比較像關係中的成長題，而不是單純合不合。",
        )
    return "這是本次合盤中可被日常互動看見的訊號。"


def relationship_aspect_advice(pair_key: str, role: str, contact_type: str) -> str:
    if role == "attractionDynamics":
        return "把吸引力當成入口，不要直接當成承諾；先看對方是否能穩定、自然地回應。"
    if role == "conflictDynamics":
        if pair_key.startswith("Mercury") or "Mercury" in pair_key:
            return "敏感話題一次只講一件事，不用長文、糾正或逼對方立刻承認。"
        if "Saturn" in pair_key:
            return "談承諾前先降低責任壓力，用可做到的小行動取代逼答案。"
        return "先停在具體事件，不把焦急、試探或輸贏感放進對話。"
    if role == "growthDynamics":
        if "Saturn" in pair_key:
            return "把期待拆成小而可執行的責任，不用一次檢查整段關係。"
        return "用支持、鼓勵和共同目標打開互動，不用樂觀蓋過現實問題。"
    return "先把這個訊號放回實際互動裡觀察。"


def relationship_aspect_does_not_prove(role: str) -> str:
    if role == "attractionDynamics":
        return "吸引相位不能證明承諾、復合或對方一定還愛。"
    if role == "conflictDynamics":
        return "衝突相位不能證明關係沒有機會，也不能用來指責單方。"
    if role == "growthDynamics":
        return "成長相位不是命定任務，也不能保證等待就會變好。"
    return "單一相位不能替整段關係下結論。"


def relationship_dynamics_block(
    *,
    key: str,
    label: str,
    headline: str,
    evidence_clusters: dict[str, dict[str, Any]],
    pair_keys: set[str],
    include_predicate: Any | None = None,
    limit: int = 4,
) -> dict[str, Any]:
    details = relationship_aspect_details(evidence_clusters)
    selected: list[dict[str, Any]] = []
    for item in details:
        pair_key = str(item.get("pairKey") or "")
        contact_type = str(item.get("contactType") or "")
        if pair_key not in pair_keys and not (include_predicate and include_predicate(item)):
            continue
        if include_predicate and not include_predicate(item) and pair_key not in pair_keys:
            continue
        if key == "growthDynamics" and pair_key in {"Sun-Saturn", "Moon-Saturn", "Venus-Saturn", "Mars-Saturn"} and contact_type != "soft":
            continue
        selected.append(relationship_aspect_public_item(item, role=key, index=len(selected)))
        if len(selected) >= limit:
            break
    gaps: list[dict[str, Any]] = []
    if key == "growthDynamics":
        available_pairs = {item.get("pairKey") for item in selected}
        if not any("Jupiter" in str(pair) for pair in available_pairs):
            gaps.append(
                {
                    "label": "Jupiter 成長相位",
                    "status": "not_selected",
                    "reason": "本次合盤沒有可用的 Jupiter 成長相位進入優先證據，不能硬寫成命中貴人或幸運加持。",
                }
            )
        gaps.extend(
            [
                {
                    "label": "Chiron 療癒相位",
                    "status": "blocked",
                    "reason": "目前計算與 source-backed runtime claims 尚未開放 Chiron 合盤 selector。",
                },
                {
                    "label": "North Node 業力方向",
                    "status": "blocked",
                    "reason": "目前計算與 source-backed runtime claims 尚未開放 North Node 合盤 selector。",
                },
            ]
        )
    summary = (
        f"{label}選出 {len(selected)} 個可用訊號；主訊號是「{selected[0]['title']}」。"
        if selected
        else f"{label}目前沒有足夠可展示的相位；此區只保留方法邊界。"
    )
    return {
        "version": "relationship-dynamics-v1",
        "key": key,
        "label": label,
        "headline": headline,
        "summary": summary,
        "items": selected,
        "gaps": gaps,
        "source": RELATIONSHIP_INSIGHT_SOURCE,
        "sourceClaimIds": relationship_insight_source_claim_ids(selected),
        "methodClaimIds": relationship_insight_method_claim_ids(selected),
        "evidenceClusterKeys": ["aspectFunctionCombination"],
        "doesNotProve": relationship_aspect_does_not_prove(key),
    }


def relationship_archetype_contact_matches(
    item: dict[str, Any],
    *,
    hard_only: bool = False,
    supportive_only: bool = False,
) -> bool:
    contact_type = str(item.get("contactType") or "")
    if hard_only:
        return contact_type in {"hard", "conjunction"}
    if supportive_only:
        return contact_type in {"soft", "conjunction"}
    return True


def relationship_archetype_pair_score(
    aspect_cluster: dict[str, Any],
    pair_keys: set[str],
    *,
    hard_only: bool = False,
    supportive_only: bool = False,
) -> float:
    selected_details = [item for item in aspect_cluster.get("selectedCombinations") or [] if isinstance(item, dict)]
    detected_details = [item for item in aspect_cluster.get("detectedPairDetails") or [] if isinstance(item, dict)]
    score = 0.0
    for item in selected_details:
        if str(item.get("pairKey") or "") in pair_keys and relationship_archetype_contact_matches(
            item,
            hard_only=hard_only,
            supportive_only=supportive_only,
        ):
            score += 1.2
    for item in detected_details:
        if str(item.get("pairKey") or "") in pair_keys and relationship_archetype_contact_matches(
            item,
            hard_only=hard_only,
            supportive_only=supportive_only,
        ):
            score += 0.2
    if not selected_details and not detected_details:
        selected_pairs = set(str(item) for item in aspect_cluster.get("selectedPairs") or [] if item)
        detected_pairs = set(str(item) for item in aspect_cluster.get("detectedPairs") or [] if item)
        score += len(selected_pairs.intersection(pair_keys)) * 1.0
        score += len((detected_pairs - selected_pairs).intersection(pair_keys)) * 0.25
    return round(score, 3)


def relationship_archetype_repeated_theme_entries(aspect_cluster: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [item for item in aspect_cluster.get("repeatedThemes") or [] if isinstance(item, dict)]
    seen = {str(item.get("themeKey") or "") for item in entries}
    dominant_key = str(aspect_cluster.get("dominantRepeatedThemeKey") or "")
    if dominant_key and dominant_key not in seen:
        entries.append({"themeKey": dominant_key, "count": 2, "selectedCount": 1})
        seen.add(dominant_key)
    for flag, theme_key in ARCHETYPE_REPEATED_THEME_FLAGS.items():
        if aspect_cluster.get(flag) and theme_key not in seen:
            entries.append({"themeKey": theme_key, "count": 2, "selectedCount": 0})
            seen.add(theme_key)
    return entries


def relationship_archetype_signal_profile(aspect_cluster: dict[str, Any]) -> dict[str, Any]:
    selected_pairs = set(str(item) for item in aspect_cluster.get("selectedPairs") or [] if item)
    detected_pairs = set(str(item) for item in aspect_cluster.get("detectedPairs") or [] if item)
    all_pairs = selected_pairs | detected_pairs
    selected_sources = set(str(item) for item in aspect_cluster.get("selectedSources") or [] if item)
    detected_sources = set(str(item) for item in aspect_cluster.get("detectedSources") or [] if item)
    dominant_theme_key = str(aspect_cluster.get("dominantRepeatedThemeKey") or "")

    attraction_score = relationship_archetype_pair_score(aspect_cluster, ATTRACTION_DYNAMICS_PAIRS)
    action_score = relationship_archetype_pair_score(aspect_cluster, ARCHETYPE_ACTION_CONFLICT_PAIRS, hard_only=True)
    pressure_score = relationship_archetype_pair_score(aspect_cluster, ARCHETYPE_SATURN_PRESSURE_PAIRS, hard_only=True)
    identity_score = relationship_archetype_pair_score(aspect_cluster, ARCHETYPE_IDENTITY_PAIRS)
    emotional_score = relationship_archetype_pair_score(aspect_cluster, ARCHETYPE_EMOTIONAL_SAFETY_PAIRS)
    communication_score = relationship_archetype_pair_score(aspect_cluster, ARCHETYPE_COMMUNICATION_PAIRS)
    jupiter_score = relationship_archetype_pair_score(aspect_cluster, ARCHETYPE_JUPITER_SUPPORT_PAIRS, supportive_only=True)
    outer_score = 3.0 if (
        aspect_cluster.get("hasRepeatedOuterIntensity")
        or "Outer-planet intensity" in all_pairs
        or "western-aspects-outer-planet-intensity-families" in selected_sources
        or "western-aspects-outer-planet-intensity-families" in detected_sources
    ) else 0.0
    friction_score = max(action_score, pressure_score)

    scores: dict[str, float] = {title: 0.0 for title in ARCHETYPE_TITLES}
    scores["前世因緣感型"] += outer_score * 3.0
    scores["命中貴人型"] += jupiter_score * 3.0
    scores["溝通修復型"] += communication_score * 0.8
    scores["彼此牽動型"] += identity_score * 1.8 + emotional_score * 0.3
    scores["靈魂伴侶型"] += emotional_score * 1.4 + identity_score * 0.7
    scores["磨合成長型"] += pressure_score * 1.5
    scores["歡喜冤家型"] += action_score * 1.6
    if attraction_score >= 2.4 and friction_score >= 1.4:
        scores["高吸引高摩擦型"] += attraction_score * 1.0 + friction_score * 1.1
    elif attraction_score >= 1.4:
        scores["自然吸引型"] += attraction_score * 1.45
    scores["慢熱安全感型"] += 1.0 + max(0.0, emotional_score - pressure_score - action_score) * 0.2

    for entry in relationship_archetype_repeated_theme_entries(aspect_cluster):
        theme_key = str(entry.get("themeKey") or "")
        title = ARCHETYPE_THEME_TO_TITLE.get(theme_key)
        if not title:
            continue
        weight = 2.0 + min(int(entry.get("count") or 0), 4) * 0.35 + int(entry.get("selectedCount") or 0) * 0.5
        if theme_key == dominant_theme_key:
            weight += 2.0
        if theme_key == "attraction_pursuit" and friction_score >= 1.4:
            scores["高吸引高摩擦型"] += weight * 0.9
            scores["自然吸引型"] += weight * 0.2
        else:
            scores[title] += weight

    if dominant_theme_key == "communication_repair":
        scores["歡喜冤家型"] -= 2.5
        scores["高吸引高摩擦型"] -= 2.0
    if dominant_theme_key == "identity_rhythm":
        scores["彼此牽動型"] += 4.0
        scores["高吸引高摩擦型"] -= 2.0
        scores["歡喜冤家型"] -= 1.0
        scores["自然吸引型"] -= 2.0
    if dominant_theme_key == "attraction_pursuit" and pressure_score < 1.4 and action_score < 1.4:
        scores["高吸引高摩擦型"] -= 2.0
    if dominant_theme_key == "emotional_safety":
        scores["高吸引高摩擦型"] -= 1.5
        scores["歡喜冤家型"] -= 1.0
        scores["自然吸引型"] -= 1.0
    if not aspect_cluster.get("hasRepeatedActionConflict"):
        scores["歡喜冤家型"] -= 1.5
    if not aspect_cluster.get("hasRepeatedSaturnPressure"):
        scores["磨合成長型"] -= 1.0

    title = max(ARCHETYPE_TITLES, key=lambda item: (scores[item], -ARCHETYPE_TITLES.index(item)))
    return {
        "title": title,
        "subtitle": ARCHETYPE_SUBTITLES.get(title, ARCHETYPE_SUBTITLES["慢熱安全感型"]),
        "has_attraction": attraction_score >= 1.4 or bool(aspect_cluster.get("hasRepeatedAttractionPursuit")),
        "has_conflict": action_score >= 1.4 or bool(aspect_cluster.get("hasRepeatedActionConflict")),
        "has_pressure": pressure_score >= 1.4 or bool(aspect_cluster.get("hasRepeatedSaturnPressure")),
        "has_identity": identity_score >= 1.0 or bool(aspect_cluster.get("hasRepeatedIdentityRhythm")),
        "has_jupiter": jupiter_score >= 1.0 or any("Jupiter" in pair for pair in selected_pairs),
        "has_outer": outer_score > 0,
        "has_communication": communication_score >= 1.4 or bool(aspect_cluster.get("hasRepeatedCommunicationRepair")),
        "selected_pairs": selected_pairs,
    }


def relationship_archetype_block(evidence_clusters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    aspect_cluster = evidence_clusters.get("aspectFunctionCombination") or {}
    profile = relationship_archetype_signal_profile(aspect_cluster)
    title = str(profile.get("title") or "慢熱安全感型")
    subtitle = str(profile.get("subtitle") or ARCHETYPE_SUBTITLES["慢熱安全感型"])
    selected_pairs = set(str(item) for item in profile.get("selected_pairs") or [] if item)
    has_pressure = bool(profile.get("has_pressure"))
    has_attraction = bool(profile.get("has_attraction"))
    has_conflict = bool(profile.get("has_conflict"))
    has_identity = bool(profile.get("has_identity"))
    has_jupiter = bool(profile.get("has_jupiter"))
    has_outer = bool(profile.get("has_outer"))
    has_communication = bool(profile.get("has_communication"))

    reasons = []
    dominant_label = str(aspect_cluster.get("dominantRepeatedThemeLabel") or "")
    if dominant_label:
        reasons.append(f"最常反覆出現：{dominant_label}")
    if selected_pairs:
        reasons.append(f"星盤重點：{format_pair_key_list(sorted(selected_pairs)[:4])}")
    if has_communication and title == "溝通修復型":
        reasons.append("關鍵不是多說，而是換成對方比較接得住的說法")
    if has_identity and title == "彼此牽動型":
        reasons.append("彼此會影響對方的反應和節奏，不能只看一次冷熱")
    if has_pressure:
        reasons.append("靠近時容易變緊，重點在語氣、距離和回應方式")
    if has_attraction:
        reasons.append("吸引相位讓互動不是單純無感")
    source_claim_ids = unique([str(claim_id) for claim_id in aspect_cluster.get("claimIds") or [] if claim_id])
    method_claim_ids = unique([*RELATIONSHIP_INSIGHT_METHOD_CLAIM_IDS, *[str(item) for item in aspect_cluster.get("methodClaimIds") or [] if item]])
    return {
        "version": "relationship-archetype-v1",
        "title": title,
        "subtitle": subtitle,
        "meaning": relationship_archetype_meaning(
            title,
            aspect_cluster,
            has_attraction=has_attraction,
            has_conflict=has_conflict,
            has_pressure=has_pressure,
            has_identity=has_identity,
            has_jupiter=has_jupiter,
            has_outer=has_outer,
        ),
        "whySelected": reasons or ["本次以合盤優先相位與重複主題作為關係類型依據。"],
        "strengths": relationship_archetype_strengths(title, has_attraction, has_identity, has_jupiter),
        "risks": relationship_archetype_risks(title, has_pressure, has_conflict),
        "source": RELATIONSHIP_INSIGHT_SOURCE,
        "sourceClaimIds": source_claim_ids,
        "methodClaimIds": method_claim_ids,
        "evidenceClusterKeys": ["aspectFunctionCombination"],
        "doesNotProve": "關係類型是閱讀入口，不是命定結論；不能證明對方一定回來、一定承諾或一定分開。",
    }


def relationship_archetype_meaning(
    title: str,
    aspect_cluster: dict[str, Any],
    *,
    has_attraction: bool,
    has_conflict: bool,
    has_pressure: bool,
    has_identity: bool,
    has_jupiter: bool,
    has_outer: bool,
) -> str:
    dominant = aspect_cluster.get("dominantRepeatedTheme") if isinstance(aspect_cluster.get("dominantRepeatedTheme"), dict) else {}
    dominant_label = str(dominant.get("label") or aspect_cluster.get("dominantRepeatedThemeLabel") or "")
    dominant_theme_key = str(dominant.get("themeKey") or aspect_cluster.get("dominantRepeatedThemeKey") or "")
    selected_pairs = [str(item) for item in aspect_cluster.get("selectedPairs") or [] if item]
    pair_phrase = format_pair_key_list(selected_pairs[:3])
    evidence_prefix = f"從這次比較明顯的 {pair_phrase} 來看，" if pair_phrase else ""
    theme_sentence = relationship_archetype_theme_plain_sentence(dominant_theme_key, dominant_label)

    if title == "歡喜冤家型":
        body = (
            f"{evidence_prefix}這段關係不是單純吵或不合，而是有火花，也容易在同一個地方變急。"
            "狀態好的時候，彼此會覺得對方很有存在感、很能帶動自己；一緊張，語氣、回覆速度、誰先靠近或誰先退讓，都可能被放大，最後變成兩個人互相頂住。"
            f"{theme_sentence}"
        )
    elif title == "高吸引高摩擦型":
        body = (
            f"{evidence_prefix}這段關係不是沒有吸引，而是有吸引的地方也很容易讓情緒升高。"
            "一靠近就有熱度，但越想確認、越想推進，越容易覺得對方在躲、在推，或好像沒有照自己的節奏來。"
            f"{theme_sentence}"
        )
    elif title == "靈魂伴侶型":
        body = (
            f"{evidence_prefix}這段關係的熟悉感比較明顯，容易有情緒被對方碰到、生活節奏像能互相理解的感覺。"
            "但熟悉不等於一定穩定，仍要看對方能不能把感受落到持續行動。"
            f"{theme_sentence}"
        )
    elif title == "磨合成長型":
        body = (
            f"{evidence_prefix}這段關係有重量，不太適合用一時熱度判斷。"
            "它容易把責任、界線、害怕受傷或承諾壓力帶出來；如果要往前，重點會是能不能慢慢建立成熟的互動規則。"
            f"{theme_sentence}"
        )
    elif title == "命中貴人型":
        body = (
            f"{evidence_prefix}你們容易打開彼此的視野，讓對方看見更大的可能性。"
            "這種關係的亮點在支持、鼓勵和一起變好；但是否能成為穩定關係，仍要看日常責任和回應是否跟得上。"
            f"{theme_sentence}"
        )
    elif title == "溝通修復型":
        body = (
            f"{evidence_prefix}這段關係的重點不只是有沒有感覺，而是兩個人怎麼把話說到對方聽得進去。"
            "如果說法太急、太滿，原本想靠近的話也可能變成壓力；但只要訊息變短、變清楚，互動就比較有機會重新接上。"
            f"{theme_sentence}"
        )
    elif title == "彼此牽動型":
        body = (
            f"{evidence_prefix}你們很容易被對方影響，不一定是誰比較強勢，而是彼此的反應會牽動下一步。"
            "狀態好的時候，這會帶來熟悉感；狀態不穩時，一次冷淡、一次沉默或一次靠近，都容易被放大成關係答案。"
            f"{theme_sentence}"
        )
    elif title == "前世因緣感型":
        body = (
            f"{evidence_prefix}這段關係的牽引感可能很強，容易讓人覺得不是普通相遇。"
            "但越有命定感，越要把強烈感受和現實行動分開看，避免用情緒濃度直接推成結果。"
            f"{theme_sentence}"
        )
    elif title == "自然吸引型":
        body = (
            f"{evidence_prefix}你們有比較自然的靠近入口，互動中容易先出現好感、興趣或被對方帶動的感覺。"
            "這是關係的起點，不是結論；後面仍要看溝通穩定度和壓力來時的修復能力。"
            f"{theme_sentence}"
        )
    else:
        body = (
            f"{evidence_prefix}這段關係比較需要從安全感和可預期回應慢慢建立。"
            "它不適合只看一時熱絡或一次冷淡，而要看互動是否能穩定累積、是否讓兩個人都比較安心。"
            f"{theme_sentence}"
        )

    modifiers: list[str] = []
    if has_attraction and has_conflict:
        modifiers.append("這也是為什麼你們有時很有火花、有時又很累；兩種感覺同時存在，才會讓人更難判斷。")
    elif has_attraction:
        modifiers.append("彼此有被帶動的位置，這是比較容易自然靠近的入口。")
    if has_pressure:
        modifiers.append("最實際的重點，是先把互動變小：少一點追問，留一點對方能自然接話的空間。")
    if has_identity:
        modifiers.append("你們的情緒節奏會互相影響，不能只看一次冷或一次熱。")
    if has_jupiter:
        modifiers.append("也有互相鼓勵、把心打開的地方，但還是要看日常行動有沒有跟上。")
    if has_outer:
        modifiers.append("牽引感強的時候，更要回頭看現實裡有沒有穩定互動。")

    return normalize_zh_text("".join([body, *modifiers[:2]]))


def relationship_archetype_theme_plain_sentence(theme_key: str, label: str) -> str:
    if theme_key == "action_conflict":
        return "你們最容易卡在靠近的速度和語氣：一方想快一點確認，另一方可能覺得被推，原本想靠近就容易變成互相拉扯。"
    if theme_key == "attraction_pursuit":
        return "吸引感會反覆出現，常表現在想找對方、想看對方反應，或被對方一句話、一個動作帶動情緒。"
    if theme_key == "emotional_safety":
        return "安全感會是關鍵：有沒有被接住、有沒有被重視，會比一次冷或一次熱更影響你們的互動。"
    if theme_key == "saturn_pressure":
        return "一談到責任、未來或結果，這段關係就容易變重；不是不能談，而是要先把話題縮到一件具體、能回答的事。"
    if theme_key == "communication_repair":
        return "很多卡住感會從說法開始：同一句話如果太急、太滿或太像逼問，就容易讓對方接不住。"
    if theme_key == "identity_rhythm":
        return "你們會互相影響彼此的反應節奏，所以不能只用一次熱絡或一次冷掉判斷整段關係。"
    if theme_key == "outer_intensity":
        return "牽引感可能很強，讓人很難完全放下；但越強烈，越要回頭看日常互動有沒有真的穩。"
    if label:
        return f"這個主題會反覆影響你們互動：{label}。"
    return ""


def relationship_archetype_strengths(title: str, has_attraction: bool, has_identity: bool, has_jupiter: bool) -> list[str]:
    strengths = []
    if title == "溝通修復型":
        strengths.append("只要說法變短、變清楚，互動比較有機會重新接上。")
    if title == "彼此牽動型":
        strengths.append("彼此的反應很容易影響下一步，這也是重新理解對方的入口。")
    if has_attraction:
        strengths.append("彼此容易被對方點到，關係不是單純無感。")
    if has_identity:
        strengths.append("熟悉感或情緒節奏容易成為重新理解彼此的入口。")
    if has_jupiter or title == "命中貴人型":
        strengths.append("彼此有機會提供鼓勵、視野或人生方向上的支持。")
    if not strengths:
        strengths.append("這段關係適合從安全感和可預期互動慢慢建立，不急著下結論。")
    return strengths[:3]


def relationship_archetype_risks(title: str, has_pressure: bool, has_conflict: bool) -> list[str]:
    risks = []
    if title == "溝通修復型":
        risks.append("話一長或一急，對方容易先接收到壓力，而不是你的本意。")
    if title == "彼此牽動型":
        risks.append("一次冷熱很容易被放大，判斷要看連續互動。")
    if has_pressure:
        risks.append("越想確認承諾，越可能碰到防衛、延遲或責任壓力。")
    if has_conflict:
        risks.append("一急著推進或辯解，互動容易從在乎變成硬碰硬。")
    if "靈魂" in title or "前世" in title:
        risks.append("不要把熟悉感或命定感當成現實承諾。")
    if not risks:
        risks.append("舒服感仍需要現實回應支撐，不能只靠感覺撐住。")
    return risks[:3]


def partner_needs_block(fixture: dict[str, Any], evidence_clusters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    need_points = western_need_points(fixture, "person_b")
    point_order = ["Moon", "Venus", "Mercury", "Saturn", "Mars", "Desc"]
    needs_by_point = {str(item.get("point") or ""): item for item in need_points}
    items: list[dict[str, Any]] = []
    for point in point_order:
        need = needs_by_point.get(point)
        if not need:
            continue
        sign_label = str(need.get("sign") or "")
        item = {
            "point": point,
            "title": partner_need_title(point, sign_label),
            "need": partner_need_copy(point, sign_label),
            "relationshipStyleWanted": partner_relationship_style(point, sign_label),
            "emotionalSafetyCondition": partner_emotional_safety(point, sign_label),
            "affectionLanguage": partner_affection_language(point, sign_label),
            "conflictDefense": partner_conflict_defense(point, sign_label),
            "commitmentPace": partner_commitment_pace(point, sign_label),
            "whatOpensHimUp": partner_opens_up(point, sign_label),
            "whatShutsHimDown": partner_shuts_down(point, sign_label),
            "commonMisread": partner_common_misread(point, sign_label),
            "finalActionSuggestion": partner_need_action(point, sign_label),
            "howItShowsUp": partner_need_signal(point, sign_label),
            "whatHelps": partner_need_action(point, sign_label),
            "confidence": str(need.get("confidence") or "medium"),
            "precisionNote": str(need.get("precisionNote") or ""),
            "source": str((evidence_clusters.get("identityNeeds") or {}).get("source") or "western-natal-relationship-needs"),
            "sourceClaimIds": [str(claim_id) for claim_id in (evidence_clusters.get("identityNeeds") or {}).get("claimIds") or [] if claim_id],
            "methodClaimIds": ["george-bloch-relationship-comparison-wants-needs", "burk-safety-validation-needs-before-compatibility"],
            "evidenceClusterKeys": ["identityNeeds", f"{point.lower()}Sign"],
        }
        items.append(ensure_distinct_partner_need_fields(item, sign_label))
        if len(items) >= 4:
            break
    return {
        "version": "partner-needs-v1",
        "label": "對方在感情中真正需要什麼",
        "framing": "從對方命盤與合盤互動看，他在關係裡想被怎麼愛、怎麼確認安全感，以及壓力大時容易怎麼保護自己。",
        "profile": partner_needs_profile(items),
        "items": items,
        "source": "western-natal-relationship-needs",
        "sourceClaimIds": relationship_insight_source_claim_ids(items),
        "methodClaimIds": relationship_insight_method_claim_ids(items),
        "evidenceClusterKeys": ["identityNeeds", "relationshipProfiles"],
        "doesNotProve": "這些關係需求線索用來看他比較接得住什麼條件，再搭配實際互動判斷下一步。",
    }


def partner_need_title(point: str, sign_label: str) -> str:
    sign_label = display_sign_label(sign_label)
    point_label = POINT_LABELS.get(point, point)
    title_map = {
        "Moon": "情緒安全需要",
        "Venus": "好感表達需要",
        "Mercury": "說話方式需要",
        "Saturn": "壓力防衛需要",
        "Mars": "行動速度需要",
    }
    return f"{title_map.get(point, '關係需求線索')}：{sign_label}{point_label}"


def normalized_need_field(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip("。；，, ")


def need_field_is_duplicate(item: dict[str, Any], key: str) -> bool:
    value = normalized_need_field(item.get(key))
    if not value:
        return True
    duplicate_sources = {
        normalized_need_field(item.get("howItShowsUp")),
        normalized_need_field(item.get("need")),
        normalized_need_field(item.get("conflictDefense")),
    }
    other_slot_values = {
        normalized_need_field(item.get(other_key))
        for other_key in ("whatOpensHimUp", "whatShutsHimDown", "commonMisread")
        if other_key != key
    }
    return value in duplicate_sources or value in other_slot_values


def ensure_distinct_partner_need_fields(item: dict[str, Any], sign_label: str) -> dict[str, Any]:
    point = str(item.get("point") or "")
    replacements = partner_need_slot_replacements(point, sign_label)
    for key, replacement in replacements.items():
        if need_field_is_duplicate(item, key):
            item[key] = replacement
    return item


def partner_need_slot_replacements(point: str, sign_label: str) -> dict[str, str]:
    sign_label = display_sign_label(sign_label)
    point_label = POINT_LABELS.get(point, point)
    by_point = {
        "Moon": {
            "whatOpensHimUp": f"情緒被接住、語氣不被審判，會讓他的{sign_label}{point_label}比較願意靠近。",
            "whatShutsHimDown": "把脆弱當成把柄、用情緒審問他，會讓他先把感受收起來。",
            "commonMisread": "他需要安全感不等於要你一直退讓；重點是互動能不能讓他安心表達。",
        },
        "Venus": {
            "whatOpensHimUp": f"他感覺自己被欣賞、好感可以自然流動時，{sign_label}{point_label}比較容易回應。",
            "whatShutsHimDown": "把好感變成考試、要求他立刻證明在乎，會讓吸引感變成壓力。",
            "commonMisread": "他表達好感的方式不一定等於承諾方式；需要把喜歡和承擔分開看。",
        },
        "Mercury": {
            "whatOpensHimUp": f"問題被說清楚、語氣有空間，他的{sign_label}{point_label}才比較能繼續對話。",
            "whatShutsHimDown": "一句話裡塞太多質問、結論和翻舊帳，會讓他不知道該先回哪一件事。",
            "commonMisread": "他說得慢或轉得遠，不一定是在逃；可能是還在整理怎麼說才不會更糟。",
        },
        "Saturn": {
            "whatOpensHimUp": f"界線被尊重、責任被拆成可做到的小步驟，{sign_label}{point_label}才比較不會只剩防衛。",
            "whatShutsHimDown": "用期限、審判或承諾壓力逼他表態，會讓他把關係先放到風險區。",
            "commonMisread": "他保守不一定是拒絕；很多時候是在評估這段關係能不能承受現實壓力。",
        },
        "Mars": {
            "whatOpensHimUp": f"讓他有主動選擇和行動空間，{sign_label}{point_label}比較容易把靠近變成實際動作。",
            "whatShutsHimDown": "把靠近變成催促、控制或勝負，會讓他的行動力變成防禦力。",
            "commonMisread": "他行動快慢不是唯一答案；要看動作之後是否持續、是否願意修正。",
        },
    }
    return by_point.get(
        point,
        {
            "whatOpensHimUp": "清楚、穩定、能保留選擇的互動，會讓他比較願意靠近。",
            "whatShutsHimDown": "追問、試探、把一次反應放大成結論，會讓他先保護自己。",
            "commonMisread": "反應變慢不一定就是沒感覺；還要看後續行動是否願意延續。",
        },
    )


def sign_relationship_texture(sign_label: str) -> dict[str, str]:
    sign_label = display_sign_label(sign_label)
    textures = {
        "牡羊": {
            "need": "直接、坦白，但不要被催著立刻反應",
            "signal": "感覺被逼表態時，容易先用硬一點的方式保護自己",
            "action": "話說清楚就好，不用連續追問或用速度測試他",
        },
        "金牛": {
            "need": "穩定、可預期、不要一下子改變節奏",
            "signal": "節奏被打亂時，容易先固守原狀，不想太快重新相信",
            "action": "用穩定的小行動累積信任，不用一次要求很大的改變",
        },
        "雙子": {
            "need": "可以呼吸的對話空間，不要把每句話都變成審問",
            "signal": "話題太重時，可能用轉移、變輕或沉默來避開壓力",
            "action": "一次只開一個話題，讓對方有自然接話的餘地",
        },
        "巨蟹": {
            "need": "情緒被照顧，也需要感覺自己沒有被推到外面",
            "signal": "沒有安全感時，容易先退回殼裡，不直接說清楚",
            "action": "先讓語氣變柔和，再談具體事情，不用逼他立刻剖白",
        },
        "獅子": {
            "need": "被尊重、被看見，不喜歡在關係裡被貶低",
            "signal": "感覺不被尊重時，容易先硬起來或不回應",
            "action": "先承認他的感受和位置，再談你真正要說的事",
        },
        "處女": {
            "need": "清楚、具體、可整理的互動，不要混亂又情緒化",
            "signal": "壓力來時會想分析細節，也可能變得挑剔或防衛",
            "action": "把問題拆小，講具體事件，不用一次談完整段關係",
        },
        "天秤": {
            "need": "互相尊重、語氣平衡，不要把對話推成對立",
            "signal": "氣氛太尖銳時，容易先維持表面和平或延後回應",
            "action": "用合作語氣開頭，少用責備句，讓對話有台階可下",
        },
        "天蠍": {
            "need": "真誠和安全感，不能只靠表面輕鬆帶過",
            "signal": "感覺不被信任時，容易測試、沉默或把界線拉高",
            "action": "少試探，多講清楚你的界線和真實感受",
        },
        "射手": {
            "need": "自由感和誠實，不喜歡被關在沉重結論裡",
            "signal": "壓力太密時，容易想逃開或把話說得很直",
            "action": "先給空間，再用簡單坦白的方式說重點",
        },
        "摩羯": {
            "need": "負責任、可落地的行動，不喜歡只有情緒沒有方案",
            "signal": "談未來或承諾時，容易先評估現實可不可行",
            "action": "把期待變成小而可做到的行動，不用逼他立刻承諾",
        },
        "水瓶": {
            "need": "理性空間和尊重界線，不喜歡被情緒綁住",
            "signal": "被逼近時，容易拉開距離，用冷靜維持自主感",
            "action": "先保留空間，用清楚但不黏人的方式開口",
        },
        "雙魚": {
            "need": "溫柔、可感受的安全感，不適合太硬的逼問",
            "signal": "壓力太明確時，容易模糊、退開或不知怎麼回答",
            "action": "先用穩定、可預期的小回應建立安全感，不急著要答案",
        },
    }
    return textures.get(
        sign_label,
        {
            "need": "可被他接住的互動節奏",
            "signal": "壓力太大時會先保護自己，不一定能立刻說清楚",
            "action": "先觀察對方實際回應，再決定下一步",
        },
    )


def sign_relationship_depth(sign_label: str) -> dict[str, str]:
    sign_label = display_sign_label(sign_label)
    profiles = {
        "牡羊": {
            "relationshipStyle": "他比較能在直接、坦白、有生命力的關係裡放鬆；不喜歡猜來猜去或被動等待太久。",
            "emotionalSafety": "清楚表達比反覆試探更有安全感；他需要知道你要的是什麼，但不想被逼著立刻回答。",
            "affectionLanguage": "欣賞他的行動力、主動性和真實反應，比鋪陳很久的情緒話更容易被他接住。",
            "conflictDefense": "被逼近時可能先硬起來、反擊或急著切斷話題，這通常是在保護自主感。",
            "commitmentPace": "承諾要讓他覺得仍有行動空間；越像命令或期限，越容易引起防衛。",
            "opensUp": "直接但不逼迫的肯定、清楚的小邀請、讓他可以自己選擇的靠近方式。",
            "shutsDown": "冷處理後突然要求答案、用速度測試在不在乎、把一次反應放大成承諾。",
            "commonMisread": "他反應快或語氣直，不一定代表不在乎；更常是先用行動保護自己。",
        },
        "金牛": {
            "relationshipStyle": "他比較想要穩定、可預期、能慢慢累積信任的關係，不喜歡忽冷忽熱。",
            "emotionalSafety": "安全感來自持續出現、說到做到，以及日常裡穩穩的可靠感。",
            "affectionLanguage": "實際照顧、穩定陪伴、記得小細節，比情緒很滿的告白更容易讓他安心。",
            "conflictDefense": "節奏被打亂時會先固守原狀，甚至看起來固執，因為他需要時間重新確認安全。",
            "commitmentPace": "承諾需要慢慢落地；他會看行動是否持續，而不是只聽當下情緒。",
            "opensUp": "固定的聯絡節奏、可信的小承諾、讓他感覺生活被穩住的互動。",
            "shutsDown": "突然改變規則、反覆推翻前面說好的事、用焦慮逼他立刻改變。",
            "commonMisread": "他慢，不一定是冷淡；可能是還在確認這份關係能不能真的穩。",
        },
        "雙子": {
            "relationshipStyle": "他比較需要能聊天、有空氣感、可以交換想法的關係，不喜歡每句話都變成沉重考題。",
            "emotionalSafety": "能輕鬆說話、保留彈性和幽默感，會比直接逼情緒結論更安全。",
            "affectionLanguage": "有來有往的分享、好奇他的想法、讓對話有轉圜，是他比較容易感到被喜歡的方式。",
            "conflictDefense": "話題太重時可能轉移、打岔或變得飄忽，不一定是不在乎，而是先避開壓力。",
            "commitmentPace": "承諾需要先從理解彼此的生活節奏開始；太早定義容易讓他覺得失去呼吸空間。",
            "opensUp": "短而清楚的訊息、開放式問題、能自然延伸的小話題。",
            "shutsDown": "長篇追問、要求一次講清所有感受、把每次回覆都拿來審核。",
            "commonMisread": "他變輕或轉話題，不一定代表沒感覺；有時是還不知道怎麼處理太重的情緒。",
        },
        "巨蟹": {
            "relationshipStyle": "他比較想要有歸屬感、被照顧、情緒能被安放的關係。",
            "emotionalSafety": "安全感來自溫柔、記得他的感受，以及不把脆弱拿來攻擊。",
            "affectionLanguage": "關心他的日常、記得他在意的小事、讓他覺得自己被放在心上。",
            "conflictDefense": "受傷時可能退回殼裡、沉默或用情緒繞路表達，因為他怕直接碰撞更受傷。",
            "commitmentPace": "承諾需要讓他感覺你真的在乎他的感受，而不是只想得到一個答案。",
            "opensUp": "柔和確認、穩定照顧、讓他知道你沒有要否定他的感受。",
            "shutsDown": "忽略情緒、用冷淡懲罰、把他的敏感說成太麻煩。",
            "commonMisread": "他退縮不一定是拒絕，可能是在等情緒比較安全時再回來。",
        },
        "獅子": {
            "relationshipStyle": "他比較需要被尊重、被看見、能保有自尊的關係。",
            "emotionalSafety": "你看見他的好，並且不在脆弱時羞辱他，會讓他比較願意打開。",
            "affectionLanguage": "真誠欣賞、公開或明確的重視、讓他感覺自己在你心中有位置。",
            "conflictDefense": "自尊被碰到時可能強硬、冷掉或維持體面，因為他不想輸在被否定的感覺裡。",
            "commitmentPace": "承諾需要帶著尊重和肯定，而不是讓他覺得被審判。",
            "opensUp": "先肯定他的感受和努力，再談你真正需要調整的事。",
            "shutsDown": "否定、嘲諷、比較，或把他的在乎說成幼稚。",
            "commonMisread": "他要面子，不代表沒有感覺；有時越在意，越不想顯得狼狽。",
        },
        "處女": {
            "relationshipStyle": "他比較需要清楚、具體、能一起把生活整理好的關係。",
            "emotionalSafety": "把事情說清楚、界線具體、問題可以被拆解，會讓他比較安心。",
            "affectionLanguage": "實際幫忙、細節上的用心、願意一起修正問題，是他容易感到被愛的方式。",
            "conflictDefense": "壓力來時會分析、挑細節或變得防衛，因為他想找到可修的地方。",
            "commitmentPace": "承諾需要可執行；空泛的保證不如一個具體可做到的改變。",
            "opensUp": "把問題拆小、講具體事件、讓他知道下一步可以怎麼做。",
            "shutsDown": "混亂指控、情緒爆量、一直換題，讓他無法判斷要修哪裡。",
            "commonMisread": "他挑細節不一定是不愛，可能是用修問題的方式處理不安。",
        },
        "天秤": {
            "relationshipStyle": "他比較想要互相尊重、好好說話、能維持平衡感的關係。",
            "emotionalSafety": "語氣公平、願意聽彼此立場，會比逼他站隊更有安全感。",
            "affectionLanguage": "溫和的欣賞、一起做決定、讓互動保持美感和禮貌。",
            "conflictDefense": "氣氛太尖銳時，他可能先維持表面和平或延後回應。",
            "commitmentPace": "承諾需要雙方都覺得公平；他不太能在被逼表態時做穩定選擇。",
            "opensUp": "用合作語氣、提供選項、讓他覺得不是被審判而是一起協調。",
            "shutsDown": "咄咄逼人、非黑即白、把對話推成輸贏。",
            "commonMisread": "他想維持和平，不一定代表沒立場；可能是怕衝突破壞關係。",
        },
        "天蠍": {
            "relationshipStyle": "他比較需要真誠、深度和安全感，不太能只靠表面輕鬆撐住關係。",
            "emotionalSafety": "真正的安全感來自可信任、不中途背叛、不拿脆弱交換控制。",
            "affectionLanguage": "專注、真實、願意面對深層問題，比漂亮話更能讓他相信。",
            "conflictDefense": "不安時可能沉默、測試或把界線拉高，因為他在確認是否還能信任。",
            "commitmentPace": "承諾不能只說好聽；他會看你是否一致、是否扛得住深層情緒。",
            "opensUp": "坦白、守住界線、少試探，讓他看見你不是在操控或逃避。",
            "shutsDown": "曖昧閃躲、說一套做一套、用猜測和控制換安全感。",
            "commonMisread": "他的沉默不一定是沒感覺，可能是在觀察這段關係還能不能信任。",
        },
        "射手": {
            "relationshipStyle": "他比較需要有自由感、誠實、能一起往前看的關係，不喜歡被關在沉重結論裡。",
            "emotionalSafety": "你能給他空間，又願意坦白講真話，會比緊盯答案更讓他安心。",
            "affectionLanguage": "一起探索、直接分享、尊重他的生活半徑，是他比較容易感到被喜歡的方式。",
            "conflictDefense": "壓力太密時可能想逃開或說話變直，因為他怕被困住。",
            "commitmentPace": "承諾需要讓他覺得關係仍有成長和呼吸空間，而不是被鎖住。",
            "opensUp": "給空間、講重點、讓對話有未來感而不是審判感。",
            "shutsDown": "連環追問、情緒勒緊、把自由感說成不負責任。",
            "commonMisread": "他需要空間不等於不愛；更多時候是需要先找回能誠實靠近的狀態。",
        },
        "摩羯": {
            "relationshipStyle": "他比較需要有責任感、能落地、經得起時間檢查的關係。",
            "emotionalSafety": "可執行的承諾、穩定行動和現實安排，比情緒宣言更能讓他安心。",
            "affectionLanguage": "可靠、一起處理現實問題、用行動證明在乎。",
            "conflictDefense": "壓力大時會先評估現實可不可行，可能看起來冷或慢。",
            "commitmentPace": "承諾要一步一步落地；他不容易只因情緒高點就答應大事。",
            "opensUp": "把期待變成小而可做到的安排，讓他看見關係不是失控負擔。",
            "shutsDown": "只談感受不談做法、用期限逼承諾、把他的保守說成不愛。",
            "commonMisread": "他慢慢評估不一定是拒絕，可能是在確認自己能不能負責。",
        },
        "水瓶": {
            "relationshipStyle": "他比較需要理性空間、尊重界線、仍能做自己的關係。",
            "emotionalSafety": "不被情緒綁住、可以保留個人空間，反而更容易讓他穩定靠近。",
            "affectionLanguage": "尊重他的想法、給他自主權、用清楚但不黏人的方式表達在乎。",
            "conflictDefense": "被逼近時容易拉開距離，用冷靜或理性維持自主感。",
            "commitmentPace": "承諾需要保有個人空間；越像控制，越容易讓他退後。",
            "opensUp": "清楚說明、不黏著、不用情緒交換答案，讓他感覺界線被尊重。",
            "shutsDown": "用情緒換答案、要求秒回、一拉開距離就追問他是不是不在乎。",
            "commonMisread": "他冷靜不一定是沒有感情；可能是需要用距離保持可回應。",
        },
        "雙魚": {
            "relationshipStyle": "他比較需要溫柔、有感受、有想像空間的關係，不適合太硬的逼問。",
            "emotionalSafety": "安全感來自被溫柔理解，而不是被要求立刻把所有感受說清楚。",
            "affectionLanguage": "柔和關心、情緒共感、讓他感覺你不是來審判他的。",
            "conflictDefense": "壓力太明確時容易模糊、退開或不知道怎麼回答。",
            "commitmentPace": "承諾需要先讓情緒安定；太硬的期限會讓他更想躲。",
            "opensUp": "柔和、穩定、可感受的回應，讓他知道靠近不會立刻被審問。",
            "shutsDown": "尖銳質問、冷硬判斷、把他的模糊直接說成逃避或欺騙。",
            "commonMisread": "他模糊不一定是故意吊著你；可能是真的還沒整理好感受。",
        },
    }
    return profiles.get(
        sign_label,
        {
            "relationshipStyle": "他比較需要一段能尊重界線、也能穩定互動的關係。",
            "emotionalSafety": "安全感要從可觀察的互動慢慢確認，不能只靠猜測補空白。",
            "affectionLanguage": "日常裡穩定、清楚、不逼迫的善意，比一次說很多更容易被接住。",
            "conflictDefense": "壓力大時會先保護自己，不一定能立刻把話說清楚。",
            "commitmentPace": "承諾需要回到現實條件和可持續行動裡確認。",
            "opensUp": "清楚、穩定、可退場的互動。",
            "shutsDown": "追問、試探、把一次反應放大成最後答案。",
            "commonMisread": "退後或變慢不一定等於沒感覺，仍要看後續可觀察行動。",
        },
    )


def partner_relationship_style(point: str, sign_label: str) -> str:
    depth = sign_relationship_depth(sign_label)
    point_label = POINT_LABELS.get(point, point)
    if point == "Moon":
        return f"從{point_label}看，他在親密關係裡最先尋找的是：{depth['relationshipStyle']}"
    if point == "Venus":
        return f"從{point_label}看，他比較容易被這種關係氛圍吸引：{depth['relationshipStyle']}"
    if point == "Mercury":
        return f"從{point_label}看，他需要一段能好好說話的關係：{depth['relationshipStyle']}"
    if point == "Saturn":
        return f"從{point_label}看，他會在意這段關係能不能經得起現實：{depth['relationshipStyle']}"
    if point == "Mars":
        return f"從{point_label}看，他靠近關係時很在意行動自由和節奏：{depth['relationshipStyle']}"
    return depth["relationshipStyle"]


def partner_emotional_safety(point: str, sign_label: str) -> str:
    return sign_relationship_depth(sign_label)["emotionalSafety"]


def partner_affection_language(point: str, sign_label: str) -> str:
    return sign_relationship_depth(sign_label)["affectionLanguage"]


def partner_conflict_defense(point: str, sign_label: str) -> str:
    return sign_relationship_depth(sign_label)["conflictDefense"]


def partner_commitment_pace(point: str, sign_label: str) -> str:
    return sign_relationship_depth(sign_label)["commitmentPace"]


def partner_opens_up(point: str, sign_label: str) -> str:
    return sign_relationship_depth(sign_label)["opensUp"]


def partner_shuts_down(point: str, sign_label: str) -> str:
    return sign_relationship_depth(sign_label)["shutsDown"]


def partner_common_misread(point: str, sign_label: str) -> str:
    return sign_relationship_depth(sign_label)["commonMisread"]


def partner_needs_profile(items: list[dict[str, Any]]) -> dict[str, str]:
    by_point = {str(item.get("point") or ""): item for item in items if isinstance(item, dict)}
    first_item = next((item for item in items if isinstance(item, dict)), {})
    moon = by_point.get("Moon") or first_item
    venus = by_point.get("Venus") or moon
    mercury = by_point.get("Mercury") or moon
    saturn = by_point.get("Saturn") or by_point.get("Mars") or moon
    return {
        "title": "他想要的關係輪廓",
        "relationshipStyleWanted": str(moon.get("relationshipStyleWanted") or ""),
        "emotionalSafetyCondition": str(moon.get("emotionalSafetyCondition") or ""),
        "affectionLanguage": str(venus.get("affectionLanguage") or ""),
        "communicationNeed": str(mercury.get("relationshipStyleWanted") or mercury.get("emotionalSafetyCondition") or ""),
        "conflictDefense": str(saturn.get("conflictDefense") or ""),
        "commitmentPace": str(saturn.get("commitmentPace") or ""),
        "whatOpensHimUp": str(moon.get("whatOpensHimUp") or venus.get("whatOpensHimUp") or ""),
        "whatShutsHimDown": str(saturn.get("whatShutsHimDown") or moon.get("whatShutsHimDown") or ""),
        "commonMisread": str(moon.get("commonMisread") or ""),
        "boundaryNote": "這是關係需求輪廓；他的想法仍要回到實際回應來確認。",
    }


def partner_need_copy(point: str, sign_label: str) -> str:
    texture = sign_relationship_texture(sign_label)
    if point == "Moon":
        return f"情緒上需要{texture['need']}；這會影響他在不安時能不能繼續靠近。"
    if point == "Venus":
        return f"好感需要透過{texture['need']}被感受到；太用力的表達反而容易變成壓力。"
    if point == "Mercury":
        return f"說話方式需要{texture['need']}；語氣對了，他比較有空間繼續對話。"
    if point == "Saturn":
        return f"壓力下需要{texture['need']}；越像審判或期限，他越容易先保守。"
    if point == "Mars":
        return f"行動節奏需要{texture['need']}；靠近太快時，衝突也會變快。"
    return f"{display_sign_label(sign_label)}提供一個補充線索，但本次不把它寫成確定內心。"


def partner_need_signal(point: str, sign_label: str = "") -> str:
    texture = sign_relationship_texture(sign_label)
    if point == "Moon":
        return texture["signal"]
    if point == "Venus":
        return f"他比較容易對{texture['need']}的善意放下防備。"
    if point == "Mercury":
        return texture["signal"]
    if point == "Saturn":
        return f"承諾、責任、復合期限這類話題，會放大「{texture['signal']}」這個反應。"
    if point == "Mars":
        return texture["signal"]
    return "需要放回實際互動裡觀察。"


def partner_need_action(point: str, sign_label: str = "") -> str:
    texture = sign_relationship_texture(sign_label)
    if point == "Moon":
        return texture["action"]
    if point == "Venus":
        return texture["action"]
    if point == "Mercury":
        return texture["action"]
    if point == "Saturn":
        return texture["action"]
    if point == "Mars":
        return texture["action"]
    return "先看實際回應，不先把他的想法定死。"


def fallback_landmine_dynamic_key(
    *,
    fixture: dict[str, Any] | None,
    evidence_clusters: dict[str, dict[str, Any]] | None,
) -> str:
    context = (fixture or {}).get("context") if isinstance((fixture or {}).get("context"), dict) else {}
    question_key = str(context.get("main_question") or "")
    aspect_cluster = (evidence_clusters or {}).get("aspectFunctionCombination") or {}
    flag_order = (
        ("hasRepeatedCommunicationRepair", "communication_repair"),
        ("hasRepeatedActionConflict", "action_conflict"),
        ("hasRepeatedSaturnPressure", "saturn_pressure"),
        ("hasRepeatedEmotionalSafety", "emotional_safety"),
        ("hasRepeatedAttractionPursuit", "attraction_pursuit"),
        ("hasRepeatedIdentityRhythm", "identity_rhythm"),
        ("hasRepeatedOuterIntensity", "outer_intensity"),
    )
    for flag, key in flag_order:
        if aspect_cluster.get(flag):
            return key
    return {
        "still-love-me": "emotional_safety",
        "any-chance": "attraction_pursuit",
        "when-to-contact": "communication_repair",
        "what-did-i-do-wrong": "action_conflict",
        "stay-or-let-go": "saturn_pressure",
    }.get(question_key, "communication_repair")


def fallback_landmine_item(
    *,
    fixture: dict[str, Any] | None,
    evidence_clusters: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    context = (fixture or {}).get("context") if isinstance((fixture or {}).get("context"), dict) else {}
    question_key = str(context.get("main_question") or "")
    stage_key = str(context.get("relationship_stage") or "")
    dynamic_key = fallback_landmine_dynamic_key(fixture=fixture, evidence_clusters=evidence_clusters)
    title_by_dynamic = {
        "emotional_safety": "用追問換安全感",
        "saturn_pressure": "把責任題一次攤開",
        "communication_repair": "想說清楚時說得太滿",
        "attraction_pursuit": "把火花立刻推成關係定位",
        "action_conflict": "急著修復時變成硬碰硬",
        "identity_rhythm": "把在意變成誰先低頭",
        "outer_intensity": "用強烈感覺替現實補答案",
    }
    trigger_by_dynamic = {
        "emotional_safety": "不安一上來，就想立刻確認對方是不是還在。",
        "saturn_pressure": "一談承諾、責任或未來，對方可能先變慢或退開。",
        "communication_repair": "越想一次講完整，對方越可能只感覺被要求回答。",
        "attraction_pursuit": "一有熱絡，就急著把它推成明確關係。",
        "action_conflict": "本來想修復，卻因為太急變成互相頂住。",
        "identity_rhythm": "對話一像在比較誰比較在乎，尊重感就容易掉下來。",
        "outer_intensity": "感覺太強時，容易把猜測當成對方的選擇。",
    }
    repair_by_dynamic = {
        "emotional_safety": "先讓自己穩住，再看對方是否有連續、溫和的回應。",
        "saturn_pressure": "先談一件具體小事，不一次討論完整關係。",
        "communication_repair": "只留一個主題、一個問題，語氣放在理解，不放在說服。",
        "attraction_pursuit": "把熱絡留在日常互動裡，不立刻逼出關係名稱。",
        "action_conflict": "先放慢一格，只做不會讓氣氛變硬的小動作。",
        "identity_rhythm": "先保留彼此台階，不用輸贏感證明誰更在乎。",
        "outer_intensity": "先看清楚行動，不用回憶、氣氛或想像替對方補答案。",
    }
    stage_tail = {
        "broke-up-recent": "剛分開不久時，這個點特別容易被情緒放大。",
        "broke-up-long": "時間拉長後，這個點需要用新的互動驗證。",
        "cold-war": "冷戰時，這個點容易變成互等對方先低頭。",
        "crisis": "關係緊繃時，這個點容易讓同一次對話背太多壓力。",
    }.get(stage_key, "")
    question_tail = {
        "still-love-me": "這會讓你更想用一句回覆確認感情。",
        "any-chance": "這會讓修復變成逼出結果，而不是慢慢變穩。",
        "when-to-contact": "這會讓聯絡從靠近變成測試。",
        "what-did-i-do-wrong": "這會讓自責變成過度補救。",
        "stay-or-let-go": "這會讓等待變得更消耗。",
    }.get(question_key, "")
    return {
        "title": title_by_dynamic.get(dynamic_key, "把焦急變成追問"),
        "trigger": normalize_zh_text(" ".join(item for item in (trigger_by_dynamic.get(dynamic_key, ""), question_tail, stage_tail) if item)),
        "whyItHappens": "本次具體衝突相位不足時，用關係主題和現實情境保守推估最容易踩到的互動點。",
        "whatToDoInstead": repair_by_dynamic.get(dynamic_key, "先停在一件具體小事，不把全部答案放進同一次互動。"),
        "source": RELATIONSHIP_INSIGHT_SOURCE,
        "sourceClaimIds": [],
        "methodClaimIds": RELATIONSHIP_INSIGHT_METHOD_CLAIM_IDS,
        "evidenceClusterKeys": ["relationshipThesis", "relationshipContext", "aspectFunctionCombination"],
    }


def fight_landmines_block(
    conflict_dynamics: dict[str, Any],
    fixture: dict[str, Any] | None = None,
    evidence_clusters: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for conflict in conflict_dynamics.get("items") or []:
        pair_key = str(conflict.get("pairKey") or "")
        title = landmine_title(pair_key, len(items))
        if title in seen_titles:
            title = f"{pair_key_label(pair_key)}：{title}"
        if title in seen_titles:
            title = str(conflict.get("title") or title)
        if title in seen_titles:
            title = f"{title}（第 {len(items) + 1} 個觸發點）"
        seen_titles.add(title)
        items.append(
            {
                "title": title,
                "trigger": landmine_trigger(pair_key),
                "whyItHappens": landmine_why(pair_key),
                "whatToDoInstead": landmine_repair(pair_key),
                "source": conflict.get("source") or RELATIONSHIP_INSIGHT_SOURCE,
                "sourceClaimIds": conflict.get("sourceClaimIds") or [],
                "methodClaimIds": conflict.get("methodClaimIds") or [],
                "evidenceClusterKeys": conflict.get("evidenceClusterKeys") or ["conflictDynamics"],
            }
        )
        if len(items) >= 3:
            break
    if not items:
        items.append(fallback_landmine_item(fixture=fixture, evidence_clusters=evidence_clusters))
    return {
        "version": "fight-landmines-v1",
        "label": "你們最容易吵架的 3 個地雷",
        "items": items,
        "gaps": [] if len(items) >= 3 else [{"status": "limited_conflict_evidence", "reason": "本次可用衝突相位不足 3 個；不硬補靜態地雷。"}],
        "source": RELATIONSHIP_INSIGHT_SOURCE,
        "sourceClaimIds": relationship_insight_source_claim_ids(items),
        "methodClaimIds": relationship_insight_method_claim_ids(items),
        "evidenceClusterKeys": ["conflictDynamics", "aspectFunctionCombination"],
        "doesNotProve": "地雷是互動風險，不是誰有問題，也不是關係必定失敗。",
    }


def landmine_why(pair_key: str) -> str:
    if pair_key == "Mercury-Mercury":
        return "兩套邏輯同時想主導對話時，容易越講越像在校正對方。"
    if pair_key == "Sun-Venus":
        return "越想確認自己有沒有被喜歡，越容易把柔和互動推成壓力題。"
    if pair_key == "Venus-Mars":
        return "火花本來能靠近，但速度一快就會變成追逐、退後和不安。"
    if pair_key == "Mercury-Sun":
        return "話題碰到自尊時，重點會從理解彼此變成保護自己不被否定。"
    if pair_key == "Sun-Mars":
        return "刺激來得太快時，行動會先衝出去，理解反而跟不上。"
    if pair_key == "Moon-Venus":
        return "需要安撫和需要被喜歡混在一起時，很容易把親近變成確認題。"
    if pair_key == "Sun-Moon":
        return "一邊想被看見，一邊先照情緒走，容易讓彼此都覺得沒有被接住。"
    if pair_key == "Sun-Saturn":
        return "責任語氣一重，對方容易先覺得被否定，真正在意的事反而說不出口。"
    if pair_key == "Moon-Saturn":
        return "情緒需要被接住，但壓力感會讓另一方先縮回責任或沉默裡。"
    if pair_key == "Venus-Saturn":
        return "好感一被拿來檢查承諾，就容易從溫柔變成審核。"
    if pair_key == "Mars-Saturn":
        return "一方想往前，一方想踩煞車；吵點常在速度，不只在愛不愛。"
    if pair_key == "Mercury-Mars":
        return "越想把話講明白，越可能讓語氣帶火，對方先聽見攻擊感。"
    if pair_key == "Mercury-Saturn":
        return "責任題需要慢慢拆；一口氣說完，容易讓對方只感覺被審問。"
    if pair_key == "Mars-Mars":
        return "兩邊都用自己的速度反應時，對話會變成互相催促或互相較勁。"
    if pair_key == "Moon-Mars":
        return "情緒一熱就行動，會讓修復變成質問，而不是被理解。"
    if "Saturn" in pair_key:
        return "承諾和責任題會放大壓力，需要拆小再談。"
    return "這個互動點容易把焦急轉成行動，先停一下會比較有空間。"


def landmine_title(pair_key: str, index: int) -> str:
    if pair_key == "Mercury-Mercury":
        return "兩個人都想照自己的邏輯說話"
    if pair_key == "Sun-Venus":
        return "被喜歡的期待變成確認壓力"
    if pair_key == "Venus-Mars":
        return "火花變成追逐和拉扯"
    if pair_key == "Mercury-Sun":
        return "說話碰到自尊時變成誰對誰錯"
    if pair_key == "Sun-Mars":
        return "一被刺激就想立刻反應"
    if pair_key == "Moon-Venus":
        return "想被安撫時變成好感壓力"
    if pair_key == "Sun-Moon":
        return "一個要被理解、一個先照感覺走"
    if pair_key == "Sun-Saturn":
        return "一談責任就覺得被否定"
    if pair_key == "Moon-Saturn":
        return "情緒需要碰到責任牆"
    if pair_key == "Venus-Saturn":
        return "好感一接近承諾就變重"
    if pair_key == "Mars-Saturn":
        return "一個想推進、一個踩煞車"
    if pair_key == "Mercury-Mars":
        return "把話說清楚時變成攻防"
    if pair_key == "Mercury-Saturn":
        return "談責任時變成沉默或審判"
    if pair_key == "Mars-Mars":
        return "兩個人都想照自己的速度走"
    if pair_key == "Moon-Mars":
        return "情緒一被碰到就立刻反擊"
    if "Saturn" in pair_key:
        return "一談承諾就變重"
    return f"互動地雷 {index + 1}"


def landmine_trigger(pair_key: str) -> str:
    if pair_key == "Mercury-Mercury":
        return "兩個人都覺得自己已經說清楚，卻越講越像在校正對方。"
    if pair_key == "Sun-Venus":
        return "把欣賞、見面或回覆直接解讀成對方應該更明確表態。"
    if pair_key == "Venus-Mars":
        return "有火花時就想推進，對方一慢下來就開始不安或追問。"
    if pair_key == "Mercury-Sun":
        return "本來想說清楚，卻變成誰比較有道理、誰被否定。"
    if pair_key == "Sun-Mars":
        return "對方一句話點到你時，立刻用行動、反擊或催促回應。"
    if pair_key == "Moon-Venus":
        return "想要被安撫或被喜歡時，忍不住把好感變成確認要求。"
    if pair_key == "Sun-Moon":
        return "一方想被看見，另一方先照情緒反應，容易錯過彼此重點。"
    if pair_key == "Sun-Saturn":
        return "用批評、否定或責任壓力碰到對方的自尊。"
    if pair_key == "Moon-Saturn":
        return "在情緒很滿時要求對方立刻安撫、承認或負責。"
    if pair_key == "Venus-Saturn":
        return "把好感、回覆或見面直接推成承諾檢查。"
    if pair_key == "Mars-Saturn":
        return "一方急著推進，另一方覺得被控制或被要求。"
    if pair_key.startswith("Mercury") or "Mercury" in pair_key:
        return "長訊息、反覆解釋、要求對方立刻承認或回答。"
    if pair_key == "Mars-Mars":
        return "用催促、比較、試探來確認誰比較在乎。"
    if pair_key == "Moon-Mars":
        return "情緒很滿時馬上追問、質問或翻舊帳。"
    if "Saturn" in pair_key:
        return "把承諾、責任、復合期限一次攤開談。"
    return "把焦急變成行動，想一次得到完整答案。"


def landmine_repair(pair_key: str) -> str:
    if pair_key == "Mercury-Mercury":
        return "先確認彼此在談同一件事，再問一個可以回答的小問題。"
    if pair_key == "Sun-Venus":
        return "把被喜歡的感覺留在當下，不急著換成關係定義。"
    if pair_key == "Venus-Mars":
        return "把火花放慢成日常互動，不用追逐感證明關係還在。"
    if pair_key == "Mercury-Sun":
        return "先說你想理解哪一件事，不用把對話變成辯論或評分。"
    if pair_key == "Sun-Mars":
        return "先停一拍再行動，不用用速度證明你很在乎。"
    if pair_key == "Moon-Venus":
        return "先用溫和日常建立安全感，不把好感立刻推成答案。"
    if pair_key == "Sun-Moon":
        return "先確認彼此聽到的是同一件事，再談感受和期待。"
    if pair_key == "Sun-Saturn":
        return "先談具體事件，不用人格評價或責任帽子壓對方。"
    if pair_key == "Moon-Saturn":
        return "先說你的感受和需要，不要求對方立刻背起全部情緒。"
    if pair_key == "Venus-Saturn":
        return "把好感留在日常互動，承諾題先拆成小而可做到的行動。"
    if pair_key == "Mars-Saturn":
        return "先約定下一步的大小和時間，不用速度證明誰比較在乎。"
    if pair_key.startswith("Mercury") or "Mercury" in pair_key:
        return "只留一個主題、一個問題，語氣先放在理解，不放在說服。"
    if pair_key == "Mars-Mars":
        return "先約定下一步的大小，不用速度證明誰比較在乎。"
    if pair_key == "Moon-Mars":
        return "先讓情緒降下來，再談具體事件，不用感受直接逼答案。"
    if "Saturn" in pair_key:
        return "把大承諾拆成小行動，看對方能不能穩定做到。"
    return "先停在可觀察行為，不用猜測對方內心。"


def survival_attraction_body(pair_key: str) -> str:
    if pair_key == "Sun-Venus":
        return "被喜歡的感覺可以留下來，但先不要把欣賞、回覆或見面推成關係定義。"
    if pair_key == "Venus-Mars":
        return "有火花時先放慢，把追逐感變成日常互動，不用用速度證明還有吸引。"
    if pair_key == "Moon-Venus":
        return "親近感出現時，先讓它變成溫和照顧，不急著用好感換保證。"
    if pair_key == "Sun-Moon":
        return "有默契時先確認彼此聽到同一件事，不把一時靠近變成情緒要求。"
    if pair_key == "Mercury-Venus":
        return "聊天變柔和時，先讓話題自然延續，不急著把語氣解讀成承諾。"
    if pair_key == "Venus-Venus":
        return "如果你們表達喜歡的方式相近，要看這份默契能不能持續出現在聊天、見面和日常關心裡。"
    if pair_key == "Moon-Moon":
        return "情緒容易互相牽動時，先讓安全感變穩，不把一次共鳴推成結果。"
    if pair_key == "Mars-Venus":
        return "吸引明顯時，先把熱度留在輕鬆互動裡，不用立刻追關係名稱。"
    if "Venus" in pair_key:
        return "好感可以被看見，但先讓它留在日常回應裡，不急著推成明確答案。"
    if "Moon" in pair_key:
        return "情緒靠近時，先看彼此能不能安穩接住，不急著把感受放大。"
    if "Mars" in pair_key:
        return "行動感被帶起來時，先把速度放慢，避免熱絡很快變成壓力。"
    return "有火花時，先讓聊天、見面或日常關心自然延續；不要把一次熱絡立刻推成關係定義。"


def survival_guide_block(
    attraction_dynamics: dict[str, Any],
    conflict_dynamics: dict[str, Any],
    growth_dynamics: dict[str, Any],
    partner_needs: dict[str, Any],
    turning_windows: dict[str, Any],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    def add(title: str, body: str, why: str, evidence_keys: list[str], source_claim_ids: list[str] | None = None) -> None:
        if any(existing.get("title") == title for existing in items):
            return
        items.append(
            {
                "title": title,
                "body": body,
                "why": why,
                "evidenceClusterKeys": evidence_keys,
                "source": RELATIONSHIP_INSIGHT_SOURCE,
                "sourceClaimIds": source_claim_ids or [],
                "methodClaimIds": RELATIONSHIP_INSIGHT_METHOD_CLAIM_IDS,
            }
        )

    attraction_item = next((item for item in attraction_dynamics.get("items") or [] if isinstance(item, dict)), {})
    conflict_item = next((item for item in conflict_dynamics.get("items") or [] if isinstance(item, dict)), {})
    partner_need = next((item for item in partner_needs.get("items") or [] if isinstance(item, dict)), {})
    growth_item = next((item for item in growth_dynamics.get("items") or [] if isinstance(item, dict)), {})
    turning_window = next((item for item in turning_windows.get("items") or [] if isinstance(item, dict)), {})

    if attraction_item:
        pair_label = pair_key_label(str(attraction_item.get("pairKey") or ""))
        pair_key = str(attraction_item.get("pairKey") or "")
        add(
            f"把「{pair_label}」當互動火花，不當關係定論",
            survival_attraction_body(pair_key),
            "吸引訊號的用途是提醒你哪裡容易靠近；真正能不能穩住，仍要看後續回應是否持續。",
            ["attractionDynamics"],
            attraction_dynamics.get("sourceClaimIds") or [],
        )
    if conflict_item:
        pair_key = str(conflict_item.get("pairKey") or "")
        title = landmine_title(pair_key, 0)
        add(
            f"先處理這個吵架地雷：{title}",
            landmine_repair(pair_key),
            "這顆地雷一出現，對話容易從理解變成互相頂住；先換成單題、短句、可停下的說法。",
            ["conflictDynamics"],
            conflict_dynamics.get("sourceClaimIds") or [],
        )
    if partner_need:
        point_label = POINT_LABELS.get(str(partner_need.get("point") or ""), str(partner_need.get("point") or "關係"))
        add(
            f"先照顧「{partner_need.get('title') or point_label}」，不要猜心",
            "把靠近方式放在他比較接得住的節奏上；先做一件小事，不追問他的內心答案。",
            "需求線索只能用來設計相處條件，不能替他宣告真正想法。",
            ["partnerNeeds"],
            partner_needs.get("sourceClaimIds") or [],
        )
    if growth_item:
        add(
            f"把「{growth_item.get('title') or '成長相位'}」變成小行動",
            "選一個接下來能做到的小行為：少一個追問、多一個明確界線，讓關係壓力有地方下降。",
            "成長線索的重點是練習新的互動方式，不是等待關係自己變好。",
            ["growthDynamics"],
            growth_dynamics.get("sourceClaimIds") or [],
        )
    if turning_window:
        add(
            f"{turning_window.get('title') or turning_window.get('windowLabel') or '行運時段'}：大問題先拆小",
            "這個區間先不把承諾、責任或復合期限一次談完；先看對方能不能做到一兩個穩定的小回應。",
            "時機線索只能說明哪段時間比較緊或比較鬆，不能當成指定日保證。",
            ["relationshipTurningWindows"],
            turning_windows.get("sourceClaimIds") or [],
        )
    add(
        "用現實回應代替猜測",
        "看對方是否穩定出現、是否能自然延續對話、是否尊重你的界線。",
        "這能避免把合盤吸引或壓力誤讀成對方內心答案。",
        ["nonfatalSynastrySafety", "contactSituationPolicy"],
    )
    return {
        "version": "survival-guide-v1",
        "label": "關係生存指南：5 個具體建議",
        "items": items[:5],
        "source": RELATIONSHIP_INSIGHT_SOURCE,
        "sourceClaimIds": relationship_insight_source_claim_ids(items),
        "methodClaimIds": relationship_insight_method_claim_ids(items),
        "evidenceClusterKeys": ["attractionDynamics", "conflictDynamics", "growthDynamics", "partnerNeeds", "relationshipTurningWindows"],
        "doesNotProve": "行動建議不能保證對方回覆或復合，只能降低無效互動和受傷風險。",
    }


def first_dict(items: Any) -> dict[str, Any]:
    return next((item for item in items or [] if isinstance(item, dict)), {})


def profile_card_for_point(profile: dict[str, Any], point: str) -> dict[str, Any]:
    return next((card for card in profile.get("cards") or [] if isinstance(card, dict) and card.get("point") == point), {})


def role_pronoun_text(text: str, role_label: str) -> str:
    text = normalize_zh_text(text)
    if role_label == "你":
        return text.replace("他的", "你的").replace("他會", "你會").replace("他在", "你在").replace("他", "你")
    if role_label in {"他", "對方"}:
        return text.replace("對方", "他")
    return text


def fit_profile_fallback_by_sign(point: str, sign_label: str, role_label: str) -> tuple[str, str]:
    depth = sign_relationship_depth(sign_label)
    if point == "Moon":
        return depth["emotionalSafety"], depth["conflictDefense"]
    if point == "Mercury":
        return depth["relationshipStyle"], depth["conflictDefense"]
    if point == "Venus":
        return depth["affectionLanguage"], depth["shutsDown"]
    if point == "Mars":
        return depth["opensUp"], depth["conflictDefense"]
    if point == "Saturn":
        return depth["commitmentPace"], depth["conflictDefense"]
    return depth["relationshipStyle"], depth["commonMisread"]


def fit_profile_basis(card: dict[str, Any], role_label: str) -> str:
    placement = str(card.get("placement") or f"{POINT_LABELS.get(str(card.get('point') or ''), '星盤功能')}")
    point = str(card.get("point") or "")
    sign_label = str(card.get("signLabel") or "")
    readable = card.get("readableInterpretation") if isinstance(card.get("readableInterpretation"), dict) else {}
    body = normalize_zh_text(
        readable.get("body")
        or card.get("naturalResponse")
        or card.get("style")
        or card.get("suitableFor")
        or ""
    )
    stuck = normalize_zh_text(
        readable.get("stuckPattern")
        or card.get("tensionPattern")
        or card.get("doesNotFit")
        or ""
    )
    body = role_pronoun_text(body, role_label)
    stuck = role_pronoun_text(stuck, role_label)
    if not body and sign_label:
        body, stuck = fit_profile_fallback_by_sign(point, sign_label, role_label)
        body = role_pronoun_text(body, role_label)
        stuck = role_pronoun_text(stuck, role_label)
    if body and stuck:
        return normalize_zh_text(f"{placement}：{body}；容易卡住在：{stuck}")
    if body:
        return normalize_zh_text(f"{placement}：{body}")
    theme = {
        "Moon": "安全感怎麼建立、壓力來時怎麼找回情緒穩定",
        "Mercury": "怎麼理解訊息、誤會後怎麼把話說回來",
        "Venus": "喜歡怎麼被靠近、愛意比較容易用什麼方式接住",
        "Mars": "靠近速度、行動衝動和吵架時的反應節奏",
        "Saturn": "遇到壓力時的防衛、界線和承諾速度",
    }.get(point, "關係裡最容易啟動的反應")
    return f"{placement}：{theme}"


RELATIONSHIP_FIT_PROFILE_REPHRASES = (
    ("溫柔但清楚的話，比逼問更能讓他開口", "語氣清楚但不逼近時，他比較容易把話接出來"),
    ("溫柔但清楚的話，比逼問更能讓你開口", "語氣清楚但不逼近時，你比較容易把話接出來"),
    ("有感覺時，通常不太想拖太久", "被火花帶動時，會比較想直接靠近"),
    ("有話直接說清楚，心才不會一直懸著", "需要看見明確回應，心裡才比較安定"),
    ("等不到明確回應時，容易把不安變成急著追問", "回應不清楚時，不安容易推高確認感"),
)


def relationship_fit_profile_basis(card: dict[str, Any], role_label: str) -> str:
    text = fit_profile_basis(card, role_label)
    for source, target in RELATIONSHIP_FIT_PROFILE_REPHRASES:
        text = text.replace(source, target)
    return normalize_zh_text(text)


def relationship_fit_best_body(item: dict[str, Any]) -> str:
    pair_key = str(item.get("pairKey") or "")
    point_a = str(item.get("personAPoint") or "")
    point_b = str(item.get("personBPoint") or "")
    points = {point_a, point_b}
    contact_type = str(item.get("contactType") or "")

    if points == {"Sun", "Mars"}:
        body = (
            "最合拍的地方，是彼此容易喚起對方的生命力和行動感。"
            "互動順的時候，不只是心裡有好感，而是比較容易出現想靠近、想回應、想一起做點什麼的動能；"
            "一句自然的邀約、一個共同任務，或把話題放回輕鬆生活，都比直接談結論更能把火花帶出來。"
        )
    elif points == {"Venus", "Mars"}:
        body = (
            "這種契合像身體感和好感同時被點到：一方的喜歡方式，容易接上另一方的行動和追求節奏。"
            "互動順時會有想靠近、想逗對方、想被對方看見的感覺；日常裡比較容易出現曖昧感、熱度和自然的身體語言。"
        )
    elif points == {"Sun", "Venus"}:
        body = (
            "契合感會表現在欣賞比較容易流動。"
            "你們比較容易在對方身上看見可愛、吸引或值得肯定的地方，日常互動裡也比較容易出現被喜歡、被看見的感覺；"
            "溫和肯定、自然聊天和生活裡的小稱讚，會比很重的表白更容易讓這份好感被看見。"
        )
    elif points == {"Moon", "Venus"}:
        body = (
            "契合感偏向情緒被照顧和好感被接住。"
            "當互動不急、不逼答案時，彼此比較容易感覺到溫柔、熟悉和願意靠近；"
            "最有用的不是大聲證明愛，而是讓對方在小細節裡感覺安全。"
        )
    elif points == {"Sun", "Moon"}:
        body = (
            "這種契合會讓一方的自我表達碰到另一方的情緒需求。"
            "狀態好的時候，容易有「我懂你在乎什麼」或「你看得見我真正的樣子」的感覺；"
            "這種熟悉感會在穩定相處、自然分享和願意聽彼此感受時慢慢浮出來。"
        )
    elif points == {"Moon"}:
        body = (
            "契合感主要落在情緒節奏。"
            "你們比較容易在脆弱、想被安撫或需要陪伴的時候碰到彼此的感受；"
            "如果語氣放輕，這會變成熟悉感，如果語氣變急，也可能很快變成敏感。"
        )
    elif "Mercury" in points:
        body = (
            "契合感會透過說話方式被看見。"
            "當對話不是審問，而是能讓彼此有台階、有回應空間時，話題比較容易接上，誤會也比較有機會被說開；"
            "所以它最適合用短、清楚、可回可不回的訊息來啟動。"
        )
    else:
        label = pair_key_label(pair_key)
        body = (
            f"契合感來自 {label} 這組功能比較容易接上。"
            "它不是抽象的好感，而是會在日常互動裡變成某種比較自然的反應：比較願意看見、靠近、回應或延續。"
        )

    if contact_type == "soft":
        body += "因為這是比較柔和的接觸，優勢在於自然帶動，不需要用很重的方式證明。"
    elif contact_type == "hard":
        body += "這份互動帶一點張力，契合會更有存在感，也更容易讓彼此記住對方的反應。"
    return normalize_zh_text(body)


def fit_lens_rating_label(value: float, *, pressure: bool = False) -> str:
    if value >= 78:
        return "高"
    if value >= 64:
        return "中高"
    if value >= 48:
        return "中低"
    return "低"


def dynamics_strength(block: dict[str, Any]) -> float:
    items = [item for item in block.get("items") or [] if isinstance(item, dict)]
    if not items:
        return 0.0
    return sum(float(item.get("strength") or 0.45) for item in items) / len(items)


def relationship_fit_radar_item(
    *,
    key: str,
    label: str,
    value: float,
    because_a: str,
    because_b: str,
    proof: str,
    pressure: bool = False,
    source_claim_ids: list[str] | None = None,
    method_claim_ids: list[str] | None = None,
    evidence_cluster_keys: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "rating": fit_lens_rating_label(value, pressure=pressure),
        "value": int(round(clamp_score(value, 0, 100))),
        "becauseA": because_a,
        "becauseB": because_b,
        "proof": proof,
        "reason": normalize_zh_text(f"因為{because_a}；同時{because_b}。合盤證據是：{proof}"),
        "sourceClaimIds": source_claim_ids or [],
        "methodClaimIds": method_claim_ids or RELATIONSHIP_INSIGHT_METHOD_CLAIM_IDS,
        "evidenceClusterKeys": evidence_cluster_keys or [],
    }


def relationship_fit_best_points(
    relationship_profiles: dict[str, Any],
    attraction_dynamics: dict[str, Any],
) -> list[dict[str, Any]]:
    person_a = relationship_profiles.get("personA") or {}
    person_b = relationship_profiles.get("personB") or {}
    a_venus = profile_card_for_point(person_a, "Venus")
    b_venus = profile_card_for_point(person_b, "Venus")
    a_moon = profile_card_for_point(person_a, "Moon")
    b_moon = profile_card_for_point(person_b, "Moon")
    items = [item for item in attraction_dynamics.get("items") or [] if isinstance(item, dict)]
    output: list[dict[str, Any]] = []
    if items:
        first = items[0]
        output.append(
            {
                "title": "火花容易先被點起來",
                "becauseA": relationship_fit_profile_basis(a_venus or a_moon, "你"),
                "becauseB": relationship_fit_profile_basis(b_venus or b_moon, "他"),
                "proof": str(first.get("technical") or first.get("title") or ""),
                "body": relationship_fit_best_body(first),
                "sourceClaimIds": first.get("sourceClaimIds") or [],
                "methodClaimIds": first.get("methodClaimIds") or [],
                "evidenceClusterKeys": ["relationshipProfiles", "attractionDynamics"],
            }
        )
    second = items[1] if len(items) > 1 else {}
    if second:
        output.append(
            {
                "title": "好感可以從日常互動延續",
                "becauseA": relationship_fit_profile_basis(a_moon or a_venus, "你"),
                "becauseB": relationship_fit_profile_basis(b_moon or b_venus, "他"),
                "proof": str(second.get("technical") or second.get("title") or ""),
                "body": relationship_fit_best_body(second),
                "sourceClaimIds": second.get("sourceClaimIds") or [],
                "methodClaimIds": second.get("methodClaimIds") or [],
                "evidenceClusterKeys": ["relationshipProfiles", "attractionDynamics"],
            }
        )
    fit_natural = first_dict(((relationship_profiles.get("fitSummary") or {}).get("natural") or []))
    if fit_natural:
        output.append(
            {
                "title": "有一個比較容易接上彼此的位置",
                "becauseA": str(fit_natural.get("personA") or relationship_fit_profile_basis(a_moon, "你")),
                "becauseB": str(fit_natural.get("personB") or relationship_fit_profile_basis(b_moon, "他")),
                "proof": str(fit_natural.get("title") or "星盤定位顯示有自然牽動"),
                "body": normalize_zh_text(str(fit_natural.get("body") or fit_natural.get("nextMove") or "")),
                "sourceClaimIds": fit_natural.get("sourceClaimIds") or fit_natural.get("claimIds") or [],
                "methodClaimIds": fit_natural.get("methodClaimIds") or [],
                "evidenceClusterKeys": ["relationshipProfiles"],
            }
        )
    return output[:3]


def relationship_fit_stuck_loop(
    relationship_profiles: dict[str, Any],
    conflict_dynamics: dict[str, Any],
    fight_landmines: dict[str, Any],
) -> dict[str, Any]:
    person_a = relationship_profiles.get("personA") or {}
    person_b = relationship_profiles.get("personB") or {}
    a_moon = profile_card_for_point(person_a, "Moon")
    a_mercury = profile_card_for_point(person_a, "Mercury")
    b_moon = profile_card_for_point(person_b, "Moon")
    b_saturn = profile_card_for_point(person_b, "Saturn")
    conflict = first_dict(conflict_dynamics.get("items") or [])
    landmine = first_dict(fight_landmines.get("items") or [])
    title = str(landmine.get("title") or conflict.get("title") or "一靠近就容易變急")
    trigger = "互動內容一變長、變成要立刻表態時，兩邊容易從在乎轉成防衛。"
    interrupt = "中斷方式不是補更多解釋，而是把主題縮到一件可以回答的事，讓語氣先回到理解。"
    steps = [
        {"label": "你的起點", "body": f"{relationship_fit_profile_basis(a_moon or a_mercury, '你')}，不安時會先想看見比較明確的回應。"},
        {"label": "他的起點", "body": f"{relationship_fit_profile_basis(b_moon or b_saturn, '他')}，壓力變高時需要先保住能接話的空間。"},
        {"label": "互相誤會", "body": normalize_zh_text(trigger or "你越想確認，他越容易感覺被推；他越慢，你越容易更不安。")},
        {"label": "怎麼升級", "body": normalize_zh_text(str(conflict.get("everydaySignal") or "一句話如果變成攻防，關係就會從在乎變成互相防衛。"))},
        {"label": "怎麼中斷", "body": normalize_zh_text(interrupt)},
    ]
    return {
        "title": title,
        "summary": normalize_zh_text(f"這個循環不是誰比較有問題，而是{relationship_fit_profile_basis(a_moon or a_mercury, '你')}，同時{relationship_fit_profile_basis(b_moon or b_saturn, '他')}，一急就容易互相推高壓力。"),
        "steps": steps,
        "sourceClaimIds": unique([*(conflict.get("sourceClaimIds") or []), *(landmine.get("sourceClaimIds") or [])]),
        "methodClaimIds": unique([*(conflict.get("methodClaimIds") or []), *(landmine.get("methodClaimIds") or [])]),
        "evidenceClusterKeys": ["relationshipProfiles", "conflictDynamics", "fightLandmines"],
    }


def relationship_fit_conditions(
    growth_dynamics: dict[str, Any],
    conflict_dynamics: dict[str, Any],
    survival_guide: dict[str, Any],
    action_guidance: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    growth = first_dict(growth_dynamics.get("items") or [])
    conflict = first_dict(conflict_dynamics.get("items") or [])
    survival_items = [item for item in survival_guide.get("items") or [] if isinstance(item, dict)]
    first_survival = first_dict(survival_items)
    action_guidance = action_guidance or {}
    return [
        {
            "label": "比較有機會穩下來",
            "body": normalize_zh_text(str(growth.get("advice") or first_survival.get("body") or "把期待拆成小而可執行的行動，先看能不能穩定接上。")),
            "watchFor": "對話能自然延伸，回應變穩，而且不用一直靠追問維持連結。",
            "evidenceClusterKeys": ["growthDynamics", "survivalGuide"],
        },
        {
            "label": "會繼續消耗的狀態",
            "body": normalize_zh_text(str(conflict.get("everydaySignal") or conflict.get("meaning") or "每次靠近都變成攻防、催促或責任檢查。")),
            "watchFor": "互動之後你更焦慮，對方更防衛，下一次又回到同一個循環。",
            "evidenceClusterKeys": ["conflictDynamics", "fightLandmines"],
        },
        {
            "label": "值得再觀察的跡象",
            "body": "對方不只回覆，還願意補充、延伸、安排或把語氣放柔。",
            "watchFor": "看三次互動是否越來越穩，不用只看一次已讀或一次熱絡。",
            "evidenceClusterKeys": ["contactSituationPolicy", "relationshipProfiles"],
        },
        {
            "label": "需要保護自己的跡象",
            "body": "如果對話需要靠你一直補訊息才維持，就先把自己抽回來，看對方是否也有主動接住。",
            "watchFor": "你已經需要犧牲睡眠、尊嚴或界線，才換到一點點回應。",
            "evidenceClusterKeys": ["actionGuidance", "contactSituationPolicy"],
        },
    ]


def baseline_field_text(baseline: dict[str, Any], field: str, fallback: str) -> str:
    return normalize_zh_text(str(baseline.get(field) or fallback))


def relationship_fit_side_note(
    baseline_a: dict[str, Any],
    baseline_b: dict[str, Any],
    conflict_item: dict[str, Any],
) -> str:
    user_need = baseline_field_text(baseline_a, "emotionalNeed", "你需要先感覺關係有穩定回應。")
    partner_response = baseline_field_text(baseline_b, "conflictResponse", "他在緊張時會先保護自己的回應空間。")
    conflict_signal = normalize_zh_text(str(conflict_item.get("everydaySignal") or conflict_item.get("meaning") or "同一句話在壓力下容易變成互相防備。"))
    return normalize_zh_text(
        f"合拍和卡點要一起看：{user_need}；同時{partner_response}。合盤卡點顯示，{conflict_signal}"
    )


def relationship_fit_lens(
    relationship_profiles: dict[str, Any],
    relationship_archetype: dict[str, Any],
    attraction_dynamics: dict[str, Any],
    conflict_dynamics: dict[str, Any],
    growth_dynamics: dict[str, Any],
    partner_needs: dict[str, Any],
    fight_landmines: dict[str, Any],
    survival_guide: dict[str, Any],
    action_guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    person_a = relationship_profiles.get("personA") or {}
    person_b = relationship_profiles.get("personB") or {}
    a_moon = profile_card_for_point(person_a, "Moon")
    b_moon = profile_card_for_point(person_b, "Moon")
    a_mercury = profile_card_for_point(person_a, "Mercury")
    b_mercury = profile_card_for_point(person_b, "Mercury")
    a_venus = profile_card_for_point(person_a, "Venus")
    b_venus = profile_card_for_point(person_b, "Venus")
    translation_baseline = relationship_profiles.get("translationBaseline") or {}
    baseline_a = translation_baseline.get("personA") or person_a.get("translationBaseline") or {}
    baseline_b = translation_baseline.get("personB") or person_b.get("translationBaseline") or {}
    fit_summary = relationship_profiles.get("fitSummary") or {}
    natural_count = len(fit_summary.get("natural") or [])
    effort_count = len(fit_summary.get("effort") or [])
    friction_count = len(fit_summary.get("friction") or [])
    attraction_strength = dynamics_strength(attraction_dynamics)
    conflict_strength = dynamics_strength(conflict_dynamics)
    growth_strength = dynamics_strength(growth_dynamics)
    attraction_item = first_dict(attraction_dynamics.get("items") or [])
    conflict_item = first_dict(conflict_dynamics.get("items") or [])
    growth_item = first_dict(growth_dynamics.get("items") or [])
    pressure_value = 42 + conflict_strength * 42 + friction_count * 4
    radar = [
        relationship_fit_radar_item(
            key="attraction",
            label="吸引力",
            value=55 + attraction_strength * 34 + len(attraction_dynamics.get("items") or []) * 3,
            because_a=relationship_fit_profile_basis(a_venus or a_moon, "你"),
            because_b=relationship_fit_profile_basis(b_venus or b_moon, "他"),
            proof=str(attraction_item.get("technical") or attraction_dynamics.get("summary") or ""),
            source_claim_ids=attraction_dynamics.get("sourceClaimIds") or [],
            method_claim_ids=attraction_dynamics.get("methodClaimIds") or [],
            evidence_cluster_keys=["relationshipProfiles", "attractionDynamics"],
        ),
        relationship_fit_radar_item(
            key="emotionalSafety",
            label="情緒安全",
            value=50 + natural_count * 6 + (1 if partner_needs.get("items") else 0) * 8 - friction_count * 3,
            because_a=relationship_fit_profile_basis(a_moon, "你"),
            because_b=relationship_fit_profile_basis(b_moon, "他"),
            proof="安全感需要空間、真話和穩定回應一起累積，不能只靠一次追問確認。",
            source_claim_ids=partner_needs.get("sourceClaimIds") or [],
            method_claim_ids=partner_needs.get("methodClaimIds") or [],
            evidence_cluster_keys=["relationshipProfiles", "partnerNeeds"],
        ),
        relationship_fit_radar_item(
            key="communicationStability",
            label="溝通穩定",
            value=62 + effort_count * 4 + growth_strength * 10 - conflict_strength * 28,
            because_a=relationship_fit_profile_basis(a_mercury, "你"),
            because_b=relationship_fit_profile_basis(b_mercury, "他"),
            proof=str(conflict_item.get("technical") or conflict_dynamics.get("summary") or ""),
            source_claim_ids=conflict_dynamics.get("sourceClaimIds") or [],
            method_claim_ids=conflict_dynamics.get("methodClaimIds") or [],
            evidence_cluster_keys=["relationshipProfiles", "conflictDynamics"],
        ),
        relationship_fit_radar_item(
            key="conflictPressure",
            label="衝突壓力",
            value=pressure_value,
            because_a=relationship_fit_profile_basis(a_mercury or a_moon, "你"),
            because_b=relationship_fit_profile_basis(b_mercury or b_moon, "他"),
            proof=str(conflict_item.get("meaning") or conflict_item.get("technical") or ""),
            pressure=True,
            source_claim_ids=conflict_dynamics.get("sourceClaimIds") or [],
            method_claim_ids=conflict_dynamics.get("methodClaimIds") or [],
            evidence_cluster_keys=["relationshipProfiles", "conflictDynamics"],
        ),
        relationship_fit_radar_item(
            key="repairPotential",
            label="修復潛力",
            value=52 + growth_strength * 24 + natural_count * 3 - max(conflict_strength - 0.55, 0) * 16,
            because_a=relationship_fit_profile_basis(a_mercury or a_venus, "你"),
            because_b=relationship_fit_profile_basis(b_mercury or b_venus, "他"),
            proof=str(growth_item.get("technical") or growth_item.get("meaning") or first_dict(survival_guide.get("items") or []).get("body") or ""),
            source_claim_ids=growth_dynamics.get("sourceClaimIds") or survival_guide.get("sourceClaimIds") or [],
            method_claim_ids=growth_dynamics.get("methodClaimIds") or survival_guide.get("methodClaimIds") or [],
            evidence_cluster_keys=["relationshipProfiles", "growthDynamics", "survivalGuide"],
        ),
        relationship_fit_radar_item(
            key="longTermAdjustment",
            label="長期磨合度",
            value=55 + natural_count * 4 + growth_strength * 14 - conflict_strength * 16,
            because_a=relationship_fit_profile_basis(a_moon or a_venus, "你"),
            because_b=relationship_fit_profile_basis(b_moon or b_venus, "他"),
            proof=str(relationship_archetype.get("meaning") or fit_summary.get("summary") or ""),
            source_claim_ids=relationship_archetype.get("sourceClaimIds") or [],
            method_claim_ids=relationship_archetype.get("methodClaimIds") or [],
            evidence_cluster_keys=["relationshipArchetype", "relationshipProfiles", "growthDynamics", "conflictDynamics"],
        ),
    ]
    best_points = relationship_fit_best_points(relationship_profiles, attraction_dynamics)
    stuck_loop = relationship_fit_stuck_loop(relationship_profiles, conflict_dynamics, fight_landmines)
    conditions = relationship_fit_conditions(growth_dynamics, conflict_dynamics, survival_guide, action_guidance)
    all_blocks = [
        relationship_archetype,
        attraction_dynamics,
        conflict_dynamics,
        growth_dynamics,
        partner_needs,
        fight_landmines,
        survival_guide,
    ]
    return {
        "version": "relationship-fit-lens-v1",
        "relationshipType": {
            "title": str(relationship_archetype.get("title") or "需要觀察的關係型"),
            "subtitle": str(relationship_archetype.get("subtitle") or ""),
            "meaning": str(relationship_archetype.get("meaning") or fit_summary.get("summary") or ""),
            "reasons": (relationship_archetype.get("whySelected") or [])[:3],
            "becauseA": baseline_field_text(baseline_a, "emotionalNeed", fit_profile_basis(a_moon or a_venus, "你")),
            "becauseB": baseline_field_text(baseline_b, "conflictResponse", fit_profile_basis(b_moon or b_venus, "他")),
            "sideNote": relationship_fit_side_note(baseline_a, baseline_b, conflict_item),
            "doesNotProve": str(relationship_archetype.get("doesNotProve") or "關係類型不是命定結論。"),
        },
        "radar": radar,
        "bestPlaces": best_points,
        "stuckLoop": stuck_loop,
        "conditions": conditions,
        "summary": normalize_zh_text(
            f"先用星盤定位看兩個人怎麼愛、怎麼退，再用合盤相位確認吸引從哪裡來、卡點會怎麼發生、修復要靠什麼條件。{relationship_archetype.get('meaning') or ''}"
        ),
        "sourceClaimIds": unique([claim_id for block in all_blocks for claim_id in block.get("sourceClaimIds") or []]),
        "methodClaimIds": unique([claim_id for block in all_blocks for claim_id in block.get("methodClaimIds") or []]),
        "evidenceClusterKeys": unique(
            [
                "relationshipProfiles",
                "relationshipArchetype",
                "attractionDynamics",
                "conflictDynamics",
                "growthDynamics",
                "partnerNeeds",
                "fightLandmines",
                "survivalGuide",
            ]
        ),
        "doesNotProve": "契合雷達與關係類型只說明互動條件，不能保證承諾、復合或長久結果。",
    }


def month_period_label(raw_date: Any) -> str:
    value = str(raw_date or "")
    parts = value.split("-")
    if len(parts) < 3:
        return ""
    try:
        month = int(parts[1])
        day = int(parts[2])
    except ValueError:
        return ""
    if day <= 10:
        period = "上旬"
    elif day <= 20:
        period = "中旬"
    else:
        period = "下旬"
    return f"{month} 月{period}"


def timing_period_range_label(start_date: Any, end_date: Any, fallback_year: str) -> str:
    start = str(start_date or "")
    end = str(end_date or "")
    start_year = start[:4] if len(start) >= 4 else fallback_year
    end_year = end[:4] if len(end) >= 4 else start_year
    start_label = month_period_label(start)
    end_label = month_period_label(end)
    if not start_label and not end_label:
        return f"{fallback_year} 年時段未定"
    if not end_label or start_label == end_label:
        return f"{start_year} 年 {start_label or end_label}"
    if start_year == end_year:
        return f"{start_year} 年 {start_label}到 {end_label}"
    return f"{start_year} 年 {start_label}到 {end_year} 年 {end_label}"


def turning_window_categories(kind: str) -> set[str]:
    return {
        "communication_window": {"communication_window"},
        "communication_pressure": {"communication_pressure"},
        "softening": {"softening", "relationship_focus"},
        "activation": {"activation_pressure"},
        "boundary": {"pressure"},
        "emotion": {"emotional_weather"},
        "background": {"background"},
    }.get(kind, {"background"})


def turning_window_period_label(scan: dict[str, Any], kind: str, year: str, fallback_date: Any = None) -> str:
    categories = turning_window_categories(kind)
    day_summaries = [item for item in scan.get("day_summaries") or [] if isinstance(item, dict)]
    matched_dates = [
        str(item.get("date") or "")
        for item in day_summaries
        if str(item.get("strongest_category") or "background") in categories and item.get("date")
    ]
    if matched_dates:
        matched_dates = sorted(matched_dates)
        return timing_period_range_label(matched_dates[0], matched_dates[-1], year)
    windows = [item for item in scan.get("windows") or [] if isinstance(item, dict)]
    for window in windows:
        dominant = {str(item) for item in window.get("dominant_categories") or []}
        if dominant.intersection(categories):
            return timing_period_range_label(window.get("start_date"), window.get("end_date"), year)
    fallback_label = timing_period_range_label(fallback_date, fallback_date, year) if fallback_date else ""
    if fallback_label and "時段未定" not in fallback_label:
        return fallback_label
    return f"{year} 年時段未定"


def turning_window_period_candidates(
    scan: dict[str, Any],
    kind: str,
    year: str,
    fallback_date: Any = None,
) -> list[dict[str, Any]]:
    categories = turning_window_categories(kind)
    day_summaries = [item for item in scan.get("day_summaries") or [] if isinstance(item, dict)]
    grouped: dict[str, dict[str, Any]] = {}
    for summary in day_summaries:
        category = str(summary.get("strongest_category") or "background")
        date = str(summary.get("date") or "")
        if category not in categories or not date:
            continue
        label = timing_period_range_label(date, date, year)
        group = grouped.setdefault(
            label,
            {
                "periodLabel": label,
                "startDate": date,
                "endDate": date,
                "sampleCount": 0,
                "score": 0.0,
                "maxScore": 0.0,
            },
        )
        group["startDate"] = min(str(group["startDate"]), date)
        group["endDate"] = max(str(group["endDate"]), date)
        group["sampleCount"] = int(group.get("sampleCount") or 0) + 1
        components = summary.get("score_components") if isinstance(summary.get("score_components"), dict) else {}
        raw_score = float(summary.get("score") or 0)
        if kind in {"activation", "boundary", "communication_pressure"}:
            score = float(components.get("avoid") or max(0.0, -raw_score))
        else:
            score = float(components.get("better") or max(0.0, raw_score))
        group["score"] = float(group.get("score") or 0) + score
        group["maxScore"] = max(float(group.get("maxScore") or 0), score)
    if grouped:
        return sorted(
            grouped.values(),
            key=lambda item: (
                float(item.get("maxScore") or 0),
                float(item.get("score") or 0),
                int(item.get("sampleCount") or 0),
                str(item.get("startDate") or ""),
            ),
            reverse=True,
        )

    windows = [item for item in scan.get("windows") or [] if isinstance(item, dict)]
    candidates: list[dict[str, Any]] = []
    for window in windows:
        dominant = {str(item) for item in window.get("dominant_categories") or []}
        if not dominant.intersection(categories):
            continue
        start_date = str(window.get("start_date") or "")
        end_date = str(window.get("end_date") or start_date)
        if not start_date:
            continue
        candidates.append(
            {
                "periodLabel": timing_period_range_label(start_date, end_date, year),
                "startDate": start_date,
                "endDate": end_date,
                "sampleCount": int(window.get("sample_count") or 0),
                "score": abs(float(window.get("max_score") or 0)),
                "maxScore": abs(float(window.get("max_score") or 0)),
            }
        )
    if candidates:
        return sorted(
            candidates,
            key=lambda item: (
                float(item.get("maxScore") or 0),
                int(item.get("sampleCount") or 0),
                str(item.get("startDate") or ""),
            ),
            reverse=True,
        )

    fallback_label = timing_period_range_label(fallback_date, fallback_date, year) if fallback_date else ""
    if fallback_label and "時段未定" not in fallback_label:
        fallback = str(fallback_date or "")
        return [
            {
                "periodLabel": fallback_label,
                "startDate": fallback,
                "endDate": fallback,
                "sampleCount": 1,
                "score": 0.0,
                "maxScore": 0.0,
            }
        ]
    return []


def turning_window_periods_overlap(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if str(first.get("periodLabel") or "") == str(second.get("periodLabel") or ""):
        return True
    first_start = str(first.get("startDate") or "")
    first_end = str(first.get("endDate") or first_start)
    second_start = str(second.get("startDate") or "")
    second_end = str(second.get("endDate") or second_start)
    if not first_start or not first_end or not second_start or not second_end:
        return False
    return not (first_end < second_start or second_end < first_start)


def force_turning_window_title(item: dict[str, Any], title: str) -> dict[str, Any]:
    output = dict(item)
    output["title"] = title
    output["categoryLabel"] = title
    return output


def relationship_turning_windows_block(fixture: dict[str, Any], evidence_clusters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    timing_profile = western_timing_profile(fixture)
    target_date = str(timing_profile.get("target_date") or "")
    year = target_date[:4] if target_date else "2026"
    scan = western_timing_window_scan(fixture)
    triggers = [
        item
        for item in timing_profile.get("relationship_triggers") or []
        if isinstance(item, dict) and item.get("eligible_for_timing", True)
    ]
    triggers = sorted(triggers, key=lambda item: float(item.get("timing_strength") or 0), reverse=True)
    candidates: dict[str, list[dict[str, Any]]] = {"soft": [], "tension": []}
    seen_candidate_keys: set[tuple[str, str, str]] = set()
    for trigger in triggers:
        category = str(trigger.get("category") or "background")
        kind = turning_window_kind(category)
        if kind in {"softening", "communication_window"}:
            slot = "soft"
            title = "關係氣氛比較柔和"
        elif kind in {"activation", "boundary", "communication_pressure"}:
            slot = "tension"
            title = "容易擦槍走火的時段"
        else:
            continue
        fallback_date = trigger.get("target_date") or trigger.get("date") or trigger.get("analysis_date") or target_date
        for period in turning_window_period_candidates(scan, kind, year, fallback_date=fallback_date):
            candidate_key = (slot, kind, str(period.get("periodLabel") or ""))
            if candidate_key in seen_candidate_keys:
                continue
            seen_candidate_keys.add(candidate_key)
            item = turning_window_item(trigger, kind, year, scan, fallback_date=fallback_date, period_range=period)
            item = force_turning_window_title(item, title)
            candidate = {
                "kind": kind,
                "slot": slot,
                "item": item,
                "periodLabel": str(period.get("periodLabel") or ""),
                "startDate": str(period.get("startDate") or ""),
                "endDate": str(period.get("endDate") or ""),
                "score": float(trigger.get("timing_strength") or 0) + float(period.get("maxScore") or 0) / 10,
            }
            candidates[slot].append(candidate)

    for slot in candidates:
        candidates[slot] = sorted(
            candidates[slot],
            key=lambda candidate: (
                float(candidate.get("score") or 0),
                str(candidate.get("startDate") or ""),
            ),
            reverse=True,
        )

    selected_soft = candidates["soft"][0] if candidates["soft"] else None
    selected_tension = candidates["tension"][0] if candidates["tension"] else None
    if candidates["soft"] and candidates["tension"]:
        non_overlapping_pairs = [
            (soft, tension)
            for soft in candidates["soft"]
            for tension in candidates["tension"]
            if not turning_window_periods_overlap(soft, tension)
        ]
        if non_overlapping_pairs:
            selected_soft, selected_tension = max(
                non_overlapping_pairs,
                key=lambda pair: (
                    float(pair[0].get("score") or 0) + float(pair[1].get("score") or 0),
                    min(float(pair[0].get("score") or 0), float(pair[1].get("score") or 0)),
                    str(pair[0].get("startDate") or ""),
                    str(pair[1].get("startDate") or ""),
                ),
            )
        elif selected_soft and selected_tension and turning_window_periods_overlap(selected_soft, selected_tension):
            soft_score = float(selected_soft.get("score") or 0)
            tension_score = float(selected_tension.get("score") or 0)
            if tension_score >= soft_score:
                selected_soft = None
            else:
                selected_tension = None

    items: list[dict[str, Any]] = [
        candidate["item"]
        for candidate in (selected_soft, selected_tension)
        if isinstance(candidate, dict) and isinstance(candidate.get("item"), dict)
    ]
    timing_contact = evidence_clusters.get("timingContactReducer") or {}
    if not items and timing_contact.get("recommendedAction") == "not_calculated":
        items.append(
            {
                "title": f"{year} 年互動時機資料不足",
                "windowLabel": "只保留節奏判斷",
                "periodLabel": timing_period_range_label(target_date, target_date, year) if target_date else f"{year} 年時段未定",
                "categoryLabel": "資料不足",
                "technical": "目前沒有足夠未來三個月 timing scan；只保留整體互動節奏。",
                "meaning": "目前只能用合盤壓力、當下行運氣候和現實聯絡狀態做保守判讀。",
                "suggestion": "先不要把任何一天當成唯一機會，改看對方是否有穩定、自然、可延續的回應。",
                "whatToAvoid": "避免把沒有 timing 資料硬寫成單一轉折點。",
                "source": "western-transits-timing-selector-windows",
                "sourceClaimIds": [],
                "methodClaimIds": ["hand-transits-timing-climate-not-guarantee"],
                "evidenceClusterKeys": ["timingContactReducer"],
            }
        )
    source_claim_ids = unique(
        [
            *[str(claim_id) for claim_id in (evidence_clusters.get("timingContactReducer") or {}).get("claimIds") or [] if claim_id],
            *[str(claim_id) for claim_id in (evidence_clusters.get("timingWindowBand") or {}).get("claimIds") or [] if claim_id],
        ]
    )
    return {
        "version": "relationship-turning-windows-v1",
        "label": f"{year} 年關係重要轉折氣候",
        "saferLabel": f"{year} 年比較需要留意的互動時段",
        "precision": "climate_window_not_exact_date",
        "preciseDatesAvailable": False,
        "summary": "月旬區間可以顯示互動比較緊或比較鬆的時段。",
        "items": items,
        "source": "western-transits-timing-selector-windows",
        "sourceClaimIds": source_claim_ids,
        "methodClaimIds": [
            "hand-transits-timing-climate-not-guarantee",
            "hand-transits-mercury-communication-window",
            "hand-transits-venus-softening-window",
            "hand-transits-mars-activation-caution",
            "hand-transits-saturn-boundary-pressure",
        ],
        "evidenceClusterKeys": [
            "timingWindowBand",
            "timingContactReducer",
            "timingMercuryCommunication",
            "timingVenusSoftening",
            "timingMarsActivation",
            "timingSaturnPressure",
            "timingMoonWeather",
        ],
        "doesNotProve": "行運時段不能保證聯絡、復合、承諾或對方內心變化。",
    }


def turning_window_kind(category: str) -> str:
    if category == "communication_window":
        return "communication_window"
    if category == "communication_pressure":
        return "communication_pressure"
    if category in {"softening", "relationship_focus"}:
        return "softening"
    if category == "activation_pressure":
        return "activation"
    if category == "pressure":
        return "boundary"
    if category == "emotional_weather":
        return "emotion"
    return "background"


def communication_window_detail(trigger: dict[str, Any]) -> dict[str, str]:
    natal_point = str(trigger.get("natal_point") or "")
    if natal_point == "Moon":
        return {
            "title": "比較適合溫和開口的時段",
            "meaning": "這段時間比較適合用一則有溫度、但不要求答案的訊息打開互動。重點放在讓情緒先鬆一點：問候近況、提到一個共同記憶，或用很輕的方式表示你想起他。",
            "suggestion": "可以選一個你們真的有感覺的小事，例如「剛想起上次你說的那件事，想問你最近還好嗎？」送出後看三個訊號：他有沒有自然接話、語氣有沒有放鬆、會不會願意多說一點。",
            "whatToAvoid": "避免一開口就問感情答案、要求安撫，或把所有委屈一次倒出來。",
        }
    if natal_point == "Mercury":
        return {
            "title": "比較適合把話說清楚的時段",
            "meaning": "這段時間比較適合處理一件簡單、具體、容易回答的事情。重點放在讓訊息清楚、不拐彎：少解釋動機，直接說你想確認什麼。",
            "suggestion": "可以用「我想確認一件小事，方便時回我就好」這種句型。送出後看三個訊號：他有沒有正面回答、會不會補充細節、對話是否能自然延續。",
            "whatToAvoid": "避免長篇解釋、反覆補充、用暗示測試對方到底在不在乎。",
        }
    return {
        "title": "比較適合開口的時段",
        "meaning": "這段時間比較適合用一則短訊息打開互動。重點放在先恢復對話感：問一件容易回答的小事、分享一個自然近況，或確認一個不帶壓力的安排。",
        "suggestion": "可以選一個你們真的聊過的小事，例如「剛看到你之前提過的那家店，想到你，想問你最近還好嗎？」送出後看三個訊號：他有沒有自然接話、語氣有沒有放鬆、會不會主動延伸下一句。",
        "whatToAvoid": "避免告白式長文、連續追問、翻舊帳，或把「你到底怎麼想」放在第一句。",
    }


def turning_window_item(
    trigger: dict[str, Any],
    kind: str,
    year: str,
    scan: dict[str, Any] | None = None,
    fallback_date: Any = None,
    period_range: dict[str, Any] | None = None,
) -> dict[str, Any]:
    period_range = period_range or {}
    period_label = str(period_range.get("periodLabel") or "") or turning_window_period_label(
        scan or {},
        kind,
        year,
        trigger.get("target_date") or trigger.get("date") or trigger.get("analysis_date") or fallback_date,
    )
    title_base_map = {
        "communication_window": "比較適合開口的時段",
        "communication_pressure": "溝通先放慢的時段",
        "softening": "關係氣氛比較柔和",
        "activation": "容易擦槍走火的時段",
        "boundary": "承諾與責任壓力期",
        "emotion": "情緒反應起伏期",
        "background": "整體節奏觀察期",
    }
    meaning_map = {
        "communication_window": "這段時間比較適合用一則短訊息打開互動。重點放在先恢復對話感：問一件容易回答的小事、分享一個自然近況，或確認一個不帶壓力的安排。",
        "communication_pressure": "這段時間對話容易被語氣或細節放大；仍然可以說話，但越需要答案，越要把問題縮小。",
        "softening": "這段時間比較容易想起好感、在意或被看見的需求；可以釋放善意，但還不能把氣氛直接當成復合答案。",
        "activation": "這段時間反應容易變急，越想證明在乎，越可能讓對話變成催促或對抗。",
        "boundary": "一談到關係定位、承諾或距離，對方可能會先慢下來；這不一定是不在意，而是現在還接不住太重的話題。",
        "emotion": "這段時間情緒比較容易被帶起來；感受是真實的，但不適合在情緒最高點做關係決定。",
        "background": "這段時間適合看關係有沒有回到日常流動：回覆是否變穩、約見面是否有實際安排、語氣是否比前一段時間柔和。",
    }
    avoid_map = {
        "communication_window": "避免告白式長文、連續追問、翻舊帳，或把「你到底怎麼想」放在第一句。",
        "communication_pressure": "避免在這種氣候下討論承諾、責任、復合期限或翻舊帳。",
        "softening": "避免把柔和氣氛直接當成復合保證。",
        "activation": "避免用衝動訊息、質問或硬碰硬推進。",
        "boundary": "避免要求對方立刻給答案、承諾或承擔整段關係。",
        "emotion": "避免在情緒被點燃的當下做重大決定。",
        "background": "避免因為一兩次互動變好就立刻談承諾，也避免因為一兩次慢回就直接判定沒機會。",
    }
    suggestion_map = {
        "communication_window": "可以選一個你們真的聊過的小事，例如「剛看到你之前提過的那家店，想到你，想問你最近還好嗎？」送出後看三個訊號：他有沒有自然接話、語氣有沒有放鬆、會不會主動延伸下一句。",
        "communication_pressure": "如果一定要談，只談一件具體事，先不要要求對方立刻表態。",
        "softening": "適合釋放善意、日常關心或溫和修復，不適合逼問結果。",
        "activation": "先降火，不要用行動證明在乎；等刺激下降再談。",
        "boundary": "先把大問題拆小，改看對方是否能做出穩定的小回應。",
        "emotion": "先照顧感受，等情緒穩了再談具體事情。",
        "background": "把觀察放在兩件事：對方有沒有穩定接話，以及有沒有把互動落到具體安排。"
    }
    source_claim_ids = []
    category = str(trigger.get("category") or "")
    for config_category, config in TIMING_CONTACT_REDUCER_CONFIG.items():
        if category == config_category:
            source_claim_ids.append(str(config.get("sourceClaimId") or ""))
    title = title_base_map.get(kind, title_base_map["background"])
    meaning = meaning_map.get(kind, meaning_map["background"])
    suggestion = suggestion_map.get(kind, suggestion_map["background"])
    what_to_avoid = avoid_map.get(kind, avoid_map["background"])
    if kind == "communication_window":
        communication_detail = communication_window_detail(trigger)
        title = communication_detail["title"]
        meaning = communication_detail["meaning"]
        suggestion = communication_detail["suggestion"]
        what_to_avoid = communication_detail["whatToAvoid"]
    return {
        "title": title,
        "windowLabel": period_label,
        "periodLabel": period_label,
        "categoryLabel": "整體節奏" if str(trigger.get("category_label") or "") == "背景行運" else str(trigger.get("category_label") or title_base_map.get(kind, "")),
        "technical": str(trigger.get("technical_summary") or ""),
        "meaning": meaning,
        "suggestion": suggestion,
        "whatToAvoid": what_to_avoid,
        "transitPoint": str(trigger.get("transit_point") or ""),
        "natalPoint": str(trigger.get("natal_point") or ""),
        "aspect": str(trigger.get("aspect") or ""),
        "strength": round(float(trigger.get("timing_strength") or 0), 3),
        "source": "western-transits-timing-selector-windows",
        "sourceClaimIds": unique(source_claim_ids),
        "methodClaimIds": ["hand-transits-timing-climate-not-guarantee"],
        "evidenceClusterKeys": ["currentTransits", "timingContactReducer"],
    }


def relationship_insight_cluster(category: str, block: dict[str, Any]) -> dict[str, Any]:
    items = block.get("items") if isinstance(block.get("items"), list) else []
    title = str(block.get("title") or block.get("label") or category)
    summary = str(block.get("summary") or block.get("meaning") or title)
    return {
        "category": category,
        "label": title,
        "claimIds": block.get("sourceClaimIds") or [],
        "methodClaimIds": block.get("methodClaimIds") or [],
        "itemCount": len(items) if items else len(block.get("whySelected") or []),
        "strongestStrength": max([float(item.get("strength") or 0) for item in items] or [0.55]),
        "averageStrength": round(sum(float(item.get("strength") or 0) for item in items) / max(len(items), 1), 3) if items else 0.55,
        "dominantContactType": str((items[0] or {}).get("contactType") or "structured_insight") if items else "structured_insight",
        "summary": summary,
        "interpretation": str(block.get("headline") or block.get("framing") or block.get("subtitle") or summary),
        "doesNotProve": str(block.get("doesNotProve") or "這個結構化區塊不能單獨證明關係結果。"),
        "confidence": "medium" if items or block.get("title") else "low",
        "source": str(block.get("source") or RELATIONSHIP_INSIGHT_SOURCE),
    }


def relationship_insight_layer(fixture: dict[str, Any], evidence_clusters: dict[str, dict[str, Any]]) -> dict[str, Any]:
    archetype = relationship_archetype_block(evidence_clusters)
    attraction = relationship_dynamics_block(
        key="attractionDynamics",
        label="核心吸引力相位",
        headline="你們為什麼會被彼此吸引",
        evidence_clusters=evidence_clusters,
        pair_keys=ATTRACTION_DYNAMICS_PAIRS,
        limit=4,
    )
    conflict = relationship_dynamics_block(
        key="conflictDynamics",
        label="衝突相位",
        headline="你們最容易在哪裡卡住或吵起來",
        evidence_clusters=evidence_clusters,
        pair_keys=CONFLICT_DYNAMICS_PAIRS,
        include_predicate=lambda item: str(item.get("contactType") or "") == "hard" or "Saturn" in str(item.get("pairKey") or ""),
        limit=5,
    )
    growth = relationship_dynamics_block(
        key="growthDynamics",
        label="成長相位",
        headline="這段關係可以練習什麼，不只是合不合",
        evidence_clusters=evidence_clusters,
        pair_keys=GROWTH_DYNAMICS_PAIRS,
        include_predicate=lambda item: "Jupiter" in str(item.get("pairKey") or ""),
        limit=4,
    )
    partner_needs = partner_needs_block(fixture, evidence_clusters)
    turning_windows = relationship_turning_windows_block(fixture, evidence_clusters)
    landmines = fight_landmines_block(conflict, fixture=fixture, evidence_clusters=evidence_clusters)
    survival = survival_guide_block(attraction, conflict, growth, partner_needs, turning_windows)
    return {
        "version": RELATIONSHIP_INSIGHT_VERSION,
        "relationshipArchetype": archetype,
        "attractionDynamics": attraction,
        "conflictDynamics": conflict,
        "growthDynamics": growth,
        "partnerNeeds": partner_needs,
        "fightLandmines": landmines,
        "survivalGuide": survival,
        "relationshipTurningWindows": turning_windows,
        "methodClaimIds": unique(
            [
                *archetype.get("methodClaimIds", []),
                *attraction.get("methodClaimIds", []),
                *conflict.get("methodClaimIds", []),
                *growth.get("methodClaimIds", []),
                *partner_needs.get("methodClaimIds", []),
                *landmines.get("methodClaimIds", []),
                *survival.get("methodClaimIds", []),
                *turning_windows.get("methodClaimIds", []),
            ]
        ),
        "source": RELATIONSHIP_INSIGHT_SOURCE,
    }


def western_answer_contract_item(cluster: dict[str, Any], kind: str) -> dict[str, Any] | None:
    evidence = western_case_cluster_evidence(cluster)
    if not evidence:
        return None
    item = evidence[0]
    return {
        "kind": kind,
        "label": item.get("label"),
        "technical": western_only_text(item.get("technical") or ""),
        "emotionalMeaning": western_only_text(item.get("emotionalMeaning") or ""),
        "doesNotProve": western_only_text(item.get("doesNotProve") or ""),
        "confidence": item.get("confidence"),
        "source": item.get("source"),
        "atomId": item.get("atomId"),
        "claimIds": item.get("claimIds") or [],
    }


def western_answer_contract_from_evidence(
    context: dict[str, str],
    evidence_clusters: dict[str, dict[str, Any]],
    timing_items: list[dict[str, Any]],
    input_quality: dict[str, Any],
    selector_evidence_cluster_keys: list[str] | None = None,
    status_answer_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question_key = context.get("main_question", "")
    status_policy = status_answer_policy if isinstance(status_answer_policy, dict) else {}
    question_selector = {
        **question_selector_trace(question_key, selector_evidence_cluster_keys, status_policy),
        "usesCalculationEvidence": True,
        "usesContextAsBoundary": True,
        "canCreateAstrologyConclusion": False,
        "requiresCalculationEvidenceForConclusion": True,
    }
    calculation_items: list[dict[str, Any]] = []
    for category in ("identityNeeds", "safetyValidationLanguage", "aspectFunctionCombination", "attraction", "emotionalSafety", "pressure", "communication", "repair"):
        item = western_answer_contract_item(evidence_clusters.get(category) or {}, "calculation")
        if item and item.get("technical") and "沒有足夠可展示" not in str(item.get("technical")):
            calculation_items.append(item)
    calculation_items = calculation_items[:4]

    transit_items = western_case_transit_evidence(timing_items, limit=2)
    current_transit_items: list[dict[str, Any]] = [
        {
            "kind": "currentTransit",
            "label": item.get("label"),
            "technical": western_only_text(item.get("technical") or ""),
            "emotionalMeaning": western_only_text(item.get("emotionalMeaning") or ""),
            "doesNotProve": western_only_text(item.get("doesNotProve") or ""),
            "confidence": item.get("confidence"),
            "source": item.get("source"),
            "claimIds": item.get("claimIds") or [],
        }
        for item in transit_items
        if item.get("technical")
    ]
    for category in ("timingWindowBand", "timingContactReducer", "timingMoonWeather"):
        item = western_answer_contract_item(evidence_clusters.get(category) or {}, "currentTransit")
        if item and item.get("technical") and "沒有足夠" not in str(item.get("technical")):
            current_transit_items.append(item)
    current_transit_items = current_transit_items[:4]

    stage_key = context.get("relationship_stage", "")
    status_key = context.get("contact_status", "")
    stage_label = STAGE_LABELS.get(stage_key, stage_key or "未提供")
    status_label = CONTACT_STATUS_LABELS.get(status_key, status_key or "未提供")
    stage_cluster = evidence_clusters.get("relationshipStage") or {}
    contact_cluster = evidence_clusters.get("contactStatus") or {}
    contact_policy_cluster = evidence_clusters.get("contactSituationPolicy") or {}
    consultation_safety_cluster = evidence_clusters.get("consultationSafety") or {}
    context_evidence = [
        item
        for item in (
            western_answer_contract_item(stage_cluster, "context"),
            western_answer_contract_item(contact_cluster, "context"),
            western_answer_contract_item(contact_policy_cluster, "context"),
            western_answer_contract_item(evidence_clusters.get("emotionalRisk") or {}, "context"),
            western_answer_contract_item(consultation_safety_cluster, "context"),
        )
        if item
    ][:5]
    context_source_claim_ids = unique(
        [
            str(claim_id)
            for item in context_evidence
            for claim_id in item.get("claimIds") or []
            if claim_id
        ]
    )
    context_method_claim_ids = unique(
        [
            str(claim_id)
            for claim_id in [
                "valley-context-modifies-action-not-conclusion",
                "valley-context-boundary-trace-not-evidence",
                *list(contact_policy_cluster.get("methodClaimIds") or []),
            ]
            if claim_id
        ]
    )
    action_boundary = str(
        contact_policy_cluster.get("allowedAction")
        or "現實狀態只能修正行動建議，不能單獨製造占星結論。"
    )
    context_evidence_boundary = {
        "version": "context-evidence-boundary-v1",
        "role": "action_framing_tone_modifier_only",
        "contextInputs": [
            "relationshipStage",
            "contactStatus",
            "desiredOutcome",
            "emotionalRisk",
        ],
        "allowedUses": [
            "answer_framing",
            "action_scale",
            "tone_safety",
            "timing_boundary",
        ],
        "cannotSatisfyEvidenceFor": [
            "synastry_conclusion",
            "timing_action",
            "compatibility_claim",
            "third_party_inner_state",
        ],
        "canCreateAstrologyConclusion": False,
        "requiresCalculationEvidenceForConclusion": True,
        "requiresTransitEvidenceForTimingAction": True,
        "sourceClaimIds": context_source_claim_ids,
        "methodClaimIds": context_method_claim_ids,
    }

    if not calculation_items:
        synthesis = "本次沒有足夠可展示的合盤計算證據時，答案必須降權，不能只依照關係狀態安慰。"
    elif current_transit_items:
        synthesis = "先用本命與合盤線索判斷關係結構，再用當下行運判斷短期氣候，最後才用現實狀態決定接下來適合做到哪一步。"
    else:
        synthesis = "先用本命與合盤證據判斷關係結構；當下行運不足時，時機判讀必須保守，不給精準窗口。"

    return {
        "version": "western-answer-evidence-contract-v1",
        "calculationEvidence": calculation_items,
        "currentTransitEvidence": current_transit_items,
        "contextModifier": {
            "role": "action_modifier_only",
            "canCreateAstrologyConclusion": False,
            "requiresCalculationEvidenceForConclusion": True,
            "requiresTransitEvidenceForTimingAction": True,
            "sourceClaimIds": context_source_claim_ids,
            "methodClaimIds": context_method_claim_ids,
            "contextEvidenceBoundary": context_evidence_boundary,
            "stageKey": stage_key,
            "stageLabel": stage_label,
            "contactStatusKey": status_key,
            "contactStatusLabel": status_label,
            "actionBoundary": action_boundary,
            "contactActionScale": contact_policy_cluster.get("actionScale"),
            "contactActionMode": contact_policy_cluster.get("actionMode"),
            "contactAllowedAction": contact_policy_cluster.get("allowedAction") or action_boundary,
            "contactBlockedActions": contact_policy_cluster.get("blockedActions") or [],
            "canSuggestDirectContact": contact_policy_cluster.get("canSuggestDirectContact"),
            "requiresEasyExit": contact_policy_cluster.get("requiresEasyExit"),
            "requiresSharedSpaceBoundary": contact_policy_cluster.get("requiresSharedSpaceBoundary"),
            "requiresCalculationSupport": contact_policy_cluster.get("requiresCalculationSupport"),
            "timingCanOverrideBoundary": contact_policy_cluster.get("timingCanOverrideBoundary"),
            "evidence": context_evidence,
        },
        "statusAnswerPolicy": {
            "role": "answer_topic_router_only",
            "version": status_policy.get("version"),
            "stageKey": status_policy.get("stageKey"),
            "questionRewrite": status_policy.get("questionRewrite"),
            "resolvedTracks": [str(item) for item in status_policy.get("resolvedTracks") or [] if item],
            "suppressedTracks": [str(item) for item in status_policy.get("suppressedTracks") or [] if item],
            "canCreateAstrologyConclusion": False,
            "requiresCalculationEvidenceForConclusion": True,
        },
        "questionSelector": question_selector,
        "synthesis": synthesis,
        "contractRules": [
            "Context can modify action, but it cannot create an astrology conclusion without calculation evidence.",
            "Current transits describe timing climate and Moon weather; they do not guarantee contact or reconciliation.",
            "Every action recommendation must combine calculation evidence, current transit evidence, and context boundary.",
            "Question selectors choose which evidence is weighted for the user's question; they cannot create chart facts.",
        ],
        "precision": {
            "inputQuality": input_quality.get("overall"),
            "timingPrecision": "analysis_datetime" if context.get("analysis_datetime") else "analysis_date_noon_fallback",
        },
    }


def western_answer_layer(
    context: dict[str, str],
    synastry_layer: dict[str, list[dict[str, Any]]],
    timing_items: list[dict[str, Any]],
    input_quality: dict[str, Any],
    evidence_clusters: dict[str, dict[str, Any]],
    structured_kb: dict[str, Any] | None = None,
    status_answer_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question_key = context.get("main_question", "")
    status_policy = status_answer_policy or resolve_relationship_status_answer_policy(context, evidence_clusters)
    question_blueprint = western_question_blueprint(structured_kb, question_key)
    selected_question = str(status_policy.get("questionRewrite") or question_blueprint.get("label") or QUESTION_TITLES.get(question_key, question_key))
    attraction_cluster = evidence_clusters.get("attraction") or {}
    safety_cluster = evidence_clusters.get("emotionalSafety") or {}
    pressure_cluster = evidence_clusters.get("pressure") or {}
    communication_cluster = evidence_clusters.get("communication") or {}
    repair_cluster = evidence_clusters.get("repair") or {}
    current_transits_cluster = evidence_clusters.get("currentTransits") or {}
    birth_data_quality_cluster = evidence_clusters.get("birthDataQuality") or {}
    identity_needs_cluster = evidence_clusters.get("identityNeeds") or {}
    repeated_theme_context = western_repeated_theme_result_context(evidence_clusters)
    attraction_strength = float(attraction_cluster.get("strongestStrength") or 0)
    safety_strength = float(safety_cluster.get("strongestStrength") or 0)
    pressure_strength = float(pressure_cluster.get("strongestStrength") or 0)
    repair_strength = float(repair_cluster.get("strongestStrength") or 0)
    communication_strength = float(communication_cluster.get("strongestStrength") or 0)
    quality_note = ""
    if input_quality.get("overall") != "high":
        quality_note = "本次出生資料精度不是完整高精度，Moon、Asc/Desc、宮位與 overlay 需要依 gate 降權或封鎖。"

    selected_rule = western_select_answer_rule(context, evidence_clusters, structured_kb)
    rule_output = (selected_rule or {}).get("output") or {}
    status_policy_cluster_keys = [str(category) for category in status_policy.get("evidenceClusterKeys") or [] if category]
    if rule_output.get("because_clusters"):
        because_cluster_keys = [str(category) for category in rule_output.get("because_clusters") or [] if category]
    elif question_blueprint.get("because_clusters"):
        because_cluster_keys = unique([
            *status_policy_cluster_keys,
            *[str(category) for category in question_blueprint.get("because_clusters") or [] if category],
        ])
    else:
        because_cluster_keys = unique([*status_policy_cluster_keys, "attraction", "emotionalSafety", "pressure"])
    selector_evidence_cluster_keys = question_selector_evidence_cluster_keys(
        question_key,
        unique(["relationshipStatusAnswerPolicy", *status_policy_cluster_keys, *because_cluster_keys]),
    )
    because_clusters = [
        evidence_clusters.get(str(category)) or {}
        for category in because_cluster_keys
    ]
    because = [
        western_cluster_fact(cluster)
        for cluster in because_clusters
    ]
    because = [item for item in because if item and "沒有足夠可展示" not in item]
    timing_fact = str(timing_items[0].get("technical") or "") if timing_items else ""
    if timing_fact:
        if question_key == "when-to-contact":
            because.insert(1, timing_fact)
        else:
            because.append(timing_fact)
    if repeated_theme_context:
        repeated_theme_fact = f"重複主題：{repeated_theme_context.get('label')}；{repeated_theme_context.get('answerFocus')}"
        because.insert(2 if question_key == "when-to-contact" and timing_fact else 1, repeated_theme_fact)
    if quality_note:
        because.append(quality_note)

    if rule_output:
        short_answer = str(rule_output.get("short_answer") or "")
        therefore = str(rule_output.get("therefore") or "")
    elif question_key == "still-love-me":
        if attraction_strength >= 0.62 and pressure_strength >= 0.62:
            short_answer = "合盤看得到在意與反應，但對方的表達容易被緊繃感或安全感議題壓住；先看這些反應能否穩定延續。"
            therefore = "這份解讀會先回答回應模式：看見在意，也看見為什麼不直接表態；矛盾點與行動策略會在後續章節整理。"
        elif attraction_strength >= 0.62:
            short_answer = "合盤看得到吸引或熟悉感，目前先觀察它能不能變成穩定回應。"
            therefore = "下一步要看安全感與修復條件能不能接住這份吸引。"
        else:
            short_answer = "本次可見的西洋證據較保守，先看互動能不能回到比較輕、比較能回應的狀態。"
            therefore = "先把星盤與現實互動一起當核心證據整理，再決定下一步。"
    elif question_key == "any-chance":
        if repair_strength >= 0.55 and pressure_strength < 0.75:
            short_answer = "仍有機會線索，但要先看互動能不能變輕、變穩，再談復合可能。"
            therefore = "這份解讀會說明可觀察條件，再把聯絡時機與訊息節奏放到時機判讀和行動方向裡。"
        elif pressure_strength >= 0.75:
            short_answer = "現在還有機會線索，但卡住的地方比可以重新靠近的條件更明顯；先看互動能不能變輕、變穩。"
            therefore = "先判斷互動能不能穩下來，再談機會。"
        else:
            short_answer = "目前看到的機會線索有限，復合條件還需要更多穩定互動支持。"
            therefore = "完整機會判斷需要更多時間與互動條件。"
    elif question_key == "when-to-contact":
        short_answer = "目前先判斷要放慢，還是用比較輕的方式靠近；聯絡日期用區間和節奏看。"
        if pressure_strength >= 0.7:
            therefore = "互動偏緊時，要先判斷什麼時候比較不會讓對方退開。"
        else:
            therefore = "先看接下來的互動狀態是否適合開口，再觀察回覆是否自然。"
    elif question_key == "what-did-i-do-wrong":
        if communication_strength >= 0.55 or pressure_strength >= 0.62:
            short_answer = "卡住不是單純誰做錯，而是溝通方式和緊繃感容易讓雙方在靠近時互相觸發。"
            therefore = "這份解讀會拆互動循環，不把責任全放到某一個人身上；盲點與修復流程會在行動方向裡整理。"
        else:
            short_answer = "目前證據不足以把問題歸因到單一錯誤，應先回到雙方需求與互動步調。"
            therefore = "不要把星盤寫成責怪用戶的結論。"
    elif question_key == "stay-or-let-go":
        if pressure_strength > max(attraction_strength, safety_strength, repair_strength):
            short_answer = "這段關係比較容易讓你更累；有吸引不等於值得繼續等待。"
            therefore = "這份解讀會先看緊繃感是否能下降與安全是否能恢復，不用等待換答案。"
        else:
            short_answer = "這段關係仍要看吸引能不能被安全地接住；有好感不等於要忽略自己越來越累。"
            therefore = "如果修復條件沒有穩定出現，就不應把在意當成繼續硬撐的理由。"
    elif pressure_strength >= 0.62:
        short_answer = "西洋合盤看得到在意，但緊繃感與情緒安全議題會讓表達變慢或先退開。"
        therefore = "修復條件不是更用力確認，而是先讓互動回到比較輕、比較接得住的狀態。"
    else:
        short_answer = "西洋合盤看得到關係吸引，但目前證據不足以把它說成穩定復合保證。"
        therefore = "先把這份解讀當作核心關係氣候判斷，再把行動策略放到後續章節整理。"

    short_answer, therefore = western_apply_repeated_theme_to_answer(
        question_key=question_key,
        short_answer=short_answer,
        therefore=therefore,
        repeated_theme_context=repeated_theme_context,
    )
    track_labels = [str(item) for item in status_policy.get("resolvedTrackLabels") or [] if item]
    boundary = ""
    for item in status_policy.get("requiredBoundaries") or []:
        if item:
            boundary = str(item)
            break
    if track_labels:
        status_sentence = f"這題先看{track_labels[0]}"
        if status_sentence not in short_answer:
            short_answer = normalize_zh_text(f"{status_sentence}。{short_answer}")
    if boundary and boundary not in therefore:
        therefore = normalize_zh_text(f"{therefore} {boundary}")

    relationship_blueprint = western_relationship_result_question_blueprint(structured_kb)
    included_sections = western_public_copy_list((relationship_blueprint or {}).get("paid_unlock") or [
        "完整 synastry map",
        "composite / Davison relationship story",
        "未來三個月聯絡時機",
        "訊息策略與需要避開的字眼",
    ])
    selected_ruleset_id = canonical_western_relationship_id(selected_rule.get("ruleset_id") if selected_rule else None)
    question_method_claim_ids = question_selector_method_claim_ids(question_key)
    question_selector = question_selector_trace(question_key, selector_evidence_cluster_keys, status_policy)
    return {
        "selectedQuestion": selected_question,
        "selectedQuestionOriginal": str(question_blueprint.get("label") or QUESTION_TITLES.get(question_key, question_key)),
        "shortAnswer": western_public_copy(short_answer),
        "because": western_public_copy_list([item for item in because if item][:4]),
        "therefore": western_public_copy(therefore),
        "ruleId": selected_rule.get("id") if selected_rule else None,
        "rulesetId": selected_ruleset_id,
        "ruleConfidence": rule_output.get("confidence") if rule_output else None,
        "questionBlueprintId": relationship_blueprint.get("blueprint_id"),
        "questionSourceArticleId": question_blueprint.get("source_article_id"),
        "questionClaimIds": question_blueprint.get("claim_ids") or [],
        "questionMethodClaimIds": question_method_claim_ids,
        "questionSelector": question_selector,
        "statusAnswerPolicy": status_policy,
        "answerContract": western_public_copy(question_blueprint.get("answer_contract")),
        "evidenceContract": western_answer_contract_from_evidence(
            context,
            evidence_clusters,
            timing_items,
            input_quality,
            selector_evidence_cluster_keys=selector_evidence_cluster_keys,
            status_answer_policy=status_policy,
        ),
        "repeatedThemeContext": repeated_theme_context,
        "includedSections": included_sections,
    }


def western_relationship_case_file(
    fixture: dict[str, Any],
    context: dict[str, str],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_a = western_birth_data_quality(fixture, "person_a")
    quality_b = western_birth_data_quality(fixture, "person_b")
    input_quality = {
        "personA": quality_a,
        "personB": quality_b,
        "overall": western_overall_input_quality(quality_a, quality_b),
    }
    identity_layer = {
        "personA": {
            "role": "person_a",
            "label": "你",
            "needs": western_need_points(fixture, "person_a", structured_kb),
        },
        "personB": {
            "role": "person_b",
            "label": "對方",
            "needs": western_need_points(fixture, "person_b", structured_kb),
        },
    }
    synastry_layer = {
        "attraction": western_aspect_evidence_items(fixture, "attraction", structured_kb),
        "emotionalSafety": western_aspect_evidence_items(fixture, "emotionalSafety", structured_kb),
        "pressure": western_aspect_evidence_items(fixture, "pressure", structured_kb),
        "communication": western_aspect_evidence_items(fixture, "communication", structured_kb),
        "repair": western_aspect_evidence_items(fixture, "repair", structured_kb),
    }
    timing_items = western_transit_evidence_items(fixture, structured_kb)
    window_scan = western_timing_window_scan_public(fixture)
    evidence_clusters = western_evidence_cluster_layer(fixture, context, identity_layer, synastry_layer, timing_items, input_quality, structured_kb)
    relationship_insights = relationship_insight_layer(fixture, evidence_clusters)
    for insight_key in (
        "relationshipArchetype",
        "attractionDynamics",
        "conflictDynamics",
        "growthDynamics",
        "partnerNeeds",
        "fightLandmines",
        "survivalGuide",
        "relationshipTurningWindows",
    ):
        insight_block = relationship_insights.get(insight_key) or {}
        evidence_clusters[insight_key] = relationship_insight_cluster(insight_key, insight_block)
    status_answer_policy = resolve_relationship_status_answer_policy(context, evidence_clusters)
    evidence_clusters["relationshipStatusAnswerPolicy"] = relationship_status_answer_policy_cluster(status_answer_policy)
    answer_layer = western_answer_layer(
        context,
        synastry_layer,
        timing_items,
        input_quality,
        evidence_clusters,
        structured_kb,
        status_answer_policy=status_answer_policy,
    )
    relationship_thesis = relationship_thesis_payload(
        context=context,
        identity_layer=identity_layer,
        synastry_layer=synastry_layer,
        timing_items=timing_items,
        input_quality=input_quality,
        evidence_clusters=evidence_clusters,
        relationship_insights=relationship_insights,
        answer_layer=answer_layer,
    )
    evidence_clusters["relationshipThesis"] = relationship_thesis_cluster(relationship_thesis)
    method_trace = western_runtime_method_trace(evidence_clusters, timing_items, answer_layer)
    return {
        "version": "western-relationship-case-file-v1",
        "principle": "先建立 Western-only 關係個案：本命關係潛力 -> 初步比較 -> 交互相位 -> 壓力/修復/timing -> 問題答案；不可用單一相位替代完整西洋證據層。",
        "calculationSettings": western_calculation_settings(fixture, context),
        "inputQuality": input_quality,
        "identityLayer": identity_layer,
        "synastryLayer": synastry_layer,
        "evidenceClusters": evidence_clusters,
        "relationshipInsightLayer": relationship_insights,
        "relationshipThesis": relationship_thesis,
        "relationshipStatusAnswerPolicy": status_answer_policy,
        "houseOverlayLayer": western_house_overlay_layer_status(fixture, structured_kb),
        "compositeLayer": western_composite_layer_status(structured_kb),
        "timingLayer": {
            "currentTransits": timing_items,
            "windowScan": window_scan,
            "methodLimits": [
                "runtime 若提供 analysis_datetime，當下行運使用該時間；否則退回分析日中午，只能做趨勢與心理天氣判斷。",
                "未來 90 天掃描只公開 better/neutral/avoid 趨勢與月旬區間；精準日期、訊息策略與避雷條件只能以可用範圍與限制呈現，不作承諾。",
                "尚未納入 composite、Davison 或 secondary progressions。",
            ],
        },
        "answerLayer": answer_layer,
        "methodTrace": method_trace,
        "methodGaps": [
            "house overlays are not calculated yet.",
            "composite / Davison relationship-chart layer is not calculated yet.",
            "exact-date timing and message strategy reducer is not exposed yet.",
            "place lookup is still a prototype list/fallback, not a production geocoder.",
        ],
    }


def western_case_aspect_evidence(items: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in items[:limit]:
        evidence_item = {
            "system": "western",
            "label": str(item.get("label") or item.get("aspectLabel") or item.get("category") or "合盤相位"),
            "technical": str(item.get("technical") or ""),
            "emotionalMeaning": str(item.get("emotionalMeaning") or ""),
            "doesNotProve": str(item.get("doesNotProve") or "單一相位不能保證復合或替對方說出完整內心。"),
            "confidence": normalized_case_confidence(item.get("confidence")),
            "source": str(item.get("source") or item.get("id") or "western-synastry"),
        }
        if item.get("atomId"):
            evidence_item["atomId"] = item.get("atomId")
        if item.get("claimIds"):
            evidence_item["claimIds"] = item.get("claimIds")
        if "strength" in item:
            evidence_item["strength"] = item.get("strength")
        if item.get("claimSupport"):
            evidence_item["claimSupport"] = item.get("claimSupport")
        evidence.append(evidence_item)
    return evidence


def western_case_identity_evidence(person_layer: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    role_label = str(person_layer.get("label") or "")
    role = str(person_layer.get("role") or role_label or "person")
    evidence: list[dict[str, Any]] = []
    for need in (person_layer.get("needs") or [])[:limit]:
        point = str(need.get("point") or "need")
        evidence.append(
            {
                "system": "western",
                "label": f"{role_label}本命需求",
                "technical": f"{role_label}{need.get('label') or point}：{need.get('meaning') or ''}",
                "emotionalMeaning": str(need.get("precisionNote") or "此本命點用來判斷關係需求，不代表對方一定會行動。"),
                "doesNotProve": "本命需求不能單獨證明對方是否回頭，也不能取代合盤互動證據。",
                "confidence": normalized_case_confidence(need.get("confidence")),
                "source": f"western-identity-{role}-{point.lower()}",
            }
        )
    return evidence


def western_case_transit_evidence(items: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in items[:limit]:
        evidence_item = {
            "system": "western",
            "label": str(item.get("label") or "當下行運觸發"),
            "technical": str(item.get("technical") or ""),
            "emotionalMeaning": str(item.get("emotionalMeaning") or ""),
            "doesNotProve": str(item.get("doesNotProve") or "行運只描述當下氣候，不保證某天一定聯絡或復合。"),
            "confidence": normalized_case_confidence(item.get("confidence")),
            "source": str(item.get("source") or item.get("id") or "western-current-transits-v1"),
        }
        if item.get("atomId"):
            evidence_item["atomId"] = item.get("atomId")
        if item.get("claimIds"):
            evidence_item["claimIds"] = item.get("claimIds")
        if item.get("claimSupport"):
            evidence_item["claimSupport"] = item.get("claimSupport")
        evidence.append(evidence_item)
    return evidence


def western_case_cluster_evidence(cluster: dict[str, Any]) -> list[dict[str, Any]]:
    if not cluster:
        return []
    evidence_item = {
        "system": "western",
        "label": str(cluster.get("label") or cluster.get("category") or "Context"),
        "technical": str(cluster.get("summary") or ""),
        "emotionalMeaning": str(cluster.get("interpretation") or ""),
        "doesNotProve": str(cluster.get("doesNotProve") or ""),
        "confidence": normalized_case_confidence(cluster.get("confidence")),
        "source": str(cluster.get("source") or cluster.get("category") or "context"),
    }
    if cluster.get("atomId"):
        evidence_item["atomId"] = cluster.get("atomId")
    if cluster.get("claimIds"):
        evidence_item["claimIds"] = cluster.get("claimIds")
    if cluster.get("sourceClaimIds"):
        evidence_item["sourceClaimIds"] = cluster.get("sourceClaimIds")
    if cluster.get("methodClaimIds"):
        evidence_item["methodClaimIds"] = cluster.get("methodClaimIds")
    if cluster.get("claimSupport"):
        evidence_item["claimSupport"] = cluster.get("claimSupport")
    if cluster.get("houseAnglePrecisionGate"):
        evidence_item["houseAnglePrecisionGate"] = cluster.get("houseAnglePrecisionGate")
    if cluster.get("contactActionBoundary"):
        evidence_item["contactActionBoundary"] = cluster.get("contactActionBoundary")
    if cluster.get("saturnProcessBoundary"):
        evidence_item["saturnProcessBoundary"] = cluster.get("saturnProcessBoundary")
    return [evidence_item]


def western_trace_unique_strings(values: list[Any]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def western_trace_claim_ids(item: dict[str, Any]) -> list[str]:
    claim_ids = list(item.get("claimIds") or [])
    for support in item.get("claimSupport") or []:
        if isinstance(support, dict):
            claim_ids.append(str(support.get("claimId") or support.get("claim_id") or ""))
    return western_trace_unique_strings(claim_ids)


def western_trace_live_evidence(
    section: dict[str, Any],
    evidence_clusters: dict[str, dict[str, Any]],
    timing_items: list[dict[str, Any]],
    answer_layer: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for cluster_key in section.get("evidenceClusterKeys") or []:
        for item in western_case_cluster_evidence(evidence_clusters.get(str(cluster_key)) or {}):
            item["clusterKey"] = str(cluster_key)
            evidence.append(item)
    if "currentTransits" in section.get("evidenceClusterKeys", []):
        for item in western_case_transit_evidence(timing_items, limit=5):
            item["clusterKey"] = "currentTransits"
            evidence.append(item)
    if section.get("sectionId") in {"question", "action"}:
        evidence_contract = answer_layer.get("evidenceContract") or {}
        evidence.extend(evidence_contract.get("calculationEvidence") or [])
        evidence.extend(evidence_contract.get("currentTransitEvidence") or [])
        context_modifier = evidence_contract.get("contextModifier") or {}
        evidence.extend(context_modifier.get("evidence") or [])
    return [item for item in evidence if isinstance(item, dict)]


def western_method_trace_section(
    section: dict[str, Any],
    evidence_clusters: dict[str, dict[str, Any]],
    timing_items: list[dict[str, Any]],
    answer_layer: dict[str, Any],
) -> dict[str, Any]:
    live_evidence = western_trace_live_evidence(section, evidence_clusters, timing_items, answer_layer)
    evidence_cluster_keys = [
        str(cluster_key)
        for cluster_key in section.get("evidenceClusterKeys") or []
        if cluster_key in evidence_clusters
    ]
    runtime_claim_ids = western_trace_unique_strings(
        [
            claim_id
            for item in live_evidence
            for claim_id in western_trace_claim_ids(item)
        ]
    )
    used_atom_ids = western_trace_unique_strings([item.get("atomId") for item in live_evidence])
    live_sources = western_trace_unique_strings([item.get("source") for item in live_evidence])
    method_claim_ids = western_trace_unique_strings(list(section.get("methodClaimIds") or []))
    required_runtime_targets = western_trace_unique_strings(list(section.get("requiredRuntimeTargets") or []))
    required_source_ids = western_trace_unique_strings(list(section.get("requiredSourceIds") or []))
    missing_requirements: list[str] = []
    if not method_claim_ids:
        missing_requirements.append("methodClaimIds")
    if not required_source_ids:
        missing_requirements.append("requiredSourceIds")
    if not evidence_cluster_keys:
        missing_requirements.append("evidenceClusterKeys")
    if not live_evidence:
        missing_requirements.append("liveEvidence")
    return {
        "sectionId": section.get("sectionId"),
        "title": section.get("title"),
        "status": "covered" if not missing_requirements else "partial",
        "requiredRuntimeTargets": required_runtime_targets,
        "requiredSourceIds": required_source_ids,
        "methodClaimIds": method_claim_ids,
        "runtimeClaimIds": runtime_claim_ids,
        "usedAtomIds": used_atom_ids,
        "liveEvidenceSources": live_sources,
        "evidenceClusterKeys": evidence_cluster_keys,
        "liveEvidenceCount": len(live_evidence),
        "missingRequirements": missing_requirements,
    }


def western_runtime_method_trace(
    evidence_clusters: dict[str, dict[str, Any]],
    timing_items: list[dict[str, Any]],
    answer_layer: dict[str, Any],
) -> dict[str, Any]:
    sections = [
        western_method_trace_section(section, evidence_clusters, timing_items, answer_layer)
        for section in WESTERN_METHOD_TRACE_SECTIONS
    ]
    return {
        "version": "western-method-trace-v1",
        "principle": "每個 V1 結果段落必須同時有書本方法 claim、實際 runtime cluster，且不能用情境答案取代計算證據。",
        "sections": sections,
        "summary": {
            "sectionCount": len(sections),
            "coveredSectionCount": sum(1 for section in sections if section.get("status") == "covered"),
            "methodClaimCount": len(western_trace_unique_strings([
                claim_id
                for section in sections
                for claim_id in section.get("methodClaimIds", [])
            ])),
            "runtimeClaimCount": len(western_trace_unique_strings([
                claim_id
                for section in sections
                for claim_id in section.get("runtimeClaimIds", [])
            ])),
            "sourceCount": len(western_trace_unique_strings([
                source_id
                for section in sections
                for source_id in section.get("requiredSourceIds", [])
            ])),
        },
    }


def western_blueprint_evidence(*groups: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            source = str(item.get("source") or item.get("label") or "")
            dedupe_key = f"{source}|{item.get('label') or ''}|{item.get('technical') or ''}"
            if not source or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            output.append(item)
            if len(output) >= limit:
                return output
    return output


def western_case_title_material(case_file: dict[str, Any]) -> dict[str, Any]:
    pressure = ((case_file.get("synastryLayer") or {}).get("pressure") or [])
    attraction = ((case_file.get("synastryLayer") or {}).get("attraction") or [])
    safety = ((case_file.get("synastryLayer") or {}).get("emotionalSafety") or [])
    primary = (pressure or attraction or safety or [{}])[0]
    point_a = str(primary.get("personAPoint") or "")
    point_b = str(primary.get("personBPoint") or "")
    aspect = str(primary.get("aspectLabel") or primary.get("aspect") or "")
    token = "-".join(item for item in (point_a, point_b) if item) or aspect or "合盤"
    readable_token = (
        token.replace("Saturn", "土星")
        .replace("Mercury", "水星")
        .replace("Moon", "月亮")
        .replace("Venus", "金星")
        .replace("Mars", "火星")
        .replace("Sun", "太陽")
    )
    if pressure:
        suggested_title = fit_result_title(f"有牽動，但{readable_token}讓回應變慢")
    elif attraction:
        suggested_title = fit_result_title(f"{readable_token}牽動明顯，但仍要看壓力")
    else:
        suggested_title = "有牽動，但需要看能不能穩住"
    seeds = [
        readable_token,
        first_clause(str(primary.get("technical") or ""), 42),
        first_clause(str(primary.get("emotionalMeaning") or ""), 42),
    ]
    return {"suggestedTitle": suggested_title, "seeds": [seed for seed in seeds if seed]}


QUESTION_SECTION_TITLES = {
    "still-love-me": {
        "thoughts": "他現在怎麼想",
        "reasons": "你們卡住的原因",
        "chance": "還有沒有機會",
    },
    "any-chance": {
        "thoughts": "現在的機會條件",
        "reasons": "機會被什麼壓住",
        "chance": "能不能重新靠近",
    },
    "when-to-contact": {
        "thoughts": "現在適不適合聯絡",
        "reasons": "訊息語氣與避雷",
        "chance": "可行方式與邊界",
    },
    "what-did-i-do-wrong": {
        "thoughts": "先不要只怪自己",
        "reasons": "互動怎麼失衡",
        "chance": "修復要先看什麼",
    },
    "stay-or-let-go": {
        "thoughts": "你現在該先看什麼",
        "reasons": "會不會更累與修復條件",
        "chance": "等或放下的界線",
    },
}


def question_chapter_title(question: str, chapter_id: str, fallback: str | None) -> str:
    return QUESTION_SECTION_TITLES.get(question, {}).get(chapter_id, str(fallback or chapter_id))


def western_blueprint_evidence_from_specs(
    specs: list[dict[str, Any]],
    evidence_pools: dict[str, list[dict[str, Any]]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    groups: list[list[dict[str, Any]]] = []
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        source = str(spec.get("source") or "")
        source_limit = int(spec.get("limit") or 1)
        group = evidence_pools.get(source) or []
        groups.append(group[:source_limit])
    return western_blueprint_evidence(*groups, limit=limit)


def western_relationship_reading_blueprint(
    case_file: dict[str, Any],
    context: dict[str, str],
    included_rows: list[dict[str, Any]],
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity = case_file.get("identityLayer") or {}
    synastry = case_file.get("synastryLayer") or {}
    timing = case_file.get("timingLayer") or {}
    answer = case_file.get("answerLayer") or {}
    clusters = case_file.get("evidenceClusters") or {}
    status_policy = case_file.get("relationshipStatusAnswerPolicy") or answer.get("statusAnswerPolicy") or {}
    question_key = context.get("main_question", "")
    question = str(status_policy.get("questionRewrite") or western_question_label(structured_kb, question_key))
    stage = STAGE_LABELS.get(context.get("relationship_stage", ""), context.get("relationship_stage", ""))
    included_titles = [western_public_copy(row.get("title")) for row in included_rows if row.get("title")]
    title_material = western_case_title_material(case_file)
    identity_a = western_case_identity_evidence(identity.get("personA") or {}, limit=3)
    identity_b = western_case_identity_evidence(identity.get("personB") or {}, limit=3)
    attraction = western_case_aspect_evidence(synastry.get("attraction") or [], limit=3)
    safety = western_case_aspect_evidence(synastry.get("emotionalSafety") or [], limit=3)
    pressure = western_case_aspect_evidence(synastry.get("pressure") or [], limit=3)
    communication = western_case_aspect_evidence(synastry.get("communication") or [], limit=2)
    repair = western_case_aspect_evidence(synastry.get("repair") or [], limit=2)
    current_transits = western_case_transit_evidence(timing.get("currentTransits") or [], limit=3)
    short_answer = western_public_copy(answer.get("shortAnswer") or "西洋合盤看得到牽動，但這份解讀只能給方向，不能給保證。")
    therefore = western_public_copy(answer.get("therefore") or "修復條件要看牽動能不能被安全地接住。")
    structured_blueprint = western_relationship_result_question_blueprint(structured_kb)
    evidence_pools = {
        "userIdentity": identity_a,
        "partnerIdentity": identity_b,
        "methodOrder": western_case_cluster_evidence(clusters.get("methodOrder") or {}),
        "natalSymbolFoundation": western_case_cluster_evidence(clusters.get("natalSymbolFoundation") or {}),
        "planetaryFunctions": western_case_cluster_evidence(clusters.get("planetaryFunctions") or {}),
        "signClassificationFoundation": western_case_cluster_evidence(clusters.get("signClassificationFoundation") or {}),
        "elementStyleFoundation": western_case_cluster_evidence(clusters.get("elementStyleFoundation") or {}),
        "modalityResponseFoundation": western_case_cluster_evidence(clusters.get("modalityResponseFoundation") or {}),
        "planetSignStyle": western_case_cluster_evidence(clusters.get("planetSignStyle") or {}),
        "moonSignEmotionalSafety": western_case_cluster_evidence(clusters.get("moonSignEmotionalSafety") or {}),
        "mercurySignCommunicationRepair": western_case_cluster_evidence(clusters.get("mercurySignCommunicationRepair") or {}),
        "venusSignAffectionStyle": western_case_cluster_evidence(clusters.get("venusSignAffectionStyle") or {}),
        "marsSignPursuitConflict": western_case_cluster_evidence(clusters.get("marsSignPursuitConflict") or {}),
        "saturnSignDefenseDelay": western_case_cluster_evidence(clusters.get("saturnSignDefenseDelay") or {}),
        "functionElementMatrix": western_case_cluster_evidence(clusters.get("functionElementMatrix") or {}),
        "functionModalityMatrix": western_case_cluster_evidence(clusters.get("functionModalityMatrix") or {}),
        "relationshipPotential": western_case_cluster_evidence(clusters.get("relationshipPotential") or {}),
        "elementComparison": western_case_cluster_evidence(clusters.get("elementComparison") or {}),
        "luminaryComparison": western_case_cluster_evidence(clusters.get("luminaryComparison") or {}),
        "ascendantImpression": western_case_cluster_evidence(clusters.get("ascendantImpression") or {}),
        "houseRelationshipFactors": western_case_cluster_evidence(clusters.get("houseRelationshipFactors") or {}),
        "angleHouseFramework": western_case_cluster_evidence(clusters.get("angleHouseFramework") or {}),
        "aspectPriority": western_case_cluster_evidence(clusters.get("aspectPriority") or {}),
        "aspectContactModifier": western_case_cluster_evidence(clusters.get("aspectContactModifier") or {}),
        "aspectPairContactTemplate": western_case_cluster_evidence(clusters.get("aspectPairContactTemplate") or {}),
        "aspectPairPhraseTemplateMethod": western_case_cluster_evidence(clusters.get("aspectPairPhraseTemplateMethod") or {}),
        "aspectFunctionCombination": western_case_cluster_evidence(clusters.get("aspectFunctionCombination") or {}),
        "aspectInterpretationFoundation": western_case_cluster_evidence(clusters.get("aspectInterpretationFoundation") or {}),
        "aspectSynthesisCrossCheck": western_case_cluster_evidence(clusters.get("aspectSynthesisCrossCheck") or {}),
        "relationshipChartLayer": western_case_cluster_evidence(clusters.get("relationshipChartLayer") or {}),
        "consultationSafety": western_case_cluster_evidence(clusters.get("consultationSafety") or {}),
        "nonfatalSynastrySafety": western_case_cluster_evidence(clusters.get("nonfatalSynastrySafety") or {}),
        "attraction": attraction,
        "emotionalSafety": safety,
        "pressure": pressure,
        "communication": communication,
        "repair": repair,
        "currentTransits": current_transits,
        "timingWindowBand": western_case_cluster_evidence(clusters.get("timingWindowBand") or {}),
        "timingMercuryCommunication": western_case_cluster_evidence(clusters.get("timingMercuryCommunication") or {}),
        "timingVenusSoftening": western_case_cluster_evidence(clusters.get("timingVenusSoftening") or {}),
        "timingMarsActivation": western_case_cluster_evidence(clusters.get("timingMarsActivation") or {}),
        "timingSaturnPressure": western_case_cluster_evidence(clusters.get("timingSaturnPressure") or {}),
        "timingMoonWeather": western_case_cluster_evidence(clusters.get("timingMoonWeather") or {}),
        "timingContactReducer": western_case_cluster_evidence(clusters.get("timingContactReducer") or {}),
        "relationshipStage": western_case_cluster_evidence(clusters.get("relationshipStage") or {}),
        "contactStatus": western_case_cluster_evidence(clusters.get("contactStatus") or {}),
        "contactSituationPolicy": western_case_cluster_evidence(clusters.get("contactSituationPolicy") or {}),
        "emotionalRisk": western_case_cluster_evidence(clusters.get("emotionalRisk") or {}),
        "desiredOutcome": western_case_cluster_evidence(clusters.get("desiredOutcome") or {}),
    }

    if structured_blueprint.get("chapters"):
        chapters = []
        for chapter in structured_blueprint.get("chapters") or []:
            if not isinstance(chapter, dict):
                continue
            core_summary_source = str(chapter.get("core_summary_source") or "shortAnswer")
            chapters.append(
                {
                    "id": chapter.get("id"),
                    "title": relationship_status_policy_section_title(
                        status_policy,
                        str(chapter.get("id") or ""),
                        question_chapter_title(question_key, str(chapter.get("id") or ""), chapter.get("title")),
                    ),
                    "sourceDimensions": chapter.get("source_dimensions") or [],
                    "coreSummary": western_public_copy(therefore if core_summary_source == "therefore" else short_answer),
                    "chapterAngle": western_public_copy(chapter.get("chapter_angle")),
                    "mustAnswer": western_public_copy_list(chapter.get("must_answer") or []),
                    "doNotRepeat": western_public_copy_list(chapter.get("do_not_repeat") or []),
                    "technicalFocus": western_public_copy(chapter.get("technical_focus")),
                    "psychologicalFocus": western_public_copy(chapter.get("psychological_focus")),
                    "evidence": western_blueprint_evidence_from_specs(
                        chapter.get("evidence") or [],
                        evidence_pools,
                        int(chapter.get("evidence_limit") or 5),
                    ),
                    "emotionalDirection": western_public_copy(chapter.get("emotional_direction")),
                    "methodBoundary": western_public_copy(chapter.get("paid_boundary")),
                    "forbiddenClaims": western_public_copy_list(chapter.get("forbidden_claims") or []),
                    "nextBridge": western_public_copy(chapter.get("next_bridge")),
                }
            )
    else:
        raise SystemExit(f"Missing `{WESTERN_RELATIONSHIP_RESULT_ID}` question blueprint. Run scripts/compile_kb.py.")

    return {
        "version": "reading-blueprint-v1",
        "mainConclusion": western_public_copy(f"{title_material['suggestedTitle']}。{short_answer}"),
        "suggestedResultTitle": title_material["suggestedTitle"],
        "resultTitleSeeds": title_material["seeds"],
        "titleDirection": western_public_copy(structured_blueprint.get("title_direction") or "主標要根據 Western case file 重寫成一句命盤結論；不可複製固定答案或用戶問題。"),
        "storyArc": western_public_copy(str(
            structured_blueprint.get("story_arc_template")
            or "用戶問題是「{question}」，目前階段是「{stage}」。這份解讀只用西洋本命需求、合盤相位與當下行運回答三件事：對方目前回應模式、卡住機制、能不能重新靠近的條件。"
        ).format(question=question, stage=stage)),
        "statusAnswerPolicy": {
            "version": status_policy.get("version"),
            "questionRewrite": status_policy.get("questionRewrite"),
            "resolvedTracks": [str(item) for item in status_policy.get("resolvedTracks") or [] if item],
            "resolvedTrackLabels": [str(item) for item in status_policy.get("resolvedTrackLabels") or [] if item],
            "suppressedTracks": [str(item) for item in status_policy.get("suppressedTracks") or [] if item],
            "requiredBoundaries": [str(item) for item in status_policy.get("requiredBoundaries") or [] if item],
        },
        "chapterOrder": structured_blueprint.get("chapter_order") or ["thoughts", "reasons", "chance"],
        "chapters": chapters,
        "includedReadingPlan": included_titles,
        "includedQuestions": included_titles,
        "forbiddenClaims": western_public_copy_list(structured_blueprint.get("global_forbidden_claims") or [
            "不可新增星盤沒有提供的事實",
            "不可做絕對預言",
            "不可說百分之百或一定會",
            "不可給精準日期承諾",
            "不可把單一章節寫成完整關係結論",
        ]),
        "styleRules": western_public_copy_list(structured_blueprint.get("style_rules") or [
            "每章只保留一個核心 summary",
            "technicalReading 用占星師口吻，保留行星、相位、orb 與精度限制",
            "psychologicalSummary 用心理師與關係教練口吻，翻譯成情緒方向",
            "supporting evidence 必須短，避免重複同一句緊繃主題",
        ]),
    }


def western_case_file_score(case_file: dict[str, Any], context: dict[str, str]) -> int:
    synastry = case_file.get("synastryLayer") or {}
    attraction_strength = max([float(item.get("strength", 0)) for item in synastry.get("attraction") or []] or [0.58])
    safety_strength = max([float(item.get("strength", 0)) for item in synastry.get("emotionalSafety") or []] or [0.45])
    pressure_strength = max([float(item.get("strength", 0)) for item in synastry.get("pressure") or []] or [0.5])
    stage_adjustment = {"broke-up-recent": -3, "cold-war": -1, "broke-up-long": -8, "crisis": -7}.get(context.get("relationship_stage", ""), 0)
    risk_adjustment = {"calm": 2, "anxious": -3, "self-blaming": -4, "desperate": -8, "unsafe-or-overwhelmed": -10}.get(context.get("emotional_risk", ""), 0)
    score = 52 + attraction_strength * 34 + safety_strength * 8 - pressure_strength * 12 + stage_adjustment + risk_adjustment
    return clamp_score(score, 38, 88)


def western_case_file_pressure_score(case_file: dict[str, Any], context: dict[str, str]) -> int:
    pressure = ((case_file.get("synastryLayer") or {}).get("pressure") or [])
    pressure_strength = max([float(item.get("strength", 0)) for item in pressure] or [0.58])
    risk_adjustment = 8 if context.get("emotional_risk") in {"anxious", "desperate", "self-blaming"} else 0
    return clamp_score(pressure_strength * 100 + risk_adjustment, 42, 90)


def western_authority_reasons(case_file: dict[str, Any], context: dict[str, str]) -> list[dict[str, str]]:
    synastry = case_file.get("synastryLayer") or {}
    attraction = (synastry.get("attraction") or [{}])[0]
    pressure = (synastry.get("pressure") or [{}])[0]
    timing = ((case_file.get("timingLayer") or {}).get("currentTransits") or [{}])[0]
    answer = case_file.get("answerLayer") or {}
    return [
        {
            "system": "西洋合盤",
            "title": str(attraction.get("label") or attraction.get("aspectLabel") or "合盤牽動"),
            "because": str(attraction.get("technical") or "本次先看合盤相位與本命關係需求。"),
            "therefore": str(attraction.get("emotionalMeaning") or answer.get("shortAnswer") or ""),
            "avoid": "不要把單一相位當作對方一定會回頭的保證。",
            "source": str(attraction.get("source") or "western-synastry"),
        },
        {
            "system": "西洋卡點",
            "title": str(pressure.get("label") or pressure.get("aspectLabel") or "合盤卡點"),
            "because": str(pressure.get("technical") or "目前卡住訊號會影響靠近速度與表達方式。"),
            "therefore": str(answer.get("therefore") or pressure.get("emotionalMeaning") or ""),
            "avoid": avoid_from_context(context, str(pressure.get("source") or "western-pressure")),
            "source": str(pressure.get("source") or "western-pressure"),
        },
        {
            "system": "西洋行運",
            "title": str(timing.get("label") or "當下行運氣候"),
            "because": western_public_copy(timing.get("technical") or "這份解讀只把當下氣候作為輔助，不把它寫成精準日期承諾。"),
            "therefore": str(timing.get("emotionalMeaning") or "行運只能輔助判斷節奏，不能保證結果。"),
            "avoid": "不要把行運氣候當成精準聯絡日或必然結果。",
            "source": str(timing.get("source") or "western-current-transits-v1"),
        },
    ]


def western_chapter_evidence_from_blueprint(blueprint: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    output: dict[str, list[dict[str, str]]] = {"thoughts": [], "reasons": [], "chance": []}
    for chapter in blueprint.get("chapters") or []:
        chapter_id = str(chapter.get("id") or "")
        if chapter_id not in output:
            continue
        output[chapter_id] = [
            {
                "label": str(item.get("label") or "西洋證據"),
                "title": first_clause(str(item.get("technical") or item.get("label") or "西洋星盤證據"), 24),
                "body": str(item.get("emotionalMeaning") or item.get("technical") or ""),
                "source": str(item.get("source") or "western-evidence"),
            }
            for item in (chapter.get("evidence") or [])[:3]
        ]
    return output


def western_source_chips(western_id: str | None, articles: dict[str, dict[str, Any]]) -> list[str]:
    source_names: list[str] = []
    if western_id and western_id in articles:
        article = articles[western_id]
        source_names.append(str(article.get("source_primary") or ""))
        source_names.extend(str(item) for item in article.get("source_secondary") or [])
    source_names.extend(["immanuel / Swiss Ephemeris", "光之谷西洋合盤知識庫"])
    return unique([item for item in source_names if item])[:4]


def attach_western_claim_support(
    case_file: dict[str, Any],
    claims_by_article: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    if not claims_by_article:
        return case_file

    for items in (case_file.get("synastryLayer") or {}).values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            support = claim_support_for(str(item.get("source") or ""), claims_by_article)
            if support:
                item["claimSupport"] = support
            modifier = item.get("contactModifier")
            if isinstance(modifier, dict):
                modifier_support = claim_support_for(
                    str(modifier.get("source") or ""),
                    claims_by_article,
                    claim_ids=[str(claim_id) for claim_id in modifier.get("claimIds") or []],
                )
                if modifier_support:
                    modifier["claimSupport"] = modifier_support
            pair_template = item.get("pairContactTemplate")
            if isinstance(pair_template, dict):
                template_support = claim_support_for(
                    str(pair_template.get("source") or ""),
                    claims_by_article,
                    claim_ids=[str(claim_id) for claim_id in pair_template.get("claimIds") or []],
                )
                if template_support:
                    pair_template["claimSupport"] = template_support

    for item in (case_file.get("timingLayer") or {}).get("currentTransits") or []:
        if not isinstance(item, dict):
            continue
        support = claim_support_for(str(item.get("source") or ""), claims_by_article)
        if support:
            item["claimSupport"] = support

    for cluster in (case_file.get("evidenceClusters") or {}).values():
        if not isinstance(cluster, dict):
            continue
        support = claim_support_for(
            str(cluster.get("source") or ""),
            claims_by_article,
            claim_ids=[str(claim_id) for claim_id in cluster.get("claimIds") or []],
        )
        if support:
            cluster["claimSupport"] = support

    return case_file


def first_clause(text: str, max_chars: int = 48) -> str:
    clause = re.split(r"[。；;]", text.strip())[0].strip()
    if len(clause) <= max_chars:
        return clause
    return clause[:max_chars].rstrip("，、：；。 ")


def fit_result_title(title: str, max_chars: int = 28) -> str:
    clean = title.replace("。", "").strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rstrip("，、；： ")


def safety_copy(stage: str, risk: str) -> str:
    if risk in {"desperate", "unsafe-or-overwhelmed"}:
        return "先保護自己，不適合逼答案或立刻攤牌"
    if stage == "broke-up-recent":
        return "先把動作放小，避免用焦慮修復"
    if stage == "crisis":
        return "先讓壓力降下來，不適合用情緒做最後決定"
    return "先看互動能不能接住，再決定要不要開口"


def western_body(article_id: str | None) -> str:
    if not article_id:
        return "西洋合盤目前資料不足，所以這份解讀先不把相位當作結論。"
    if article_id == "western-aspects-sun-mars":
        return "你們之間有明顯行動力與吸引力，但互動速度太快時，也容易把彼此推入壓力反應。"
    if article_id == "western-aspects-venus-mars":
        return "吸引力比較直接，容易讓人想重新靠近；關係能不能穩，還要看靠近之後對方能不能自然延續回應。"
    if article_id == "western-aspects-mars-saturn":
        return "一方想前進時，另一方容易感到壓力或限制，這會讓互動出現靠近與煞車並存的狀態。"
    if article_id == "western-aspects-sun-moon":
        return "核心自我與情緒需求有可互相看見的地方，但危機期仍要看是否能用成熟方式回應彼此。"
    if article_id == "western-aspects-moon-saturn":
        return "情緒連結容易被責任、害怕失控或防衛感壓住，所以表達會先變保守。"
    if article_id == "western-aspects-moon-venus":
        return "月亮與金星讓互動有柔軟好感與被照顧感，但情緒安全感不足時也容易變成想確認、怕失去。"
    if article_id == "western-aspects-venus-saturn":
        return "感情表達偏慢，靠近時容易同時想退；這會讓你感覺對方忽冷忽熱。"
    if article_id == "western-aspects-sun-saturn":
        return "太陽與土星的互動會讓關係帶著責任感與壓力，越想確認，越容易讓表達變慢、變保守。"
    if article_id == "western-aspects-mercury-contacts":
        return "水星相位讓問題集中在訊息、語氣與理解方式；說法一緊，對方就容易進入防衛。"
    return "西洋合盤提供吸引、壓力與互動節奏的證據，目前應避免把單一相位當成確定答案。"


def thoughts(question: str, stage: str, risk: str) -> list[str]:
    if question == "still-love-me":
        return [
            "這一題先看對方還有沒有穩定回應、情緒反應和靠近意願。",
            "有反應時，重點是看它能不能持續；冷淡時，重點是看對話是否還能變輕。",
            "越急著問他還愛不愛，越容易把原本可以觀察的線索變成逼問感。",
        ]
    if question == "any-chance":
        return [
            "這一題看的是修復條件還在不在。",
            "如果你們還能用比較輕的方式接上，機會才有地方慢慢打開。",
            "如果一靠近就回到追問、辯解或翻舊帳，機會會被舊互動模式卡住。",
        ]
    if question == "when-to-contact":
        return [
            "現在先看這段互動承不承受得住新的訊息，避開急著逼出答案。",
            "冷戰或斷聯時，訊息要短、輕、沒有要求；一像追問，對方就更容易退開。",
            "適不適合聯絡，要看對方比較接得住的時機，也要避開你最焦慮的那一刻。",
        ]
    if question == "what-did-i-do-wrong":
        return [
            "先看你們怎麼一步步互相觸發，再找可以改得比較輕的地方。",
            "重點是找出可調整的互動，把責任拆回具體事件。",
            "先分清楚：哪一部分你能改，哪一部分是對方自己的反應模式。",
        ]
    if question == "stay-or-let-go":
        return [
            "這一題先看你要不要繼續等，也要看這段互動會不會讓你更累。",
            "如果對方只有在被逼到時才回應，短暫靠近不一定是真正修復。",
            "先把自己的步調拿回來，再看這段關係有沒有值得繼續等待的行動證據。",
        ]
    if stage == "broke-up-recent" or risk in {"anxious", "self-blaming"}:
        return [
            "他仍有反應線索，只是現在比較容易被緊繃感推遠。",
            "剛分開或冷戰時，沉默常常是在自我保護，不一定是徹底放下。",
            "你越急著確認，互動越容易變得更緊。",
        ]
    return [
        "他仍有感受線索，同時也在避免再回到高壓互動。",
        "目前比較像觀望與自我保護，不代表完全放下。",
        "如果你現在太急著確認，反而容易把他推遠。",
    ]


def timeline(context: dict[str, str], relationship_theme: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if relationship_theme:
        theme_steps = repeated_theme_timeline_steps(relationship_theme)
        if theme_steps:
            return theme_steps
    stage = context.get("relationship_stage", "")
    risk = context.get("emotional_risk", "")
    question = context.get("main_question", "")
    if question == "still-love-me":
        return [
            {"range": "第 1-2 天", "title": "停止逼問內心", "body": "先不要用「你還愛不愛」逼對方表態，先讓可以觀察的反應留下來。"},
            {"range": "第 3-5 天", "title": "觀察回應是否穩定", "body": "看對方是否有自然、連續、不是被逼出來的回應，而不是只看一次冷淡或一次熱絡。"},
            {"range": "第 6-7 天", "title": "再判斷能不能靠近", "body": "如果反應穩定一點，再考慮輕量靠近；如果只剩防衛，就先不要追答案。"},
        ]
    if question == "any-chance":
        return [
            {"range": "第 1-2 天", "title": "先停下舊模式", "body": "不要立刻用同一種追問、解釋或道歉重開關係，先讓原本卡住的互動停下來。"},
            {"range": "第 3-5 天", "title": "確認修復條件", "body": "看你們是否還能用比較輕、比較不防衛的方式說話，這比一句復合答案更重要。"},
            {"range": "第 6-7 天", "title": "做一次小型重啟", "body": "如果條件比較穩，只做一個不逼承諾的小動作，觀察對方是否自然接住。"},
        ]
    if question == "when-to-contact":
        return [
            {"range": "第 1-2 天", "title": "先不要開口", "body": "先讓自己的情緒和想開口的急迫感降下來，不用訊息去測答案。"},
            {"range": "第 3-5 天", "title": "整理一句輕一點的訊息", "body": "只保留問候或具體事實，不提復合、承諾，也不急著分誰對誰錯。"},
            {"range": "第 6-7 天", "title": "看時機再送出", "body": "如果自己仍想追問，就繼續觀察；若真的送出，只看對方有沒有自然接住。"},
        ]
    if question == "what-did-i-do-wrong":
        return [
            {"range": "第 1-2 天", "title": "停止全責自責", "body": "先不要把冷淡或分開解讀成都是你做錯，避免用焦慮修復。"},
            {"range": "第 3-5 天", "title": "找出一個互動循環", "body": "把最常重複的誤解、追問、退開或沉默，整理成一個看得見的模式。"},
            {"range": "第 6-7 天", "title": "只修一個可修點", "body": "先調整自己的語氣或步調，不用一次道歉承擔整段關係。"},
        ]
    if question == "stay-or-let-go":
        return [
            {"range": "第 1-2 天", "title": "先暫停做最後決定", "body": "先不要在最痛或最焦慮的時候判定要等或放下，避免被情緒推著走。"},
            {"range": "第 3-5 天", "title": "檢查等待條件", "body": "看對方是否有穩定回應、願意修復，還是只有你一個人在撐。"},
            {"range": "第 6-7 天", "title": "設一條可執行界線", "body": "如果互動沒有變穩，就把下一步放回自己身上，停止無限等待。"},
        ]
    if stage == "crisis":
        return [
            {"range": "第 1-2 天", "title": "停止逼迫決定", "body": "先不要在情緒最高點談結論，避免把關係推向對抗。"},
            {"range": "第 3-5 天", "title": "觀察能否變穩", "body": "看互動是否能從爭辯回到基本尊重與穩定。"},
            {"range": "第 6-7 天", "title": "設定一次不逼結論的談話", "body": "只談一個具體問題，讓對話保留退路。"},
        ]
    if stage == "broke-up-long":
        return [
            {"range": "第 1-2 天", "title": "不急著重啟舊議題", "body": "先確認自己為什麼想聯絡，不要一開口就翻回憶或急著道歉。"},
            {"range": "第 3-5 天", "title": "找比較好開口的方式", "body": "如果要靠近，從輕量、沒有要求的訊息開始。"},
            {"range": "第 6-7 天", "title": "看回應而不是幻想", "body": "看對方有沒有自然接住，再判斷下一步能不能繼續。"},
        ]
    if risk in {"anxious", "self-blaming", "desperate"}:
        return [
            {"range": "第 1-2 天", "title": "不主動追問", "body": "先讓情緒降下來，不用新的訊息刺激對方退開。"},
            {"range": "第 3-5 天", "title": "觀察自然回應", "body": "看對方是否有自然互動，不主動把氣氛推緊。"},
            {"range": "第 6-7 天", "title": "一句輕量訊息", "body": "如果情緒比較穩了，再用一句不要求答案的訊息開口。"},
        ]
    return [
        {"range": "第 1-2 天", "title": "保持距離", "body": "先不要增加新的情緒負擔。"},
        {"range": "第 3-5 天", "title": "觀察回應", "body": "看對方是否願意自然接近。"},
        {"range": "第 6-7 天", "title": "輕一點開口", "body": "只用一個輕量行動，看看互動能不能回穩。"},
    ]


def donts(context: dict[str, str], relationship_theme: dict[str, Any] | None = None) -> list[str]:
    question = context.get("main_question", "")
    if relationship_theme:
        theme_items = repeated_theme_donts(relationship_theme)
        if theme_items:
            if question == "when-to-contact":
                return unique([*theme_items[:2], "不要用長訊息、追問或連續補訊息測對方反應"])[:3]
            return theme_items
    risk = context.get("emotional_risk", "")
    if question == "still-love-me":
        return ["不要直接問他還愛不愛你", "不要把一次冷淡或一次熱絡當成全部答案", "不要用長訊息逼對方說清楚內心"]
    if question == "any-chance":
        return ["不要一開口就問還能不能復合", "不要用舊模式重新靠近", "不要把一次回覆當成關係已經重啟"]
    if question == "when-to-contact":
        return ["不要一開口就問為什麼不回", "不要一開口談復合或承諾", "不要一直補訊息解釋自己的用意"]
    if question == "what-did-i-do-wrong":
        return ["不要把所有錯都攬到自己身上", "不要用道歉換對方安慰", "不要用星盤判定誰該負全責"]
    if question == "stay-or-let-go":
        return ["不要只因為還有感覺就無限等待", "不要用對方偶爾回應，忽略自己一直很累", "不要在情緒最高點做最後決定"]
    if risk in {"desperate", "unsafe-or-overwhelmed"}:
        return ["不要在情緒崩潰時傳長訊息求答案", "不要逼對方立刻承諾", "不要用委屈自己換回應"]
    if context.get("relationship_stage") == "broke-up-long":
        return ["不要翻舊帳開場", "不要突然告白逼對方表態", "不要要求對方立刻表態"]
    return ["不要連續傳訊息", "不要用一大段道歉換回應", "不要問「你到底還愛不愛我」"]


def selected_western_aspects(fixture: dict[str, Any]) -> list[dict[str, str]]:
    signals = fixture.get("candidate_signals", {}).get("western_signals") or []
    if not signals:
        return [
            {
                "label": "資料不足",
                "value": "暫不判斷",
                "meaning": western_unavailable_reason(fixture),
            }
        ]
    rows: list[dict[str, str]] = []
    for signal in signals[:3]:
        article_id = signal.get("id")
        rows.append(
            {
                "label": WESTERN_CHIP_LABELS.get(article_id, str(article_id or "Aspect")),
                "value": "強互動" if float(signal.get("strength", 0)) >= 0.8 else "中高壓力" if "saturn" in str(article_id) else "有牽引",
                "meaning": western_evidence_meaning(str(article_id) if article_id else None),
            }
        )
    return rows


def western_chips(fixture: dict[str, Any], selected_id: str | None) -> list[str]:
    ids = [selected_id] if selected_id else []
    ids.extend(signal.get("id") for signal in fixture.get("candidate_signals", {}).get("western_signals", [])[:5])
    if not any(ids):
        return ["合盤資料不足", "暫不判斷"]
    chips = [WESTERN_CHIP_LABELS.get(str(article_id), str(article_id)) for article_id in unique([str(item) for item in ids if item])]
    extra = ["attraction-pressure", "balance-pressure"]
    return unique(chips + extra)[:4]


def calculation_steps() -> list[dict[str, str]]:
    return [
        {
            "label": "確認出生資料",
            "result": "日期 / 時間 / 地點 / 時區",
        },
        {
            "label": "計算西洋星盤",
            "result": "太陽 / 月亮 / 金星 / 火星 / 土星",
        },
        {
            "label": "比對合盤相位",
            "result": "相位類型 / 容許度 orb / 強弱",
        },
        {
            "label": "整合關係指標",
            "result": "本命需求 / 合盤壓力 / 機會 / 安全提醒",
        },
    ]


def included_reading_items(
    context: dict[str, str],
    relationship_theme: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    question = context.get("main_question", "")
    stage = context.get("relationship_stage", "")
    timing_hint = "接下來 7 天與 6 個月的行動時機" if stage != "broke-up-long" else "重新開口前比較不會讓氣氛變重的時機"

    by_question: dict[str, list[dict[str, list[str] | str]]] = {
        "still-love-me": [
            {"title": "他真正逃避的是什麼", "preview": ["從土星、月亮、金星的卡點拆解", "分辨沒感覺、怕承諾，還是自我保護"]},
            {"title": "他對你最矛盾的地方", "preview": ["吸引點、表達延遲與現實顧慮", "哪些反應不能被直接當成沒感覺"]},
            {"title": "下一次靠近策略", "preview": ["什麼語氣比較不會把他推遠", "什麼問題會讓他更想退開"]},
        ],
        "any-chance": [
            {"title": "復合條件地圖", "preview": ["哪些訊號支持重新靠近", "哪些卡點會讓機會無法落地"]},
            {"title": "重新開口路徑", "preview": ["從輕一點的互動到可談關係的順序", "每一步該看什麼回應"]},
            {"title": "破局點與修復點", "preview": ["哪些模式一碰就卡住", "哪些條件出現才值得繼續"]},
        ],
        "when-to-contact": [
            {"title": "接下來三個月怎麼開口", "preview": ["適合開口、先觀察、暫時避開的時機", "把可行範圍與限制整理清楚"]},
            {"title": "訊息語氣模板", "preview": ["輕一點的開場、收尾與不追問版本", "依照對方容易退開的點改寫"]},
            {"title": "送出後怎麼判讀", "preview": ["已讀、不讀、短回、自然接話各代表什麼", "下一步要等、停，還是輕微推進"]},
        ],
        "what-did-i-do-wrong": [
            {"title": "你的可調整盲點", "preview": ["不是責怪，而是找出可修正的互動習慣", "哪些地方容易讓好意變重"]},
            {"title": "對方自己的退開模式", "preview": ["分清你的部分與他的反應模式", "避免把星盤變成自責工具"]},
            {"title": "怎麼修復才不會變更重", "preview": ["道歉、解釋、沉默各自的風險", "先改哪一個點最有效"]},
        ],
        "stay-or-let-go": [
            {"title": "等待是否還健康", "preview": ["在意、累不累、修復條件一起判斷", "避免把不甘心誤認成命運"]},
            {"title": "該退的界線", "preview": ["哪些訊號代表這段互動正在讓你更累", "什麼情況下需要先保護自己"]},
            {"title": "如果要等，等什麼", "preview": ["不是等他一句話，而是等穩定行動", "哪些改變才算真的可觀察"]},
        ],
    }
    common_rows = [
        {
            "title": "你們的吸引與卡住來源",
            "preview": ["合盤互動力道與相位交叉確認", "哪一種吸引最強，哪一種卡點最傷"],
        },
        {
            "title": "最佳行動步調",
            "preview": [timing_hint, "什麼時候先觀察，什麼時候才適合輕一點靠近"],
        },
        {
            "title": "完整星盤依據",
            "preview": ["本命需求、合盤相位、當下行運逐層列出", "每個判斷標示可用與不可用邊界"],
        },
        {
            "title": "個人化行動策略",
            "preview": ["該做 5 件事", "不該做 5 件事", "什麼話會讓對方退開"],
        },
        {
            "title": "你的關係盲點",
            "preview": ["你在這段關係中看不見的模式", "不改就算重新靠近也會再卡住的地方"],
        },
    ]
    if relationship_theme:
        theme_rows = repeated_theme_included_rows(relationship_theme)
        if theme_rows:
            selected_rows = theme_rows
        else:
            selected_rows = by_question.get(question) or by_question["still-love-me"]
    else:
        selected_rows = by_question.get(question) or by_question["still-love-me"]
    return [
        {
            "title": western_public_copy(row.get("title")),
            "preview": western_public_copy_list(row.get("preview") or []),
            **{
                key: value
                for key, value in repeated_theme_metadata(relationship_theme or {}).items()
                if key in {"themeKey", "relationshipThemeLabel", "source", "methodClaimIds"}
            },
        }
        for row in [*selected_rows, *common_rows]
    ]


def scenario_metrics(
    score: int,
    pressure_score: int,
    context: dict[str, str],
    relationship_theme: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    question = context.get("main_question", "")
    action = "先保護自己" if context.get("emotional_risk") in {"desperate", "unsafe-or-overwhelmed"} else "先穩住"
    chance_label = "關係條件"
    chance_helper = "看步調"
    if context.get("relationship_stage") == "broke-up-long":
        action = "輕一點試探"
    if context.get("relationship_stage") == "crisis":
        action = "先慢下來"
    if question == "any-chance":
        chance_label = "修復條件"
        chance_helper = "先看條件"
        action = "慢慢靠近"
    elif question == "when-to-contact":
        chance_label = "開口時機"
        chance_helper = "先看狀態"
        action = "先等變輕"
    elif question == "what-did-i-do-wrong":
        chance_label = "修復線索"
        chance_helper = "先拆循環"
        action = "先停自責"
    elif question == "stay-or-let-go":
        chance_label = "等待條件"
        chance_helper = "先看會不會更累"
    metrics = [
        {"key": "attraction", "label": "在意程度", "value": level_from_score(score), "helper": "仍有反應"},
        {"key": "pressure", "label": "卡住程度", "value": level_from_score(pressure_score), "helper": "容易退開"},
        {"key": "chance", "label": chance_label, "value": "有條件", "helper": chance_helper},
        {"key": "action", "label": "最佳行動", "value": action, "helper": "先觀察"},
    ]
    theme_metrics = repeated_theme_metrics(relationship_theme, score, pressure_score, action)
    return theme_metrics or metrics


THEME_REASON_CARD_TEMPLATES = {
    "saturn_pressure": [
        {
            "label": "界線變硬",
            "body": "土星相關線索反覆出現時，關係容易從想靠近變成怕被要求。這裡要先看誰在收緊、誰在追答案。",
            "value": "pressure",
        },
        {
            "label": "表達變慢",
            "body": "慢不一定等於沒感覺，也可能是在評估責任、害怕承擔，或怕再次受傷。",
            "value": "pressure",
        },
        {
            "label": "先減少要求",
            "body": "能不能讓對方不用立刻給關係答案，比你把話說得多完整更重要。",
            "value": "mixed",
        },
    ],
    "emotional_safety": [
        {
            "label": "安心感是核心",
            "body": "安全感線索反覆出現時，重點不是只有喜不喜歡，而是脆弱時能不能被接住。",
            "value": "pressure",
        },
        {
            "label": "反應容易被放大",
            "body": "一方想確認，另一方可能先縮回去；這會讓小反應看起來像整段關係的答案。",
            "value": "mixed",
        },
        {
            "label": "先讓感受落地",
            "body": "要修復，先用具體、安穩、可退回的位置說話，不要一次倒出所有不安。",
            "value": "score",
        },
    ],
    "communication_repair": [
        {
            "label": "話會碰到自尊",
            "body": "溝通線索反覆出現時，問題常不是講太少，而是話一出口就像說服、糾正或逼表態。",
            "value": "pressure",
        },
        {
            "label": "越解釋越緊",
            "body": "越急著補充完整，越容易讓對方只聽見被推著回答，而不是聽見你的本意。",
            "value": "pressure",
        },
        {
            "label": "一句話就好",
            "body": "比較適合短、清楚、沒有追問的一句話；先讓對話能回來，不急著談完整段關係。",
            "value": "score",
        },
    ],
    "attraction_pursuit": [
        {
            "label": "好感不是單點",
            "body": "吸引、欣賞或想靠近的線索不只一個，所以可以說有反應；但這還不是承諾。",
            "value": "score",
        },
        {
            "label": "熱度要被接住",
            "body": "火花如果沒有安全感和現實回應接住，容易變成一下靠近、一下退開。",
            "value": "mixed",
        },
        {
            "label": "看自然回應",
            "body": "真正要看的不是你能不能再點燃感覺，而是對方能不能自然接住一點善意。",
            "value": "score",
        },
    ],
    "action_conflict": [
        {
            "label": "速度容易互相刺激",
            "body": "行動和衝突線索反覆出現時，一方想快點處理，另一方可能只感覺被推著走。",
            "value": "pressure",
        },
        {
            "label": "先不要測試",
            "body": "現在不適合用攤牌、追問或突然靠近測反應；那會讓本來的小火花變成對抗。",
            "value": "pressure",
        },
        {
            "label": "先把速度放小",
            "body": "下一步只做一件小事，讓互動能停在可承受的位置，不要一次處理全部。",
            "value": "score",
        },
    ],
    "identity_rhythm": [
        {
            "label": "自尊感會被碰到",
            "body": "自我感線索反覆出現時，對方怎麼被尊重、怎麼被看見，會直接影響他能不能放鬆。",
            "value": "pressure",
        },
        {
            "label": "不要逼他承認",
            "body": "越要求對方立刻承認心意，越可能讓他先保護面子或拉開距離。",
            "value": "pressure",
        },
        {
            "label": "先留台階",
            "body": "比較好的做法是讓對話有台階，不用把對方推到非黑即白的位置。",
            "value": "mixed",
        },
    ],
    "outer_intensity": [
        {
            "label": "強度不是答案",
            "body": "強烈感受反覆出現時，可能有吸引、想像或投射；但不能直接翻成穩定愛意。",
            "value": "score",
        },
        {
            "label": "界線要更清楚",
            "body": "越強烈，越要把現實回應、對方界線和自己的不安分開看。",
            "value": "pressure",
        },
        {
            "label": "先回到可觀察",
            "body": "下一步只看對方是否有穩定、可看見的回應，不用猜測或放大氣氛。",
            "value": "mixed",
        },
    ],
}


THEME_CHANCE_NOTE_TEMPLATES = {
    "saturn_pressure": [
        "這段關係不是不能靠近，而是靠近時很容易變沉重；機會要看彼此能不能先放下審問感。",
        "如果一開口就要結論，對方比較可能先把界線收緊，所以這裡要用保守方式判斷。",
        "接下來先看回應能不能變自然，不要用一次談話要求整段關係表態。",
    ],
    "emotional_safety": [
        "這段關係的機會要先看安心感能不能回來，不是只看對方有沒有一時反應。",
        "越想確認，越要把話說得具體、安穩，不把所有不安一次交給對方處理。",
        "如果對方能接住小而清楚的表達，再判斷後面能不能慢慢靠近。",
    ],
    "communication_repair": [
        "這段關係的機會卡在說話方式，不一定是完全沒有感覺。",
        "現在不適合長篇解釋；越想講完整，對方越可能只聽見你在要求答案。",
        "先用一句清楚、沒有追問的話讓對話能回來，再看後續反應。",
    ],
    "attraction_pursuit": [
        "好感或火花可以看見，但它還不是承諾；機會要看熱度能不能被穩定回應接住。",
        "如果只有忽然熱絡，沒有後續一致行動，判斷仍要保守。",
        "下一步不要放大一次互動，先看對方能不能自然延續一點善意。",
    ],
    "action_conflict": [
        "這段關係比較怕一急就升溫；機會不是靠測反應換來的。",
        "越想快點處理，越要先把動作變小，避免把本來能談的事推成對抗。",
        "先看彼此能不能在不攤牌的情況下有一點穩定互動。",
    ],
    "identity_rhythm": [
        "這段關係要保留彼此的自尊感；機會不適合靠逼對方承認來確認。",
        "如果開口讓對方覺得被審判或被比較，他會比較難放鬆回應。",
        "先用讓雙方都有台階的方式靠近，再看對方是否願意自然接話。",
    ],
    "outer_intensity": [
        "強烈感受可以是真實線索，但不能直接等於穩定愛意。",
        "越強烈，越要回到可觀察的行動，不要靠猜測或氣氛下結論。",
        "下一步先守住界線，只看對方是否有清楚、持續的回應。",
    ],
}


THEME_TIMELINE_TEMPLATES = {
    "saturn_pressure": [
        {"range": "第 1-2 天", "title": "先把話變輕", "body": "不要急著談責任、承諾或誰對誰錯，先讓互動離開沉重感。"},
        {"range": "第 3-5 天", "title": "只留一個好接的話題", "body": "如果要開口，只提一件具體小事，讓對方可以回，也可以先不回。"},
        {"range": "第 6-7 天", "title": "看他有沒有放鬆一點", "body": "重點不是馬上談復合，而是看回應是否比之前少一點防備。"},
    ],
    "emotional_safety": [
        {"range": "第 1-2 天", "title": "先安頓自己的不安", "body": "不要把所有感受一次倒出來，先整理成一句最需要被理解的話。"},
        {"range": "第 3-5 天", "title": "用具體感受開口", "body": "如果要說，說一件具體情境和你的感受，不要求對方立刻安撫你。"},
        {"range": "第 6-7 天", "title": "看對方能不能接住", "body": "如果他願意回應，再慢慢延續；如果沒有，就先停在保護自己的位置。"},
    ],
    "communication_repair": [
        {"range": "第 1-2 天", "title": "先刪掉多餘解釋", "body": "不要寫成長文，也不要把每個誤會一次補完，先留下最清楚的一句話。"},
        {"range": "第 3-5 天", "title": "只送出一個小回應", "body": "用沒有追問的方式開口，讓對話有機會回來，而不是逼出結論。"},
        {"range": "第 6-7 天", "title": "跟著回應調整", "body": "有回應就延續一點，沒有回應就先停，不用再補第二段說明。"},
    ],
    "attraction_pursuit": [
        {"range": "第 1-2 天", "title": "先不要放大火花", "body": "把有反應當線索，不要立刻談復合或要求確認關係。"},
        {"range": "第 3-5 天", "title": "看他能不能自然接住", "body": "如果有互動，只延續一件小事，不把話題推滿。"},
        {"range": "第 6-7 天", "title": "用穩定回應判斷", "body": "看回應是否持續，而不是靠一次熱絡下結論。"},
    ],
    "action_conflict": [
        {"range": "第 1-2 天", "title": "先停止測反應", "body": "不要突然靠近、攤牌或丟問題，先讓情緒從對抗裡退一步。"},
        {"range": "第 3-5 天", "title": "只做一件小事", "body": "如果要行動，只選一個不刺激對方的動作，不一次處理全部問題。"},
        {"range": "第 6-7 天", "title": "看互動有沒有降溫", "body": "能平穩說話再往下走；如果一碰就吵，先不要再推進。"},
    ],
    "identity_rhythm": [
        {"range": "第 1-2 天", "title": "先保留彼此台階", "body": "不要要求對方立刻承認心意，也不要把問題說成誰比較不在乎。"},
        {"range": "第 3-5 天", "title": "用尊重感開場", "body": "如果要開口，先承認彼此都需要空間，不把對方推到非黑即白。"},
        {"range": "第 6-7 天", "title": "看他能否自然靠近", "body": "真正要看的不是他有沒有被說服，而是他是否願意比較自在地接話。"},
    ],
    "outer_intensity": [
        {"range": "第 1-2 天", "title": "先回到現實線索", "body": "不要用強烈感受替對方下結論，先看他實際做了什麼。"},
        {"range": "第 3-5 天", "title": "把界線說清楚", "body": "如果要互動，只保留清楚、可退回的位置，不用情緒強度換答案。"},
        {"range": "第 6-7 天", "title": "看行動是否持續", "body": "有持續回應才繼續觀察；只有氣氛或猜測，就先不要加碼。"},
    ],
}


THEME_DONT_TEMPLATES = {
    "saturn_pressure": [
        "不要要求對方立刻給關係答案",
        "不要把沉默解讀成你需要再講更多",
        "不要用長訊息追責或翻舊帳",
    ],
    "emotional_safety": [
        "不要一次倒出所有不安",
        "不要用反覆確認換安心",
        "不要把一次冷淡當成全部答案",
    ],
    "communication_repair": [
        "不要連續補充解釋",
        "不要把訊息寫成辯論或說服",
        "不要一句話裡同時道歉、質問又求確認",
    ],
    "attraction_pursuit": [
        "不要把一次熱絡當成承諾",
        "不要用曖昧感加速談復合",
        "不要為了延續火花故意丟測試題",
    ],
    "action_conflict": [
        "不要突然攤牌或逼對方選邊",
        "不要用冷處理測試他在不在乎",
        "不要在一碰就吵時繼續推進",
    ],
    "identity_rhythm": [
        "不要逼對方立刻承認心意",
        "不要把問題說成誰比較不在乎",
        "不要用比較、嘲諷或失望感讓他低頭",
    ],
    "outer_intensity": [
        "不要用強烈感受替對方下結論",
        "不要靠猜測、試探或控制感換答案",
        "不要把一時氣氛寫成命定結果",
    ],
}


THEME_METRIC_TEMPLATES = {
    "saturn_pressure": [
        {"key": "attraction", "label": "靠近感", "value": "score", "helper": "仍有牽引"},
        {"key": "pressure", "label": "界線緊度", "value": "pressure", "helper": "容易變重"},
        {"key": "chance", "label": "修復條件", "value": "有條件", "helper": "先減要求"},
        {"key": "action", "label": "最佳行動", "value": "先放輕", "helper": "留出空間"},
    ],
    "emotional_safety": [
        {"key": "attraction", "label": "安心程度", "value": "score", "helper": "需要被接住"},
        {"key": "pressure", "label": "不安觸發", "value": "pressure", "helper": "容易放大"},
        {"key": "chance", "label": "靠近條件", "value": "有條件", "helper": "先給安穩"},
        {"key": "action", "label": "最佳行動", "value": "先安頓", "helper": "說得具體"},
    ],
    "communication_repair": [
        {"key": "attraction", "label": "對話可能", "value": "score", "helper": "仍可修復"},
        {"key": "pressure", "label": "誤解風險", "value": "pressure", "helper": "話別太滿"},
        {"key": "chance", "label": "修復條件", "value": "有條件", "helper": "一句就好"},
        {"key": "action", "label": "最佳行動", "value": "先短說", "helper": "不追問"},
    ],
    "attraction_pursuit": [
        {"key": "attraction", "label": "好感反應", "value": "score", "helper": "有火花"},
        {"key": "pressure", "label": "穩定難度", "value": "pressure", "helper": "別推太快"},
        {"key": "chance", "label": "穩定條件", "value": "有條件", "helper": "看後續"},
        {"key": "action", "label": "最佳行動", "value": "先輕靠近", "helper": "不加速"},
    ],
    "action_conflict": [
        {"key": "attraction", "label": "行動火花", "value": "score", "helper": "容易升溫"},
        {"key": "pressure", "label": "衝突風險", "value": "pressure", "helper": "先控速"},
        {"key": "chance", "label": "緩和條件", "value": "有條件", "helper": "少測試"},
        {"key": "action", "label": "最佳行動", "value": "先停一下", "helper": "不攤牌"},
    ],
    "identity_rhythm": [
        {"key": "attraction", "label": "被看見感", "value": "score", "helper": "仍在意"},
        {"key": "pressure", "label": "表態難度", "value": "pressure", "helper": "別逼承認"},
        {"key": "chance", "label": "靠近條件", "value": "有條件", "helper": "留台階"},
        {"key": "action", "label": "最佳行動", "value": "先尊重", "helper": "別比較"},
    ],
    "outer_intensity": [
        {"key": "attraction", "label": "強烈程度", "value": "score", "helper": "感受很重"},
        {"key": "pressure", "label": "投射風險", "value": "pressure", "helper": "回到現實"},
        {"key": "chance", "label": "穩定條件", "value": "有條件", "helper": "看行動"},
        {"key": "action", "label": "最佳行動", "value": "先守界線", "helper": "不猜測"},
    ],
}


THEME_INCLUDED_READING_ROW_TEMPLATES = {
    "saturn_pressure": [
        {"title": "界線為什麼變硬", "preview": ["哪些相位讓靠近變沉重", "分辨慢回應、怕承擔與沒感覺"]},
        {"title": "怎麼靠近才不變重", "preview": ["該少問哪些問題", "怎麼讓對方不用立刻表態"]},
        {"title": "能否修復要看什麼", "preview": ["回應是否變自然", "界線是否開始鬆動"]},
    ],
    "emotional_safety": [
        {"title": "安全感卡在哪裡", "preview": ["誰容易不安、誰容易退開", "情緒需求能不能被接住"]},
        {"title": "怎麼說比較安心", "preview": ["把感受說具體", "避免一次倒出所有不安"]},
        {"title": "靠近前要看什麼", "preview": ["對方是否能接住小回應", "互動能不能慢慢穩下來"]},
    ],
    "communication_repair": [
        {"title": "話為什麼說不開", "preview": ["哪些語氣容易變成說服", "哪一種解釋會越講越緊"]},
        {"title": "一句話修復路徑", "preview": ["短訊息怎麼保留退路", "不要一次把整段關係講完"]},
        {"title": "回應後怎麼判讀", "preview": ["有回應如何延續", "沒回應時何時該先停"]},
    ],
    "attraction_pursuit": [
        {"title": "好感能不能被接住", "preview": ["哪些星盤線索支持靠近感", "火花和承諾要分開看"]},
        {"title": "不要把熱絡當答案", "preview": ["一次互動不能放大", "看後續是否穩定延續"]},
        {"title": "輕靠近的順序", "preview": ["從小話題開始", "不急著確認關係"]},
    ],
    "action_conflict": [
        {"title": "一急就升溫的原因", "preview": ["誰想快點處理", "誰會覺得被推著走"]},
        {"title": "避免對抗的做法", "preview": ["不要攤牌或測試", "先把動作變小"]},
        {"title": "何時才適合再談", "preview": ["互動能否平穩", "能不能只談一件小事"]},
    ],
    "identity_rhythm": [
        {"title": "自尊感怎麼被碰到", "preview": ["被看見和被尊重的差異", "為什麼越逼越難承認"]},
        {"title": "留台階的靠近方式", "preview": ["不比較、不嘲諷", "讓對方不用立刻證明"]},
        {"title": "自然回應怎麼判讀", "preview": ["看他是否比較自在", "不要把說服當作修復"]},
    ],
    "outer_intensity": [
        {"title": "強烈感從哪裡來", "preview": ["吸引、想像與投射分開看", "不把強度寫成命定"]},
        {"title": "先回到可觀察線索", "preview": ["看實際行動", "不靠猜測補答案"]},
        {"title": "界線清楚才有方向", "preview": ["哪些互動可以保留", "哪些情緒不適合加碼"]},
    ],
}


def repeated_theme_metadata(relationship_theme: dict[str, Any]) -> dict[str, Any]:
    theme_key = str(relationship_theme.get("themeKey") or "")
    if not theme_key:
        return {}
    return {
        "themeKey": theme_key,
        "relationshipThemeLabel": str(relationship_theme.get("label") or ""),
        "source": str(relationship_theme.get("source") or "burk-repeated-themes-outweigh-single-contacts"),
        "methodClaimIds": relationship_theme.get("methodClaimIds") or [],
    }


def repeated_theme_chance_notes(relationship_theme: dict[str, Any]) -> list[str]:
    theme_key = str(relationship_theme.get("themeKey") or "")
    return [str(item) for item in THEME_CHANCE_NOTE_TEMPLATES.get(theme_key, []) if item]


def repeated_theme_timeline_steps(relationship_theme: dict[str, Any]) -> list[dict[str, Any]]:
    theme_key = str(relationship_theme.get("themeKey") or "")
    templates = THEME_TIMELINE_TEMPLATES.get(theme_key) or []
    metadata = repeated_theme_metadata(relationship_theme)
    return [{**template, **metadata} for template in templates]


def repeated_theme_donts(relationship_theme: dict[str, Any]) -> list[str]:
    theme_key = str(relationship_theme.get("themeKey") or "")
    return [str(item) for item in THEME_DONT_TEMPLATES.get(theme_key, []) if item]


def repeated_theme_included_rows(relationship_theme: dict[str, Any]) -> list[dict[str, Any]]:
    theme_key = str(relationship_theme.get("themeKey") or "")
    return [dict(item) for item in THEME_INCLUDED_READING_ROW_TEMPLATES.get(theme_key, [])]


def repeated_theme_metric_value(value_key: Any, score: int, pressure_score: int, action: str) -> str:
    if value_key == "score":
        return level_from_score(score)
    if value_key == "pressure":
        return level_from_score(pressure_score)
    if value_key == "action":
        return action
    return str(value_key or "")


def repeated_theme_metrics(
    relationship_theme: dict[str, Any] | None,
    score: int,
    pressure_score: int,
    action: str,
) -> list[dict[str, Any]]:
    if not relationship_theme:
        return []
    theme_key = str(relationship_theme.get("themeKey") or "")
    templates = THEME_METRIC_TEMPLATES.get(theme_key) or []
    metadata = repeated_theme_metadata(relationship_theme)
    return [
        {
            "key": str(template.get("key") or ""),
            "label": str(template.get("label") or ""),
            "value": repeated_theme_metric_value(template.get("value"), score, pressure_score, action),
            "helper": str(template.get("helper") or ""),
            **metadata,
        }
        for template in templates
    ]


def theme_reason_card_value(kind: str, score: int, pressure_score: int, risk_value: int, contact_value: int) -> int:
    if kind == "score":
        return score
    if kind == "pressure":
        return pressure_score
    if kind == "risk":
        return risk_value
    if kind == "contact":
        return contact_value
    return clamp_score((score + pressure_score + contact_value) / 3)


def repeated_theme_reason_cards(
    *,
    score: int,
    pressure_score: int,
    risk_value: int,
    contact_value: int,
    relationship_theme: dict[str, Any],
) -> list[dict[str, Any]]:
    theme_key = str(relationship_theme.get("themeKey") or "")
    templates = THEME_REASON_CARD_TEMPLATES.get(theme_key)
    if not templates:
        return []
    theme_label = str(relationship_theme.get("label") or "")
    return [
        {
            "label": str(template.get("label") or ""),
            "body": str(template.get("body") or ""),
            "value": theme_reason_card_value(str(template.get("value") or "mixed"), score, pressure_score, risk_value, contact_value),
            "themeKey": theme_key,
            "relationshipThemeLabel": theme_label,
            "source": str(relationship_theme.get("source") or "burk-repeated-themes-outweigh-single-contacts"),
            "methodClaimIds": relationship_theme.get("methodClaimIds") or [],
        }
        for template in templates
    ]


def reason_cards(
    score: int,
    pressure_score: int,
    context: dict[str, str],
    relationship_theme: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    question = context.get("main_question", "")
    risk = context.get("emotional_risk", "")
    risk_value = 84 if risk in {"anxious", "self-blaming", "desperate", "unsafe-or-overwhelmed"} else 62
    contact_value = 82 if context.get("contact_status") in {"no-contact", "blocked"} else 68
    if relationship_theme:
        cards = repeated_theme_reason_cards(
            score=score,
            pressure_score=pressure_score,
            risk_value=risk_value,
            contact_value=contact_value,
            relationship_theme=relationship_theme,
        )
        if cards:
            return cards
    if question == "any-chance":
        return [
            {"label": "修復條件", "body": "有在意不等於可以立刻復合；先看你們還能不能用比較輕的方式自然接上。", "value": score},
            {"label": "舊模式門檻", "body": "越急著告白、追問或翻舊帳，越容易把對方推回原本的保護狀態。", "value": pressure_score},
            {"label": "重啟線索", "body": "對方有沒有自然接住、願不願意延續話題，比你把訊息修到完美更重要。", "value": clamp_score((score + contact_value) / 2)},
        ]
    if question == "when-to-contact":
        return [
            {"label": "開口時機", "body": "現在先看這段互動承不承受得住訊息，再用月份區間抓低壓靠近的節奏。", "value": pressure_score},
            {"label": "語氣門檻", "body": "訊息要短一點、輕一點、沒有要求；一像追問就容易讓對方退開。", "value": contact_value},
            {"label": "可以開口的狀態", "body": "當你能用短、輕、可停下的方式開口時，訊息才比較有空間被接住。", "value": score},
        ]
    if question == "what-did-i-do-wrong":
        return [
            {"label": "自責放大", "body": "這一題先幫你把全責自責停下來；星盤拆的是互動循環和可調整的位置。", "value": risk_value},
            {"label": "溝通觸發", "body": "真正要看的是哪種語氣和反應會讓兩個人更難接住彼此。", "value": pressure_score},
            {"label": "可調整的互動", "body": "你能調整的是自己的表達和步調，先把下一次互動變得更輕、更清楚。", "value": score},
        ]
    if question == "stay-or-let-go":
        return [
            {"label": "會不會更累", "body": "有在意不代表就值得繼續撐下去，先看這段關係有沒有讓你越來越不穩。", "value": pressure_score},
            {"label": "等待條件", "body": "只有緊繃感降下來、回應變穩，等待才不是你一個人在撐。", "value": score},
            {"label": "自我保護", "body": "越急著做決定，越要先把自己從最緊繃的狀態拉回來。", "value": risk_value},
        ]
    return [
        {"label": "穩定回應", "body": "還看得到吸引和情緒反應，但要看它能不能穩定出現，不能直接當成表態。", "value": score},
        {"label": "不敢表態", "body": "比較像害怕失控或被逼問，不能只用冷淡就判定完全不在乎。", "value": pressure_score},
        {"label": "追問感", "body": "越想立刻問清楚，越容易讓對話變成逼答案，反而看不清真正反應。", "value": risk_value},
    ]


def chance_note_list(question: str, stage: str, relationship_theme: dict[str, Any] | None = None) -> list[str]:
    if relationship_theme:
        theme_notes = repeated_theme_chance_notes(relationship_theme)
        if theme_notes:
            return theme_notes
    if question == "when-to-contact":
        return ["目前只能看什麼時候比較好開口，不適合靠訊息逼出關係結論。", "如果要聯絡，語氣要短、輕、不要求立刻回；不要一開口談復合。", "送出後先看對方有沒有自然接住，不把一次回覆當成全部答案。"]
    if question == "what-did-i-do-wrong":
        return ["修復先從看見互動循環開始，不是把責任全放回你身上。", "如果道歉變成求安慰，對方反而更難接住。", "先改一個可調整的互動，比一次說完所有後悔更有效。"]
    if question == "stay-or-let-go":
        return ["仍有在意，但要不要繼續等，要看現實行動，不只看感覺。", "先看互動有沒有真的變穩，再決定要不要等。", "如果這段關係一直讓你更累，先慢下來比硬撐更重要。"]
    if question == "any-chance":
        return ["還有重新靠近的可能，但要先確認修復條件，不要用舊模式重新開始。", "重點是先恢復比較輕、比較自然的互動，不是立刻談復合。", "對方有沒有自然接住，比你一次訊息寫得多完整更重要。"]
    if stage == "broke-up-long":
        return ["還有重新靠近的可能，但不能用舊模式重新開始。", "重點是先恢復比較輕、比較自然的互動，不是立刻談復合。", "對方有沒有自然接住，比你一次訊息寫得多完整更重要。"]
    return ["有反應，但速度要先放慢。", "如果對方有穩定回應，才有重新靠近的空間。", "現在不適合追問他心裡還有沒有你，比較適合觀察實際回應。"]


def answer_source_claim_ids(answer_layer: dict[str, Any]) -> list[str]:
    return unique(str(item) for item in answer_layer.get("questionClaimIds") or [] if item)


def attach_reason_readable(
    cards: list[dict[str, Any]],
    *,
    context: dict[str, str],
    source_claim_ids: list[str],
    question_selector: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    question = context.get("main_question", "")
    stage = context.get("relationship_stage", "")
    selector = question_selector or question_selector_trace(question)
    selector_method_claim_ids = [str(item) for item in selector.get("methodClaimIds") or [] if item]
    selector_evidence_cluster_keys = [str(item) for item in selector.get("evidenceClusterKeys") or [] if item]
    output: list[dict[str, Any]] = []
    for card in cards:
        readable = reason_card_readable_interpretation(
            label=str(card.get("label") or ""),
            body=str(card.get("body") or ""),
            value=int(card.get("value") or 0),
            question_key=question,
            stage_key=stage,
            source_claim_ids=source_claim_ids,
            question_selector=selector,
        )
        output.append({
            **card,
            "questionSelector": selector,
            "methodClaimIds": unique([*list(card.get("methodClaimIds") or []), *selector_method_claim_ids]),
            "selectorEvidenceClusterKeys": selector_evidence_cluster_keys,
            "readableInterpretation": readable,
            "nextMove": readable.get("nextMove"),
        })
    return output


def attach_timeline_readable(
    steps: list[dict[str, Any]],
    *,
    context: dict[str, str],
    source_claim_ids: list[str],
    question_selector: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    question = context.get("main_question", "")
    stage = context.get("relationship_stage", "")
    selector = question_selector or question_selector_trace(question)
    selector_method_claim_ids = [str(item) for item in selector.get("methodClaimIds") or [] if item]
    selector_evidence_cluster_keys = [str(item) for item in selector.get("evidenceClusterKeys") or [] if item]
    output: list[dict[str, Any]] = []
    for step in steps:
        readable = timeline_step_readable_interpretation(
            range_label=str(step.get("range") or ""),
            title=str(step.get("title") or ""),
            body=str(step.get("body") or ""),
            question_key=question,
            stage_key=stage,
            source_claim_ids=source_claim_ids,
            question_selector=selector,
        )
        output.append({
            **step,
            "questionSelector": selector,
            "methodClaimIds": unique([*list(step.get("methodClaimIds") or []), *selector_method_claim_ids]),
            "selectorEvidenceClusterKeys": selector_evidence_cluster_keys,
            "readableInterpretation": readable,
            "nextMove": readable.get("nextMove"),
        })
    return output


def chance_payload(
    *,
    value: int,
    notes: list[str],
    context: dict[str, str],
    source_claim_ids: list[str],
    relationship_theme: dict[str, Any] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question = context.get("main_question", "")
    selector = question_selector or question_selector_trace(question)
    selector_method_claim_ids = [str(item) for item in selector.get("methodClaimIds") or [] if item]
    theme_method_claim_ids = [str(item) for item in (relationship_theme or {}).get("methodClaimIds") or [] if item]
    readable = chance_readable_interpretation(
        value=value,
        notes=notes,
        question_key=question,
        stage_key=context.get("relationship_stage", ""),
        source_claim_ids=source_claim_ids,
        question_selector=selector,
    )
    return {
        "value": value,
        "notes": notes,
        "relationshipTheme": relationship_theme or {},
        "questionSelector": selector,
        "methodClaimIds": unique([*theme_method_claim_ids, *selector_method_claim_ids]),
        "selectorEvidenceClusterKeys": [str(item) for item in selector.get("evidenceClusterKeys") or [] if item],
        "readableInterpretation": readable,
        "nextMove": readable.get("nextMove"),
    }


def cluster_claim_ids(*clusters: dict[str, Any]) -> list[str]:
    return unique(
        [
            str(claim_id)
            for cluster in clusters
            for claim_id in (cluster.get("claimIds") or [])
            if claim_id
        ]
    )


def build_complete_relationship_result_view_model(
    fixture: dict[str, Any],
    articles: dict[str, dict[str, Any]],
    claims_by_article: dict[str, list[dict[str, Any]]] | None = None,
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    structured_kb = structured_kb if structured_kb is not None else load_structured_kb()
    context = fixture.get("runtime_context") or fixture.get("context") or {}
    selection = fixture.get("selection") or {}
    slots = slot_map(selection)
    stage = context.get("relationship_stage", "")
    question = context.get("main_question", "")
    risk = context.get("emotional_risk", "")
    western_id = slot_article_id(slots, "western_core") or strongest_western_relationship_signal_id(fixture, None)

    western_insight_title = article_title(western_id, articles) if western_id else western_missing_title()
    western_insight_body = western_body(western_id) if western_id else western_unavailable_reason(fixture)
    western_insight_source = western_id or "western-calculation"
    western_case_file = western_relationship_case_file(fixture, context, structured_kb)
    western_case_file = attach_western_claim_support(western_case_file, claims_by_article or {})
    relationship_profiles = western_relationship_profiles(fixture, western_case_file)
    relationship_insights = western_case_file.get("relationshipInsightLayer") or {}
    relationship_thesis = western_case_file.get("relationshipThesis") or {}
    score = western_case_file_score(western_case_file, context)
    pressure_score = western_case_file_pressure_score(western_case_file, context)
    answer_layer = western_case_file.get("answerLayer") or {}
    status_answer_policy = western_case_file.get("relationshipStatusAnswerPolicy") or answer_layer.get("statusAnswerPolicy") or {}
    repeated_theme_context = answer_layer.get("repeatedThemeContext") or {}
    included_rows = included_reading_items(context, repeated_theme_context)
    reading_blueprint = western_relationship_reading_blueprint(western_case_file, context, included_rows, structured_kb)
    chapter_evidence_payload = western_chapter_evidence_from_blueprint(reading_blueprint)
    source_chips = western_source_chips(western_id, articles)
    reading_answer = western_public_copy(answer_layer.get("shortAnswer") or "西洋合盤看得到吸引，但這份解讀只給方向，不能給保證。")
    question_label = str(status_answer_policy.get("questionRewrite") or western_question_label(structured_kb, question))
    source_claim_ids = answer_source_claim_ids(answer_layer)
    question_selector = answer_layer.get("questionSelector") or question_selector_trace(question)
    chance_notes = chance_note_list(question, stage, repeated_theme_context)
    contact_policy = (western_case_file.get("evidenceClusters") or {}).get("contactSituationPolicy") or {}
    contact_policy_claim_ids = [str(item) for item in contact_policy.get("claimIds") or [] if item]
    evidence_clusters = western_case_file.get("evidenceClusters") or {}
    timing_window_cluster = evidence_clusters.get("timingWindowBand") or {}
    timing_contact_cluster = evidence_clusters.get("timingContactReducer") or {}
    timing_selector_clusters = {
        key: evidence_clusters.get(key) or {}
        for key in (
            "timingMercuryCommunication",
            "timingVenusSoftening",
            "timingMarsActivation",
            "timingSaturnPressure",
            "timingMoonWeather",
        )
    }
    timing_claim_ids = cluster_claim_ids(timing_window_cluster, timing_contact_cluster, *timing_selector_clusters.values())
    readable_source_claim_ids = unique([*source_claim_ids, *contact_policy_claim_ids, *timing_claim_ids])
    timing_guidance = timing_guidance_payload(
        timing_contact=timing_contact_cluster,
        timing_window=timing_window_cluster,
        timing_selectors=timing_selector_clusters,
        question_key=question,
        stage_key=stage,
        relationship_theme=repeated_theme_context,
        source_claim_ids=unique([*source_claim_ids, *timing_claim_ids]),
        question_selector=question_selector,
    )
    answer_guidance = answer_guidance_payload(
        answer_layer=answer_layer,
        question_key=question,
        question_label=question_label,
        stage_key=stage,
        contact_policy=contact_policy,
        timing_guidance=timing_guidance,
        relationship_theme=repeated_theme_context,
        source_claim_ids=readable_source_claim_ids,
        question_selector=question_selector,
        emotional_risk=risk,
    )
    normal_user_answer = answer_guidance.get("normalUserAnswer") or {}
    reading_answer = str(answer_guidance.get("shortAnswer") or reading_answer)
    thought_items = thoughts(question, stage, risk)
    reason_items = attach_reason_readable(
        reason_cards(score, pressure_score, context, relationship_theme=repeated_theme_context),
        context=context,
        source_claim_ids=readable_source_claim_ids,
        question_selector=question_selector,
    )
    chance_item = chance_payload(
        value=score,
        notes=chance_notes,
        context=context,
        source_claim_ids=readable_source_claim_ids,
        relationship_theme=repeated_theme_context,
        question_selector=question_selector,
    )
    timeline_items = attach_timeline_readable(
        timeline(context, repeated_theme_context),
        context=context,
        source_claim_ids=readable_source_claim_ids,
        question_selector=question_selector,
    )
    dont_items = donts(context, repeated_theme_context)
    readable_question_answer = question_answer_readable_payload(
        question_key=question,
        question_label=question_label,
        stage_key=stage,
        thoughts=thought_items,
        reasons=reason_items,
        chance=chance_item,
        timeline=timeline_items,
        donts=dont_items,
        source_claim_ids=readable_source_claim_ids,
        contact_policy=contact_policy,
        timing_guidance=timing_guidance,
        answer_guidance=answer_guidance,
        relationship_theme=repeated_theme_context,
        question_selector=question_selector,
    )
    action_guidance = (readable_question_answer.get("sections") or {}).get("action") or {}
    relationship_case_model = relationship_case_model_payload(
        context=context,
        question_label=question_label,
        relationship_thesis=relationship_thesis,
        answer_guidance=answer_guidance,
        normal_user_answer=normal_user_answer,
        timing_guidance=timing_guidance,
        action_guidance=action_guidance,
        contact_policy=contact_policy,
        relationship_theme=repeated_theme_context,
    )
    context_storyline = relationship_context_storyline_payload(
        context=context,
        relationship_case_model=relationship_case_model,
        relationship_thesis=relationship_thesis,
        contact_policy=contact_policy,
        timing_guidance=timing_guidance,
        status_answer_policy=status_answer_policy,
    )
    relationship_case_model["statusAnswerPolicy"] = status_answer_policy
    relationship_case_model["contextStoryline"] = context_storyline
    relationship_case_model["evidenceClusterKeys"] = unique([
        *[str(item) for item in relationship_case_model.get("evidenceClusterKeys") or [] if item],
        RELATIONSHIP_CONTEXT_STORYLINE_KEY,
    ])
    for section_id, section_plan in (relationship_case_model.get("sectionPlans") or {}).items():
        if isinstance(section_plan, dict):
            if section_id == "relationship-fit":
                continue
            section_plan["evidenceClusterKeys"] = unique([
                *[str(item) for item in section_plan.get("evidenceClusterKeys") or [] if item],
                RELATIONSHIP_CONTEXT_STORYLINE_KEY,
            ])
    western_case_file["relationshipCaseModel"] = relationship_case_model
    western_case_file["relationshipContextStoryline"] = context_storyline
    western_case_file.setdefault("evidenceClusters", {})[RELATIONSHIP_CONTEXT_STORYLINE_KEY] = relationship_context_storyline_cluster(context_storyline)
    western_case_file.setdefault("evidenceClusters", {})["relationshipStatusAnswerPolicy"] = relationship_status_answer_policy_cluster(status_answer_policy)
    dominant_narrative_angle = dominant_narrative_angle_payload(
        context=context,
        relationship_case_model=relationship_case_model,
        relationship_thesis=relationship_thesis,
    )
    western_case_file["dominantNarrativeAngle"] = dominant_narrative_angle
    final_interpretation = final_reading_interpretation_payload(
        question_key=question,
        question_label=question_label,
        stage_key=stage,
        relationship_profiles=relationship_profiles,
        relationship_archetype=relationship_insights.get("relationshipArchetype") or {},
        attraction_dynamics=relationship_insights.get("attractionDynamics") or {},
        conflict_dynamics=relationship_insights.get("conflictDynamics") or {},
        growth_dynamics=relationship_insights.get("growthDynamics") or {},
        partner_needs=relationship_insights.get("partnerNeeds") or {},
        fight_landmines=relationship_insights.get("fightLandmines") or {},
        survival_guide=relationship_insights.get("survivalGuide") or {},
        relationship_turning_windows=relationship_insights.get("relationshipTurningWindows") or {},
        answer_guidance=answer_guidance,
        normal_user_answer=normal_user_answer,
        timing_guidance=timing_guidance,
        action_guidance=action_guidance,
        contact_policy=contact_policy,
        relationship_theme=repeated_theme_context,
        relationship_thesis=relationship_thesis,
        relationship_case_model=relationship_case_model,
        dominant_narrative_angle=dominant_narrative_angle,
        context_storyline=context_storyline,
        source_claim_ids=readable_source_claim_ids,
        question_selector=question_selector,
    )
    readable_question_answer.setdefault("sections", {})["finalInterpretation"] = final_interpretation
    relationship_fit_lens_payload = relationship_fit_lens(
        relationship_profiles=relationship_profiles,
        relationship_archetype=relationship_insights.get("relationshipArchetype") or {},
        attraction_dynamics=relationship_insights.get("attractionDynamics") or {},
        conflict_dynamics=relationship_insights.get("conflictDynamics") or {},
        growth_dynamics=relationship_insights.get("growthDynamics") or {},
        partner_needs=relationship_insights.get("partnerNeeds") or {},
        fight_landmines=relationship_insights.get("fightLandmines") or {},
        survival_guide=relationship_insights.get("survivalGuide") or {},
        action_guidance=action_guidance,
    )

    view_model = {
        "contractVersion": "complete-relationship-result-v1",
        "id": fixture.get("reading_id"),
        "label": f"{STAGE_LABELS.get(stage, stage)} · {question_label}",
        "context": context,
        "brand": BRAND,
        "westernRelationshipCaseFile": western_case_file,
        "relationshipProfiles": relationship_profiles,
        "relationshipFitLens": relationship_fit_lens_payload,
        "relationshipArchetype": relationship_insights.get("relationshipArchetype") or {},
        "attractionDynamics": relationship_insights.get("attractionDynamics") or {},
        "conflictDynamics": relationship_insights.get("conflictDynamics") or {},
        "growthDynamics": relationship_insights.get("growthDynamics") or {},
        "partnerNeeds": relationship_insights.get("partnerNeeds") or {},
        "fightLandmines": relationship_insights.get("fightLandmines") or {},
        "survivalGuide": relationship_insights.get("survivalGuide") or {},
        "relationshipTurningWindows": relationship_insights.get("relationshipTurningWindows") or {},
        "relationshipThesis": relationship_thesis,
        "relationshipStatusAnswerPolicy": status_answer_policy,
        "relationshipCaseModel": relationship_case_model,
        "relationshipContextStoryline": context_storyline,
        "dominantNarrativeAngle": dominant_narrative_angle,
        "sectionNarrativeSpecs": final_interpretation.get("sectionSpecs") or {},
        "readingBlueprint": reading_blueprint,
        "reading": {
            "badge": "完整合盤解讀",
            "question": question_label,
            "stage": STAGE_LABELS.get(stage, stage),
            "answer": western_public_copy(reading_answer),
            "score": score,
            "safety": safety_copy(stage, risk),
        },
        "metrics": scenario_metrics(score, pressure_score, context, repeated_theme_context),
        "calculationSteps": calculation_steps(),
        "authorityReasons": western_authority_reasons(western_case_file, context),
        "chapterEvidence": chapter_evidence_payload,
        "insights": [
            {"label": "西洋核心訊號", "title": western_insight_title, "body": western_insight_body, "source": western_insight_source},
            {"label": "關係階段", "title": STAGE_TITLES.get(stage, "階段訊號"), "body": STAGE_BODIES.get(stage, ""), "source": slot_article_id(slots, "stage") or "missing"},
            {
                "label": "安全提醒",
                "title": "不要用追問換聯絡" if risk not in {"desperate", "unsafe-or-overwhelmed"} else "先保護自己再談關係",
                "body": safety_copy(stage, risk),
                "source": "stage-risk",
            },
        ],
        "thoughts": thought_items,
        "reasons": reason_items,
        "chance": chance_item,
        "timeline": timeline_items,
        "answerGuidance": answer_guidance,
        "normalUserAnswer": normal_user_answer,
        "timingGuidance": timing_guidance,
        "donts": dont_items,
        "readableQuestionAnswer": readable_question_answer,
        "actionGuidance": action_guidance,
        "finalInterpretation": final_interpretation,
        "evidence": {
            "western": {
                "title": "西洋合盤",
                "signal": western_insight_title,
                "summary": western_evidence_summary(fixture, western_id),
                "visual": western_visual(fixture, western_id),
                "points": western_evidence_points(fixture, context, western_id),
                "chips": western_chips(fixture, western_id),
                "aspects": selected_western_aspects(fixture),
            },
        },
        "includedReadingRows": included_rows,
        "sources": source_chips,
        "debug": {
            "stageSlot": slot_article_id(slots, "stage"),
            "questionSlot": slot_article_id(slots, "question"),
            "westernSlot": western_id,
        },
    }
    public_view_model = western_public_payload(view_model)
    refresh_fact_contracts_in_payload(public_view_model)
    return public_view_model

# Backward-compatible aliases for callers that still expect old names.
build_western_free_result_view_model = build_complete_relationship_result_view_model
build_view_model = build_complete_relationship_result_view_model

__all__ = [
    "DEFAULT_ARTICLES_PATH",
    "DEFAULT_CALCULATION_DIR",
    "DEFAULT_CLAIMS_PATH",
    "DEFAULT_OUTPUT_PATH",
    "SCENARIO_ORDER",
    "build_complete_relationship_result_view_model",
    "build_view_model",
    "build_western_free_result_view_model",
    "load_articles",
    "load_claims_by_article",
    "read_json",
]
