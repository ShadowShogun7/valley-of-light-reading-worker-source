import { createHash } from "node:crypto";

const targetUrl = process.env.DASHBOARD_URL ?? "http://127.0.0.1:3000";
const concurrency = positiveInteger(process.env.RELATIONSHIP_API_MATRIX_CONCURRENCY, 4);
const requestTimeoutMs = positiveInteger(process.env.RELATIONSHIP_API_MATRIX_TIMEOUT_MS, 45000);
const expectedStructuredKbSource = process.env.VALLEY_EXPECT_STRUCTURED_KB_SOURCE ?? "local";

const stages = ["ambiguous", "cold-war", "broke-up-recent", "broke-up-long", "crisis"];
const questions = ["still-love-me", "any-chance", "when-to-contact", "what-did-i-do-wrong", "stay-or-let-go"];
const contacts = [
  { input: "none", normalized: "no-contact" },
  { input: "occasional", normalized: "occasional-contact" },
  { input: "cold-chat", normalized: "still-in-contact" },
  { input: "awkward-meeting", normalized: "living-or-working-together" },
  { input: "blocked", normalized: "blocked" }
];

const anchor = {
  stage: "cold-war",
  question: "stay-or-let-go",
  contact: "no-contact"
};

const birthPairs = [
  {
    id: "taipei-taichung",
    user: birthProfile("1995-11-04", "13:00", "台北市", "female"),
    partner: birthProfile("1993-03-15", "10:00", "台中市", "male")
  },
  {
    id: "kaohsiung-tainan",
    user: birthProfile("1992-07-09", "22:10", "高雄市", "female"),
    partner: birthProfile("1990-12-02", "06:40", "台南市", "male")
  },
  {
    id: "taipei-kaohsiung",
    user: birthProfile("1992-02-08", "21:20", "台北市", "female"),
    partner: birthProfile("1991-08-19", "07:45", "高雄市", "male")
  },
  {
    id: "new-taipei-date-only",
    user: birthProfile("1996-02-18", "08:30", "新北市", "female"),
    partner: birthProfile("1994-09-27", "", "台北市", "male", true)
  },
  {
    id: "hong-kong-singapore",
    user: birthProfile("1988-04-12", "05:55", "香港", "female"),
    partner: birthProfile("1989-09-23", "19:35", "新加坡", "male")
  }
];

const sectionIds = [
  "chart-positioning",
  "relationship-fit",
  "core-answer",
  "timing-reading",
  "action-direction"
];
const customerSummaryIds = ["relationship-fit", "core-answer", "timing-reading", "action-direction"];
const visibleFields = ["headline", "meaning", "body", "nextMove", "caution"];
const sectionModules = {
  "chart-positioning": "final_chart_positioning",
  "relationship-fit": "final_relationship_fit",
  "core-answer": "final_core_answer",
  "timing-reading": "final_timing_reading",
  "action-direction": "final_action_direction"
};
const contactPolicies = {
  blocked: { actionMode: "boundary_only", actionScale: 0, canSuggestDirectContact: false },
  "no-contact": { actionMode: "observe_or_single_low_stimulation_test", actionScale: 1, canSuggestDirectContact: true },
  "occasional-contact": { actionMode: "small_bid_response_led", actionScale: 2, canSuggestDirectContact: true },
  "still-in-contact": { actionMode: "tone_repair_in_existing_channel", actionScale: 3, canSuggestDirectContact: true },
  "living-or-working-together": { actionMode: "shared_space_boundary", actionScale: 2, canSuggestDirectContact: true }
};
const stageLabels = {
  ambiguous: "曖昧 / 不確定關係",
  "cold-war": "冷戰 / 斷聯中",
  "broke-up-recent": "剛分手 / 情緒未穩",
  "broke-up-long": "分手一段時間",
  crisis: "還在一起但很不穩"
};
const statusQuestionMarkers = {
  "ambiguous|still-love-me": ["認真"],
  "ambiguous|any-chance": ["發展", "往前"],
  "ambiguous|when-to-contact": ["清楚", "定義"],
  "ambiguous|what-did-i-do-wrong": ["忽冷忽熱", "一近一退"],
  "ambiguous|stay-or-let-go": ["觀察", "值得"],
  "broke-up-recent|still-love-me": ["心意", "在意", "感情", "心裡"],
  "broke-up-recent|any-chance": ["復合", "修復"],
  "broke-up-recent|when-to-contact": ["恢復互動"],
  "broke-up-recent|what-did-i-do-wrong": ["分手", "原因", "自責"],
  "broke-up-recent|stay-or-let-go": ["穩住", "穩下來", "等待"],
  "broke-up-long|still-love-me": ["看你", "怎麼看", "看待", "態度", "伴侶位置"],
  "broke-up-long|any-chance": ["延續", "現實"],
  "broke-up-long|when-to-contact": ["重新開口"],
  "broke-up-long|what-did-i-do-wrong": ["過去", "卡住", "問題"],
  "broke-up-long|stay-or-let-go": ["等", "放下", "投入", "時間"],
  "cold-war|still-love-me": ["主動", "聯絡"],
  "cold-war|any-chance": ["冷戰", "變軟", "鬆動", "化開"],
  "cold-war|when-to-contact": ["開口", "壓力", "加分", "扣分"],
  "cold-war|what-did-i-do-wrong": ["冷戰", "沉默", "防衛"],
  "cold-war|stay-or-let-go": ["界線", "停", "等"],
  "crisis|still-love-me": ["繼續", "維持", "關係"],
  "crisis|any-chance": ["修復"],
  "crisis|when-to-contact": ["降低", "衝突", "惡性循環"],
  "crisis|what-did-i-do-wrong": ["爭吵", "循環", "衝突"],
  "crisis|stay-or-let-go": ["修", "傷", "關係"]
};
const forbiddenVisibleTerms = [
  "selector",
  "reducer",
  "action_scale",
  "boundary_only",
  "contactSituationPolicy",
  "relationshipThesis",
  "relationshipCaseModel",
  "semanticSlots",
  "timing band",
  "orb 約",
  "這裡只看",
  "下一頁再看"
];

