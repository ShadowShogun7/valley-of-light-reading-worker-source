import { z } from "zod";
import { isSupportedBirthPlace } from "@/lib/paid-reading/locations";

const relationshipStages = [
  "ambiguous",
  "cold-war",
  "broke-up-recent",
  "broke-up-long",
  "crisis",
] as const;
const mainQuestions = [
  "still-love-me",
  "any-chance",
  "when-to-contact",
  "what-did-i-do-wrong",
  "stay-or-let-go",
] as const;
const contactStatuses = [
  "none",
  "occasional",
  "cold-chat",
  "awkward-meeting",
  "blocked",
  "no-contact",
  "occasional-contact",
  "still-in-contact",
  "living-or-working-together",
] as const;
const genders = ["female", "male", "other"] as const;

const draftBirthProfileSchema = z
  .object({
    birthDate: z.string().max(10),
    birthTime: z.string().max(5),
    birthPlace: z.string().trim().max(120),
    gender: z.union([z.literal(""), z.enum(genders)]),
    unknownTime: z.boolean(),
  })
  .strict();

const draftChoice = <T extends readonly [string, ...string[]]>(values: T) =>
  z.string().max(80).refine((value) => value === "" || values.includes(value), {
    message: "unsupported choice",
  });

export const intakeDraftSchema = z
  .object({
    relationshipStage: draftChoice(relationshipStages),
    mainQuestion: draftChoice(mainQuestions),
    contactStatus: draftChoice(contactStatuses),
    user: draftBirthProfileSchema,
    partner: draftBirthProfileSchema,
  })
  .strict();

const finalBirthProfileSchema = draftBirthProfileSchema.superRefine(
  (profile, context) => {
    if (!isValidIsoDate(profile.birthDate)) {
      context.addIssue({
        code: "custom",
        message: "請確認出生日期。",
        path: ["birthDate"],
      });
    }
    if (!profile.gender) {
      context.addIssue({
        code: "custom",
        message: "請選擇性別。",
        path: ["gender"],
      });
    }
    if (!profile.unknownTime && !isValidBirthTime(profile.birthTime)) {
      context.addIssue({
        code: "custom",
        message: "請填寫出生時間，或選擇不知道出生時間。",
        path: ["birthTime"],
      });
    }
    if (!isSupportedBirthPlace(profile.birthPlace)) {
      context.addIssue({
        code: "custom",
        message:
          "目前無法安全定位這個城市。請從清單選擇，或留空讓解讀避開宮位與上升相關判斷。",
        path: ["birthPlace"],
      });
    }
  }
);

export const finalIntakeSchema = z
  .object({
    relationshipStage: z.enum(relationshipStages),
    mainQuestion: z.enum(mainQuestions),
    contactStatus: z.enum(contactStatuses),
    user: finalBirthProfileSchema,
    partner: finalBirthProfileSchema,
    generationConsentAccepted: z.literal(true),
    generationConsentVersion: z.string().min(1).max(80),
  })
  .strict();

export type IntakeDraft = z.infer<typeof intakeDraftSchema>;
export type FinalIntake = z.infer<typeof finalIntakeSchema>;

export function emptyIntakeDraft(): IntakeDraft {
  const emptyProfile = {
    birthDate: "",
    birthPlace: "",
    birthTime: "",
    gender: "" as const,
    unknownTime: false,
  };
  return {
    contactStatus: "",
    mainQuestion: "",
    partner: { ...emptyProfile },
    relationshipStage: "",
    user: { ...emptyProfile },
  };
}

export function buildPrecisionSnapshot(intake: FinalIntake) {
  return {
    version: "birth-data-precision-v1",
    user: {
      birthPlaceProvided: intake.user.birthPlace.length > 0,
      birthPlaceSupported: isSupportedBirthPlace(intake.user.birthPlace),
      birthTimeKnown: !intake.user.unknownTime,
    },
    partner: {
      birthPlaceProvided: intake.partner.birthPlace.length > 0,
      birthPlaceSupported: isSupportedBirthPlace(intake.partner.birthPlace),
      birthTimeKnown: !intake.partner.unknownTime,
    },
  };
}

function isValidIsoDate(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1900 || month < 1 || month > 12 || day < 1) return false;
  const date = new Date(Date.UTC(year, month - 1, day));
  const today = new Date();
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day &&
    date.getTime() <= today.getTime()
  );
}

function isValidBirthTime(value: string) {
  const match = /^(\d{2}):(\d{2})$/.exec(value);
  if (!match) return false;
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
}
