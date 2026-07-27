# Valley of Light Web

Next.js application for paid intake, processing state, and immutable reading
delivery. The fixture-driven dashboard remains available as development code,
but the public root no longer exposes an unpaid intake.

## Run

```bash
python3 ../../scripts/build_relationship_result_view_models.py
npm install
npm run dev
```

Open `http://localhost:3000`.

## Current Scope

- Generated scenario fixtures from `examples/calculations/*.json`
- Scenario switcher for comparing multiple real selector outputs
- Implements the active paid-only V1 contract in `docs/product/00-current-v1-contract.md`
  and `docs/product/09-frontend-flow-view-model.md`
- Uses the same slot language as `docs/product/07-reading-contract.md`
- Frontend data contract is `src/data/complete-relationship-result.ts`
- Generated local data is `src/data/generated/relationship-result-scenarios.json`

## Runtime Reading Layer

The local prototype `POST /api/readings/relationship-result` runs:

```text
intake answers
→ Python calculation + selector
→ CompleteRelationshipResultViewModel
→ result dashboard
```

`POST /api/readings/free-result` remains as a legacy compatibility alias.
Both prototype endpoints return `404` unless
`VALLEY_ENABLE_LOCAL_RESULT_PROTOTYPE=1`; do not enable that variable in
Preview or Production.

Environment:

- `VALLEY_STRUCTURED_KB_SOURCE=local|supabase` selects the structured KB runtime adapter. If unset, Vercel Preview or `VALLEY_RUNTIME_ENV=staging` defaults to `supabase`; other environments default to `local`.
- `VALLEY_STRUCTURED_KB_ENV_FILE` optionally points Supabase mode at an env file containing the runtime service credentials.
- In local development, the API can read `/Users/novaos/.openclaw/workspace/.env` if process env vars are not set.

The reading page is deterministic. Copy is produced by the structured runtime fields
(`relationshipProfiles`, `answerGuidance`, `timingGuidance`, `actionGuidance`,
and `readingBlueprint`) instead of a runtime LLM layer.

## Paid Reading Foundation

The production-oriented route boundary is:

```text
POST /api/integrations/woocommerce/webhook
GET  /api/reading-access
PATCH /api/reading-access/intake
POST /api/reading-access/submit
POST /api/reading-access/recover
POST /api/internal/reading-worker/claim
POST /api/internal/reading-worker/failure
POST /api/internal/reading-worker/result
POST /api/internal/reading-worker/email-reconciliation
GET  /api/internal/woocommerce/reconciliation
GET  /api/health/paid-reading
GET  /r with capability in the URL fragment
POST /api/reading-access/exchange -> HttpOnly cookie -> /reading
GET  /recover
```

The email URL is a deterministic `grant_id + expiry + HMAC` capability. The
database stores its SHA-256 hash, never the raw token. The one emailed URL
exchanges the capability for a host-only `HttpOnly` cookie and immediately
redirects to `/reading`, so polling and form requests do not repeat the token
in URLs. The database migration atomically locks final intake submission,
creates at most one fulfillment for the order, exposes a signed lease-based
worker claim with attempt fencing, accepts only lease-fenced result/failure
callbacks, independently reconciles missing transactional emails, revokes
access and result delivery after a verified refund, and makes the stored result
immutable. Failed or cancelled pre-payment orders remain eligible for a later
authoritative paid retry; a refund remains terminal. Cookie-authenticated
intake writes require the exact app origin and JSON content type. A repeated
visit therefore routes to intake, processing, or the same stored result; it
cannot create a second intake.

Customer-facing reading notifications use WooCommerce's built-in customer
emails. The app signs a narrow WordPress request containing only the Woo order
ID, non-secret grant UUID, expiry, message kind, template version, and
idempotency key. WordPress never stores or receives the raw app URL/token: it
reconstructs the exact token in memory from the shared access-signing secret
while rendering the email. Woo's Processing Order email carries the
post-payment intake link. After the result is durably stored, the signed
result-ready action is the only path that moves the order from `processing` to
`completed`; Woo's Completed Order email repeats the same link.

Before creating an entitlement, the WooCommerce receiver re-fetches the order
and requires immutable server-owned evidence for both terms acceptance and the
buyer's exact-match billing-email confirmation. The confirmation proof is a
WordPress-created HMAC digest plus its confirmation timestamp and validated
classic/Store API boundary; the app stores and replay-compares that proof but
never receives the second plaintext email value.

Vercel Cron calls the authenticated WooCommerce reconciliation route every ten
minutes. Each invocation leases and scans at most one configured REST page
inside a persisted window, with a 48-hour overlap by default. Its event IDs are
deterministic, so a crash safely retries the same page through the exact paid
and refund RPCs used by webhooks. A page containing a review failure does not
advance its cursor or high-water mark. Production health stays closed until a
clean scan reaches a recent high-water mark.

