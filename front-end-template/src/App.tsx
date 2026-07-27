import {
  CSSProperties,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import type { FormEvent, ReactNode } from "react";
import { motion } from "motion/react";
import {
  Apple,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Monitor,
  Palette,
  Play,
  Star,
  Zap
} from "lucide-react";
import { READING_CHECKOUT_URL } from "./config/commerce";

const PORTAL_BG =
  "https://res.cloudinary.com/dy5er7kv5/image/upload/q_auto/f_auto/v1779707217/image_1_vdzwae.png";
const WORLD_BG =
  "/assets/world-bg.png";
const BOTTOM_CLOUDS =
  "/assets/bottom-clouds.png";
const LUMINA_CARD_VIDEO =
  "https://cdn.sceneai.art/Hero%20Section%20Video/9ad5cc99-2fa4-4154-bcc2-5c9ec152778e.mp4";
const FOOTER_BG_VIDEO =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260525_052706_d2e390fd-1846-4fe7-a4d8-8d2f1c875358.mp4";
const CTA_PURPLE_GRADIENT =
  "linear-gradient(123deg, #18011f 7%, #b600a8 37%, #7621b0 72%, #be4c00 100%)";

const LUMINA_BRANDS = ["NASA JPL", "Swiss Ephemeris", "西洋星盤", "關係合盤", "隱私保護"];

const WORDPRESS_CONTENT_URLS = {
  blog: "https://www.valeoflight.com/blog/",
  privacy: "https://www.valeoflight.com/privacy-policy/",
  refunds: "https://www.valeoflight.com/refund_returns/",
  terms: "https://www.valeoflight.com/term-of-service/"
} as const;

const VIDEO_NAV_LINKS = [
  { label: "關係", href: "#relationship-reading" },
  { label: "時機", href: "#reading-flow" },
  { label: "答案", href: "#faq" },
  { label: "方案", href: "#pricing" }
] as const;

const LUMINA_NAV_LINKS = [
  { label: "首頁", href: "#top" },
  { label: "關於", href: "#about" },
  { label: "合盤", href: "#relationship-reading" },
  { label: "見證", href: "#reviews" },
  { label: "部落格", href: WORDPRESS_CONTENT_URLS.blog }
] as const;

const VIDEO_HERO_HEAD =
  "/assets/zodiac-hero-large.webp";
const BRAND_LOGOS = {
  horizontal: "/brand/valley-of-light-horizontal.webp",
  mark: "/brand/valley-of-light-mark.webp",
  stacked: "/brand/valley-of-light-stacked.webp",
  wordmark: "/brand/valley-of-light-wordmark.webp"
} as const;

const VIDEO_MARQUEE_IMAGES = [
  "/assets/relationship-signal-chart.webp",
  "/assets/relationship-signal-loading.webp",
  "/assets/relationship-signal-understanding.webp",
  "/assets/relationship-signal-input.webp",
  "/assets/relationship-signal-reunion.webp",
  "/assets/relationship-signal-profile.webp",
  "/assets/relationship-signal-emotion.webp"
];

const VIDEO_SERVICE_ITEMS = [
  {
    number: "01",
    title: "星盤定位",
    description:
      "先分開看懂你和他：你們各自需要什麼安全感、怎麼溝通、怎麼表達喜歡，以及遇到壓力時會怎麼防衛。先看懂兩個人，後面才不會只用單一事件判斷整段關係。"
  },
  {
    number: "02",
    title: "兩個人的關係契合度分析",
    description:
      "把兩個人的星盤放在一起看：你們哪裡容易自然靠近、哪裡需要磨合，哪些反應最容易被彼此誤會。這一段會整理吸引、情緒安全、溝通與壓力點，讓你看懂關係真正卡住的地方。"
  },
  {
    number: "03",
    title: "核心問題解讀",
    description:
      "針對你最想問的那句話：他心裡還有我嗎？這段關係還有機會嗎？我現在適合主動聯絡嗎？我該繼續等，還是慢慢放下？解讀會把問題整理成清楚方向，而不是只給你一堆星盤術語。"
  },
  {
    number: "04",
    title: "時機判讀",
    description:
      "判斷現在適合主動聯絡、輕輕靠近、繼續觀察，還是先暫停行動。解讀會整理比較適合開口的時間感與聯絡節奏，幫你避開最容易衝動、誤判，或把對方推遠的時候。"
  },
  {
    number: "05",
    title: "行動方向",
    description:
      "整理你現在可以做的下一步：要不要聯絡、該用什麼姿態靠近、哪些話先不要說、哪些行動容易造成反效果，讓你的選擇更有方向。"
  }
];

const VIDEO_DECOR_IMAGES = [
  {
    src: "https://shrug-person-78902957.figma.site/_components/v2/ebb2b8f25d8e24d5f0a5ca8af4c950de81aa2fd7/moon_icon.11395d36.png",
    x: -80,
    delay: 0.1,
    position: { top: "4%", left: "4%" }
  },
  {
    src: "/assets/about-us-star.webp",
    x: -80,
    delay: 0.25,
    mobileWidth: 144,
    desktopWidth: 238,
    position: { bottom: "8%", left: "9%" }
  },
  {
    src: "https://shrug-person-78902957.figma.site/_components/v2/ebb2b8f25d8e24d5f0a5ca8af4c950de81aa2fd7/lego_icon-1.703bb594.png",
    x: 80,
    delay: 0.15,
    position: { top: "4%", right: "4%" }
  },
  {
    src: "https://shrug-person-78902957.figma.site/_components/v2/ebb2b8f25d8e24d5f0a5ca8af4c950de81aa2fd7/Group_134-1.2e04f3ce.png",
    x: 80,
    delay: 0.3,
    position: { bottom: "8%", right: "8%" }
  }
];

type VideoReviewCardData = {
  name: string;
  rating: number;
  title: string;
  description: string;
};

type PublicRelationshipReview = {
  name?: string;
  meta?: string;
  rating?: number;
  title?: string;
  body?: string;
  tags?: string[];
};

const VIDEO_REVIEW_CARDS: VideoReviewCardData[] = [
  {
    name: "Mandy",
    rating: 5,
    title: "終於知道自己不是只能等",
    description:
      "原本一直想知道他會不會回來，解讀把他的防衛、我的不安和適合聯絡的時間分開講，心裡變清楚很多。"
  },
  {
    name: "Y. Lin",
    rating: 5,
    title: "比一般塔羅更像一份關係報告",
    description:
      "不是只說好或不好，而是把我們為什麼互相吸引、又為什麼容易退縮講得很具體。"
  },
  {
    name: "Claire",
    rating: 5,
    title: "下一步建議很實用",
    description:
      "我最喜歡最後的行動方向，直接告訴我現在適合先穩住自己，不要急著逼對方表態。"
  },
  {
    name: "Hana",
    rating: 5,
    title: "看懂我們真正卡住的地方",
    description:
      "本來以為只是他不夠愛，結果看到我們兩個都在用不同方式保護自己，反而比較能冷靜溝通。"
  },
  {
    name: "S. Wong",
    rating: 5,
    title: "時間點判斷很有幫助",
    description:
      "解讀不是叫我馬上行動，而是指出比較適合打開對話的窗口，讓我不用一直衝動傳訊息。"
  },
  {
    name: "Jasmine",
    rating: 5,
    title: "答案溫柔但不逃避現實",
    description:
      "它沒有只安慰我，而是把還有機會的地方和需要面對的現實都講出來，這點很重要。"
  }
];

const VIDEO_TESTIMONIAL_PLACEHOLDERS = [
  {
    name: "Mandy",
    meta: "復合時機",
    title: "原來等待不是唯一選擇，這次我知道該怎麼靠近",
    image:
      "https://cdn.sceneai.art/Image%20for%20any%20section/20009828-ab1c-4b6a-a1d8-59ba1fcc0415.webp"
  },
  {
    name: "Y. Lin",
    meta: "他的心意",
    title: "比起一句答案，我更需要看懂我們為什麼卡住",
    image:
      "https://cdn.sceneai.art/Image%20for%20any%20section/687a21b2-e30f-4df3-93e0-20f43dab94c7.webp"
  },
  {
    name: "Claire",
    meta: "行動方向",
    title: "看完之後，我終於沒有急著傳出那封訊息",
    image:
      "https://cdn.sceneai.art/Image%20for%20any%20section/7fce3708-e690-4b42-bc46-6117a04d0501.png"
  },
  {
    name: "Hana",
    meta: "關係真相",
    title: "不是他不愛，而是我們都在用自己的方式防衛",
    image:
      "https://cdn.sceneai.art/Image%20for%20any%20section/b0688a16-2d8b-4bfb-8f7f-201788eae921.webp"
  },
  {
    name: "S. Wong",
    meta: "聯絡時機",
    title: "有一個比較適合開口的窗口，讓我冷靜很多",
    image:
      "https://cdn.sceneai.art/Image%20for%20any%20section/bb56b4f0-50c0-42bf-8aea-d21fa5e55460.webp"
  },
  {
    name: "Jasmine",
    meta: "未來走向",
    title: "答案很溫柔，但也把我該面對的現實說清楚",
    image:
      "https://cdn.sceneai.art/Image%20for%20any%20section/20009828-ab1c-4b6a-a1d8-59ba1fcc0415.webp"
  }
];

const RELATIONSHIP_REVIEW_API_URL =
  typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://localhost:3000/api/relationship-reviews"
    : "https://chat.ig-hero.com/api/relationship-reviews";

function normalizePublicReview(review: PublicRelationshipReview): VideoReviewCardData {
  const rating = Math.round(Number(review.rating));

  return {
    name: review.name?.trim() || "Anonymous",
    rating: Number.isFinite(rating) ? Math.min(5, Math.max(1, rating)) : 5,
    title: review.title?.trim() || "用戶真實回饋",
    description: review.body?.trim() || ""
  };
}

const FEATURE_CARDS = [
  {
    title: "星盤定位",
    description:
      "以出生時間與地點校準雙方星盤，先看見這段關係真正牽動你的核心位置。",
    icon: <Monitor size={32} strokeWidth={2.5} />,
    gradient: "linear-gradient(137deg, #FF3D77 0%, #FFB1CE 45%, #FF9D3C 100%)",
    delay: 0.1
  },
  {
    title: "關係真相",
    description:
      "從他的心意、互動模式與現實阻礙，拆解你最想確認卻一直想不清的問題。",
    icon: <Palette size={32} strokeWidth={2.5} />,
    gradient: "linear-gradient(137deg, #FFFFFF 0%, #7DD3FC 45%, #06B6D4 100%)",
    delay: 0.2
  },
  {
    title: "行動方向",
    description:
      "把復合機會、聯絡時機與下一步選擇，整理成清楚、可執行的建議。",
    icon: <Zap size={32} strokeWidth={2.5} />,
    gradient: "linear-gradient(137deg, #4361EE 0%, #E0AEFF 45%, #F72585 100%)",
    delay: 0.3
  }
];

const BANNER_SLIDES = [
  {
    label: "關係地圖",
    title: "看清這段關係的下一步",
    body: "從他的心意、復合機會到行動時機，把答案整理成可以執行的方向。",
    image: WORLD_BG,
    position: "center center"
  },
  {
    label: "時機判讀",
    title: "找到最適合前進的時機",
    body: "用星盤節奏判斷該靠近、等待，或把重心放回自己。",
    image: PORTAL_BG,
    position: "center center"
  },
  {
    label: "行動建議",
    title: "讓混亂變成清楚路線",
    body: "把情緒裡最難判斷的問題，轉成一段有順序的解讀流程。",
    image: WORLD_BG,
    position: "center bottom"
  }
];

const ARC_CARDS = [
  {
    title: "他的心意",
    desc: "他現在心裡還有我嗎？",
    color: "#f3cdd6"
  },
  {
    title: "復合機會",
    desc: "這段關係還有機會回到彼此身邊嗎？",
    color: "#dcedc2"
  },
  {
    title: "真正原因",
    desc: "我們卡住的真正原因是什麼？",
    color: "#c3e3f4"
  },
  {
    title: "聯絡時機",
    desc: "他會主動聯絡我嗎？什麼時候最適合開口？",
    color: "#f0e4c0"
  },
  {
    title: "等待或放下",
    desc: "我該繼續等，還是該把重心放回自己？",
    color: "#dcd2f2"
  },
  {
    title: "未來走向",
    desc: "這段緣分接下來會往哪裡走？",
    color: "#f3cdd6"
  },
  {
    title: "現實阻礙",
    desc: "距離、壓力或第三者正在影響我們嗎？",
    color: "#c3e3f4"
  },
  {
    title: "他的想法",
    desc: "他怎麼看待我？又怎麼看待這段關係？",
    color: "#f0e4c0"
  },
  {
    title: "下一步",
    desc: "現在最能改變局面的行動是什麼？",
    color: "#dcedc2"
  }
];

const MAG = {
  world: 6,
  clouds: 9
};

type ArcCard = (typeof ARC_CARDS)[number];
type MousePoint = { x: number; y: number };

function clamp(val: number, min: number, max: number) {
  return Math.min(Math.max(val, min), max);
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function easeInOut(t: number) {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

function useIsMobile() {
  const getIsMobile = () =>
    typeof window !== "undefined" &&
    window.matchMedia("(max-width: 767px)").matches;
  const [isMobile, setIsMobile] = useState(getIsMobile);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const onChange = () => setIsMobile(media.matches);
    onChange();
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return isMobile;
}

function layerTransform(
  mouse: MousePoint,
  mag: number,
  scale: number,
  yDampen = 1,
  extraTranslate = ""
) {
  const x = -mouse.x * mag;
  const y = -mouse.y * mag * yDampen;
  return `translate3d(${x}px, ${y}px, 0) ${extraTranslate} scale(${scale})`;
}

function entranceStyle(
  visible: boolean,
  delaySeconds: number,
  distance = 18
): CSSProperties {
  return {
    opacity: visible ? 1 : 0,
    transform: visible ? "translateY(0)" : `translateY(${distance}px)`,
    transition: `opacity 0.9s ease ${delaySeconds}s, transform 0.9s ease ${delaySeconds}s`
  };
}

function BrandLogo({
  variant,
  width
}: {
  variant: keyof typeof BRAND_LOGOS;
  width: number;
}) {
  return (
    <img
      src={BRAND_LOGOS[variant]}
      alt="光之谷 Vale of Light"
      draggable={false}
      style={{
        display: "block",
        width,
        maxWidth: "100%",
        height: "auto",
        objectFit: "contain",
        filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.24))"
      }}
    />
  );
}

function ScrollChevron() {
  return (
    <div
      style={{
        width: 34,
        height: 34,
        borderRadius: "50%",
        border: "1.5px solid rgba(255,255,255,0.5)",
        display: "grid",
        placeItems: "center",
        animation: "bobUp 1.8s ease-in-out infinite"
      }}
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M4 6L8 10L12 6"
          stroke="rgba(255,255,255,0.72)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      style={{
        fontFamily: "'Imprima', sans-serif",
        fontSize: 10,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: "#fff",
        opacity: 0.9,
        textDecoration: "none"
      }}
    >
      {label}
    </a>
  );
}

function Nav() {
  const mobileLinkStyle: CSSProperties = {
    fontFamily: "'Imprima', sans-serif",
    fontSize: 9,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "#fff",
    opacity: 0.9,
    textDecoration: "none"
  };

  return (
    <nav
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        pointerEvents: "auto"
      }}
    >
      <div
        className="flex md:hidden"
        style={{
          padding: "18px 20px",
          justifyContent: "space-between",
          alignItems: "center"
        }}
      >
        <a href="#relationship-reading" style={mobileLinkStyle}>
          解讀
        </a>
        <BrandLogo variant="mark" width={32} />
        <a href="#faq" style={mobileLinkStyle}>
          常見問題
        </a>
      </div>
      <div
        className="hidden md:flex"
        style={{
          padding: "18px 42px",
          justifyContent: "space-between",
          alignItems: "center"
        }}
      >
        <div style={{ display: "flex", gap: 28, alignItems: "center" }}>
          <NavLink href="#relationship-reading" label="關係解讀" />
          <NavLink href="#reading-flow" label="解讀流程" />
          <NavLink href="#pricing" label="完整方案" />
        </div>
        <BrandLogo variant="mark" width={36} />
        <div style={{ display: "flex", gap: 28, alignItems: "center" }}>
          <NavLink href="#faq" label="常見問題" />
          <NavLink href="#reviews" label="用戶見證" />
          <NavLink href={WORDPRESS_CONTENT_URLS.blog} label="部落格" />
        </div>
      </div>
    </nav>
  );
}

