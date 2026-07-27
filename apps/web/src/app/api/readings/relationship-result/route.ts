import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdtemp, rmdir, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import type { CompleteRelationshipResultViewModel } from "@/data/complete-relationship-result";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);
type StructuredKbSource = "local" | "supabase";

const validStructuredKbSources = new Set<StructuredKbSource>(["local", "supabase"]);

type IntakeBirthProfile = {
  birthDate: string;
  birthTime: string;
  birthPlace: string;
  gender: "" | "female" | "male" | "other";
  unknownTime: boolean;
};

type IntakePayload = {
  relationshipStage: string;
  mainQuestion: string;
  contactStatus: string;
  emotionalState?: string;
  user: IntakeBirthProfile;
  partner: IntakeBirthProfile;
};

export async function POST(request: Request) {
  if (
    process.env.NODE_ENV !== "development" ||
    process.env.VALLEY_RUNTIME_ENV === "production" ||
    process.env.VALLEY_ENABLE_LOCAL_RESULT_PROTOTYPE !== "1"
  ) {
    return Response.json(
      { error: "route_not_available" },
      {
        headers: {
          "Cache-Control": "private, no-store",
          "X-Robots-Tag": "noindex, nofollow, noarchive",
        },
        status: 404,
      }
    );
  }

  let payload: IntakePayload;
  try {
    payload = (await request.json()) as IntakePayload;
  } catch {
    return Response.json(
      {
        error: "invalid_intake_payload",
        message: "資料格式無法讀取，請重新填寫一次。",
      },
      { status: 400 }
    );
  }

  const validationIssues = validateIntakePayload(payload);
  if (validationIssues.length > 0) {
    return Response.json(
      {
        error: "invalid_intake_payload",
        message: validationIssues[0]?.message ?? "請確認出生資料後再試一次。",
        fields: validationIssues,
      },
      { status: 400 }
    );
  }

  const readingInput = buildReadingInput(payload);
  const repoRoot = path.resolve(process.cwd(), "../..");
  const pythonPath = process.env.VALLEY_PYTHON_PATH ?? path.join(repoRoot, ".venv/bin/python");
  const scriptPath = path.join(repoRoot, "scripts/build_relationship_result_from_reading.py");
  const structuredKbSource = structuredKbSourceForRuntime();
  if (!isStructuredKbSource(structuredKbSource)) {
    return Response.json(
      {
        error: "invalid_structured_kb_source",
        message: "VALLEY_STRUCTURED_KB_SOURCE must be local or supabase.",
      },
      { status: 500 }
    );
  }

  const tempDir = await mkdtemp(path.join(tmpdir(), "valley-reading-"));
  const readingPath = path.join(tempDir, `${readingInput.reading_id}.json`);
  const scriptArgs = [
    scriptPath,
    "--reading",
    readingPath,
    "--include-drafts",
    "--json",
    "--structured-kb-source",
    structuredKbSource,
  ];
  if (process.env.VALLEY_STRUCTURED_KB_ENV_FILE) {
    scriptArgs.push("--structured-kb-env-file", process.env.VALLEY_STRUCTURED_KB_ENV_FILE);
  }

  await writeFile(readingPath, JSON.stringify(readingInput), "utf8");

  try {
    const { stdout } = await execFileAsync(pythonPath, scriptArgs, {
      cwd: repoRoot,
      maxBuffer: 1024 * 1024 * 16,
      timeout: 20000,
    });
    const viewModel = JSON.parse(stdout.trim()) as CompleteRelationshipResultViewModel;
    viewModel.debug = {
      ...viewModel.debug,
      structuredKbSource,
    };
    return Response.json(viewModel);
  } catch (error) {
    return Response.json(
      {
        error: "relationship_result_calculation_failed",
        message: "合盤計算暫時失敗，請確認出生日期與時間後再試一次。",
        debugMessage: shortErrorMessage(error),
      },
      { status: 500 }
    );
  } finally {
    await unlink(readingPath).catch(() => undefined);
    await rmdir(tempDir).catch(() => undefined);
  }
}

type IntakeValidationIssue = {
  field: string;
  message: string;
};

const validRelationshipStages = new Set(["ambiguous", "cold-war", "broke-up-recent", "broke-up-long", "crisis"]);
const validMainQuestions = new Set(["still-love-me", "any-chance", "when-to-contact", "what-did-i-do-wrong", "stay-or-let-go"]);
const validContactStatuses = new Set([
  "none",
  "occasional",
  "cold-chat",
  "awkward-meeting",
  "blocked",
  "no-contact",
  "occasional-contact",
  "still-in-contact",
  "living-or-working-together",
]);

function validateIntakePayload(payload: IntakePayload): IntakeValidationIssue[] {
  const issues: IntakeValidationIssue[] = [];
  if (!validRelationshipStages.has(String(payload?.relationshipStage || ""))) {
    issues.push({ field: "relationshipStage", message: "請選擇你們現在的關係狀態。" });
  }
  if (!validMainQuestions.has(String(payload?.mainQuestion || ""))) {
    issues.push({ field: "mainQuestion", message: "請選擇你現在最想知道的問題。" });
  }
  if (!validContactStatuses.has(String(payload?.contactStatus || ""))) {
    issues.push({ field: "contactStatus", message: "請選擇你們最近的聯絡狀況。" });
  }
  issues.push(...validateBirthProfile(payload?.user, "user", "你的"));
  issues.push(...validateBirthProfile(payload?.partner, "partner", "對方的"));
  return issues;
}

