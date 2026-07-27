# 13 - Production Commerce And Reading Delivery Architecture

> Status: recommended launch architecture
> Updated: 2026-07-26
> Product: one `NT$1,280` paid Western relationship reading
> Customer identity: guest checkout plus post-payment email access; no account

## Decision

Use WordPress and WooCommerce for content publishing, guest checkout, payment
state, refunds, and staff order management. Keep all astrology intake,
calculation, result data, and reading access in the application stack.

The launch boundary is:

```text
Vercel landing
  -> native WooCommerce guest checkout: payment first
  -> payment gateway
  -> signed WooCommerce webhook
  -> private Supabase paid entitlement
  -> signed app-to-WordPress notification
  -> Woo Customer Processing email with secure intake link
  -> Vercel reading app: post-payment intake
  -> durable queue after final intake submission
  -> Python reading worker
  -> private Supabase result
  -> signed app-to-WordPress result-ready notification
  -> Woo Customer Completed email with the same secure link
  -> Vercel reading app
```

WooCommerce is the commerce source of truth. Supabase is the reading and
fulfillment source of truth. Vercel is the customer experience. The Python
worker is the only service allowed to run the paid calculation and final
Traditional Chinese realization pipeline.

Do not make WordPress store birth data or generated readings. Do not make
WooCommerce decide whether a result is ready. Do not treat a browser return from
the payment gateway as proof of payment. Do not collect birth or relationship
data before payment.

## Why This Is Better Than A Permanent Public Result URL

The product does not need customer accounts, but email alone is not
authorization. The email should carry an opaque access credential that the app
exchanges for a secure session.

Recommended behavior:

1. After verified payment and durable grant creation, the application authorizes
   WordPress through a signed narrow endpoint to send WooCommerce's Customer
   Processing email with one branded `開始填寫解讀資料` button to the billing
   email.
2. Its credential is an opaque HMAC-signed capability token with a server-owned
   grant id and expiry.
3. Supabase stores only the token hash, never the raw token.
4. The app exchanges the token for an `HttpOnly`, `Secure`, `SameSite=Lax`
   reading session cookie.
5. The app removes the token from the visible URL before showing the current
   reading state.
6. The same order-linked entry point routes an authorized customer to intake,
   processing, or the stored result according to the server-side state.
7. A `找回我的解讀` form resends the still-valid link, or replaces an expired
   one, to the order email without revealing whether an order exists.
8. Staff can revoke or rotate access after a refund, support request, or
   suspected leak.
9. When the result is durable, the application calls the same signed WordPress
   boundary; WordPress changes the order to `completed` and sends WooCommerce's
   Customer Completed email with the exact same link.

This preserves the user's desired one-click experience without publishing
guessable order ids or making the billing email a password.

The tradeoff must be explicit: anyone who receives or is forwarded a valid
capability link can open the reading. If that is not acceptable, add a new-device
email verification step later. Do not silently add a password or customer
account to V1.

## Domain Topology

Confirmed launch domains:

| Surface | Domain | Owner | Current state |
| --- | --- | --- | --- |
| Canonical marketing homepage | `valeoflight.com` | Cloudflare edge + Vercel landing | Landing proxy active |
| Checkout, orders, legal pages, blog, WordPress | `www.valeoflight.com` | WordPress + WooCommerce | WordPress currently canonicalizes its routes to `www` |
| Landing origin | `official.valeoflight.com` | Vercel landing project | DNS, alias, and HTTPS active |
| Intake, status, result, recovery | `app.valeoflight.com` | Vercel Next.js app | DNS, alias, and HTTPS active |

The Cloudflare Worker `valeoflight-apex-router` reverse-proxies the public
homepage at `valeoflight.com` to the Vercel landing origin while preserving
`valeoflight.com` in the browser. It uses an explicit allowlist: read requests
for `/`, `/index.html`, `/assets/*`, and `/brand/*` go to the landing origin.
Every other path, all WordPress/WooCommerce query shapes, and every mutation
request continue to the existing WordPress/Kinsta origin. This keeps
WordPress admin, REST API, `/wp-content/*`, `/wp-includes/*`, shop, cart,
checkout, blog, products, callbacks, and future WordPress paths out of the
landing proxy by default. WordPress currently redirects its public routes to
the `www.valeoflight.com` canonical host; the checkout URL therefore uses
`www`, while the marketing homepage stays on the apex.

Plain HTTP requests to the apex are upgraded to HTTPS with a permanent
method-preserving redirect. The version-controlled Worker, tests, production
smoke check, and rollback instructions live in
`infrastructure/cloudflare/apex-router/`.

`official.valeoflight.com` is an origin hostname, not the canonical public
marketing URL. The Worker overwrites `x-vale-proxy` with `1` on every request
to that origin. Vercel serves marked requests normally and permanently
redirects every unmarked direct request to the equivalent
`https://valeoflight.com/` path. The landing HTML and edge response also name
the apex URL as canonical.

`app.valeoflight.com` is customer-facing directly and must not be reverse-
proxied back through `valeoflight.com`. Private intake and result routes remain
`noindex, nofollow`.

Keep the same logo, header, footer, colors, support address, privacy link, and
refund language across all three surfaces.

For launch, use WordPress's native blog frontend on a WordPress-owned path.
Moving the blog through the WordPress REST API is a later SEO/design project,
not a payment-launch requirement.

The `www` homepage permanently redirects to the canonical apex landing page.
This rule is deliberately limited to read-only requests for `/` and
`/index.html`. WordPress search/query shapes, mutations, blog, shop, checkout,
API, callback, admin, and every other path remain on `www`.

