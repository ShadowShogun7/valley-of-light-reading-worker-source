import { z } from "zod";

const forbiddenKeys = new Set([
  "debug",
  "dominantNarrativeAngle",
  "debugMessage",
  "draft",
  "draftContent",
  "readingBlueprint",
  "relationshipCaseModel",
  "relationshipStatusAnswerPolicy",
  "relationshipThesis",
  "sectionNarrativeSpecs",
  "serviceRoleKey",
  "service_role_key",
]);

const allowedTopLevelKeys = new Set([
  "actionGuidance",
  "answerGuidance",
  "attractionDynamics",
  "authorityReasons",
  "baziCompatibilityDiagnosis",
  "brand",
  "calculationProof",
  "calculationSteps",
  "chance",
  "chapterEvidence",
  "conflictDynamics",
  "context",
  "contractVersion",
  "debug",
  "dominantNarrativeAngle",
  "donts",
  "evidence",
  "fightLandmines",
  "finalInterpretation",
  "growthDynamics",
  "id",
  "includedReadingRows",
  "insights",
  "label",
  "lockedRows",
  "metrics",
  "normalUserAnswer",
  "partnerNeeds",
  "readableQuestionAnswer",
  "reading",
  "readingBlueprint",
  "reasons",
  "relationshipArchetype",
  "relationshipCaseFile",
  "relationshipCaseModel",
  "relationshipContextStoryline",
  "relationshipDiagnosis",
  "relationshipFitLens",
  "relationshipProfiles",
  "relationshipStatusAnswerPolicy",
  "relationshipThesis",
  "relationshipTurningWindows",
  "sources",
  "sectionNarrativeSpecs",
  "survivalGuide",
  "thoughts",
  "timeline",
  "timingGuidance",
  "westernRelationshipCaseFile",
]);

const resultShellSchema = z
  .object({
    brand: z
      .object({
        subtitle: z.string().min(1).max(160),
        title: z.string().min(1).max(160),
      })
      .strict(),
    calculationSteps: z.array(z.unknown()).max(500),
    chance: z.record(z.string(), z.unknown()),
    chapterEvidence: z.record(z.string(), z.unknown()),
    context: z.record(z.string(), z.string()),
    contractVersion: z.literal("complete-relationship-result-v1"),
    donts: z.array(z.string().max(10_000)).max(500),
    evidence: z.record(z.string(), z.unknown()),
    id: z.string().min(1).max(160),
    includedReadingRows: z.array(z.unknown()).max(500),
    insights: z.array(z.unknown()).max(500),
    label: z.string().min(1).max(300),
    metrics: z.array(z.unknown()).min(1).max(100),
    reading: z
      .object({
        answer: z.string().min(1).max(20_000),
        badge: z.string().min(1).max(300),
        question: z.string().min(1).max(2_000),
        safety: z.string().max(10_000),
        score: z.number().finite().min(0).max(100),
        stage: z.string().min(1).max(300),
      })
      .strict(),
    reasons: z.array(z.unknown()).max(500),
    sources: z.array(z.string().max(2_000)).max(500),
    thoughts: z.array(z.string().max(20_000)).max(500),
    timeline: z.array(z.unknown()).max(500),
  })
  .passthrough();

export function sanitizeCustomerResult(value: unknown): Record<string, unknown> {
  const sanitized = sanitizeValue(value);
  if (!isPlainObject(sanitized)) throw new Error("INVALID_CUSTOMER_RESULT");
  return sanitized;
}

export function validateCustomerResultContract(
  value: unknown
): Record<string, unknown> {
  if (!isPlainObject(value)) throw new Error("INVALID_CUSTOMER_RESULT");
  for (const key of Object.keys(value)) {
    if (!allowedTopLevelKeys.has(key)) {
      throw new Error("INVALID_CUSTOMER_RESULT");
    }
  }
  resultShellSchema.parse(value);
  assertBoundedCustomerJson(value);
  return sanitizeCustomerResult(value);
}

function sanitizeValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sanitizeValue);
  if (!isPlainObject(value)) return value;

  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !forbiddenKeys.has(key))
      .map(([key, nestedValue]) => [key, sanitizeValue(nestedValue)])
  );
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function assertBoundedCustomerJson(value: unknown) {
  const stack: Array<{ depth: number; value: unknown }> = [
    { depth: 0, value },
  ];
  let visitedNodes = 0;

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) break;
    visitedNodes += 1;
    if (visitedNodes > 100_000 || current.depth > 20) {
      throw new Error("INVALID_CUSTOMER_RESULT");
    }
    if (typeof current.value === "string") {
      if (current.value.length > 20_000) {
        throw new Error("INVALID_CUSTOMER_RESULT");
      }
      continue;
    }
    if (Array.isArray(current.value)) {
      if (current.value.length > 5_000) {
        throw new Error("INVALID_CUSTOMER_RESULT");
      }
      for (const nestedValue of current.value) {
        stack.push({ depth: current.depth + 1, value: nestedValue });
      }
      continue;
    }
    if (!isPlainObject(current.value)) continue;
    const entries = Object.entries(current.value);
    if (entries.length > 1_000) throw new Error("INVALID_CUSTOMER_RESULT");
    for (const [key, nestedValue] of entries) {
      if (forbiddenKeys.has(key)) continue;
      if (
        /(?:api.?key|password|raw.?prompt|secret|service.?role|system.?prompt|token)/i.test(
          key
        )
      ) {
        throw new Error("INVALID_CUSTOMER_RESULT");
      }
      stack.push({ depth: current.depth + 1, value: nestedValue });
    }
  }
}
