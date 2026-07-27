# 14 - Production Launch Readiness

> Status: **NOT READY FOR PRODUCTION**
> Updated: 2026-07-26
> Launch gate: **OFF**
> Scope: WooCommerce payment -> post-payment intake -> generated result -> same-link revisit

## Purpose

This document is the operational source of truth for launching the paid
relationship reading. It distinguishes:

1. safeguards implemented and validated only in the local repository;
2. configuration already present on the live WordPress/WooCommerce site;
3. external services that are not yet production-confirmed; and
4. actions that require the user's credentials, infrastructure decision, or
   explicit production approval.

The presence of code, domains, a WooCommerce product, or a payment plugin does
not make the complete paid flow production-ready.

## Current Decision

Keep `vol_commerce_launch_enabled` set to `no`.

Do not deploy the new paid-access application, apply the private production
database migration, create the live WooCommerce webhook, run a charge, or
enable purchasing until the gates in this document have passed in order.

## Current State At A Glance

| Area | Current state | Launch meaning |
| --- | --- | --- |
| Public domain and landing reverse proxy | Live and guarded | Apex marketing routing is live; WordPress/WooCommerce routes remain on the `www` canonical host |
| `app.valeoflight.com` domain | Attached to `valley-of-light-relationship-preview` | The paid-access implementation is still local; the production project remains preset to Vite and must be reviewed for the Next.js deployment |
| Result-app Vercel environment | Empty | The live project has none of the required paid-flow variables and its paid-reading health route is not deployed |
| Result-app staging Vercel project | `valley-of-light-app-staging`, Next.js preset | It has no environment variables or deployment; only its default non-production hostname exists |
| Local Vercel link | Points to the production result project | Staging work must use an isolated worktree/source copy linked and re-verified against the staging project ID |
| Vercel plan | Pro | The ten-minute Cron cadence is supported, but Cron still runs only on a project's Production deployment |
| WordPress commerce bridge | Live, version `0.1.7` | Product and checkout policy checks pass |
| WordPress commerce bridge candidate | Local, version `0.3.0` | Adds signed Woo Processing/Completed email delivery and result-owned completion; not installed on staging or live |
| Fixed WooCommerce product | Product ID `13` configured | Correct SKU, type, virtual/sold-individually settings, stock, `TWD 1,280`, and currency were confirmed |
| Guest checkout | Enabled | Account creation is disabled; checkout and terms pages exist |
| Commerce launch gate | **OFF** | The fixed reading must remain non-purchasable |
| Paid-access Next.js foundation | Implemented and validated locally | Not connected to production services |
| Private paid-reading migration | Present locally; production project identified | The linked `Valley of light` project is production; no migration was applied and no staging project is configured |
| Taiwan commerce/legal copy | Drafted, not approved | Company disclosures, delivery/retention promises, the service-start refund cutoff, and two separately recorded final-submit confirmations still block launch |
| Reading email rendering | Woo core Processing/Completed templates through local signed bridge | Staging bridge, secrets, templates, and endpoint have not been exercised |
| WordPress mail transport | Not production-confirmed | Authenticated SMTP/API transport, sender DNS, provider logs, inbox tests, and support resend are required; Resend is not a launch dependency |
| Result worker | Portable container, AGPL release guard, and Render blueprints implemented; not hosted | AGPL is selected, but the matching source archive still must be published before worker deployment |
| WooCommerce application webhook | Not launch-verified | A valid shared secret and deployed receiver are still required |
| ECPay | Multiple live WooCommerce methods configured | No sandbox method matrix or application-handoff proof exists; every untested method must remain disabled at launch |
| `www` homepage SEO policy | Canonical redirect implemented | Read-only `/` and `/index.html` requests redirect to the apex; WordPress routes remain on `www` |

The live WordPress state above was confirmed through the authenticated,
non-mutating commerce health endpoint on 2026-07-26. It returned HTTP `200`,
all product/checkout checks passed, `launch_enabled` was `false`, and the
overall `ready` value was therefore `false`.

## Implemented Locally

The following safeguards exist in the repository and passed local automated
validation. They are not evidence of a working live integration.

### Commerce verification