Do not depend on cookies being shared across these domains. Use the email access
grant exchange and app-owned sessions across the WordPress-to-Vercel boundary.

## Customer Journey

### 1. Landing

- The landing CTA goes directly to the fixed WooCommerce guest checkout for the
  one reading product.
- The price, included five chapters, expected delivery time, data requirements,
  refund rule, and support contact are visible before payment.
- The CTA wording is `立即購買完整解讀`, not `開始填寫資料`.
- Replace the current unimplemented CTA buttons with the same real direct
  checkout destination.

### 2. Direct Guest Checkout

The V1 product is a single virtual, sold-individually WooCommerce product.

Recommended settings:

- guest checkout enabled
- account creation disabled
- no login prompt
- no shipping fields
- quantity fixed to one
- direct checkout that skips the visible cart
- cart remains available internally for future multi-product work

The customer supplies only the commerce information WooCommerce and the payment
gateway need, including a valid billing email. Do not collect birth data,
relationship stage, question text, contact status, or astrology context in
WordPress, WooCommerce order metadata, URL parameters, or analytics.

Because that email is the accountless delivery credential, checkout requires a
second exact-match confirmation field and clear Traditional Chinese copy that
the paid form/result link will be sent there. Classic checkout and Checkout
Blocks must both validate the match on the server; browser-only comparison is
not sufficient.

The fixed product and price are server-owned. Never accept a price, arbitrary
product id, or customer email from a landing-page query string as trusted
commerce data.

### 3. Checkout Disclosure And Consent

Before payment, show:

- that this purchase is for one personalized relationship reading
- that the secure data form is sent by email only after payment is confirmed
- what birth and relationship data will be needed after payment
- `NT$1,280` total
- the expected delivery window measured from complete intake submission, not
  from checkout
- the billing email as the delivery and recovery address
- privacy notice
- refund/cancellation terms
- a required acknowledgement of the current commerce terms and privacy notice

Store the checkout terms version, timestamp, validated acceptance boundary, and
stamped reading-product ID on the WooCommerce order and in the private commerce
mirror. Also store the WordPress-server-created billing-email confirmation
digest, confirmation timestamp, and validated classic/Store API boundary. The
paid-order receiver must reject missing, malformed, future-dated, unsupported,
or replay-conflicting confirmation evidence; it must never infer confirmation
from the billing email alone. The current Taiwan legal draft requires two
separate, unchecked confirmations immediately before personalized generation:
data accuracy and immediate service commencement. Store each wording version,
content hash, timestamp, and immutable intake association separately.

Treat checkout terms as payment cohorts, not as one mutable global label. The
order's original presented version and timestamp are immutable and must never
be overwritten merely because the current terms changed. During a rotation,
the paid-order receiver must first accept both the old and new versions; only
then may WordPress stamp the new version on newly accepted checkouts while
retaining the old cohort for delayed ECPay callbacks and legitimate retries.
Keep both versions eligible until the old gateway payment, callback, and retry
windows are closed and every old-version order is reconciled. Removing a
version from only one side can charge a customer and then reject fulfillment.
If an old cohort is retired, block a fresh gateway handoff and require a newly
created order with explicit customer acceptance; never silently restamp the
old order.

### 4. Payment Confirmation And Invitation

WooCommerce and its gateway own card/wallet collection. The Vercel apps never
receive payment credentials.

The payment gateway may return the customer to a WooCommerce thank-you page,
but a return URL is not proof of payment and must not expose the intake form or
result link. The page should:

- confirm that the order was received
- show the destination email in masked form
- tell the customer to check inbox and spam for `開始填寫解讀資料`
- explain that the result delivery window starts after the form is submitted
- provide a neutral resend/support path if the email does not arrive

WooCommerce sends a signed webhook to the Vercel integration route. The route
and its durable email reconciler:

1. reads the raw request body
2. verifies `X-WC-Webhook-Signature`
3. deduplicates the delivery id
4. records a redacted event and payload hash
5. confirms the current order through the authenticated WooCommerce REST API
6. accepts only the recognized product, immutable checkout/confirmed-email
   evidence, and a genuinely paid order state
7. creates or updates one private commerce order and one reading entitlement in
   `awaiting_intake`
8. creates one active intake/result access grant
9. creates one fenced post-payment email job
10. calls the signed WordPress
    `POST /wp-json/vale-of-light/v1/access-email` boundary with only the order
    ID, grant ID, expiry, reviewed message kind, template version, and
    idempotency key
11. lets WordPress reconstruct the capability in memory and trigger
    WooCommerce's Customer Processing email
12. records WordPress mail acceptance or a retryable failure without treating a
    public gateway return as proof

The paid webhook creates entitlement and access. It does not enqueue or generate
a reading because no astrology intake exists yet.

#### ECPay method policy

Treat every enabled ECPay payment method as a separate production surface.
Credit card, installment, ATM, CVS, barcode, and iPASS must not share one
generic “ECPay passed” result. Each method that remains enabled needs its own
sandbox evidence for redirect/return, server callback, Woo paid timestamp and
`processing` transition, gateway transaction ID, duplicate/delayed callback,
failure/cancellation, and retry behavior. ATM, CVS, and barcode also require
instruction, `on-hold`, expiry, and late-callback cases.

Launch with only the smallest fully tested set; credit card is the recommended
first method. Disable every untested ECPay method. A staging clone must have all
live merchant credentials removed before sandbox credentials are installed, and
every callback/return host must resolve to staging during the test.

### 5. Post-Payment Email Access

