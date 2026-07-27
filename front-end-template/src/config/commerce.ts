const DEFAULT_READING_CHECKOUT_URL =
  "https://www.valeoflight.com/start-reading/";

function resolveReadingCheckoutUrl(configuredUrl?: string) {
  const candidate = configuredUrl?.trim();

  if (!candidate) {
    return DEFAULT_READING_CHECKOUT_URL;
  }

  try {
    const url = new URL(candidate);
    return url.protocol === "https:"
      ? url.toString()
      : DEFAULT_READING_CHECKOUT_URL;
  } catch {
    return DEFAULT_READING_CHECKOUT_URL;
  }
}

export const READING_CHECKOUT_URL = resolveReadingCheckoutUrl(
  import.meta.env.VITE_READING_CHECKOUT_URL
);
