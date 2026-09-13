import type { ReadableInterpretation } from "@/data/complete-relationship-result";

export const READER_DISPLAY_VERSION = "reader-chapter-v1";
export const READER_FIELDS = ["headline", "meaning", "body", "nextMove", "caution"] as const;
export type ReaderSectionId = "chart-positioning" | "relationship-fit" | "core-answer" | "timing-reading" | "action-direction";
export type ReaderCopy = Pick<ReadableInterpretation, (typeof READER_FIELDS)[number]>;

// A missing final field is not permission to fall back to upstream prose.
export function readerChapter(sectionId: ReaderSectionId, value?: Partial<ReadableInterpretation>) {
  if (!value || READER_FIELDS.some((field) => typeof value[field] !== "string" || !value[field]!.trim())) return null;
  const copy = Object.fromEntries(READER_FIELDS.map((field) => [field, value[field]!.trim()])) as ReaderCopy;
  const groups = sectionId === "action-direction"
    ? [["meaning", "nextMove"], ["body"]] as const
    : sectionId === "chart-positioning"
      ? [["meaning", "body"], ["nextMove"]] as const
      : [["meaning", "body", "nextMove"]] as const;
  return { headline: copy.headline, caution: copy.caution, paragraphs: groups.map((fields) => ({ fields, text: fields.map((field) => copy[field]).join("") })) };
}