Use WooCommerce's core customer email templates for both reading handoffs:

1. Customer Processing Order:
   `付款成功，請完成你的關係解讀資料`
2. Customer Completed Order:
   `你的完整關係解讀已完成`

The bridge suppresses automatic Processing and Completed emails for the reading
product so a normal Woo status event cannot send before the app has created the
grant or stored the result. The app is the only caller of a timestamped,
HMAC-signed WordPress notification endpoint. WordPress validates the order,
product, paid timestamp, terms and billing-email evidence, grant reference,
message kind, and idempotency key before triggering the appropriate core email.

The request never contains a raw capability URL or token. WordPress stores only
the non-secret grant ID and expiry, then reconstructs the capability in memory
with `VOL_ACCESS_SIGNING_SECRET` while Woo renders the email. The access secret
must match the app's `VALLEY_ACCESS_SIGNING_SECRET`. A separate notification
secret must match the app's
`VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET`; the two secrets must differ and
must be unique per environment. WordPress `VOL_APP_BASE_URL` must equal the
app's `VALEOFLIGHT_APP_BASE_URL`, and the app's
`VALEOFLIGHT_WORDPRESS_EMAIL_API_URL` must resolve to the matching environment's
`/wp-json/vale-of-light/v1/access-email` endpoint.

An asynchronous gateway may separately send an order-received, payment
instruction, or Customer On-Hold email before payment settles. That message is
not the reading-access invitation and must never contain the secure link.

The Processing and Completed emails use the exact same active capability link.
The Processing email is the primary handoff after verified payment and contains
the secure `開始填寫解讀資料` button. After authorization, that one URL resolves
according to current state:

- `awaiting_intake` or `intake_in_progress` -> open the form
- `queued`, `generating`, or `retrying` -> open the processing state
- `ready` or `delivered` -> open the stored result
- `refunded` or `revoked` -> apply the explicit refund/access policy

This gives the customer one memorable email entry point without creating an
account. The Completed email repeats the same link because the customer may
close the browser while generation is running; it does not create a second
reading link.

WooCommerce provides the templates and triggers, not inbox transport.
WordPress must use an authenticated SMTP/API mail transport with an approved
domain sender, SPF, DKIM, DMARC, delivery logs, and click tracking disabled for
capability links. A successful `wp_mail()`/Woo callback means the transport
accepted the message; it does not prove inbox delivery. Delivery, bounce,
complaint, or suppression claims are permitted only when the actual transport
provides stable message IDs/events and the application maps those events to the
matching delivery generation.

### 6. Post-Payment Intake

Collect the current required reading inputs in the Vercel reading app:

- relationship stage
- main question
- contact status
- both birth dates
- birth time when known
- birth city when known
- the existing framing field only where required

The form is available only to an authorized paid reading session. Save a private
draft in Supabase as the customer progresses. Do not put birth data, email,
relationship status, or question text in URLs, analytics, WooCommerce metadata,
or browser storage.

The final review screen shows:

- the two birth-data summaries and precision limitations
- the selected question and relationship context
- the expected result delivery window
- one unchecked data-accuracy confirmation
- one separately unchecked immediate personalized-service/withdrawal-exception
  confirmation using the approved Taiwan legal wording
- one clear `確認資料並開始產生報告` action

The customer can correct the form before final submission. After submission,
lock the intake snapshot used by the result. Later corrections require an
audited support/regeneration path rather than silently changing a paid result.

### 7. Submission And Paid Fulfillment

Final intake submission:

1. validates every required input server-side
2. verifies that the reading is paid, authorized, not refunded, and not already
   submitted
3. atomically changes the state from `intake_in_progress` to
   `intake_submitted`
4. stores the immutable intake and precision snapshot
5. stores the data-confirmation and service-start consent versions, content
   hashes, and timestamps
6. writes one durable fulfillment message in the same successful transaction;
   this is the service-start boundary
7. returns the authorized processing state

Generation is asynchronous. A Python worker consumes the durable message, runs
the locked reading pipeline, and returns the result and fingerprints through a
signed lease-fenced callback. The application first stores the result durably,
then sends a signed `result_ready` notification to WordPress. That authorized
WordPress action is the only supported path that changes the reading order from
`processing` to `completed` and triggers WooCommerce's Customer Completed
email. The app's WooCommerce REST credential may remain read-only because the
status mutation belongs to the narrow signed WordPress bridge.

The submission and worker must be idempotent. Repeated button presses, webhook
deliveries, or queue deliveries may create only one active fulfillment and one
result version for the order. After `intake_submitted`, normal customer routes
must never reopen or overwrite the form: intake writes return `INTAKE_LOCKED`,
and the state-aware reading link opens processing or the stored result.

### 8. Result Delivery

For access emails:

- use WooCommerce's Customer Processing and Customer Completed templates
- send them only through the signed app-to-WordPress bridge
- route WordPress through an authenticated SMTP/API transport with retained
  provider logs
- authenticate the sending domain with SPF, DKIM, and DMARC
- include accessible HTML and plain text
- include the order reference and support contact
- do not include sensitive reading conclusions in subject lines or previews
- disable click tracking on capability links
- never log or place the raw capability token in analytics
- verify the received email's raw `href` remains exactly the issued capability
  link

The result-ready email button must reuse the exact active order link from the
intake invitation. Do not rotate it merely because the result became ready.
Rotation is reserved for expiry, suspected disclosure, refund policy, or an
audited support action. An ordinary recovery request resends a still-valid
grant without disabling it. A replacement grant still points to the same
locked reading; it never creates a second intake or result.