function HeroHeading({
  variant
}: {
  variant: "mobile" | "tablet" | "desktop";
}) {
  const desktop = variant === "desktop";
  const tablet = variant === "tablet";
  const titleSize = desktop
    ? "clamp(50px, 4.2vw, 76px)"
    : tablet
      ? "clamp(34px, 5vw, 48px)"
      : "clamp(30px, 8.4vw, 40px)";
  const color = "#fff";
  const textShadow =
    "0 3px 26px rgba(0,0,0,0.56), 0 1px 4px rgba(0,0,0,0.7)";

  return (
    <h1
      style={{
        margin: 0,
        fontFamily:
          "'Noto Serif TC', 'Songti TC', 'Noto Sans TC', 'PingFang TC', serif",
        color,
        textShadow,
        fontWeight: 900,
        letterSpacing: desktop ? "0.018em" : "0.01em",
        lineHeight: desktop ? 1.12 : 1.12
      }}
    >
      <span
        style={{
          display: "block",
          fontSize: titleSize
        }}
      >
        在感情低谷裡
      </span>
      <span
        style={{
          display: "block",
          fontSize: titleSize
        }}
      >
        找到命定的光
      </span>
    </h1>
  );
}

function HeroEyebrow({ compact = false }: { compact?: boolean }) {
  return (
    <div
      style={{
        marginBottom: compact ? 8 : 14,
        color: "#e4c17d",
        display: "flex",
        alignItems: "center",
        gap: compact ? 9 : 13,
        minHeight: compact ? 34 : 46,
        fontFamily:
          "'Noto Serif TC', 'Songti TC', 'Noto Sans TC', 'PingFang TC', serif",
        fontSize: compact ? 11 : 15,
        fontWeight: 700,
        letterSpacing: compact ? "0.18em" : "0.24em",
        textShadow:
          "0 1px 12px rgba(0,0,0,0.52), 0 0 20px rgba(228,193,125,0.16)"
      }}
    >
      <span>光之谷</span>
      <span aria-hidden="true">·</span>
      <span
        style={{
          fontFamily: "'Times New Roman', 'Noto Serif TC', serif",
          fontSize: compact ? 9 : 12,
          letterSpacing: compact ? "0.24em" : "0.3em"
        }}
      >
        VALE OF LIGHT
      </span>
    </div>
  );
}

function HeroCta({ compact = false }: { compact?: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: compact ? "center" : "flex-start",
        gap: compact ? 12 : 14
      }}
    >
      <a
        href="#pricing"
        className="hero-glass-cta"
        style={{
          width: compact ? "min(100%, 284px)" : 274,
          minHeight: compact ? 48 : 50,
          borderRadius: 999,
          color: "#fff",
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          gap: compact ? 10 : 10,
          fontFamily:
            "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
          fontSize: compact ? 13 : 14,
          fontWeight: 700,
          letterSpacing: "0.08em",
          textDecoration: "none",
          padding: compact ? "11px 20px" : "12px 24px",
          pointerEvents: "auto"
        }}
      >
        <span className="hero-glass-cta-shine" aria-hidden="true" />
        <span>開始關係解讀</span>
        <ArrowRight
          className="hero-glass-cta-icon"
          size={compact ? 16 : 18}
          strokeWidth={1.8}
        />
      </a>
      <p
        style={{
          margin: 0,
          color: "rgba(255,255,255,0.82)",
          fontFamily:
            "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
          fontSize: compact ? 9 : 10,
          letterSpacing: compact ? "0.08em" : "0.16em",
          lineHeight: 1.5,
          textAlign: compact ? "center" : "left",
          textShadow: "0 1px 12px rgba(0,0,0,0.72)"
        }}
      >
        安全結帳 ・ 無需註冊 ・ 付款後寄送填寫連結
      </p>
    </div>
  );
}

function LaurelIcon({
  compact = false,
  flip = false
}: {
  compact?: boolean;
  flip?: boolean;
}) {
  const width = compact ? 26 : 28;
  const height = compact ? 17 : 18;

  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 58 38"
      fill="none"
      aria-hidden="true"
      style={{
        transform: flip ? "scaleX(-1)" : undefined,
        flex: "0 0 auto"
      }}
    >
      <path
        d="M53 34C38.5 32.5 22.5 25 9 8"
        stroke="rgba(255,255,255,0.9)"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {[
        [11, 10, -22],
        [17, 16, -14],
        [24, 21, -5],
        [31, 26, 5],
        [39, 30, 14],
        [47, 33, 22]
      ].map(([cx, cy, rotate]) => (
        <ellipse
          key={`${cx}-${cy}`}
          cx={cx}
          cy={cy}
          rx="3.5"
          ry="8"
          fill="rgba(255,255,255,0.9)"
          transform={`rotate(${rotate} ${cx} ${cy})`}
        />
      ))}
    </svg>
  );
}

function AppOfTheDay({ compact = false }: { compact?: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: compact ? "center" : "flex-start",
        gap: compact ? 7 : 8,
        color: "#fff",
        filter: "drop-shadow(0 2px 10px rgba(0,0,0,0.78))",
        opacity: 0.98
      }}
    >
      <LaurelIcon compact={compact} />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: compact ? 6 : 7
        }}
      >
        <div
          style={{
            fontFamily:
              "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
            fontSize: compact ? 8 : 9,
            fontWeight: 900,
            letterSpacing: "0.1em",
            lineHeight: 1.05,
            textTransform: "uppercase",
            whiteSpace: "nowrap"
          }}
        >
          APP OF
          <br />
          THE DAY
        </div>
        <Apple size={compact ? 14 : 15} fill="white" strokeWidth={2.4} />
      </div>
      <div
        style={{
          width: 1,
          height: compact ? 22 : 23,
          background: "rgba(255,255,255,0.34)"
        }}
      />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: compact ? 5 : 5,
          whiteSpace: "nowrap"
        }}
      >
        <span
          style={{
            fontFamily:
              "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
            fontSize: compact ? 19 : 21,
            fontWeight: 900,
            lineHeight: 0.9
          }}
        >
          1萬
        </span>
        <span
          style={{
            fontFamily:
              "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
            fontSize: compact ? 8 : 9,
            fontWeight: 900,
            letterSpacing: "0.08em",
            lineHeight: 1.08
          }}
        >
          次
          <br />
          解讀
        </span>
      </div>
      <LaurelIcon compact={compact} flip />
    </div>
  );
}

function MediaReports({ compact = false }: { compact?: boolean }) {
  return (
    <div
      style={{
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: compact ? 5 : 6,
        textShadow: "0 1px 12px rgba(0,0,0,0.62)",
        filter: "drop-shadow(0 2px 10px rgba(0,0,0,0.78))",
        opacity: 0.98
      }}
    >
      <div
        style={{
          fontFamily:
            "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
          fontSize: compact ? 8 : 9,
          fontWeight: 900,
          letterSpacing: "0.1em"
        }}
      >
        媒體報道
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: compact ? 11 : 14,
          fontFamily: "'Times New Roman', 'Noto Serif TC', serif",
          fontWeight: 700,
          lineHeight: 1,
          whiteSpace: "nowrap"
        }}
      >
        <span style={{ fontSize: compact ? 14 : 16, letterSpacing: "-0.05em" }}>
          VOGUE
        </span>
        <span
          style={{
            fontSize: compact ? 13 : 15,
            fontFamily:
              "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
            fontWeight: 900,
            letterSpacing: "-0.06em"
          }}
        >
          GLAMOUR
        </span>
        <span style={{ fontSize: compact ? 14 : 16, letterSpacing: "0.2em" }}>
          ELLE
        </span>
      </div>
    </div>
  );
}

function HeroAwardsStrip({ compact = false }: { compact?: boolean }) {
  return (
    <div
      style={{
        width: "100%",
        display: "flex",
        flexDirection: compact ? "column" : "row",
        alignItems: compact ? "center" : "flex-end",
        justifyContent: compact ? "center" : "space-between",
        gap: compact ? 8 : 22,
        pointerEvents: "none"
      }}
    >
      <AppOfTheDay compact={compact} />
      <MediaReports compact={compact} />
    </div>
  );
}

function Dots() {
  return (
    <div style={{ display: "flex", gap: 7, alignItems: "center" }}>
      {[0, 1, 2, 3].map((dot) => (
        <span
          key={dot}
          style={{
            width: dot === 0 ? 28 : 14,
            height: 4,
            borderRadius: 2,
            background:
              dot === 0 ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.35)"
          }}
        />
      ))}
    </div>
  );
}

function SceneOne({ uiVisible }: { uiVisible: boolean }) {
  const subtext =
    "幫你看清這段關係的真相、時機與未來走向\n重新看清彼此，看懂這段緣分";

  return (
    <>
      <div
        className="flex md:hidden"
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 20,
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          padding: "84px 24px 180px",
          pointerEvents: "none"
        }}
      >
        <div
          style={{
            ...entranceStyle(uiVisible, 0.3),
            width: "100%",
            maxWidth: 350,
            display: "flex",
            flexDirection: "column",
            alignItems: "center"
          }}
        >
          <HeroEyebrow compact />
          <HeroHeading variant="mobile" />
          <p
            style={{
              margin: "14px auto 20px",
              maxWidth: 320,
              color: "rgba(255,255,255,0.9)",
              fontSize: 13,
              lineHeight: 1.65,
              textShadow: "0 1px 10px rgba(0,0,0,0.72)",
              whiteSpace: "pre-line"
            }}
          >
            {subtext}
          </p>
          <HeroCta compact />
        </div>
        <div
          style={{
            ...entranceStyle(uiVisible, 0.7, 12),
            position: "absolute",
            left: 22,
            right: 22,
            bottom: 22,
            zIndex: 3,
            display: "flex",
            justifyContent: "center"
          }}
        >
          <HeroAwardsStrip compact />
        </div>
      </div>

      <div
        className="hidden md:flex xl:hidden"
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 20,
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          gap: 28,
          padding: "96px 32px 176px",
          pointerEvents: "none"
        }}
      >
        <div
          style={{
            ...entranceStyle(uiVisible, 0.3),
            display: "flex",
            flexDirection: "column",
            alignItems: "center"
          }}
        >
          <HeroEyebrow />
          <HeroHeading variant="tablet" />
          <p
            style={{
              margin: "14px auto 22px",
              maxWidth: 460,
              color: "rgba(255,255,255,0.9)",
              fontSize: 14,
              lineHeight: 1.65,
              textShadow: "0 1px 10px rgba(0,0,0,0.72)",
              whiteSpace: "pre-line"
            }}
          >
            {subtext}
          </p>
          <HeroCta compact />
        </div>
        <div
          style={{
            ...entranceStyle(uiVisible, 0.7, 12),
            position: "absolute",
            left: 32,
            right: 32,
            bottom: 30,
            zIndex: 3,
            display: "flex",
            justifyContent: "center"
          }}
        >
          <HeroAwardsStrip />
        </div>
      </div>

      <div
        className="hidden xl:block"
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 20,
          pointerEvents: "none"
        }}
      >
        <div
          style={{
            ...entranceStyle(uiVisible, 0.3),
            position: "absolute",
            top: "46%",
            left: "clamp(72px, 9.5vw, 164px)",
            maxWidth: 520,
            transform: uiVisible
              ? "translateY(-50%)"
              : "translateY(calc(-50% + 18px))"
          }}
        >
          <HeroEyebrow />
          <HeroHeading variant="desktop" />
          <p
            style={{
              margin: "17px 0 22px",
              maxWidth: 500,
              color: "rgba(255,245,235,0.88)",
              fontSize: 15,
              lineHeight: 1.55,
              textShadow: "0 1px 12px rgba(0,0,0,0.8)",
              whiteSpace: "pre-line"
            }}
          >
            {subtext}
          </p>
          <HeroCta />
        </div>

        <div
          className="hidden xl:flex"
          style={{
            ...entranceStyle(uiVisible, 0.7, 12),
            position: "absolute",
            left: 44,
            right: 44,
            bottom: 44,
            zIndex: 3,
            transform: uiVisible
              ? "translateY(0)"
              : "translateY(12px)",
            justifyContent: "center"
          }}
        >
          <HeroAwardsStrip />
        </div>
      </div>
    </>
  );
}