- The WooCommerce receiver verifies the webhook HMAC over the raw request body.
- It re-fetches the order through authenticated WooCommerce REST API access.
- It accepts only `processing` or `completed` orders with a paid timestamp.
- It verifies the fixed product, quantity, currency, exact expected amount,
  billing email, and immutable checkout-terms evidence: accepted version,
  presentation timestamp, validated acceptance boundary, and stamped reading
  product ID.
- It also requires the WordPress-server-created billing-email confirmation
  digest, confirmation time, and recognized classic/Store API acceptance
  boundary. Missing, malformed, future-dated, unsupported, or conflicting
  evidence fails closed.
- The local bridge `0.3.0` candidate also enforces the exact `TWD 1,280`
  contract before gateway handoff for classic checkout, Checkout Block, and
  order-pay retries. Coupons, discounts, fees, shipping, taxes, variations,
  extra products, and quantity drift fail closed.
- That bridge requires the buyer to enter the payment email twice, compares the
  values at WooCommerce's server boundary, stores only a keyed digest plus
  timestamp/source evidence, and revalidates it before every initial or retried
  payment handoff.
- The same bridge blocks order-payment retries while the launch gate or current
  configuration is invalid, retains immutable per-order terms evidence, and
  supports an explicit old/new terms-cohort overlap during safe rotations.
- Duplicate webhook deliveries and duplicate paid-order processing are
  designed to remain idempotent.
- A verified refund creates the durable terminal-order tombstone, so a delayed
  paid event cannot recreate access. Failed and cancelled pre-payment states
  are recorded without becoming permanent tombstones, allowing a later
  authoritative ECPay retry to reach `processing` or `completed`.
- Historical refunds are revalidated by current Woo order ID and status but do
  not depend on today's catalog price, currency, or product configuration for
  an existing entitlement. A refund seen before a missed paid webhook creates
  a terminal fence only when its line items identify the configured product;
  unrelated unknown orders are recorded without revoking anything.
- A ten-minute authenticated Vercel Cron performs bounded Woo REST
  reconciliation with persisted leases, scan windows, page cursors, run
  outcomes, deterministic event IDs, and an overlapping lookback. Failed
  review pages do not advance. Launch health requires a recent clean
  high-water mark.
- A paid order whose total, currency, or shape violates the fixed contract is
  recorded as failed and returns a retryable receiver error for operational
  review; it is not silently accepted or granted access.
- A reused WooCommerce delivery ID is accepted only when its topic, order, and
  payload hash match the original delivery.

### Reading access and intake

- One signed order-linked URL exchanges into a host-only `HttpOnly` cookie,
  removes the capability from the visible URL, and resolves to intake,
  processing, or the stored result according to server state.
- The raw capability URL is not stored in the database; only its hash is
  stored.
- Draft intake can be resumed before final submission.
- Final submission atomically locks the intake and creates one fulfillment.
- The private fulfillment record supports signed worker claims, leases,
  attempt fencing, bounded retry attempts, and terminal `needs_review` state.
- Later visits cannot reopen or submit a different data set.
- Unsupported nonempty birth cities fail closed. The customer can choose a
  reviewed supported city or leave the field blank, which blocks
  location-sensitive house/angle claims.
- Public lookup, draft, and submit routes have validation, body limits, rate
  limits, exact-origin and JSON mutation checks, private caching rules, and
  generic failure responses.

### Result and email boundaries

- WooCommerce's core Customer Processing and Customer Completed templates are
  the customer-facing reading emails. They reuse the exact same state-aware
  reading URL.
- The candidate bridge suppresses automatic Processing and Completed emails for
  the reading product. Only the app's timestamped HMAC request to
  `POST /wp-json/vale-of-light/v1/access-email` may trigger them.
- The signed request contains only the order ID, non-secret grant UUID and
  expiry, reviewed message kind, template version, and idempotency key.
  WordPress reconstructs the raw capability in memory while Woo renders the
  message; the raw token or result never enters the request or stored order
  metadata.
- After verified payment and grant creation, the signed
  `intake_invitation` request triggers the Processing email. After the result is
  durable, the signed `result_ready` request is the only authorized path that
  changes `processing` to `completed` and triggers the Completed email.
- Email claims and stored results have idempotency boundaries. WordPress stores
  a non-autoloaded request receipt and returns the same receipt for an exact
  replay without sending a second message.
- Invitation, result, and recovery attempts are fenced in the private outbox;
  the worker reconciles missing, failed, and stale attempts independently of
  WooCommerce and result callbacks.
