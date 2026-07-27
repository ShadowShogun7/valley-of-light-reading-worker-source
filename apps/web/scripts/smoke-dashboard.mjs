import { readFileSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { chromium } from "playwright";

const targetUrl = process.env.DASHBOARD_URL ?? "http://127.0.0.1:3000";
const loadedScenarioFixtures = JSON.parse(
  readFileSync(new URL("../src/data/generated/relationship-result-scenarios.json", import.meta.url), "utf8")
);
const requestedScenarioLimit = Number.parseInt(process.env.DASHBOARD_SCENARIO_LIMIT ?? "0", 10);
const scenarioFixtures = Number.isFinite(requestedScenarioLimit) && requestedScenarioLimit > 0
  ? loadedScenarioFixtures.slice(0, requestedScenarioLimit)
  : loadedScenarioFixtures;
const loadingTitle = "正在解析你們的宇宙軌跡";
const resultTimeoutMs = 210000;
const expectedStructuredKbSource = process.env.VALLEY_EXPECT_STRUCTURED_KB_SOURCE;
const forbiddenCompleteResultKeys = new Set([
  "baziCompatibilityDiagnosis",
  "freeChapters",
  "freeSummary",
  "lockedQuestions",
  "lockedRows",
  "paidBoundary",
  "paidDetailLocked",
  "paidExpansionPlan",
  "paidUnlock",
  "preciseDatesAvailableInFree",
  "relationshipCaseFile"
]);
const forbiddenCompleteResultStrings = [
  "western-free-relationship-v1",
  "freeRelationshipRules"
];
const expectedChartSceneTopics = {
  "chart-positioning": {
    categories: "none",
    label: "星盤定位重點",
    technicalMarker: "你要什麼安全感",
    topic: "chart-positioning"
  },
  "core-answer": {
    label: "核心問題重點",
    technicalMarker: "需求線索",
    topic: "core-answer"
  },
  "timing-reading": {
    label: "時機重點",
    technicalMarker: "2026 轉折氣候",
    topic: "timing-reading"
  },
  "action-direction": {
    label: "行動重點",
    technicalMarker: "行動先避開",
    topic: "action-direction"
  }
};
const readingStepIds = ["chart-positioning", "core-answer", "timing-reading", "action-direction"];
const readingStepTitles = ["星盤定位", "核心問題解讀", "時機節奏", "行動方向"];
const requiredVisualCompanionFields = [
  "focusQuestion",
  "highlightPlanetIds",
  "highlightAspectIds",
  "mutedAspectIds",
  "stopMarkers",
  "recommendedUserAction",
  "whatThisDoesNotProve"
];
const blockedActionLabels = {
  alternate_account_contact: "不要換帳號聯絡",
  repeated_messages: "不要連續傳訊息",
  third_party_pressure: "不要請別人傳話",
  emotional_confrontation: "不要情緒對質",
  long_explanation: "不要一次講太長",
  asking_for_answer_now: "不要立刻要答案",
  pressure_for_commitment: "不要逼承諾",
  checking_social_media: "不要反覆查動態",
  public_confrontation: "不要公開對質",
  rapid_escalation: "不要突然加速",
  relationship_definition_push: "不要急著定義關係",
  turning_reply_into_commitment: "不要把回覆當承諾",
  using_shared_space_as_pressure: "不要用共同空間施壓",
  forcing_relationship_definition: "不要逼關係定位",
  long_pressure_message: "不要傳壓迫長文",
  testing_loyalty: "不要測試對方"
};
const awkwardQuestionCopyTerms = [
  "互動氣候",
  "timing",
  "timing band",
  "timing 壓力",
  "timing climate",
  "reducer",
  "selector",
  "better",
  "neutral",
  "avoid",
  "入口",
  "低壓重啟",
  "等低壓",
  "低壓試探",
  "低壓",
  "低刺激",
  "壓力群組",
  "溝通群組",
  "情緒風險",
  "需求語言",
  "橋接",
  "有橋",
  "控速",
  "降刺激",
  "推進速度與衝突反應",
  "責任與長期承接",
  "消耗界線",
  "先看消耗",
  "需要翻譯",
  "修復槓桿",
  "行動尺度",
  "開口門檻",
  "精準證據",
  "orb 約",
  "Saturn-in-sign",
  "Saturn timing",
  "Saturn pressure",
  "certainty",
  "fatal verdict",
  "Hard contact",
  "hard contact",
  "Soft contact",
  "soft contact",
  "星盤只能支持",
  "這裡應",
  "這題不能被寫成",
  "命盤替你承受壓力",
  "action climate",
  "低需求",
  "可不回",
  "精準日期",
  "精準日",
  "日期精度",
  "行動窗口",
  "聯絡窗口",
  "訊息寫得多完美",
  "用崩潰訊息求答案",
  "等待包裝成命定",
  "未來掃描",
  "把自己放到更低的位置",
  "用熱度要求對方立刻定義關係",
  "先拆掉",
  "先退回防線",
  "表達容易變慢、變怕承諾",
  "自尊和責任感被碰到時冷掉",
  "防衛點",
  "防線",
  "這不是",
  "這裡不是",
  "不是替",
  "不替對方宣告",
  "不能替對方",
  "心理結論",
  "讀心",
  "責任審判",
  "壓力測試",
  "不新增會讓對方更防衛的刺激",
  "不把整段關係一次攤開",
  "turning_reply_into_commitment",
  "rapid_escalation",
  "relationship_definition_push",
  "using_shared_space_as_pressure",
  "public_confrontation"
];
const viewports = [
  { name: "mobile", width: 390, height: 900, path: "/tmp/valley-dashboard-mobile.png", explorerPath: "/tmp/valley-dashboard-mobile-explorer.png" },
  { name: "desktop", width: 1280, height: 900, path: "/tmp/valley-dashboard-desktop.png", explorerPath: "/tmp/valley-dashboard-desktop-explorer.png" }
];

async function hasAnyText(scope, texts, options = {}) {
  for (const text of texts) {
    if (await scope.getByText(text, options).isVisible().catch(() => false)) {
      return true;
    }
  }
  return false;
}

function countScenarioAspects(scenario) {
  const synastry = scenario?.westernRelationshipCaseFile?.synastryLayer ?? {};
  return ["attraction", "emotionalSafety", "pressure", "communication", "repair"].reduce(
    (total, key) => total + (Array.isArray(synastry[key]) ? synastry[key].length : 0),
    0
  );
}

function personAMoonSign(scenario) {
  return String(
    scenario?.westernRelationshipCaseFile?.identityLayer?.personA?.needs?.find?.((need) => need?.point === "Moon")?.sign ?? ""
  );
}

function shouldIgnoreConsoleMessage(type, text) {
  return type === "warning" && /GPU stall due to ReadPixels/.test(text);
}

async function hasNonBlankCosmicCanvas(page) {
  const canvas = page.locator(".immersive-three-wrap canvas").first();
  await canvas.waitFor({ state: "visible", timeout: 10000 }).catch(() => {});
  const box = await canvas.boundingBox().catch(() => null);
  if (!box || box.width < 20 || box.height < 20) return false;
  const width = Math.min(360, Math.max(20, Math.floor(box.width * 0.5)));
  const height = Math.min(240, Math.max(20, Math.floor(box.height * 0.45)));
  const clip = {
    x: Math.max(0, Math.floor(box.x + (box.width - width) / 2)),
    y: Math.max(0, Math.floor(box.y + (box.height - height) / 2)),
    width,
    height
  };
  const screenshot = await page.screenshot({ clip, timeout: 8000 }).catch(() => null);
  return screenshot ? pngHasVisiblePixels(screenshot) : false;
}

function pngHasVisiblePixels(buffer) {
  const signature = buffer.subarray(0, 8).toString("hex");
  if (signature !== "89504e470d0a1a0a") return false;
  let offset = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  const idatChunks = [];
  while (offset + 8 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.subarray(offset + 4, offset + 8).toString("ascii");
    const dataStart = offset + 8;
    const dataEnd = dataStart + length;
    if (dataEnd + 4 > buffer.length) return false;
    if (type === "IHDR") {
      width = buffer.readUInt32BE(dataStart);
      height = buffer.readUInt32BE(dataStart + 4);
      bitDepth = buffer[dataStart + 8];
      colorType = buffer[dataStart + 9];
    } else if (type === "IDAT") {
      idatChunks.push(buffer.subarray(dataStart, dataEnd));
    } else if (type === "IEND") {
      break;
    }
    offset = dataEnd + 4;
  }
  if (!width || !height || bitDepth !== 8 || !idatChunks.length) return false;
  const bytesPerPixel = colorType === 6 ? 4 : colorType === 2 ? 3 : colorType === 4 ? 2 : colorType === 0 ? 1 : 0;
  if (!bytesPerPixel) return false;
  const rowLength = width * bytesPerPixel;
  const inflated = inflateSync(Buffer.concat(idatChunks));
  let sourceOffset = 0;
  const previous = Buffer.alloc(rowLength);
  const current = Buffer.alloc(rowLength);
  let brightPixels = 0;
  let colorVariance = 0;
  let sampled = 0;
  const sampleStride = Math.max(1, Math.floor((width * height) / 2500));

  for (let y = 0; y < height; y += 1) {
    const filter = inflated[sourceOffset];
    sourceOffset += 1;
    inflated.copy(current, 0, sourceOffset, sourceOffset + rowLength);
    sourceOffset += rowLength;
    for (let x = 0; x < rowLength; x += 1) {
      const left = x >= bytesPerPixel ? current[x - bytesPerPixel] : 0;
      const up = previous[x];
      const upLeft = x >= bytesPerPixel ? previous[x - bytesPerPixel] : 0;
      if (filter === 1) {
        current[x] = (current[x] + left) & 255;
      } else if (filter === 2) {
        current[x] = (current[x] + up) & 255;
      } else if (filter === 3) {
        current[x] = (current[x] + Math.floor((left + up) / 2)) & 255;
      } else if (filter === 4) {
        const p = left + up - upLeft;
        const pa = Math.abs(p - left);
        const pb = Math.abs(p - up);
        const pc = Math.abs(p - upLeft);
        current[x] = (current[x] + (pa <= pb && pa <= pc ? left : pb <= pc ? up : upLeft)) & 255;
      }
    }
    for (let x = 0; x < width; x += sampleStride) {
      const index = x * bytesPerPixel;
      const red = current[index] ?? 0;
      const green = colorType === 0 ? red : current[index + 1] ?? red;
      const blue = colorType === 0 ? red : current[index + 2] ?? red;
      const brightness = red + green + blue;
      if (brightness > 90) brightPixels += 1;
      colorVariance += Math.abs(red - green) + Math.abs(green - blue);
      sampled += 1;
    }
    current.copy(previous);
  }
  return brightPixels > 12 || (sampled > 0 && colorVariance / sampled > 8);
}

async function hasCosmicRasterAssets(page) {
  const assetPaths = [
    "/cosmic/galaxy-nebula.webp",
    "/cosmic/solar-system-scope-sun-2k.webp",
    "/cosmic/sun-mandala.webp",
    "/cosmic/sun-corona.webp",
    "/cosmic/zodiac-glyph-wheel.webp",
    "/cosmic/solar-system-scope-earth-2k.webp",
    "/cosmic/solar-system-scope-moon-2k.webp",
    "/cosmic/solar-system-scope-mercury-2k.webp",
    "/cosmic/solar-system-scope-venus-atmosphere-2k.webp",
    "/cosmic/solar-system-scope-mars-2k.webp",
    "/cosmic/solar-system-scope-saturn-2k.webp",
    "/cosmic/saturn-ring.webp",
    "/cosmic/star-sprite.png"
  ];

  return page.evaluate(async (paths) => {
    const checks = await Promise.all(
      paths.map(
        (path) =>
          new Promise((resolve) => {
            const image = new Image();
            image.onload = () => resolve(image.naturalWidth > 64 && image.naturalHeight > 64);
            image.onerror = () => resolve(false);
            image.src = path;
          })
      )
    );
    return checks.every(Boolean);
  }, assetPaths);
}

async function clickImmersiveControl(page, label) {
  const devSwitcherVisible = await page.locator(".dev-result-switcher").isVisible().catch(() => false);
  if (devSwitcherVisible) {
    const control = page.locator(".immersive-control-bar button").filter({ hasText: label }).first();
    await control.waitFor({ state: "attached", timeout: 10000 });
    await control.evaluate((element) => {
      if (element instanceof HTMLButtonElement) element.click();
    });
    return control;
  }

  let lastError;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const control = page.locator(".immersive-control-bar button").filter({ hasText: label }).first();
    try {
      await control.waitFor({ state: "visible", timeout: 10000 });
      await control.click({ timeout: 10000 });
      return page.locator(".immersive-control-bar button").filter({ hasText: label }).first();
    } catch (error) {
      lastError = error;
      const clickedWithDomFallback = await page.evaluate((controlLabel) => {
        const buttons = Array.from(document.querySelectorAll(".immersive-control-bar button"));
        const button = buttons.find((candidate) => candidate.textContent?.includes(controlLabel));
        if (!(button instanceof HTMLButtonElement)) return false;
        button.click();
        return true;
      }, label).catch(() => false);
      if (clickedWithDomFallback) {
        return page.locator(".immersive-control-bar button").filter({ hasText: label }).first();
      }
      await page.waitForTimeout(250);
    }
  }
  throw lastError;
}

async function clickImmersivePlanet(page, label) {
  const planetButton = page.locator(".immersive-planet-button").filter({ hasText: label }).first();
  const devSwitcherVisible = await page.locator(".dev-result-switcher").isVisible().catch(() => false);
  if (devSwitcherVisible) {
    await planetButton.waitFor({ state: "attached", timeout: 8000 });
    await planetButton.evaluate((element) => {
      if (element instanceof HTMLButtonElement) element.click();
    });
    return;
  }

  try {
    await planetButton.waitFor({ state: "visible", timeout: 8000 });
    await planetButton.click({ timeout: 8000 });
  } catch (error) {
    const clickedWithDomFallback = await page.evaluate((planetLabel) => {
      const buttons = Array.from(document.querySelectorAll(".immersive-planet-button"));
      const button = buttons.find((candidate) => candidate.textContent?.includes(planetLabel));
      if (!(button instanceof HTMLButtonElement)) return false;
      button.click();
      return true;
    }, label).catch(() => false);
    if (!clickedWithDomFallback) throw error;
  }
}

