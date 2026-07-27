"use client";

import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import { Eye, EyeOff, Orbit, RotateCcw, Sparkles, ZoomIn, ZoomOut } from "lucide-react";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { AdditiveBlending, CanvasTexture, CatmullRomCurve3, Color, DoubleSide, LinearFilter, SRGBColorSpace, TextureLoader, Vector3 } from "three";
import type { Group, Mesh, MeshBasicMaterial, ShaderMaterial } from "three";
import type {
  CompleteRelationshipResultViewModel,
  RelationshipThemeContext,
  RelationshipProfileCard,
  TimingGuidance,
  TimingSignal,
  WesternAspectEvidence,
  WesternRelationshipCaseFile,
  WesternNeedPoint
} from "@/data/complete-relationship-result";

type DashboardMode = "personA" | "personB" | "relationship";
type NeedRole = "person_a" | "person_b";
type ResultStepId = "chart-positioning" | "relationship-fit" | "core-answer" | "timing-reading" | "action-direction";
type ChartSceneTone = "foundation" | "fit" | "answer" | "timing" | "action";
type VisualCompanionMode = "personal-systems" | "mechanics-lanes" | "answer-path" | "timing-weather" | "action-route";
type ChartPoint = WesternNeedPoint["point"];
type AspectCategory = WesternAspectEvidence["category"];
type RelationshipThemeLike = Partial<
  Pick<RelationshipThemeContext, "actionFocus" | "answerFocus" | "doesNotProve" | "label" | "pairKeys" | "themeKey" | "timingFocus">
>;

type VisualPlanet = {
  id: string;
  role: NeedRole;
  ownerLabel: "你" | "對方";
  point: WesternNeedPoint["point"];
  pointLabel: string;
  sign: string;
  signLabel: string;
  house?: number | null;
  angleDeg: number;
  orbitRadius: number;
  orbitLevel: number;
  color: string;
  texture: string;
  placement: string;
  elementLabel?: string;
  modalityLabel?: string;
  meaning: string;
  body: string;
  stuckPattern?: string;
  nextMove?: string;
  confidence?: string;
};

type VisualAspect = {
  id: string;
  category: WesternAspectEvidence["category"];
  label: string;
  relationLabel: string;
  personAPoint: string;
  personBPoint: string;
  aspectLabel: string;
  orb?: number | null;
  strength: number;
  contactType?: string;
  body: string;
};

type VisualAspectRender = VisualAspect & {
  combinedCategories: AspectCategory[];
  combinedMeaning?: string;
  combinedPairLabel?: string;
  lineColorMode: "category" | "relationship-fit";
  sourceAspectIds: string[];
  visualRole: "highlight" | "muted";
};

type VisualCompanionStopMarker = {
  aspectId?: string;
  id: string;
  label: string;
  planetId?: string;
  tone: "boundary" | "caution" | "stop";
};

type VisualCompanionLane = {
  aspectIds: string[];
  id: "natural" | "practice" | "stuck";
  label: string;
  tone: AspectCategory | "mixed";
};

type VisualCompanionNote = {
  body: string;
  label: string;
  pointColor?: string;
  tone?: "support" | "neutral" | "caution" | "stop";
};

type VisualCompanionPlan = {
  focusQuestion: string;
  highlightAspectIds: string[];
  highlightPlanetIds: string[];
  mode: VisualCompanionMode;
  mutedAspectIds: string[];
  recommendedUserAction: string;
  stopMarkers: VisualCompanionStopMarker[];
  technicalNotes: VisualCompanionNote[];
  timingCertainty?: "trend_only" | "not_applicable";
  version: "visual-companion-plan-v1";
  whatThisDoesNotProve: string;
};

type ChartScenePlan = {
  aspectCategories: AspectCategory[];
  defaultMode: DashboardMode;
  sceneDescription: string;
  sceneTitle: string;
  selectedPlanetId: string;
  selectorHeading: string;
  stepId: ResultStepId;
  tone: ChartSceneTone;
  topicBody: string;
  topicDetail?: string;
  topicKey: string;
  topicLabel: string;
  topicTitle: string;
  visualCompanionPlan: VisualCompanionPlan;
};

type VisualModel = {
  aspects: VisualAspect[];
  defaultSelectedId: string;
  personAPlanets: VisualPlanet[];
  personBPlanets: VisualPlanet[];
  pointPositions: Record<string, PointPosition>;
  relationshipPlanets: VisualPlanet[];
};

type PointPosition = {
  x: number;
  y: number;
  z: number;
};

const ZODIAC_WHEEL = [
  { key: "白羊", label: "牡羊" },
  { key: "金牛", label: "金牛" },
  { key: "雙子", label: "雙子" },
  { key: "巨蟹", label: "巨蟹" },
  { key: "獅子", label: "獅子" },
  { key: "處女", label: "處女" },
  { key: "天秤", label: "天秤" },
  { key: "天蠍", label: "天蠍" },
  { key: "射手", label: "射手" },
  { key: "摩羯", label: "摩羯" },
  { key: "水瓶", label: "水瓶" },
  { key: "雙魚", label: "雙魚" }
] as const;

const POINT_META: Record<
  WesternNeedPoint["point"],
  { label: string; shortLabel: string; glyph: string; color: string; orbitLevel: number; offset: number }
> = {
  Moon: { label: "月亮", shortLabel: "情緒", glyph: "☾", color: "#d9ebff", orbitLevel: 1, offset: -8 },
  Mercury: { label: "水星", shortLabel: "溝通", glyph: "☿", color: "#9ee7f2", orbitLevel: 2, offset: -3 },
  Venus: { label: "金星", shortLabel: "喜歡", glyph: "♀", color: "#ffc86f", orbitLevel: 3, offset: 4 },
  Mars: { label: "火星", shortLabel: "行動", glyph: "♂", color: "#f2794f", orbitLevel: 4, offset: 9 },
  Saturn: { label: "土星", shortLabel: "界線", glyph: "♄", color: "#c9a777", orbitLevel: 5, offset: 14 },
  Desc: { label: "下降", shortLabel: "關係期待", glyph: "↘", color: "#b8e0ff", orbitLevel: 2, offset: 17 }
};

const POINT_LABEL_FALLBACKS: Record<string, string> = {
  Asc: "上升",
  Ascendant: "上升",
  Chiron: "凱龍星",
  Desc: "下降",
  Descendant: "下降",
  Jupiter: "木星",
  Mars: "火星",
  Mercury: "水星",
  Moon: "月亮",
  Neptune: "海王星",
  NorthNode: "北交點",
  Pluto: "冥王星",
  Saturn: "土星",
  SouthNode: "南交點",
  Sun: "太陽",
  Uranus: "天王星",
  Venus: "金星"
};

const MODE_COPY: Record<DashboardMode, { label: string; description: string }> = {
  personA: {
    label: "我的星盤",
    description: "先看你在關係裡怎麼需要安全感、怎麼說話、怎麼靠近。"
  },
  personB: {
    label: "對方星盤",
    description: "再看對方比較容易接住什麼，也看壓力來時會怎麼保護自己。"
  },
  relationship: {
    label: "合盤連線",
    description: "把兩個人的星盤放在一起，看自然牽動、磨合與容易誤會的位置。"
  }
};

const ASPECT_CATEGORY_LABELS: Record<WesternAspectEvidence["category"], string> = {
  attraction: "自然牽動",
  emotionalSafety: "安全感",
  pressure: "壓力",
  communication: "溝通",
  repair: "修復"
};

const ASPECT_CATEGORIES: WesternAspectEvidence["category"][] = ["attraction", "emotionalSafety", "pressure", "communication", "repair"];

const ASPECT_LINE_COLORS: Record<AspectCategory, string> = {
  attraction: "#ff4fd8",
  communication: "#36e7ff",
  emotionalSafety: "#66a6ff",
  pressure: "#ff4568",
  repair: "#58f6b0"
};

const COMBINED_ASPECT_LINE_COLOR = "#b875ff";
const COMBINED_ASPECT_LINE_LABEL = "紫金線";
const COMBINED_ASPECT_LEGEND_MEANING = "複合關係線";
const RELATIONSHIP_FIT_LINE_COLOR = COMBINED_ASPECT_LINE_COLOR;
const RELATIONSHIP_FIT_LINE_LABEL = "紫金線";
const RELATIONSHIP_FIT_LINE_MEANING = "合盤重點線";

const ASPECT_COLOR_GUIDE: Record<AspectCategory, { lineLabel: string; meaning: string }> = {
  attraction: { lineLabel: "玫瑰線", meaning: "自然牽動" },
  communication: { lineLabel: "青藍線", meaning: "溝通" },
  emotionalSafety: { lineLabel: "冰藍線", meaning: "安全感" },
  pressure: { lineLabel: "橘紅線", meaning: "壓力或卡住" },
  repair: { lineLabel: "薄荷線", meaning: "修復" }
};

const BLOCKED_ACTION_SUMMARY_LABELS: Record<string, string> = {
  alternate_account_contact: "不要換帳號聯絡",
  asking_for_answer_now: "不要立刻要答案",
  checking_social_media: "不要反覆查動態",
  emotional_confrontation: "不要情緒對質",
  forcing_relationship_definition: "不要逼關係定位",
  long_explanation: "不要一次講太長",
  long_pressure_message: "不要傳壓迫長文",
  pressure_for_commitment: "不要逼承諾",
  public_confrontation: "不要公開對質",
  rapid_escalation: "不要突然加速",
  relationship_definition_push: "不要急著定義關係",
  repeated_messages: "不要連續傳訊息",
  testing_loyalty: "不要測試對方",
  third_party_pressure: "不要請別人傳話",
  turning_reply_into_commitment: "不要把回覆當承諾",
  using_shared_space_as_pressure: "不要用共同空間施壓"
};

const COSMIC_ASSETS = {
  auraBlue: "/cosmic/aura-blue.png",
  auraGold: "/cosmic/aura-gold.png",
  galaxy: "/cosmic/galaxy-nebula.webp",
  star: "/cosmic/star-sprite.png",
  saturnRing: "/cosmic/saturn-ring.webp",
  sunMandala: "/cosmic/sun-mandala.webp",
  sunSurface: "/cosmic/solar-system-scope-sun-2k.webp",
  sunCorona: "/cosmic/sun-corona.webp",
  zodiacWheel: "/cosmic/zodiac-glyph-wheel.webp"
} as const;

const PLANET_TEXTURES: Record<WesternNeedPoint["point"], string> = {
  Moon: "/cosmic/solar-system-scope-moon-2k.webp",
  Mercury: "/cosmic/solar-system-scope-mercury-2k.webp",
  Venus: "/cosmic/solar-system-scope-venus-atmosphere-2k.webp",
  Mars: "/cosmic/solar-system-scope-mars-2k.webp",
  Saturn: "/cosmic/solar-system-scope-saturn-2k.webp",
  Desc: "/cosmic/solar-system-scope-earth-2k.webp"
};

const SUN_GOLD_VERTEX_SHADER = `
  varying vec2 vUv;
  varying vec3 vNormalView;
  varying vec3 vViewDirection;

  void main() {
    vUv = uv;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vNormalView = normalize(normalMatrix * normal);
    vViewDirection = normalize(-mvPosition.xyz);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const SUN_GOLD_FRAGMENT_SHADER = `
  uniform sampler2D uTexture;
  uniform float uTime;

  varying vec2 vUv;
  varying vec3 vNormalView;
  varying vec3 vViewDirection;

  void main() {
    vec2 uv = vUv;
    uv.x = fract(uv.x + sin(uTime * 0.08) * 0.004);

    vec3 raw = texture2D(uTexture, uv).rgb;
    float light = dot(raw, vec3(0.299, 0.587, 0.114));
    float textureFire = smoothstep(0.12, 0.95, raw.r) * 0.06 + smoothstep(0.2, 0.9, raw.g) * 0.03;

    vec3 emberGold = vec3(0.48, 0.30, 0.08);
    vec3 ritualGold = vec3(0.86, 0.62, 0.18);
    vec3 champagneGold = vec3(1.0, 0.80, 0.32);
    vec3 sacredWhite = vec3(1.0, 0.95, 0.68);

    vec3 gold = mix(emberGold, ritualGold, smoothstep(0.12, 0.54, light));
    gold = mix(gold, champagneGold, smoothstep(0.48, 0.82, light));
    gold = mix(gold, sacredWhite, smoothstep(0.82, 1.0, light));
    gold += vec3(0.28, 0.11, 0.01) * textureFire;

    float rim = pow(1.0 - max(dot(normalize(vNormalView), normalize(vViewDirection)), 0.0), 1.85);
    float pulse = 0.94 + sin(uTime * 1.45 + light * 5.0) * 0.045;
    gold = gold * pulse + vec3(1.0, 0.72, 0.24) * rim * 0.58;

    gl_FragColor = vec4(gold, 1.0);
  }
`;

const SUN_GLOW_FRAGMENT_SHADER = `
  uniform float uTime;

  varying vec2 vUv;
  varying vec3 vNormalView;
  varying vec3 vViewDirection;

  void main() {
    float rim = pow(1.0 - max(dot(normalize(vNormalView), normalize(vViewDirection)), 0.0), 1.45);
    float verticalWarmth = smoothstep(0.08, 0.92, vUv.y);
    float breath = 0.68 + sin(uTime * 1.25) * 0.13;
    vec3 glow = mix(vec3(1.0, 0.58, 0.12), vec3(1.0, 0.88, 0.48), verticalWarmth);
    gl_FragColor = vec4(glow, rim * breath * 0.32);
  }