function positiveInteger(value, fallback) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function birthProfile(birthDate, birthTime, birthPlace, gender, unknownTime = false) {
  return { birthDate, birthTime, birthPlace, gender, unknownTime };
}

function normalizeText(value) {
  return String(value ?? "").replace(/\s+/gu, " ").trim();
}

function hash(value) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex").slice(0, 16);
}

function visibleSection(section) {
  return Object.fromEntries(visibleFields.map((field) => [field, normalizeText(section?.[field])]));
}

function visibleSectionText(section) {
  return visibleFields.map((field) => normalizeText(section?.[field])).filter(Boolean).join(" ");
}

function finalSections(result) {
  return result?.finalInterpretation?.sections ?? {};
}

function sectionSpecs(result) {
  return result?.finalInterpretation?.sectionSpecs?.sections ?? {};
}

function caseKey(item) {
  return `${item.stage}|${item.question}|${item.contact.normalized}|${item.birthPair.id}`;
}

function isOwnershipAxisCase(stage, question, contact) {
  return (
    (question === anchor.question && contact === anchor.contact) ||
    (stage === anchor.stage && contact === anchor.contact) ||
    (stage === anchor.stage && question === anchor.question)
  );
}

function contextCases() {
  const output = [];
  for (const [stageIndex, stage] of stages.entries()) {
    for (const [questionIndex, question] of questions.entries()) {
      for (const [contactIndex, contact] of contacts.entries()) {
        const birthPairIndex = isOwnershipAxisCase(stage, question, contact.normalized)
          ? 0
          : (stageIndex * 7 + questionIndex * 3 + contactIndex) % birthPairs.length;
        output.push({
          birthPair: birthPairs[birthPairIndex],
          contact,
          kind: "context-matrix",
          question,
          stage
        });
      }
    }
  }
  return output;
}

function chartVariationCases() {
  const contact = contacts.find((item) => item.normalized === anchor.contact);
  return birthPairs.slice(1).map((birthPair) => ({
    birthPair,
    contact,
    kind: "chart-variation",
    question: anchor.question,
    stage: anchor.stage
  }));
}

function intakePayload(item) {
  return {
    relationshipStage: item.stage,
    mainQuestion: item.question,
    contactStatus: item.contact.input,
    user: { ...item.birthPair.user },
    partner: { ...item.birthPair.partner }
  };
}

