# Vale of Light apex router

This Cloudflare Worker preserves `valeoflight.com` as the public landing URL
while using `official.valeoflight.com` as its Vercel origin.

Every landing-origin request overwrites `x-vale-proxy` with `1`. The Vercel
landing project uses that marker to serve proxied requests normally while
permanently redirecting direct `official.valeoflight.com` requests to the
canonical public URL. Deploy the marker-enabled Worker before enabling or
changing the Vercel redirect guard.

The same Worker also permanently redirects only the read-only
`www.valeoflight.com` homepage (`/` and `/index.html`) to the canonical apex.
WordPress search/query shapes, mutations, blog, shop, checkout, REST, admin,
callbacks, and every other `www` path continue to WordPress unchanged.

## Routing contract

Only read requests for these apex paths go to the landing origin:

- `/`
- `/index.html`
- `/assets/*`
- `/brand/*`

Every other apex path goes to the existing WordPress/Kinsta origin.
`www.valeoflight.com` is routed through the Worker only to canonicalize its
homepage; all other `www` traffic passes through to WordPress.
`app.valeoflight.com` remains outside the Worker route.

Plain HTTP requests to the apex are upgraded to HTTPS with a `308` redirect
before the origin decision.

This allowlist is intentional. New landing-owned path namespaces must be added
to `worker.mjs` and its tests before deployment.

## Validation

```sh
node --test worker.test.mjs
npx wrangler deploy --dry-run
node smoke-production.mjs
```

Production deployment uses the `valeoflight.com/*` route declared in
`wrangler.toml`. The apex DNS record must remain proxied through Cloudflare.

## Rollback

Disable or remove the `valeoflight.com/*` and `www.valeoflight.com/*` Worker
routes in Cloudflare. With no matching apex Worker route, the existing proxied
apex DNS record sends requests directly to the WordPress/Kinsta origin again.