### 9. Revisit And Recovery

Normal revisit:

- click the email button
- exchange the access grant
- set or refresh the reading session
- resume the unfinished form or show the same stored immutable result

Recovery:

- enter the checkout email and, optionally, the order reference
- always show the same neutral response
- rate-limit by IP and normalized email hash
- resend the current deterministic link when it remains valid
- rotate only an expired eligible grant, or through an audited staff action
- send only to the stored order email
- never expose a list of readings to an unauthenticated browser

## Responsibility Boundaries

| Concern | Source of truth | Must not own |
| --- | --- | --- |
| Blog posts | WordPress | reading data |
| Product, price, taxes, receipt, order, refund | WooCommerce | generated result |
| Gateway payment status | WooCommerce + payment gateway | app access |
| Intake and consent snapshot | private Supabase schema | Woo product catalog |
| Fulfillment state and retries | private Supabase schema + queue | payment capture |
| Calculation and Chinese realization | Python worker | checkout UI |
| Intake/result access and sessions | Vercel reading app + private Supabase | Woo customer login |
| Reading email authorization and delivery state | Vercel app + private Supabase | payment capture |
| Processing/Completed email rendering and order completion | signed WordPress bridge + WooCommerce core emails | reading calculation |
| Inbox transport and provider logs | authenticated WordPress SMTP/API provider | entitlement creation |

## Order And Fulfillment State

Keep commerce and fulfillment statuses separate.

```text
WooCommerce
pending -> processing (paid) -> completed (reading ready)
       \-> failed / cancelled
failed / cancelled -> processing (successful payment retry)
processing or completed -> refunded

Application
paid
  -> awaiting_intake
  -> intake_in_progress
  -> intake_submitted
  -> queued
  -> generating
  -> ready
  -> delivered
  -> revoked
  -> erased

queued / generating -> retrying -> needs_review
paid / awaiting_intake / intake_in_progress / intake_submitted / queued /
generating / ready / delivered -> refunded
```

Rules:

- `order.created` is not payment proof.
- `processing` or an equivalent paid state creates the entitlement and sends
  the intake invitation only after server-side verification.
- `failed` and `cancelled` are pre-payment states: they create no entitlement,
  but a later authoritative paid retry on the same order remains allowed.
- `refunded` is terminal in the application and creates the durable tombstone.
- only authorized final intake submission may create the durable fulfillment
  message and start generation.
- `completed` means the reading is ready, not merely that money was received.
- a refund event follows the agreed access policy and records the decision.
- fulfillment transitions are monotonic; the only supported commerce reversal
  is a failed/cancelled payment retry reaching a paid state. Refund remains
  terminal.

## Private Supabase Data Model

Customer and fulfillment tables should live in a non-exposed `private` schema.
The browser never queries them directly. Server and worker credentials stay
server-side.

### `private.readings`

- `id`
- `public_id`
- `intake_version`, nullable until final submission
- `person_a`, nullable until intake
- `person_b`, nullable until intake
- `context`, nullable until intake
- `precision_snapshot`, nullable until final submission
- `checkout_terms_version`
- `checkout_terms_accepted_at`
- `data_confirmation_version`, nullable until final submission
- `data_confirmation_content_hash`, nullable until final submission
- `data_confirmation_accepted_at`, nullable until final submission
- `generation_consent_version`, nullable until final submission
- `generation_consent_content_hash`, nullable until final submission
- `generation_consent_accepted_at`, nullable until final submission
- `status`
- `intake_started_at`, `intake_submitted_at`
- `created_at`, `updated_at`

Create this row only after verified payment. Until intake is submitted it is a
paid entitlement in `awaiting_intake` or `intake_in_progress`, not an unpaid
draft and not a queued reading.

### Intake Lock Invariant

Enforce the one-order, one-intake rule below the UI:

- `private.commerce_orders.reading_id` is unique and identifies the only normal
  reading journey for that order
- final submission uses one database transaction with a conditional state
  change from `intake_in_progress` to `intake_submitted`
- if that conditional update affects zero rows, the API returns
  `INTAKE_LOCKED` and does not write a queue message
- a database trigger rejects changes to `person_a`, `person_b`, `context`,
  `precision_snapshot`, both final confirmations, and their evidence after
  `intake_submitted_at` is set
- the unique active-fulfillment constraint prevents a second generation job

Any legitimate correction is a staff-only, audited versioning workflow that
preserves the original intake and result. It must never reopen the ordinary
customer form or silently overwrite the first submission.

### `private.commerce_orders`

- `id`
- `provider`
- `provider_order_id`
- `reading_id`
- `product_code`
- `amount_minor`
- `currency`
- `billing_email`
- `normalized_status`
- `gateway_transaction_id`
- `paid_at`, `refunded_at`
- unique `(provider, provider_order_id)`

Do not store raw card or wallet credentials. Decide whether application-level
encryption is required for email and birth-data fields before production.

### `private.fulfillments`

- `id`
- `reading_id`
- `commerce_order_id`
- `status`
- `attempt_count`
- `last_error_code`
- `runtime_version`
- `result_contract_version`
- `started_at`, `ready_at`, `delivered_at`
- unique active fulfillment per order

### `private.reading_results`

- `reading_id`
- `contract_version`
- `result_payload`
- `result_hash`
- `source_fingerprints`
- `created_at`
- `revoked_at`

Once ready, the customer result is immutable. A regeneration creates a new
version with an audit reason; it does not silently rewrite an old paid reading.

### `private.reading_access_grants`

