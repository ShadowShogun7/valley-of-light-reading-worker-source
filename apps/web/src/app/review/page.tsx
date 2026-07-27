import { notFound } from "next/navigation";
import { ReadingReviewDashboard } from "@/components/Phase5ReviewDashboard";
import reviewCorpus from "@/data/generated/phase7-review-cases.json";

export default function ReadingReviewPage() {
  if (
    process.env.NODE_ENV === "production" &&
    process.env.NEXT_PUBLIC_ENABLE_PHASE7_REVIEW !== "1" &&
    process.env.NEXT_PUBLIC_ENABLE_PHASE5_REVIEW !== "1"
  ) {
    notFound();
  }

  return <ReadingReviewDashboard corpus={reviewCorpus} />;
}
