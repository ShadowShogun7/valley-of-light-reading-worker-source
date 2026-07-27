type BrandLogoVariant = "horizontal" | "mark" | "stacked" | "wordmark";

const logoAssets: Record<
  BrandLogoVariant,
  { height: number; src: string; width: number }
> = {
  horizontal: {
    height: 246,
    src: "/brand/valley-of-light-horizontal.webp",
    width: 595,
  },
  mark: {
    height: 240,
    src: "/brand/valley-of-light-mark.webp",
    width: 246,
  },
  stacked: {
    height: 450,
    src: "/brand/valley-of-light-stacked.webp",
    width: 600,
  },
  wordmark: {
    height: 154,
    src: "/brand/valley-of-light-wordmark.webp",
    width: 369,
  },
};

export function BrandLogo({
  className = "",
  decorative = false,
  variant = "horizontal",
}: {
  className?: string;
  decorative?: boolean;
  variant?: BrandLogoVariant;
}) {
  const asset = logoAssets[variant];

  return (
    <img
      alt={decorative ? "" : "光之谷 Valley of Light"}
      aria-hidden={decorative || undefined}
      className={`brand-logo brand-logo-${variant} ${className}`.trim()}
      draggable="false"
      height={asset.height}
      src={asset.src}
      width={asset.width}
    />
  );
}