- `id`
- `reading_id`
- `token_hash`
- `purpose`
- `expires_at`
- `last_used_at`
- `revoked_at`
- `created_at`

Use a purpose such as `intake_and_result`; the grant authorizes access to one
reading journey but never creates a paid entitlement by itself.

### `private.reading_sessions`

- `id`
- `reading_id`
- `session_token_hash`
- `expires_at`
- `last_used_at`
- `revoked_at`

### `private.integration_events`

- `source`
- `delivery_id`
- `topic`
- `payload_hash`
- `signature_verified`
- `processing_status`
- `error_code`
- `received_at`, `processed_at`
- unique `(source, delivery_id)`

Store only the minimum redacted payload needed for support and reconciliation.

### `private.email_deliveries`

- `reading_id`
- `message_kind`
- `template_version`
- `provider_message_id`
- `provider_generation`
- `provider_request_hash`
- `recipient_hash`
- `status`
- `attempt_count`
- `sent_at`, `delivered_at`, `bounced_at`

For `provider = 'woocommerce'`, the request hash binds the grant, message kind,
template, and signed WordPress request to one delivery generation. The current
`woo.<hash>` value is a synthetic WordPress notification/idempotency receipt;
it is not an SMTP provider message ID and does not prove inbox delivery.

Email health must therefore be provider-aware:

- pending, sending, and retryable failed rows may become overdue for every
  provider;
- a Woo row marked `sent` means WordPress's mail transport accepted it and must
  not become permanently overdue merely because no Resend-style delivery
  webhook exists;
- an accepted row may be held to a delivery-event deadline only when its actual
  SMTP/API provider supplies a stable message ID and mapped events; and
- provider-level `delivered`, `bounced`, `complained`, or `suppressed` claims
  must never be inferred from the synthetic Woo receipt.

If the selected WordPress transport supplies verified provider events,
recipient-level suppression is stored separately so a complaint, hard bounce,
or provider suppression cannot be bypassed by a new template or recovery row.
Only a DB-owner support action may clear it, with actor evidence and a reason
code. Without that integration, operations must rely on authenticated provider
logs and a tested support resend/correction process and must describe the
database state only as accepted by WordPress.

## Application Routes

Recommended public/server route shape:

```text
POST /api/integrations/woocommerce/webhook
POST /api/integrations/resend/webhook          # optional legacy compatibility
POST /api/internal/woocommerce/reconciliation
POST /api/internal/reading-worker/email-reconciliation
POST /api/reading-access/exchange
POST /api/reading-access/recover
GET  /api/reading-access
PATCH /api/reading-access/intake
POST /api/reading-access/submit
```

The app also makes one narrow outbound call:

```text
POST https://<matching-wordpress-host>/wp-json/vale-of-light/v1/access-email
```

That call uses the exact raw JSON body, a short-lived timestamp, and a separate
HMAC notification secret. It never sends the raw access token, result payload,
birth data, or relationship data to WordPress.

Requirements:

- validate all public input server-side
- add request size limits and rate limits
- reject every intake mutation after `intake_submitted`, regardless of what the
  browser UI displays
- set reading/status/access responses to `Cache-Control: private, no-store`
- add `noindex, nofollow` to private result routes
- perform authorization in each route handler, not only in middleware/proxy
- return a customer DTO with no debug block, internal rule ids, source
  fingerprints, full evidence graph, or service metadata

The current public `POST /api/readings/relationship-result` must become an
internal worker boundary or be removed before launch. A browser may not create a
paid result without both a verified paid entitlement and a valid final intake
submission.

## WordPress Bridge

Keep the custom WordPress surface small:

```text
wordpress/
  valley-of-light-commerce-bridge/
    valley-of-light-commerce-bridge.php
    src/
      DirectCheckout.php
      OrderMetadata.php
      ThankYouMessage.php
      AccessEmailPolicy.php
      AccessEmail.php
      HealthStatus.php
    tests/
```

Responsibilities:

- provide one fixed, server-owned product/direct-checkout entry point
- store immutable checkout terms and billing-email confirmation evidence
- show the masked-email post-payment instruction on the thank-you page
- keep verified paid reading orders in `processing`
- suppress automatic Customer Processing and Customer Completed emails for the
  reading product
- expose one signed, timestamped, idempotent `/access-email` endpoint
- reconstruct the same state-aware capability only while rendering the
  authorized Woo core email
- change `processing` to `completed` only for a signed `result_ready` request
- provide a protected staff resend action that reuses the current grant

It must not contain astrology calculation logic, Supabase service credentials,
birth or relationship intake, raw access tokens, or result payloads.

Its app-base URL, access-signing secret, and notification-signing secret are
environment-owned configuration. Missing, weak, identical, cross-environment,
or non-HTTPS values fail the bridge health check and keep checkout closed.

Use WooCommerce's built-in signed webhooks for order updates. Add a small custom
event only if the built-in paid/refund events cannot express the required state
reliably.

## Durable Work And Reconciliation

Launch implementation:

- Supabase Queues for durable fulfillment messages
- a separately deployed Python worker using the existing calculation/runtime
  code
- an authenticated Vercel Cron route that scans bounded WooCommerce REST pages
  through the same paid/refund database paths as webhooks

The Woo scan persists its active time window, page cursor, run outcome, lease,
clean-success time, and high-water mark. Every run overlaps the prior
high-water window, and every REST order receives a deterministic integration
event ID. A crash therefore replays the same page idempotently. Review failures
retain the current page and prevent high-water advancement; production health
remains closed until a later clean run reaches a recent high-water mark.

