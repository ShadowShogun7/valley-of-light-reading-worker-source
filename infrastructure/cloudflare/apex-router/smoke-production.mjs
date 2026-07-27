import assert from "node:assert/strict";

const LANDING_TITLE = "<title>光之谷 | Vale of Light</title>";

async function request(path, options = {}) {
  return fetch(`https://valeoflight.com${path}`, {
    redirect: "manual",
    signal: AbortSignal.timeout(20_000),
    ...options
  });
}

const landingResponse = await request("/");
const landingHtml = await landingResponse.text();

assert.equal(landingResponse.status, 200);
assert.match(
  landingResponse.headers.get("content-type") ?? "",
  /^text\/html/
);
assert.ok(landingHtml.includes(LANDING_TITLE));
assert.match(
  landingResponse.headers.get("link") ?? "",
  /<https:\/\/valeoflight\.com\/>; rel="canonical"/
);
assert.match(
  landingHtml,
  /<link rel="canonical" href="https:\/\/valeoflight\.com\/"\s*\/?>/
);

const directOriginResponse = await fetch(
  "https://official.valeoflight.com/",
  {
    redirect: "manual",
    signal: AbortSignal.timeout(20_000)
  }
);
assert.equal(directOriginResponse.status, 308);
assert.equal(
  directOriginResponse.headers.get("location"),
  "https://valeoflight.com/"
);

const markedOriginResponse = await fetch(
  "https://official.valeoflight.com/",
  {
    headers: {
      "x-vale-proxy": "1"
    },
    signal: AbortSignal.timeout(20_000)
  }
);
const markedOriginHtml = await markedOriginResponse.text();
assert.equal(markedOriginResponse.status, 200);
assert.ok(markedOriginHtml.includes(LANDING_TITLE));

const insecureResponse = await fetch("http://valeoflight.com/", {
  redirect: "manual",
  signal: AbortSignal.timeout(20_000)
});
assert.equal(insecureResponse.status, 308);
assert.equal(
  insecureResponse.headers.get("location"),
  "https://valeoflight.com/"
);

const assetPaths = [
  ...new Set(
    [...landingHtml.matchAll(/(?:src|href)="(\/(?:assets|brand)\/[^"]+)"/g)]
      .map((match) => match[1])
  )
];

assert.ok(assetPaths.length >= 3);

for (const assetPath of assetPaths) {
  const assetResponse = await request(assetPath);
  assert.equal(assetResponse.status, 200, assetPath);
}

const jsonResponse = await request("/wp-json/");
assert.equal(jsonResponse.status, 200);
assert.match(
  jsonResponse.headers.get("content-type") ?? "",
  /^application\/json/
);

const redirectPaths = [
  "/wp-admin/",
  "/shop/",
  "/cart/",
  "/checkout/",
  "/blog/"
];

for (const path of redirectPaths) {
  const response = await request(path);
  assert.ok([301, 302].includes(response.status), path);
  assert.match(
    response.headers.get("location") ?? "",
    /^https:\/\/www\.valeoflight\.com\//,
    path
  );
}

const wooAjaxResponse = await request("/?wc-ajax=checkout");
const wooAjaxBody = await wooAjaxResponse.text();
assert.match(
  wooAjaxResponse.headers.get("content-type") ?? "",
  /^application\/json/
);
assert.ok(!wooAjaxBody.includes(LANDING_TITLE));

const searchResponse = await request("/?s=relationship");
const searchHtml = await searchResponse.text();
assert.equal(searchResponse.status, 200);
assert.ok(!searchHtml.includes(LANDING_TITLE));

const mutationResponse = await request("/", { method: "POST" });
const mutationHtml = await mutationResponse.text();
assert.ok(!mutationHtml.includes(LANDING_TITLE));

const [wwwResponse, wwwBlogResponse, appResponse] = await Promise.all([
  fetch("https://www.valeoflight.com/", {
    redirect: "manual",
    signal: AbortSignal.timeout(20_000)
  }),
  fetch("https://www.valeoflight.com/blog/", {
    redirect: "manual",
    signal: AbortSignal.timeout(20_000)
  }),
  fetch("https://app.valeoflight.com/", {
    redirect: "manual",
    signal: AbortSignal.timeout(20_000)
  })
]);

assert.equal(wwwResponse.status, 308);
assert.equal(
  wwwResponse.headers.get("location"),
  "https://valeoflight.com/"
);
assert.equal(wwwBlogResponse.status, 200);
assert.equal(appResponse.status, 200);

console.log(
  JSON.stringify(
    {
      app: appResponse.status,
      directOrigin: directOriginResponse.status,
      landing: landingResponse.status,
      landingAssets: assetPaths.length,
      markedOrigin: markedOriginResponse.status,
      wordpress: jsonResponse.status,
      www: wwwResponse.status,
      wwwBlog: wwwBlogResponse.status
    },
    null,
    2
  )
);