- Notification retries are capped at five, use persisted exponential backoff,
  and finish in a terminal `suppressed` state instead of retrying forever.
- A `woo.<hash>` value is a synthetic WordPress notification receipt. It proves
  bridge idempotency and WordPress mail acceptance only; it is not an SMTP
  provider message ID and does not prove inbox delivery.
- Production requires an authenticated WordPress SMTP/API transport, approved
  sender, SPF/DKIM/DMARC, provider logs, inbox tests, support resend/correction,
  and click tracking disabled. The received raw `href` must exactly match the
  issued capability link.
- Delivery, bounce, complaint, and provider suppression may be claimed only if
  the chosen transport exposes stable provider message IDs and verified events
  mapped to the correct delivery generation. Without that integration,
  operations must describe the message only as accepted by WordPress and use
  provider logs plus the support process.
- The worker callback requires a timestamped HMAC signature.
- Customer result payloads must pass the explicit paid-result contract, size
  and depth bounds, and remove debug, draft-only, and hidden storyline fields.
- The paid result is immutable through the normal customer flow.
- A result that completes close to link expiry receives a replacement grant
  atomically instead of becoming ready but inaccessible.
- A revalidated `refunded` WooCommerce order revokes the active grant and
  result and prevents automatic re-entitlement. Failed/cancelled payment
  attempts do not receive access and can later be paid on the same order.
- Customer recovery is non-enumerating and uses the billing email plus unique
  WooCommerce order number. If the current grant is still valid, recovery
  keeps it working and resends the same deterministic URL. It rotates only an
  already-expired grant, returns without waiting on WordPress delivery, and
  sends only through the signed reconciler to the stored order email.
- An authoritative paid replay with an expired, unrevoked grant atomically
  revokes that grant, creates one replacement, and sends the replacement as a
  recovery link instead of failing the webhook.
- A DB-owner-only audited reading-content erasure action revokes grants and
  active work, then clears intake and result payloads through narrow one-way
  immutability-trigger exceptions. The app service role cannot execute it,
  and delayed webhooks/workers cannot recreate access afterward.
- Retention has no invented default duration. Production health fails until
  the approved `VALLEY_RETENTION_POLICY_VERSION` matches an explicitly enabled
  database policy with positive incomplete, delivered, and revoked windows.
  Commerce, provider, log, and backup retention remain separate policy items.
- Each retention run stores the exact approved policy snapshot, rechecks that
  each reading is still due after acquiring its row locks, honors holds, and
  bounds every owner batch. Stale candidates are skipped rather than erased.
- Approved/enabled retention semantics and approval evidence are immutable.
  The enabled flag remains a kill switch; changing a duration, cadence, or
  anchor requires a newly reviewed policy version.
- Local launch health is provider-aware. Pending, sending, and retryable failed
  rows may become overdue for every provider. A Woo row marked `sent` is counted
  as WordPress-accepted evidence and does not become overdue merely because no
  Resend-style delivery webhook exists. An accepted-to-delivered deadline is
  applied only to the legacy provider path with mapped delivery events.
- Staging must verify that provider-aware behavior after the configured queue
  age before production approval.
- Launch health also fails for an overdue actionable email queue or a worker
  whose email reconciliation has stopped succeeding. Mapped provider
  suppressions may also fail health when that integration exists.
- A new rate-limited recovery request can reset a transiently retry-exhausted
  recovery email. Where verified provider suppression exists, a bounced,
  complained, or provider-suppressed recovery email can reopen only after a
  DB-owner support action records audited re-consent or a false-positive
  correction and no active recipient suppression remains. Public recovery can
  never perform that clearance, and refund, erasure, billing-correction, or
  grant-rotation suppressions stay closed.

### Default-off safeguards

- The existing unauthenticated result prototype is hard-disabled outside local
  development even if its feature flag is accidentally enabled.
- Missing required server configuration fails closed.
- Private result routes are `noindex`, `nofollow`, and `no-store`.
- The live WordPress product remains blocked by its separate launch gate.

### Local evidence