function validateBirthProfile(profile: IntakeBirthProfile | undefined, fieldPrefix: string, label: string): IntakeValidationIssue[] {
  const issues: IntakeValidationIssue[] = [];
  if (!profile) {
    return [{ field: fieldPrefix, message: `請填寫${label}出生資料。` }];
  }
  if (!isValidIsoDate(profile.birthDate)) {
    issues.push({
      field: `${fieldPrefix}.birthDate`,
      message: `請確認${label}出生日期，這個月份沒有這一天。`,
    });
  }
  if (!profile.unknownTime && !isValidBirthTime(profile.birthTime)) {
    issues.push({
      field: `${fieldPrefix}.birthTime`,
      message: `請填寫${label}出生時間，或選擇不知道出生時間。`,
    });
  }
  if (!profile.gender) {
    issues.push({
      field: `${fieldPrefix}.gender`,
      message: `請選擇${label}性別。`,
    });
  }
  return issues;
}

function isValidIsoDate(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return false;
  if (year < 1 || month < 1 || month > 12 || day < 1) return false;
  return day <= daysInMonth(year, month);
}

function isValidBirthTime(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const match = /^(\d{2}):(\d{2})$/.exec(value);
  if (!match) return false;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
}

function daysInMonth(year: number, month: number) {
  const lengths = [31, isLeapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return lengths[month - 1] ?? 0;
}

function isLeapYear(year: number) {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function shortErrorMessage(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return message.split("\n").slice(0, 2).join("\n");
}

function structuredKbSourceForRuntime() {
  const explicit = process.env.VALLEY_STRUCTURED_KB_SOURCE?.trim();
  if (explicit) return explicit;
  if (process.env.VALLEY_RUNTIME_ENV === "staging" || process.env.VERCEL_ENV === "preview") return "supabase";
  return "local";
}

function isStructuredKbSource(value: string): value is StructuredKbSource {
  return validStructuredKbSources.has(value as StructuredKbSource);
}

function buildReadingInput(payload: IntakePayload) {
  const analysisMoment = nowInTaipei();
  return {
    reading_id: `runtime-${randomUUID()}`,
    person_a: normalizePerson(payload.user),
    person_b: normalizePerson(payload.partner),
    context: {
      relationship_stage: payload.relationshipStage,
      main_question: payload.mainQuestion,
      contact_status: normalizeContactStatus(payload.contactStatus),
      desired_outcome: desiredOutcomeFor(payload.mainQuestion),
      emotional_risk: payload.emotionalState ?? "not-collected",
      analysis_date: analysisMoment.date,
      analysis_datetime: analysisMoment.dateTime,
      analysis_timezone: analysisMoment.timezone,
    },
  };
}

function normalizePerson(profile: IntakeBirthProfile) {
  return {
    birth_date: profile.birthDate,
    birth_time: profile.unknownTime ? "" : profile.birthTime,
    birth_timezone: timezoneFor(profile.birthPlace),
    birth_place: profile.birthPlace.trim(),
    gender: profile.gender || "other",
  };
}

function normalizeContactStatus(value: string) {
  const mapping: Record<string, string> = {
    none: "no-contact",
    occasional: "occasional-contact",
    "cold-chat": "still-in-contact",
    "awkward-meeting": "living-or-working-together",
    blocked: "blocked",
  };
  return mapping[value] ?? value;
}

function desiredOutcomeFor(question: string) {
  const mapping: Record<string, string> = {
    "still-love-me": "reconnect",
    "any-chance": "reconnect",
    "when-to-contact": "reconnect",
    "what-did-i-do-wrong": "understand",
    "stay-or-let-go": "decide",
  };
  return mapping[question] ?? "understand";
}

function timezoneFor(place: string) {
  if (/東京|tokyo/i.test(place)) return "Asia/Tokyo";
  if (/首爾|seoul/i.test(place)) return "Asia/Seoul";
  if (/香港|hong kong/i.test(place)) return "Asia/Hong_Kong";
  if (/新加坡|singapore/i.test(place)) return "Asia/Singapore";
  return "Asia/Taipei";
}

function nowInTaipei() {
  const parts = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    month: "2-digit",
    timeZone: "Asia/Taipei",
    year: "numeric",
  })
    .formatToParts(new Date())
    .reduce<Record<string, string>>((acc, part) => {
      if (part.type !== "literal") acc[part.type] = part.value;
      return acc;
    }, {});
  const hour = parts.hour === "24" ? "00" : parts.hour;
  const date = `${parts.year}-${parts.month}-${parts.day}`;
  return {
    date,
    dateTime: `${date}T${hour}:${parts.minute}`,
    timezone: "Asia/Taipei",
  };
}