Refund reconciliation intentionally does not compare a historical order with
today's product ID, price, or currency. It still trusts only the authenticated
current Woo order ID and `refunded` status, and it can revoke only an
entitlement already recorded by the application. If the paid webhook was
missed entirely, an unknown refund creates a terminal fence only when the
refunded order itself contains the configured product; unrelated orders are
recorded and ignored.

The paid webhook does not write a generation queue message. It creates the paid
entitlement and triggers the invitation email. The queue message is written
only after the authorized customer submits a complete intake.

The current Next.js route shells out to a local `.venv` Python executable. That
is a local prototype bridge, not a Vercel production boundary.

The reconciliation job must find:

- paid Woo orders with no application entitlement
- paid Woo orders with no WordPress-accepted Processing email
- `awaiting_intake` orders past the reminder/support threshold
- `intake_in_progress` orders past the completion threshold
- submitted intakes with no fulfillment
- fulfillment stuck in `queued`, `generating`, or `retrying`
- results ready but no WordPress-accepted Completed email
- Woo webhooks disabled after repeated failures
- refunded orders with active access
- paid-order total/currency/shape exceptions awaiting reconciliation

The ten-minute Woo reconciliation schedule runs only on a Vercel project's
Production deployment. Staging therefore uses the Production target of its
separate staging project; Preview deployments do not prove the schedule.
Every scheduled request remains authenticated and idempotent because Vercel
does not retry a failed invocation and may deliver duplicates.

## Security And Privacy

### Environment isolation

- use separate Supabase, Vercel, WordPress, worker, mail, and ECPay environments
  for staging and production
- use an isolated source copy/worktree linked to the staging Vercel project;
  never reuse the production-linked `apps/web/.vercel/project.json`
- deploy the staging app to the Production target of its separate staging
  Vercel project so its stable host and Cron can be tested without touching
  Valley production
- create the staging Woo webhook only after the isolated receiver and health
  route are deployed and verified
- keep the production WordPress launch gate OFF; enable only the staging gate
  during a bounded checkout test and turn it back OFF afterward
- never share Supabase, Woo REST, webhook, access, WordPress-notification,
  worker, Cron, mail, or ECPay credentials across environments
- prefer a clean WordPress staging install; otherwise scrub real customers,
  orders, sessions, logs, queued emails/webhooks, and copied scheduled actions
  while all outbound traffic remains paused
- remove live ECPay merchant credentials from a clone before configuring
  sandbox, and allowlist only test email recipients
- ensure Basic Auth/deployment protection allows the HMAC-protected webhook,
  `/access-email`, Woo REST, and Cron machine requests without exposing private
  customer routes

### Vercel application

- use a commercial Vercel plan for the live paid product; Hobby is documented
  for personal, non-commercial use
- upgrade Next.js and React to current patched releases before customer traffic
- add CSP and standard security headers
- set strict body limits and timeouts
- rate-limit intake, access, recovery, and webhook routes
- keep all service credentials in environment-specific server secrets
- do not rely on route middleware as the only access control
- do not send email, birth data, token values, or relationship context to
  analytics

### WordPress and WooCommerce

- use managed hosting with staging, backups, WAF/CDN, and supported PHP
- enable admin MFA and separate named staff accounts
- disable public WordPress registration and Woo account creation
- keep the plugin list minimal
- pin a WordPress/WooCommerce/PHP matrix supported by the payment plugin
- test upgrades on staging before production
- protect and rotate REST API and webhook credentials
- protect the signed `/access-email` route with its own environment-specific
  HMAC secret and timestamp window
- use an authenticated SMTP/API transport with SPF, DKIM, DMARC, retained logs,
  a test-recipient allowlist in staging, and click tracking disabled
- keep Customer Processing and Customer Completed emails enabled while the
  bridge suppresses their unauthorized automatic triggers

### Supabase

- use separate staging and production projects
- keep customer data out of browser-exposed schemas
- otherwise enable RLS and revoke `anon`/`authenticated` access explicitly
- never expose the service-role key
- back up customer/order/result data and test restore
- keep the reading-content erasure executor private from the app service role
- define and approve positive retention windows for incomplete, delivered, and
  revoked readings; do not assign defaults in code
- treat commerce/provider/log/backups as separate retention scopes, and replay
  the erasure ledger before restored backups receive traffic

### Access links

- use at least 256 bits of randomness
- compare token hashes in constant-time application logic
- support rotation and revocation
- scope the grant to the order-linked intake/result journey
- keep the V1 grant usable for 30 days across devices unless rotated or revoked;
  recovery resends the same deterministic link while it remains valid and
  sends a fresh grant to the order email only after expiry
- exclude access routes from analytics and session replay
- exchange the signed route capability once into a host-only `HttpOnly` cookie,
  then immediately redirect to the clean `/reading` URL
- disable provider click tracking for access links
- verify transport/provider rewriting does not change the received capability
  `href`

## Taiwan Commerce And Consent Gate

Before launch, have Taiwan counsel/accounting review:

- legal entity and support contact disclosures
- service scope, price, payment, delivery time, and complaint path
- privacy notice and retention
- refund/cancellation language
- checkout acknowledgement and the two separately accepted final-submit
  confirmations recorded immediately before personalized generation begins
- whether and how the seven-day withdrawal exception applies
- invoice issuance and the selected ECPay/WooCommerce invoice flow