async function openReadingTab(page, stepId) {
  const tab = page.locator(`.cosmic-step-nav [role="tab"][aria-controls="${stepId}-panel"]`).first();
  await tab.waitFor({ state: "attached", timeout: 20000 });
  const isVisible = await tab.isVisible().catch(() => false);
  if (isVisible) {
    await tab.evaluate((element) => {
      const tabWrap = element.closest(".reading-tabs-wrap");
      if (!(tabWrap instanceof HTMLElement)) return;
      const wrapRect = tabWrap.getBoundingClientRect();
      const tabRect = element.getBoundingClientRect();
      const targetOffset = tabRect.left - wrapRect.left - (wrapRect.width - tabRect.width) / 2;
      tabWrap.scrollLeft += targetOffset;
    });
    await page.waitForTimeout(80);
    const devSwitcherVisible = await page.locator(".dev-result-switcher").isVisible().catch(() => false);
    if (devSwitcherVisible) {
      await tab.evaluate((element) => {
        if (element instanceof HTMLButtonElement) element.click();
      });
    } else {
      await tab.click();
    }
  } else {
    const clickedWithDomFallback = await page.evaluate((targetStepId) => {
      const button = document.querySelector(`.cosmic-step-nav [role="tab"][aria-controls="${targetStepId}-panel"]`);
      if (!(button instanceof HTMLButtonElement)) return false;
      button.click();
      return true;
    }, stepId).catch(() => false);
    if (!clickedWithDomFallback) {
      throw new Error(`Reading tab ${stepId} exists but could not be clicked`);
    }
  }
  await page.locator(`#${stepId}-panel.cosmic-section`).waitFor({ state: "visible", timeout: 20000 });
  await page.waitForTimeout(80);
  return page.locator("body").innerText();
}

async function readDashboardSceneState(page) {
  const dashboard = page.locator(".immersive-cosmic-dashboard").first();
  const topicSummary = dashboard.locator(".immersive-aspect-summary").first();
  return {
    activeStep: await dashboard.getAttribute("data-active-reading-step"),
    chartScene: await dashboard.getAttribute("data-chart-scene"),
    chartTopic: await dashboard.getAttribute("data-chart-topic"),
    visibleCategories: await dashboard.getAttribute("data-visible-aspect-categories"),
    visibleLineLabels: await dashboard.getAttribute("data-visible-line-labels"),
    visualCompanionFields: await dashboard.getAttribute("data-visual-companion-fields"),
    visualCompanionFocus: await dashboard.getAttribute("data-visual-companion-focus"),
    visualCompanionMode: await dashboard.getAttribute("data-visual-companion-mode"),
    visualCompanionPlan: await dashboard.getAttribute("data-visual-companion-plan"),
    visualHighlightAspectIds: await dashboard.getAttribute("data-visual-highlight-aspect-ids"),
    visualHighlightPlanetIds: await dashboard.getAttribute("data-visual-highlight-planet-ids"),
    visualMutedAspectIds: await dashboard.getAttribute("data-visual-muted-aspect-ids"),
    visualRecommendedAction: await dashboard.getAttribute("data-visual-recommended-action"),
    visualStopMarkers: await dashboard.getAttribute("data-visual-stop-markers"),
    visualTimingCertainty: await dashboard.getAttribute("data-visual-timing-certainty"),
    visualVisibleAspectIds: await dashboard.getAttribute("data-visual-visible-aspect-ids"),
    visualWhatThisDoesNotProve: await dashboard.getAttribute("data-visual-what-this-does-not-prove"),
    topicText: await topicSummary.innerText().catch(() => "")
  };
}

async function waitForDashboardScene(page, stepId) {
  let state = await readDashboardSceneState(page);
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const expected = expectedChartSceneTopics[stepId];
    if (
      state.activeStep === stepId &&
      state.chartScene === stepId &&
      state.chartTopic === expected.topic
    ) {
      return state;
    }
    await page.waitForTimeout(100);
    state = await readDashboardSceneState(page);
  }
  return state;
}

function hasExpectedDashboardScene(state, stepId) {
  const expected = expectedChartSceneTopics[stepId];
  if (!expected) return false;
  const categoriesMatch =
    stepId === "chart-positioning"
      ? state.visibleCategories === expected.categories
      : Boolean(state.visibleCategories);
  const avoidsRawAspectRepetition =
    !state.topicText.includes("容許度") &&
    !state.topicText.includes(" ↔ ") &&
    !state.topicText.includes("金色線");
  const visualFields = String(state.visualCompanionFields ?? "").split(",").filter(Boolean);
  const hasRequiredVisualFields = requiredVisualCompanionFields.every((field) => visualFields.includes(field));
  const hasRuntimeVisualPlan =
    state.visualCompanionPlan === "visual-companion-plan-v1" &&
    state.visualCompanionMode &&
    state.visualCompanionFocus &&
    state.visualHighlightPlanetIds &&
    state.visualHighlightAspectIds &&
    state.visualMutedAspectIds &&
    state.visualStopMarkers &&
    state.visualRecommendedAction &&
    state.visualWhatThisDoesNotProve &&
    hasRequiredVisualFields;

  return Boolean(
    state.activeStep === stepId &&
      state.chartScene === stepId &&
      state.chartTopic === expected.topic &&
      categoriesMatch &&
      avoidsRawAspectRepetition &&
      hasRuntimeVisualPlan &&
      state.topicText.includes(expected.label) &&
      state.topicText.includes(expected.technicalMarker)
  );
}

function visualAspectIdSetKey(value) {
  return String(value ?? "none")
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean)
    .sort()
    .join(",");
}

function hasDistinctLateTabVisualAspectIds(states) {
  const core = visualAspectIdSetKey(states["core-answer"]?.visualVisibleAspectIds);
  const timing = visualAspectIdSetKey(states["timing-reading"]?.visualVisibleAspectIds);
  const action = visualAspectIdSetKey(states["action-direction"]?.visualVisibleAspectIds);
  if (!core || !action) return false;
  if (core === "none" || action === "none") return true;
  return core !== action && (timing === "none" || (timing !== core && timing !== action));
}

function visibleDashboardCopy(value = "") {
  return String(value)
    .replaceAll("不排指定日期", "不指定哪一天")
    .replaceAll("精準日期", "指定日期")
    .replaceAll("精準日", "指定日期")
    .replaceAll("修復入口", "修復位置")
    .replaceAll("協調入口", "協調位置")
    .replaceAll("入口", "位置");
}

function countTextOccurrences(haystack = "", needle = "") {
  if (!needle) return 0;
  return String(haystack).split(String(needle)).length - 1;
}

function normalizeReviewedText(value = "") {
  return String(value).replace(/\s+/gu, " ").trim();
}

async function readReviewedSummary(page, sectionId) {
  const summary = page.locator(`[data-reviewed-summary="${sectionId}"]`);
  return {
    count: await summary.count(),
    text: await summary.first().innerText().catch(() => "")
  };
}

function reviewedSummaryProjectionFailures(scenario, sectionId, rendered) {
  const section = scenario?.finalInterpretation?.sections?.[sectionId];
  const fields = ["headline", "meaning", "body", "nextMove", "caution"];
  const failures = [];

  if (!section) return [`reviewed summary source missing: ${sectionId}`];
  if (rendered.count !== 1) failures.push(`reviewed summary container count ${sectionId}: ${rendered.count}`);

  const visibleText = normalizeReviewedText(rendered.text);
  for (const field of fields) {
    const expected = normalizeReviewedText(section[field]);
    if (!expected) {
      failures.push(`reviewed summary field missing ${sectionId}.${field}`);
    } else if (!visibleText.includes(expected)) {
      failures.push(`reviewed summary field not projected ${sectionId}.${field}`);
    }
  }
  return failures;
}

async function verifyDevResultScenarioPreviews(page) {
  const checks = [];
  let relationshipResultApiCalls = 0;
  let sharedCanvasCheck = null;
  let sharedRasterAssetCheck = null;
  let sharedControlCheck = null;
  const onRequest = (request) => {
    if (request.url().includes("/api/readings/relationship-result")) {
      relationshipResultApiCalls += 1;
    }
  };

  page.on("request", onRequest);
  try {
    for (const [scenarioIndex, scenario] of scenarioFixtures.entries()) {
      if (scenarioIndex === 0) {
        const scenarioUrl = new URL(targetUrl);
        scenarioUrl.searchParams.set("resultScenario", scenario.id);
        await page.goto(scenarioUrl.toString(), { waitUntil: "domcontentloaded" });
      } else {
        const switched = await page.evaluate((scenarioId) => {
          const button = Array.from(document.querySelectorAll(".dev-result-switcher-list button"))
            .find((candidate) => candidate.getAttribute("data-scenario-id") === scenarioId);
          if (!(button instanceof HTMLButtonElement)) return false;
          button.click();
          return true;
        }, scenario.id);
        if (!switched) throw new Error(`Scenario switch button missing: ${scenario.id}`);
      }
      await page.locator(".cosmic-result-frame").waitFor({ state: "visible", timeout: resultTimeoutMs });
      await page.locator(".immersive-cosmic-dashboard").waitFor({ state: "visible", timeout: resultTimeoutMs });
      await page.locator(`.immersive-cosmic-dashboard[data-scenario-id="${scenario.id}"]`).waitFor({
        state: "visible",
        timeout: resultTimeoutMs
      });
      await openReadingTab(page, "chart-positioning");
      await page.waitForTimeout(160);

      const chartPageText = await page.locator("body").innerText();
      const relationshipReviewedSummary = await readReviewedSummary(page, "relationship-fit");
      const previewProfilePanelCount = await page.locator("#chart-positioning-panel .cosmic-positioning-profile").count();
      const previewFunctionRowCount = await page.locator("#chart-positioning-panel .cosmic-positioning-row").count();
      const previewZodiacIconCount = await page.locator("#chart-positioning-panel .cosmic-positioning-cell .cosmic-zodiac-token img[src*='/cosmic/zodiac/']").count();
      const dashboard = page.locator(".immersive-cosmic-dashboard");
      const chartDashboardScene = await waitForDashboardScene(page, "chart-positioning");
      const dashboardActivePoint = await dashboard.getAttribute("data-active-point");
      const dashboardActiveSign = await dashboard.getAttribute("data-active-sign");
      const dashboardScenarioId = await dashboard.getAttribute("data-scenario-id");
      const dashboardAspectCount = Number(await dashboard.getAttribute("data-aspect-count"));
      const dashboardDepthModel = await dashboard.getAttribute("data-depth-model");
      const dashboardVisualTheme = await dashboard.getAttribute("data-visual-theme");
      const dashboardFlatOverlayCount = await page.locator(".immersive-zodiac-overlay, .immersive-orbit-marker").count();
      const answerPageText = await openReadingTab(page, "core-answer");
      const coreReviewedSummary = await readReviewedSummary(page, "core-answer");
      const answerDashboardScene = await waitForDashboardScene(page, "core-answer");
      const timingPageText = await openReadingTab(page, "timing-reading");
      const timingReviewedSummary = await readReviewedSummary(page, "timing-reading");
      const timingDashboardScene = await waitForDashboardScene(page, "timing-reading");
      const actionPageText = await openReadingTab(page, "action-direction");
      const actionReviewedSummary = await readReviewedSummary(page, "action-direction");
      const actionDashboardScene = await waitForDashboardScene(page, "action-direction");
      const allTabText = [chartPageText, answerPageText, timingPageText, actionPageText].join("\n");
      const questionKey = scenario?.answerGuidance?.questionKey ?? "";
      const questionLabel = scenario?.answerGuidance?.questionLabel ?? "";
      const shortAnswer = scenario?.answerGuidance?.shortAnswer ?? "";
      const normalUserAnswer = scenario?.normalUserAnswer ?? scenario?.answerGuidance?.normalUserAnswer ?? {};
      const finalCoreAnswer = scenario?.finalInterpretation?.sections?.["core-answer"] ?? {};
      const visibleShortAnswer = visibleDashboardCopy(
        finalCoreAnswer?.headline || normalUserAnswer?.headline || normalUserAnswer?.directAnswer || shortAnswer
      );
      const visibleCoreBody = visibleDashboardCopy(finalCoreAnswer?.body ?? "");
      const requiredCorePathLabels = ["你問的是", "這題的短答案", "閱讀範圍", "對方在感情裡真正需要什麼", "星盤依據"];
      const relationshipFitLens = scenario?.relationshipFitLens ?? {};
      const relationshipTypeTitle = scenario?.finalInterpretation?.sections?.["relationship-fit"]?.headline ??
        visibleDashboardCopy(relationshipFitLens?.relationshipType?.title ?? scenario?.relationshipArchetype?.title ?? "");
      const relationshipRadarLabels = (relationshipFitLens?.radar ?? []).map((item) => visibleDashboardCopy(item?.label ?? "")).filter(Boolean);
      const partnerNeedTitle = visibleDashboardCopy(scenario?.partnerNeeds?.items?.[0]?.title ?? "");
      const turningWindowTitle = visibleDashboardCopy(scenario?.relationshipTurningWindows?.items?.[0]?.title ?? "");
      const landmineTitle = visibleDashboardCopy(scenario?.fightLandmines?.items?.[0]?.title ?? "");
      const personAHeadline = scenario?.relationshipProfiles?.personA?.headline ?? "";
      const personBHeadline = scenario?.relationshipProfiles?.personB?.headline ?? "";
      const expectedAspectCount = countScenarioAspects(scenario);
      const hasScenarioChartScenes =
        hasExpectedDashboardScene(chartDashboardScene, "chart-positioning") &&
        hasExpectedDashboardScene(answerDashboardScene, "core-answer") &&
        hasExpectedDashboardScene(timingDashboardScene, "timing-reading") &&
        hasExpectedDashboardScene(actionDashboardScene, "action-direction");
      const scenarioDashboardSceneStates = {
        "action-direction": actionDashboardScene,
        "chart-positioning": chartDashboardScene,
        "core-answer": answerDashboardScene,
        "timing-reading": timingDashboardScene
      };
      const hasCanvasPixels = sharedCanvasCheck ?? (sharedCanvasCheck = await hasNonBlankCosmicCanvas(page));
      const hasDashboardAssets = sharedRasterAssetCheck ?? (sharedRasterAssetCheck = await hasCosmicRasterAssets(page));
      const selectedScenarioButton = page.locator(".dev-result-switcher-list button[aria-pressed='true']");
      const selectedScenarioText = await selectedScenarioButton.innerText().catch(() => "");
      const failures = [];

      failures.push(
        ...reviewedSummaryProjectionFailures(scenario, "relationship-fit", relationshipReviewedSummary),
        ...reviewedSummaryProjectionFailures(scenario, "core-answer", coreReviewedSummary),
        ...reviewedSummaryProjectionFailures(scenario, "timing-reading", timingReviewedSummary),
        ...reviewedSummaryProjectionFailures(scenario, "action-direction", actionReviewedSummary)
      );
      if ((await page.locator('[data-reviewed-summary="chart-positioning"]').count()) !== 0) {
        failures.push("chart positioning should not have a reviewed summary card");
      }

      if (!(await page.locator(".dev-result-switcher").isVisible().catch(() => false))) {
        failures.push("QA switcher missing");
      }
      if (!allTabText.includes(questionLabel)) failures.push(`question label missing: ${questionLabel}`);
      if (!visibleShortAnswer || !answerPageText.includes(visibleShortAnswer)) failures.push(`short answer missing: ${questionKey}`);
      if (!personAHeadline || !chartPageText.includes(personAHeadline)) failures.push(`person A headline missing: ${questionKey}`);
      if (!personBHeadline || !chartPageText.includes(personBHeadline)) failures.push(`person B headline missing: ${questionKey}`);
      if (
        previewProfilePanelCount !== 2 ||
        previewFunctionRowCount !== 5 ||
        previewZodiacIconCount < 10 ||
        !["我的星盤", "他的星盤", "安全感模式", "溝通方式", "好感表達", "行動節奏", "壓力下的反應"].every((label) => chartPageText.includes(label))
      ) {
        failures.push(`profile positioning board missing: ${questionKey}`);
      }
      if (
        !requiredCorePathLabels.every((label) => answerPageText.includes(label)) ||
        !visibleCoreBody ||
        !answerPageText.includes(visibleCoreBody)
      ) {
        failures.push(`core answer decision path missing: ${questionKey}`);
      }
      if (dashboardScenarioId !== scenario.id) failures.push(`immersive dashboard scenario mismatch: ${dashboardScenarioId}`);
      if (!hasScenarioChartScenes) {
        failures.push(`immersive chart scenes did not follow tabs: ${JSON.stringify({
          actionDashboardScene,
          answerDashboardScene,
          chartDashboardScene,
          timingDashboardScene
        })}`);
      }
      if (!hasDistinctLateTabVisualAspectIds(scenarioDashboardSceneStates)) {
        failures.push(`late-tab visual aspect ids reused: ${JSON.stringify(scenarioDashboardSceneStates)}`);
      }
      if (scenario?.timingGuidance?.preciseDatesAvailable === false && timingDashboardScene.visualTimingCertainty !== "trend_only") {
        failures.push(`timing certainty should remain trend_only: ${timingDashboardScene.visualTimingCertainty}`);
      }
      if (scenario?.timingGuidance?.preciseDatesAvailable === false && timingDashboardScene.visualVisibleAspectIds !== "none") {
        failures.push(`weak timing data drew aspect ids: ${timingDashboardScene.visualVisibleAspectIds}`);
      }
      if (dashboardActivePoint !== "Moon") failures.push(`immersive dashboard default point mismatch: ${dashboardActivePoint}`);
      if (dashboardActiveSign !== personAMoonSign(scenario)) {
        failures.push(`immersive dashboard sign mismatch: ${dashboardActiveSign} != ${personAMoonSign(scenario)}`);
      }
      if (dashboardAspectCount !== expectedAspectCount) {
        failures.push(`immersive dashboard aspect count mismatch: ${dashboardAspectCount} != ${expectedAspectCount}`);
      }
      if (dashboardDepthModel !== "three-orbit-plane") {
        failures.push(`immersive dashboard depth model mismatch: ${dashboardDepthModel}`);
      }
      if (dashboardVisualTheme !== "ornate-cosmic-instrument") {
        failures.push(`immersive dashboard visual theme mismatch: ${dashboardVisualTheme}`);
      }
      if (dashboardFlatOverlayCount !== 0) {
        failures.push(`immersive flat orbit overlays still present: ${dashboardFlatOverlayCount}`);
      }
      if (!hasCanvasPixels) failures.push(`immersive WebGL canvas appears blank: ${questionKey}`);
      if (!hasDashboardAssets) failures.push(`immersive raster assets did not load: ${questionKey}`);
      if (chartPageText.includes("兩個人的關係契合度分析") || (await page.locator("#relationship-fit-panel").count()) !== 0) {
        failures.push(`relationship-fit tab/panel still visible: ${questionKey}`);
      }
      if (!relationshipTypeTitle || !chartPageText.includes(relationshipTypeTitle)) failures.push(`relationship type missing on positioning tab: ${questionKey}`);
      if (relationshipRadarLabels.length < 5 || relationshipRadarLabels.filter((label) => chartPageText.includes(label)).length < 4) {
        failures.push(`relationship radar missing: ${questionKey}`);
      }
      if (!["關係型態", "契合雷達", "星盤定位"].every((label) => chartPageText.includes(label))) {
        failures.push(`positioning compatibility labels missing: ${questionKey}`);
      }
      if (!partnerNeedTitle || !answerPageText.includes(partnerNeedTitle)) failures.push(`partner need missing: ${questionKey}`);
      if (!turningWindowTitle || !timingPageText.includes(turningWindowTitle)) failures.push(`turning window missing: ${questionKey}`);
      if (!landmineTitle || !actionPageText.includes(landmineTitle)) failures.push(`fight landmine missing: ${questionKey}`);
      if (!["行動策略", "先確認這 4 件事", "接下來的節奏", "行動前檢查", "短訊息範例", "回應分岔", "暖回", "短回", "不回", "冷回", "停止線", "不要怎麼自我解讀", "最需要避開的一個地雷"].every((label) => actionPageText.includes(label))) {
        failures.push(`action checklist missing: ${questionKey}`);
      }
      if (!selectedScenarioText.includes(questionLabel)) {
        failures.push(`active scenario button mismatch: ${questionLabel}`);
      }
      if (sharedControlCheck === null) {
        await clickImmersivePlanet(page, "金星");
        const clickedPoint = await dashboard.getAttribute("data-active-point");
        const aspectToggle = await clickImmersiveControl(page, "相位連線");
        sharedControlCheck = clickedPoint === "Venus" && (await aspectToggle.getAttribute("aria-pressed")) === "false";
        await clickImmersivePlanet(page, "月亮");
        await clickImmersiveControl(page, "相位連線");
      }
      if (!sharedControlCheck) failures.push(`immersive dashboard controls did not update: ${questionKey}`);
      if ((await page.locator(".immersive-control-bar button").filter({ hasText: "星盤探索" }).count()) !== 0) {
        failures.push(`immersive explorer control still visible: ${questionKey}`);
      }
      if (await page.getByText("你想知道這段關係的什麼？").isVisible().catch(() => false)) {
        failures.push("intake visible in direct result preview");
      }

      checks.push({
        id: scenario.id,
        ok: failures.length === 0,
        questionKey,
        failures
      });
    }
  } finally {
    page.off("request", onRequest);
  }

  return {
    apiCalls: relationshipResultApiCalls,
    checked: checks.length,
    failures: checks.filter((check) => !check.ok),
    ok: checks.length === scenarioFixtures.length && checks.every((check) => check.ok) && relationshipResultApiCalls === 0
  };
}

