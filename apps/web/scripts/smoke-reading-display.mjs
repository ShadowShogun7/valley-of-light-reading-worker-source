import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";
import sharp from "sharp";

const base = process.env.READING_PREVIEW_URL ?? "http://127.0.0.1:3000";
const directory = process.env.READING_SCREENSHOT_DIR ?? "/tmp/valley-reading-display";
await mkdir(directory, { recursive: true });
const browser = await chromium.launch({ headless: true });
const failures = [];
try {
  for (const [name, viewport] of [["desktop", { width: 1440, height: 1000 }], ["mobile", { width: 390, height: 844 }]]) {
    const page = await browser.newPage({ viewport });
    page.on("pageerror", (error) => failures.push(error.message));
    page.on("console", (message) => {
      // The existing local CSP intentionally blocks React's development-only
      // eval debugger. Do not relax production CSP for a preview smoke test.
      if (message.type() === "error" && !message.text().startsWith("eval() is not supported in this environment.")) failures.push(message.text());
    });
    page.on("response", (response) => {
      if (response.status() >= 400 && /\.(webp|png|jpg|svg)(\?|$)/.test(response.url())) failures.push(`asset ${response.status()}: ${response.url()}`);
    });
    await page.goto(`${base}/preview`, { waitUntil: "networkidle", timeout: 120_000 });
    await page.locator("canvas").waitFor();
    await page.waitForTimeout(1500);
    const canvas = page.locator("canvas").first();
    const before = await canvas.screenshot();
    const statistics = await sharp(before).stats();
    assert.ok(statistics.channels.slice(0, 3).some((channel) => channel.stdev > 5), `${name}: blank canvas`);
    await page.waitForTimeout(800);
    assert.ok(!before.equals(await canvas.screenshot()), `${name}: canvas did not move`);
    for (const id of ["chart-positioning", "core-answer", "timing-reading", "action-direction"]) {
      if (name === "mobile") await page.locator(`a[href="#${id}"]:visible`).first().click();
      else await page.locator(`#${id}-tab`).click();
      const panel = page.locator(`[data-reading-step="${id}"]`);
      await panel.waitFor();
      await panel.scrollIntoViewIfNeeded();
      const chapters = panel.locator("[data-reader-display]");
      assert.equal(await chapters.count(), id === "chart-positioning" ? 2 : 1);
      const snapshot = await chapters.evaluateAll((elements) => elements.map((element) => ({
        owner: element.getAttribute("data-reviewed-summary"),
        fields: [...element.querySelectorAll("[data-reader-fields]")].flatMap((node) => node.getAttribute("data-reader-fields").split(",")),
        text: element.textContent,
      })));
      for (const chapter of snapshot) {
        assert.deepEqual(chapter.fields.slice().sort(), ["body", "meaning", "nextMove"]);
        assert.ok(!/副動力|通道未斷|這裡只看|下一頁再看/.test(chapter.text));
      }
      assert.equal(await chapters.locator("p").first().evaluate((node) => getComputedStyle(node).fontWeight), "400");
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
      assert.equal(overflow, false, `${name}/${id}: horizontal overflow`);
      await panel.screenshot({ path: `${directory}/${name}-${id}.png` });
      console.log(`${name}/${id}: canonical chapters, fields, and layout passed`);
    }
    await page.screenshot({ path: `${directory}/${name}-full.png`, fullPage: true });
    await page.goto(`${base}/preview?case=blocked-anxious-still-love-me`, { waitUntil: "networkidle", timeout: 120_000 });
    for (const id of ["timing-reading", "action-direction"]) {
      if (name === "mobile") await page.locator(`a[href="#${id}"]:visible`).first().click();
      else await page.locator(`#${id}-tab`).click();
      const chapter = page.locator(`[data-reviewed-summary="${id}"]`);
      const text = await chapter.innerText();
      assert.match(text, /不主動聯絡|先不要聯絡|不要換|先不要|停止(?:所有)?主動聯絡/);
      if (id === "timing-reading") assert.match(text, /若他主動恢復聯絡|不能預測他是否/);
      await chapter.screenshot({ path: `${directory}/${name}-blocked-${id}.png` });
    }
    await page.goto(`${base}/review`, { waitUntil: "networkidle", timeout: 120_000 });
    assert.equal(await page.locator(".phase5-score-row").count(), 3);
    const tabs = page.locator(".phase5-section-tabs button");
    assert.equal(await tabs.count(), 5);
    for (let index = 0; index < 5; index++) {
      await tabs.nth(index).click();
      assert.equal(await page.locator(".phase5-copy-preview [data-reader-display]").count(), 1);
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, `${name}/review: horizontal overflow`);
    await page.locator(".phase5-copy-preview").screenshot({ path: `${directory}/${name}-review.png` });
    console.log(`${name}: blocked boundaries and shared review display passed`);
    await page.close();
  }
  assert.deepEqual(failures, []);
} finally {
  await browser.close();
}
console.log(`Reading display verified. Screenshots: ${directory}`);