function ArcCardSlider({
  cards,
  rotationOffset,
  continuationProgress,
  isMobile
}: {
  cards: ArcCard[];
  rotationOffset: number;
  continuationProgress: number;
  isMobile: boolean;
}) {
  const totalCards = cards.length;
  const centerIndex = Math.floor(totalCards / 2);
  const cardSpacingDeg = isMobile ? 12 : 9;
  const arcRadius = isMobile ? 700 : 1100;
  const cardW = isMobile ? 160 : 220;
  const cardH = isMobile ? 175 : 230;
  const sliderH = isMobile ? 420 : 560;
  const halfW = cardW / 2;
  const gatherProgress = easeInOut(clamp(continuationProgress / 0.46, 0, 1));
  const spreadProgress = easeInOut(clamp((continuationProgress - 0.46) / 0.54, 0, 1));
  const stackBottom = isMobile ? 150 : 230;
  const baseArcBottom = isMobile ? 140 : 200;
  const finalStartX = isMobile ? -86 : -170;
  const finalGapX = isMobile ? 28 : 68;
  const finalGapY = isMobile ? 22 : 28;
  const finalBaseBottom = isMobile ? 88 : 128;
  const finalScale = isMobile ? 0.72 : 0.76;

  return (
    <div
      style={{
        position: "relative",
        width: "100vw",
        maxWidth: "100vw",
        height: sliderH,
        pointerEvents: "none"
      }}
    >
      {cards.map((card, i) => {
        const baseDeg = (i - centerIndex) * cardSpacingDeg;
        const deg = baseDeg - rotationOffset + centerIndex * cardSpacingDeg;
        const rad = (deg * Math.PI) / 180;
        const x = Math.sin(rad) * arcRadius;
        const y = arcRadius - Math.cos(rad) * arcRadius;
        const arcBottom = -y + baseArcBottom;
        const finalX = finalStartX + i * finalGapX;
        const finalBottom = finalBaseBottom + i * finalGapY;
        const finalRotate = -8 + i * 2.4;
        const gatheredX = lerp(x, 0, gatherProgress);
        const gatheredBottom = lerp(arcBottom, stackBottom, gatherProgress);
        const gatheredRotate = lerp(deg, 0, gatherProgress);
        const gatheredScale = lerp(1, 0.9, gatherProgress);
        const currentX = lerp(gatheredX, finalX, spreadProgress);
        const currentBottom = lerp(gatheredBottom, finalBottom, spreadProgress);
        const currentRotate = lerp(gatheredRotate, finalRotate, spreadProgress);
        const currentScale = lerp(gatheredScale, finalScale, spreadProgress);
        const continuationZ = continuationProgress > 0.36 ? totalCards - i : i + 1;

        return (
          <div
            key={card.title}
            style={{
              position: "absolute",
              bottom: currentBottom,
              left: `calc(50% + ${currentX}px - ${halfW}px)`,
              zIndex: continuationZ,
              width: cardW,
              height: cardH,
              borderRadius: isMobile ? 18 : 26,
              background: card.color,
              boxShadow:
                continuationProgress > 0.18
                  ? "0 18px 56px rgba(15,8,18,0.24)"
                  : "0 8px 40px rgba(80,40,60,0.18)",
              padding: isMobile ? 18 : 24,
              transform: `rotate(${currentRotate}deg) scale(${currentScale})`,
              transformOrigin:
                continuationProgress > 0.02 ? "50% 50%" : `${halfW}px ${arcRadius}px`,
              overflow: "hidden",
              color: "#3a2530"
            }}
          >
            <div
              style={{
                position: "absolute",
                top: isMobile ? 14 : 18,
                right: isMobile ? 14 : 18,
                width: 24,
                height: 24,
                borderRadius: "50%",
                border: "1.5px solid rgba(80,50,60,0.3)",
                display: "grid",
                placeItems: "center",
                color: "rgba(80,50,60,0.6)",
                fontSize: 10,
                letterSpacing: "0.06em"
              }}
            >
              {String(i + 1).padStart(2, "0")}
            </div>
            <div
              style={{
                position: "absolute",
                left: isMobile ? 18 : 24,
                right: isMobile ? 18 : 24,
                top: isMobile ? 52 : 60
              }}
            >
              <h3
                style={{
                margin: 0,
                fontFamily:
                  "'Noto Serif TC', 'Songti TC', 'Noto Sans TC', serif",
                fontWeight: 900,
                fontSize: isMobile ? 21 : 28,
                lineHeight: 1.1,
                color: "#3a2530"
              }}
              >
                {card.title}
              </h3>
              <p
                style={{
                  margin: isMobile ? "9px 0 0" : "12px 0 0",
                  fontFamily:
                    "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
                  fontSize: isMobile ? 12 : 14,
                  fontWeight: 700,
                  lineHeight: 1.5,
                  color: "rgba(58,37,48,0.72)"
                }}
              >
                {card.desc}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ContinuationPanel({
  isMobile,
  progress,
  surfaceProgress
}: {
  isMobile: boolean;
  progress: number;
  surfaceProgress: number;
}) {
  const panelProgress = easeInOut(clamp((progress - 0.42) / 0.44, 0, 1));
  const textColor = `rgba(17,17,17,${surfaceProgress})`;
  const mutedColor = `rgba(17,17,17,${surfaceProgress * 0.58})`;
  const shadowOpacity = 1 - surfaceProgress;

  return (
    <div
      style={{
        position: "absolute",
        left: isMobile ? 24 : "clamp(64px, 8vw, 132px)",
        right: isMobile ? 24 : "auto",
        bottom: isMobile ? 248 : 300,
        zIndex: 42,
        maxWidth: isMobile ? "none" : 390,
        opacity: panelProgress,
        transform: `translateY(${lerp(26, 0, panelProgress)}px)`,
        pointerEvents: "none"
      }}
    >
      <div
        style={{
          color: mutedColor,
          fontFamily:
            "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
          fontSize: isMobile ? 10 : 11,
          fontWeight: 800,
          letterSpacing: "0.18em",
          marginBottom: 12,
          textShadow: `0 1px 12px rgba(0,0,0,${0.65 * shadowOpacity})`
        }}
      >
        關係問題拆解
      </div>
      <h3
        style={{
          margin: 0,
          color: textColor,
          fontFamily: "'Noto Serif TC', 'Songti TC', 'Noto Sans TC', serif",
          fontSize: isMobile ? 24 : 36,
          fontWeight: 900,
          lineHeight: 1.12,
          letterSpacing: "0.02em",
          textShadow: `0 2px 18px rgba(0,0,0,${0.48 * shadowOpacity})`
        }}
      >
        把心裡的問題
        <br />
        排成看得懂的路徑
      </h3>
      <p
        style={{
          margin: "14px 0 0",
          color: mutedColor,
          fontFamily:
            "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
          fontSize: isMobile ? 12 : 14,
          lineHeight: 1.65,
          maxWidth: 360,
          textShadow: `0 1px 12px rgba(0,0,0,${0.62 * shadowOpacity})`
        }}
      >
        從他的心意、復合機會到下一步行動，先把混亂的情緒整理成可以判斷的順序。
      </p>
    </div>
  );
}

function FeatureCard({
  title,
  description,
  icon,
  gradient,
  delay
}: {
  title: string;
  description: string;
  icon: ReactNode;
  gradient: string;
  delay: number;
}) {
  return (
    <motion.div
      className="relative flex flex-col justify-start items-start w-full max-w-[260px] md:max-w-[300px] group mx-auto"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: "easeOut", delay }}
    >
      <div
        className="absolute w-full h-[260px] md:h-[300px] rounded-[40px] pointer-events-none"
        style={{
          padding: 6,
          background: gradient,
          filter: "blur(12px)",
          opacity: 0.82,
          WebkitMask:
            "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
          WebkitMaskComposite: "xor",
          maskComposite: "exclude"
        }}
      />
      <div
        className="relative self-stretch h-[260px] md:h-[300px] rounded-[40px] z-10 overflow-hidden"
        style={{
          border: "2px solid transparent",
          background: `linear-gradient(145deg, rgba(255,255,255,0.13) 0%, rgba(255,255,255,0.045) 48%, rgba(255,255,255,0.1) 100%) padding-box, ${gradient} border-box`,
          boxShadow:
            "0 22px 58px rgba(0,0,0,0.28), 0 0 34px rgba(255,255,255,0.08), inset 0 1px 0 rgba(255,255,255,0.18), inset 0 -1px 0 rgba(255,255,255,0.06)",
          backdropFilter: "blur(14px)",
          WebkitBackdropFilter: "blur(14px)"
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(circle at 18% 12%, rgba(255,255,255,0.18) 0%, transparent 34%)",
            pointerEvents: "none"
          }}
        />
        <div className="relative z-10 w-full h-full p-7 flex flex-col justify-between">
          <div
            className="text-white/90"
            style={{
              width: 48,
              height: 48,
              borderRadius: 16,
              display: "grid",
              placeItems: "center",
              border: "1px solid rgba(255,255,255,0.16)",
              background: "rgba(255,255,255,0.08)",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.12)"
            }}
          >
            {icon}
          </div>
          <div>
            <h3 className="text-white font-medium text-xl mb-3 tracking-tight">
              {title}
            </h3>
            <p className="text-white/65 text-[14px] leading-[1.6] font-normal selection:bg-white/20">
              {description}
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function VideoFeatureCardGrid() {
  return (
    <div className="relative z-20 min-h-screen flex flex-col items-center justify-center p-6 md:p-12 font-sans pointer-events-none">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-3 lg:gap-3 w-full max-w-[936px]">
        {FEATURE_CARDS.map((card) => (
          <FeatureCard
            key={card.title}
            title={card.title}
            description={card.description}
            icon={card.icon}
            gradient={card.gradient}
            delay={card.delay}
          />
        ))}
      </div>
    </div>
  );
}

function LuminaLogo() {
  return (
    <BrandLogo variant="horizontal" width={184} />
  );
}

function LuminaBrandMark({ name }: { name: string }) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        color: "rgba(255,255,255,0.55)",
        filter: "grayscale(1)",
        opacity: 0.55,
        fontFamily:
          "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
        fontSize: 11,
        fontWeight: 800,
        letterSpacing: "0.08em"
      }}
    >
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
        <rect x="2" y="2" width="11" height="11" rx="3" stroke="currentColor" strokeWidth="1.4" />
        <path d="M4.8 7.5H10.2M7.5 4.8V10.2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
      {name}
    </div>
  );
}

function LuminaTicker() {
  const brands = [...LUMINA_BRANDS, ...LUMINA_BRANDS];

  return (
    <div style={{ overflow: "hidden", width: "100%" }}>
      <div className="lumina-ticker-track">
        {brands.map((brand, index) => (
          <LuminaBrandMark key={`${brand}-${index}`} name={brand} />
        ))}
      </div>
    </div>
  );
}

function LuminaVideoBackground({
  opacity = 1,
  sticky = false,
  fixed = false
}: {
  opacity?: number;
  sticky?: boolean;
  fixed?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || opacity <= 0) {
      return;
    }

    const playVideo = () => {
      video.muted = true;
      void video.play().catch(() => undefined);
    };
    const resumeOnScroll = () => {
      if (video.paused) {
        playVideo();
      }
    };

    playVideo();
    window.addEventListener("scroll", resumeOnScroll, { passive: true });
    document.addEventListener("visibilitychange", playVideo);

    return () => {
      window.removeEventListener("scroll", resumeOnScroll);
      document.removeEventListener("visibilitychange", playVideo);
    };
  }, [opacity]);

  return (
    <div
      style={{
        position: fixed ? "fixed" : sticky ? "sticky" : "absolute",
        inset: fixed || !sticky ? 0 : undefined,
        top: 0,
        height: fixed || sticky ? "100vh" : undefined,
        width: fixed ? "100vw" : undefined,
        zIndex: 0,
        overflow: "hidden",
        background: "#050506",
        opacity,
        pointerEvents: "none"
      }}
    >
      <video
        ref={videoRef}
        src={LUMINA_CARD_VIDEO}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        onCanPlay={(event) => {
          event.currentTarget.muted = true;
          void event.currentTarget.play().catch(() => undefined);
        }}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: "right center",
          transform: "scale(1.3)",
          transformOrigin: "right center",
          opacity: 1,
          filter: "brightness(1.1) contrast(1.1)"
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(to right, rgba(0,0,0,1) 0%, rgba(0,0,0,0.85) 30%, rgba(0,0,0,0) 85%)"
        }}
      />
    </div>
  );
}

function EphemerisIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
      <circle cx="13" cy="13" r="9.2" stroke="currentColor" strokeWidth="1.4" opacity="0.72" />
      <path
        d="M5.2 15.2C7.8 18.8 18.2 18.8 20.8 15.2"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        opacity="0.64"
      />
      <path
        d="M5.2 10.8C7.8 7.2 18.2 7.2 20.8 10.8"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        opacity="0.64"
      />
      <path d="M13 4v18M4 13h18" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" opacity="0.42" />
      <circle cx="18.3" cy="7.7" r="1.7" fill="currentColor" />
    </svg>
  );
}

function NasaDataIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
      <path
        d="M5.5 18.2C8.1 11.6 13.1 6.7 20.5 4.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        opacity="0.62"
      />
      <path
        d="M4.8 7.1C10.3 10.2 14.2 14.5 17.4 21.2"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        opacity="0.62"
      />
      <circle cx="13" cy="13" r="9" stroke="currentColor" strokeWidth="1.3" opacity="0.74" />
      <circle cx="13" cy="13" r="2.2" fill="currentColor" />
      <circle cx="20.5" cy="4.5" r="1.5" fill="currentColor" />
      <circle cx="5.5" cy="18.2" r="1.25" fill="currentColor" />
    </svg>
  );
}

function LuminaSourceBadge({
  icon,
  label,
  text,
  isMobile
}: {
  icon: ReactNode;
  label: string;
  text: string;
  isMobile: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: isMobile ? 10 : 12,
        minWidth: isMobile ? "100%" : 220,
        padding: isMobile ? "11px 13px" : "12px 15px",
        borderRadius: 18,
        border: "1px solid rgba(255,255,255,0.18)",
        background: "rgba(255,255,255,0.07)",
        boxShadow:
          "0 18px 42px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.08)",
        backdropFilter: "blur(10px)",
        WebkitBackdropFilter: "blur(10px)"
      }}
    >
      <div
        style={{
          width: isMobile ? 34 : 38,
          height: isMobile ? 34 : 38,
          borderRadius: "50%",
          display: "grid",
          placeItems: "center",
          flex: "0 0 auto",
          color: "#7dd3fc",
          background: "rgba(125,211,252,0.12)",
          boxShadow: "0 0 18px rgba(56,189,248,0.16)"
        }}
      >
        {icon}
      </div>
      <div>
        <div
          style={{
            fontSize: isMobile ? 12 : 13,
            fontWeight: 900,
            letterSpacing: "0.08em",
            color: "#fff",
            lineHeight: 1
          }}
        >
          {label}
        </div>
        <div
          style={{
            marginTop: 6,
            fontSize: isMobile ? 11 : 12,
            fontWeight: 700,
            lineHeight: 1.35,
            color: "rgba(255,255,255,0.62)"
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
}

function LuminaSourceBadges({ isMobile }: { isMobile: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: isMobile ? "column" : "row",
        gap: isMobile ? 10 : 12,
        margin: "0 0 30px",
        maxWidth: isMobile ? "100%" : 500
      }}
    >
      <LuminaSourceBadge
        icon={<EphemerisIcon />}
        label="SWISS EPHEMERIS"
        text="瑞士星曆精準計算"
        isMobile={isMobile}
      />
      <LuminaSourceBadge
        icon={<NasaDataIcon />}
        label="NASA JPL"
        text="太空總署等級天文資料"
        isMobile={isMobile}
      />
    </div>
  );
}

function LuminaHeroPanel({ isMobile }: { isMobile: boolean }) {
  const sidePadding = isMobile ? 24 : 70;

  return (
    <div
      style={{
        position: "relative",
        minHeight: "100vh",
        color: "#fff",
        fontFamily:
          "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif"
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 28,
          left: sidePadding,
          right: sidePadding,
          display: "flex",
          alignItems: "center",
          gap: 24,
          zIndex: 30
        }}
      >
        <LuminaLogo />
        {!isMobile && (
          <div
            style={{
              marginLeft: "auto",
              marginRight: 48,
              display: "flex",
              alignItems: "center",
              gap: 28,
              color: "rgba(255,255,255,0.6)",
              fontSize: "0.85rem",
              fontWeight: 400
            }}
          >
            {LUMINA_NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                style={{ color: "inherit", textDecoration: "none" }}
              >
                {link.label}
              </a>
            ))}
          </div>
        )}
        <button
          type="button"
          aria-label="Play"
          style={{
            width: 52,
            height: 52,
            borderRadius: "50%",
            border: "1px solid rgba(255,255,255,0.25)",
            background: "rgba(255,255,255,0.08)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
            display: "grid",
            placeItems: "center",
            color: "#fff",
            marginLeft: isMobile ? "auto" : 0,
            cursor: "pointer"
          }}
        >
          <Play size={16} fill="white" strokeWidth={0} />
        </button>
      </div>

      <div
        style={{
          position: "absolute",
          left: sidePadding,
          top: "50%",
          transform: "translateY(-62%)",
          maxWidth: isMobile ? "calc(100vw - 48px)" : 620
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            minHeight: 24,
            borderRadius: 999,
            border: "1px solid rgba(255,255,255,0.18)",
            padding: "6px 12px",
            color: "rgba(255,255,255,0.74)",
            fontSize: 9,
            fontWeight: 900,
            letterSpacing: "0.4em",
            textTransform: "uppercase",
            marginBottom: 12,
            background: "rgba(255,255,255,0.04)",
            backdropFilter: "blur(10px)",
            WebkitBackdropFilter: "blur(10px)"
          }}
        >
          RELATIONSHIP READING
        </div>
        <h1
          style={{
            margin: "0 0 22px",
            fontFamily:
              "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
            fontSize: isMobile ? "clamp(38px, 10vw, 54px)" : 64,
            fontWeight: 900,
            lineHeight: 1.08,
            letterSpacing: 0,
            color: "#fff"
          }}
        >
          不再靠猜，讓命盤替你看見答案
        </h1>
        <LuminaSourceBadges isMobile={isMobile} />
        <a
          href="#pricing"
          className="lumina-orbit-button"
          style={{ textDecoration: "none" }}
        >
          <span className="hero-glass-cta-shine" aria-hidden="true" />
          <span>開始關係解讀</span>
          <ArrowRight className="lumina-arrow" size={15} strokeWidth={2.2} />
        </a>
      </div>

      <div
        style={{
          position: "absolute",
          left: sidePadding,
          right: sidePadding,
          bottom: 24,
          display: "flex",
          flexDirection: "column",
          gap: 16,
          alignItems: "center"
        }}
      >
        <div
          style={{
            color: "rgba(255,255,255,0.25)",
            fontSize: 9,
            fontWeight: 900,
            letterSpacing: "0.6em",
            textAlign: "center"
          }}
        >
          VALE OF LIGHT RELATIONSHIP SYSTEM
        </div>
        <LuminaTicker />
      </div>
    </div>
  );
}

function VideoContactButton({ isMobile }: { isMobile: boolean }) {
  return (
    <a
      href="#pricing"
      className="hero-glass-cta"
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: isMobile ? 8 : 12,
        borderRadius: 999,
        padding: isMobile ? "13px 24px" : "17px 42px",
        minHeight: isMobile ? 50 : 60,
        color: "#fff",
        fontSize: isMobile ? 12 : 14,
        fontWeight: 900,
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        textDecoration: "none",
        cursor: "pointer",
        whiteSpace: "nowrap"
      }}
    >
      <span className="hero-glass-cta-shine" aria-hidden="true" />
      <span>開始關係解讀</span>
      <ArrowRight size={isMobile ? 15 : 17} strokeWidth={2.2} />
    </a>
  );
}