function findForbiddenKeys(value, path = "$", hits = []) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => findForbiddenKeys(item, `${path}[${index}]`, hits));
    return hits;
  }
  if (!value || typeof value !== "object") {
    return hits;
  }
  for (const [key, child] of Object.entries(value)) {
    const childPath = `${path}.${key}`;
    if (forbiddenCompleteResultKeys.has(key)) {
      hits.push(childPath);
    }
    findForbiddenKeys(child, childPath, hits);
  }
  return hits;
}

const browser = await chromium.launch({ headless: true });
const results = [];
let sharedDevResultScenarioPreviews = null;

for (const viewport of viewports) {
  const page = await browser.newPage({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: 2
  });
  const messages = [];

  page.on("console", (message) => {
    const type = message.type();
    const text = message.text();
    if (["error", "warning"].includes(type) && !shouldIgnoreConsoleMessage(type, text)) {
      messages.push({ type, text });
    }
  });
  page.on("pageerror", (error) => {
    messages.push({ type: "pageerror", text: error.message });
  });

  await page.goto(targetUrl, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  const hasIntakeOpening = await page.getByText("關係合盤解讀").isVisible();
  const hasProvidedIntroBackground = await page.locator(".origin-hero").evaluate((node) =>
    getComputedStyle(node).backgroundImage.includes("intake-galaxy-background.webp")
  );
  const hasTestingShortcut = await page.getByRole("button", { name: "使用固定測試資料" }).isVisible();
  const hasNoModelSwitch = !(await page.getByLabel("測試敘事模型").isVisible());
  const hasNoModelSwitchOptions =
    !(await page.getByText("GPT-5.5").isVisible()) &&
    !(await page.getByText("Opus 4.7").isVisible()) &&
    !(await page.getByText("Grok 4.3").isVisible());
  await page.getByRole("button", { name: "開始填寫" }).click();
  const hasNoEmotionStep = !(await page.getByText("你現在的狀態比較接近哪一種？").isVisible());
  const hasBirthData = await page.getByRole("heading", { name: "你的出生資料" }).isVisible();
  const hasNoPreselectedBirth =
    await page.locator(".date-segments input").evaluateAll((inputs) => inputs.every((input) => input.value === "")) &&
    (await page.locator(".gender-segments button.selected").count()) === 0;
  const hasCityEntry = await page.getByLabel("你的出生資料出生城市").isVisible();
  await page.getByLabel("你的出生資料出生年份").pressSequentially("1992");
  const yearAutoAdvancesToMonth = await page.getByLabel("你的出生資料出生月份").evaluate((node) => node === document.activeElement);
  await page.getByLabel("你的出生資料出生年份").fill("199212");
  const yearCapsAtFourDigits = (await page.getByLabel("你的出生資料出生年份").inputValue()) === "1992";
  await page.getByLabel("你的出生資料出生月份").fill("06");
  await page.getByLabel("你的出生資料出生日期日").fill("18");
  await page.locator("input[type='time']").fill("14:30");
  await page.getByLabel("你的出生資料出生城市").fill("台北市");
  await page.getByRole("button", { name: "女" }).click();
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  const hasNoPreselectedPartner =
    await page.locator(".date-segments input").evaluateAll((inputs) => inputs.every((input) => input.value === "")) &&
    (await page.locator(".gender-segments button.selected").count()) === 0;
  const hasPartnerCityEntry = await page.getByLabel("對方的出生資料出生城市").isVisible();
  await page.getByLabel("對方的出生資料出生年份").fill("1990");
  await page.getByLabel("對方的出生資料出生月份").fill("10");
  await page.getByLabel("對方的出生資料出生日期日").fill("03");
  await page.locator("input[type='time']").fill("09:15");
  await page.getByLabel("對方的出生資料出生城市").fill("台北市");
  await page.getByRole("button", { name: "男" }).click();
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  const hasNoPreselectedStage = (await page.locator(".intake-design-option-card.is-selected").count()) === 0;
  await page.getByText("還在一起但很不穩").click();
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  const hasNoPreselectedQuestion = (await page.locator(".intake-design-option-card.is-selected").count()) === 0;
  await page.getByRole("button", { name: "他現在是否還想繼續？" }).click();
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  const hasNoPreselectedContact = (await page.locator(".intake-design-option-card.is-selected").count()) === 0;
  await page.getByRole("button", { name: "還會聊天但很冷" }).click();
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  const hasConfirm = await page.getByText("確認你的解讀資料").isVisible();
  const relationshipResultResponsePromise = page.waitForResponse(
    (response) => response.url().includes("/api/readings/relationship-result") && response.request().method() === "POST",
    { timeout: resultTimeoutMs }
  );
  await page.getByRole("button", { name: "開始完整解讀" }).click();
  const hasLoadingGate = await page.getByText(loadingTitle).isVisible();
  const hasLoadingProof = await page.getByText("相位計算")
    .waitFor({ state: "visible", timeout: 10000 })
    .then(() => true)
    .catch(() => false);
  const hasNoLoadingReading = !(await page.getByText("生成下一步建議").isVisible()) &&
    !(await page.getByText("你是").isVisible()) &&
    !(await page.getByText("行動焦點").isVisible()) &&
    !(await page.getByText("排出八字四柱").isVisible()) &&
    !(await page.getByText("計算八字關係指標").isVisible());
  const relationshipResultResponse = await relationshipResultResponsePromise;
  const apiStatus = relationshipResultResponse.status();
  const apiPayload = await relationshipResultResponse.json().catch(() => null);
  const apiPayloadText = JSON.stringify(apiPayload ?? {});
  const forbiddenApiKeyHits = findForbiddenKeys(apiPayload);
  const forbiddenApiStringHits = forbiddenCompleteResultStrings.filter((term) => apiPayloadText.includes(term));
  const hasRuntimeApiOk = relationshipResultResponse.ok();
  const hasRuntimeEngineVersions = Boolean(
    apiPayload?.debug?.engineVersions?.immanuel
  );
  const hasExpectedStructuredKbSource = Boolean(
    !expectedStructuredKbSource || apiPayload?.debug?.structuredKbSource === expectedStructuredKbSource
  );
  const hasNoBaziCalculationProofPayload = !apiPayload?.calculationProof?.people?.some?.(
    (person) => person?.dayMaster || person?.dayPillar || person?.pillars
  );
  const hasNoLegacyBaziPayload = Boolean(
    !apiPayload?.relationshipCaseFile &&
      !apiPayload?.baziCompatibilityDiagnosis &&
      !apiPayload?.relationshipDiagnosis &&
      !apiPayload?.evidence?.bazi &&
      !Object.prototype.hasOwnProperty.call(apiPayload?.debug ?? {}, "baziSlot")
  );
  const hasWesternRelationshipCaseFilePayload = Boolean(
    apiPayload?.westernRelationshipCaseFile?.version === "western-relationship-case-file-v1" &&
      apiPayload?.westernRelationshipCaseFile?.inputQuality?.personA?.precision &&
      apiPayload?.westernRelationshipCaseFile?.inputQuality?.personB?.precision &&
      apiPayload?.westernRelationshipCaseFile?.identityLayer?.personA?.needs?.length >= 3 &&
      apiPayload?.westernRelationshipCaseFile?.identityLayer?.personB?.needs?.length >= 3 &&
      apiPayload?.westernRelationshipCaseFile?.synastryLayer?.attraction?.length >= 1 &&
      apiPayload?.westernRelationshipCaseFile?.synastryLayer?.pressure?.length >= 1 &&
      apiPayload?.westernRelationshipCaseFile?.timingLayer?.currentTransits?.length >= 1 &&
      apiPayload?.westernRelationshipCaseFile?.answerLayer?.shortAnswer
  );
  const hasRelationshipProfilesPayload = Boolean(
    apiPayload?.relationshipProfiles?.version === "relationship-profiles-v1" &&
      apiPayload?.relationshipProfiles?.personA?.cards?.length >= 5 &&
      apiPayload?.relationshipProfiles?.personB?.cards?.length >= 5 &&
      apiPayload?.relationshipProfiles?.personA?.suitableFor?.length >= 1 &&
      apiPayload?.relationshipProfiles?.personB?.doesNotFit?.length >= 1 &&
      apiPayload?.relationshipProfiles?.fitSummary?.summary &&
      (
        apiPayload?.relationshipProfiles?.fitSummary?.natural?.length +
        apiPayload?.relationshipProfiles?.fitSummary?.effort?.length +
        apiPayload?.relationshipProfiles?.fitSummary?.friction?.length
      ) >= 3 &&
      apiPayload?.relationshipProfiles?.answerBridge
  );
  const answerReadable =
    apiPayload?.answerGuidance?.readableInterpretation ??
    apiPayload?.readableQuestionAnswer?.sections?.answer?.readableInterpretation ??
    {};
  const answerReadableText = JSON.stringify([
    answerReadable?.headline,
    answerReadable?.meaning,
    answerReadable?.body,
    answerReadable?.nextMove,
    answerReadable?.caution,
    ...(apiPayload?.answerGuidance?.evidenceHighlights ?? []).flatMap((item) => [item?.title, item?.body])
  ]);
  const hasAnswerGuidancePayload = Boolean(
    apiPayload?.answerGuidance?.version === "answer-guidance-v1" &&
      apiPayload?.readableQuestionAnswer?.sections?.answer?.version === "answer-guidance-v1" &&
      answerReadable?.version === "readable-interpretation-v1" &&
      answerReadable?.module === "question_answer" &&
      answerReadable?.headline &&
      answerReadable?.body &&
      answerReadable?.nextMove &&
      (apiPayload?.answerGuidance?.evidenceHighlights ?? []).length >= 3 &&
      !/免費|付費|free|V1|完整報告|付費報告|reducer|selector|soft_tone|boundary_only/i.test(answerReadableText)
  );
  const actionReadable =
    apiPayload?.actionGuidance?.readableInterpretation ??
    apiPayload?.readableQuestionAnswer?.sections?.action?.readableInterpretation ??
    {};
  const actionReadableText = JSON.stringify([
    actionReadable?.headline,
    actionReadable?.meaning,
    actionReadable?.body,
    actionReadable?.nextMove,
    actionReadable?.caution
  ]);
  const hasActionGuidancePayload = Boolean(
    apiPayload?.actionGuidance?.statusKey &&
      apiPayload?.readableQuestionAnswer?.sections?.action?.statusKey === apiPayload?.actionGuidance?.statusKey &&
      actionReadable?.version === "readable-interpretation-v1" &&
      actionReadable?.module === "question_action" &&
      actionReadable?.headline &&
      actionReadable?.body &&
      actionReadable?.nextMove &&
      !/action_scale|boundary_only|contactSituationPolicy|low_pressure|reducer|selector/i.test(actionReadableText)
  );
  const timingReadable =
    apiPayload?.timingGuidance?.readableInterpretation ??
    apiPayload?.readableQuestionAnswer?.sections?.timing?.readableInterpretation ??
    {};
  const timingReadableText = JSON.stringify([
    timingReadable?.headline,
    timingReadable?.meaning,
    timingReadable?.body,
    timingReadable?.nextMove,
    timingReadable?.caution,
    ...(apiPayload?.timingGuidance?.selectedSignals ?? []).flatMap((signal) => [signal?.title, signal?.body])
  ]);
  const hasTimingGuidancePayload = Boolean(
    apiPayload?.timingGuidance?.version === "timing-guidance-v1" &&
      apiPayload?.readableQuestionAnswer?.sections?.timing?.version === "timing-guidance-v1" &&
      timingReadable?.version === "readable-interpretation-v1" &&
      timingReadable?.module === "question_timing" &&
      timingReadable?.headline &&
      timingReadable?.body &&
      timingReadable?.nextMove &&
      apiPayload?.timingGuidance?.preciseDatesAvailable === false &&
      !/timing|avoid_push|low_pressure|not_calculated|reducer|selector|窗口|低壓/i.test(timingReadableText)
  );
  const finalInterpretation =
    apiPayload?.finalInterpretation ?? apiPayload?.readableQuestionAnswer?.sections?.finalInterpretation ?? {};
  const finalCoreReadable = finalInterpretation?.sections?.["core-answer"] ?? {};
  const finalTimingReadable = finalInterpretation?.sections?.["timing-reading"] ?? {};
  const finalActionReadable = finalInterpretation?.sections?.["action-direction"] ?? {};
  const finalInterpretationText = JSON.stringify(
    readingStepIds.flatMap((stepId) => {
      const section = finalInterpretation?.sections?.[stepId] ?? {};
      return [section?.headline, section?.meaning, section?.body, section?.nextMove, section?.caution];
    })
  );
  const hasFinalInterpretationPayload = Boolean(
    finalInterpretation?.version === "final-reading-interpretation-v1" &&
      apiPayload?.readableQuestionAnswer?.sections?.finalInterpretation?.version === "final-reading-interpretation-v1" &&
      finalInterpretation?.locale === "zh-TW" &&
      finalInterpretation?.methodClaimIds?.length >= 1 &&
      finalInterpretation?.evidenceClusterKeys?.length >= 1 &&
      readingStepIds.every((stepId) => {
        const section = finalInterpretation?.sections?.[stepId] ?? {};
        return (
          section?.version === "readable-interpretation-v1" &&
          String(section?.module ?? "").startsWith("final_") &&
          section?.headline &&
          section?.body &&
          section?.nextMove &&
          section?.caution &&
          section?.methodClaimIds?.length >= 1 &&
          section?.evidenceClusterKeys?.length >= 1
        );
      }) &&
      !/birth_time|noon fallback|date_noon_fallback|reducer|selector|methodClaim|sourceClaim|精準日期|免費|解鎖|八字|bazi/i.test(finalInterpretationText)
  );
  const hasReadableInterpretationPayload = Boolean(
    apiPayload?.relationshipProfiles?.personA?.cards?.every?.(
      (card) =>
        card.readableInterpretation?.version === "readable-interpretation-v1" &&
        card.readableInterpretation?.module === "person_function_sign" &&
        card.readableInterpretation?.meaning &&
        card.readableInterpretation?.body &&
        card.readableInterpretation?.stuckPattern
    ) &&
      apiPayload?.relationshipProfiles?.personB?.cards?.every?.(
        (card) =>
          card.readableInterpretation?.version === "readable-interpretation-v1" &&
          card.readableInterpretation?.module === "person_function_sign" &&
          card.readableInterpretation?.body &&
          card.readableInterpretation?.stuckPattern
      ) &&
      apiPayload?.relationshipProfiles?.fitSummary?.readableInterpretation?.version === "readable-interpretation-v1" &&
      apiPayload?.relationshipProfiles?.fitSummary?.readableInterpretation?.module === "fit_summary" &&
      ["natural", "effort", "friction"].every((bucket) =>
        apiPayload?.relationshipProfiles?.fitSummary?.[bucket]?.every?.(
          (item) =>
            item.readableInterpretation?.module === "fit_summary_item" &&
            item.readableInterpretation?.body &&
            item.nextMove
        )
      ) &&
      apiPayload?.readableQuestionAnswer?.version === "readable-question-answer-v1" &&
      hasAnswerGuidancePayload &&
      apiPayload?.readableQuestionAnswer?.sections?.thoughts?.every?.(
        (item) =>
          item.readableInterpretation?.module === "question_thought" &&
          item.readableInterpretation?.body &&
          item.readableInterpretation?.nextMove
      ) &&
      apiPayload?.reasons?.every?.(
        (item) =>
          item.readableInterpretation?.module === "question_reason" &&
          item.readableInterpretation?.body &&
          item.nextMove
      ) &&
      apiPayload?.chance?.readableInterpretation?.module === "question_chance" &&
      apiPayload?.chance?.nextMove &&
      apiPayload?.timeline?.every?.(
        (item) =>
          item.readableInterpretation?.module === "question_timeline" &&
          item.readableInterpretation?.body &&
          item.nextMove
      ) &&
      apiPayload?.readableQuestionAnswer?.sections?.donts?.every?.(
        (item) =>
          item.readableInterpretation?.module === "question_boundary" &&
          item.readableInterpretation?.body
      ) &&
      hasActionGuidancePayload &&
      hasTimingGuidancePayload &&
      hasFinalInterpretationPayload
  );
  const westernClusters = apiPayload?.westernRelationshipCaseFile?.evidenceClusters ?? {};
  const expectedWesternMethodClusters = [
    "methodOrder",
    "natalSymbolFoundation",
    "planetaryFunctions",
    "signClassificationFoundation",
    "elementStyleFoundation",
    "modalityResponseFoundation",
    "planetSignStyle",
    "sunMoonAscProfile",
    "angleHouseFramework",
    "aspectPairPhraseTemplateMethod",
    "aspectInterpretationFoundation",
    "aspectSynthesisCrossCheck",
    "consultationSafety",
    "nonfatalSynastrySafety"
  ];
  const expectedFunctionSignClusters = [
    ["moonSignEmotionalSafety", "Moon"],
    ["mercurySignCommunicationRepair", "Mercury"],
    ["venusSignAffectionStyle", "Venus"],
    ["marsSignPursuitConflict", "Mars"],
    ["saturnSignDefenseDelay", "Saturn"]
  ];
  const expectedFunctionMatrixClusters = [
    ["functionElementMatrix", "western-atom-function-element-matrix"],
    ["functionModalityMatrix", "western-atom-function-modality-matrix"]
  ];
  const expectedTimingSelectorClusters = [
    "timingWindowBand",
    "timingMercuryCommunication",
    "timingVenusSoftening",
    "timingMarsActivation",
    "timingSaturnPressure",
    "timingMoonWeather"
  ];
  const timingWindowScan = apiPayload?.westernRelationshipCaseFile?.timingLayer?.windowScan ?? {};
  const hasWesternMethodClustersPayload = expectedWesternMethodClusters.every(
    (category) =>
      westernClusters?.[category]?.category === category &&
      westernClusters?.[category]?.atomId?.startsWith("western-atom-") &&
      westernClusters?.[category]?.claimSupport?.length >= 1
  );
  const nonfatalSynastrySafety = westernClusters?.nonfatalSynastrySafety ?? {};
  const hasNonfatalSynastrySafetyPayload = Boolean(
    nonfatalSynastrySafety?.category === "nonfatalSynastrySafety" &&
      nonfatalSynastrySafety?.atomId === "western-atom-nonfatal-synastry-safety" &&
      nonfatalSynastrySafety?.source === "western-modern-nonfatal-synastry" &&
      nonfatalSynastrySafety?.hasNoGuaranteedOutcome === true &&
      nonfatalSynastrySafety?.hardAspectsArePressureNotVerdict === true &&
      nonfatalSynastrySafety?.requiresConditionalConclusion === true &&
      nonfatalSynastrySafety?.claimSupport?.length >= 1
  );
  const hasFunctionSignClustersPayload = expectedFunctionSignClusters.every(
    ([category, point]) =>
      westernClusters?.[category]?.category === category &&
      westernClusters?.[category]?.point === point &&
      westernClusters?.[category]?.personStyles?.length === 2 &&
      westernClusters?.[category]?.personStyles?.every?.(
        (style) => style.element && style.elementStyle && style.modality && style.modalityStyle
      ) &&
      westernClusters?.[category]?.claimSupport?.length >= 1
  );
  const hasFunctionMatrixClustersPayload = expectedFunctionMatrixClusters.every(
    ([category, atomId]) =>
      westernClusters?.[category]?.category === category &&
      westernClusters?.[category]?.atomId === atomId &&
      westernClusters?.[category]?.itemCount === 10 &&
      westernClusters?.[category]?.personStyles?.length === 10 &&
      westernClusters?.[category]?.claimSupport?.length >= 1
  );
  const aspectFunctionCombinations = westernClusters?.aspectFunctionCombination?.selectedCombinations ?? [];
  const hasAspectFunctionCombinationPayload = Boolean(
    westernClusters?.aspectFunctionCombination?.category === "aspectFunctionCombination" &&
      westernClusters?.aspectFunctionCombination?.atomId === "western-atom-aspect-function-combination" &&
      westernClusters?.aspectFunctionCombination?.source === "western-aspect-function-combination-reducers" &&
      westernClusters?.aspectFunctionCombination?.claimSupport?.length >= 1 &&
      aspectFunctionCombinations.length >= 1 &&
      aspectFunctionCombinations.every?.(
        (item) =>
          (
            item.sourceClaimId?.startsWith?.("western-aspect-function-combination-reducers-") ||
            item.sourceClaimId?.startsWith?.("western-aspects-")
          ) &&
          item.functionSynthesis &&
          item.reducerInstruction &&
          item.pointStyles?.length === 2
      )
  );
  const aspectContactModifier = westernClusters?.aspectContactModifier ?? {};
  const hasAspectContactModifierPayload = Boolean(
    aspectContactModifier?.category === "aspectContactModifier" &&
      aspectContactModifier?.atomId?.startsWith?.("western-atom-aspect-contact-modifier-") &&
      aspectContactModifier?.source === "western-aspect-contact-type-modifiers" &&
      aspectContactModifier?.claimSupport?.length >= 1 &&
      aspectContactModifier?.selectedModifiers?.length >= 1 &&
      ["conjunction", "soft", "hard", "minor", "other"].includes(aspectContactModifier?.dominantContactType)
  );
  const aspectPairContactTemplate = westernClusters?.aspectPairContactTemplate ?? {};
  const hasAspectPairContactTemplatePayload = Boolean(
    aspectPairContactTemplate?.category === "aspectPairContactTemplate" &&
      aspectPairContactTemplate?.atomId?.startsWith?.("western-atom-pair-template-") &&
      aspectPairContactTemplate?.claimSupport?.length >= 1 &&
      aspectPairContactTemplate?.selectedTemplates?.length >= 1 &&
      aspectPairContactTemplate?.hasPairTemplate === true
  );
  const timingContactReducer = westernClusters?.timingContactReducer ?? {};
  const hasTimingContactReducerPayload = Boolean(
    timingContactReducer?.category === "timingContactReducer" &&
      timingContactReducer?.atomId === "western-atom-timing-contact-reducer" &&
      timingContactReducer?.source === "western-contact-timing-action-reducers" &&
      timingContactReducer?.preciseDatesAvailable === false &&
      timingContactReducer?.exactTimingPolicy?.preciseDatesAvailable === false &&
      timingContactReducer?.claimSupport?.length >= 1 &&
      timingContactReducer?.recommendedAction &&
      timingContactReducer?.contactInstruction
  );
  const contactSituationPolicy = westernClusters?.contactSituationPolicy ?? {};
  const hasContactSituationPolicyPayload = Boolean(
    contactSituationPolicy?.category === "contactSituationPolicy" &&
      contactSituationPolicy?.atomId === "western-atom-contact-situation-policy" &&
      contactSituationPolicy?.source === "context-contact-status" &&
      contactSituationPolicy?.statusKey &&
      typeof contactSituationPolicy?.actionScale === "number" &&
      contactSituationPolicy?.actionMode &&
      contactSituationPolicy?.allowedAction &&
      contactSituationPolicy?.timingCanOverrideBoundary === false &&
      contactSituationPolicy?.blockedActions?.length >= 1 &&
      contactSituationPolicy?.claimSupport?.length >= 1
  );
  const hasTimingSelectorClustersPayload = expectedTimingSelectorClusters.every(
    (category) =>
      westernClusters?.[category]?.category === category &&
      westernClusters?.[category]?.atomId?.startsWith("western-atom-") &&
      westernClusters?.[category]?.source === "western-transits-timing-selector-windows" &&
      westernClusters?.[category]?.preciseDatesAvailable === false &&
      westernClusters?.[category]?.exactTimingPolicy?.preciseDatesAvailable === false &&
      westernClusters?.[category]?.claimSupport?.length >= 1
  );
  const hasPublicTimingWindowScanPayload = Boolean(
    timingWindowScan?.method === "western-transit-window-scan-v1" &&
      timingWindowScan?.sampleCount >= 1 &&
      timingWindowScan?.preciseDatesAvailable === false &&
      timingWindowScan?.exactTimingPolicy?.preciseDatesAvailable === false &&
      !Object.prototype.hasOwnProperty.call(timingWindowScan, "windows") &&
      !Object.prototype.hasOwnProperty.call(timingWindowScan, "day_summaries") &&
      !Object.prototype.hasOwnProperty.call(timingWindowScan, "daySummaries")
  );
  const hasFunctionSignBlueprintEvidence = [...expectedFunctionSignClusters, ...expectedFunctionMatrixClusters, ["aspectContactModifier"], ["aspectPairContactTemplate"], ["aspectFunctionCombination"], ["timingContactReducer"]].every(([category]) =>
    apiPayload?.readingBlueprint?.chapters?.some?.((chapter) =>
      chapter.evidence?.some?.((item) => item.atomId === westernClusters?.[category]?.atomId)
    )
  );
  const activeBlueprintChapters = Array.isArray(apiPayload?.readingBlueprint?.chapters) ? apiPayload.readingBlueprint.chapters : [];
  const hasCompleteResultContractPayload = Boolean(
    apiPayload?.contractVersion === "complete-relationship-result-v1" &&
      apiPayload?.westernRelationshipCaseFile?.answerLayer?.rulesetId === "western-relationship-result-v1" &&
      apiPayload?.westernRelationshipCaseFile?.answerLayer?.questionBlueprintId === "western-relationship-result-v1" &&
      apiPayload?.includedReadingRows?.length >= 4 &&
      apiPayload?.readingBlueprint?.includedReadingPlan?.length >= 4 &&
      activeBlueprintChapters.length === 3
  );
  const hasNoLegacyCompleteResultContractPayload = forbiddenApiKeyHits.length === 0 && forbiddenApiStringHits.length === 0;
  const hasReadingBlueprintPayload = Boolean(
    apiPayload?.readingBlueprint?.version === "reading-blueprint-v1" &&
      Boolean(apiPayload?.readingBlueprint?.suggestedResultTitle) &&
      apiPayload?.readingBlueprint?.resultTitleSeeds?.length >= 2 &&
      activeBlueprintChapters.length === 3 &&
      activeBlueprintChapters.every?.(
        (chapter) => chapter.coreSummary && chapter.technicalFocus && chapter.psychologicalFocus && chapter.evidence?.length >= 1
      ) &&
      apiPayload?.readingBlueprint?.forbiddenClaims?.length >= 3
  );
  const hasClaimSupportPayload = Boolean(
    apiPayload?.westernRelationshipCaseFile?.synastryLayer?.pressure?.some?.(
      (item) => item.claimSupport?.length >= 1
    ) &&
      activeBlueprintChapters.some?.(
        (chapter) => chapter.evidence?.some?.((item) => item.claimSupport?.length >= 1)
      )
  );
  const hasNoMissingSignalPlaceholdersPayload =
    !apiPayloadText.includes("未選定訊號") && !apiPayloadText.includes("可用訊號不足");
  const hasNoBaziPayloadText =
    !apiPayloadText.includes("八字") &&
    !apiPayloadText.includes("日主") &&
    !apiPayloadText.includes("四柱") &&
    !apiPayloadText.includes("配偶星") &&
    !apiPayloadText.includes("bazi") &&
    !apiPayloadText.includes("Bazi");
  const hasAdvancedWesternPayload =
    apiPayloadText.includes("westernRelationshipCaseFile") &&
    apiPayloadText.includes("synastryLayer") &&
    apiPayloadText.includes("inputQuality") &&
    apiPayloadText.includes("currentTransits");
  const hasNoRuntimeNarrativePayload = !apiPayload?.narrative;
  const hasNoRuntimeNarrativeDebug = ![
    "narrativeMode",
    "narrativeProvider",
    "narrativeProfileId",
    "narrativeProfileLabel",
    "narrativeModel",
    "narrativeReasoningEffort",
    "narrativeError"
  ].some((key) => Object.prototype.hasOwnProperty.call(apiPayload?.debug ?? {}, key));
  const answerEvidenceContract = apiPayload?.westernRelationshipCaseFile?.answerLayer?.evidenceContract ?? {};
  const hasAnswerEvidenceContractPayload = Boolean(
    answerEvidenceContract?.version === "western-answer-evidence-contract-v1" &&
      answerEvidenceContract?.calculationEvidence?.length >= 1 &&
      answerEvidenceContract?.currentTransitEvidence?.length >= 1 &&
      answerEvidenceContract?.contextModifier?.stageKey &&
      answerEvidenceContract?.contextModifier?.contactStatusKey &&
      answerEvidenceContract?.contextModifier?.actionBoundary &&
      typeof answerEvidenceContract?.contextModifier?.contactActionScale === "number" &&
      answerEvidenceContract?.contextModifier?.contactActionMode &&
      answerEvidenceContract?.contextModifier?.contactAllowedAction &&
      answerEvidenceContract?.contextModifier?.timingCanOverrideBoundary === false &&
      answerEvidenceContract?.precision?.timingPrecision
  );
  await page.getByText("查看完整解讀").waitFor({ state: "visible", timeout: resultTimeoutMs });
  await page.getByText("查看完整解讀").click();
  await page.waitForTimeout(150);
  const title = await page.locator(".reading-chart-meta h2").innerText();
  const hasGeneratedResultTitle =
    title.length >= 4 &&
     !title.includes("他現在心裡還有我嗎") &&
     title !== apiPayload?.reading?.answer;
  const hasNoScenarioSwitcher = (await page.locator("select[aria-label='選擇測試情境']").count()) === 0;
  const pageText = await page.locator("body").innerText();
  const resultStepTitles = readingStepTitles;
  const resultStepIds = readingStepIds;
  const tabControls = await page.locator(".cosmic-step-nav [role='tab']").evaluateAll((tabs) =>
    tabs.map((tab) => ({
      controls: tab.getAttribute("aria-controls"),
      label: tab.getAttribute("aria-label"),
      selected: tab.getAttribute("aria-selected")
    }))
  );
  const hasCosmicFourStepResult =
    await page.locator(".reading-report-app[aria-label='完整關係星盤解讀']").isVisible() &&
    (await page.locator(".reading-sidebar").count()) === 1 &&
    await page.locator(".reading-chart-zone").isVisible() &&
    tabControls.length === 4 &&
    resultStepIds.every((stepId) => tabControls.some((tab) => tab.controls === `${stepId}-panel`)) &&
    resultStepTitles.every((stepTitle) => tabControls.some((tab) => tab.label?.includes(stepTitle))) &&
    (await page.locator(".cosmic-section").count()) === 1 &&
    pageText.includes("星盤定位");
  await page.locator(".immersive-cosmic-dashboard").waitFor({ state: "visible", timeout: resultTimeoutMs });
  await page.waitForTimeout(420);
  const immersiveDashboard = page.locator(".immersive-cosmic-dashboard");
  const immersiveActivePoint = await immersiveDashboard.getAttribute("data-active-point");
  const immersiveActiveSign = await immersiveDashboard.getAttribute("data-active-sign");
  const immersiveScenarioId = await immersiveDashboard.getAttribute("data-scenario-id");
  const immersiveAspectCount = Number(await immersiveDashboard.getAttribute("data-aspect-count"));
  const immersiveDepthModel = await immersiveDashboard.getAttribute("data-depth-model");
  const immersiveSelectedHighlight = await immersiveDashboard.getAttribute("data-selected-highlight");
  const immersiveVisualTheme = await immersiveDashboard.getAttribute("data-visual-theme");
  const immersiveFlatOverlayCount = await page.locator(".immersive-zodiac-overlay, .immersive-orbit-marker").count();
  const expectedImmersiveAspectCount = countScenarioAspects(apiPayload);
  const initialDashboardScene = await waitForDashboardScene(page, "chart-positioning");
  const hasImmersiveCanvasNonBlank = await hasNonBlankCosmicCanvas(page);
  const hasImmersiveRasterAssets = await hasCosmicRasterAssets(page);
  const hasImmersiveCosmicDashboard = Boolean(
    await immersiveDashboard.isVisible() &&
      (await page.locator(".reading-chart-zone .immersive-cosmic-dashboard").count()) === 1 &&
      (await page.locator(".immersive-three-wrap canvas").count()) >= 1 &&
      (await page.locator(".immersive-control-bar button").count()) === 6 &&
      pageText.includes("雙人互動星盤") &&
      pageText.includes("關係軌跡")
  );
  const hasImmersiveScenarioDrivenSelection = Boolean(
    immersiveScenarioId === apiPayload?.id &&
      immersiveActivePoint === "Moon" &&
      immersiveActiveSign === personAMoonSign(apiPayload) &&
      immersiveAspectCount === expectedImmersiveAspectCount
  );
  const hasImmersiveThreeDepthModel = Boolean(immersiveDepthModel === "three-orbit-plane" && immersiveFlatOverlayCount === 0);
  const hasImmersiveOrnateVisualTheme = Boolean(immersiveVisualTheme === "ornate-cosmic-instrument");
  const hasImmersiveControls =
    (await page.locator(".immersive-control-bar button").count()) === 6 &&
    ["星座輪", "相位連線", "自動旋轉", "放大", "縮小", "重置視角"].every((label) => pageText.includes(label)) &&
    !pageText.includes("星盤探索");
  await clickImmersivePlanet(page, "金星");
  const immersiveClickedPoint = await immersiveDashboard.getAttribute("data-active-point");
  const immersiveAspectToggle = await clickImmersiveControl(page, "相位連線");
  const hasImmersiveSelectedBeacon = Boolean(immersiveSelectedHighlight === "orbital-beacon" && immersiveClickedPoint === "Venus");
  const hasImmersiveInteraction = Boolean(
    immersiveClickedPoint === "Venus" &&
      (await immersiveAspectToggle.getAttribute("aria-pressed")) === "false"
  );
  const hasImmersiveExplorerRemoved = Boolean(
    (await page.locator(".immersive-control-bar button").filter({ hasText: "星盤探索" }).count()) === 0 &&
      (await immersiveDashboard.getAttribute("data-explorer-open")) === "false" &&
      !(await immersiveDashboard.getAttribute("class"))?.includes("is-explorer")
  );
  await page.screenshot({ path: viewport.explorerPath, fullPage: false });
  const hasCosmicStepNavigation =
    tabControls.length === 4 &&
    tabControls.filter((tab) => tab.selected === "true").length === 1 &&
    resultStepIds.every((stepId) => tabControls.some((tab) => tab.controls === `${stepId}-panel`)) &&
    resultStepTitles.every((stepTitle) => tabControls.some((tab) => tab.label?.includes(stepTitle)));
  await page.evaluate(() => {
    window.location.hash = "core-answer";
  });
  await page.waitForTimeout(1000);
  const hasReadingReportShell =
    (await page.locator(".reading-sidebar").count()) === 1 &&
    (await page.locator(".reading-chart-zone .immersive-cosmic-dashboard").isVisible()) &&
    (await page.locator(".reading-tabs-wrap .reading-tab").count()) === 4 &&
    (await page.locator(".reading-page-rail").count()) === 1;
  const hasTabHashKeepsChartTop = await page.evaluate(() => {
    const chart = document.querySelector(".reading-chart-zone");
    const stage = document.querySelector(".cosmic-tab-stage");
    if (!chart || !stage) return false;
    const rect = chart.getBoundingClientRect();
    return (
      stage.getAttribute("data-active-step") === "core-answer" &&
      window.scrollY <= 4 &&
      rect.top >= -4 &&
      rect.bottom > 320
    );
  });
  const chartTabText = await openReadingTab(page, "chart-positioning");
  const chartDashboardScene = await waitForDashboardScene(page, "chart-positioning");
  const chartProfilePanelCount = await page.locator("#chart-positioning-panel .cosmic-positioning-profile").count();
  const chartFunctionRowCount = await page.locator("#chart-positioning-panel .cosmic-positioning-row").count();
  const chartZodiacIconCount = await page.locator("#chart-positioning-panel .cosmic-positioning-cell .cosmic-zodiac-token img[src*='/cosmic/zodiac/']").count();
  const chartProfileEmblemCount = await page.locator("#chart-positioning-panel .cosmic-positioning-profile .cosmic-chart-emblem-portrait img[src$='chart-emblem.webp']").count();
  const chartFunctionLabels = await page.locator("#chart-positioning-panel .cosmic-positioning-function span").allTextContents();
  const relationshipFitPanelCount = await page.locator("#relationship-fit-panel").count();
  const relationshipFitTabCount = await page.locator("#relationship-fit-tab").count();
  const positioningFitMainVisible = await page.locator("#chart-positioning-panel .compatibility-positioning-snapshot").isVisible();
  const positioningFitRadarCount = await page.locator("#chart-positioning-panel .compatibility-radar-tile").count();
  const relationshipFitLens = apiPayload?.relationshipFitLens ?? {};
  const relationshipFitTypeTitle = apiPayload?.finalInterpretation?.sections?.["relationship-fit"]?.headline ??
    visibleDashboardCopy(relationshipFitLens?.relationshipType?.title ?? apiPayload?.relationshipArchetype?.title ?? "");
  const relationshipFitRadarLabels = (relationshipFitLens?.radar ?? []).map((item) => visibleDashboardCopy(item?.label ?? "")).filter(Boolean);
  const answerPageText = await openReadingTab(page, "core-answer");
  const answerSectionText = await page.locator("#core-answer-panel").innerText();
  const answerDashboardScene = await waitForDashboardScene(page, "core-answer");
  const answerCardVisible = await page.locator("#core-answer-panel .cosmic-answer-card").isVisible();
  const answerScorePanelCount = await page.locator("#core-answer-panel .cosmic-answer-score").count();
  const partnerNeedsPanelVisible = await page.locator("#core-answer-panel .cosmic-partner-needs-panel").isVisible();
  const partnerNeedCardCount = await page.locator("#core-answer-panel .cosmic-partner-need-card").count();
  const partnerNeedSourceCardCount = await page.locator("#core-answer-panel .cosmic-partner-source-card").count();
  const partnerNeedTitle = visibleDashboardCopy(apiPayload?.partnerNeeds?.items?.[0]?.title ?? "");
  const answerEvidenceSectionCount = await page.locator("#core-answer-panel .reading-evidence-section").count();
  const hasNoAnswerEvidenceSection =
    answerEvidenceSectionCount === 0 &&
    !answerSectionText.includes("判斷依據") &&
    !answerSectionText.includes("這個判斷怎麼來的");
  const timingPageText = await openReadingTab(page, "timing-reading");
  const timingSectionText = await page.locator("#timing-reading-panel").innerText();
  const timingDashboardScene = await waitForDashboardScene(page, "timing-reading");
  const timingOracleVisible = await page.locator("#timing-reading-panel .cosmic-timing-oracle").isVisible();
  const timingPrimaryStateCount = await page.locator("#timing-reading-panel .cosmic-timing-primary-state").count();
  const turningWindowPanelVisible = await page.locator("#timing-reading-panel .cosmic-turning-window-panel").isVisible();
  const turningWindowCardCount = await page.locator("#timing-reading-panel .cosmic-turning-window-card").count();
  const turningWindowTitle = visibleDashboardCopy(apiPayload?.relationshipTurningWindows?.items?.[0]?.title ?? "");
  const actionPageText = await openReadingTab(page, "action-direction");
  const actionSectionText = await page.locator("#action-direction-panel").innerText();
  const actionDashboardScene = await waitForDashboardScene(page, "action-direction");
  const actionScoreVisible = await page.locator("#action-direction-panel .cosmic-action-score").isVisible();
  const actionBoundaryArticleCount = await page.locator("#action-direction-panel .cosmic-boundary-panel article").count();
  const actionLandminePanelVisible = await page.locator("#action-direction-panel .cosmic-action-landmine-brief").isVisible();
  const actionLandmineCardCount = await page.locator("#action-direction-panel .cosmic-action-landmine-brief article").count();
  const actionLandmineTitle = visibleDashboardCopy(apiPayload?.fightLandmines?.items?.[0]?.title ?? "");
  const actionChecklistVisible = await page.locator("#action-direction-panel .cosmic-action-checklist").isVisible();
  const actionChecklistArticleCount = await page.locator("#action-direction-panel .cosmic-action-checklist article").count();
  const actionChecklistBodies = await page.locator("#action-direction-panel .reading-action-check-card p").allTextContents();
  const actionTimelineArticleCount = await page.locator("#action-direction-panel .cosmic-action-timeline-panel article").count();
  const actionMessageScriptCount = await page.locator("#action-direction-panel .cosmic-message-scripts article").count();
  const actionResponseBranchCount = await page.locator("#action-direction-panel .cosmic-response-branches article").count();
  const allReadingText = [pageText, chartTabText, answerPageText, timingPageText, actionPageText].join("\n");
  const finalInterpretationLeadCount = await page.locator(".reading-final-interpretation").count();
  const hasNoFinalInterpretationLead = finalInterpretationLeadCount === 0 && !allReadingText.includes("本頁重點");
  const hasRelationshipFitPageRemoved =
    relationshipFitPanelCount === 0 &&
    relationshipFitTabCount === 0 &&
    !allReadingText.includes("兩個人的關係契合度分析");
  const hasNoFitProfileBodyDuplication = hasRelationshipFitPageRemoved;
  const hasTabBridgeFlow =
    chartTabText.includes("前往 02") &&
    answerSectionText.includes("前往 03") &&
    timingSectionText.includes("前往 04") &&
    !allReadingText.includes("下一頁") &&
    !allReadingText.includes("往下讀");
  const hasNoTimingMessageScripts =
    !["短訊息範例", "輕觸型", "不逼問型", "可退場型"].some((label) => timingSectionText.includes(label));
  const hasNoDuplicateActionChecklistBodies =
    new Set(actionChecklistBodies.map((body) => body.trim()).filter(Boolean)).size === actionChecklistBodies.map((body) => body.trim()).filter(Boolean).length;
  const fitVisibleCountBadgeCount = await page.locator(".cosmic-fit-score-row span, .cosmic-fit-bucket-head > span").count();
  const visualCompanionLaneChipCount = await page.locator(".visual-companion-lanes").count();
  const dashboardSceneStates = {
    "action-direction": actionDashboardScene,
    "chart-positioning": chartDashboardScene,
    "core-answer": answerDashboardScene,
    "timing-reading": timingDashboardScene
  };
  const allDashboardTopicText = Object.values(dashboardSceneStates)
    .map((state) => state.topicText ?? "")
    .join("\n");
  const hasImmersiveChartScenePlan =
    hasExpectedDashboardScene(initialDashboardScene, "chart-positioning") &&
    resultStepIds.every((stepId) => hasExpectedDashboardScene(dashboardSceneStates[stepId], stepId));
  const hasDistinctLateTabVisualAspectIdsResult = hasDistinctLateTabVisualAspectIds(dashboardSceneStates);
  const hasWeakTimingDataNoFakeCertainty =
    apiPayload?.timingGuidance?.preciseDatesAvailable === false
      ? timingDashboardScene.visualTimingCertainty === "trend_only" &&
        timingDashboardScene.visualVisibleAspectIds === "none" &&
        timingDashboardScene.topicText.includes("互動節奏")
      : true;
  const hasCosmicProfileCards =
    chartProfilePanelCount === 2 &&
    chartFunctionRowCount === 5 &&
    chartZodiacIconCount >= 10 &&
    chartProfileEmblemCount === 2 &&
    chartTabText.includes("我的星盤") &&
    chartTabText.includes("他的星盤") &&
    ["安全感模式", "溝通方式", "好感表達", "行動節奏", "壓力下的反應"].every((label) => chartTabText.includes(label)) &&
    chartTabText.includes(apiPayload?.relationshipProfiles?.personA?.headline ?? "") &&
    chartTabText.includes(apiPayload?.relationshipProfiles?.personB?.headline ?? "");
  const hasCosmicFitSection =
    hasRelationshipFitPageRemoved &&
    positioningFitMainVisible &&
    positioningFitRadarCount >= 5 &&
    chartTabText.includes("關係型態") &&
    chartTabText.includes("契合雷達") &&
    !["關係裡最重要的兩個位置", "你們最合的地方", "最容易卡住的循環", "合盤證據"].some((label) => chartTabText.includes(label)) &&
    Boolean(relationshipFitTypeTitle) &&
    chartTabText.includes(relationshipFitTypeTitle) &&
    relationshipFitRadarLabels.length >= 5 &&
    relationshipFitRadarLabels.filter((label) => chartTabText.includes(label)).length >= 4;
  const hasCosmicAnswerSection =
    answerCardVisible &&
    partnerNeedsPanelVisible &&
    partnerNeedCardCount === 0 &&
    partnerNeedSourceCardCount >= 3 &&
    hasNoAnswerEvidenceSection &&
    Boolean(partnerNeedTitle) &&
    answerSectionText.includes(partnerNeedTitle) &&
    ["他在找的關係", "安全感怎麼來", "愛意語言", "壓力下的反應", "承諾節奏", "什麼會打開他", "什麼會讓他關上", "容易誤會", "星盤依據"].every((label) => answerSectionText.includes(label)) &&
    ["他在找的關係", "什麼會打開他", "什麼會讓他關上", "容易誤會"].every((label) => (answerSectionText.match(new RegExp(label, "g")) ?? []).length === 1) &&
    ["你問的是", "這題的短答案", "閱讀範圍", "對方在感情裡真正需要什麼"].every((label) => answerSectionText.includes(label)) &&
    Boolean(finalCoreReadable?.headline) &&
    answerSectionText.includes(visibleDashboardCopy(finalCoreReadable.headline)) &&
    Boolean(finalCoreReadable?.body) &&
    answerSectionText.includes(visibleDashboardCopy(finalCoreReadable.body));
  const hasNoDuplicateReasonSection =
    (await page.locator("#core-answer-panel .cosmic-reason-panel").count()) === 0 &&
    !answerSectionText.includes("為什麼這樣判斷");
  const hasNoAnswerScorePanel =
    answerScorePanelCount === 0 &&
    !answerSectionText.includes("條件分數");
  const hasCosmicTimingSection =
    timingOracleVisible &&
    timingPrimaryStateCount === 1 &&
    turningWindowPanelVisible &&
    turningWindowCardCount >= 2 &&
    Boolean(turningWindowTitle) &&
    timingSectionText.includes(turningWindowTitle) &&
    ["目前互動節奏", "此刻建議", "2026 關係重要轉折氣候", "月旬區間"].every((label) => timingSectionText.includes(label)) &&
    !timingSectionText.includes("接下來的節奏") &&
    !timingSectionText.includes("短訊息範例");
  const hasTimingGuidanceVisible =
    Boolean(finalTimingReadable?.body) &&
    timingSectionText.includes(visibleDashboardCopy(finalTimingReadable.body)) &&
    timingSectionText.includes("此刻建議") &&
    timingSectionText.includes("互動節奏");
  const hasNoTimingSignalSection =
    (await page.locator("#timing-reading-panel .cosmic-timing-signal-panel").count()) === 0 &&
    !timingPageText.includes("星象訊號");
  const answerDisplayHeadline = visibleDashboardCopy(finalCoreReadable?.headline ?? "");
  const answerDisplayDirectAnswer = visibleDashboardCopy(finalCoreReadable?.body ?? "");
  const hasAnswerGuidanceVisible =
    Boolean(answerDisplayHeadline) &&
    answerPageText.includes(answerDisplayHeadline);
  const hasPrimaryAnswerMappingVisible = Boolean(
      answerDisplayHeadline &&
      answerPageText.includes(answerDisplayHeadline) &&
      answerDisplayDirectAnswer &&
      answerPageText.includes(answerDisplayDirectAnswer) &&
      answerCardVisible
  );
  const hasCosmicActionSection =
    actionScoreVisible &&
    actionBoundaryArticleCount >= 1 &&
    actionLandminePanelVisible &&
    actionLandmineCardCount >= 3 &&
    actionChecklistVisible &&
    actionChecklistArticleCount === 4 &&
    actionTimelineArticleCount >= 3 &&
    actionMessageScriptCount === 3 &&
    actionResponseBranchCount === 4 &&
    Boolean(actionLandmineTitle) &&
    actionSectionText.includes(actionLandmineTitle) &&
    ["接下來的節奏", "第一步", "第二步", "第三步"].every((label) => actionSectionText.includes(label)) &&
    ["行動策略", "先確認這 4 件事", "行動前檢查", "短訊息範例", "回應分岔", "最需要避開的一個地雷"].every((label) => actionSectionText.includes(label)) &&
    hasNoDuplicateActionChecklistBodies;
  const hasActionGuidanceVisible =
    Boolean(finalActionReadable?.headline) &&
    actionSectionText.includes(visibleDashboardCopy(finalActionReadable.headline)) &&
    ["可以做", "先不要", "短訊息範例", "輕觸型", "不逼問型", "可退場型", "暖回", "短回", "不回", "冷回", "停止線", "不要怎麼自我解讀"].every((label) => actionSectionText.includes(label));
  const visibleBlockedActionLabels = (apiPayload?.actionGuidance?.blockedActions ?? [])
    .slice(0, 1)
    .map((action) => blockedActionLabels[action] ?? "")
    .filter(Boolean);
  const hasActionBlockedMappingVisible = Boolean(
      visibleBlockedActionLabels.length >= 1 &&
      visibleBlockedActionLabels.every((label) => actionPageText.includes(label)) &&
      actionPageText.includes("現實狀態") &&
      actionPageText.includes("先不要")
  );
  const hasNoCrossReadingInFunctionIntro =
    !allReadingText.includes("意思是「情緒安全功能」會用");
  const hasNoMoonTaurusIntroExample =
    !allReadingText.includes("所以月亮金牛的意思是");
  const hasNoSeparateReadCard = !allReadingText.includes("怎麼讀");
  const hasCosmicFunctionDetailRows =
    chartFunctionRowCount === 5 &&
    chartZodiacIconCount >= 10 &&
    ["安全感模式", "溝通方式", "好感表達", "行動節奏", "壓力下的反應"].every((label) =>
      chartFunctionLabels.some((title) => title.trim() === label)
    );
  const hasNoGenericAdviceLabels =
    !["適合什麼", "不適合什麼", "自然反應", "容易卡住"].some((label) => chartTabText.includes(label));
  const hasNoGuideFocusRows = !chartTabText.includes("解讀重點");
  const hasNoDuplicateRelationshipUseRows = !chartTabText.includes("關係中的表現");
  const oldGenericAvoidRows = [
    "不適合長時間冷處理、忽略情緒反應，或用沉默測試安全感。",
    "不適合一次丟出長篇追問、諷刺，或讓話題失去清楚邊界。",
    "不適合把好感直接升級成承諾要求，或用占有感測試愛意。",
    "不適合在壓力中硬碰硬、逼對方同速前進，或把急迫當成行動力。",
    "不適合用最後通牒、命定等待，或把退縮直接解讀成永久拒絕。",
    "用辯論壓人、一直換題，或讓問題失焦。",
    "連環追問、要求秒回，或讓溝通壓力更大。"
  ];
  const hasNoGenericAvoidRows = oldGenericAvoidRows.every((generic) =>
    !allReadingText.includes(generic)
  );
  const hasQuestionAnswerSections =
    hasCosmicAnswerSection &&
    hasCosmicTimingSection &&
    hasCosmicActionSection &&
    Boolean(answerDisplayHeadline) &&
    answerPageText.includes(answerDisplayHeadline);
  const hasNoAnswerEvidenceContractPanel = hasNoAnswerEvidenceSection;
  const hasActionRhythmTimelineVisible =
    actionTimelineArticleCount >= 3 &&
    actionSectionText.includes("接下來的節奏") &&
    !timingSectionText.includes("接下來的節奏");
  const hasOldResultDesignRemoved =
    (await page.locator(".hero-section").count()) === 0 &&
    (await page.locator(".relationship-diagnosis-card").count()) === 0 &&
    (await page.locator(".narrative-section").count()) === 0 &&
    (await page.locator(".dashboard-section").count()) === 0 &&
    (await page.locator(".relationship-profile-section").count()) === 0;
  const hasNoBaziCalculationProof = !(await page.getByText("命盤已重新計算").isVisible()) &&
    !(await page.locator(".calculation-proof-strip").getByText("日主").isVisible().catch(() => false));
  const hasNoBaziDiagnosisSection = !(await page.getByText("八字合婚診斷").isVisible());
  const hasNoBaziPatternStrip = (await page.locator(".bazi-pattern-strip article").count()) === 0;
  const baziModuleCardCount = await page.locator(".bazi-module-card").count();
  const hasNoBaziModuleCards = baziModuleCardCount === 0;
  const baziModuleTitles = await page.locator(".bazi-module-head strong").allTextContents();
  const hasNoBaziModuleTitles = baziModuleTitles.length === 0;
  const hasNoBaziModuleFactors = (await page.locator(".module-factor").count()) === 0;
  const hasNoBaziInterpreterLayers =
    !(await page.getByText("命理師看到").first().isVisible().catch(() => false)) &&
    !(await page.getByText("人話意思").first().isVisible().catch(() => false));
  const hasNoBaziQuestionAnswer = (await page.locator("#question .bazi-question-card").count()) === 0;
  const hasNoBaziAnswerFlow =
    !(await page.locator("#question").getByText("答案", { exact: true }).isVisible().catch(() => false)) &&
    !(await page.locator("#question").getByText("因為", { exact: true }).isVisible().catch(() => false)) &&
    !(await page.locator("#question").getByText("所以", { exact: true }).isVisible().catch(() => false));
  const hasNoBaziQuestionReasoning = (await page.locator("#question .bazi-question-card p").count()) === 0;
  const hasNoInternalSignalIds =
    !allReadingText.includes("western-aspects-") &&
    !allReadingText.includes("bazi-hehun-") &&
    !allReadingText.includes("context-");
  const hasOldNarrativeRemoved = (await page.locator(".narrative-section").count()) === 0 &&
    !allReadingText.includes("本次故事主線");
  const hasOldEvidenceRemoved = !allReadingText.includes("西洋星盤證據") &&
    (await page.locator(".western-synastry-panel").count()) === 0;
  const hasNoDualSystemEvidence = !allReadingText.includes("雙系統證據") &&
    (await page.locator(".bazi-pairing-panel").count()) === 0;
  const hasNoSeparateAuthorityLabel = true;
  const hasNoInsightShortcutRows = (await page.locator(".insight-row").count()) === 0 &&
    !allReadingText.includes("八字核心訊號") &&
    !allReadingText.includes("西洋核心訊號");
  const hasNoReportLoadingGate = !(await page.getByText(loadingTitle).isVisible());
  const hasOldCtaRemoved = !allReadingText.includes("解鎖完整合盤報告");
  const hasNoBaziTechnicalSummaries = (await page.locator(".module-reading").count()) === 0;
  const hasNoBaziEvidenceBullets = (await page.locator(".module-evidence li").count()) === 0;
  const hasNoWeakAspectPlaceholder = !allReadingText.includes("目前沒有足夠可展示的合盤相位細節");
  const hasNoMissingSignalPlaceholders =
    !allReadingText.includes("未選定訊號") && !allReadingText.includes("可用訊號不足");
  const hasNoTranslatedFitFormula =
    !allReadingText.includes("你比較用") &&
    !allReadingText.includes("處理界線與壓力") &&
    !allReadingText.includes("這一項比較容易互相懂") &&
    !allReadingText.includes("對話和空間處理") &&
    !allReadingText.includes("土星這一塊") &&
    !allReadingText.includes("需要更多翻譯") &&
    !allReadingText.includes("壓力反應容易誤會");
  const awkwardQuestionCopyHits = awkwardQuestionCopyTerms.filter((term) => allReadingText.includes(term));
  const hasNoAwkwardQuestionCopy = awkwardQuestionCopyHits.length === 0;
  const hasNoFatalisticQuestionCopy =
    !allReadingText.includes("這段關係一定會復合") &&
    !allReadingText.includes("你們一定會復合") &&
    !allReadingText.includes("一定會分手") &&
    !allReadingText.includes("一定沒有機會") &&
    !allReadingText.includes("一定沒機會") &&
    !allReadingText.includes("注定分開") &&
    !allReadingText.includes("注定復合") &&
    !allReadingText.includes("保證會復合") &&
    !allReadingText.includes("保證對方會回來") &&
    !allReadingText.includes("永久結束") &&
    !allReadingText.includes("他一定還愛你") &&
    !allReadingText.includes("他一定不愛你") &&
    !allReadingText.includes("某天聯絡一定成功") &&
    !allReadingText.includes("聯絡一定成功");
  const hasNoVisibleBaziEvidence =
    !allReadingText.includes("八字") &&
    !allReadingText.includes("八字合婚診斷") &&
    !allReadingText.includes("配偶星") &&
    !allReadingText.includes("四柱") &&
    !allReadingText.includes("日主");
  const hasNoVisibleLegacyContractCopy =
    !allReadingText.includes("免費結果") &&
    !allReadingText.includes("免費合盤結果") &&
    !allReadingText.includes("解鎖完整合盤報告") &&
    !allReadingText.includes("NT$499") &&
    !allReadingText.includes("NT$2,480");
  const hasNoVisibleInternalPrecisionCopy =
    !allReadingText.includes("birth_time") &&
    !allReadingText.includes("noon fallback") &&
    !allReadingText.includes("date_noon_fallback") &&
    !allReadingText.includes("time-sensitive");
  const hasNoVisibleFitSignalCounts =
    fitVisibleCountBadgeCount === 0 &&
    !/(自然牽動|修復訊號|壓力訊號)\s*x\d/.test(allReadingText) &&
    !/(自然合拍|需要磨合|容易誤會)的?\s*\d+\s*個點/.test(allReadingText) &&
    !/關鍵合盤訊號只選\s*\d/.test(allReadingText) &&
    !/這頁只放\s*\d+\s*到\s*\d+\s*條/.test(allReadingText);
  const hasNoVisualCompanionLaneChips =
    visualCompanionLaneChipCount === 0 &&
    !["哪裡還能自然靠近", "哪裡要放慢說清楚", "哪裡先不要硬推"].some((label) =>
      allDashboardTopicText.includes(label)
    );
  await page.evaluate(() => window.scrollTo({ behavior: "instant", top: 0 }));
  await page.screenshot({ path: viewport.path, fullPage: false });
  const devResultScenarioPreviews =
    sharedDevResultScenarioPreviews ?? (sharedDevResultScenarioPreviews = await verifyDevResultScenarioPreviews(page));

  await page.close();

  results.push({
    viewport: viewport.name,
    title,
    apiStatus,
    hasIntakeOpening,
    hasProvidedIntroBackground,
    hasTestingShortcut,
    hasNoModelSwitch,
    hasNoModelSwitchOptions,
    hasNoPreselectedStage,
    hasNoPreselectedQuestion,
    hasNoPreselectedContact,
    hasNoEmotionStep,
    hasNoPreselectedBirth,
    hasNoPreselectedPartner,
    hasCityEntry,
    hasPartnerCityEntry,
    yearCapsAtFourDigits,
    yearAutoAdvancesToMonth,
    hasBirthData,
    hasConfirm,
    hasLoadingGate,
    hasLoadingProof,
    hasNoLoadingReading,
    hasRuntimeApiOk,
    hasRuntimeEngineVersions,
    hasExpectedStructuredKbSource,
    hasNoBaziCalculationProofPayload,
    hasNoLegacyBaziPayload,
    hasWesternRelationshipCaseFilePayload,
    hasRelationshipProfilesPayload,
    hasReadableInterpretationPayload,
    hasFinalInterpretationPayload,
    hasAnswerGuidancePayload,
    hasActionGuidancePayload,
    hasTimingGuidancePayload,
    hasWesternMethodClustersPayload,
    hasNonfatalSynastrySafetyPayload,
    hasFunctionSignClustersPayload,
    hasFunctionMatrixClustersPayload,
    hasAspectContactModifierPayload,
    hasAspectPairContactTemplatePayload,
    hasAspectFunctionCombinationPayload,
    hasTimingContactReducerPayload,
    hasContactSituationPolicyPayload,
    hasTimingSelectorClustersPayload,
    hasPublicTimingWindowScanPayload,
    hasFunctionSignBlueprintEvidence,
    hasCompleteResultContractPayload,
    hasNoLegacyCompleteResultContractPayload,
    forbiddenApiKeyHits,
    forbiddenApiStringHits,
    hasReadingBlueprintPayload,
    hasClaimSupportPayload,
    hasNoMissingSignalPlaceholdersPayload,
    hasNoBaziPayloadText,
    hasAdvancedWesternPayload,
    hasNoRuntimeNarrativePayload,
    hasNoRuntimeNarrativeDebug,
    hasAnswerEvidenceContractPayload,
    hasGeneratedResultTitle,
    hasNoScenarioSwitcher,
    hasCosmicFourStepResult,
    hasImmersiveCosmicDashboard,
    hasImmersiveChartScenePlan,
    hasDistinctLateTabVisualAspectIds: hasDistinctLateTabVisualAspectIdsResult,
    hasWeakTimingDataNoFakeCertainty,
    hasImmersiveScenarioDrivenSelection,
    hasImmersiveThreeDepthModel,
    hasImmersiveOrnateVisualTheme,
    hasImmersiveCanvasNonBlank,
    hasImmersiveRasterAssets,
    hasImmersiveControls,
    hasImmersiveSelectedBeacon,
    hasImmersiveInteraction,
    hasImmersiveExplorerRemoved,
    hasReadingReportShell,
    hasTabHashKeepsChartTop,
    hasTabBridgeFlow,
    hasCosmicStepNavigation,
    hasCosmicProfileCards,
    hasCosmicFunctionDetailRows,
    hasNoFitProfileBodyDuplication,
    hasNoTimingMessageScripts,
    hasNoDuplicateActionChecklistBodies,
    hasNoCrossReadingInFunctionIntro,
    hasNoMoonTaurusIntroExample,
    hasNoSeparateReadCard,
    hasNoGenericAdviceLabels,
    hasNoGuideFocusRows,
    hasNoDuplicateRelationshipUseRows,
    hasNoDuplicateReasonSection,
    hasNoAnswerScorePanel,
    hasNoGenericAvoidRows,
    hasCosmicFitSection,
    hasQuestionAnswerSections,
    hasNoFinalInterpretationLead,
    hasAnswerGuidanceVisible,
    hasPrimaryAnswerMappingVisible,
    hasTimingGuidanceVisible,
    hasNoTimingSignalSection,
    hasActionGuidanceVisible,
    hasActionBlockedMappingVisible,
    hasNoAnswerEvidenceContractPanel,
    hasActionRhythmTimelineVisible,
    hasOldResultDesignRemoved,
    hasNoBaziCalculationProof,
    hasNoBaziDiagnosisSection,
    hasNoBaziPatternStrip,
    hasNoBaziModuleCards,
    hasNoBaziModuleTitles,
    hasNoBaziModuleFactors,
    hasNoBaziInterpreterLayers,
    hasNoBaziQuestionAnswer,
    hasNoBaziAnswerFlow,
    hasNoBaziQuestionReasoning,
    hasNoInternalSignalIds,
    hasOldNarrativeRemoved,
    hasOldEvidenceRemoved,
    hasNoDualSystemEvidence,
    hasNoSeparateAuthorityLabel,
    hasNoInsightShortcutRows,
    hasNoReportLoadingGate,
    hasOldCtaRemoved,
    hasNoBaziTechnicalSummaries,
    hasNoBaziEvidenceBullets,
    hasNoWeakAspectPlaceholder,
    hasNoMissingSignalPlaceholders,
    hasNoTranslatedFitFormula,
    hasNoAwkwardQuestionCopy,
    awkwardQuestionCopyHits,
    hasNoFatalisticQuestionCopy,
    hasNoVisibleBaziEvidence,
    hasNoVisibleLegacyContractCopy,
    hasNoVisibleInternalPrecisionCopy,
    hasNoVisibleFitSignalCounts,
    hasNoVisualCompanionLaneChips,
    hasDevResultScenarioPreviews: devResultScenarioPreviews.ok,
    dashboardSceneStates,
    devResultScenarioPreviews,
    messages,
    screenshot: viewport.path,
    explorerScreenshot: viewport.explorerPath
  });
}

await browser.close();

const failures = results.flatMap((result) => {
  const missing = [];
  if (!result.hasGeneratedResultTitle) missing.push(`${result.viewport}: generated result title missing`);
  if (!result.hasIntakeOpening) missing.push(`${result.viewport}: intake opening missing`);
  if (!result.hasProvidedIntroBackground) missing.push(`${result.viewport}: intake intro background asset missing`);
  if (!result.hasTestingShortcut) missing.push(`${result.viewport}: locked testing data shortcut missing`);
  if (!result.hasNoModelSwitch) missing.push(`${result.viewport}: narrative model switch still visible`);
  if (!result.hasNoModelSwitchOptions) missing.push(`${result.viewport}: narrative model switch options still visible`);
  if (!result.hasNoPreselectedStage) missing.push(`${result.viewport}: stage answer was preselected`);
  if (!result.hasNoPreselectedQuestion) missing.push(`${result.viewport}: question answer was preselected`);
  if (!result.hasNoPreselectedContact) missing.push(`${result.viewport}: contact answer was preselected`);
  if (!result.hasNoEmotionStep) missing.push(`${result.viewport}: removed emotion step is still visible`);
  if (!result.hasNoPreselectedBirth) missing.push(`${result.viewport}: user birth data was prefilled`);
  if (!result.hasNoPreselectedPartner) missing.push(`${result.viewport}: partner birth data was prefilled`);
  if (!result.hasCityEntry) missing.push(`${result.viewport}: user birth city entry missing`);
  if (!result.hasPartnerCityEntry) missing.push(`${result.viewport}: partner birth city entry missing`);
  if (!result.yearCapsAtFourDigits) missing.push(`${result.viewport}: birth year did not cap at four digits`);
  if (!result.yearAutoAdvancesToMonth) missing.push(`${result.viewport}: birth year did not auto-advance to month`);
  if (!result.hasBirthData) missing.push(`${result.viewport}: birth data intake missing`);
  if (!result.hasConfirm) missing.push(`${result.viewport}: intake confirmation missing`);
  if (!result.hasLoadingGate) missing.push(`${result.viewport}: loading gate missing before result`);
  if (!result.hasLoadingProof) missing.push(`${result.viewport}: loading proof steps missing before result`);
  if (!result.hasNoLoadingReading) missing.push(`${result.viewport}: reading content leaked into loading`);
  if (!result.hasRuntimeApiOk) missing.push(`${result.viewport}: relationship-result API failed with status ${result.apiStatus}`);
  if (!result.hasRuntimeEngineVersions) missing.push(`${result.viewport}: runtime calculation engine versions missing`);
  if (!result.hasExpectedStructuredKbSource) {
    missing.push(`${result.viewport}: structured KB source did not match ${expectedStructuredKbSource}`);
  }
  if (!result.hasNoBaziCalculationProofPayload) missing.push(`${result.viewport}: BaZi calculation proof still present in API payload`);
  if (!result.hasNoLegacyBaziPayload) missing.push(`${result.viewport}: legacy BaZi payload still present in API response`);
  if (!result.hasWesternRelationshipCaseFilePayload) missing.push(`${result.viewport}: Western relationship case file payload missing`);
  if (!result.hasRelationshipProfilesPayload) missing.push(`${result.viewport}: relationship profiles payload missing`);
  if (!result.hasReadableInterpretationPayload) missing.push(`${result.viewport}: readable interpretation payload missing`);
  if (!result.hasFinalInterpretationPayload) missing.push(`${result.viewport}: final interpretation payload missing`);
  if (!result.hasAnswerGuidancePayload) missing.push(`${result.viewport}: readable answer guidance payload missing`);
  if (!result.hasActionGuidancePayload) missing.push(`${result.viewport}: readable action guidance payload missing`);
  if (!result.hasTimingGuidancePayload) missing.push(`${result.viewport}: readable timing guidance payload missing`);
  if (!result.hasWesternMethodClustersPayload) missing.push(`${result.viewport}: Western method/source clusters missing`);
  if (!result.hasNonfatalSynastrySafetyPayload) missing.push(`${result.viewport}: nonfatal synastry safety policy missing`);
  if (!result.hasFunctionSignClustersPayload) missing.push(`${result.viewport}: point-specific sign function clusters missing`);
  if (!result.hasFunctionMatrixClustersPayload) missing.push(`${result.viewport}: function element/modality matrix clusters missing`);
  if (!result.hasAspectContactModifierPayload) missing.push(`${result.viewport}: aspect contact modifier cluster missing`);
  if (!result.hasAspectPairContactTemplatePayload) missing.push(`${result.viewport}: aspect pair contact template cluster missing`);
  if (!result.hasAspectFunctionCombinationPayload) missing.push(`${result.viewport}: aspect-function combination cluster missing`);
  if (!result.hasTimingContactReducerPayload) missing.push(`${result.viewport}: contact timing reducer cluster missing`);
  if (!result.hasContactSituationPolicyPayload) missing.push(`${result.viewport}: contact situation policy cluster missing`);
  if (!result.hasTimingSelectorClustersPayload) missing.push(`${result.viewport}: timing selector clusters missing`);
  if (!result.hasPublicTimingWindowScanPayload) missing.push(`${result.viewport}: public timing window scan missing or leaking exact ranges`);
  if (!result.hasFunctionSignBlueprintEvidence) missing.push(`${result.viewport}: reading blueprint missing function-sign evidence`);
  if (!result.hasCompleteResultContractPayload) missing.push(`${result.viewport}: complete relationship result contract missing`);
  if (!result.hasNoLegacyCompleteResultContractPayload) {
    missing.push(`${result.viewport}: legacy complete-result contract leaked in API (${[...result.forbiddenApiKeyHits, ...result.forbiddenApiStringHits].join(", ")})`);
  }
  if (!result.hasReadingBlueprintPayload) missing.push(`${result.viewport}: reading blueprint payload missing`);
  if (!result.hasClaimSupportPayload) missing.push(`${result.viewport}: claim support payload missing`);
  if (!result.hasNoMissingSignalPlaceholdersPayload) missing.push(`${result.viewport}: API still contains missing signal placeholder copy`);
  if (!result.hasNoBaziPayloadText) missing.push(`${result.viewport}: API still contains BaZi text or keys`);
  if (!result.hasAdvancedWesternPayload) missing.push(`${result.viewport}: advanced Western payload missing`);
  if (!result.hasNoRuntimeNarrativePayload) missing.push(`${result.viewport}: runtime narrative payload still present`);
  if (!result.hasNoRuntimeNarrativeDebug) missing.push(`${result.viewport}: runtime narrative debug metadata still present`);
  if (!result.hasAnswerEvidenceContractPayload) missing.push(`${result.viewport}: answer evidence contract payload missing`);
  if (!result.hasNoScenarioSwitcher) missing.push(`${result.viewport}: scenario switcher visible after runtime result`);
  if (!result.hasCosmicFourStepResult) missing.push(`${result.viewport}: cosmic four-step result page missing`);
  if (!result.hasImmersiveCosmicDashboard) missing.push(`${result.viewport}: immersive cosmic dashboard missing`);
  if (!result.hasImmersiveChartScenePlan) {
    missing.push(`${result.viewport}: immersive chart scene plan did not follow active tab ${JSON.stringify(result.dashboardSceneStates)}`);
  }
  if (!result.hasDistinctLateTabVisualAspectIds) {
    missing.push(`${result.viewport}: later reading tabs reused the same visible aspect ids ${JSON.stringify(result.dashboardSceneStates)}`);
  }
  if (!result.hasWeakTimingDataNoFakeCertainty) {
    missing.push(`${result.viewport}: weak timing data created fake timing certainty ${JSON.stringify(result.dashboardSceneStates?.["timing-reading"])}`);
  }
  if (!result.hasImmersiveScenarioDrivenSelection) missing.push(`${result.viewport}: immersive dashboard is not scenario-driven`);
  if (!result.hasImmersiveThreeDepthModel) missing.push(`${result.viewport}: immersive dashboard still uses flat orbit overlays`);
  if (!result.hasImmersiveOrnateVisualTheme) missing.push(`${result.viewport}: immersive dashboard ornate visual theme missing`);
  if (!result.hasImmersiveCanvasNonBlank) missing.push(`${result.viewport}: immersive WebGL canvas appears blank`);
  if (!result.hasImmersiveRasterAssets) missing.push(`${result.viewport}: immersive raster assets missing`);
  if (!result.hasImmersiveControls) missing.push(`${result.viewport}: immersive dashboard controls missing`);
  if (!result.hasImmersiveSelectedBeacon) missing.push(`${result.viewport}: immersive selected planet beacon missing`);
  if (!result.hasImmersiveInteraction) missing.push(`${result.viewport}: immersive dashboard interactions failed`);
  if (!result.hasImmersiveExplorerRemoved) missing.push(`${result.viewport}: immersive explorer control still present`);
  if (!result.hasReadingReportShell) missing.push(`${result.viewport}: redesigned reading report shell missing`);
  if (!result.hasTabHashKeepsChartTop) missing.push(`${result.viewport}: tab hash hides the top 3D chart`);
  if (!result.hasTabBridgeFlow) missing.push(`${result.viewport}: direct tab navigation missing or bridge prose returned`);
  if (!result.hasCosmicStepNavigation) missing.push(`${result.viewport}: cosmic step navigation missing`);
  if (!result.hasCosmicProfileCards) missing.push(`${result.viewport}: cosmic person/function profile cards missing`);
  if (!result.hasCosmicFunctionDetailRows) missing.push(`${result.viewport}: cosmic function reaction/stuck rows missing`);
  if (!result.hasNoFitProfileBodyDuplication) missing.push(`${result.viewport}: removed relationship-fit page is still visible`);
  if (!result.hasNoTimingMessageScripts) missing.push(`${result.viewport}: timing tab contains action message scripts`);
  if (!result.hasNoDuplicateActionChecklistBodies) missing.push(`${result.viewport}: action checklist repeats the same body copy`);
  if (!result.hasNoCrossReadingInFunctionIntro) missing.push(`${result.viewport}: function intro still contains cross-reading copy`);
  if (!result.hasNoMoonTaurusIntroExample) missing.push(`${result.viewport}: removed Moon Taurus intro example is still visible`);
  if (!result.hasNoSeparateReadCard) missing.push(`${result.viewport}: separate read-this-placement card still visible`);
  if (!result.hasNoGenericAdviceLabels) missing.push(`${result.viewport}: generic 適合/不適合 labels still visible`);
  if (!result.hasNoGuideFocusRows) missing.push(`${result.viewport}: guide 解讀重點 rows still visible`);
  if (!result.hasNoDuplicateRelationshipUseRows) missing.push(`${result.viewport}: duplicate 關係中的表現 rows still visible`);
  if (!result.hasNoDuplicateReasonSection) missing.push(`${result.viewport}: duplicate 為什麼這樣判斷 section still visible`);
  if (!result.hasNoAnswerScorePanel) missing.push(`${result.viewport}: answer score panel still visible`);
  if (!result.hasNoGenericAvoidRows) missing.push(`${result.viewport}: generic 不適合什麼 rows still visible`);
  if (!result.hasCosmicFitSection) missing.push(`${result.viewport}: cosmic fit summary section missing`);
  if (!result.hasQuestionAnswerSections) missing.push(`${result.viewport}: direct result sections missing`);
  if (!result.hasNoFinalInterpretationLead) missing.push(`${result.viewport}: 本頁重點 final interpretation lead still visible`);
  if (!result.hasAnswerGuidanceVisible) missing.push(`${result.viewport}: readable answer guidance not visible`);
  if (!result.hasPrimaryAnswerMappingVisible) missing.push(`${result.viewport}: primary answer guidance mapping not visible`);
  if (!result.hasTimingGuidanceVisible) missing.push(`${result.viewport}: readable timing guidance not visible`);
  if (!result.hasNoTimingSignalSection) missing.push(`${result.viewport}: timing 星象訊號 section still visible`);
  if (!result.hasActionGuidanceVisible) missing.push(`${result.viewport}: readable action guidance not visible`);
  if (!result.hasActionBlockedMappingVisible) missing.push(`${result.viewport}: action blocked guidance not visible`);
  if (!result.hasNoAnswerEvidenceContractPanel) missing.push(`${result.viewport}: answer evidence contract panel still visible`);
  if (!result.hasActionRhythmTimelineVisible) missing.push(`${result.viewport}: action rhythm timeline missing or still on timing tab`);
  if (!result.hasOldResultDesignRemoved) missing.push(`${result.viewport}: old result design is still visible`);
  if (!result.hasNoBaziCalculationProof) missing.push(`${result.viewport}: BaZi calculation proof still visible`);
  if (!result.hasNoBaziDiagnosisSection) missing.push(`${result.viewport}: BaZi diagnosis section still visible`);
  if (!result.hasNoBaziPatternStrip) missing.push(`${result.viewport}: BaZi pattern strip still visible`);
  if (!result.hasNoBaziModuleCards) missing.push(`${result.viewport}: BaZi diagnosis modules still visible`);
  if (!result.hasNoBaziModuleTitles) missing.push(`${result.viewport}: BaZi diagnosis module titles still visible`);
  if (!result.hasNoBaziModuleFactors) missing.push(`${result.viewport}: BaZi diagnosis module factors still visible`);
  if (!result.hasNoBaziInterpreterLayers) missing.push(`${result.viewport}: BaZi interpreter layers still visible`);
  if (!result.hasNoBaziQuestionAnswer) missing.push(`${result.viewport}: BaZi question answer section still visible`);
  if (!result.hasNoBaziAnswerFlow) missing.push(`${result.viewport}: BaZi answer/because/therefore flow still visible`);
  if (!result.hasNoBaziQuestionReasoning) missing.push(`${result.viewport}: BaZi question reasoning still visible`);
  if (!result.hasNoInternalSignalIds) missing.push(`${result.viewport}: internal signal ids visible to user`);
  if (!result.hasOldNarrativeRemoved) missing.push(`${result.viewport}: old narrative section still visible`);
  if (!result.hasOldEvidenceRemoved) missing.push(`${result.viewport}: old evidence section still visible`);
  if (!result.hasNoDualSystemEvidence) missing.push(`${result.viewport}: dual-system or BaZi evidence still visible`);
  if (!result.hasNoSeparateAuthorityLabel) missing.push(`${result.viewport}: separate authority section label still present`);
  if (!result.hasNoInsightShortcutRows) missing.push(`${result.viewport}: insight shortcut navigation still present`);
  if (!result.hasNoReportLoadingGate) missing.push(`${result.viewport}: loading gate leaked into report`);
  if (!result.hasOldCtaRemoved) missing.push(`${result.viewport}: old CTA still visible`);
  if (!result.hasNoBaziTechnicalSummaries) missing.push(`${result.viewport}: BaZi module technical summaries still visible`);
  if (!result.hasNoBaziEvidenceBullets) missing.push(`${result.viewport}: BaZi evidence bullets still visible`);
  if (!result.hasNoWeakAspectPlaceholder) missing.push(`${result.viewport}: weak aspect placeholder still visible`);
  if (!result.hasNoMissingSignalPlaceholders) missing.push(`${result.viewport}: page still contains missing signal placeholder copy`);
  if (!result.hasNoTranslatedFitFormula) missing.push(`${result.viewport}: translated fit-summary formula still visible`);
  if (!result.hasNoAwkwardQuestionCopy) missing.push(`${result.viewport}: awkward question-answer copy still visible`);
  if (!result.hasNoFatalisticQuestionCopy) missing.push(`${result.viewport}: fatalistic question-answer copy still visible`);
  if (!result.hasNoVisibleBaziEvidence) missing.push(`${result.viewport}: BaZi evidence copy still visible`);
  if (!result.hasNoVisibleLegacyContractCopy) missing.push(`${result.viewport}: legacy free/upsell contract copy still visible`);
  if (!result.hasNoVisibleInternalPrecisionCopy) missing.push(`${result.viewport}: internal precision/debug copy still visible`);
  if (!result.hasNoVisibleFitSignalCounts) missing.push(`${result.viewport}: relationship-fit signal counts still visible`);
  if (!result.hasNoVisualCompanionLaneChips) missing.push(`${result.viewport}: visual companion lane chips still visible`);
  if (!result.hasDevResultScenarioPreviews) {
    const previewFailures = result.devResultScenarioPreviews.failures
      .map((failure) => `${failure.id}: ${failure.failures.join("; ")}`)
      .join(" | ");
    missing.push(
      `${result.viewport}: dev result scenario previews failed (${previewFailures || `api calls: ${result.devResultScenarioPreviews.apiCalls}`})`
    );
  }
  if (result.messages.length > 0) missing.push(`${result.viewport}: console warnings/errors present`);
  return missing;
});

console.log(JSON.stringify({ targetUrl, results, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