- 39 paid-access security and state tests pass.
- TypeScript validation passes.
- The Next.js production build passes.
- The production dependency audit reports zero known vulnerabilities.
- WooCommerce static hook/health verification passes for the local `0.3.0`
  bridge candidate, including the signed access-email boundary. The authored
  PHP invariant, terms, billing-email confirmation, access-email policy, and
  syntax checks remain a staging prerequisite because this workstation has no
  PHP, WordPress CLI, or Docker runtime.
- 28 focused worker tests pass, and the hash-locked Python 3.11 dependency set
  installs and imports cleanly.
- Desktop and mobile browser smoke checks pass with no accessibility
  violations reported.

## Live WordPress/WooCommerce Setup

The following live WordPress checks currently pass:

- bridge plugin active at version `0.1.7`;
- fixed product ID `13` configured;
- expected SKU matches;
- product is published, simple, virtual, sold individually, in stock, and
  priced at `TWD 1,280`;
- WooCommerce store currency is `TWD`;
- guest checkout is enabled;
- checkout account creation is disabled;
- checkout and terms pages are published; and
- `/start-reading/` is installed as the fixed checkout entry route.

The same health response intentionally reports `ready: false` because
`launch_enabled: false`. This is the correct state until every remaining gate
below has passed.

ECPay is configured in live mode on WooCommerce, but its callback,
payment-state transition, compatibility matrix, and complete application
handoff have not yet been proven by a staging/no-charge test.

## Mandatory Staging Isolation

The current `apps/web/.vercel/project.json` points to production project
`valley-of-light-relationship-preview`
(`prj_p6gWIhCeP5qlDgW3hfG6MrK5gBiZ`). Staging commands must never run from that
link. Use an isolated worktree or clean source copy linked only to
`valley-of-light-app-staging`
(`prj_uvQHU9QJC0nT0HyDkVCiRjYwWq6J`), and assert the exact project name and ID
immediately before every environment or deployment command.
Use `apps/web/.env.staging.example` as the non-secret review checklist inside
that isolated copy. Never fill the repository template with credentials or
reuse it as a production environment file.

Vercel Cron is registered only on a project's Production deployment. The
stable staging build must therefore use the Production target of the isolated
staging project. That target remains staging because it has a different
project, hostname, environment, and credentials. A Preview deployment does not
prove the ten-minute reconciliation schedule.

Before any staging outbound traffic:

1. positively identify a separate staging Supabase URL and service-role key;
2. confirm the staging app uses only the staging WordPress/Woo REST host,
   access-email endpoint, worker URL, and app base URL;
3. confirm no staging component references `www.valeoflight.com`,
   `app.valeoflight.com`, the production Vercel project, the production
   Supabase project, production Woo keys, or production ECPay credentials;
4. never source `/Users/novaos/.openclaw/workspace/.env` into staging;
5. use unique staging webhook, access, WordPress-notification, worker, and Cron
   secrets; and
6. keep the production `vol_commerce_launch_enabled` option `no`.

The app and WordPress secret pairs are exact:

- app `VALEOFLIGHT_APP_BASE_URL` equals WordPress `VOL_APP_BASE_URL` and points
  to the matching app environment;
- app `VALLEY_ACCESS_SIGNING_SECRET` equals WordPress
  `VOL_ACCESS_SIGNING_SECRET`;
- app `VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET` equals WordPress
  `VOL_APP_TO_WORDPRESS_SIGNING_SECRET`;
- app `VALEOFLIGHT_WORDPRESS_EMAIL_API_URL` points to the matching WordPress
  `/wp-json/vale-of-light/v1/access-email` endpoint;
- the access and notification secrets differ from one another; and
- every staging value differs from production.

A managed WordPress clone is unsafe until real customers, orders, sessions,
logs, queued email/webhook jobs, and copied scheduled actions are removed or a
clean install is used. Keep outbound email, webhooks, ECPay, and copied Action
Scheduler work paused during sanitization. Remove live ECPay merchant
credentials, allowlist test recipients, and verify every callback/return target
before enabling sandbox traffic. Basic Auth or deployment protection must not
block the HMAC-protected Woo webhook, `/access-email`, Woo REST fetch, or Cron
paths.

## Blocking Gates Requiring User Input Or Approval

### Gate 0 - Approve Commerce, Privacy, And Service-Start Terms

**Status:** blocked.

The working Traditional Chinese copy is in
`docs/product/20-production-commerce-legal-copy-zh-tw.md`. It is a draft, not
legal advice and not a production terms version.