`;

function cleanDashboardCopy(value?: string | null) {
  const raw = value ?? "";
  if (/birth_time|noon fallback|date_noon_fallback|time-sensitive/i.test(raw)) {
    return "出生時間不完整時，會避開上升、宮位與其他時間敏感結論；這些只作背景，不拿來下精準判斷。";
  }
  if (/house overlay|not wired|calculation/i.test(raw)) {
    return "目前還沒有合盤宮位覆蓋計算，所以宮位只作背景，不拿來做精準關係結論。";
  }

  return raw
    .replaceAll("白羊", "牡羊")
    .replaceAll("低壓", "壓力比較小")
    .replaceAll("低刺激", "短、輕、可退場")
    .replaceAll("互動氣候", "互動節奏")
    .replaceAll("壓力層承接", "壓力能不能被處理")
    .replaceAll("現實回應承接", "穩定的現實回應")
    .replaceAll("情緒承接位置", "情緒比較容易被接住的位置")
    .replaceAll("情緒承接", "情緒比較容易被接住")
    .replaceAll("可預期承接", "可預期回應")
    .replaceAll("成熟承接", "成熟回應")
    .replaceAll("被安全承接", "被安全地接住")
    .replaceAll("被承接", "被接住")
    .replaceAll("可承接", "比較接得住")
    .replaceAll("是否能承接", "能不能接住")
    .replaceAll("能否承接", "能不能接住")
    .replaceAll("能承接", "能接住")
    .replaceAll("穩定承接", "穩定接住")
    .replaceAll("需要翻譯", "需要說清楚")
    .replaceAll("先翻譯成", "先說成")
    .replaceAll("修復槓桿", "可以怎麼修")
    .replaceAll("行動尺度", "接下來適合做到哪一步")
    .replaceAll("開口門檻", "開口前先看什麼")
    .replaceAll("精準證據", "主要依據")
    .replaceAll("orb 約", "角度差約")
    .replaceAll("先降壓", "先讓壓力降下來")
    .replaceAll("降壓", "讓壓力降下來")
    .replaceAll("窗口", "時段")
    .replace(/(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])/g, "");
}

export function ImmersiveCosmicDashboard({
  activeStepId = "chart-positioning",
  data
}: {
  activeStepId?: ResultStepId;
  data: CompleteRelationshipResultViewModel;
}) {
  const visualModel = useMemo(() => buildVisualModel(data), [data]);
  const scenePlan = useMemo(() => buildChartScenePlan(data, activeStepId, visualModel), [activeStepId, data, visualModel]);
  const [mode, setMode] = useState<DashboardMode>("relationship");
  const [selectedId, setSelectedId] = useState(visualModel.defaultSelectedId);
  const [showAspects, setShowAspects] = useState(true);
  const [showZodiac, setShowZodiac] = useState(true);
  const [autoRotate, setAutoRotate] = useState(true);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    setMode(scenePlan.defaultMode);
    setSelectedId(scenePlan.selectedPlanetId || visualModel.defaultSelectedId);
    setShowAspects(true);
  }, [scenePlan.defaultMode, scenePlan.selectedPlanetId, visualModel.defaultSelectedId, activeStepId]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (media.matches) setAutoRotate(false);
  }, []);

  const activePlanets =
    mode === "personA"
      ? visualModel.personAPlanets
      : mode === "personB"
        ? visualModel.personBPlanets
        : visualModel.relationshipPlanets;
  const selectedPlanet = activePlanets.find((planet) => planet.id === selectedId) ?? activePlanets[0] ?? visualModel.relationshipPlanets[0];
  const visualCompanionPlan = scenePlan.visualCompanionPlan;
  const sceneAspects = buildSceneAspects(visualModel.aspects, visualCompanionPlan);
  const relationshipAspects = showAspects && mode === "relationship" ? sceneAspects : [];
  const visibleAspectCategories = useMemo(() => categoriesInAspectOrder(relationshipAspects), [relationshipAspects]);
  const visibleAspectIds = relationshipAspects.flatMap((aspect) => (aspect.sourceAspectIds.length ? aspect.sourceAspectIds : [aspect.id]));
  const visibleLineLabels = useMemo(
    () => aspectLegendItems(relationshipAspects).map((item) => `${item.lineLabel}：${item.meaning}`),
    [relationshipAspects]
  );
  const stopMarkerLabels = visualCompanionPlan.stopMarkers.map((marker) => marker.label).filter(Boolean);

  useEffect(() => {
    if (!activePlanets.some((planet) => planet.id === selectedId)) {
      setSelectedId(activePlanets[0]?.id ?? visualModel.defaultSelectedId);
    }
  }, [activePlanets, selectedId, visualModel.defaultSelectedId]);

  return (
    <section
      className="immersive-cosmic-dashboard"
      data-active-mode={mode}
      data-active-owner={selectedPlanet?.role ?? ""}
      data-active-point={selectedPlanet?.point ?? ""}
      data-active-reading-step={activeStepId}
      data-active-sign={selectedPlanet?.sign ?? ""}
      data-aspect-count={visualModel.aspects.length}
      data-chart-scene={scenePlan.stepId}
      data-chart-topic={scenePlan.topicKey}
      data-depth-model="three-orbit-plane"
      data-explorer-open="false"
      data-overlay-markers={visualCompanionPlan.stopMarkers.length ? "visual-companion-stop-markers" : "none"}
      data-selected-highlight="orbital-beacon"
      data-scenario-id={data.id}
      data-visual-companion-fields={visualCompanionFieldTrace(visualCompanionPlan)}
      data-visual-companion-focus={visualCompanionPlan.focusQuestion}
      data-visual-companion-mode={visualCompanionPlan.mode}
      data-visual-companion-plan={visualCompanionPlan.version}
      data-visual-highlight-aspect-ids={visualCompanionPlan.highlightAspectIds.length ? visualCompanionPlan.highlightAspectIds.join(",") : "none"}
      data-visual-highlight-planet-ids={visualCompanionPlan.highlightPlanetIds.length ? visualCompanionPlan.highlightPlanetIds.join(",") : "none"}
      data-visual-muted-aspect-ids={visualCompanionPlan.mutedAspectIds.length ? visualCompanionPlan.mutedAspectIds.join(",") : "none"}
      data-visual-recommended-action={visualCompanionPlan.recommendedUserAction}
      data-visual-stop-markers={stopMarkerLabels.length ? stopMarkerLabels.join("|") : "none"}
      data-visual-timing-certainty={visualCompanionPlan.timingCertainty ?? "not_applicable"}
      data-visual-visible-aspect-ids={visibleAspectIds.length ? visibleAspectIds.join(",") : "none"}
      data-visual-what-this-does-not-prove={visualCompanionPlan.whatThisDoesNotProve}
      data-visible-aspect-categories={visibleAspectCategories.length ? visibleAspectCategories.join(",") : "none"}
      data-visible-line-labels={visibleLineLabels.length ? visibleLineLabels.join("|") : "none"}
      data-visual-theme="ornate-cosmic-instrument"
      aria-label="互動式星盤儀表板"
    >
      <div className="immersive-dashboard-top">
        <div className="immersive-title-lockup">
          <span>光之谷 星盤儀表板</span>
          <h1>{scenePlan.sceneTitle}</h1>
          <p>{scenePlan.sceneDescription}</p>
        </div>
        <div className="immersive-dashboard-tabs" aria-label="切換星盤視角">
          {(["personA", "personB", "relationship"] as const).map((item) => (
            <button
              aria-pressed={mode === item}
              key={item}
              onClick={() => setMode(item)}
              type="button"
            >
              {MODE_COPY[item].label}
            </button>
          ))}
        </div>
      </div>

      <div className="immersive-dashboard-grid">
        <aside className="immersive-planet-panel" aria-label="選擇行星">
          <div className="immersive-panel-heading">
            <span>{scenePlan.selectorHeading}</span>
          </div>
          <div className="immersive-planet-list">
            {activePlanets.map((planet) => (
              <button
                aria-label={`${planet.ownerLabel}的${planet.pointLabel}：${cleanDashboardCopy(planet.placement)}`}
                aria-pressed={selectedPlanet?.id === planet.id}
                className="immersive-planet-button"
                key={planet.id}
                onClick={() => setSelectedId(planet.id)}
                type="button"
              >
                <span
                  className="planet-glow-dot"
                  style={{ backgroundColor: planet.color, backgroundImage: `url(${planet.texture})` }}
                />
                <span className="planet-row-copy">
                  <strong>{planet.pointLabel}</strong>
                  <small>{planet.ownerLabel}</small>
                </span>
                <span className="planet-glyph" aria-hidden="true">{POINT_META[planet.point].glyph}</span>
                <Eye size={17} aria-hidden="true" />
              </button>
            ))}
          </div>
        </aside>

        <div className="immersive-chart-stage">
          <div className="immersive-three-wrap" aria-hidden="true">
            <CosmicThreeCanvas
              aspects={relationshipAspects}
              autoRotate={autoRotate}
              sceneTone={scenePlan.tone}
              planets={activePlanets}
              pointPositions={visualModel.pointPositions}
              selectedId={selectedPlanet?.id}
              visualCompanionPlan={visualCompanionPlan}
              showZodiac={showZodiac}
              isExplorerOpen={false}
              onSelectPlanet={setSelectedId}
              zoom={zoom}
            />
          </div>
          <div className="immersive-selected-ribbon">
            <span>{selectedPlanet?.ownerLabel}</span>
            <strong>
              {selectedPlanet ? `${selectedPlanet.pointLabel} ${cleanDashboardCopy(selectedPlanet.signLabel)}` : "星盤定位"}
            </strong>
            <small>{selectedPlanet?.house ? `第 ${selectedPlanet.house} 宮` : "宮位需可靠出生時間"}</small>
          </div>
          <div className="immersive-control-bar" aria-label="星盤控制">
            <button aria-pressed={showZodiac} onClick={() => setShowZodiac((current) => !current)} type="button">
              <Orbit size={16} aria-hidden="true" />
              星座輪
            </button>
            <button aria-pressed={showAspects} onClick={() => setShowAspects((current) => !current)} type="button">
              {showAspects ? <Eye size={16} aria-hidden="true" /> : <EyeOff size={16} aria-hidden="true" />}
              相位連線
            </button>
            <button aria-pressed={autoRotate} onClick={() => setAutoRotate((current) => !current)} type="button">
              <Sparkles size={16} aria-hidden="true" />
              自動旋轉
            </button>
            <button onClick={() => setZoom((current) => Math.min(1.35, Number((current + 0.1).toFixed(2))))} type="button">
              <ZoomIn size={16} aria-hidden="true" />
              放大
            </button>
            <button onClick={() => setZoom((current) => Math.max(0.82, Number((current - 0.1).toFixed(2))))} type="button">
              <ZoomOut size={16} aria-hidden="true" />
              縮小
            </button>
            <button onClick={() => setZoom(1)} type="button">
              <RotateCcw size={16} aria-hidden="true" />
              重置視角
            </button>
          </div>
        </div>

        <aside className="immersive-reading-panel" aria-label="目前選定星盤解讀">
          {selectedPlanet ? (
            <>
              <div className="immersive-reading-head">
                <span
                  className="reading-orb"
                  style={{ backgroundColor: selectedPlanet.color, backgroundImage: `url(${selectedPlanet.texture})` }}
                />
                <div>
                  <span>{selectedPlanet.ownerLabel}的{selectedPlanet.pointLabel}</span>
                  <h2>{cleanDashboardCopy(selectedPlanet.placement)}</h2>
                </div>
              </div>
              <dl className="immersive-fact-grid">
                <div>
                  <dt>星座</dt>
                  <dd>{cleanDashboardCopy(selectedPlanet.signLabel)}</dd>
                </div>
                <div>
                  <dt>宮位</dt>
                  <dd>{selectedPlanet.house ? `第 ${selectedPlanet.house} 宮` : "未使用"}</dd>
                </div>
                <div>
                  <dt>元素</dt>
                  <dd>{selectedPlanet.elementLabel ?? "以星座判讀"}</dd>
                </div>
                <div>
                  <dt>品質</dt>
                  <dd>{selectedPlanet.modalityLabel ?? "以星座判讀"}</dd>
                </div>
              </dl>
              <section className="immersive-reading-copy">
                <span>這代表什麼</span>
                <p>{cleanDashboardCopy(selectedPlanet.body || selectedPlanet.meaning)}</p>
                {selectedPlanet.stuckPattern ? (
                  <p>{cleanDashboardCopy(selectedPlanet.stuckPattern)}</p>
                ) : null}
              </section>
              <section className="immersive-aspect-summary" data-chart-topic={scenePlan.topicKey}>
                <span>{scenePlan.topicLabel}</span>
                <strong>{cleanDashboardCopy(scenePlan.topicTitle)}</strong>
                {scenePlan.topicBody ? <p>{cleanDashboardCopy(scenePlan.topicBody)}</p> : null}
                {scenePlan.topicDetail ? <p>{cleanDashboardCopy(scenePlan.topicDetail)}</p> : null}
                <VisualCompanionPlanPanel plan={visualCompanionPlan} />
                <AspectColorLegend aspects={relationshipAspects} />
              </section>
            </>
          ) : (
            <p>目前沒有足夠的星盤定位資料可以顯示。</p>
          )}
        </aside>
      </div>
    </section>
  );
}

function buildChartScenePlan(data: CompleteRelationshipResultViewModel, activeStepId: ResultStepId, visualModel: VisualModel): ChartScenePlan {
  const strongestAspect = visualModel.aspects[0];
  const answerGuidance = data.answerGuidance ?? data.readableQuestionAnswer?.sections.answer;
  const timingGuidance = data.timingGuidance ?? data.readableQuestionAnswer?.sections.timing;
  const actionGuidance = data.actionGuidance ?? data.readableQuestionAnswer?.sections.action;

  if (activeStepId === "relationship-fit") {
    const selectedAspects = selectRelationshipFitAspects(visualModel.aspects);
    const selectedPlanetId = selectedPlanetForAspect(visualModel, selectedAspects[0] ?? strongestAspect) ?? visualModel.defaultSelectedId;
    const companionPlan = buildRelationshipFitCompanionPlan(data, visualModel, selectedAspects);
    const archetype = data.relationshipArchetype;
    const attractionItem = data.attractionDynamics?.items?.[0];
    const conflictItem = data.conflictDynamics?.items?.[0];
    return {
      aspectCategories: categoriesInAspectOrder(selectedAspects),
      defaultMode: "relationship",
      sceneDescription: "把兩個人的星盤放在一起，看自然牽動、磨合與容易誤會的位置。",
      sceneTitle: "兩個人的關係契合度分析",
      selectedPlanetId,
      selectorHeading: "關係線索",
      stepId: activeStepId,
      tone: "fit",
      topicBody: archetype
        ? `關係型態：${archetype.title}。${archetype.subtitle}`
        : "金星和火星反映吸引與行動節奏，月亮和水星反映情緒與溝通，土星則反映壓力與卡點。",
      topicDetail: [attractionItem?.technical, conflictItem?.technical]
        .filter(Boolean)
        .join("；") || "圖上突出會影響互動機制的合盤線，讓你直接看到吸引、溝通、壓力與修復節奏。",
      topicKey: "relationship-fit",
      topicLabel: "合盤重點",
      topicTitle: "看關係型態與主相位",
      visualCompanionPlan: companionPlan
    };
  }

  if (activeStepId === "core-answer") {
    const theme = relationshipThemeFrom(answerGuidance?.relationshipTheme);
    const categories = categoriesForEvidenceKeys(answerGuidance?.evidenceClusterKeys, theme?.themeKey);
    const focusPoint = pointForText([answerGuidance?.questionKey, answerGuidance?.questionLabel, answerGuidance?.shortAnswer, theme?.label, theme?.answerFocus]);
    const selectedAspects = selectCoreAnswerAspects(visualModel.aspects, theme, categories);
    const companionPlan = buildCoreAnswerCompanionPlan(data, visualModel, selectedAspects);
    const selectedPlanetId = selectedPlanetForPoint(visualModel, focusPoint ?? "Moon") ?? visualModel.defaultSelectedId;
    const answerCategories: AspectCategory[] = categories.length ? categories : ["emotionalSafety", "pressure"];
    const partnerNeed = data.partnerNeeds?.items?.[0];
    const partnerProfile = data.partnerNeeds?.profile;
    return {
      aspectCategories: answerCategories,
      defaultMode: "relationship",
      sceneDescription: "只突出本題真正用到的星盤線索，避免把所有資訊都混在一起。",
      sceneTitle: "核心問題解讀",
      selectedPlanetId,
      selectorHeading: "答案線索",
      stepId: activeStepId,
      tone: "answer",
      topicBody: partnerProfile?.relationshipStyleWanted
        ? `關係需求：${partnerProfile.relationshipStyleWanted}`
        : partnerNeed
        ? `需求線索：${partnerNeed.title}。${partnerNeed.relationshipStyleWanted ?? partnerNeed.need}`
        : "只有直接支持核心問題的星盤證據，才適合放進答案。",
      topicDetail: partnerProfile?.commonMisread
        ? `容易誤會：${partnerProfile.commonMisread}`
        : partnerNeed
        ? `容易誤會：${partnerNeed.commonMisread ?? partnerNeed.howItShowsUp}`
        : "圖上亮起的是答案路徑，不是對方內心宣告；一般契合度也不能直接變成結論。",
      topicKey: "core-answer",
      topicLabel: "核心問題重點",
      topicTitle: "看答案證據與需求線索",
      visualCompanionPlan: companionPlan
    };
  }

  if (activeStepId === "timing-reading") {
    const theme = relationshipThemeFrom(timingGuidance?.relationshipTheme);
    const focusPoint = pointForTimingSignals(timingGuidance?.selectedSignals) ?? pointForText([timingGuidance?.recommendedAction, timingGuidance?.contactMode, theme?.timingFocus]);
    const selectedPlanetId = selectedPlanetForPoint(visualModel, focusPoint ?? "Mercury") ?? visualModel.defaultSelectedId;
    const timingCategories = categoriesForTimingSignals(timingGuidance?.selectedSignals, theme?.themeKey);
    const selectedAspects = selectTimingAspects(visualModel.aspects, timingGuidance, theme);
    const companionPlan = buildTimingCompanionPlan(data, visualModel, selectedAspects);
    const turningWindow = data.relationshipTurningWindows?.items?.[0];
    return {
      aspectCategories: timingCategories,
      defaultMode: "relationship",
      sceneDescription: "用當下關係氣候看節奏：適合觀察、輕靠近，還是先不要加壓。",
      sceneTitle: "時機判讀",
      selectedPlanetId,
      selectorHeading: "時機線索",
      stepId: activeStepId,
      tone: "timing",
      topicBody: turningWindow
        ? `2026 轉折氣候：${turningWindow.title}。${turningWindow.meaning}`
        : "水星反映溝通時段，金星反映情感柔軟度，火星反映衝動摩擦，土星反映現實壓力，月亮反映短期情緒。",
      topicDetail: turningWindow
        ? `建議：${turningWindow.suggestion}`
        : companionPlan.highlightAspectIds.length
        ? "亮起的線保留會影響互動節奏的線索，幫你判斷現在適合觀察、輕觸、暫停，還是先保持距離。"
        : "目前只標出互動節奏主角，幫你用關係氣候判斷觀察、輕觸、暫停或保持距離。",
      topicKey: "timing-reading",
      topicLabel: "時機重點",
      topicTitle: "看現在的互動節奏",
      visualCompanionPlan: companionPlan
    };
  }

  if (activeStepId === "action-direction") {
    const theme = relationshipThemeFrom(actionGuidance?.relationshipTheme);
    const focusPoint = pointForText([
      actionGuidance?.actionMode,
      actionGuidance?.nextMove,
      actionGuidance?.readableInterpretation?.body,
      actionGuidance?.blockedActions?.join(" "),
      theme?.actionFocus
    ]);
    const selectedPlanetId = selectedPlanetForPoint(visualModel, focusPoint ?? "Saturn") ?? visualModel.defaultSelectedId;
    const actionCategories = categoriesForEvidenceKeys(actionGuidance?.evidenceClusterKeys, theme?.themeKey, ["pressure", "communication", "repair"]);
    const selectedAspects = selectActionAspects(visualModel.aspects, actionGuidance?.actionMode, actionGuidance?.blockedActions, theme);
    const companionPlan = buildActionCompanionPlan(data, visualModel, selectedAspects);
    const landmine = data.fightLandmines?.items?.[0];
    return {
      aspectCategories: actionCategories,
      defaultMode: "relationship",
      sceneDescription: "把下一步變成可以執行的尺度：怎麼靠近、怎麼說、哪些先不要做。",
      sceneTitle: "行動方向",
      selectedPlanetId,
      selectorHeading: "行動線索",
      stepId: activeStepId,
      tone: "action",
      topicBody: landmine
        ? `行動先避開：${landmine.title}。${landmine.trigger}`
        : "安全行動要同時包含可以做的事、需要避開的事，以及清楚的停止線。",
      topicDetail: landmine
        ? `改成：${landmine.whatToDoInstead}`
        : `${blockedActionSummary(actionGuidance?.blockedActions) || "停止線：依目前情境保留短、輕、可退場的互動方式。"} 行動建議優先考慮：壓力小、可退場、不逼迫、不過度自我解讀。`,
      topicKey: "action-direction",
      topicLabel: "行動重點",
      topicTitle: "看地雷與安全行動",
      visualCompanionPlan: companionPlan
    };
  }

  const companionPlan = buildChartPositioningCompanionPlan(data, visualModel);
  return {
    aspectCategories: [],
    defaultMode: "relationship",
    sceneDescription: "先看你和對方各自的關係功能，再看兩個人的互動怎麼接上。",
    sceneTitle: "星盤定位",
    selectedPlanetId: selectedPlanetForPoint(visualModel, "Moon") ?? visualModel.defaultSelectedId,
    selectorHeading: "選擇行星",
    stepId: "chart-positioning",
    tone: "foundation",
    topicBody: "被圈起來的星是目前查看的關係功能。先看月亮、水星、金星、火星、土星各自負責什麼。",
    topicDetail: "月亮、水星、金星、火星與土星，分別描述情緒、溝通、吸引、行動與壓力反應。",
    topicKey: "chart-positioning",
    topicLabel: "星盤定位重點",
    topicTitle: "先定位兩人的關係使用說明",
    visualCompanionPlan: companionPlan
  };
}

function buildChartPositioningCompanionPlan(data: CompleteRelationshipResultViewModel, visualModel: VisualModel): VisualCompanionPlan {
  const myMoonId = selectedPlanetForPoint(visualModel, "Moon", "person_a");
  const partnerSaturnId = selectedPlanetForPoint(visualModel, "Saturn", "person_b");
  const precisionNote = readablePrecisionNote(data);

  return {
    focusQuestion: "你在關係裡需要什麼安全感？對方在壓力下怎麼保護自己？",
    highlightAspectIds: [],
    highlightPlanetIds: compactIds([myMoonId, partnerSaturnId]),
    mode: "personal-systems",
    mutedAspectIds: visualModel.aspects.map((aspect) => aspect.id),
    recommendedUserAction: "先把兩個人的關係使用說明分開看懂，不急著下合不合或會不會回來的結論。",
    stopMarkers: [],
    technicalNotes: [
      { body: "月亮先看安全感：不安時需要什麼，才不會把焦慮全丟到對方身上。", label: "你要什麼安全感", tone: "support" },
      { body: "土星先看壓力反應：壓力來時對方可能變慢、變硬，先看他能不能用穩定行動回應。", label: "對方怎麼回應壓力", tone: "caution" },
      { body: precisionNote, label: "資料精度提醒", tone: "neutral" }
    ],
    timingCertainty: "not_applicable",
    version: "visual-companion-plan-v1",
    whatThisDoesNotProve: "先看月亮、水星、金星、火星、土星，把關係需求翻成可觀察的互動方式。"
  };
}

function buildRelationshipFitCompanionPlan(
  data: CompleteRelationshipResultViewModel,
  visualModel: VisualModel,
  selectedAspects: VisualAspect[]
): VisualCompanionPlan {
  const highlightedIds = selectedAspects.slice(0, 5).map((aspect) => aspect.id);
  const lanes = relationshipMechanicLanes(selectedAspects);
  const laneNotes = lanes.map((lane) => ({
    body: relationshipLaneExplanation(lane),
    label: lane.label,
    tone: lane.id === "stuck" ? "caution" : lane.id === "natural" ? "support" : "neutral"
  }) satisfies VisualCompanionNote);
  const insightNoteCandidates: Array<VisualCompanionNote | undefined> = [
    data.attractionDynamics?.items?.[0]
      ? {
          body: data.attractionDynamics.items[0].technical,
          label: "核心吸引力相位",
          tone: "support"
        }
      : undefined,
    data.conflictDynamics?.items?.[0]
      ? {
          body: data.conflictDynamics.items[0].technical,
          label: "最需要留意的卡點",
          tone: "caution"
        }
      : undefined,
    data.growthDynamics?.items?.[0]
      ? {
          body: data.growthDynamics.items[0].technical,
          label: "成長線索",
          tone: "neutral"
        }
      : undefined
  ];
  const insightNotes = insightNoteCandidates.filter((note): note is VisualCompanionNote => Boolean(note));

  return {
    focusQuestion: "你們哪裡自然靠近、哪裡需要說清楚、哪裡最容易被壓力卡住？",
    highlightAspectIds: highlightedIds,
    highlightPlanetIds: planetIdsForAspects(visualModel, selectedAspects),
    mode: "mechanics-lanes",
    mutedAspectIds: mutedAspectIds(visualModel.aspects, highlightedIds, 5),
    recommendedUserAction: "先看哪一組相位負責吸引，哪一組相位帶來摩擦，再看有沒有能重新接話的橋。",
    stopMarkers: stopMarkersForPressureAspects(visualModel, selectedAspects, "壓力觸發"),
    technicalNotes: [
      ...insightNotes,
      ...laneNotes,
      ...relationshipAspectTechnicalNotes(selectedAspects).slice(0, 2)
    ].slice(0, 5),
    timingCertainty: "not_applicable",
    version: "visual-companion-plan-v1",
    whatThisDoesNotProve: "用這些契合訊號看吸引、摩擦和修復方向，再回到實際互動判斷下一步。"
  };
}

function buildCoreAnswerCompanionPlan(
  data: CompleteRelationshipResultViewModel,
  visualModel: VisualModel,
  selectedAspects: VisualAspect[]
): VisualCompanionPlan {
  const answerGuidance = data.answerGuidance ?? data.readableQuestionAnswer?.sections.answer;
  const theme = relationshipThemeFrom(answerGuidance?.relationshipTheme);
  const supportAspect = selectedAspects.find((aspect) => aspect.category !== "pressure");
  const pressureAspect = selectedAspects.find((aspect) => aspect.category === "pressure");
  const highlightedIds = selectedAspects.map((aspect) => aspect.id);
  const boundary = answerGuidance?.readableInterpretation?.caution ?? theme?.answerFocus ?? "先看可觀察的關係訊號和現實回應，再決定下一步。";
  const partnerNeed = data.partnerNeeds?.items?.[0];
  const partnerProfile = data.partnerNeeds?.profile;

  return {
    focusQuestion: `${answerGuidance?.questionLabel ?? data.reading.question}：先看有沒有反應線，再看為什麼沒有行動。`,
    highlightAspectIds: highlightedIds,
    highlightPlanetIds: planetIdsForAspects(visualModel, selectedAspects),
    mode: "answer-path",
    mutedAspectIds: mutedAspectIds(visualModel.aspects, highlightedIds, 4),
    recommendedUserAction: answerGuidance?.nextMove ?? answerGuidance?.readableInterpretation?.nextMove ?? "先看下一個可觀察反應，不用立刻逼答案。",
    stopMarkers: pressureAspect
      ? [
          {
            aspectId: pressureAspect.id,
            id: "core-boundary",
            label: "看可觀察回應",
            planetId: selectedPlanetForAspect(visualModel, pressureAspect),
            tone: "boundary"
          }
        ]
      : [],
    technicalNotes: [
      partnerProfile?.relationshipStyleWanted
        ? {
            body: partnerProfile.relationshipStyleWanted,
            label: "他想要的關係輪廓",
            tone: "support"
          }
        : partnerNeed
        ? {
            body: partnerNeed.relationshipStyleWanted ?? partnerNeed.need,
            label: "對方關係需求",
            tone: "support"
          }
        : undefined,
      supportAspect ? technicalAspectNote(supportAspect, "反應線") : { body: "目前核心答案會先看可觀察的回應，不用一句有或沒有收掉。", label: "反應線", tone: "neutral" },
      pressureAspect ? technicalAspectNote(pressureAspect, "為什麼卡住") : { body: "目前壓力線不明顯時，答案會更多依賴現實狀態修正。", label: "為什麼卡住", tone: "caution" }
    ].filter((note): note is VisualCompanionNote => Boolean(note)),
    timingCertainty: "not_applicable",
    version: "visual-companion-plan-v1",
    whatThisDoesNotProve: boundary
  };
}

function buildTimingCompanionPlan(
  data: CompleteRelationshipResultViewModel,
  visualModel: VisualModel,
  selectedAspects: VisualAspect[]
): VisualCompanionPlan {
  const timingGuidance = data.timingGuidance ?? data.readableQuestionAnswer?.sections.timing;
  const signals = timingGuidance?.selectedSignals?.slice(0, 5) ?? [];
  const signalPoints = signals.map((signal) => pointForTimingNote(signal.key, signal.title, signal.body)).filter(Boolean) as ChartPoint[];
  const turningPoints = (data.relationshipTurningWindows?.items ?? [])
    .slice(0, 2)
    .map((item) => normalizePointForChart(item.transitPoint) ?? pointForText([item.title, item.suggestion]))
    .filter(Boolean) as ChartPoint[];
  const fallbackWeatherPoints: ChartPoint[] = ["Mercury", "Venus", "Mars", "Saturn", "Moon"];
  const weatherPoints: ChartPoint[] = compactPoints([...turningPoints, ...signalPoints]).length
    ? compactPoints([...turningPoints, ...signalPoints])
    : fallbackWeatherPoints;
  const highlightedIds = selectedAspects.map((aspect) => aspect.id);
  const exactTimingReason =
    data.westernRelationshipCaseFile?.timingLayer.windowScan.exactTimingPolicy.reason ??
    timingGuidance?.readableInterpretation?.caution ??
    "目前先回到互動節奏。";
  const turningNotes = (data.relationshipTurningWindows?.items ?? []).slice(0, 2).map((item) => {
    const point = normalizePointForChart(item.transitPoint) ?? pointForText([item.title, item.suggestion]);
    return {
      body: item.suggestion,
      label: item.title,
      pointColor: point ? POINT_META[point]?.color : undefined,
      tone: item.transitPoint === "Mars" || item.transitPoint === "Saturn" ? "caution" : "neutral"
    } satisfies VisualCompanionNote;
  });

  return {
    focusQuestion: "現在適合觀察、輕觸、暫停，還是不建議聯絡？",
    highlightAspectIds: highlightedIds,
    highlightPlanetIds: planetIdsForPoints(visualModel, weatherPoints, ["person_a"]),
    mode: "timing-weather",
    mutedAspectIds: mutedAspectIds(visualModel.aspects, highlightedIds, 3),
    recommendedUserAction: timingGuidance?.recommendedActionLabel ?? timingGuidance?.nextMove ?? "先觀察，讓互動有一點空間。",
    stopMarkers: signals
      .filter((signal) => signal.state === "caution")
      .slice(0, 2)
      .map((signal, index) => {
        const point = pointForText([signal.key, signal.title, signal.body]) ?? (index === 0 ? "Mars" : "Saturn");
        return {
          id: `timing-caution-${index + 1}`,
          label: cleanDashboardCopy(signal.title),
          planetId: selectedPlanetForPoint(visualModel, point, "person_a"),
          tone: "caution" as const
        };
      }),
    technicalNotes: [...turningNotes, ...timingWeatherNotes(signals)].slice(0, 5),
    timingCertainty: "trend_only",
    version: "visual-companion-plan-v1",
    whatThisDoesNotProve: timingGuidance?.preciseDatesAvailable === false ? "用月份區間抓互動節奏，再決定行動大小。" : "把比較適合的時段當成輕一點靠近的參考。"
  };
}

function buildActionCompanionPlan(
  data: CompleteRelationshipResultViewModel,
  visualModel: VisualModel,
  selectedAspects: VisualAspect[]
): VisualCompanionPlan {
  const actionGuidance = data.actionGuidance ?? data.readableQuestionAnswer?.sections.action;
  const pressureAspect = selectedAspects.find((aspect) => aspect.category === "pressure");
  const safeAspect = selectedAspects.find((aspect) => aspect.category === "repair" || aspect.category === "communication");
  const highlightedIds = selectedAspects.map((aspect) => aspect.id);
  const blockedActions = actionGuidance?.blockedActions?.slice(0, 2) ?? [];
  const boundary = compactDashboardGuidanceCopy(actionGuidance?.readableInterpretation?.caution) ?? "一次訊息先觀察當下反應，再決定下一步要停、等，還是延續。";
  const landmine = data.fightLandmines?.items?.[0];
  const guide = data.survivalGuide?.items?.[0];

  return {
    focusQuestion: "接下來先避開什麼？如果要開口，只能用多輕的方式？",
    highlightAspectIds: highlightedIds,
    highlightPlanetIds: planetIdsForAspects(visualModel, selectedAspects),
    mode: "action-route",
    mutedAspectIds: mutedAspectIds(visualModel.aspects, highlightedIds, 4),
    recommendedUserAction: compactDashboardGuidanceCopy(actionGuidance?.nextMove ?? actionGuidance?.readableInterpretation?.nextMove) ?? "先停，或只用一句短訊息試一次。",
    stopMarkers: blockedActions.length
      ? blockedActions.map((action, index) => ({
          aspectId: pressureAspect?.id,
          id: `action-stop-${action}`,
          label: BLOCKED_ACTION_SUMMARY_LABELS[action] ?? "先不要加壓",
          planetId: selectedPlanetForAspect(visualModel, pressureAspect) ?? selectedPlanetForPoint(visualModel, index === 0 ? "Saturn" : "Mars", "person_a"),
          tone: "stop" as const
        }))
      : stopMarkersForPressureAspects(visualModel, selectedAspects, "先停"),
    technicalNotes: [
      landmine
        ? {
            body: landmine.whatToDoInstead,
            label: landmine.title,
            tone: "stop"
          }
        : undefined,
      guide
        ? {
            body: guide.body,
            label: guide.title,
            tone: "support"
          }
        : undefined,
      safeAspect ? technicalAspectNote(safeAspect, "安全開口") : { body: "如果沒有明顯修復線，就把下一步縮到最小，不急著談全部關係。", label: "安全開口", tone: "neutral" },
      pressureAspect ? technicalAspectNote(pressureAspect, "停止線") : { body: "目前先用現實狀態當停止線，不把等待當成答案。", label: "停止線", tone: "stop" }
    ].filter((note): note is VisualCompanionNote => Boolean(note)).slice(0, 4),
    timingCertainty: "not_applicable",
    version: "visual-companion-plan-v1",
    whatThisDoesNotProve: boundary
  };
}

function buildSceneAspects(aspects: VisualAspect[], visualCompanionPlan: VisualCompanionPlan): VisualAspectRender[] {
  if (visualCompanionPlan.mode === "personal-systems") return [];
  const highlightedIds = new Set(visualCompanionPlan.highlightAspectIds);
  return combineAspectsByPair(
    aspects.filter((aspect) => highlightedIds.has(aspect.id)),
    visualCompanionPlan.mode === "mechanics-lanes"
  );
}

function combineAspectsByPair(aspects: VisualAspect[], useRelationshipFitLineColor = false): VisualAspectRender[] {
  return groupAspectsByDirectedPair(aspects).map((group) => {
    const primary = group[0];
    const combinedCategories = orderedAspectCategories(group.map((aspect) => aspect.category));
    return {
      ...primary,
      body: group.map((aspect) => aspect.body).filter(Boolean).join(" "),
      category: combinedCategories[0] ?? primary.category,
      combinedCategories,
      combinedMeaning: aspectCategoryMeaning(combinedCategories),
      id: group.map((aspect) => aspect.id).join("+"),
      lineColorMode: useRelationshipFitLineColor ? "relationship-fit" : "category",
      relationLabel: combinedCategories.length > 1 ? aspectCategoryMeaning(combinedCategories) : primary.relationLabel,
      sourceAspectIds: group.map((aspect) => aspect.id),
      strength: Math.max(...group.map((aspect) => aspect.strength)),
      visualRole: "highlight"
    };
  });
}

function groupAspectsByDirectedPair(aspects: VisualAspect[]) {
  const groups = new Map<string, VisualAspect[]>();
  aspects.forEach((aspect) => {
    const key = directedAspectPairKey(aspect);
    const group = groups.get(key) ?? [];
    group.push(aspect);
    groups.set(key, group);
  });
  return [...groups.values()];
}

function directedAspectPairKey(aspect: Pick<VisualAspect, "personAPoint" | "personBPoint">) {
  return `${aspect.personAPoint}->${aspect.personBPoint}`;
}

function selectRelationshipFitAspects(aspects: VisualAspect[]) {
  return collectUniqueAspects([
    bestAspect(aspects, { categories: ["attraction"] }),
    bestAspect(aspects, { categories: ["repair"] }),
    bestAspect(aspects, { categories: ["communication"] }),
    bestAspect(aspects, { categories: ["pressure"], contactTypes: ["hard", "conjunction"] }),
    bestAspect(aspects, { categories: ["emotionalSafety"] })
  ]).slice(0, 5);
}

function selectCoreAnswerAspects(aspects: VisualAspect[], theme?: RelationshipThemeLike, categories: AspectCategory[] = []) {
  return collectUniqueAspects([
    bestAspect(aspects, { categories: categories.includes("emotionalSafety") ? ["emotionalSafety"] : ["emotionalSafety", "repair", "attraction"] }),
    bestAspect(aspects, { categories: ["pressure"], pairKeys: theme?.pairKeys }),
    bestAspect(aspects, { categories: ["pressure"] })
  ]).slice(0, 2);
}

function selectTimingAspects(aspects: VisualAspect[], timingGuidance?: TimingGuidance, theme?: RelationshipThemeLike) {
  if (timingGuidance?.preciseDatesAvailable === false) return [];
  const signals = timingGuidance?.selectedSignals;
  const supportOrCaution = (signals ?? []).filter((signal) => signal.state === "support" || signal.state === "caution");
  if (!supportOrCaution.length) return [];

  const selected = collectUniqueAspects(
    supportOrCaution.map((signal) => {
      const point = pointForText([signal.key, signal.title, signal.body]);
      const categories: AspectCategory[] = signal.state === "caution" ? ["pressure"] : ["communication", "repair", "attraction"];
      return bestAspect(aspects, { categories, points: point ? [point] : undefined, pairKeys: theme?.pairKeys });
    })
  );
  return selected.slice(0, 2);
}

function selectActionAspects(aspects: VisualAspect[], actionMode?: string, blockedActions?: string[], theme?: RelationshipThemeLike) {
  const modeText = `${actionMode ?? ""} ${(blockedActions ?? []).join(" ")} ${theme?.actionFocus ?? ""}`;
  const pressurePoint = pointForText([modeText]) ?? "Saturn";
  const selected = collectUniqueAspects([
    bestAspect(aspects, { categories: ["pressure"], pairKeys: theme?.pairKeys, points: [pressurePoint] }),
    bestAspect(aspects, { categories: ["repair"], points: ["Mercury", "Saturn"] }),
    bestAspect(aspects, { categories: ["communication"], points: ["Mercury"] })
  ]);
  return selected.slice(0, 3);
}

function bestAspect(
  aspects: VisualAspect[],
  filters: {
    categories?: AspectCategory[];
    contactTypes?: string[];
    pairKeys?: string[];
    points?: string[];
  }
) {
  const categories = new Set(filters.categories ?? []);
  const contactTypes = new Set((filters.contactTypes ?? []).map((value) => value.toLowerCase()));
  const pairKeys = new Set((filters.pairKeys ?? []).map(normalizePairKey));
  const points = new Set((filters.points ?? []).map((point) => normalizePointForChart(point) ?? String(point)));
  return aspects
    .filter((aspect) => {
      if (categories.size && !categories.has(aspect.category)) return false;
      if (contactTypes.size && !contactTypes.has(String(aspect.contactType ?? "").toLowerCase())) return false;
      if (pairKeys.size && !pairKeys.has(normalizeAspectPairKey(aspect))) return false;
      if (points.size && !points.has(normalizePointForChart(aspect.personAPoint) ?? aspect.personAPoint) && !points.has(normalizePointForChart(aspect.personBPoint) ?? aspect.personBPoint)) return false;
      return true;
    })
    .sort((first, second) => second.strength - first.strength)[0];
}

function collectUniqueAspects(items: Array<VisualAspect | undefined>) {
  const seen = new Set<string>();
  return items.filter((item): item is VisualAspect => {
    if (!item || seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

function normalizeAspectPairKey(aspect: VisualAspect) {
  return normalizePairKey(`${aspect.personAPoint}-${aspect.personBPoint}`);
}

function normalizePairKey(value: string) {
  return value
    .replace("->", "-")
    .split("-")
    .map((part) => normalizePointForChart(part) ?? part.trim())
    .filter(Boolean)
    .sort()
    .join("-");
}

function relationshipMechanicLanes(aspects: VisualAspect[]): VisualCompanionLane[] {
  const naturalIds = aspects.filter((aspect) => aspect.category === "attraction" || aspect.category === "emotionalSafety").map((aspect) => aspect.id);
  const practiceIds = aspects.filter((aspect) => aspect.category === "communication" || aspect.category === "repair").map((aspect) => aspect.id);
  const stuckIds = aspects.filter((aspect) => aspect.category === "pressure").map((aspect) => aspect.id);
  const lanes: VisualCompanionLane[] = [
    { aspectIds: naturalIds, id: "natural", label: "自然牽動", tone: "attraction" },
    { aspectIds: practiceIds, id: "practice", label: "需要說清楚", tone: "repair" },
    { aspectIds: stuckIds, id: "stuck", label: "壓力觸發", tone: "pressure" }
  ];
  return lanes.filter((lane) => lane.aspectIds.length > 0);
}

function relationshipLaneExplanation(lane: VisualCompanionLane) {
  if (lane.id === "natural") {
    return "你們仍有能自然靠近、比較容易被彼此接住的位置；連結感要放回日常互動裡延續。";
  }
  if (lane.id === "practice") {
    return "需要放慢練習的是說話方式：短一點、清楚一點，對方才比較有空間接住。";
  }
  return "壓力一被觸發，越急著推進越容易讓互動變重，所以要先讓壓力降下來。";
}

function relationshipAspectTechnicalNotes(aspects: VisualAspect[]) {
  return groupAspectsByDirectedPair(aspects).map((group) => {
    if (group.length === 1) return relationshipFitTechnicalAspectNote(group[0]);
    return combinedTechnicalAspectNote(group);
  });
}

function combinedTechnicalAspectNote(group: VisualAspect[]): VisualCompanionNote {
  const primary = group[0];
  const categories = orderedAspectCategories(group.map((aspect) => aspect.category));
  const meaning = aspectCategoryMeaning(categories);
  return {
    body: `${ownerPointLabel("person_a", primary.personAPoint)}和${ownerPointLabel("person_b", primary.personBPoint)}形成${primary.aspectLabel}。${combinedAspectMeaning(categories)}`,
    label: meaning,
    tone: aspectCategoryTone(categories)
  };
}

function relationshipFitTechnicalAspectNote(aspect: VisualAspect, label = ASPECT_CATEGORY_LABELS[aspect.category] ?? "合盤訊號"): VisualCompanionNote {
  const roleTone = aspect.category === "pressure" ? "caution" : aspect.category === "repair" || aspect.category === "communication" ? "support" : "neutral";
  return {
    body: `${ownerPointLabel("person_a", aspect.personAPoint)}和${ownerPointLabel("person_b", aspect.personBPoint)}形成${aspect.aspectLabel}。${relationshipFitAspectMeaning(aspect)}`,
    label,
    tone: roleTone
  };
}

function technicalAspectNote(aspect: VisualAspect, label = ASPECT_CATEGORY_LABELS[aspect.category] ?? "合盤訊號"): VisualCompanionNote {
  const roleTone = aspect.category === "pressure" ? "caution" : aspect.category === "repair" || aspect.category === "communication" ? "support" : "neutral";
  return {
    body: `${ownerPointLabel("person_a", aspect.personAPoint)}和${ownerPointLabel("person_b", aspect.personBPoint)}形成${aspect.aspectLabel}。${simpleAspectMeaning(aspect)}`,
    label,
    tone: roleTone
  };
}

function simpleAspectMeaning(aspect: VisualAspect) {
  if (aspect.category === "attraction") {
    return "這條玫瑰線看自然牽動：有被對方點到、被吸引的位置，先看日常互動能不能穩定延續。";
  }
  if (aspect.category === "emotionalSafety") {
    return "這條冰藍線看安全感：哪裡比較容易被安撫，也看哪裡容易被不安放大。";
  }
  if (aspect.category === "communication") {
    return "這條青藍線看說話方式：適合把話說短、說清楚，不適合一次追問全部答案。";
  }
  if (aspect.category === "repair") {
    return "這條薄荷線看修復位置：有機會用比較輕、可退場的方式接話，但仍要看對方是否自然回應。";
  }
  return "這條橘紅線看壓力和停止線：越急著推進，越容易讓互動變重或變防衛。";
}

function relationshipFitAspectMeaning(aspect: VisualAspect) {
  if (aspect.category === "attraction") {
    return "自然牽動會顯示彼此被點到、被吸引的位置，也要看日常互動能不能穩定延續。";
  }
  if (aspect.category === "emotionalSafety") {
    return "安全感會顯示哪裡比較容易被安撫，以及哪裡容易把不安放大。";
  }
  if (aspect.category === "communication") {
    return "說話方式適合短而清楚，不適合一次追問全部答案。";
  }
  if (aspect.category === "repair") {
    return "修復可以從比較輕、能自然停下的方式接話，但仍要看對方是否自然回應。";
  }
  return "壓力和停止線很清楚：越急著推進，越容易讓互動變重或讓對方先保護自己。";
}

function combinedAspectMeaning(categories: AspectCategory[]) {
  const meaning = aspectCategoryMeaning(categories);
  if (categories.includes("attraction") && categories.includes("repair")) {
    return `這條合盤線同時標到${meaning}：同一組星體既帶來吸引，也提供比較容易重新接話的位置；閱讀上只把它當關係機制，不當成復合保證。`;
  }
  return `這條合盤線同時標到${meaning}：同一組星體被多個主題使用，所以圖上合併顯示，避免把同一個證據重複計算。`;
}

function aspectCategoryTone(categories: AspectCategory[]): VisualCompanionNote["tone"] {
  if (categories.includes("pressure")) return "caution";
  if (categories.includes("repair") || categories.includes("communication") || categories.includes("emotionalSafety")) return "support";
  return "neutral";
}

function aspectCategoryMeaning(categories: AspectCategory[]) {
  return categories.map((category) => ASPECT_COLOR_GUIDE[category]?.meaning ?? ASPECT_CATEGORY_LABELS[category]).join(" + ");
}

function readablePrecisionNote(data: CompleteRelationshipResultViewModel) {
  const rawNote = data.relationshipProfiles?.precisionWarnings[0] ?? data.westernRelationshipCaseFile?.houseOverlayLayer?.reason ?? "";
  if (/birth_time|noon fallback|date_noon_fallback|time-sensitive/i.test(rawNote)) {
    return "出生時間不完整時，會避開上升、宮位與其他時間敏感結論；這些只作背景，不拿來下精準判斷。";
  }
  if (/house overlay|not wired|calculation/i.test(rawNote)) {
    return "目前還沒有合盤宮位覆蓋計算，所以宮位只當背景，不拿來做精準關係結論。";
  }
  if (/[a-z_]/i.test(rawNote)) {
    return "出生資料精度不足時，時間敏感的星盤訊號只作背景，不拿來下精準結論。";
  }
  return rawNote || "出生時間不足時，宮位和角度只能當背景，不用拿來下精準結論。";
}

function compactDashboardGuidanceCopy(value?: string | null) {
  const clean = stringValue(value)
    .replace(/同時因為合盤重複主題是「[^」]+」，行動建議要先服務這個模式，而不是只看你想不想聯絡。/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return clean || undefined;
}

function timingWeatherNotes(signals: TimingSignal[]): VisualCompanionNote[] {
  const fallbackSignals: TimingSignal[] = [
    { body: "看話能不能說清楚，適合短句，不適合長篇追問。", key: "mercury", state: "none", title: "水星：話能不能說清楚" },
    { body: "看語氣能不能放柔軟，不用把喜歡直接推成承諾。", key: "venus", state: "none", title: "金星：語氣能不能變柔和" },
    { body: "看會不會太急，越急越要縮小動作。", key: "mars", state: "none", title: "火星：會不會太急" },
    { body: "看界線和壓力是否變硬，壓力高時先不要逼答案。", key: "saturn", state: "none", title: "土星：邊界會不會變硬" },
    { body: "看短期情緒起伏，不把一時焦慮當成最終答案。", key: "moon", state: "none", title: "月亮：短期情緒起伏" }
  ];
  const sourceSignals = signals.length ? signals : fallbackSignals;
  return sourceSignals.slice(0, 5).map((signal) => {
    const point = pointForTimingNote(signal.key, signal.title, signal.body);
    return {
      body: signal.body,
      label: signal.title,
      pointColor: point ? POINT_META[point]?.color : undefined,
      tone: signal.state === "caution" ? "caution" : signal.state === "support" ? "support" : "neutral"
    };
  });
}

function pointForTimingNote(key?: string, title?: string, body?: string) {
  const explicit = `${key ?? ""} ${title ?? ""}`.toLowerCase();
  if (/mercury|水星/.test(explicit)) return "Mercury";
  if (/venus|金星/.test(explicit)) return "Venus";
  if (/mars|火星/.test(explicit)) return "Mars";
  if (/saturn|土星/.test(explicit)) return "Saturn";
  if (/moon|月亮/.test(explicit)) return "Moon";
  return pointForText([key, title, body]);
}

function ownerPointLabel(role: NeedRole, point: string) {
  return `${role === "person_a" ? "你的" : "對方的"}${pointLabelFor(point)}`;
}

function planetIdsForAspects(visualModel: VisualModel, aspects: VisualAspect[]) {
  const ids = aspects.flatMap((aspect) => [
    selectedPlanetForPoint(visualModel, aspect.personAPoint, "person_a"),
    selectedPlanetForPoint(visualModel, aspect.personBPoint, "person_b")
  ]);
  return compactIds(ids);
}

function planetIdsForPoints(visualModel: VisualModel, points: ChartPoint[], roles: NeedRole[] = ["person_a", "person_b"]) {
  return compactIds(points.flatMap((point) => roles.map((role) => selectedPlanetForPoint(visualModel, point, role))));
}

function mutedAspectIds(aspects: VisualAspect[], highlightedIds: string[], maxCount: number) {
  const highlighted = new Set(highlightedIds);
  return aspects
    .filter((aspect) => !highlighted.has(aspect.id))
    .slice(0, maxCount)
    .map((aspect) => aspect.id);
}

function stopMarkersForPressureAspects(visualModel: VisualModel, aspects: VisualAspect[], label: string): VisualCompanionStopMarker[] {
  return aspects
    .filter((aspect) => aspect.category === "pressure")
    .slice(0, 2)
    .map((aspect, index) => ({
      aspectId: aspect.id,
      id: `pressure-stop-${index + 1}`,
      label,
      planetId: selectedPlanetForAspect(visualModel, aspect),
      tone: "caution"
    }));
}

function compactIds(ids: Array<string | undefined>) {
  const seen = new Set<string>();
  return ids.filter((id): id is string => {
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

function compactPoints(points: Array<ChartPoint | undefined>) {
  const seen = new Set<ChartPoint>();
  return points.filter((point): point is ChartPoint => {
    if (!point || seen.has(point)) return false;
    seen.add(point);
    return true;
  });
}

function visualCompanionFieldTrace(plan: VisualCompanionPlan) {
  const requiredFields: Array<keyof VisualCompanionPlan> = [
    "focusQuestion",
    "highlightPlanetIds",
    "highlightAspectIds",
    "mutedAspectIds",
    "stopMarkers",
    "recommendedUserAction",
    "whatThisDoesNotProve"
  ];
  return requiredFields.filter((field) => Object.prototype.hasOwnProperty.call(plan, field)).join(",");
}

function categoriesInAspectOrder(aspects: Array<VisualAspect | VisualAspectRender>) {
  const categories = new Set<AspectCategory>();
  aspects.forEach((aspect) => {
    const combinedCategories = "combinedCategories" in aspect ? aspect.combinedCategories : [];
    const sourceCategories = combinedCategories.length ? combinedCategories : [aspect.category];
    sourceCategories.forEach((category) => categories.add(category));
  });
  return ASPECT_CATEGORIES.filter((category) => categories.has(category));
}

function orderedAspectCategories(categories: Iterable<AspectCategory>) {
  const categorySet = new Set(categories);
  return ASPECT_CATEGORIES.filter((category) => categorySet.has(category));
}

type AspectLegendItem = {
  color: string;
  key: string;
  lineLabel: string;
  meaning: string;
};

function aspectLegendItems(aspects: VisualAspectRender[]): AspectLegendItem[] {
  if (aspects.some((aspect) => aspect.lineColorMode === "relationship-fit")) {
    return [
      {
        color: RELATIONSHIP_FIT_LINE_COLOR,
        key: "relationship-fit",
        lineLabel: RELATIONSHIP_FIT_LINE_LABEL,
        meaning: RELATIONSHIP_FIT_LINE_MEANING
      }
    ];
  }

  let combinedItem: AspectLegendItem | undefined;
  const seen = new Set<string>();
  const items: AspectLegendItem[] = [];

  aspects.forEach((aspect) => {
    const categories = aspect.combinedCategories.length ? aspect.combinedCategories : [aspect.category];
    if (categories.length > 1) {
      if (!combinedItem) {
        combinedItem = {
          color: COMBINED_ASPECT_LINE_COLOR,
          key: "combined",
          lineLabel: COMBINED_ASPECT_LINE_LABEL,
          meaning: COMBINED_ASPECT_LEGEND_MEANING
        };
        items.push(combinedItem);
      }
      return;
    }

    const category = categories[0];
    if (seen.has(category)) return;
    seen.add(category);
    const guide = ASPECT_COLOR_GUIDE[category];
    items.push({
      color: ASPECT_LINE_COLORS[category],
      key: category,
      lineLabel: guide.lineLabel,
      meaning: guide.meaning
    });
  });

  return items;
}

function AspectColorLegend({ aspects }: { aspects: VisualAspectRender[] }) {
  const items = aspectLegendItems(aspects);
  if (!items.length) return null;

  return (
    <div className="aspect-color-legend" aria-label="目前可見線色">
      {items.map((item) => {
        return (
          <span key={item.key}>
            <i style={{ backgroundColor: item.color, boxShadow: `0 0 12px ${item.color}` }} aria-hidden="true" />
            {item.lineLabel}：{item.meaning}
          </span>
        );
      })}
    </div>
  );
}

function VisualCompanionPlanPanel({ plan }: { plan: VisualCompanionPlan }) {
  return (
    <div className="visual-companion-plan" data-visual-companion-mode={plan.mode}>
      <p className="visual-companion-focus">{cleanDashboardCopy(plan.focusQuestion)}</p>
      <div className="visual-companion-notes" aria-label="星盤技術說明">
        {plan.technicalNotes.slice(0, 5).map((note, index) => (
          <article className={`companion-note-${note.tone ?? "neutral"}`} key={`${note.label}-${index}`}>
            <strong className={note.pointColor ? "has-companion-note-color" : undefined}>
              {note.pointColor ? (
                <i
                  className="companion-note-color-dot"
                  style={{ backgroundColor: note.pointColor, boxShadow: `0 0 12px ${note.pointColor}` }}
                  aria-hidden="true"
                />
              ) : null}
              <span>{cleanDashboardCopy(note.label)}</span>
            </strong>
            <p>{cleanDashboardCopy(note.body)}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function selectedPlanetForAspect(visualModel: VisualModel, aspect?: VisualAspect) {
  if (!aspect) return undefined;
  return (
    selectedPlanetForPoint(visualModel, aspect.personAPoint, "person_a") ??
    selectedPlanetForPoint(visualModel, aspect.personBPoint, "person_b") ??
    selectedPlanetForPoint(visualModel, aspect.personAPoint) ??
    selectedPlanetForPoint(visualModel, aspect.personBPoint)
  );
}

function selectedPlanetForPoint(visualModel: VisualModel, point?: unknown, role?: NeedRole) {
  const chartPoint = normalizePointForChart(point);
  if (!chartPoint) return undefined;

  if (role) {
    return visualModel.relationshipPlanets.find((planet) => planet.role === role && planet.point === chartPoint)?.id;
  }

  return (
    visualModel.personAPlanets.find((planet) => planet.point === chartPoint)?.id ??
    visualModel.relationshipPlanets.find((planet) => planet.point === chartPoint)?.id
  );
}

function relationshipThemeFrom(value: unknown): RelationshipThemeLike | undefined {
  if (!value || typeof value !== "object") return undefined;
  const record = value as Record<string, unknown>;
  const themeKey = stringValue(record.themeKey);
  const label = stringValue(record.label);
  if (!themeKey && !label) return undefined;

  return {
    actionFocus: stringValue(record.actionFocus),
    answerFocus: stringValue(record.answerFocus),
    doesNotProve: stringValue(record.doesNotProve),
    label,
    pairKeys: stringArray(record.pairKeys),
    themeKey,
    timingFocus: stringValue(record.timingFocus)
  };
}

function categoriesForEvidenceKeys(keys?: unknown, themeKey?: unknown, fallback: AspectCategory[] = []) {
  const categories = new Set<AspectCategory>();
  [...stringArray(keys), stringValue(themeKey)].filter(Boolean).forEach((token) => {
    addCategoriesFromToken(token, categories);
  });
  return orderedCategories(categories, fallback);
}

function categoriesForTimingSignals(signals?: TimingSignal[], themeKey?: unknown) {
  const categories = new Set<AspectCategory>(categoriesForEvidenceKeys(undefined, themeKey));
  (signals ?? []).forEach((signal) => {
    addCategoriesFromToken([signal.key, signal.title, signal.body, signal.state].join(" "), categories);
    if (signal.state === "support") categories.add("repair");
    if (signal.state === "caution") categories.add("pressure");
  });
  return orderedCategories(categories, ["communication", "repair", "pressure"]);
}

function addCategoriesFromToken(value: unknown, categories: Set<AspectCategory>) {
  const token = stringValue(value).toLowerCase();
  if (!token) return;

  if (/emotional[_-]?safety|moon|安全|情緒|moonweather|moon[_-]?sign|luminary/.test(token)) {
    categories.add("emotionalSafety");
  }
  if (/communication[_-]?repair|communication|mercury|訊息|聯絡|溝通|說話|回覆|對話|timingmercurycommunication|contact[_-]?status/.test(token)) {
    categories.add("communication");
  }
  if (/repair|gottman|bid|reply|修復|接話|回應|contact[_-]?reducer|timingvenussoftening/.test(token)) {
    categories.add("repair");
  }
  if (/pressure|saturn|boundary|界線|邊界|壓力|防衛|停止|blocked|no[_-]?contact|contact[_-]?situation|emotional[_-]?risk|action[_-]?conflict|mars|衝突/.test(token)) {
    categories.add("pressure");
  }
  if (/attraction|venus|affection|吸引|喜歡|好感|金星|moonvenus|relationship[_-]?potential|attraction[_-]?pursuit|pursuit/.test(token)) {
    categories.add("attraction");
  }
}

function orderedCategories(categories: Set<AspectCategory>, fallback: AspectCategory[]) {
  const ordered = ASPECT_CATEGORIES.filter((category) => categories.has(category));
  return ordered.length ? ordered : fallback;
}

function pointForText(parts: unknown[]) {
  const text = parts.map(stringValue).filter(Boolean).join(" ").toLowerCase();
  if (!text) return undefined;

  if (/saturn|土星|界線|邊界|停止線|壓力|退縮|防衛|blocked|no[_ -]?contact|冷處理|承諾|共同空間|shared/.test(text)) {
    return "Saturn";
  }
  if (/mercury|水星|訊息|聯絡|溝通|說話|回覆|回應|修復語言|對話|contact|reply|message/.test(text)) {
    return "Mercury";
  }
  if (/moon|月亮|情緒|安全感|照顧|穩定回應|感受/.test(text)) {
    return "Moon";
  }
  if (/venus|金星|柔和|喜歡|好感|吸引|靠近|soft|affection/.test(text)) {
    return "Venus";
  }
  if (/mars|火星|急|衝突|推進|行動|加速|pursuit/.test(text)) {
    return "Mars";
  }
  if (/desc|下降|第\s*7\s*宮|伴侶期待|關係期待/.test(text)) {
    return "Desc";
  }

  return undefined;
}

function pointForTimingSignals(signals?: TimingSignal[]) {
  const prioritizedSignals = [
    ...(signals ?? []).filter((signal) => signal.state === "support"),
    ...(signals ?? []).filter((signal) => signal.state === "caution"),
    ...(signals ?? []).filter((signal) => signal.state !== "support" && signal.state !== "caution")
  ];

  for (const signal of prioritizedSignals) {
    const point = pointForText([signal.key, signal.title, signal.body, signal.state]);
    if (point) return point;
  }

  return undefined;
}

function timingStateLabel(state?: string) {
  if (state === "support") return "比較支持";
  if (state === "caution") return "需要放慢";
  return "先觀察";
}

function blockedActionSummary(blockedActions?: string[]) {
  const labels = (blockedActions ?? [])
    .slice(0, 3)
    .map((action) => BLOCKED_ACTION_SUMMARY_LABELS[action] ?? "")
    .filter(Boolean);

  return labels.length ? `先不要：${labels.join("、")}。` : "";
}

function normalizePointForChart(value?: unknown): ChartPoint | undefined {
  const token = stringValue(value).toLowerCase();
  if (!token) return undefined;

  if (/moon|月亮/.test(token)) return "Moon";
  if (/mercury|水星/.test(token)) return "Mercury";
  if (/venus|金星/.test(token)) return "Venus";
  if (/mars|火星/.test(token)) return "Mars";
  if (/saturn|土星/.test(token)) return "Saturn";
  if (/desc|下降/.test(token)) return "Desc";
  return undefined;
}

function stringArray(value?: unknown) {
  if (!Array.isArray(value)) return [];
  return value.map(stringValue).filter(Boolean);
}

function stringValue(value?: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function buildVisualModel(data: CompleteRelationshipResultViewModel): VisualModel {
  const caseFile = data.westernRelationshipCaseFile;
  const profiles = data.relationshipProfiles;
  const personAPlanets = (caseFile?.identityLayer.personA.needs ?? []).map((need) =>
    buildPlanet(need, "person_a", "你", profiles?.personA.cards.find((card) => card.point === need.point))
  );
  const personBPlanets = (caseFile?.identityLayer.personB.needs ?? []).map((need) =>
    buildPlanet(need, "person_b", "對方", profiles?.personB.cards.find((card) => card.point === need.point))
  );
  const relationshipPlanets = [...personAPlanets, ...personBPlanets];
  const aspects = flattenAspects(caseFile?.synastryLayer);
  const pointPositions = Object.fromEntries(
    relationshipPlanets.map((planet) => [planet.id, positionForPlanet(planet)])
  );
  const defaultSelectedId =
    personAPlanets.find((planet) => planet.point === "Moon")?.id ??
    personAPlanets[0]?.id ??
    relationshipPlanets[0]?.id ??
    "";

  return {
    aspects,
    defaultSelectedId,
    personAPlanets,
    personBPlanets,
    pointPositions,
    relationshipPlanets
  };
}

function buildPlanet(
  need: WesternNeedPoint,
  role: NeedRole,
  ownerLabel: "你" | "對方",
  profileCard?: RelationshipProfileCard
): VisualPlanet {
  const meta = POINT_META[need.point];
  const signIndex = signIndexFor(need.sign);
  const roleOffset = role === "person_a" ? -4 : 4;
  const angleDeg = signIndex * 30 - 90 + 15 + meta.offset + roleOffset;
  const orbitLevel = meta.orbitLevel + (role === "person_b" ? 0.28 : 0);

  return {
    id: `${role}-${need.point}`,
    angleDeg,
    body: profileCard?.readableInterpretation?.body ?? profileCard?.naturalResponse ?? need.meaning,
    color: role === "person_b" ? tintForPartner(meta.color) : meta.color,
    confidence: need.confidence,
    elementLabel: profileCard?.elementLabel,
    house: need.house,
    meaning: need.meaning,
    modalityLabel: profileCard?.modalityLabel,
    nextMove: profileCard?.readableInterpretation?.nextMove,
    orbitLevel,
    orbitRadius: 1.65 + orbitLevel * 0.46,
    ownerLabel,
    placement: profileCard?.placement ?? need.label,
    point: need.point,
    pointLabel: meta.label,
    role,
    sign: normalizeSign(need.sign),
    signLabel: displaySign(need.sign),
    stuckPattern: profileCard?.readableInterpretation?.stuckPattern ?? profileCard?.tensionPattern,
    texture: PLANET_TEXTURES[need.point]
  };
}

function flattenAspects(synastryLayer?: WesternRelationshipCaseFile["synastryLayer"]) {
  if (!synastryLayer) return [];
  return (Object.entries(synastryLayer) as Array<[WesternAspectEvidence["category"], WesternAspectEvidence[]]>)
    .flatMap(([category, items]) =>
      items.map((item) => ({
        body: item.emotionalMeaning,
        category,
        contactType: item.contactType,
        id: item.id,
        label: `${pointLabelFor(String(item.personAPoint))}-${pointLabelFor(String(item.personBPoint))}`,
        orb: item.orb,
        personAPoint: item.personAPoint,
        personBPoint: item.personBPoint,
        relationLabel: ASPECT_CATEGORY_LABELS[category] ?? "合盤訊號",
        aspectLabel: item.aspectLabel,
        strength: item.strength
      }))
    )
    .sort((first, second) => second.strength - first.strength);
}

function CosmicThreeCanvas({
  aspects,
  autoRotate,
  isExplorerOpen,
  onSelectPlanet,
  planets,
  pointPositions,
  sceneTone,
  selectedId,
  visualCompanionPlan,
  showZodiac,
  zoom
}: {
  aspects: VisualAspectRender[];
  autoRotate: boolean;
  isExplorerOpen: boolean;
  onSelectPlanet: (id: string) => void;
  planets: VisualPlanet[];
  pointPositions: Record<string, PointPosition>;
  sceneTone: ChartSceneTone;
  selectedId?: string;
  visualCompanionPlan: VisualCompanionPlan;
  showZodiac: boolean;
  zoom: number;
}) {
  return (
    <Canvas
      camera={{ fov: isExplorerOpen ? 38 : 42, position: [0, 1.1 / zoom, 7.4 / zoom] }}
      className="immersive-cosmic-canvas"
      dpr={[1, 2]}
      gl={{ alpha: false, antialias: true, preserveDrawingBuffer: true }}
      onCreated={({ camera, gl, invalidate }) => {
        gl.setClearColor("#020714", 1);
        gl.setClearAlpha(1);
        gl.clear();
        camera.lookAt(0, 0.1, 0);
        invalidate();
      }}
    >
      <color attach="background" args={["#020714"]} />
      <fog attach="fog" args={["#020714", 8.5, 18]} />
      <ambientLight intensity={0.62} />
      <pointLight color="#ffd78a" intensity={48} position={[0, 1.1, 0]} />
      <pointLight color="#79d4ff" intensity={14} position={[-4, 3, 4]} />
      <pointLight color="#f5b65d" intensity={9} position={[4, 1.2, -5]} />
      <FocusCameraRig isExplorerOpen={isExplorerOpen} pointPositions={pointPositions} selectedId={selectedId} zoom={zoom} />
      <RenderPresenceAnchor />
      <Suspense fallback={null}>
        <CosmicSceneGroup
          aspects={aspects}
          autoRotate={autoRotate}
          planets={planets}
          pointPositions={pointPositions}
          sceneTone={sceneTone}
          selectedId={selectedId}
          visualCompanionPlan={visualCompanionPlan}
          showZodiac={showZodiac}
          onSelectPlanet={onSelectPlanet}
        />
      </Suspense>
    </Canvas>
  );
}

function FocusCameraRig({
  isExplorerOpen,
  pointPositions,
  selectedId,
  zoom
}: {
  isExplorerOpen: boolean;
  pointPositions: Record<string, PointPosition>;
  selectedId?: string;
  zoom: number;
}) {
  const { camera } = useThree();
  const targetPosition = useMemo(() => new Vector3(), []);
  const lookTarget = useMemo(() => new Vector3(), []);

  useFrame(() => {
    const focus = selectedId ? pointPositions[selectedId] : undefined;
    const depth = isExplorerOpen ? 6.15 : 7.35;
    const height = isExplorerOpen ? 4.85 : 5.7;
    targetPosition.set(
      focus ? focus.x * 0.18 : 0,
      height / zoom,
      depth / zoom + (focus ? focus.z * 0.08 : 0)
    );
    lookTarget.set(focus ? focus.x * 0.17 : 0, focus ? 0.18 : 0.05, focus ? focus.z * 0.17 : 0);
    camera.position.lerp(targetPosition, 0.055);
    camera.lookAt(lookTarget);
  });

  return null;
}

function RenderPresenceAnchor() {
  return (
    <group position={[0, 0.08, 0]}>
      <mesh>
        <sphereGeometry args={[0.2, 32, 32]} />
        <meshBasicMaterial color="#ffe8a7" toneMapped={false} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.16, 0.005, 8, 160]} />
        <meshBasicMaterial color="#f4c56f" transparent opacity={0.34} blending={AdditiveBlending} depthWrite={false} toneMapped={false} />
      </mesh>
    </group>
  );
}

function CosmicSceneGroup({
  aspects,
  autoRotate,
  onSelectPlanet,
  planets,
  pointPositions,
  sceneTone,
  selectedId,
  visualCompanionPlan,
  showZodiac
}: {
  aspects: VisualAspectRender[];
  autoRotate: boolean;
  onSelectPlanet: (id: string) => void;
  planets: VisualPlanet[];
  pointPositions: Record<string, PointPosition>;
  sceneTone: ChartSceneTone;
  selectedId?: string;
  visualCompanionPlan: VisualCompanionPlan;
  showZodiac: boolean;
}) {
  const groupRef = useRef<Group>(null);

  useFrame((_, delta) => {
    if (!groupRef.current || !autoRotate) return;
    groupRef.current.rotation.y += delta * 0.085;
  });

  return (
    <>
      <CinematicBackdrop autoRotate={autoRotate} />
      <group ref={groupRef} rotation={[-0.3, 0, 0]}>
        <StarField />
        <GalaxyDust />
        <CinematicParticleVeil />
        <CentralSun />
        <OrbitRings showZodiac={showZodiac} subdued={aspects.length > 0} />
        <SceneFocusRings tone={sceneTone} />
        <AspectLines aspects={aspects} pointPositions={pointPositions} />
        <StopMarkers markers={visualCompanionPlan.stopMarkers} pointPositions={pointPositions} />
        {planets.map((planet) => (
          <PlanetMesh
            isCompanionHighlighted={visualCompanionPlan.highlightPlanetIds.includes(planet.id)}
            isSelected={planet.id === selectedId}
            key={planet.id}
            onSelect={onSelectPlanet}
            planet={planet}
          />
        ))}
      </group>
    </>
  );
}

function useCosmicTexture(path: string) {
  const texture = useLoader(TextureLoader, path);
  useMemo(() => {
    texture.colorSpace = SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }, [texture]);
  return texture;
}

function useTextTexture(text: string, tone: "planet" | "selected" | "zodiac") {
  const texture = useMemo(() => {
    if (typeof document === "undefined") return undefined;

    const canvas = document.createElement("canvas");
    canvas.width = tone === "zodiac" ? 256 : 320;
    canvas.height = tone === "zodiac" ? 96 : 112;
    const context = canvas.getContext("2d");
    if (!context) return undefined;

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font =
      tone === "zodiac"
        ? '700 34px "Noto Serif TC", "Songti TC", serif'
        : '700 30px "Noto Sans TC", "PingFang TC", sans-serif';
    context.shadowBlur = tone === "selected" ? 20 : 14;
    context.shadowColor = tone === "planet" ? "rgba(96, 205, 255, 0.86)" : "rgba(245, 192, 95, 0.92)";
    context.fillStyle = tone === "planet" ? "#dcefff" : "#f5d184";

    if (tone !== "zodiac") {
      const gradient = context.createLinearGradient(0, 0, canvas.width, 0);
      gradient.addColorStop(0, "rgba(2, 8, 20, 0)");
      gradient.addColorStop(0.18, "rgba(2, 8, 20, 0.58)");
      gradient.addColorStop(0.82, "rgba(2, 8, 20, 0.58)");
      gradient.addColorStop(1, "rgba(2, 8, 20, 0)");
      context.fillStyle = gradient;
      context.fillRect(0, 24, canvas.width, 64);
      context.fillStyle = tone === "planet" ? "#dcefff" : "#f5d184";
    }

    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const map = new CanvasTexture(canvas);
    map.colorSpace = SRGBColorSpace;
    map.minFilter = LinearFilter;
    map.magFilter = LinearFilter;
    map.needsUpdate = true;
    return map;
  }, [text, tone]);

  useEffect(() => {
    return () => {
      texture?.dispose();
    };
  }, [texture]);

  return texture;
}

function TextSprite({
  opacity = 0.92,
  position,
  scale,
  text,
  tone
}: {
  opacity?: number;
  position: [number, number, number];
  scale: [number, number, number];
  text: string;
  tone: "planet" | "selected" | "zodiac";
}) {
  const texture = useTextTexture(text, tone);
  return (
    <sprite position={position} scale={scale}>
      <spriteMaterial map={texture} transparent opacity={opacity} depthWrite={false} depthTest toneMapped={false} />
    </sprite>
  );
}

function CinematicBackdrop({ autoRotate }: { autoRotate: boolean }) {
  const goldAura = useCosmicTexture(COSMIC_ASSETS.auraGold);
  const blueAura = useCosmicTexture(COSMIC_ASSETS.auraBlue);
  const groupRef = useRef<Group>(null);

  useFrame((_, delta) => {
    if (!groupRef.current || !autoRotate) return;
    groupRef.current.rotation.z += delta * 0.006;
  });

  return (
    <group ref={groupRef} position={[0, 1.05, -8.4]}>
      <sprite position={[-4.8, 0.7, 0.15]} scale={[3.8, 3.8, 1]}>
        <spriteMaterial map={goldAura} color="#f6c46d" transparent opacity={0.26} blending={AdditiveBlending} depthWrite={false} />
      </sprite>
      <sprite position={[4.4, -0.35, 0.2]} scale={[5.8, 3.1, 1]}>
        <spriteMaterial map={blueAura} color="#6fbfff" transparent opacity={0.16} blending={AdditiveBlending} depthWrite={false} />
      </sprite>
    </group>
  );
}

function CentralSun() {
  const coronaTexture = useCosmicTexture(COSMIC_ASSETS.sunCorona);
  const auraTexture = useCosmicTexture(COSMIC_ASSETS.auraGold);
  const mandalaTexture = useCosmicTexture(COSMIC_ASSETS.sunMandala);
  const surfaceTexture = useCosmicTexture(COSMIC_ASSETS.sunSurface);
  const groupRef = useRef<Group>(null);
  const sunMaterialRef = useRef<ShaderMaterial>(null);
  const glowMaterialRef = useRef<ShaderMaterial>(null);
  const sunUniforms = useMemo(
    () => ({
      uTexture: { value: surfaceTexture },
      uTime: { value: 0 }
    }),
    [surfaceTexture]
  );
  const glowUniforms = useMemo(
    () => ({
      uTime: { value: 0 }
    }),
    []
  );

  useFrame(({ clock }, delta) => {
    if (sunMaterialRef.current) sunMaterialRef.current.uniforms.uTime.value = clock.elapsedTime;
    if (glowMaterialRef.current) glowMaterialRef.current.uniforms.uTime.value = clock.elapsedTime;
    if (!groupRef.current) return;
    const pulse = 1 + Math.sin(clock.elapsedTime * 1.4) * 0.025;
    groupRef.current.scale.setScalar(pulse);
    groupRef.current.rotation.y += delta * 0.15;
  });

  return (
    <group ref={groupRef}>
      <mesh position={[0, 0.028, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <planeGeometry args={[2.5, 2.5]} />
        <meshBasicMaterial
          map={mandalaTexture}
          transparent
          opacity={0.92}
          blending={AdditiveBlending}
          depthWrite={false}
          side={DoubleSide}
          toneMapped={false}
        />
      </mesh>
      <sprite position={[0, 0.18, 0]} scale={[2.22, 2.22, 1]}>
        <spriteMaterial map={coronaTexture} color="#ffd17d" transparent opacity={0.72} blending={AdditiveBlending} depthWrite={false} />
      </sprite>
      <sprite position={[0, 0.18, 0]} scale={[3.22, 3.22, 1]}>
        <spriteMaterial map={auraTexture} color="#f6bd5f" transparent opacity={0.28} blending={AdditiveBlending} depthWrite={false} />
      </sprite>
      <mesh position={[0, 0.14, 0]}>
        <sphereGeometry args={[0.39, 56, 56]} />
        <shaderMaterial
          ref={sunMaterialRef}
          fragmentShader={SUN_GOLD_FRAGMENT_SHADER}
          toneMapped={false}
          uniforms={sunUniforms}
          vertexShader={SUN_GOLD_VERTEX_SHADER}
        />
      </mesh>
      <mesh position={[0, 0.14, 0]} scale={1.08}>
        <sphereGeometry args={[0.39, 56, 56]} />
        <shaderMaterial
          ref={glowMaterialRef}
          blending={AdditiveBlending}
          depthWrite={false}
          fragmentShader={SUN_GLOW_FRAGMENT_SHADER}
          toneMapped={false}
          transparent
          uniforms={glowUniforms}
          vertexShader={SUN_GOLD_VERTEX_SHADER}
        />
      </mesh>
      <mesh position={[0, 0.14, 0]}>
        <sphereGeometry args={[0.72, 48, 48]} />
        <meshBasicMaterial color="#ffbd58" transparent opacity={0.14} blending={AdditiveBlending} depthWrite={false} toneMapped={false} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.9, 0.008, 8, 192]} />
        <meshBasicMaterial color="#ffe09a" transparent opacity={0.72} blending={AdditiveBlending} depthWrite={false} toneMapped={false} />
      </mesh>
    </group>
  );
}

function OrbitRings({ showZodiac, subdued = false }: { showZodiac: boolean; subdued?: boolean }) {
  const zodiacWheelTexture = useCosmicTexture(COSMIC_ASSETS.zodiacWheel);
  const radii = [1.72, 2.15, 2.58, 3.02, 3.46, 3.9, 4.36];
  return (
    <group visible={showZodiac}>
      <mesh position={[0, -0.018, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <planeGeometry args={[9.55, 9.55]} />
        <meshBasicMaterial
          map={zodiacWheelTexture}
          transparent
          opacity={subdued ? 0.46 : 0.68}
          blending={AdditiveBlending}
          depthWrite={false}
          side={DoubleSide}
          toneMapped={false}
        />
      </mesh>
      {radii.map((radius, index) => (
        <mesh key={radius} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[radius, index % 2 === 0 ? 0.006 : 0.003, 6, 224]} />
          <meshBasicMaterial
            color={index % 2 === 0 ? "#f4c56f" : "#ffe2a0"}
            transparent
            opacity={subdued ? (index % 2 === 0 ? 0.2 : 0.1) : index % 2 === 0 ? 0.34 : 0.18}
            blending={AdditiveBlending}
            depthWrite={false}
            toneMapped={false}
          />
        </mesh>
      ))}
      {Array.from({ length: 12 }, (_, index) => (
        <mesh key={index} position={[0, 0.004, 0]} rotation={[Math.PI / 2, 0, (index * Math.PI) / 6]}>
          <boxGeometry args={[0.005, 4.82, 0.005]} />
          <meshBasicMaterial color="#f5c66d" transparent opacity={subdued ? 0.12 : 0.22} blending={AdditiveBlending} depthWrite={false} toneMapped={false} />
        </mesh>
      ))}
    </group>
  );
}

function SceneFocusRings({ tone }: { tone: ChartSceneTone }) {
  const toneMeta: Record<ChartSceneTone, { color: string; secondColor: string; radius: number; opacity: number }> = {
    action: { color: "#ff4568", secondColor: "#58f6b0", radius: 2.32, opacity: 0.34 },
    answer: { color: "#66a6ff", secondColor: "#ff4fd8", radius: 2.04, opacity: 0.32 },
    fit: { color: "#36e7ff", secondColor: "#ff4fd8", radius: 2.86, opacity: 0.38 },
    foundation: { color: "#66a6ff", secondColor: "#36e7ff", radius: 1.74, opacity: 0.26 },
    timing: { color: "#8bdcff", secondColor: "#d8f3ff", radius: 3.18, opacity: 0.34 }
  };
  const meta = toneMeta[tone];

  return (
    <group position={[0, 0.02, 0]} rotation={[Math.PI / 2, 0, 0]}>
      <mesh>
        <torusGeometry args={[meta.radius, 0.009, 8, 192]} />
        <meshBasicMaterial color={meta.color} transparent opacity={meta.opacity} blending={AdditiveBlending} depthWrite={false} toneMapped={false} />
      </mesh>
      <mesh>
        <torusGeometry args={[meta.radius + 0.22, 0.004, 8, 192]} />
        <meshBasicMaterial color={meta.secondColor} transparent opacity={meta.opacity * 0.62} blending={AdditiveBlending} depthWrite={false} toneMapped={false} />
      </mesh>
    </group>
  );
}

function StopMarkers({
  markers,
  pointPositions
}: {
  markers: VisualCompanionStopMarker[];
  pointPositions: Record<string, PointPosition>;
}) {
  if (!markers.length) return null;

  return (
    <group>
      {markers.slice(0, 3).map((marker, index) => {
        if (!marker.planetId) return null;
        const position = pointPositions[marker.planetId];
        if (!position) return null;
        const color = marker.tone === "stop" ? "#ff5f5f" : marker.tone === "boundary" ? "#ff8e6a" : "#ffb067";
        return (
          <group key={marker.id} position={[position.x, position.y + 0.2 + index * 0.012, position.z]}>
            <mesh rotation={[Math.PI / 2, 0, 0]}>
              <ringGeometry args={[0.24, 0.31, 36]} />
              <meshBasicMaterial color={color} transparent opacity={0.74} blending={AdditiveBlending} depthWrite={false} depthTest={false} toneMapped={false} />
            </mesh>
            <mesh rotation={[Math.PI / 2, 0, Math.PI / 4]}>
              <boxGeometry args={[0.42, 0.024, 0.012]} />
              <meshBasicMaterial color={color} transparent opacity={0.86} blending={AdditiveBlending} depthWrite={false} depthTest={false} toneMapped={false} />
            </mesh>
            <mesh rotation={[Math.PI / 2, 0, -Math.PI / 4]}>
              <boxGeometry args={[0.42, 0.024, 0.012]} />
              <meshBasicMaterial color={color} transparent opacity={0.86} blending={AdditiveBlending} depthWrite={false} depthTest={false} toneMapped={false} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function PlanetMesh({
  isCompanionHighlighted,
  isSelected,
  onSelect,
  planet
}: {
  isCompanionHighlighted: boolean;
  isSelected: boolean;
  onSelect: (id: string) => void;
  planet: VisualPlanet;
}) {
  const position = positionForPlanet(planet);
  const texture = useCosmicTexture(PLANET_TEXTURES[planet.point]);
  const saturnRingTexture = useCosmicTexture(COSMIC_ASSETS.saturnRing);
  const auraTexture = useCosmicTexture(isSelected ? COSMIC_ASSETS.auraGold : COSMIC_ASSETS.auraBlue);
  const groupRef = useRef<Group>(null);
  const beaconRef = useRef<Group>(null);
  const bodyRadius = 0.155;
  const highlightColor = planet.color;

  useFrame(({ clock }, delta) => {
    if (!groupRef.current) return;
    groupRef.current.position.y = position.y + Math.sin(clock.elapsedTime * 0.9 + planet.angleDeg) * 0.006;
    groupRef.current.scale.setScalar(1);
    groupRef.current.rotation.y += delta * (planet.role === "person_b" ? -0.2 : 0.24);
    if (beaconRef.current) {
      const beaconPulse = 1 + Math.sin(clock.elapsedTime * 2.65) * 0.07;
      beaconRef.current.rotation.y += delta * 0.64;
      beaconRef.current.scale.setScalar(beaconPulse);
    }
  });

  return (
    <group
      ref={groupRef}
      position={[position.x, position.y, position.z]}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(planet.id);
      }}
      onPointerOut={() => {
        document.body.style.cursor = "";
      }}
      onPointerOver={(event) => {
        event.stopPropagation();
        document.body.style.cursor = "pointer";
      }}
    >
      {isSelected ? (
        <group ref={beaconRef}>
          <mesh position={[0, -0.01, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[bodyRadius * 1.9, 0.012, 10, 128]} />
            <meshBasicMaterial
              color={highlightColor}
              transparent
              opacity={0.92}
              blending={AdditiveBlending}
              depthWrite={false}
              depthTest={false}
              toneMapped={false}
            />
          </mesh>
          <mesh position={[0, -0.012, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[bodyRadius * 2.48, 0.006, 8, 128]} />
            <meshBasicMaterial
              color={highlightColor}
              transparent
              opacity={0.48}
              blending={AdditiveBlending}
              depthWrite={false}
              depthTest={false}
              toneMapped={false}
            />
          </mesh>
        </group>
      ) : null}
      {isCompanionHighlighted && !isSelected ? (
        <group>
          <mesh position={[0, -0.012, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[bodyRadius * 2.12, 0.006, 8, 112]} />
            <meshBasicMaterial
              color={highlightColor}
              transparent
              opacity={0.84}
              blending={AdditiveBlending}
              depthWrite={false}
              depthTest={false}
              toneMapped={false}
            />
          </mesh>
          <mesh position={[0, -0.014, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[bodyRadius * 2.62, 0.003, 8, 112]} />
            <meshBasicMaterial
              color={highlightColor}
              transparent
              opacity={0.44}
              blending={AdditiveBlending}
              depthWrite={false}
              depthTest={false}
              toneMapped={false}
            />
          </mesh>
        </group>
      ) : null}
      <sprite scale={[isSelected ? 0.78 : 0.54, isSelected ? 0.78 : 0.54, 1]}>
        <spriteMaterial
          map={auraTexture}
          color={planet.color}
          transparent
          opacity={isSelected || isCompanionHighlighted ? 0.38 : 0.28}
          blending={AdditiveBlending}
          depthWrite={false}
          depthTest
          toneMapped={false}
        />
      </sprite>
      <mesh rotation={[0.18, planet.angleDeg / 58, -0.08]}>
        <sphereGeometry args={[bodyRadius, 48, 48]} />
        <meshStandardMaterial
          map={texture}
          color="#ffffff"
          emissive={planet.color}
          emissiveIntensity={isSelected || isCompanionHighlighted ? 0.18 : 0.08}
          roughness={planet.point === "Venus" ? 0.72 : 0.58}
          metalness={0.02}
        />
      </mesh>
      {planet.point === "Saturn" ? (
        <mesh rotation={[1.32, 0.3, 0.1]}>
          <ringGeometry args={[bodyRadius * 1.42, bodyRadius * 2.55, 96]} />
          <meshBasicMaterial
            map={saturnRingTexture}
            color="#ffe0a0"
            transparent
            opacity={0.82}
            side={DoubleSide}
            blending={AdditiveBlending}
            depthWrite={false}
            toneMapped={false}
          />
        </mesh>
      ) : null}
      <mesh>
        <sphereGeometry args={[bodyRadius * 1.75, 18, 18]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.002} depthWrite={false} />
      </mesh>
      <TextSprite
        opacity={isSelected ? 0.98 : 0.72}
        position={[0, bodyRadius + 0.12, 0]}
        scale={[isSelected ? 0.62 : 0.46, isSelected ? 0.22 : 0.16, 1]}
        text={`${planet.ownerLabel}${planet.pointLabel}`}
        tone={isSelected ? "selected" : "planet"}
      />
    </group>
  );
}

function AspectLines({
  aspects,
  pointPositions
}: {
  aspects: VisualAspectRender[];
  pointPositions: Record<string, PointPosition>;
}) {
  const lineInstances = useMemo(() => buildAspectLineInstances(aspects), [aspects]);

  return (
    <group>
      {lineInstances.map(({ aspect, duplicateCount, duplicateIndex }, index) => {
        const from = pointPositions[`person_a-${aspect.personAPoint}`];
        const to = pointPositions[`person_b-${aspect.personBPoint}`];
        if (!from || !to) return null;
        return (
          <CurvedAspectArc
            aspect={aspect}
            duplicateCount={duplicateCount}
            duplicateIndex={duplicateIndex}
            from={from}
            key={`${aspect.id}-${index}`}
            to={to}
          />
        );
      })}
    </group>
  );
}

function buildAspectLineInstances(aspects: VisualAspectRender[]) {
  const pairCounts = new Map<string, number>();
  aspects.forEach((aspect) => {
    const pairKey = `${aspect.personAPoint}->${aspect.personBPoint}`;
    pairCounts.set(pairKey, (pairCounts.get(pairKey) ?? 0) + 1);
  });

  const pairIndexes = new Map<string, number>();
  return aspects.map((aspect) => {
    const pairKey = `${aspect.personAPoint}->${aspect.personBPoint}`;
    const duplicateIndex = pairIndexes.get(pairKey) ?? 0;
    pairIndexes.set(pairKey, duplicateIndex + 1);
    return {
      aspect,
      duplicateCount: pairCounts.get(pairKey) ?? 1,
      duplicateIndex
    };
  });
}

function isCombinedAspect(aspect: VisualAspectRender) {
  return aspect.combinedCategories.length > 1;
}

function aspectLineColor(aspect: VisualAspectRender) {
  if (aspect.visualRole === "muted") return "#6f87a8";
  if (aspect.lineColorMode === "relationship-fit") return RELATIONSHIP_FIT_LINE_COLOR;
  if (isCombinedAspect(aspect)) return COMBINED_ASPECT_LINE_COLOR;
  return ASPECT_LINE_COLORS[aspect.category] ?? "#4de7ff";
}

function CurvedAspectArc({
  aspect,
  duplicateCount,
  duplicateIndex,
  from,
  to
}: {
  aspect: VisualAspectRender;
  duplicateCount: number;
  duplicateIndex: number;
  from: PointPosition;
  to: PointPosition;
}) {
  const beadGroupRef = useRef<Group>(null);
  const curve = useMemo(() => {
    const dx = to.x - from.x;
    const dz = to.z - from.z;
    const distance = Math.max(0.001, Math.hypot(dx, dz));
    const directionX = dx / distance;
    const directionZ = dz / distance;
    const perpendicularX = -dz / distance;
    const perpendicularZ = dx / distance;
    const duplicateSlot = duplicateIndex - (duplicateCount - 1) / 2;
    const lateralOffset = duplicateSlot * 0.095;
    const endpointInset = Math.min(0.165, distance * 0.12);
    const heightLift = 0.12 + Math.min(0.26, distance * 0.055) + Math.abs(duplicateSlot) * 0.035;
    const endpointLift = 0.078 + Math.abs(duplicateSlot) * 0.012;

    const start = new Vector3(
      from.x + directionX * endpointInset + perpendicularX * lateralOffset,
      from.y + endpointLift,
      from.z + directionZ * endpointInset + perpendicularZ * lateralOffset
    );
    const middle = new Vector3(
      (from.x + to.x) / 2 + perpendicularX * lateralOffset * 1.45,
      Math.max(from.y, to.y) + heightLift,
      (from.z + to.z) / 2 + perpendicularZ * lateralOffset * 1.45
    );
    const end = new Vector3(
      to.x - directionX * endpointInset + perpendicularX * lateralOffset,
      to.y + endpointLift,
      to.z - directionZ * endpointInset + perpendicularZ * lateralOffset
    );

    return new CatmullRomCurve3([start, middle, end], false, "catmullrom", 0.35);
  }, [duplicateCount, duplicateIndex, from.x, from.y, from.z, to.x, to.y, to.z]);
  const color = aspectLineColor(aspect);
  const beadPoints = useMemo(() => curve.getSpacedPoints(15), [curve]);
  const muted = aspect.visualRole === "muted";
  const combined = isCombinedAspect(aspect);
  const hairlineOpacity = muted ? 0.08 : combined ? 0.42 : 0.18 + Math.min(0.12, aspect.strength * 0.12);
  const beadOpacity = muted ? 0.18 : combined ? 0.78 : 0.54 + Math.min(0.28, aspect.strength * 0.3);
  const beadRadius = muted ? 0.009 : combined ? 0.023 : 0.014 + Math.min(0.007, aspect.strength * 0.007);
  const tubeRadius = combined ? 0.006 : 0.003;

  useFrame(({ clock }) => {
    if (!beadGroupRef.current) return;
    beadGroupRef.current.children.forEach((child, index) => {
      const mesh = child as Mesh;
      const material = mesh.material as MeshBasicMaterial | undefined;
      const edgeDistance = Math.min(index + 1, beadPoints.length - index - 2);
      const edgeFade = Math.min(1, edgeDistance / 4);
      const shimmer = 0.5 + Math.sin(clock.elapsedTime * 2.35 - index * 0.78 + duplicateIndex * 0.9) * 0.5;
      const scale = 0.72 + shimmer * 0.52;
      child.scale.setScalar(scale);
      if (material) material.opacity = beadOpacity * edgeFade * (0.34 + shimmer * 0.82);
    });
  });

  return (
    <group>
      <mesh renderOrder={20}>
        <tubeGeometry args={[curve, 48, tubeRadius, 6, false]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={hairlineOpacity}
          blending={AdditiveBlending}
          depthWrite={false}
          depthTest={false}
          toneMapped={false}
        />
      </mesh>
      <group ref={beadGroupRef}>
        {beadPoints.slice(1, -1).map((point, index) => {
          const edgeDistance = Math.min(index + 1, beadPoints.length - index - 2);
          const edgeFade = Math.min(1, edgeDistance / 4);
          const scale = 0.72 + edgeFade * 0.36 + (index % 4 === 0 ? 0.08 : 0);
          return (
            <mesh key={`${aspect.id}-bead-${index}`} position={point} renderOrder={21}>
              <sphereGeometry args={[beadRadius * scale, 12, 12]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={beadOpacity * edgeFade}
                blending={AdditiveBlending}
                depthWrite={false}
                depthTest={false}
                toneMapped={false}
              />
            </mesh>
          );
        })}
      </group>
    </group>
  );
}

function StarField() {
  const starTexture = useCosmicTexture(COSMIC_ASSETS.star);
  const { positions, colors } = useMemo(() => {
    const values = new Float32Array(1200 * 3);
    const colorValues = new Float32Array(1200 * 3);
    let seed = 7;
    const random = () => {
      seed = (seed * 16807) % 2147483647;
      return (seed - 1) / 2147483646;
    };
    const color = new Color();
    for (let index = 0; index < 1200; index += 1) {
      const radius = 7 + random() * 8;
      const angle = random() * Math.PI * 2;
      const height = (random() - 0.5) * 5.8;
      values[index * 3] = Math.cos(angle) * radius;
      values[index * 3 + 1] = height;
      values[index * 3 + 2] = Math.sin(angle) * radius;
      color.set(random() > 0.72 ? "#ffd98d" : random() > 0.56 ? "#9bd9ff" : "#fff4d2");
      colorValues[index * 3] = color.r;
      colorValues[index * 3 + 1] = color.g;
      colorValues[index * 3 + 2] = color.b;
    }
    return { colors: colorValues, positions: values };
  }, []);

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        map={starTexture}
        size={0.074}
        sizeAttenuation
        transparent
        opacity={0.86}
        vertexColors
        blending={AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

function GalaxyDust() {
  const groupRef = useRef<Group>(null);

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.z -= delta * 0.015;
  });

  return (
    <group ref={groupRef} rotation={[Math.PI / 2, 0, -0.28]}>
      {[1.8, 2.35, 2.9, 3.45].map((radius, index) => (
        <mesh key={radius}>
          <torusGeometry args={[radius, 0.018, 6, 220]} />
          <meshBasicMaterial
            color={index % 2 === 0 ? "#315fa8" : "#dba45f"}
            transparent
            opacity={0.13}
            blending={AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}

function CinematicParticleVeil() {
  const starTexture = useCosmicTexture(COSMIC_ASSETS.star);
  const groupRef = useRef<Group>(null);
  const { positions, colors } = useMemo(() => {
    const count = 420;
    const values = new Float32Array(count * 3);
    const colorValues = new Float32Array(count * 3);
    const color = new Color();
    let seed = 43;
    const random = () => {
      seed = (seed * 48271) % 2147483647;
      return (seed - 1) / 2147483646;
    };
    for (let index = 0; index < count; index += 1) {
      const lane = index / count;
      const angle = lane * Math.PI * 7.8 + random() * 0.45;
      const radius = 1.2 + lane * 4.4 + random() * 0.6;
      values[index * 3] = Math.cos(angle) * radius;
      values[index * 3 + 1] = -0.16 + random() * 0.58;
      values[index * 3 + 2] = Math.sin(angle) * radius * 0.74;
      color.set(index % 3 === 0 ? "#f6c46d" : index % 3 === 1 ? "#72c9ff" : "#fff4d2");
      colorValues[index * 3] = color.r;
      colorValues[index * 3 + 1] = color.g;
      colorValues[index * 3 + 2] = color.b;
    }
    return { colors: colorValues, positions: values };
  }, []);

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y += delta * 0.018;
  });

  return (
    <group ref={groupRef}>
      <points rotation={[0.08, 0, 0]}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
          <bufferAttribute attach="attributes-color" args={[colors, 3]} />
        </bufferGeometry>
        <pointsMaterial
          map={starTexture}
          size={0.09}
          sizeAttenuation
          transparent
          opacity={0.5}
          vertexColors
          blending={AdditiveBlending}
          depthWrite={false}
        />
      </points>
    </group>
  );
}

function positionForPlanet(planet: VisualPlanet): PointPosition {
  return positionForAngle(planet.angleDeg, planet.orbitRadius, planet.role === "person_b" ? 0.062 : 0.044);
}

function positionForAngle(angleDeg: number, orbitRadius: number, y: number): PointPosition {
  const radians = (angleDeg * Math.PI) / 180;
  return {
    x: Math.cos(radians) * orbitRadius,
    y,
    z: Math.sin(radians) * orbitRadius
  };
}

function signIndexFor(sign: string) {
  const normalized = normalizeSign(sign);
  const index = ZODIAC_WHEEL.findIndex((item) => item.key === normalized || item.label === normalized);
  return index >= 0 ? index : 0;
}

function normalizeSign(sign: string) {
  return sign.replace("牡羊", "白羊").trim();
}

function displaySign(sign: string) {
  const normalized = normalizeSign(sign);
  return ZODIAC_WHEEL.find((item) => item.key === normalized)?.label ?? sign;
}

function pointLabelFor(point: string) {
  const normalized = point.trim();
  return POINT_META[normalized as WesternNeedPoint["point"]]?.label ?? POINT_LABEL_FALLBACKS[normalized] ?? normalized;
}

function tintForPartner(color: string) {
  const partnerTints: Record<string, string> = {
    "#d9ebff": "#9fc7ff",
    "#9ee7f2": "#6fc9ff",
    "#ffc86f": "#f6a95d",
    "#f2794f": "#dd6d75",
    "#c9a777": "#a98ce0",
    "#b8e0ff": "#7ac6df"
  };
  return partnerTints[color] ?? color;
}