async function requestResult(item) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), requestTimeoutMs);
  const startedAt = Date.now();
  try {
    const response = await fetch(new URL("/api/readings/relationship-result", targetUrl), {
      body: JSON.stringify(intakePayload(item)),
      headers: { "Content-Type": "application/json" },
      method: "POST",
      signal: controller.signal
    });
    const payload = await response.json().catch(() => null);
    return {
      ...item,
      elapsedMs: Date.now() - startedAt,
      payload,
      status: response.status
    };
  } catch (error) {
    return {
      ...item,
      elapsedMs: Date.now() - startedAt,
      error: error instanceof Error ? error.message : String(error),
      payload: null,
      status: 0
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function concurrentMap(items, workerCount, worker) {
  const results = new Array(items.length);
  let cursor = 0;
  let completed = 0;

  async function runWorker() {
    while (true) {
      const index = cursor;
      cursor += 1;
      if (index >= items.length) return;
      results[index] = await worker(items[index], index);
      completed += 1;
      if (completed % 10 === 0 || completed === items.length) {
        process.stderr.write(`API matrix: ${completed}/${items.length}\n`);
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(workerCount, items.length) }, () => runWorker()));
  return results;
}

function pushFailure(failures, record, message) {
  failures.push(`${record ? caseKey(record) : "matrix"}: ${message}`);
}

function assertRecord(record, failures) {
  const result = record.payload;
  if (record.status !== 200 || !result || result.error) {
    pushFailure(failures, record, `API returned ${record.status}: ${result?.message ?? result?.debugMessage ?? record.error ?? "no payload"}`);
    return;
  }

  const context = result.context ?? {};
  if (!String(result.id ?? "").startsWith("runtime-")) pushFailure(failures, record, "runtime result id missing");
  if (result.contractVersion !== "complete-relationship-result-v1") pushFailure(failures, record, "complete result contract mismatch");
  if (context.relationship_stage !== record.stage) pushFailure(failures, record, `stage mismatch: ${context.relationship_stage}`);
  if (context.main_question !== record.question) pushFailure(failures, record, `question mismatch: ${context.main_question}`);
  if (context.contact_status !== record.contact.normalized) pushFailure(failures, record, `contact normalization mismatch: ${context.contact_status}`);
  if (!result?.debug?.engineVersions?.immanuel) pushFailure(failures, record, "calculation engine version missing");
  if (expectedStructuredKbSource && result?.debug?.structuredKbSource !== expectedStructuredKbSource) {
    pushFailure(failures, record, `structured KB source mismatch: ${result?.debug?.structuredKbSource}`);
  }

  const final = result.finalInterpretation ?? {};
  const storyline = final.contextStoryline ?? {};
  const statusPolicy = storyline.statusAnswerPolicy ?? {};
  if (final.version !== "final-reading-interpretation-v1") pushFailure(failures, record, "final interpretation version missing");
  if (final.locale !== "zh-TW") pushFailure(failures, record, `final interpretation locale mismatch: ${final.locale}`);
  if (final.stageKey !== record.stage) pushFailure(failures, record, `final stage mismatch: ${final.stageKey}`);
  if (final.questionKey !== record.question) pushFailure(failures, record, `final question mismatch: ${final.questionKey}`);
  if (storyline.comboKey !== `${record.stage}|${record.question}|${record.contact.normalized}`) {
    pushFailure(failures, record, `storyline combo mismatch: ${storyline.comboKey}`);
  }
  if (statusPolicy.version !== "relationship-status-answer-policy-v1") pushFailure(failures, record, "status answer policy missing");
  if (!normalizeText(statusPolicy.questionRewrite)) pushFailure(failures, record, "status-specific question rewrite missing");
  if (normalizeText(final.questionLabel) !== normalizeText(statusPolicy.questionRewrite)) {
    pushFailure(failures, record, "final question label does not follow status policy rewrite");
  }
  if (result?.relationshipThesis?.validation?.passed !== true) pushFailure(failures, record, "relationship thesis validation failed");

  const sections = finalSections(result);
  const specs = sectionSpecs(result);
  for (const sectionId of sectionIds) {
    const section = sections[sectionId];
    const spec = specs[sectionId];
    if (!section) {
      pushFailure(failures, record, `final section missing: ${sectionId}`);
      continue;
    }
    if (section.module !== sectionModules[sectionId]) pushFailure(failures, record, `${sectionId} module mismatch: ${section.module}`);
    if (section.locale !== "zh-TW") pushFailure(failures, record, `${sectionId} locale mismatch: ${section.locale}`);
    for (const field of visibleFields) {
      if (!normalizeText(section[field])) pushFailure(failures, record, `${sectionId}.${field} missing`);
    }
    if (!Array.isArray(section.sourceClaimIds) || section.sourceClaimIds.length === 0) pushFailure(failures, record, `${sectionId} source claims missing`);
    if (!Array.isArray(section.methodClaimIds) || section.methodClaimIds.length === 0) pushFailure(failures, record, `${sectionId} method claims missing`);
    if (!Array.isArray(section.evidenceClusterKeys) || section.evidenceClusterKeys.length === 0) pushFailure(failures, record, `${sectionId} evidence clusters missing`);
    if (section?.questionSelector?.questionKey !== record.question) pushFailure(failures, record, `${sectionId} question selector mismatch`);
    if (!spec || spec.sectionId !== sectionId || !normalizeText(spec.purpose)) pushFailure(failures, record, `${sectionId} page spec missing`);

    const copy = visibleSectionText(section);
    for (const forbidden of forbiddenVisibleTerms) {
      if (copy.toLowerCase().includes(forbidden.toLowerCase())) pushFailure(failures, record, `${sectionId} leaked forbidden visible term: ${forbidden}`);
    }
    const internalStagePhrase = `在「${stageLabels[record.stage]}」裡`;
    if (copy.includes(internalStagePhrase)) pushFailure(failures, record, `${sectionId} exposed internal stage framing`);
  }

  for (const sectionId of customerSummaryIds) {
    if (!visibleFields.every((field) => normalizeText(sections?.[sectionId]?.[field]))) {
      pushFailure(failures, record, `customer summary contract incomplete: ${sectionId}`);
    }
  }

  const coreMeaning = normalizeText(sections?.["core-answer"]?.meaning);
  const focusKey = `${record.stage}|${record.question}`;
  if (!statusQuestionMarkers[focusKey]?.some((marker) => coreMeaning.includes(marker))) {
    pushFailure(failures, record, `core direct answer does not address status-specific question ${focusKey}`);
  }

  const chartSlots = specs?.["chart-positioning"]?.semanticSlots ?? {};
  const fitSlots = specs?.["relationship-fit"]?.semanticSlots ?? {};
  const contextOwnedKeys = ["questionKey", "relationshipStage", "contactStatus", "actionMode", "timingPostureKey"];
  for (const key of contextOwnedKeys) {
    if (Object.hasOwn(chartSlots, key)) pushFailure(failures, record, `chart-positioning owns context key ${key}`);
    if (Object.hasOwn(fitSlots, key)) pushFailure(failures, record, `relationship-fit owns context key ${key}`);
  }
  const coreSlots = specs?.["core-answer"]?.semanticSlots ?? {};
  const timingSlots = specs?.["timing-reading"]?.semanticSlots ?? {};
  const actionSlots = specs?.["action-direction"]?.semanticSlots ?? {};
  if (coreSlots.questionKey !== record.question || coreSlots.relationshipStage !== record.stage || coreSlots.contactStatus !== record.contact.normalized) {
    pushFailure(failures, record, "core-answer semantic ownership mismatch");
  }
  if (timingSlots.questionKey !== record.question || timingSlots.contactStatus !== record.contact.normalized) {
    pushFailure(failures, record, "timing-reading semantic ownership mismatch");
  }
  if (actionSlots.questionKey !== record.question || actionSlots.contactStatus !== record.contact.normalized) {
    pushFailure(failures, record, "action-direction semantic ownership mismatch");
  }

  const expectedPolicy = contactPolicies[record.contact.normalized];
  const actualPolicy = result?.westernRelationshipCaseFile?.evidenceClusters?.contactSituationPolicy ?? {};
  const boundary = actualPolicy.contactActionBoundary ?? {};
  if (actualPolicy.statusKey !== record.contact.normalized) pushFailure(failures, record, "contact policy status mismatch");
  if (actualPolicy.actionScale !== expectedPolicy.actionScale) pushFailure(failures, record, `contact action scale mismatch: ${actualPolicy.actionScale}`);
  if (actualPolicy.actionMode !== expectedPolicy.actionMode) pushFailure(failures, record, `contact action mode mismatch: ${actualPolicy.actionMode}`);
  if (actualPolicy.canSuggestDirectContact !== expectedPolicy.canSuggestDirectContact) pushFailure(failures, record, "direct contact boundary mismatch");
  if (boundary.timingCanOverrideBoundary !== false || boundary.canOverrideRealWorldBoundary !== false) {
    pushFailure(failures, record, "timing can override a real-world contact boundary");
  }
  if (result?.actionGuidance?.actionScale !== expectedPolicy.actionScale) pushFailure(failures, record, "action guidance scale diverges from contact policy");
  if (result?.actionGuidance?.actionMode !== expectedPolicy.actionMode) pushFailure(failures, record, "action guidance mode diverges from contact policy");
  if (record.contact.normalized === "blocked") {
    const blocked = new Set(actualPolicy.blockedActions ?? []);
    for (const action of ["alternate_account_contact", "repeated_messages", "third_party_pressure"]) {
      if (!blocked.has(action)) pushFailure(failures, record, `blocked contact is missing stop action ${action}`);
    }
    if (boundary.isHardBoundary !== true || boundary.canSuggestDirectContact !== false) {
      pushFailure(failures, record, "blocked contact did not produce a hard no-contact boundary");
    }
  }

  const answerRuleId = result?.westernRelationshipCaseFile?.answerLayer?.ruleId;
  if (!answerRuleId || String(answerRuleId).endsWith("-fallback")) pushFailure(failures, record, `fallback answer rule selected: ${answerRuleId}`);

  const sentencesBySection = new Map();
  for (const sectionId of sectionIds) {
    const sentenceSource = ["headline", "meaning", "body", "nextMove"]
      .map((field) => normalizeText(sections?.[sectionId]?.[field]))
      .join("。")
      .split(/[。！？!?；]+/u)
      .map(normalizeText)
      .filter((sentence) => sentence.length >= 14);
    for (const sentence of sentenceSource) {
      const owners = sentencesBySection.get(sentence) ?? new Set();
      owners.add(sectionId);
      sentencesBySection.set(sentence, owners);
    }
  }
  for (const [sentence, owners] of sentencesBySection) {
    if (owners.size > 1) pushFailure(failures, record, `visible sentence is reused across pages (${[...owners].join(", ")}): ${sentence}`);
  }

  const inputQuality = result?.westernRelationshipCaseFile?.inputQuality ?? {};
  const houseGate = result?.westernRelationshipCaseFile?.evidenceClusters?.houseRelationshipFactors?.houseAnglePrecisionGate ?? {};
  if (record.birthPair.id === "new-taipei-date-only") {
    if (inputQuality?.personB?.precision !== "date_only") pushFailure(failures, record, "unknown partner time did not produce date-only precision");
    if (houseGate.status !== "blocked_by_birth_time") pushFailure(failures, record, `unknown time did not block house claims: ${houseGate.status}`);
  } else if (inputQuality.overall !== "high") {
    pushFailure(failures, record, `known birth data did not produce high precision: ${inputQuality.overall}`);
  }
}

function semanticFingerprint(result, sectionId) {
  const slots = sectionSpecs(result)?.[sectionId]?.semanticSlots ?? {};
  if (sectionId === "chart-positioning") {
    return hash({
      personACommunicationStyle: slots.personACommunicationStyle,
      personAEmotionalNeed: slots.personAEmotionalNeed,
      personBPressureResponse: slots.personBPressureResponse,
      precisionMode: slots.precisionMode
    });
  }
  if (sectionId === "relationship-fit") {
    return hash({
      fitSignature: slots.fitSignature,
      primaryDynamicKey: slots.primaryDynamicKey,
      secondaryDynamicKeys: slots.secondaryDynamicKeys
    });
  }
  if (sectionId === "core-answer") {
    return hash({
      answerTrackKeys: slots.answerTrackKeys,
      centralDynamicKey: slots.centralDynamicKey,
      centralEvidenceKey: slots.centralEvidenceSignal?.key,
      contactStatus: slots.contactStatus,
      questionKey: slots.questionKey,
      relationshipStage: slots.relationshipStage
    });
  }
  if (sectionId === "timing-reading") {
    return hash({
      contactStatus: slots.contactStatus,
      questionKey: slots.questionKey,
      timingPostureKey: slots.timingPostureKey,
      topBand: slots.topBand,
      topWindowKey: slots.topWindowKey
    });
  }
  return hash({
    actionMode: slots.actionMode,
    blockedActions: slots.blockedActions,
    completionBoundaryKey: slots.completionBoundaryKey,
    contactStatus: slots.contactStatus,
    questionKey: slots.questionKey,
    stopConditionKey: slots.stopConditionKey
  });
}

function visibleFingerprint(result, sectionId) {
  return hash(visibleSection(finalSections(result)?.[sectionId]));
}

function distinctCount(records, sectionId) {
  return new Set(records.map((record) => visibleFingerprint(record.payload, sectionId))).size;
}

function recordsForAxis(records, axis) {
  return records.filter((record) => {
    if (record.kind !== "context-matrix" || record.birthPair.id !== birthPairs[0].id) return false;
    if (axis === "stage") return record.question === anchor.question && record.contact.normalized === anchor.contact;
    if (axis === "question") return record.stage === anchor.stage && record.contact.normalized === anchor.contact;
    return record.stage === anchor.stage && record.question === anchor.question;
  });
}

function assertAggregate(records, failures) {
  const validRecords = records.filter((record) => record.status === 200 && record.payload && !record.payload.error);
  const contextRecords = validRecords.filter((record) => record.kind === "context-matrix");
  const contextKeys = new Set(contextRecords.map((record) => `${record.stage}|${record.question}|${record.contact.normalized}`));
  if (contextRecords.length !== 125 || contextKeys.size !== 125) pushFailure(failures, null, `context matrix incomplete: ${contextRecords.length} records, ${contextKeys.size} combinations`);
  if (new Set(validRecords.map((record) => record.payload.id)).size !== validRecords.length) pushFailure(failures, null, "API reused runtime result ids");
  if (new Set(contextRecords.map((record) => record.birthPair.id)).size !== birthPairs.length) pushFailure(failures, null, "birth-pair variation incomplete");

  for (const sectionId of sectionIds) {
    const outputToMeaning = new Map();
    for (const record of contextRecords) {
      const output = visibleFingerprint(record.payload, sectionId);
      const meaning = semanticFingerprint(record.payload, sectionId);
      const meanings = outputToMeaning.get(output) ?? new Set();
      meanings.add(meaning);
      outputToMeaning.set(output, meanings);
    }
    const collapseCount = [...outputToMeaning.values()].filter((meanings) => meanings.size > 1).length;
    if (collapseCount) pushFailure(failures, null, `${sectionId} has ${collapseCount} visible output collapse group(s) across different semantic frames`);
  }

  const fullOutputGroups = new Map();
  for (const record of contextRecords) {
    const fullFingerprint = hash(Object.fromEntries(sectionIds.map((sectionId) => [sectionId, visibleSection(finalSections(record.payload)?.[sectionId])])));
    const owners = fullOutputGroups.get(fullFingerprint) ?? [];
    owners.push(record);
    fullOutputGroups.set(fullFingerprint, owners);
  }
  const fullCollapses = [...fullOutputGroups.values()].filter((group) => new Set(group.map(caseKey)).size > 1);
  if (fullCollapses.length) pushFailure(failures, null, `full reading output collapsed across ${fullCollapses.length} different input group(s)`);

  for (const birthPair of birthPairs) {
    const sameChartRecords = contextRecords.filter((record) => record.birthPair.id === birthPair.id);
    if (distinctCount(sameChartRecords, "chart-positioning") !== 1) pushFailure(failures, null, `${birthPair.id} chart-positioning changed when only context changed`);
    if (distinctCount(sameChartRecords, "relationship-fit") !== 1) pushFailure(failures, null, `${birthPair.id} relationship-fit changed when only context changed`);
  }

  const stageAxis = recordsForAxis(contextRecords, "stage");
  const questionAxis = recordsForAxis(contextRecords, "question");
  const contactAxis = recordsForAxis(contextRecords, "contact");
  for (const [axis, axisRecords] of [["stage", stageAxis], ["question", questionAxis], ["contact", contactAxis]]) {
    if (axisRecords.length !== 5) pushFailure(failures, null, `${axis} metamorphic axis incomplete: ${axisRecords.length}`);
    if (distinctCount(axisRecords, "chart-positioning") !== 1 || distinctCount(axisRecords, "relationship-fit") !== 1) {
      pushFailure(failures, null, `${axis} context change altered a chart-owned page`);
    }
  }
  if (distinctCount(stageAxis, "core-answer") < 4) pushFailure(failures, null, "relationship status does not sufficiently change the core answer");
  if (distinctCount(questionAxis, "core-answer") !== 5) pushFailure(failures, null, "selected question does not produce five distinct core answers");
  if (distinctCount(contactAxis, "timing-reading") < 4) pushFailure(failures, null, "contact status does not sufficiently change timing");
  if (distinctCount(contactAxis, "action-direction") !== 5) pushFailure(failures, null, "contact status does not produce five distinct action boundaries");

  const chartRecords = validRecords.filter(
    (record) => record.stage === anchor.stage && record.question === anchor.question && record.contact.normalized === anchor.contact
  );
  if (new Set(chartRecords.map((record) => record.birthPair.id)).size !== birthPairs.length) pushFailure(failures, null, "fixed-context chart variation set incomplete");
  if (distinctCount(chartRecords, "chart-positioning") < 4) pushFailure(failures, null, "varied birth charts collapse in chart positioning");
  if (distinctCount(chartRecords, "relationship-fit") < 4) pushFailure(failures, null, "varied birth charts collapse in relationship fit");

  for (const question of questions) {
    const family = contextRecords.filter((record) => record.question === question);
    if (distinctCount(family, "core-answer") < 12) pushFailure(failures, null, `${question} core-answer family is too repetitive`);
  }

  const directAnswers = contextRecords.map((record) => normalizeText(finalSections(record.payload)?.["core-answer"]?.meaning));
  if (new Set(directAnswers).size !== 125) {
    pushFailure(failures, null, `status-question-contact direct answers collapsed: ${new Set(directAnswers).size}/125 unique`);
  }
  for (const question of questions) {
    for (const contact of contacts) {
      const stageMeanings = contextRecords
        .filter((record) => record.question === question && record.contact.normalized === contact.normalized)
        .map((record) => normalizeText(finalSections(record.payload)?.["core-answer"]?.meaning));
      if (new Set(stageMeanings).size !== stages.length) {
        pushFailure(failures, null, `${question}|${contact.normalized} direct answer did not change across all statuses`);
      }
    }
  }

  return {
    chartVariation: {
      chartPositioning: distinctCount(chartRecords, "chart-positioning"),
      relationshipFit: distinctCount(chartRecords, "relationship-fit")
    },
    contextCombinations: contextKeys.size,
    sectionVariation: Object.fromEntries(sectionIds.map((sectionId) => [sectionId, distinctCount(contextRecords, sectionId)])),
    questionCoreVariation: Object.fromEntries(
      questions.map((question) => [question, distinctCount(contextRecords.filter((record) => record.question === question), "core-answer")])
    ),
    directAnswerVariation: new Set(directAnswers).size
  };
}

async function assertInvalidDateBoundary(failures) {
  const payload = intakePayload({
    birthPair: birthPairs[0],
    contact: contacts[0],
    question: questions[0],
    stage: stages[0]
  });
  payload.user.birthDate = "2026-02-30";
  const response = await fetch(new URL("/api/readings/relationship-result", targetUrl), {
    body: JSON.stringify(payload),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  const body = await response.json().catch(() => null);
  if (response.status !== 400 || body?.error !== "invalid_intake_payload") {
    pushFailure(failures, null, `invalid calendar date was not rejected cleanly: ${response.status}`);
  }
  if (!(body?.fields ?? []).some((item) => item?.field === "user.birthDate")) {
    pushFailure(failures, null, "invalid calendar date response did not identify user.birthDate");
  }
}

const requestedCases = [...contextCases(), ...chartVariationCases()];
const startedAt = Date.now();
const records = await concurrentMap(requestedCases, concurrency, requestResult);
const failures = [];
for (const record of records) assertRecord(record, failures);
const aggregate = assertAggregate(records, failures);
await assertInvalidDateBoundary(failures);

const elapsedValues = records.map((record) => record.elapsedMs).filter(Number.isFinite).sort((left, right) => left - right);
const result = {
  targetUrl,
  ok: failures.length === 0,
  elapsedSeconds: Number(((Date.now() - startedAt) / 1000).toFixed(2)),
  apiRequests: records.length + 1,
  successfulResults: records.filter((record) => record.status === 200).length,
  contextMatrixCases: records.filter((record) => record.kind === "context-matrix").length,
  birthPairs: birthPairs.map((item) => item.id),
  summaryContractsChecked: records.filter((record) => record.status === 200).length * customerSummaryIds.length,
  requiredVisibleFieldsChecked: records.filter((record) => record.status === 200).length * sectionIds.length * visibleFields.length,
  requestLatencyMs: {
    median: elapsedValues[Math.floor(elapsedValues.length / 2)] ?? null,
    max: elapsedValues.at(-1) ?? null
  },
  aggregate,
  failures
};

console.log(JSON.stringify(result, null, 2));
if (!result.ok) process.exit(1);