function VideoLandingHero({ isMobile }: { isMobile: boolean }) {
  const sidePadding = isMobile ? 22 : 42;
  const headRef = useRef<HTMLDivElement | null>(null);
  const [headOffset, setHeadOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const onMouseMove = (event: MouseEvent) => {
      const head = headRef.current;
      if (!head) {
        return;
      }

      const rect = head.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const dx = event.clientX - centerX;
      const dy = event.clientY - centerY;
      const padding = 150;
      const isActive =
        Math.abs(dx) < rect.width / 2 + padding &&
        Math.abs(dy) < rect.height / 2 + padding;

      if (!isActive) {
        setHeadOffset({ x: 0, y: 0 });
        return;
      }

      setHeadOffset({
        x: clamp(dx / (isMobile ? 4.4 : 3.2), isMobile ? -18 : -42, isMobile ? 18 : 42),
        y: clamp(dy / (isMobile ? 4.4 : 3.2), isMobile ? -14 : -34, isMobile ? 14 : 34)
      });
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMouseMove);
  }, [isMobile]);

  return (
    <section
      style={{
        position: "relative",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-start",
        padding: isMobile
          ? "22px 22px 32px"
          : "30px clamp(34px, 4vw, 72px) 42px",
        overflow: "hidden"
      }}
    >
      <motion.nav
        initial={{ opacity: 0, y: -18 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0 }}
        transition={{ duration: 0.72, ease: [0.25, 0.1, 0.25, 1] }}
        style={{
          position: "relative",
          zIndex: 6,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: isMobile ? 12 : 26,
          color: "#d7e2ea",
          fontSize: isMobile ? 12 : "clamp(14px, 1.05vw, 19px)",
          fontWeight: 800,
          letterSpacing: "0.12em",
          textTransform: "uppercase"
        }}
      >
        {VIDEO_NAV_LINKS.map((link) => (
          <a
            key={link.label}
            href={link.href}
            style={{
              color: "inherit",
              textDecoration: "none",
              opacity: 0.92,
              whiteSpace: "nowrap"
            }}
          >
            {link.label}
          </a>
        ))}
      </motion.nav>

      <motion.div
        initial={{ opacity: 0, y: 38 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0 }}
        transition={{
          duration: 0.9,
          delay: 0.12,
          ease: [0.25, 0.1, 0.25, 1]
        }}
        style={{
          position: "relative",
          zIndex: 3,
          overflow: "hidden",
          marginTop: isMobile ? 28 : -10
        }}
      >
        <h2
          aria-label="Vale of Light"
          style={{
            margin: 0,
            width: "100%",
            fontFamily:
              "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
            fontSize: isMobile
              ? "clamp(56px, 17vw, 92px)"
              : "clamp(110px, 17vw, 260px)",
            fontWeight: 900,
            lineHeight: 0.86,
            letterSpacing: 0,
            textAlign: "center",
            textTransform: "uppercase",
            whiteSpace: isMobile ? "normal" : "nowrap",
            color: "rgba(255,255,255,0.72)"
          }}
        >
          VALE OF LIGHT
        </h2>
      </motion.div>

      <motion.div
        ref={headRef}
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true, amount: 0 }}
        transition={{
          duration: 0.75,
          delay: 0.26,
          ease: [0.25, 0.1, 0.25, 1]
        }}
        style={{
          position: "absolute",
          left: "50%",
          top: isMobile ? "50%" : "auto",
          bottom: isMobile ? "auto" : 0,
          zIndex: 5,
          width: isMobile ? "min(92vw, 390px)" : "min(72vw, 820px)",
          transformStyle: "preserve-3d",
          perspective: 900,
          transformOrigin: "50% 58%",
          transform: `translate3d(calc(-50% + ${headOffset.x}px), calc(${isMobile ? "-50%" : "0px"} + ${headOffset.y}px), 0) rotateX(${clamp(
            -headOffset.y / 10,
            -4,
            4
          )}deg) rotateY(${clamp(headOffset.x / 6, -8, 8)}deg)`,
          transition:
            headOffset.x || headOffset.y
              ? "transform 0.24s ease-out"
              : "transform 0.58s ease-in-out",
          filter: "drop-shadow(0 30px 70px rgba(0,0,0,0.55))",
          pointerEvents: "none"
        }}
      >
        <img
          src={VIDEO_HERO_HEAD}
          alt=""
          loading="eager"
          style={{
            width: "100%",
            height: "auto",
            objectFit: "contain",
            opacity: 0.96
          }}
        />
      </motion.div>

      <div
        style={{
          position: "absolute",
          left: isMobile ? 22 : "clamp(34px, 4vw, 72px)",
          right: isMobile ? 22 : "clamp(34px, 4vw, 72px)",
          bottom: isMobile ? 32 : 42,
          zIndex: 6,
          display: "flex",
          justifyContent: "space-between",
          alignItems: isMobile ? "center" : "flex-end",
          gap: isMobile ? 20 : 34,
          paddingLeft: 0,
          paddingRight: 0,
          flexDirection: isMobile ? "column" : "row",
          width: "auto"
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0 }}
          transition={{
            duration: 0.72,
            delay: 0.34,
            ease: [0.25, 0.1, 0.25, 1]
          }}
          style={{
            margin: 0,
            maxWidth: isMobile ? 300 : 520,
            textAlign: isMobile ? "center" : "left",
            alignSelf: isMobile ? "center" : "auto"
          }}
        >
          <h3
            style={{
              margin: 0,
              color: "#fff",
              fontFamily:
                "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
              fontSize: isMobile
                ? 13
                : "clamp(13px, 1.25vw, 20px)",
              fontWeight: 700,
              lineHeight: 1.35,
              letterSpacing: "0.08em",
              textShadow: "0 2px 18px rgba(0,0,0,0.58)"
            }}
          >
            不再靠猜，讓命盤替你看見答案
          </h3>
          <div
            style={{
              display: "flex",
              flexDirection: isMobile ? "column" : "row",
              justifyContent: isMobile ? "center" : "flex-start",
              alignItems: isMobile ? "center" : "flex-start",
              gap: isMobile ? 8 : 10,
              marginTop: isMobile ? 10 : 12
            }}
          >
            {[
              {
                icon: <EphemerisIcon />,
                label: "SWISS EPHEMERIS",
                text: "瑞士星曆精準計算"
              },
              {
                icon: <NasaDataIcon />,
                label: "NASA JPL",
                text: "太空總署等級天文資料"
              }
            ].map((badge) => (
              <div
                key={badge.label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  minWidth: isMobile ? 220 : 190,
                  padding: "8px 10px",
                  borderRadius: 16,
                  border: "1px solid rgba(255,255,255,0.16)",
                  background: "rgba(255,255,255,0.07)",
                  boxShadow:
                    "0 12px 28px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.08)",
                  backdropFilter: "blur(10px)",
                  WebkitBackdropFilter: "blur(10px)"
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    display: "grid",
                    placeItems: "center",
                    flex: "0 0 auto",
                    color: "#7dd3fc",
                    background: "rgba(125,211,252,0.12)"
                  }}
                >
                  {badge.icon}
                </div>
                <div>
                  <div
                    style={{
                      color: "#fff",
                      fontSize: 10,
                      fontWeight: 900,
                      letterSpacing: "0.08em",
                      lineHeight: 1
                    }}
                  >
                    {badge.label}
                  </div>
                  <div
                    style={{
                      marginTop: 5,
                      color: "rgba(255,255,255,0.62)",
                      fontSize: 10,
                      fontWeight: 700,
                      lineHeight: 1.25
                    }}
                  >
                    {badge.text}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0 }}
          transition={{
            duration: 0.72,
            delay: 0.48,
            ease: [0.25, 0.1, 0.25, 1]
          }}
          style={{ alignSelf: isMobile ? "center" : "flex-end" }}
        >
          <VideoContactButton isMobile={isMobile} />
        </motion.div>
      </div>
    </section>
  );
}

function VideoMarqueeSection({ isMobile }: { isMobile: boolean }) {
  const sectionRef = useRef<HTMLDivElement | null>(null);
  const [scrollOffset, setScrollOffset] = useState(0);
  const rowOne = VIDEO_MARQUEE_IMAGES;
  const rowTwo = [...VIDEO_MARQUEE_IMAGES].reverse();
  const tileWidth = isMobile ? 250 : 420;
  const tileHeight = isMobile ? 164 : 270;
  const baseShift = isMobile ? 110 : 200;

  useEffect(() => {
    const updateOffset = () => {
      const section = sectionRef.current;
      if (!section) {
        return;
      }

      const sectionTop = section.getBoundingClientRect().top + window.scrollY;
      setScrollOffset(
        (window.scrollY - sectionTop + window.innerHeight) * 0.3
      );
    };

    updateOffset();
    window.addEventListener("scroll", updateOffset, { passive: true });
    window.addEventListener("resize", updateOffset);
    return () => {
      window.removeEventListener("scroll", updateOffset);
      window.removeEventListener("resize", updateOffset);
    };
  }, []);

  const renderRow = (images: string[], reverse = false) => (
    <div
      style={{
        display: "flex",
        gap: 12,
        width: "max-content",
        transform: `translate3d(${
          reverse ? -(scrollOffset - baseShift) : scrollOffset - baseShift
        }px, 0, 0)`,
        willChange: "transform"
      }}
    >
      {images.map((src, index) => (
        <img
          key={`${src}-${index}`}
          src={src}
          alt=""
          loading="lazy"
          style={{
            width: tileWidth,
            height: tileHeight,
            borderRadius: isMobile ? 18 : 24,
            objectFit: "cover",
            border: "1px solid rgba(255,255,255,0.13)",
            boxShadow: "0 24px 60px rgba(0,0,0,0.4)",
            background: "rgba(255,255,255,0.06)"
          }}
        />
      ))}
    </div>
  );

  return (
    <section
      ref={sectionRef}
      style={{
        position: "relative",
        overflow: "hidden",
        padding: isMobile ? "72px 0 58px" : "120px 0 74px"
      }}
    >
      <div
        style={{
          padding: isMobile ? "0 22px 30px" : "0 clamp(34px, 4vw, 72px) 44px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          gap: 24,
          flexDirection: isMobile ? "column" : "row"
        }}
      >
        <motion.h3
          initial={{ opacity: 0, y: 32 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.76, ease: [0.25, 0.1, 0.25, 1] }}
          style={{
            margin: 0,
            maxWidth: isMobile ? "100%" : 760,
            fontFamily:
              "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
            fontSize: isMobile
              ? "clamp(34px, 10vw, 52px)"
              : "clamp(66px, 8vw, 132px)",
            fontWeight: 900,
            lineHeight: 0.92,
            letterSpacing: 0,
            textTransform: "uppercase",
            background: "linear-gradient(180deg, #f4f8ff 0%, #7f8794 100%)",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            WebkitTextFillColor: "transparent"
          }}
        >
          看見關係的每一層訊號
        </motion.h3>
        <p
          style={{
            margin: 0,
            maxWidth: isMobile ? "100%" : 320,
            color: "rgba(215,226,234,0.76)",
            fontSize: isMobile ? 13 : 15,
            lineHeight: 1.7,
            fontWeight: 500
          }}
        >
          每一次提問都會被拆成清楚的判斷路徑，讓直覺、命盤與行動建議連在一起。
        </p>
      </div>

      <div style={{ display: "grid", gap: 12 }}>
        {renderRow(rowOne)}
        {renderRow(rowTwo, true)}
      </div>
    </section>
  );
}

function VideoAboutSection({ isMobile }: { isMobile: boolean }) {
  return (
    <section
      id="about"
      style={{
        position: "relative",
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: isMobile ? "88px 22px" : "120px 40px",
        overflow: "hidden"
      }}
    >
      {VIDEO_DECOR_IMAGES.map((image, index) => (
        <motion.img
          key={image.src}
          src={image.src}
          alt=""
          initial={{ opacity: 0, x: image.x }}
          whileInView={{ opacity: isMobile ? 0.28 : 0.58, x: 0 }}
          viewport={{ once: true, amount: 0.15 }}
          transition={{
            duration: 0.9,
            delay: image.delay,
            ease: [0.25, 0.1, 0.25, 1]
          }}
          style={{
            position: "absolute",
            width: isMobile
              ? image.mobileWidth ?? (index % 2 === 0
                ? 116
                : 96)
              : image.desktopWidth ?? (index % 2 === 0
                ? 190
                : 164),
            height: "auto",
            objectFit: "contain",
            filter:
              "drop-shadow(0 24px 50px rgba(0,0,0,0.55)) saturate(1.08)",
            pointerEvents: "none",
            ...image.position
          }}
        />
      ))}

      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: isMobile ? 32 : 48,
          maxWidth: 760,
          textAlign: "center"
        }}
      >
        <motion.h3
          initial={{ opacity: 0, y: 38 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.78, ease: [0.25, 0.1, 0.25, 1] }}
          style={{
            margin: 0,
            fontFamily:
              "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
            fontSize: isMobile
              ? "clamp(48px, 14vw, 72px)"
              : "clamp(78px, 12vw, 160px)",
            fontWeight: 900,
            lineHeight: 0.9,
            letterSpacing: 0,
            textTransform: "uppercase",
            background: "linear-gradient(180deg, #646973 0%, #bbccd7 100%)",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            WebkitTextFillColor: "transparent",
            filter: "drop-shadow(0 20px 42px rgba(0,0,0,0.46))"
          }}
        >
          斗轉星移
        </motion.h3>

        <motion.p
          initial={{ opacity: 0.18, y: 26 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.32 }}
          transition={{ duration: 0.9, delay: 0.16, ease: [0.25, 0.1, 0.25, 1] }}
          style={{
            margin: 0,
            maxWidth: 640,
            color: "#d7e2ea",
            fontSize: isMobile ? 16 : "clamp(18px, 2vw, 23px)",
            fontWeight: 700,
            lineHeight: 1.75,
            textShadow: "0 2px 22px rgba(0,0,0,0.58)"
          }}
        >
          光之谷把西洋占星、NASA JPL 天文資料與關係合盤流程整合在一起。
          我們不是要替你做決定，而是幫你把混亂的感情問題拆成能看懂的訊號，
          讓你知道該靠近、等待，還是把重心放回自己。
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.72, delay: 0.28, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <VideoContactButton isMobile={isMobile} />
        </motion.div>
      </div>
    </section>
  );
}

