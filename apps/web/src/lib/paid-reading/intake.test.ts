import assert from "node:assert/strict";
import test from "node:test";
import {
  emptyIntakeDraft,
  finalIntakeSchema,
  intakeDraftSchema,
} from "@/lib/paid-reading/intake";

test("empty intake is valid only as a resumable draft", () => {
  const draft = emptyIntakeDraft();
  assert.equal(intakeDraftSchema.safeParse(draft).success, true);
  assert.equal(
    finalIntakeSchema.safeParse({
      ...draft,
      dataConfirmationAccepted: true,
      dataConfirmationVersion: "data-confirmation-v1",
      generationConsentAccepted: true,
      generationConsentVersion: "consent-v1",
    }).success,
    false
  );
});

test("complete consented intake validates", () => {
  const profile = {
    birthDate: "1992-07-09",
    birthPlace: "台北市",
    birthTime: "22:10",
    gender: "female" as const,
    unknownTime: false,
  };
  const parsed = finalIntakeSchema.safeParse({
    contactStatus: "none",
    dataConfirmationAccepted: true,
    dataConfirmationVersion: "data-confirmation-v1",
    generationConsentAccepted: true,
    generationConsentVersion: "consent-v1",
    mainQuestion: "stay-or-let-go",
    partner: {
      ...profile,
      birthDate: "1990-12-02",
      birthTime: "",
      gender: "male",
      unknownTime: true,
    },
    relationshipStage: "broke-up-recent",
    user: profile,
  });
  assert.equal(parsed.success, true);
});

test("unknown nonempty birth cities fail closed instead of skipping a chart", () => {
  const profile = {
    birthDate: "1992-07-09",
    birthPlace: "Atlantis",
    birthTime: "22:10",
    gender: "female" as const,
    unknownTime: false,
  };
  const parsed = finalIntakeSchema.safeParse({
    contactStatus: "none",
    dataConfirmationAccepted: true,
    dataConfirmationVersion: "data-confirmation-v1",
    generationConsentAccepted: true,
    generationConsentVersion: "consent-v1",
    mainQuestion: "stay-or-let-go",
    partner: {
      ...profile,
      birthPlace: "",
      birthTime: "",
      gender: "male",
      unknownTime: true,
    },
    relationshipStage: "broke-up-recent",
    user: profile,
  });
  assert.equal(parsed.success, false);
});