Required:

1. Obtain Taiwan legal/consumer-protection review for the intended personalized
   digital-service exception.
2. Provide the seller's complete legal identity, registration/tax details,
   address, effective support channel, invoice flow, and complaint process.
3. Approve a delivery promise measured from successful final intake submission,
   an unused-order/intake deadline, access-link behavior, result retention, and
   deletion/backup handling.
4. Approve the service-start boundary: the recommended policy allows full
   cancellation before the server successfully accepts the final intake and
   creates the generation job; only then does the separately accepted
   personalized-service exception begin. Do not publish a blanket
   “no refunds immediately after order placement” promise.
5. Implement two separate, unchecked final-submit confirmations—data accuracy
   and immediate personalized-service commencement—and retain both versions,
   content hashes, timestamps, and the immutable intake snapshot. The current
   one-checkbox UI and single generation-consent record are not sufficient.
6. Either implement and test an audited two-system billing-email correction
   workflow or disclose/use the pre-service cancel-and-reorder support path.
   The candidate intentionally blocks a Supabase-only correction.
7. Replace every `draft` terms identifier only after the matching wording is
   frozen and approved.

### Gate 1 - Create Staging Supabase And Approve Migration

**Status:** blocked.

Required:

1. The user confirmed on 2026-07-26 that the linked project named
   `Valley of light` is production. Do not use it for staging orders or preview
   deployments.
2. Create and positively identify a separate staging Supabase project and
   staging-only service-role credential.
3. Confirm each URL and credential against its intended environment; do not
   infer this from an existing variable name.
4. Approve the retention policy version, time windows and clock anchors for
   incomplete, delivered, and revoked readings; define legal holds, accountless
   deletion verification, logs/providers, and backup/PITR erasure replay.
5. Insert that approved policy in staging. The migration creates no enabled
   policy or duration by default.
6. Apply every repository migration to the new staging project in timestamp
   order. The paid migration depends on the earlier extension/runtime
   foundation; do not apply it alone to a blank project.
7. Run health/RPC/lease/idempotency/refund/recovery/concurrency checks,
   including the private audited content-erasure action, and complete one clean
   initial Woo reconciliation scan.
8. Apply the reviewed production migrations only after explicit user approval
   and staging evidence.

Required staging migration order:

```text
20260519152111_init_kb_runtime.sql
20260525095713_add_structured_kb_runtime.sql
20260525112318_add_question_blueprint_version.sql
20260726170000_add_paid_reading_delivery.sql
```

Do not point staging checkout tests at an unconfirmed production customer
database.

### Gate 2 - Configure Woo Email And Authenticated WordPress Transport

**Status:** blocked.

A successful Woo email trigger or `wp_mail()` return value is insufficient.
Required:

1. Install candidate bridge `0.3.0` on sanitized WordPress staging.
2. Enable WooCommerce's Customer Processing and Customer Completed emails.
3. Configure the matching staging app base URL, access-signing secret, and
   separate app-to-WordPress notification secret at both ends.
4. POST the authenticated commerce-health route and require
   `access_email_bridge: true` while all other product, terms, billing-email,
   checkout, and account checks pass. Keep the production launch gate OFF.
5. Choose an authenticated WordPress SMTP/API transport with retained logs and
   configure only a staging sender and test-recipient allowlist first.
6. Choose and approve the production `From`, `Reply-To`, and support addresses.
7. Publish and verify SPF and DKIM, then publish an approved DMARC policy and
   confirm alignment.
8. Disable click tracking and verify the received raw `href` is exactly the
   state-aware capability link issued by the app.
9. Exercise the signed `/access-email` boundary with valid invitation,
   result-ready, recovery, exact replay, invalid signature, stale timestamp,
   mutated body, unknown fields, unpaid/refunded order, wrong product, and grant
   conflict cases.
10. Send Processing, Completed, and recovery messages to test inboxes at
    multiple providers; verify acceptance, inbox/spam placement, provider logs,
    exact link, subject/heading, and support resend/correction behavior.
11. Verify paid-access health after the queue-age threshold: Woo-accepted
    `sent` rows remain healthy without a delivery webhook, while actionable
    pending/sending/failed rows become overdue.