function VideoServicesSection({ isMobile }: { isMobile: boolean }) {
  return (
    <section
      id="reading-flow"
      style={{
        position: "relative",
        padding: isMobile
          ? "72px 22px 110px"
          : "110px clamp(42px, 5vw, 88px) 150px",
        color: "#f8fafc"
      }}
    >
      <div
        style={{
          maxWidth: 1120,
          margin: "0 auto",
          borderRadius: isMobile ? 28 : 44,
          border: "1px solid rgba(255,255,255,0.13)",
          background:
            "linear-gradient(145deg, rgba(12,12,12,0.42), rgba(12,12,12,0.18))",
          boxShadow:
            "0 36px 110px rgba(0,0,0,0.38), inset 0 1px 0 rgba(255,255,255,0.12)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          overflow: "hidden"
        }}
      >
        <div
          style={{
            padding: isMobile ? "32px 22px 20px" : "54px 56px 28px"
          }}
        >
          <div
            style={{
              color: "rgba(215,226,234,0.62)",
              fontSize: isMobile ? 11 : 12,
              fontWeight: 900,
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              marginBottom: 12
            }}
          >
            READING FLOW
          </div>
          <h3
            style={{
              margin: 0,
              fontFamily:
                "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
              fontSize: isMobile
                ? "clamp(40px, 12vw, 58px)"
                : "clamp(78px, 8.8vw, 150px)",
              fontWeight: 900,
              lineHeight: 0.93,
              letterSpacing: 0,
              textTransform: "uppercase",
              background: "linear-gradient(180deg, #ffffff 0%, #9aa4b1 100%)",
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              WebkitTextFillColor: "transparent"
            }}
          >
            從星盤到行動
            <br />
            看懂整段關係
          </h3>
        </div>

        <div>
          {VIDEO_SERVICE_ITEMS.map((item, index) => (
            <motion.div
              key={item.number}
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.12 }}
              transition={{
                duration: 0.62,
                delay: index * 0.08,
                ease: [0.25, 0.1, 0.25, 1]
              }}
              style={{
                display: "grid",
                gridTemplateColumns: isMobile ? "1fr" : "minmax(150px, 0.28fr) 1fr",
                gap: isMobile ? 12 : 34,
                alignItems: "center",
                padding: isMobile ? "26px 22px" : "34px 56px",
                borderTop: "1px solid rgba(255,255,255,0.12)"
              }}
            >
              <div
                style={{
                  color: "rgba(215,226,234,0.92)",
                  fontSize: isMobile
                    ? "clamp(46px, 14vw, 74px)"
                    : "clamp(72px, 8vw, 130px)",
                  fontWeight: 900,
                  lineHeight: 0.86,
                  letterSpacing: 0
                }}
              >
                {item.number}
              </div>
              <div>
                <h4
                  style={{
                    margin: 0,
                    color: "#fff",
                    fontSize: isMobile
                      ? "clamp(18px, 5vw, 26px)"
                      : "clamp(22px, 2.4vw, 38px)",
                    fontWeight: 900,
                    letterSpacing: "0.04em"
                  }}
                >
                  {item.title}
                </h4>
                <p
                  style={{
                    margin: "10px 0 0",
                    maxWidth: 720,
                    color: "rgba(215,226,234,0.66)",
                    fontSize: isMobile ? 13 : "clamp(14px, 1.15vw, 18px)",
                    fontWeight: 400,
                    lineHeight: 1.72
                  }}
                >
                  {item.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function VideoReviewStars({ rating, isMobile }: { rating: number; isMobile: boolean }) {
  return (
    <div
      aria-label={`${rating} out of 5 stars`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: isMobile ? 2 : 3,
        color: "#f8d56b"
      }}
    >
      {Array.from({ length: 5 }).map((_, index) => (
        <Star
          key={index}
          size={isMobile ? 12 : 14}
          strokeWidth={1.8}
          fill={index < rating ? "currentColor" : "transparent"}
        />
      ))}
    </div>
  );
}

function VideoReviewCard({
  review,
  index,
  isMobile
}: {
  review: VideoReviewCardData;
  index: number;
  isMobile: boolean;
}) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 34 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.18 }}
      transition={{
        duration: 0.7,
        delay: index * 0.06,
        ease: [0.25, 0.1, 0.25, 1]
      }}
      style={{
        position: "relative",
        display: "inline-block",
        width: "100%",
        marginBottom: isMobile ? 10 : 16,
        breakInside: "avoid",
        borderRadius: isMobile ? 18 : 28,
        border: "1px solid rgba(255,255,255,0.16)",
        background:
          "linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.045) 58%, rgba(255,255,255,0.09))",
        boxShadow:
          "0 28px 88px rgba(0,0,0,0.34), inset 0 1px 0 rgba(255,255,255,0.14)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        padding: isMobile ? "14px 12px" : "22px",
        overflow: "hidden"
      }}
    >
      <style>
        {`
          .pricing-package-card {
            transition:
              transform 260ms ease,
              box-shadow 260ms ease,
              background-color 260ms ease;
          }
          .pricing-package-card:hover {
            transform: translateY(-8px);
            background-color: rgba(255,255,255,0.12) !important;
            box-shadow:
              0 30px 92px rgba(0,0,0,0.34),
              0 0 0 1px rgba(255,255,255,0.18),
              inset 0 1px 0 rgba(255,255,255,0.22) !important;
          }
          .pricing-package-card:hover::before {
            opacity: 1;
          }
        `}
      </style>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 18% 10%, rgba(248,213,107,0.18), transparent 36%), radial-gradient(circle at 90% 82%, rgba(96,165,250,0.14), transparent 34%)",
          pointerEvents: "none"
        }}
      />

      <div style={{ position: "relative", zIndex: 2 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: isMobile ? 8 : 12,
            marginBottom: isMobile ? 10 : 16
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: isMobile ? 7 : 10,
              minWidth: 0
            }}
          >
            <div
              style={{
                width: isMobile ? 28 : 40,
                height: isMobile ? 28 : 40,
                borderRadius: "50%",
                display: "grid",
                placeItems: "center",
                flex: "0 0 auto",
                color: "#111827",
                background:
                  "linear-gradient(135deg, rgba(248,213,107,0.96), rgba(255,255,255,0.88))",
                boxShadow: "0 10px 24px rgba(248,213,107,0.14)",
                fontSize: isMobile ? 11 : 15,
                fontWeight: 900,
              }}
            >
              {review.name.slice(0, 1)}
            </div>
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  color: "#fff",
                  fontSize: isMobile ? 12 : 15,
                  fontWeight: 900,
                  lineHeight: 1.1
                }}
              >
                {review.name}
              </div>
            </div>
          </div>
          <VideoReviewStars rating={review.rating} isMobile={isMobile} />
        </div>

        <h4
          style={{
            margin: 0,
            color: "#fff",
            fontSize: isMobile ? "clamp(15px, 4.35vw, 20px)" : "clamp(19px, 2vw, 29px)",
            fontWeight: 900,
            lineHeight: 1.14,
            letterSpacing: 0
          }}
        >
          {review.title}
        </h4>
        <p
          style={{
            margin: isMobile ? "9px 0 0" : "11px 0 0",
            color: "rgba(215,226,234,0.72)",
            fontSize: isMobile ? 11 : 14,
            lineHeight: isMobile ? 1.58 : 1.64,
            fontWeight: 500
          }}
        >
          {review.description}
        </p>
      </div>
    </motion.article>
  );
}

function VideoTestimonialCard({
  item,
  isMobile
}: {
  item: (typeof VIDEO_TESTIMONIAL_PLACEHOLDERS)[number];
  isMobile: boolean;
}) {
  return (
    <motion.article
      data-video-testimonial-card
      className="video-testimonial-card"
      style={{
        flex: "0 0 auto",
        width: isMobile ? "78vw" : 360,
        position: "relative",
        borderRadius: isMobile ? 24 : 34,
        border: "1px solid rgba(255,255,255,0.16)",
        background:
          "linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.045) 58%, rgba(255,255,255,0.08))",
        boxShadow:
          "0 28px 88px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.13)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        padding: isMobile ? 14 : 18,
        overflow: "hidden",
        boxSizing: "border-box",
        scrollSnapAlign: isMobile ? "center" : "start",
        transition: "border-color 240ms ease, background-color 240ms ease"
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 16% 8%, rgba(248,213,107,0.13), transparent 34%), radial-gradient(circle at 92% 84%, rgba(96,165,250,0.13), transparent 36%)",
          pointerEvents: "none"
        }}
      />

      <div
        className="video-testimonial-thumb"
        style={{
          aspectRatio: "4 / 3",
          position: "relative",
          overflow: "hidden",
          borderRadius: isMobile ? 18 : 26,
          marginBottom: isMobile ? 16 : 20,
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.1)"
        }}
      >
        <img
          src={item.image}
          alt={`${item.name} video testimonial placeholder`}
          loading="lazy"
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
            opacity: 0.76,
            transition: "transform 700ms ease"
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "linear-gradient(180deg, rgba(4,8,16,0.08) 0%, rgba(4,8,16,0.48) 100%)"
          }}
        />
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
            width: isMobile ? 54 : 62,
            height: isMobile ? 54 : 62,
            borderRadius: "50%",
            display: "grid",
            placeItems: "center",
            color: "#111827",
            background:
              "linear-gradient(145deg, rgba(255,255,255,0.94), rgba(255,255,255,0.64))",
            border: "1px solid rgba(255,255,255,0.36)",
            boxShadow: "0 18px 42px rgba(0,0,0,0.28)"
          }}
        >
          <Play
            size={isMobile ? 20 : 24}
            strokeWidth={2.4}
            fill="currentColor"
            style={{ marginLeft: 3 }}
          />
        </div>
      </div>

      <p
        style={{
          margin: "0 0 12px",
          color: "rgba(248,213,107,0.84)",
          fontSize: isMobile ? 10 : 12,
          fontWeight: 900,
          letterSpacing: "0.12em",
          textTransform: "uppercase"
        }}
      >
        {item.name} · {item.meta}
      </p>

      <h4
        style={{
          margin: 0,
          minHeight: isMobile ? 84 : 100,
          color: "#fff",
          fontSize: isMobile ? "clamp(18px, 5vw, 24px)" : "clamp(22px, 2vw, 32px)",
          fontWeight: 900,
          lineHeight: 1.12,
          letterSpacing: 0,
          display: "-webkit-box",
          WebkitLineClamp: 3,
          WebkitBoxOrient: "vertical",
          overflow: "hidden"
        }}
      >
        {item.title}
      </h4>

      <button
        type="button"
        className="video-testimonial-link"
        style={{
          marginTop: isMobile ? 18 : 22,
          border: "1px solid rgba(248,213,107,0.18)",
          borderRadius: 999,
          background: "rgba(248,213,107,0.1)",
          color: "rgba(248,213,107,0.92)",
          padding: isMobile ? "8px 12px" : "9px 14px",
          fontSize: isMobile ? 10 : 12,
          fontWeight: 900,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          cursor: "default",
          position: "relative",
          display: "inline-flex"
        }}
      >
        影片見證
      </button>
    </motion.article>
  );
}