The recommended commercial policy is a full cancellation before the server
successfully accepts the final intake and creates its generation job, followed
by no voluntary change-of-mind refund after that clearly accepted service-start
boundary, to the extent Taiwan law allows. A blanket “no refund once the order
is placed” rule is not approved. Do not copy a generic `digital content is
non-refundable` checkbox without Taiwan review. This policy does not remove
operational handling for a full Woo refund, payment reversal, chargeback,
duplicate charge, non-delivery, or material defect. Those commerce reversals
remain terminal and revoke access. Partial refunds are unsupported for V1 and
must not be offered through staff or gateway workflows unless a separate
product, access, accounting, and reconciliation policy is implemented and
tested.

## Observability And Support

Minimum production signals:

- paid orders per hour/day
- payment-confirmed to invitation-sent latency
- invitation-sent to intake-started conversion and latency
- intake-started to intake-submitted conversion and latency
- paid orders still awaiting intake after the reminder threshold
- intake-submitted to queued latency
- queued to ready latency, including p50/p95
- generation error and retry rate
- paid order with no result after the delivery SLO
- webhook signature failures and webhook delivery gaps
- WordPress notification accepted/failed/retried
- SMTP/API inbox delivery, bounce, and complaint only when the actual transport
  exposes verified mapped events; otherwise provider-log and support exceptions
- recovery-link request rate
- result access 4xx/5xx rate
- WordPress, worker, Vercel, and Supabase health

Create one support lookup using Woo order number or billing email. It should
show order status, intake status, fulfillment status, email status, access
status, and safe actions without exposing raw tokens.

## Failure Behavior

| Failure | Customer behavior | System behavior |
| --- | --- | --- |
| Payment redirect returns before webhook | Thank-you page says confirmation email will follow | Never create access or generate from the redirect |
| Duplicate webhook | No visible duplicate | Unique delivery/order constraints make it idempotent |
| Webhook missed/disabled | Intake invitation may be delayed | Reconciliation imports the paid order and alerts staff |
| Invitation send fails | Thank-you page still gives a resend/support path | Retry delivery; alert staff; never expose the link on the public order page |
| Customer has not started intake | No pressure or false processing message | Send the approved reminder cadence and expose status to support |
| Customer leaves intake unfinished | Link resumes the saved form | Retain the paid draft under the approved policy and allow reminders |
| Customer resubmits or revisits the form after submission | Open processing or the completed result | Reject all intake mutations with `INTAKE_LOCKED`; never enqueue a second reading |
| Calculation fails | Show a calm processing/support state | Retry with backoff, then `needs_review` |
| WordPress mail transport rejects a message | Public thank-you page does not expose intake | Retry the fenced notification and alert support |
| Mapped SMTP/API provider reports a bounce or complaint | Public thank-you page does not expose intake | Suppress later sends to that recipient hash; require audited correction or re-consent |
| Provider has no mapped delivery events | Do not claim delivered status | Use authenticated provider logs, inbox tests, and the approved support resend/correction process |
| Link is still valid but email was lost | Show the neutral recovery action | Keep the working grant active and resend the same deterministic link |
| Link is expired/revoked | Show recovery action, no intake or result | Rotate only an eligible expired grant and send it to the stored order email |
| Result page refreshes | Same reading reopens | Load stored result by authorized session |
| Full refund, reversal, or chargeback | Follow visible policy and support wording | Revoke active access/result delivery and retain the terminal tombstone |
| Partial refund attempt | Support explains V1 does not support partial refunds | Block the workflow; do not create an undefined mixed access state |

## Current Launch Blockers

The repository now has the private schema, payment verification, exact
pre-gateway WooCommerce total guard, one-link access journey, immutable
intake/result storage, portable published-only worker, bounded email
outbox/reconciliation, signed app-to-WordPress Woo email bridge, terminal refund
revocation, asynchronous email-based link recovery, and a private audited
reading-content erasure path. The legacy browser generation routes fail closed
outside local development.

The remaining launch blockers are external validation and explicit decisions:

1. create and positively identify an isolated staging Supabase project, apply
   every repository migration in order, and execute concurrency/state tests;
2. configure an authenticated WordPress SMTP/API transport, authenticate the
   sending domain, disable click tracking, and prove acceptance, exact-link,
   inbox, provider-log, and support behavior;
3. validate paid-access provider-aware email health in staging so a Woo-accepted
   message does not require a nonexistent Resend delivery webhook, and map
   provider delivery events before claiming bounce/complaint suppression;
4. resolve Immanuel/Swiss Ephemeris licensing and deploy the worker;
5. deploy the paid app with reviewed secrets and create the signed
   WooCommerce webhook;
6. run a payment-neutral Woo integration test and an ECPay sandbox matrix for
   every method that will remain enabled; disable all untested methods;
7. approve the result-delivery promise, generation-consent copy, no-voluntary-
   refund wording, support ownership, and retention windows/anchors/holds/
   backups;
8. finish the remaining final-Chinese realization review and human acceptance;
9. receive explicit production deployment and final launch-gate approvals;
10. confirm hosted Supabase structured KB parity and production-only status
   gates;
11. run the migration and concurrency scenarios against a disposable staging
    database;
12. complete the staging checkout, webhook, full-refund/reversal, recovery,
    erasure, and restore test matrix; and
13. confirm paid production plans, budgets, spend alerts, and retention for
    Vercel, managed WordPress, Supabase, the Python worker, email, and
    monitoring.

## Implementation Phases

### Phase 0 - Lock Launch Decisions

- domain names
- payment gateway through WooCommerce
- direct checkout and no visible cart
- payment-before-intake
- result delivery SLO
- access-link lifetime and recovery policy
- refund/access policy
- legal consent and invoice requirements

### Phase 1 - Commerce And Data Foundation