12. If the chosen transport exposes stable message IDs and signed delivery,
    bounce, complaint, or suppression events, map and replay those events before
    enabling provider-level claims. Otherwise omit those claims and use
    provider logs plus the approved support process.

No live webhook should create paid entitlements until the invitation email can
be delivered reliably.

### Gate 3 - Choose And Deploy The Result Worker

**Status:** blocked.

Required user decisions:

- worker host/provider and budget;
- staging and production separation;
- retry limits and exponential backoff;
- terminal `needs_review` behavior;
- alert destination and support owner; and
- reconciliation schedule for stuck fulfillment.

Required technical evidence:

1. Compile and validate a fresh published-only KB in the private build.
2. Generate and publish the matching source archive under the selected AGPL
   path. The worker fails closed unless the immutable public URL and exact
   archive SHA-256 are configured.
3. Deploy the image to the chosen worker host.
4. Configure a strong, environment-specific worker signing secret.
5. Configure the app's worker URL.
6. Demonstrate signed lease claims and retries without duplicate results.
7. Demonstrate terminal failure handling, outbox reconciliation, and manual
   recovery.
8. Confirm the startup gate rejects draft/non-published KB artifacts.

Without this gate, intake submission can lock successfully but the customer
will remain on the processing page indefinitely.

### Gate 4 - Deploy Receiver And Create WooCommerce Webhook

**Status:** blocked.

The webhook must be created only after a staging receiver is deployed and
healthy. Required:

1. Generate a strong webhook secret and place it in both WooCommerce and the
   matching app environment.
2. Confirm that the WooCommerce REST credentials are read-only where practical
   and can retrieve protected order metadata using `context=edit`.
3. Link an isolated source copy to the exact staging Vercel project, configure
   staging-only variables, deploy its Production target, and verify
   `/api/health/paid-reading` before allowing WordPress traffic.
4. Create the required staging `order.updated` webhook only after the receiver
   is healthy. If `order.created` is also configured intentionally, verify it
   cannot create access for an unpaid order.
5. Point staging/no-charge tests only at that receiver. Create the production
   paid-order/update webhook at
   `https://app.valeoflight.com/api/integrations/woocommerce/webhook` only
   after the production app deployment is explicitly approved.
6. Confirm delivery ID, topic, signature, retry, and disable-after-failure
   behavior.
7. Confirm that an unpaid, failed, cancelled, wrong-product, invalid-terms, or
   wrong-total order never receives access.
8. Verify that a failed/cancelled ECPay attempt can later become paid on the
   same order, while a full refund/reversal remains terminal and revokes access.
   Confirm the legally reviewed no-voluntary-refund wording and support process
   for an already-delivered reading.
9. Verify that the receiver accepts every terms version still eligible for an
   ECPay callback or order-payment retry, and that WordPress never replaces an
   order's original terms evidence during a rotation.
10. Drop or disable one webhook during staging, let reconciliation recover the
    paid order, and prove a later delayed webhook creates no duplicate
    entitlement or email.
11. Verify paid reading orders remain `processing` until a durable result. The
    app then calls the signed WordPress `result_ready` action, which is the only
    authorized transition to `completed` and triggers the Completed email. The
    Woo REST credential remains read-only.

The current absence of a verified shared webhook secret is an intentional
fail-closed condition.

### Gate 5 - ECPay Staging Or No-Charge End-To-End Test

**Status:** blocked.

Do not use a real customer or silently create a live charge for verification.
Use ECPay's supported staging/sandbox mode or an approved no-charge test method.

First run the payment-neutral integration flow through a normal guest storefront
checkout with a staging-only offline gateway. Do not create the order in Admin.
If Woo sends a Customer On-Hold email for that gateway, either disable it for
the synthetic test or verify that it contains payment instructions only and no
reading link. Then set the checkout-created order explicitly to `processing`
and confirm Woo recorded `date_paid`. This proves the Woo/app/worker/email
journey but is not ECPay evidence.

Run a separate ECPay sandbox matrix for every method that will remain enabled.
Credit card, installment, ATM, CVS, barcode, and iPASS are distinct cases.
Launch with only the smallest fully tested set and disable every untested
method. Async methods also require payment-instruction, `on-hold`, expiry,
late-callback, and retry cases.

The combined tests must prove:

