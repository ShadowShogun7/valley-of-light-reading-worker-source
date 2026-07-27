export type StoredReadingStatus =
  | "awaiting_intake"
  | "intake_in_progress"
  | "intake_submitted"
  | "queued"
  | "generating"
  | "retrying"
  | "needs_review"
  | "ready"
  | "delivered"
  | "refunded"
  | "revoked"
  | "erased";

export type CustomerReadingState =
  | "intake"
  | "processing"
  | "ready"
  | "unavailable";

export function customerStateFor(status: string): CustomerReadingState {
  if (status === "awaiting_intake" || status === "intake_in_progress") return "intake";
  if (
    status === "intake_submitted" ||
    status === "queued" ||
    status === "generating" ||
    status === "retrying" ||
    status === "needs_review"
  ) {
    return "processing";
  }
  if (status === "ready" || status === "delivered") return "ready";
  return "unavailable";
}