function VideoTestimonialsSection({ isMobile }: { isMobile: boolean }) {
  const carouselRef = useRef<HTMLDivElement | null>(null);

  const scrollCarousel = (direction: -1 | 1) => {
    const carousel = carouselRef.current;
    if (!carousel) return;

    const firstCard = carousel.querySelector<HTMLElement>("[data-video-testimonial-card]");
    const gap = Number.parseFloat(window.getComputedStyle(carousel).columnGap || "24");
    const cardWidth = firstCard?.getBoundingClientRect().width ?? (isMobile ? window.innerWidth * 0.78 : 360);
    carousel.scrollBy({
      left: direction * (cardWidth + gap),
      behavior: "smooth"
    });
  };

  return (
    <section
      id="reviews"
      style={{
        position: "relative",
        width: "100%",
        marginBottom: isMobile ? 72 : 104,
        color: "#fff"
      }}
    >
      <style>
        {`
          .video-testimonial-carousel::-webkit-scrollbar {
            display: none;
          }
          .video-testimonial-card:hover {
            border-color: rgba(248,213,107,0.32) !important;
            background-color: rgba(255,255,255,0.12) !important;
          }
          .video-testimonial-card:hover img {
            transform: scale(1.05);
          }
        `}
      </style>

      <div
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          padding: 0
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 36 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.78, ease: [0.25, 0.1, 0.25, 1] }}
          style={{
            display: "grid",
            gridTemplateColumns: isMobile ? "1fr" : "1fr auto",
            gap: isMobile ? 22 : 34,
            alignItems: "end",
            marginBottom: isMobile ? 30 : 46
          }}
        >
          <div>
            <div
              style={{
                color: "rgba(248,213,107,0.86)",
                fontSize: isMobile ? 11 : 12,
                fontWeight: 900,
                letterSpacing: "0.24em",
                textTransform: "uppercase",
                marginBottom: 14
              }}
            >
              VIDEO TESTIMONIALS
            </div>
            <h3
              style={{
                margin: 0,
                fontFamily:
                  "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
                fontSize: isMobile
                  ? "clamp(42px, 13vw, 64px)"
                  : "clamp(72px, 8vw, 128px)",
                fontWeight: 900,
                lineHeight: 0.9,
                letterSpacing: 0,
                background: "linear-gradient(180deg, #f4f8ff 0%, #7f8794 100%)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                WebkitTextFillColor: "transparent"
              }}
            >
              用戶影片見證
            </h3>
          </div>

          <p
            style={{
              margin: 0,
              maxWidth: isMobile ? "100%" : 330,
              color: "rgba(215,226,234,0.68)",
              fontSize: isMobile ? 13 : 15,
              lineHeight: 1.72,
              fontWeight: 600
            }}
          >
            每一段關係都有自己的轉折，保留給真實用戶分享看見答案後的改變。
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.18 }}
          transition={{ duration: 0.74, delay: 0.38, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <div
            ref={carouselRef}
            className="video-testimonial-carousel"
            onWheel={(event) => {
              if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;

              window.scrollBy({
                top: event.deltaY,
                behavior: "auto"
              });
              event.preventDefault();
            }}
            style={{
              display: "flex",
              gap: isMobile ? 18 : 24,
              overflowX: "auto",
              overflowY: "hidden",
              scrollSnapType: "x mandatory",
              scrollBehavior: "smooth",
              overscrollBehaviorY: "auto",
              scrollbarWidth: "none",
              msOverflowStyle: "none",
              WebkitOverflowScrolling: "touch",
              padding: isMobile ? "2px 6px 8px" : "2px 4px 10px"
            }}
          >
            {VIDEO_TESTIMONIAL_PLACEHOLDERS.map((item) => (
              <VideoTestimonialCard
                key={`${item.name}-${item.meta}`}
                item={item}
                isMobile={isMobile}
              />
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.62, delay: 0.48, ease: [0.25, 0.1, 0.25, 1] }}
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 14,
            marginTop: isMobile ? 28 : 38
          }}
        >
          {[
            { label: "Previous video testimonial", icon: ArrowLeft, direction: -1 as const },
            { label: "Next video testimonial", icon: ArrowRight, direction: 1 as const }
          ].map(({ label, icon: Icon, direction }) => (
            <button
              key={label}
              type="button"
              aria-label={label}
              onClick={() => scrollCarousel(direction)}
              style={{
                width: 56,
                height: 56,
                borderRadius: "50%",
                border: "1px solid rgba(248,213,107,0.2)",
                background: "rgba(255,255,255,0.08)",
                color: "rgba(248,213,107,0.94)",
                display: "grid",
                placeItems: "center",
                cursor: "pointer",
                backdropFilter: "blur(12px)",
                WebkitBackdropFilter: "blur(12px)",
                transition: "background-color 180ms ease, border-color 180ms ease"
              }}
              onMouseEnter={(event) => {
                event.currentTarget.style.background = "rgba(248,213,107,0.14)";
                event.currentTarget.style.borderColor = "rgba(248,213,107,0.42)";
              }}
              onMouseLeave={(event) => {
                event.currentTarget.style.background = "rgba(255,255,255,0.08)";
                event.currentTarget.style.borderColor = "rgba(248,213,107,0.2)";
              }}
            >
              <Icon size={22} strokeWidth={2.2} />
            </button>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function PricingPackagesSection({ isMobile }: { isMobile: boolean }) {
  const pricingIcyBlueSoft = "rgba(125,223,255,0.14)";
  const pricingLavenderSoft = "rgba(183,143,255,0.16)";
  const pricingLavenderBorder = "rgba(183,143,255,0.34)";

  const packages = [
    {
      eyebrow: "Relationship Reading",
      title: "完整關係星盤解讀",
      price: "NT$1,280",
      note: "一次完整解讀",
      description:
        "這份解讀會幫你把混亂的感情訊號整理成清楚方向。",
      features: [
        "星盤定位：分開看懂你和他的關係習慣",
        "契合度分析：整理吸引、情緒安全、溝通與壓力點",
        "核心問題解讀：回答你最放不下的那句話",
        "時機判讀：整理適合開口的時間感與聯絡節奏",
        "行動方向：要不要聯絡、怎麼靠近、什麼先不要做"
      ],
      cta: "立即購買",
      featured: true
    }
  ];

  return (
    <section
      id="pricing"
      style={{
        position: "relative",
        width: "100%",
        scrollMarginTop: isMobile ? 72 : 88,
        marginBottom: isMobile ? 82 : 120,
        color: "#fff",
        overflow: "hidden"
      }}
    >
      <div
        style={{
          position: "absolute",
          top: isMobile ? 78 : 40,
          left: "50%",
          transform: "translateX(-50%)",
          width: isMobile ? 520 : 900,
          height: isMobile ? 260 : 420,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(37,99,235,0.24) 0%, rgba(37,99,235,0.06) 42%, rgba(37,99,235,0) 70%)",
          filter: "blur(12px)",
          pointerEvents: "none"
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 36 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.18 }}
        transition={{ duration: 0.78, ease: [0.25, 0.1, 0.25, 1] }}
        style={{
          position: "relative",
          zIndex: 2,
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr" : "1fr auto",
          gap: isMobile ? 22 : 34,
          alignItems: "end",
          marginBottom: isMobile ? 32 : 48
        }}
      >
        <div>
          <div
            style={{
              color: "rgba(248,213,107,0.86)",
              fontSize: isMobile ? 11 : 12,
              fontWeight: 900,
              letterSpacing: "0.24em",
              textTransform: "uppercase",
              marginBottom: 14
            }}
          >
            RELATIONSHIP READING
          </div>
          <h3
            style={{
              margin: 0,
              fontFamily:
                "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
              fontSize: isMobile
                ? "clamp(42px, 13vw, 64px)"
                : "clamp(72px, 8vw, 128px)",
              fontWeight: 900,
              lineHeight: 0.9,
              letterSpacing: 0,
              background: "linear-gradient(180deg, #f4f8ff 0%, #7f8794 100%)",
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              WebkitTextFillColor: "transparent"
            }}
          >
            完整解讀
          </h3>
        </div>

        <p
          style={{
            margin: 0,
            maxWidth: isMobile ? "100%" : 360,
            color: "rgba(215,226,234,0.68)",
            fontSize: isMobile ? 13 : 15,
            lineHeight: 1.72,
            fontWeight: 600
          }}
        >
          一次解讀，完整看懂你們的關係
        </p>
      </motion.div>

      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr" : "minmax(0, min(100%, 620px))",
          justifyContent: "center",
          gap: isMobile ? 18 : 26
        }}
      >
        {packages.map((item, index) => (
          <motion.article
            key={item.title}
            className="liquid-glass pricing-package-card"
            initial={{ opacity: 0, y: 34 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.22 }}
            transition={{
              duration: 0.72,
              delay: index * 0.08,
              ease: [0.25, 0.1, 0.25, 1]
            }}
            style={{
              position: "relative",
              borderRadius: isMobile ? 28 : 38,
              minHeight: isMobile ? "auto" : 500,
              padding: isMobile ? 24 : 34,
              background: item.featured
                ? "linear-gradient(145deg, rgba(255,255,255,0.17), rgba(37,99,235,0.11) 44%, rgba(255,255,255,0.06))"
                : "linear-gradient(145deg, rgba(255,255,255,0.11), rgba(255,255,255,0.035) 52%, rgba(255,255,255,0.07))",
              boxShadow:
                "0 26px 84px rgba(0,0,0,0.32), inset 0 1px 0 rgba(255,255,255,0.14)",
              backdropFilter: "blur(18px)",
              WebkitBackdropFilter: "blur(18px)",
              isolation: "isolate",
              overflow: "hidden"
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: item.featured
                  ? "radial-gradient(circle at 62% 24%, rgba(182,0,168,0.12), transparent 44%), radial-gradient(circle at 28% 76%, rgba(190,76,0,0.1), transparent 46%)"
                  : "radial-gradient(circle at 26% 22%, rgba(118,33,176,0.1), transparent 44%), radial-gradient(circle at 70% 72%, rgba(190,76,0,0.07), transparent 46%)",
                pointerEvents: "none"
              }}
            />

            {item.featured ? (
              <div
                style={{
                  position: "absolute",
                  top: isMobile ? 18 : 24,
                  right: isMobile ? 18 : 24,
                  borderRadius: 999,
                  border: `1px solid ${pricingLavenderBorder}`,
                  background: pricingLavenderSoft,
                  color: "#fff",
                  boxShadow: "0 0 22px rgba(183,143,255,0.16)",
                  padding: "7px 11px",
                  fontSize: 10,
                  fontWeight: 900,
                  letterSpacing: "0.14em",
                  textTransform: "uppercase"
                }}
              >
                Complete Reading
              </div>
            ) : null}

            <div style={{ position: "relative", zIndex: 2 }}>
              <p
                style={{
                  margin: "0 0 12px",
                  color: "rgba(215,226,234,0.58)",
                  fontSize: isMobile ? 11 : 12,
                  fontWeight: 900,
                  letterSpacing: "0.14em",
                  textTransform: "uppercase"
                }}
              >
                {item.eyebrow}
              </p>
              <h4
                style={{
                  margin: 0,
                  color: "#fff",
                  fontSize: isMobile ? 28 : 34,
                  fontWeight: 900,
                  lineHeight: 1.08,
                  letterSpacing: 0
                }}
              >
                {item.title}
              </h4>
              <div
                style={{
                  display: "flex",
                  alignItems: "end",
                  flexWrap: "wrap",
                  gap: 12,
                  marginTop: isMobile ? 20 : 26,
                  marginBottom: 14
                }}
              >
                <div
                  style={{
                    color: "#fff",
                    fontSize: isMobile ? "clamp(44px, 12vw, 62px)" : 74,
                    fontWeight: 900,
                    lineHeight: 0.88,
                    letterSpacing: "-0.02em"
                  }}
                >
                  {item.price}
                </div>
                <div
                  style={{
                    color: "rgba(248,213,107,0.82)",
                    fontSize: isMobile ? 12 : 13,
                    fontWeight: 900,
                    letterSpacing: "0.12em",
                    textTransform: "uppercase",
                    paddingBottom: 5
                  }}
                >
                  {item.note}
                </div>
              </div>
              <p
                style={{
                  margin: 0,
                  maxWidth: 460,
                  color: "rgba(215,226,234,0.66)",
                  fontSize: isMobile ? 13 : 15,
                  lineHeight: 1.72,
                  fontWeight: 600
                }}
              >
                {item.description}
              </p>

              <div
                style={{
                  display: "grid",
                  gap: isMobile ? 14 : 17,
                  marginTop: isMobile ? 28 : 36,
                  marginBottom: isMobile ? 30 : 42
                }}
              >
                {item.features.map((feature) => (
                  <div
                    key={feature}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "30px 1fr",
                      gap: 12,
                      alignItems: "center",
                      color: "rgba(248,250,252,0.86)",
                      fontSize: isMobile ? 13 : 15,
                      fontWeight: 800,
                      lineHeight: 1.45
                    }}
                  >
                    <span
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: "50%",
                        display: "grid",
                        placeItems: "center",
                        background: item.featured
                          ? pricingIcyBlueSoft
                          : "rgba(255,255,255,0.12)",
                        color: item.featured
                          ? "rgba(255,255,255,0.92)"
                          : "rgba(255,255,255,0.84)"
                      }}
                    >
                      <Check size={15} strokeWidth={3} />
                    </span>
                    {feature}
                  </div>
                ))}
              </div>

              <a
                href={READING_CHECKOUT_URL}
                rel="nofollow"
                className={item.featured ? "hero-glass-cta" : undefined}
                style={{
                  width: isMobile ? "100%" : "auto",
                  minWidth: isMobile ? "auto" : 210,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  border: item.featured
                    ? undefined
                    : "1px solid rgba(255,255,255,0.2)",
                  borderRadius: 999,
                  background: item.featured
                    ? undefined
                    : "rgba(255,255,255,0.92)",
                  color: item.featured ? "#fff" : "#111827",
                  padding: isMobile ? "14px 20px" : "14px 28px",
                  fontSize: isMobile ? 13 : 14,
                  fontWeight: 900,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  textDecoration: "none",
                  cursor: "pointer",
                  boxShadow: item.featured
                    ? undefined
                    : "0 16px 36px rgba(0,0,0,0.24)"
                }}
              >
                {item.featured ? (
                  <span className="hero-glass-cta-shine" aria-hidden="true" />
                ) : null}
                <span>{item.cta}</span>
              </a>
            </div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}

function FaqSection({ isMobile }: { isMobile: boolean }) {
  const [openFaqIndex, setOpenFaqIndex] = useState(0);

  const faqItems = [
    {
      question: "這是塔羅還是星盤？",
      answer:
        "這不是塔羅抽牌，而是以雙方出生資料建立西洋星盤與合盤結構，從互動模式、吸引點、壓力點與時機窗口來解讀關係。"
    },
    {
      question: "需要對方的出生時間嗎？",
      answer:
        "有完整出生時間會更準確；如果只有生日，也可以先做基礎解讀，但時機與宮位細節會以可判讀範圍呈現。"
    },
    {
      question: "分析會告訴我他會不會回來嗎？",
      answer:
        "會看復合機會、對方狀態與適合行動的時機，但不會用絕對保證包裝結果；重點是讓你看清局勢並知道下一步怎麼做。"
    },
    {
      question: "付款後怎麼填資料與查看結果？",
      answer:
        "付款確認後，安全連結會寄到結帳信箱。完成雙方資料與主要問題後，頁面會顯示處理進度；解讀完成時會再寄信通知，之後也能用同一連結回到已鎖定的結果。"
    },
    {
      question: "我的資料會公開嗎？",
      answer:
        "不會。出生資料與關係內容只用於本次解讀，不會公開在用戶回饋或影片見證區。"
    },
    {
      question: "這份 NT$1,280 解讀包含什麼？",
      answer:
        "會包含我的星盤、他的星盤、兩個人的關係契合度分析、核心問題解讀、判斷理由、現在該怎麼做、時間感與最佳聯繫時間，最後整理成清楚結論。"
    },
    {
      question: "出生城市一定要填嗎？",
      answer:
        "不一定。付款後可從支援城市清單選擇；若不知道或不在清單，可以留空。解讀仍會使用可可靠計算的部分，並自動避開需要精準地點的宮位與角度判斷。"
    },
    {
      question: "最佳聯繫時間會精準到哪裡？",
      answer:
        "這份解讀會提供聯絡節奏、窗口與注意事項，幫你判斷要靠近、等待還是降低壓力；不會把任何日期包裝成保證復合或保證回覆。"
    },
    {
      question: "如果我只想知道他還愛不愛我，適合做嗎？",
      answer:
        "適合，但解讀不會替對方下絕對結論。它會從星盤互動、情緒反應、吸引與壓力點，判斷這段關係還有哪些連結、哪些地方正在退縮，以及你現在最該看清什麼。"
    }
  ];

  return (
    <section
      id="faq"
      style={{
        position: "relative",
        width: "100%",
        marginBottom: isMobile ? 78 : 112,
        color: "#fff",
        boxSizing: "border-box"
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 34 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.2 }}
        transition={{ duration: 0.76, ease: [0.25, 0.1, 0.25, 1] }}
        style={{
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr" : "minmax(0, 0.92fr) minmax(0, 1.12fr)",
          gap: isMobile ? 30 : 76,
          alignItems: "start"
        }}
      >
        <div>
          <div
            style={{
              color: "rgba(248,213,107,0.86)",
              fontSize: isMobile ? 11 : 12,
              fontWeight: 900,
              letterSpacing: "0.24em",
              textTransform: "uppercase",
              marginBottom: 14
            }}
          >
            FAQ
          </div>
          <h3
            style={{
              margin: 0,
              fontFamily:
                "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
              fontSize: isMobile
                ? "clamp(42px, 13vw, 64px)"
                : "clamp(72px, 8vw, 128px)",
              fontWeight: 900,
              lineHeight: 0.9,
              letterSpacing: 0,
              background: "linear-gradient(180deg, #f4f8ff 0%, #7f8794 100%)",
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              WebkitTextFillColor: "transparent"
            }}
          >
            常見問題
          </h3>
          <p
            style={{
              margin: isMobile ? "18px 0 0" : "24px 0 0",
              maxWidth: 420,
              color: "rgba(215,226,234,0.68)",
              fontSize: isMobile ? 13 : 15,
              lineHeight: 1.72,
              fontWeight: 600
            }}
          >
            在開始解讀前，先把資料、準確度、隱私與方案差異說清楚。
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gap: 0,
            borderTop: "1px solid rgba(255,255,255,0.18)"
          }}
        >
          {faqItems.map((item, index) => {
            const isOpen = openFaqIndex === index;

            return (
              <motion.article
                key={item.question}
                initial={{ opacity: 0, y: 22 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.18 }}
                transition={{
                  duration: 0.58,
                  delay: index * 0.035,
                  ease: [0.25, 0.1, 0.25, 1]
                }}
                style={{
                  borderBottom: "1px solid rgba(255,255,255,0.14)"
                }}
              >
                <button
                  type="button"
                  aria-expanded={isOpen}
                  onClick={() => setOpenFaqIndex(isOpen ? -1 : index)}
                  style={{
                    width: "100%",
                    border: 0,
                    background: "transparent",
                    color: "#fff",
                    display: "grid",
                    gridTemplateColumns: "1fr auto",
                    alignItems: "center",
                    gap: 22,
                    padding: isMobile ? "18px 0" : "21px 0",
                    textAlign: "left",
                    cursor: "pointer"
                  }}
                >
                  <span
                    style={{
                      fontSize: isMobile ? 15 : 17,
                      lineHeight: 1.35,
                      fontWeight: 800,
                      letterSpacing: 0
                    }}
                  >
                    {item.question}
                  </span>
                  <span
                    style={{
                      width: 24,
                      height: 24,
                      display: "grid",
                      placeItems: "center",
                      color: isOpen ? "rgba(248,213,107,0.94)" : "rgba(255,255,255,0.82)",
                      fontSize: isMobile ? 24 : 25,
                      fontWeight: 300,
                      lineHeight: 1
                    }}
                    aria-hidden="true"
                  >
                    {isOpen ? "−" : "+"}
                  </span>
                </button>

                {isOpen ? (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.22 }}
                    style={{
                      padding: isMobile ? "0 0 20px" : "0 42px 24px 0",
                      color: "rgba(215,226,234,0.68)",
                      fontSize: isMobile ? 13 : 14,
                      lineHeight: 1.68,
                      fontWeight: 600
                    }}
                  >
                    {item.answer}
                  </motion.div>
                ) : null}
              </motion.article>
            );
          })}
        </div>
      </motion.div>
    </section>
  );
}