- create managed WordPress staging
- install only WooCommerce, the selected gateway/invoice module, and the bridge
- configure one virtual sold-individually product
- add private Supabase customer/commerce migrations
- enable durable queue
- deploy the Python worker against staging

### Phase 2 - Checkout And Paid Entitlement

- connect all landing CTAs to the fixed direct WooCommerce checkout
- implement and verify WooCommerce webhooks
- build the paid entitlement and state-aware reading entry point
- configure the signed WordPress bridge and Woo Customer Processing invitation
- configure authenticated WordPress SMTP/API transport and WooCommerce
  thank-you instructions
- add invitation retry, resend, and reconciliation

### Phase 3 - Post-Payment Intake, Fulfillment, And Access

- implement access-grant exchange and session checks
- persist authorized post-payment intake drafts
- implement final intake validation, consent, and idempotent submission
- enqueue only after final intake submission
- store immutable results
- implement the processing/status page
- implement recovery and resend
- configure the Woo Customer Completed result-ready template and signed
  completion trigger
- add admin fulfillment state and resend/reconcile actions
- remove debug/internal data from customer payloads

### Phase 4 - Production Hardening

- fix city/timezone correctness
- finish R7/R8 human acceptance
- upgrade and audit dependencies
- add rate limits, CSP, private/no-store headers, and noindex
- add reconciliation, alerting, backups, and restore drill
- validate the private reading-content erasure action and approved retention
  scheduler without granting it to the app service role
- complete privacy, terms, refund, invoice, and support pages

### Phase 5 - Release Validation

Run at least:

- desktop and mobile successful guest checkout
- failed, abandoned, and delayed payment
- failed/cancelled payment followed by a successful retry on the same order
- coupon, tax, fee, shipping, extra-item, and wrong-total checkout rejection
- duplicate, delayed, invalid-signature, and missing webhook
- paid order, invitation delivery, and first-device intake access
- paid order with no intake start, reminder, and staff resend
- saved intake resume and duplicate final submission
- calculation timeout and retry
- refresh during processing
- result refresh and second-device access
- expired/revoked link and recovery
- wrong email recovery attempt
- transport rejection, inbox placement, provider logs, and support resend
- bounce/complaint suppression only when verified provider events are integrated
- refund before intake submission and after result readiness
- delayed paid webhook after refund cannot recreate access
- full refund, payment reversal, and chargeback where the gateway exposes them
- verify partial refunds are disabled/unsupported for V1
- each ECPay method that will remain enabled; disable every untested method
- unknown birth time
- invalid and overseas city
- WordPress/plugin upgrade rehearsal
- Supabase restore rehearsal
- audited reading-content erasure and restored-backup erasure replay
- rollback rehearsal for Vercel, worker, and WordPress

Do not go live until a paid sandbox order can travel from landing CTA to
invitation email, authorized intake, stored result, result email, revisit,
refund, and reconciliation without manual database edits.

## Recommended Defaults Requiring Approval

| Decision | Recommended default |
| --- | --- |
| Customer account | none |
| Visible cart | skip for V1 |
| Checkout | native WooCommerce guest checkout |
| Journey order | payment, secure email link, intake, result |
| Payment gateway | ECPay through its supported WooCommerce module, pending sandbox verification |
| Blog | native WordPress at launch |
| Result compute | durable queue plus separate Python worker |
| Intake/result access | opaque email capability exchanged for an app session |
| Number of reading links | one state-aware order link reused in Woo Processing and Completed emails |
| Email rendering | WooCommerce core customer templates through the signed WordPress bridge |
| Inbox transport | authenticated WordPress SMTP/API provider; acceptance is not delivery |
| Email access grant | reusable for 30 days unless rotated/revoked; then recover by email |
| Session | 30 days, renewable by valid access grant |
| Incomplete-intake reminders | two maximum, at 24 and 72 hours, pending copy/privacy approval |
| Result content | stored immutable payload, not regenerated on every visit |
| Woo completion | only after the result is ready |
| Paid-result cache | `private, no-store` |
| Recovery | resend the valid link or rotate an expired grant by email; never expose order existence |
| Voluntary refund | none once ordered, pending Taiwan legal review; full reversals remain terminal |
| Partial refund | unsupported and disabled for V1 |

## Official References

- WooCommerce Accounts and Privacy:
  <https://woocommerce.com/document/configuring-woocommerce-settings/accounts-and-privacy/>
- WooCommerce webhooks:
  <https://woocommerce.com/document/webhooks/>
- WooCommerce Store API security:
  <https://developer.woocommerce.com/docs/apis/store-api/nonce-tokens/>
- ECPay WooCommerce module:
  <https://developers.ecpay.com.tw/62167/>
- Supabase Queues:
  <https://supabase.com/docs/guides/queues>
- Supabase RLS:
  <https://supabase.com/docs/guides/database/postgres/row-level-security>
- Vercel cache control:
  <https://vercel.com/docs/caching/cache-control-headers>
- Vercel Python runtime:
  <https://vercel.com/docs/functions/runtimes/python>
- Vercel plans:
  <https://vercel.com/pricing>
- Taiwan distance-transaction disclosure duties:
  <https://cpc.ey.gov.tw/Page/4432D6D5FA6677B9/d4f8fdec-7fff-4100-bbbb-1e3c9792c58e>
- Taiwan withdrawal-right exception guidance:
  <https://cpc.ey.gov.tw/Page/BC16ACF0BBB9CCC2/f8e15c56-0cbe-49ac-a7ba-2f41e1d9ca55>
