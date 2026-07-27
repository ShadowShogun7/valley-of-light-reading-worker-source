const APEX_HOST = "valeoflight.com";
const WWW_HOST = "www.valeoflight.com";
const LANDING_ORIGIN_HOST = "official.valeoflight.com";
const PROXY_MARKER_HEADER = "x-vale-proxy";
const PROXY_MARKER_VALUE = "1";
const LANDING_PATH_PREFIXES = ["/assets/", "/brand/"];
const WORDPRESS_QUERY_KEYS = [
  "add-to-cart",
  "attachment_id",
  "author",
  "feed",
  "p",
  "page_id",
  "post_type",
  "preview",
  "rest_route",
  "s",
  "wc-api",
  "wc-ajax"
];

export function shouldRedirectToHttps(request) {
  const url = new URL(request.url);
  return url.hostname === APEX_HOST && url.protocol !== "https:";
}

export function shouldRedirectWwwHomepage(request) {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return false;
  }

  const url = new URL(request.url);

  if (url.hostname !== WWW_HOST) {
    return false;
  }

  if (WORDPRESS_QUERY_KEYS.some((key) => url.searchParams.has(key))) {
    return false;
  }

  return url.pathname === "/" || url.pathname === "/index.html";
}

export function createCanonicalHomepageUrl(request) {
  const canonicalUrl = new URL(request.url);
  canonicalUrl.protocol = "https:";
  canonicalUrl.hostname = APEX_HOST;
  canonicalUrl.port = "";
  canonicalUrl.pathname = "/";
  return canonicalUrl;
}

export function shouldUseLandingOrigin(request) {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return false;
  }

  const url = new URL(request.url);

  if (url.hostname !== APEX_HOST) {
    return false;
  }

  if (WORDPRESS_QUERY_KEYS.some((key) => url.searchParams.has(key))) {
    return false;
  }

  return (
    url.pathname === "/" ||
    url.pathname === "/index.html" ||
    LANDING_PATH_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))
  );
}

function rewriteLandingLocation(headers) {
  const location = headers.get("location");

  if (!location) {
    return;
  }

  const target = new URL(location, `https://${LANDING_ORIGIN_HOST}`);

  if (target.hostname === LANDING_ORIGIN_HOST) {
    target.hostname = APEX_HOST;
    headers.set("location", target.toString());
  }
}

async function fetchWordPress(request) {
  return fetch(request);
}

export function createLandingOriginRequest(request) {
  const upstreamUrl = new URL(request.url);
  upstreamUrl.protocol = "https:";
  upstreamUrl.hostname = LANDING_ORIGIN_HOST;
  upstreamUrl.port = "";

  const upstreamRequest = new Request(upstreamUrl, request);
  upstreamRequest.headers.set(PROXY_MARKER_HEADER, PROXY_MARKER_VALUE);

  return upstreamRequest;
}

async function fetchLanding(request) {
  const upstreamRequest = createLandingOriginRequest(request);
  const upstreamUrl = new URL(upstreamRequest.url);
  const response = await fetch(upstreamRequest, { redirect: "manual" });

  if (response.status >= 500) {
    return fetchWordPress(request);
  }

  const headers = new Headers(response.headers);
  rewriteLandingLocation(headers);

  if (
    upstreamUrl.pathname === "/" ||
    upstreamUrl.pathname === "/index.html"
  ) {
    headers.append("link", `<https://${APEX_HOST}/>; rel="canonical"`);
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

export default {
  async fetch(request) {
    if (shouldRedirectWwwHomepage(request)) {
      return Response.redirect(createCanonicalHomepageUrl(request), 308);
    }

    if (shouldRedirectToHttps(request)) {
      const httpsUrl = new URL(request.url);
      httpsUrl.protocol = "https:";
      return Response.redirect(httpsUrl, 308);
    }

    if (!shouldUseLandingOrigin(request)) {
      return fetchWordPress(request);
    }

    try {
      return await fetchLanding(request);
    } catch {
      return fetchWordPress(request);
    }
  }
};
