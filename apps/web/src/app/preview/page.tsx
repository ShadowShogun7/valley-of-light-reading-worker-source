import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { notFound } from "next/navigation";
import { AstrologyResultPage } from "@/components/AstrologyResultPage";
import type { CompleteRelationshipResultViewModel } from "@/data/complete-relationship-result";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false } };

const examples = ["broke-up-long-any-chance", "ambiguous-still-love-me", "blocked-anxious-still-love-me"] as const;

export default async function PreviewPage({ searchParams }: { searchParams: Promise<{ case?: string }> }) {
  if (process.env.NODE_ENV !== "development" || process.env.VALLEY_RUNTIME_ENV === "production") notFound();
  const requested = (await searchParams).case ?? examples[0];
  const example = examples.find((item) => item === requested);
  if (!example) notFound();
  const root = path.resolve(process.cwd(), "../..");
  const { stdout } = await promisify(execFile)(process.env.VALLEY_PYTHON_PATH ?? path.join(root, ".venv/bin/python"), [
    path.join(root, "scripts/build_relationship_result_from_reading.py"),
    "--reading", path.join(root, `examples/readings/${example}.json`), "--json", "--structured-kb-source", "local"
  ], { cwd: root, maxBuffer: 16 * 1024 * 1024, timeout: 30_000 });
  return <AstrologyResultPage data={JSON.parse(stdout) as CompleteRelationshipResultViewModel} />;
}