If the capability expires, the customer can request a replacement using the
WooCommerce order number and billing email. The response does not reveal
whether an order exists, and the request only enqueues delivery. An unexpired
working grant is deliberately kept active and the same deterministic link is
resent; only an already-expired grant is rotated. The signed reconciler sends
only to the stored billing address, so the public response does not wait on the
email transport. App-to-WordPress delivery uses five fenced attempts with
persisted exponential backoff, WordPress-side idempotency, and a terminal
suppressed state. A later rate-limited recovery request may reopen only its own
transiently exhausted recovery delivery; it cannot clear a recipient, refund,
erasure, or access-rotation suppression. Woo's `wp_mail()` acceptance is not
proof of inbox delivery, so production also requires authenticated SMTP/API
transport, provider logs, and a tested support resend process. The optional
Resend webhook route remains only for backward-compatible provider-event rows;
it is not required by the Woo email path.

Email queue health is provider-aware. A Woo `sent` row means only that
WordPress/`wp_mail()` accepted the message, so it is terminal for retry health
and is reported as `acceptance-only`; it never becomes `delivered`, `bounced`,
or `complained` without a future authenticated provider-event integration.
Legacy Resend `sent` rows still require their signed provider event and become
overdue if it does not arrive. Keep the legacy webhook live until those rows
are resolved. The WordPress launch gate separately stays closed until the
operator explicitly attests that authenticated SMTP/API delivery, logs, and
the support resend path have passed an end-to-end test.

Immediately before every intake, result-ready, or recovery notification, the
app reads the immutable paid snapshot from Supabase, re-fetches the Woo order,
and requires the current paid order to match the stored recipient, amount,
currency, product evidence, terms evidence, payment time, and email-confirmation
proof. This delivery check intentionally does not reuse today's new-payment
terms/price/catalog allowlist, so retiring an old checkout cohort cannot block
that customer's later result or recovery email. A Supabase-only address change
therefore cannot be recorded as a successful send while WordPress sends to the
old order address. The database billing-correction procedure is deliberately
disabled until there is an audited Woo-first workflow that also renews
WordPress's billing-email confirmation proof. Until then, support must not edit
a paid reading's email in either system and describe the address as corrected.

The migration also includes a DB-owner-only, audited reading-content erasure
action. It revokes grants and active work, clears intake and result payloads,
and cannot be executed by the app service role. Commerce, consent, provider
records, backups, and their separate legal retention requirements are
deliberately not represented as fully erased. Production health remains closed
until an explicitly approved, enabled retention-policy version matches
`VALLEY_RETENTION_POLICY_VERSION`.

The production intake only accepts a reviewed list of resolvable birth cities.
Customers whose city is not listed can safely leave it blank; the calculation
then blocks location-sensitive house/angle claims instead of silently skipping
a natal chart.

Before running the paid path locally:

1. Copy `.env.example` to an ignored local env file and fill only local/staging
   credentials.
2. Review, then apply
   `../../supabase/migrations/20260726170000_add_paid_reading_delivery.sql` to
   the intended non-production project first.
   Create no enabled retention policy until the owner has approved its
   incomplete, delivered, and revoked time windows and backup/legal-hold
   handling.
3. Configure `CRON_SECRET` and verify the scheduled WooCommerce reconciliation
   route completes a clean initial scan.
4. Configure a WooCommerce webhook for the deployed integration endpoint using
   the same webhook secret.
5. Configure `VALEOFLIGHT_WORDPRESS_EMAIL_API_URL` and a separate
   `VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET`. Configure the same
   notification secret plus the existing access-signing secret in
   `wp-config.php`, then verify the bridge health check. Enable Woo's Processing
   and Completed customer emails and connect WordPress to authenticated
   SMTP/API mail with SPF, DKIM, DMARC, provider logs, and click tracking
   disabled for capability links.
6. Configure both worker variables plus `VALLEY_AGPL_SOURCE_URL` and
   `VALLEY_AGPL_SOURCE_SHA256`. The app and worker must identify the same
   immutable public source release. The worker polls the signed claim endpoint
   as its durable source of locked jobs, reports permanent/retryable failures
   through the signed failure endpoint, and calls email reconciliation on its
   own schedule. The submission-time request is only a wake-up hint.
7. Generate and publish the public source archive, then build the portable
   worker from `../../services/reading-worker/Dockerfile.agpl`. Production
   health rejects a worker whose `/source` metadata does not match the app.

The service-role key, Woo credentials, access-signing secret, WordPress
notification-signing secret, optional Resend credentials, and worker-signing
secret are server-only and must never use a `NEXT_PUBLIC_` prefix.

Validation:

```bash
npm test
npm run typecheck
npm run build
npm audit --omit=dev
```