1. landing CTA opens the fixed native WooCommerce guest checkout;
2. no birth or relationship data is requested before payment;
3. checkout requires an exact confirmation of the delivery email and stores
   the expected terms version, timestamp, acceptance source, and reading
   product evidence;
4. turning the launch gate off or drifting the fixed product configuration
   blocks an existing order-payment retry before ECPay receives it;
5. a terms rotation keeps the original order version and timestamp immutable,
   and both receiver and WordPress accept every still-open payment cohort;
6. the ECPay return page alone creates no access;
7. the verified ECPay server callback records the gateway transaction ID,
   `date_paid`, and moves WooCommerce into `processing`;
8. duplicate, delayed, and out-of-order ECPay callbacks remain safe;
9. a failed/cancelled ECPay attempt can later be paid through the same eligible
   order-pay flow without a second entitlement;
10. the signed WooCommerce webhook reaches the isolated deployed app exactly as
    expected;
11. a missed webhook is recovered by authenticated reconciliation and a later
    webhook replay creates no duplicate;
12. one private entitlement and one access grant are created;
13. the app's signed WordPress call triggers one Woo Customer Processing email
    only after the grant exists;
14. the Processing email reaches the verified billing email through the
    authenticated WordPress mail transport and its raw link is unchanged;
15. the link opens the intake form;
16. final submission permanently locks the data;
17. worker retry behavior does not create a second result;
18. the durable result triggers the signed WordPress `result_ready` action,
    order completion, and one Woo Customer Completed email;
19. the Completed email reuses the exact same link;
20. revisiting that link opens the stored result;
21. duplicate webhook delivery, WordPress notification, and repeated submission
    remain idempotent;
22. recovery does not revoke a still-valid link, while an expired link rotates
    only through the billing email without disclosing whether an order exists;
23. a full refund, payment reversal, or chargeback remains terminal and no
    delayed webhook can recreate access;
24. partial refunds are unavailable/unsupported for V1 and are not offered by
    staff or an enabled gateway flow;
25. the audited content-erasure action clears reading payloads in staging
    without deleting commerce or consent evidence;
26. WordPress transport rejection, retry exhaustion, provider logs, inbox/spam,
    and support resend/correction paths work; and
27. where provider events are integrated, signed delivery, bounce, complaint,
    suppression, duplicate, and out-of-order events update the correct
    generation and enforce the approved recovery policy.

Record order ID, webhook delivery ID, WordPress notification receipt, actual
mail-provider message ID only when available, reading ID, fulfillment status,
and timestamps as launch evidence without recording raw access tokens or
personal birth data.

### Gate 6 - Explicit Deploy And Enable Approval

**Status:** blocked.

Two separate approvals are required:

1. approval to deploy the reviewed paid-access app and environment variables to
   the production Vercel project; and
2. final approval to change `vol_commerce_launch_enabled` from `no` to `yes`.

The launch switch is the last step, not a testing shortcut. Enable it only
after Gates 1-5 pass and the production health check is green.

## Required Execution Order

```text
keep PRODUCTION WordPress launch gate OFF
  -> confirm staging and production Supabase projects
  -> sanitize WordPress staging with all outbound traffic paused
  -> apply every repository migration in order and validate staging
  -> link an isolated source copy to the exact staging Vercel project
  -> configure and deploy the staging project's Production target
  -> configure the signed Woo email bridge and authenticated WP mail transport
  -> deploy and validate worker with retry/recovery
  -> verify app and WordPress health with staging launch gate OFF
  -> create and verify the staging WooCommerce webhook
  -> enable the STAGING WordPress launch gate only
  -> complete payment-neutral guest-checkout and missed-webhook reconciliation tests
  -> complete every enabled ECPay sandbox method
  -> turn the STAGING launch gate back OFF
  -> review evidence and receive production deployment approval
  -> apply approved production migration and secrets
  -> correct the production Vercel Next.js configuration
  -> deploy paid-access app, bridge, mail transport, and worker to production
  -> create/verify production WooCommerce webhook
  -> run production-safe health checks
  -> receive final enable approval
  -> turn PRODUCTION WordPress launch gate ON
```

Changing the order requires an explicit risk review. In particular, do not
enable purchasing before email and worker delivery are proven.

## Final Go-Live Checklist

- [x] Production Supabase project positively identified
- [ ] Taiwan commerce/refund/privacy copy reviewed and seller disclosures filled
- [ ] Two separate final-submit confirmations are stored with versions, hashes,
      timestamps, and the immutable intake snapshot
