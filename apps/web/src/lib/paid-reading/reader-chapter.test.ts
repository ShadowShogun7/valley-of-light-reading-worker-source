import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";
import ts from "typescript";
import { readerChapter, READER_FIELDS } from "./reader-chapter";

const copy = { headline: "標題", meaning: "目的。", body: "完成條件。", nextMove: "具體動作。", caution: "停止條件。" };

test("display includes every final field once and action precedes completion", () => {
  for (const id of ["chart-positioning", "relationship-fit", "core-answer", "timing-reading", "action-direction"] as const) {
    const chapter = readerChapter(id, copy)!;
    assert.deepEqual(new Set(chapter.paragraphs.flatMap((p) => p.fields)), new Set(["meaning", "body", "nextMove"]));
    assert.equal(chapter.headline, copy.headline);
    assert.equal(chapter.caution, copy.caution);
  }
  assert.equal(readerChapter("action-direction", copy)!.paragraphs[0].text, "目的。具體動作。");
});

test("incomplete final copy fails closed, without upstream fallbacks", () => {
  assert.equal(readerChapter("core-answer"), null);
  for (const field of READER_FIELDS) assert.equal(readerChapter("core-answer", { ...copy, [field]: "" }), null);
  const poisoned = { ...copy, summary: "UNREVIEWED", advice: "UNREVIEWED" };
  assert.ok(!JSON.stringify(readerChapter("core-answer", poisoned)).includes("UNREVIEWED"));
});

test("customer and review use the same component; legacy interpretation panels are unreachable", () => {
  for (const name of ["AstrologyResultPage", "Phase5ReviewDashboard", "ImmersiveCosmicDashboard"]) {
    const source = readFileSync(resolve(`src/components/${name}.tsx`), "utf8");
    if (name !== "ImmersiveCosmicDashboard") assert.match(source, /import \{ ReaderChapter \}/);
    const ast = ts.createSourceFile(name, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    const forbidden = new Set(["CoreQuestionPanel", "PartnerNeedsPanel", "TimingPanel", "ActionDirectionPanel", "VisualCompanionPlanPanel"]);
    const functions = new Map<string, ts.FunctionDeclaration>();
    for (const statement of ast.statements) {
      if (ts.isFunctionDeclaration(statement) && statement.name) functions.set(statement.name.text, statement);
    }
    const visited = new Set<string>();
    // Follow local helper calls as well as JSX, so wrapping a legacy panel in a
    // new component cannot silently reopen the upstream-prose display path.
    const visitFunction = (functionName: string) => {
      if (visited.has(functionName)) return;
      visited.add(functionName);
      assert.ok(!forbidden.has(functionName), `legacy panel reachable from ${name}: ${functionName}`);
      const declaration = functions.get(functionName);
      if (!declaration) return;
      const visit = (node: ts.Node) => {
        if (ts.isJsxSelfClosingElement(node) || ts.isJsxOpeningElement(node)) visitFunction(node.tagName.getText(ast));
        if (ts.isCallExpression(node) && ts.isIdentifier(node.expression)) visitFunction(node.expression.text);
        ts.forEachChild(node, visit);
      };
      visit(declaration);
    };
    const root = name === "Phase5ReviewDashboard" ? "ReadingReviewDashboard" : name;
    assert.ok(functions.has(root));
    visitFunction(root);
  }
});