function VideoReviewsSection({ isMobile }: { isMobile: boolean }) {
  const [displayReviews, setDisplayReviews] = useState<VideoReviewCardData[]>(VIDEO_REVIEW_CARDS);
  const [reviewName, setReviewName] = useState("");
  const [reviewEmail, setReviewEmail] = useState("");
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewTitle, setReviewTitle] = useState("");
  const [reviewBody, setReviewBody] = useState("");
  const [reviewSubmitState, setReviewSubmitState] = useState<
    "idle" | "submitting" | "success" | "error"
  >("idle");
  const [reviewSubmitMessage, setReviewSubmitMessage] = useState("");

  const reviewInputStyle: CSSProperties = {
    width: "100%",
    border: "1px solid rgba(255,255,255,0.14)",
    borderRadius: isMobile ? 16 : 18,
    background: "rgba(255,255,255,0.08)",
    color: "#fff",
    outline: "none",
    padding: isMobile ? "13px 14px" : "15px 16px",
    fontSize: isMobile ? 14 : 15,
    fontWeight: 700,
    boxSizing: "border-box"
  };

  const canSubmitReview =
    reviewSubmitState !== "submitting" &&
    reviewName.trim().length > 0 &&
    reviewTitle.trim().length > 0 &&
    reviewBody.trim().length > 0;

  useEffect(() => {
    let isCancelled = false;

    async function loadPublicReviews() {
      try {
        const response = await fetch(`${RELATIONSHIP_REVIEW_API_URL}?appKey=relationship-app`, {
          cache: "no-store"
        });
        const payload = (await response.json().catch(() => null)) as
          | { reviews?: PublicRelationshipReview[] }
          | null;

        if (!response.ok || !Array.isArray(payload?.reviews)) return;

        const nextReviews = payload.reviews
          .map(normalizePublicReview)
          .filter((review) => review.description.length > 0);
        if (!isCancelled && nextReviews.length > 0) {
          setDisplayReviews(nextReviews);
        }
      } catch {
        // Keep the local fallback cards when the review backend is unavailable.
      }
    }

    void loadPublicReviews();
    return () => {
      isCancelled = true;
    };
  }, []);

  async function submitRelationshipReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmitReview) {
      setReviewSubmitState("error");
      setReviewSubmitMessage("請填寫暱稱、標題與回饋內容。");
      return;
    }

    setReviewSubmitState("submitting");
    setReviewSubmitMessage("");

    try {
      const response = await fetch(RELATIONSHIP_REVIEW_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          appKey: "relationship-app",
          source: "valley-of-light-review-section",
          name: reviewName.trim(),
          email: reviewEmail.trim() || undefined,
          rating: reviewRating,
          title: reviewTitle.trim(),
          body: reviewBody.trim()
        })
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(
          payload && typeof payload.error === "string"
            ? payload.error
            : "送出評論失敗，請稍後再試。"
        );
      }

      setReviewName("");
      setReviewEmail("");
      setReviewRating(5);
      setReviewTitle("");
      setReviewBody("");
      setReviewSubmitState("success");
      setReviewSubmitMessage("已收到你的評論，審核後會公開顯示。");
    } catch (error) {
      setReviewSubmitState("error");
      setReviewSubmitMessage(
        error instanceof Error ? error.message : "送出評論失敗，請稍後再試。"
      );
    }
  }

  return (
    <section
      style={{
        position: "relative",
        zIndex: 3,
        padding: isMobile
          ? "76px 18px 130px"
          : "112px clamp(34px, 5vw, 78px) 160px",
        background:
          "linear-gradient(180deg, rgba(12,12,12,0.1) 0%, rgba(12,12,12,0.72) 20%, rgba(12,12,12,0.72) 100%)",
        borderTopLeftRadius: isMobile ? 36 : 58,
        borderTopRightRadius: isMobile ? 36 : 58,
        marginTop: isMobile ? -28 : -54
      }}
    >
      <div
        style={{
          maxWidth: 1180,
          margin: "0 auto"
        }}
      >
        <PricingPackagesSection isMobile={isMobile} />

        <FaqSection isMobile={isMobile} />

        <VideoTestimonialsSection isMobile={isMobile} />

        <motion.div
          initial={{ opacity: 0, y: 36 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.78, ease: [0.25, 0.1, 0.25, 1] }}
          style={{
            display: "grid",
            gridTemplateColumns: isMobile ? "1fr" : "1fr auto",
            gap: isMobile ? 26 : 34,
            alignItems: "end",
            marginBottom: isMobile ? 36 : 58
          }}
        >
          <div>
            <div
              style={{
                color: "rgba(248,213,107,0.86)",
                fontSize: isMobile ? 11 : 12,
                fontWeight: 900,
                letterSpacing: "0.24em",
                textTransform: "uppercase",
                marginBottom: 14
              }}
            >
              CUSTOMER REVIEWS
            </div>
            <h3
              style={{
                margin: 0,
                fontFamily:
                  "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
                fontSize: isMobile
                  ? "clamp(42px, 13vw, 64px)"
                  : "clamp(72px, 8vw, 128px)",
                fontWeight: 900,
                lineHeight: 0.9,
                letterSpacing: 0,
                background: "linear-gradient(180deg, #f4f8ff 0%, #7f8794 100%)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                WebkitTextFillColor: "transparent"
              }}
            >
              用戶真實回饋
            </h3>
          </div>

          <div
            style={{
              borderRadius: isMobile ? 24 : 30,
              border: "1px solid rgba(248,213,107,0.2)",
              background: "rgba(255,255,255,0.08)",
              boxShadow: "0 22px 70px rgba(0,0,0,0.26)",
              backdropFilter: "blur(14px)",
              WebkitBackdropFilter: "blur(14px)",
              padding: isMobile ? "18px 20px" : "22px 26px",
              minWidth: isMobile ? "auto" : 250
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 10,
                color: "#fff"
              }}
            >
              <span style={{ fontSize: isMobile ? 42 : 52, fontWeight: 900, lineHeight: 1 }}>
                4.9
              </span>
              <span style={{ color: "rgba(215,226,234,0.62)", fontWeight: 800 }}>
                / 5.0
              </span>
            </div>
            <div style={{ marginTop: 8 }}>
              <VideoReviewStars rating={5} isMobile={isMobile} />
            </div>
            <div
              style={{
                marginTop: 10,
                color: "rgba(215,226,234,0.62)",
                fontSize: isMobile ? 12 : 13,
                fontWeight: 700,
                lineHeight: 1.5
              }}
            >
              來自 1萬+ 次關係解讀回饋
            </div>
          </div>
        </motion.div>

        <div
          style={{
            columnCount: isMobile ? 2 : 3,
            columnGap: isMobile ? 14 : 22,
            width: "100%"
          }}
        >
          {displayReviews.map((review, index) => (
            <VideoReviewCard
              key={`${review.name}-${review.title}`}
              review={review}
              index={index}
              isMobile={isMobile}
            />
          ))}
        </div>

        <motion.form
          onSubmit={submitRelationshipReview}
          initial={{ opacity: 0, y: 34 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.18 }}
          transition={{ duration: 0.74, ease: [0.25, 0.1, 0.25, 1] }}
          style={{
            marginTop: isMobile ? 28 : 38,
            borderRadius: isMobile ? 30 : 42,
            border: "1px solid rgba(248,213,107,0.2)",
            background:
              "linear-gradient(145deg, rgba(255,255,255,0.14), rgba(255,255,255,0.045) 58%, rgba(248,213,107,0.08))",
            boxShadow:
              "0 30px 92px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.13)",
            backdropFilter: "blur(18px)",
            WebkitBackdropFilter: "blur(18px)",
            padding: isMobile ? 22 : 34,
            overflow: "hidden"
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: isMobile ? "1fr" : "0.85fr 1.15fr",
              gap: isMobile ? 22 : 34,
              alignItems: "start"
            }}
          >
            <div>
              <div
                style={{
                  color: "rgba(248,213,107,0.9)",
                  fontSize: isMobile ? 11 : 12,
                  fontWeight: 900,
                  letterSpacing: "0.22em",
                  textTransform: "uppercase",
                  marginBottom: 14
                }}
              >
                WRITE A REVIEW
              </div>
              <h4
                style={{
                  margin: 0,
                  color: "#fff",
                  fontSize: isMobile ? "clamp(30px, 9vw, 42px)" : "clamp(38px, 4vw, 64px)",
                  fontWeight: 900,
                  lineHeight: 1.04,
                  letterSpacing: 0
                }}
              >
                分享你的關係解讀回饋
              </h4>
              <p
                style={{
                  margin: "16px 0 0",
                  color: "rgba(215,226,234,0.66)",
                  fontSize: isMobile ? 14 : 16,
                  lineHeight: 1.72,
                  fontWeight: 500
                }}
              >
                留下星級與感受，審核後會出現在用戶真實回饋區。
              </p>
            </div>

            <div style={{ display: "grid", gap: isMobile ? 14 : 16 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
                  gap: isMobile ? 14 : 16
                }}
              >
                <label style={{ display: "grid", gap: 8 }}>
                  <span style={{ color: "rgba(215,226,234,0.72)", fontSize: 12, fontWeight: 900 }}>
                    暱稱
                  </span>
                  <input
                    value={reviewName}
                    onChange={(event) => setReviewName(event.target.value)}
                    placeholder="例如 Mandy"
                    style={reviewInputStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: 8 }}>
                  <span style={{ color: "rgba(215,226,234,0.72)", fontSize: 12, fontWeight: 900 }}>
                    Email（選填）
                  </span>
                  <input
                    type="email"
                    value={reviewEmail}
                    onChange={(event) => setReviewEmail(event.target.value)}
                    placeholder="只供審核聯絡"
                    style={reviewInputStyle}
                  />
                </label>
              </div>

              <div>
                <span style={{ color: "rgba(215,226,234,0.72)", fontSize: 12, fontWeight: 900 }}>
                  星級評分
                </span>
                <div style={{ display: "flex", gap: 8, marginTop: 9 }}>
                  {Array.from({ length: 5 }).map((_, index) => {
                    const starValue = index + 1;
                    const isActive = starValue <= reviewRating;
                    return (
                      <button
                        key={starValue}
                        type="button"
                        onClick={() => setReviewRating(starValue)}
                        aria-label={`${starValue} star rating`}
                        style={{
                          width: isMobile ? 38 : 42,
                          height: isMobile ? 38 : 42,
                          borderRadius: "50%",
                          border: isActive
                            ? "1px solid rgba(248,213,107,0.54)"
                            : "1px solid rgba(255,255,255,0.14)",
                          background: isActive
                            ? "rgba(248,213,107,0.16)"
                            : "rgba(255,255,255,0.06)",
                          color: isActive ? "#f8d56b" : "rgba(215,226,234,0.5)",
                          display: "grid",
                          placeItems: "center",
                          cursor: "pointer"
                        }}
                      >
                        <Star
                          size={isMobile ? 18 : 20}
                          strokeWidth={1.8}
                          fill={isActive ? "currentColor" : "transparent"}
                        />
                      </button>
                    );
                  })}
                </div>
              </div>

              <label style={{ display: "grid", gap: 8 }}>
                <span style={{ color: "rgba(215,226,234,0.72)", fontSize: 12, fontWeight: 900 }}>
                  評論標題
                </span>
                <input
                  value={reviewTitle}
                  onChange={(event) => setReviewTitle(event.target.value)}
                  placeholder="一句話形容這次解讀"
                  style={reviewInputStyle}
                />
              </label>

              <label style={{ display: "grid", gap: 8 }}>
                <span style={{ color: "rgba(215,226,234,0.72)", fontSize: 12, fontWeight: 900 }}>
                  你的回饋
                </span>
                <textarea
                  value={reviewBody}
                  onChange={(event) => setReviewBody(event.target.value)}
                  placeholder="分享你看完後更清楚的地方、行動方向或感受。"
                  rows={isMobile ? 5 : 6}
                  style={{
                    ...reviewInputStyle,
                    resize: "vertical",
                    lineHeight: 1.7
                  }}
                />
              </label>

              <div
                style={{
                  display: "flex",
                  flexDirection: isMobile ? "column" : "row",
                  alignItems: isMobile ? "stretch" : "center",
                  gap: 14,
                  justifyContent: "space-between"
                }}
              >
                <button
                  type="submit"
                  disabled={!canSubmitReview}
                  style={{
                    border: "none",
                    borderRadius: 999,
                    padding: isMobile ? "15px 22px" : "16px 30px",
                    color: canSubmitReview ? "#111827" : "rgba(215,226,234,0.44)",
                    background: canSubmitReview
                      ? "linear-gradient(135deg, #f8d56b, #fff3bf)"
                      : "rgba(255,255,255,0.08)",
                    fontSize: isMobile ? 15 : 16,
                    fontWeight: 900,
                    cursor: canSubmitReview ? "pointer" : "not-allowed",
                    boxShadow: canSubmitReview
                      ? "0 18px 42px rgba(248,213,107,0.18)"
                      : "none"
                  }}
                >
                  {reviewSubmitState === "submitting" ? "送出中..." : "送出評論"}
                </button>

                {reviewSubmitMessage ? (
                  <div
                    role="status"
                    style={{
                      color:
                        reviewSubmitState === "success"
                          ? "rgba(187,247,208,0.94)"
                          : "rgba(252,165,165,0.96)",
                      fontSize: isMobile ? 13 : 14,
                      fontWeight: 800,
                      lineHeight: 1.5
                    }}
                  >
                    {reviewSubmitMessage}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </motion.form>
      </div>
    </section>
  );
}

function VideoExperienceSection({
  isMobile,
  opacity = 1
}: {
  isMobile: boolean;
  opacity?: number;
}) {
  const sectionHeight = isMobile ? "760vh" : "720vh";

  return (
    <section
      id="relationship-reading"
      data-section="video-experience"
      style={{
        position: "relative",
        minHeight: sectionHeight,
        marginTop: "-100vh",
        zIndex: 1,
        background: "transparent",
        opacity,
        pointerEvents: opacity > 0.99 ? "auto" : "none"
      }}
    >
      <div
        style={{
          position: "relative",
          zIndex: 2,
          minHeight: sectionHeight,
          color: "#fff",
          fontFamily:
            "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif"
        }}
      >
        <VideoLandingHero isMobile={isMobile} />
        <VideoMarqueeSection isMobile={isMobile} />
        <VideoAboutSection isMobile={isMobile} />
        <VideoServicesSection isMobile={isMobile} />
        <VideoReviewsSection isMobile={isMobile} />
      </div>
    </section>
  );
}