- [ ] Billing-email correction or pre-service cancel/reorder support flow approved
- [ ] Separate staging Supabase project created and positively identified
- [ ] Every repository migration applied in order and validated on staging
- [ ] Retention policy durations, anchors, holds, provider/log and backup
      handling approved; matching policy enabled
- [ ] Supabase paid-reading health check passes
- [ ] Email health is provider-aware; Woo-accepted rows do not require a
      nonexistent delivery webhook
- [ ] `CRON_SECRET` configured and the Woo reconciliation cursor has completed
      a clean, recent scan
- [ ] Isolated staging Vercel project ID verified before variables and deploy
- [ ] `apps/web/.env.staging.example` reviewed with only staging targets
- [ ] Staging project's Production target deployed and Cron invocation verified
- [ ] Production Vercel project reviewed/corrected for the Next.js app
- [ ] Candidate WordPress bridge `0.3.0` and `/access-email` boundary validated
- [ ] Woo Customer Processing and Customer Completed emails enabled
- [ ] Authenticated WordPress SMTP/API transport and provider logs validated
- [ ] SPF, DKIM, and DMARC pass
- [ ] Click tracking disabled and received capability `href` unchanged
- [ ] Production sender/support addresses approved
- [ ] Worker hosting and budget approved
- [x] Immanuel / Swiss Ephemeris AGPL production path approved
- [ ] Matching AGPL source archive publicly released and checksum verified
- [ ] Worker retry, terminal failure, and reconciliation tested
- [ ] Production app environment reviewed without exposing secrets
- [ ] Paid-access app deployment explicitly approved
- [ ] WooCommerce webhook secret generated and installed at both ends
- [ ] WooCommerce webhook delivery and retry verified
- [ ] Missed-webhook reconciliation and delayed-webhook replay pass
- [ ] Payment-neutral guest storefront checkout passes; On-Hold email is
      disabled or verified to contain no reading link
- [ ] Every ECPay method left enabled passes its sandbox matrix; all others are
      disabled
- [ ] Duplicate, invalid-signature, unpaid, and wrong-product cases pass
- [ ] Invalid/stale/replayed app-to-WordPress notification cases pass
- [ ] Same-link intake lock and result revisit pass
- [ ] WordPress bridge PHP unit and syntax checks pass on staging PHP 8.1+
- [ ] Checkout delivery-email confirmation passes in classic and Blocks flows
- [ ] Expired-link email recovery passes without order enumeration
- [ ] Valid-link recovery resends without revocation
- [ ] Transport rejection, provider logs, inbox/spam, and support resend pass
- [ ] Bounce/complaint suppression passes if provider events are integrated;
      otherwise no unsupported delivery claim remains
- [ ] No-voluntary-refund wording is legally reviewed; full reversal/revocation
      and support behavior are approved
- [ ] Failed/cancelled retry and terminal-refund matrix passes with ECPay
- [ ] Partial refunds are disabled/unsupported for V1
- [ ] Private content-erasure action and restored-backup erasure procedure pass
- [ ] Customer-facing delivery-time promise and support owner approved
- [ ] Signed result-ready action is the only path to Woo `completed`
- [ ] Monitoring and alert ownership assigned
- [ ] Final go-live approval recorded
- [ ] `vol_commerce_launch_enabled` changed to `yes` only after all prior items

## Rollback

If a launch check fails after enablement:

1. immediately set `vol_commerce_launch_enabled` back to `no`;
2. preserve WooCommerce orders, webhook evidence, and private reading records;
3. disable the failing webhook only if it is causing repeated unsafe behavior;
4. roll back the Vercel app or worker to the last verified deployment;
5. do not destructively roll back the database migration;
6. reconcile every order accepted during the affected window; and
7. re-enable only after the failing gate is tested again and approved.

The launch gate controls new purchases. It must not be used to hide or abandon
existing paid customer fulfillment.

The WordPress payment guard deliberately also applies the launch gate to a
fresh `order-pay` gateway handoff. It cannot recall an ECPay payment that was
already started. For that reason, a terms-version rollout must begin with a
receiver overlap window and end only after all older payment and callback
windows have drained; changing the receiver's expected version alone is not a
safe rollback.
