import assert from "node:assert/strict";
import test from "node:test";

import {
  createCanonicalHomepageUrl,
  createLandingOriginRequest,
  shouldRedirectToHttps,
  shouldRedirectWwwHomepage,
  shouldUseLandingOrigin
} from "./worker.mjs";

function request(path, method = "GET", hostname = "valeoflight.com") {
  return new Request(`https://${hostname}${path}`, { method });
}

test("proxies the apex landing document", () => {
  assert.equal(shouldUseLandingOrigin(request("/")), true);
  assert.equal(shouldUseLandingOrigin(request("/?campaign=launch")), true);
  assert.equal(shouldUseLandingOrigin(request("/?utm_source=instagram")), true);
  assert.equal(shouldUseLandingOrigin(request("/index.html")), true);
});

test("proxies only the landing build asset namespaces", () => {
  assert.equal(
    shouldUseLandingOrigin(request("/assets/index-cLoDkC9Q.js")),
    true
  );
  assert.equal(
    shouldUseLandingOrigin(request("/brand/valley-of-light-mark.webp")),
    true
  );
});

test("keeps WordPress and WooCommerce paths on the existing origin", () => {
  const wordpressPaths = [
    "/wp-admin/",
    "/wp-login.php",
    "/wp-json/",
    "/wp-content/theme.css",
    "/wp-includes/script.js",
    "/shop/",
    "/cart/",
    "/checkout/",
    "/start-reading/",
    "/my-account/",
    "/blog/",
    "/product/relationship-reading/",
    "/wc-api/payment-callback",
    "/?wc-ajax=checkout"
  ];

  for (const path of wordpressPaths) {
    assert.equal(shouldUseLandingOrigin(request(path)), false, path);
  }

  assert.equal(shouldUseLandingOrigin(request("/?s=relationship")), false);
  assert.equal(shouldUseLandingOrigin(request("/?rest_route=/wc/v3")), false);
});

test("does not proxy mutation requests or other hostnames", () => {
  assert.equal(shouldUseLandingOrigin(request("/", "POST")), false);
  assert.equal(
    shouldUseLandingOrigin(request("/", "GET", "www.valeoflight.com")),
    false
  );
  assert.equal(
    shouldUseLandingOrigin(request("/", "GET", "app.valeoflight.com")),
    false
  );
});

test("redirects only apex HTTP requests to HTTPS", () => {
  assert.equal(
    shouldRedirectToHttps(new Request("http://valeoflight.com/")),
    true
  );
  assert.equal(
    shouldRedirectToHttps(new Request("https://valeoflight.com/")),
    false
  );
  assert.equal(
    shouldRedirectToHttps(new Request("http://www.valeoflight.com/")),
    false
  );
});

test("redirects only the safe www homepage variants to the canonical apex", () => {
  assert.equal(
    shouldRedirectWwwHomepage(request("/", "GET", "www.valeoflight.com")),
    true
  );
  assert.equal(
    shouldRedirectWwwHomepage(
      request("/?utm_source=instagram", "HEAD", "www.valeoflight.com")
    ),
    true
  );
  assert.equal(
    shouldRedirectWwwHomepage(
      request("/index.html", "GET", "www.valeoflight.com")
    ),
    true
  );
  assert.equal(
    shouldRedirectWwwHomepage(
      request("/?s=relationship", "GET", "www.valeoflight.com")
    ),
    false
  );
  assert.equal(
    shouldRedirectWwwHomepage(
      request("/checkout/", "GET", "www.valeoflight.com")
    ),
    false
  );
  assert.equal(
    shouldRedirectWwwHomepage(request("/", "POST", "www.valeoflight.com")),
    false
  );
  assert.equal(shouldRedirectWwwHomepage(request("/")), false);

  assert.equal(
    createCanonicalHomepageUrl(
      request("/index.html?utm_source=instagram", "GET", "www.valeoflight.com")
    ).toString(),
    "https://valeoflight.com/?utm_source=instagram"
  );
});

test("marks every landing-origin request for the Vercel redirect guard", () => {
  const upstreamRequest = createLandingOriginRequest(
    new Request("https://valeoflight.com/?utm_source=launch", {
      headers: {
        "x-vale-proxy": "untrusted-client-value"
      }
    })
  );

  assert.equal(
    upstreamRequest.url,
    "https://official.valeoflight.com/?utm_source=launch"
  );
  assert.equal(upstreamRequest.headers.get("x-vale-proxy"), "1");
});