function LiquidGlassFooter({ isMobile }: { isMobile: boolean }) {
  const footerGroups = [
    {
      title: "Discover",
      links: [
        { label: "合盤解讀", href: "#relationship-reading" },
        { label: "解讀流程", href: "#reading-flow" },
        { label: "完整方案", href: "#pricing" },
        { label: "用戶見證", href: "#reviews" },
        { label: "部落格", href: WORDPRESS_CONTENT_URLS.blog }
      ]
    },
    {
      title: "The Mission",
      links: [
        { label: "光之谷起源", href: "#about" },
        { label: "天文資料標準", href: "#relationship-reading" },
        { label: "常見問題", href: "#faq" }
      ]
    },
    {
      title: "Legal",
      links: [
        { label: "隱私政策", href: WORDPRESS_CONTENT_URLS.privacy },
        { label: "退款政策", href: WORDPRESS_CONTENT_URLS.refunds },
        { label: "服務條款", href: WORDPRESS_CONTENT_URLS.terms }
      ]
    }
  ];

  return (
    <section
      id="site-footer"
      style={{
        position: "relative",
        zIndex: 4,
        overflow: "hidden",
        padding: isMobile
          ? "160px 18px 34px"
          : "230px clamp(34px, 5vw, 78px) 48px",
        marginTop: isMobile ? -58 : -96,
        minHeight: isMobile ? 760 : 900,
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-end",
        alignItems: "stretch",
        color: "#fff",
        fontFamily: "var(--font-sans)"
      }}
    >
      <motion.video
        src={FOOTER_BG_VIDEO}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        aria-hidden="true"
        initial={{ opacity: 0.08, scale: 1.08, y: -34 }}
        whileInView={{ opacity: 0.96, scale: 1.02, y: 0 }}
        viewport={{ once: true, amount: 0.22 }}
        transition={{ duration: 1.25, ease: [0.25, 0.1, 0.25, 1] }}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: "center",
          pointerEvents: "none"
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: isMobile ? 280 : 360,
          zIndex: 1,
          background:
            "linear-gradient(180deg, rgba(12,12,12,0.98) 0%, rgba(12,12,12,0.72) 34%, rgba(12,12,12,0.22) 72%, rgba(12,12,12,0) 100%)",
          pointerEvents: "none"
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 1,
          background:
            "linear-gradient(180deg, rgba(5,3,6,0.1) 0%, rgba(5,3,6,0.42) 44%, rgba(5,3,6,0.82) 100%)",
          pointerEvents: "none"
        }}
      />
      <motion.footer
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.32 }}
        transition={{ duration: 0.9, delay: 0.16, ease: "easeOut" }}
        className="liquid-glass w-full rounded-3xl p-6 md:p-10 text-white/70"
        style={{
          position: "relative",
          zIndex: 2,
          maxWidth: 1280,
          marginLeft: "auto",
          marginRight: "auto"
        }}
      >
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-12 mb-10">
          <div className="md:col-span-5">
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                marginBottom: 18
              }}
            >
              <BrandLogo variant="horizontal" width={190} />
            </div>
            <p
              className="text-sm leading-relaxed max-w-sm"
              style={{ margin: 0, color: "rgba(255,255,255,0.68)" }}
            >
              以 NASA JPL 天文資料與西洋合盤邏輯，幫你把感情裡的模糊訊號，
              轉成可以理解、可以行動的關係方向。
            </p>
          </div>

          <div className="md:col-span-7 grid grid-cols-1 sm:grid-cols-3 gap-8 md:gap-10">
            {footerGroups.map((group) => (
              <div key={group.title}>
                <h3 className="text-sm uppercase tracking-wider text-white font-medium mb-4">
                  {group.title}
                </h3>
                <ul className="space-y-2" style={{ listStyle: "none", margin: 0, padding: 0 }}>
                  {group.links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        className="text-xs hover:text-white transition-colors"
                        style={{
                          color: "inherit",
                          textDecoration: "none"
                        }}
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-6 border-t border-white/10">
          <p className="text-[10px] uppercase tracking-widest opacity-50" style={{ margin: 0 }}>
            Curated by Vale of Light
          </p>
        </div>
      </motion.footer>
    </section>
  );
}

function BannerNextSection({ isMobile }: { isMobile: boolean }) {
  const [activeSlide, setActiveSlide] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveSlide((current) => (current + 1) % BANNER_SLIDES.length);
    }, 3600);

    return () => window.clearInterval(timer);
  }, []);

  const goToPrevious = () => {
    setActiveSlide(
      (current) => (current - 1 + BANNER_SLIDES.length) % BANNER_SLIDES.length
    );
  };

  const goToNext = () => {
    setActiveSlide((current) => (current + 1) % BANNER_SLIDES.length);
  };

  return (
    <section
      data-section="three"
      style={{
        minHeight: "100vh",
        position: "relative",
        overflow: "hidden",
        background: "#f2f2f0",
        padding: isMobile ? "84px 20px 72px" : "96px clamp(42px, 5vw, 80px) 88px",
        color: "#111"
      }}
    >
      <div
        style={{
          position: "absolute",
          top: isMobile ? -90 : -140,
          right: isMobile ? -120 : -180,
          width: isMobile ? 280 : 520,
          height: isMobile ? 280 : 520,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(219,190,255,0.28) 0%, rgba(219,190,255,0) 68%)",
          filter: "blur(18px)",
          pointerEvents: "none"
        }}
      />
      <div
        style={{
          position: "relative",
          zIndex: 2,
          maxWidth: 1120,
          margin: "0 auto"
        }}
      >
        <div
          style={{
            maxWidth: isMobile ? 340 : 760,
            marginBottom: isMobile ? 34 : 46
          }}
        >
          <div
            style={{
              color: "rgba(17,17,17,0.48)",
              fontFamily:
                "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
              fontSize: isMobile ? 10 : 11,
              fontWeight: 900,
              letterSpacing: "0.18em",
              marginBottom: 16
            }}
          >
            解讀之後
          </div>
          <h2
            style={{
              margin: 0,
              fontFamily: "'Noto Serif TC', 'Songti TC', 'Noto Sans TC', serif",
              fontSize: isMobile ? "clamp(36px, 10vw, 52px)" : "clamp(64px, 7vw, 92px)",
              fontWeight: 900,
              lineHeight: 0.98,
              letterSpacing: "0.01em"
            }}
          >
            把看見的答案
            <br />
            變成行動方向
          </h2>
        </div>

        <div
          style={{
            position: "relative",
            width: "100%",
            height: isMobile ? 430 : "min(58vh, 620px)",
            minHeight: isMobile ? 430 : 520,
            overflow: "hidden",
            borderRadius: isMobile ? 22 : 30,
            background: "#111",
            boxShadow: "0 28px 90px rgba(18,12,24,0.24)"
          }}
        >
          {BANNER_SLIDES.map((slide, index) => {
            const active = index === activeSlide;

            return (
              <img
                key={slide.label}
                src={slide.image}
                alt=""
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  objectPosition: slide.position,
                  opacity: active ? 1 : 0,
                  transform: `scale(${active ? 1 : 1.045})`,
                  transition:
                    "opacity 0.65s ease, transform 1.2s cubic-bezier(0.22, 1, 0.36, 1)"
                }}
              />
            );
          })}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "linear-gradient(90deg, rgba(7,5,12,0.84) 0%, rgba(7,5,12,0.48) 44%, rgba(7,5,12,0.12) 100%)"
            }}
          />
          <img
            src={BOTTOM_CLOUDS}
            alt=""
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: -18,
              width: "100%",
              height: "auto",
              opacity: 0.34,
              filter: "saturate(1.1)"
            }}
          />

          <div
            style={{
              position: "absolute",
              top: isMobile ? 20 : 26,
              right: isMobile ? 20 : 28,
              display: "flex",
              gap: 6,
              zIndex: 4
            }}
          >
            {BANNER_SLIDES.map((slide, index) => (
              <button
                key={slide.label}
                type="button"
                aria-label={`Show banner ${index + 1}`}
                onClick={() => setActiveSlide(index)}
                style={{
                  width: index === activeSlide ? 22 : 7,
                  height: 7,
                  border: 0,
                  borderRadius: 999,
                  padding: 0,
                  background:
                    index === activeSlide
                      ? "rgba(255,255,255,0.95)"
                      : "rgba(255,255,255,0.42)",
                  cursor: "pointer",
                  transition: "width 0.25s ease, background 0.25s ease"
                }}
              />
            ))}
          </div>

          <div
            style={{
              position: "absolute",
              left: isMobile ? 22 : 34,
              right: isMobile ? 22 : "auto",
              top: isMobile ? 56 : 70,
              zIndex: 3,
              maxWidth: isMobile ? "none" : 460,
              color: "#fff"
            }}
          >
            <div
              style={{
                fontFamily:
                  "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
                fontSize: isMobile ? 10 : 11,
                fontWeight: 900,
                letterSpacing: "0.2em",
                color: "rgba(255,255,255,0.66)",
                marginBottom: 16
              }}
            >
              {BANNER_SLIDES[activeSlide].label}
            </div>
            <h3
              style={{
                margin: 0,
                fontFamily:
                  "'Noto Serif TC', 'Songti TC', 'Noto Sans TC', serif",
                fontSize: isMobile ? 34 : 56,
                fontWeight: 900,
                lineHeight: 1.03,
                letterSpacing: "0.01em",
                textShadow: "0 3px 24px rgba(0,0,0,0.45)"
              }}
            >
              {BANNER_SLIDES[activeSlide].title}
            </h3>
            <p
              style={{
                margin: "18px 0 0",
                color: "rgba(255,255,255,0.78)",
                fontFamily:
                  "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
                fontSize: isMobile ? 13 : 15,
                lineHeight: 1.7,
                maxWidth: 390
              }}
            >
              {BANNER_SLIDES[activeSlide].body}
            </p>
          </div>

          <div
            style={{
              position: "absolute",
              left: isMobile ? 22 : 34,
              bottom: isMobile ? 24 : 34,
              zIndex: 4
            }}
          >
            <span
              style={{
                position: "absolute",
                inset: -7,
                borderRadius: 999,
                border: "1.5px solid rgba(255,255,255,0.32)",
                animation: "bannerPulse 2.2s ease-out infinite"
              }}
            />
            <span
              style={{
                position: "absolute",
                inset: -3,
                borderRadius: 999,
                border: "1.5px solid rgba(255,255,255,0.22)",
                animation: "bannerPulse 2.2s ease-out 0.55s infinite"
              }}
            />
            <button
              type="button"
              style={{
                position: "relative",
                zIndex: 2,
                border: 0,
                borderRadius: 999,
                background: "#fff",
                color: "#111",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: isMobile ? "11px 18px" : "12px 24px",
                fontFamily:
                  "'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif",
                fontSize: isMobile ? 12 : 14,
                fontWeight: 800,
                cursor: "pointer"
              }}
            >
              <Play size={15} fill="#111" strokeWidth={0} />
              觀看完整解讀
            </button>
          </div>

          <div
            style={{
              position: "absolute",
              right: isMobile ? 20 : 28,
              bottom: isMobile ? 24 : 34,
              zIndex: 4,
              display: "flex",
              gap: 10
            }}
          >
            {[
              { label: "Previous slide", icon: ChevronLeft, onClick: goToPrevious },
              { label: "Next slide", icon: ChevronRight, onClick: goToNext }
            ].map(({ label, icon: Icon, onClick }) => (
              <button
                key={label}
                type="button"
                aria-label={label}
                onClick={onClick}
                style={{
                  width: isMobile ? 38 : 44,
                  height: isMobile ? 38 : 44,
                  border: 0,
                  borderRadius: "50%",
                  background: "rgba(255,255,255,0.88)",
                  color: "#111",
                  display: "grid",
                  placeItems: "center",
                  cursor: "pointer",
                  boxShadow: "0 8px 22px rgba(0,0,0,0.18)"
                }}
              >
                <Icon size={isMobile ? 18 : 20} strokeWidth={2.2} />
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function QuestionPromptTitle({ isMobile }: { isMobile: boolean }) {
  return (
    <div style={{ marginTop: isMobile ? "8vh" : 0 }}>
      <h2
        style={{
          margin: 0,
          fontFamily: "'Noto Serif TC', 'Songti TC', 'Noto Sans TC', serif",
          fontWeight: 900,
          fontSize: isMobile
            ? "clamp(28px, 7vw, 38px)"
            : "clamp(42px, 5vw, 72px)",
          lineHeight: 1.14,
          letterSpacing: "0.02em",
          color: "#fff",
          textShadow: "0 2px 20px rgba(0,0,0,0.4)"
        }}
      >
        你是否正在經歷這些感情困惑?
      </h2>
      <p
        style={{
          margin: "18px auto 0",
          maxWidth: isMobile ? 300 : 720,
          fontSize: isMobile ? 14 : 20,
          lineHeight: 1.6,
          letterSpacing: 0,
          color: "rgba(255,255,255,0.82)"
        }}
      >
        <span style={{ display: "block" }}>
          全新一代NASA航天級精準度的星盤定位系統。
        </span>
        <span style={{ display: "block" }}>
          看清這段感情的真相、未來與行動方向。
        </span>
      </p>
    </div>
  );
}

export default function App() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const worldRef = useRef<HTMLDivElement | null>(null);
  const cloudsRef = useRef<HTMLDivElement | null>(null);

  const isMobile = useIsMobile();
  const [scrollProgress, setScrollProgress] = useState(0);
  const [mouse, setMouse] = useState<MousePoint>({ x: 0, y: 0 });
  const [uiVisible, setUiVisible] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setUiVisible(true), 600);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const updateScroll = () => {
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const maxScroll = container.offsetHeight - window.innerHeight;
      const localScroll = window.scrollY - container.offsetTop;
      setScrollProgress(maxScroll > 0 ? clamp(localScroll / maxScroll, 0, 1) : 0);
    };

    updateScroll();
    window.addEventListener("scroll", updateScroll, { passive: true });
    window.addEventListener("resize", updateScroll);
    return () => {
      window.removeEventListener("scroll", updateScroll);
      window.removeEventListener("resize", updateScroll);
    };
  }, []);

  useEffect(() => {
    const target = { x: 0, y: 0 };
    const current = { x: 0, y: 0 };
    let frame = 0;

    const onMouseMove = (event: MouseEvent) => {
      target.x = (event.clientX / window.innerWidth - 0.5) * 2;
      target.y = (event.clientY / window.innerHeight - 0.5) * 2;
    };

    const tick = () => {
      current.x = lerp(current.x, target.x, 0.07);
      current.y = lerp(current.y, target.y, 0.07);
      setMouse({ x: current.x, y: current.y });
      frame = window.requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    frame = window.requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.cancelAnimationFrame(frame);
    };
  }, []);

  const ep = easeInOut(scrollProgress);
  const scene1Opacity = clamp(1 - scrollProgress / 0.22, 0, 1);
  const scene2Opacity = clamp((scrollProgress - 0.48) / 0.18, 0, 1);
  const cloudOpacity = lerp(0.7, 1, clamp(scrollProgress / 0.05, 0, 1));
  const cardToVideoFadeProgress = easeInOut(clamp((scrollProgress - 0.88) / 0.12, 0, 1));
  const cardOpacity = scene2Opacity * (1 - cardToVideoFadeProgress);
  const promptTitleOpacity = scene2Opacity * (1 - cardToVideoFadeProgress);
  const videoTransitionOpacity = cardToVideoFadeProgress;
  const spinningSceneOpacity = 1 - videoTransitionOpacity;
  const transitionPreviewOpacity =
    scrollProgress >= 0.999 ? 0 : videoTransitionOpacity;
  const realVideoSectionOpacity = scrollProgress >= 0.999 ? 1 : 0;
  const continuationProgress = 0;
  const sectionSurfaceProgress = easeInOut(clamp((continuationProgress - 0.18) / 0.56, 0, 1));
  const arcSweepDeg = (ARC_CARDS.length - 1) * 10;
  const rotationOffset = lerp(
    0,
    arcSweepDeg,
    clamp((scrollProgress - 0.5) / 0.5, 0, 1)
  );

  const layerStyles = useMemo(() => {
    return {
      world: layerTransform(mouse, MAG.world, lerp(1, 1.18, ep)),
      clouds: layerTransform(mouse, MAG.clouds, lerp(1, 1.4, ep), 0.4)
    };
  }, [ep, mouse]);

  return (
    <main
      id="top"
      style={{ minHeight: "100vh", position: "relative", background: "#050306" }}
    >
      <LuminaVideoBackground fixed opacity={videoTransitionOpacity} />
      <div
        ref={containerRef}
        style={{ height: "620vh", position: "relative", zIndex: 2 }}
      >
      <section
        style={{
          position: "sticky",
          top: 0,
          height: "100vh",
          overflow: "hidden",
          background: `rgba(10,6,8,${spinningSceneOpacity})`
        }}
      >
        <div
          ref={worldRef}
          style={{
            position: "absolute",
            inset: 0,
            transformOrigin: "50% 50%",
            transform: layerStyles.world,
            opacity: spinningSceneOpacity,
            pointerEvents: "none"
          }}
        >
          <img
            src={WORLD_BG}
            alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>

        <div
          ref={cloudsRef}
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: cardOpacity > 0.05 ? 35 : 10,
            transformOrigin: "50% 100%",
            transform: layerStyles.clouds,
            opacity: cloudOpacity * spinningSceneOpacity,
            pointerEvents: "none"
          }}
        >
          <img
            src={BOTTOM_CLOUDS}
            alt=""
            style={{ width: "100%", height: "auto" }}
          />
        </div>

        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 28,
            background: "transparent",
            overflow: "hidden",
            borderTopLeftRadius: isMobile
              ? lerp(26, 0, sectionSurfaceProgress)
              : lerp(46, 0, sectionSurfaceProgress),
            borderTopRightRadius: isMobile
              ? lerp(26, 0, sectionSurfaceProgress)
              : lerp(46, 0, sectionSurfaceProgress),
            boxShadow: "none",
            transform: `translateY(${lerp(105, 0, sectionSurfaceProgress)}%)`,
            willChange: "transform",
            pointerEvents: "none"
          }}
        >
        </div>

        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 60,
            opacity: transitionPreviewOpacity,
            pointerEvents: "none"
          }}
        >
          <VideoLandingHero isMobile={isMobile} />
        </div>

        <div
          className="spinning-card-stage"
          style={{
            position: "absolute",
            left: "50%",
            transform: "translateX(-50%)",
            opacity: cardOpacity,
            pointerEvents: "none"
          }}
        >
          <ArcCardSlider
            cards={ARC_CARDS}
            rotationOffset={rotationOffset}
            continuationProgress={0}
            isMobile={isMobile}
          />
        </div>

        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 16,
            height: "40%",
            background:
              "linear-gradient(to top, rgba(0,0,0,0.45) 0%, transparent 100%)",
            opacity: spinningSceneOpacity,
            pointerEvents: "none"
          }}
        />

        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            zIndex: 45,
            height: "42vh",
            background:
              "linear-gradient(to bottom, rgba(0,0,0,0.45) 0%, transparent 100%)",
            opacity: spinningSceneOpacity,
            pointerEvents: "none"
          }}
        />

        <div
          style={{
            opacity: scene1Opacity,
            pointerEvents: scene1Opacity > 0.25 ? "auto" : "none"
          }}
        >
          <Nav />
        </div>

        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 20,
            opacity: scene1Opacity,
            pointerEvents: "none"
          }}
        >
          <SceneOne uiVisible={uiVisible} />
        </div>

        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 46,
            display: "flex",
            justifyContent: "center",
            alignItems: isMobile ? "center" : "flex-start",
            textAlign: "center",
            padding: isMobile ? "0 24px" : "clamp(96px, 12vh, 150px) 24px 0",
            opacity: promptTitleOpacity,
            transform: `translateY(${lerp(30, 0, scene2Opacity)}px)`,
            pointerEvents: "none"
          }}
        >
          <QuestionPromptTitle isMobile={isMobile} />
        </div>

      </section>
      </div>
      <VideoExperienceSection
        isMobile={isMobile}
        opacity={realVideoSectionOpacity}
      />
      <LiquidGlassFooter isMobile={isMobile} />
    </main>
  );
}
