# 15 - Staging Commerce End-to-End Runbook

> Status: infrastructure prerequisites missing
> Updated: 2026-07-26
> Production launch gate: **OFF**

## Purpose

Prove the complete payment-first, accountless reading journey without using a
real customer, production Supabase data, or a live ECPay charge.

The confirmed Supabase project named `Valley of light` is production. It must
not be used by WordPress staging, Vercel staging, a staging worker, or test
orders.

## Required Isolated Staging Surfaces

| Surface | Required staging target | Current state |
| --- | --- | --- |
| WordPress/WooCommerce | managed staging clone of `www.valeoflight.com` | missing |
| Supabase | new project containing schema only, no production customer clone | missing |
| Result app | `valley-of-light-app-staging`, Next.js app | project created and preset corrected; environment and deployment missing |
| Result app hostname | isolated default Vercel hostname first; optional approved custom staging host | default hostname exists; custom host missing |
| Reading worker | separate staging container and signing secret | Render blueprint prepared; service/account/budget missing |
| Email transport | authenticated staging sender with delivery logs | missing |
| ECPay | sandbox credentials or documented approved no-charge method | missing |

Do not repurpose the production-linked Vercel project or production Supabase
project for preview testing.

Before any outbound staging request, record and compare the resolved staging
targets. Abort if any app, WordPress, worker, webhook, Cron, or ECPay setting
references:

- production Supabase project `Valley of light` or its URL/key;
- production Vercel project `valley-of-light-relationship-preview`;
- `app.valeoflight.com` as the result-app target;
- `www.valeoflight.com` as the Woo REST or access-email target;
- production WooCommerce REST keys, webhook secrets, WordPress notification
  secrets, worker secrets, or Cron secrets; or
- live ECPay merchant credentials or a live callback/return host.

## Phase A - Create The Staging Foundation

1. Create a separate Supabase project such as `Valley of Light Staging`.
2. Apply every repository migration in timestamp order. A new project must not
   start with only the paid-reading migration because it depends on the earlier
   extensions and runtime foundation:

   ```text
   20260519152111_init_kb_runtime.sql
   20260525095713_add_structured_kb_runtime.sql
   20260525112318_add_question_blueprint_version.sql
   20260726170000_add_paid_reading_delivery.sql
   ```

3. Insert a staging-only retention policy version and keep it clearly separate
   from the future production policy.
4. Run schema, RPC, lease, idempotency, refund, recovery, erasure, and
   concurrency checks against staging.
5. Use the separate Vercel project
   `valley-of-light-app-staging`
   (`prj_uvQHU9QJC0nT0HyDkVCiRjYwWq6J`), whose framework preset is Next.js.
6. Use `apps/web/.env.staging.example` as the review checklist inside the
   isolated source copy. Do not rename or fill the repository template with
   real secrets; load its completed values into the staging Vercel environment.
7. Configure only staging Supabase, WooCommerce, email, Cron, access-signing,
   worker-signing, and WordPress-notification values. Verify these exact pairs:

   - app `VALEOFLIGHT_APP_BASE_URL` equals WordPress `VOL_APP_BASE_URL` and
     resolves to the isolated staging app;
   - app `VALLEY_ACCESS_SIGNING_SECRET` equals WordPress
     `VOL_ACCESS_SIGNING_SECRET`;
   - app `VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET` equals WordPress
     `VOL_APP_TO_WORDPRESS_SIGNING_SECRET`;
   - app `VALEOFLIGHT_WORDPRESS_EMAIL_API_URL` resolves to the staging
     `/wp-json/vale-of-light/v1/access-email` endpoint;
   - the access and notification secrets are different; and
   - every staging secret is different from production.
8. Deploy the stable staging build to the staging project's **Production**
   environment. This does not mean Valley production: it is the production
   environment of the isolated staging project, which is required for its
   stable hostname and Vercel Cron.
9. Use the isolated default hostname or attach an approved custom staging
   hostname, and keep every private route `noindex, nofollow`.
10. Create or clone managed WordPress staging with outbound email, webhooks,
    ECPay, and copied scheduled actions initially disabled.
11. Prefer a clean WordPress install. If using a production clone, remove real
    customers, orders, sessions, logs, queued email/webhook jobs, and copied
    Action Scheduler work before outbound traffic is allowed. Use a
    test-recipient allowlist.
12. Remove all cloned live ECPay merchant credentials. Install sandbox
    credentials only after every callback and return host is verified as
    staging.
13. Install candidate commerce bridge `0.3.0` on staging only. Configure
    `VOL_APP_BASE_URL` to the staging app and both matching staging secrets.
14. Enable WooCommerce's Customer Processing and Customer Completed emails.
    Configure an authenticated staging SMTP/API transport with provider logs,
    SPF/DKIM/DMARC alignment, and click tracking disabled.
15. Deploy the separately configured worker only after the commercial
    Swiss Ephemeris AGPL path and matching public source release are recorded.
16. Verify the app paid-reading health route and authenticated WordPress
    commerce-health route while the staging launch gate is still OFF. Require
    product, price, terms, billing-email confirmation, guest/account, and
    `access_email_bridge` checks to pass.
17. Only after the receiver is deployed and healthy, create the required
    staging `order.updated` webhook with the staging-only secret. If
    `order.created` is also enabled intentionally, verify it cannot create an
    unpaid entitlement.
18. Run one authenticated reconciliation invocation and confirm a clean recent
    high-water mark. Vercel does not retry a failed Cron invocation.
19. If staging uses Basic Auth or deployment protection, provide machine access
    for the HMAC-protected Woo webhook, WordPress `/access-email`, Woo REST, and
    Cron paths without making private customer routes public.

Every environment must use a unique webhook secret, access-signing secret,
worker-signing secret, cron secret, and Email/WordPress notification secret.

### Vercel target guard

`apps/web/.vercel/project.json` intentionally remains linked to the existing
result project `valley-of-light-relationship-preview`, which owns
`app.valeoflight.com`. An ordinary `vercel env` or `vercel deploy` command from
that directory can therefore mutate or deploy the production project.

For staging:

1. create a clean temporary source copy or isolated worktree;
2. remove no repository files from the user's working tree;
3. link only that isolated copy to `valley-of-light-app-staging`;
4. verify the exact project name and project ID immediately before every
   environment or deployment command;
5. never source `/Users/novaos/.openclaw/workspace/.env`, because it contains
   production WordPress and Supabase values;
6. load only reviewed staging secrets; and
7. use `--prod` only after verifying the isolated staging project ID.

Abort immediately if a command resolves to
`valley-of-light-relationship-preview`,
`prj_p6gWIhCeP5qlDgW3hfG6MrK5gBiZ`, or production Supabase.

## Phase B - WordPress Payment-Neutral Test

A generic WooCommerce “send test Email” cannot prove a customer access link
because it has no verified paid order or reading grant.

Do not create the test order directly in WordPress Admin. An admin-created order
does not pass through the normal checkout and therefore lacks the immutable
`_vol_*` terms and billing-Email confirmation evidence. The application is
designed to reject it.

Use this flow:

1. On WordPress staging, temporarily enable one staging-only offline gateway
   such as Check Payments or Direct Bank Transfer.
2. Keep all live ECPay methods disabled in this phase.
3. Decide how to handle WooCommerce's Customer On-Hold email for the offline
   gateway: disable it for this synthetic test, or keep it enabled and verify it
   contains only order/payment instructions and never the secure reading link.
4. Verify the staging WordPress URL, product, checkout, terms, email transport,
   webhook target, and authenticated commerce-health response. Require
   `access_email_bridge: true`; `launch_enabled` should still be `false`.
5. Enable `vol_commerce_launch_enabled` on **WordPress staging only**.
6. Open `/start-reading/` as a guest and complete the normal storefront
   checkout.
7. Verify the fixed product, quantity, `TWD 1,280`, legal acknowledgement, and
   exact-match Email confirmation.
8. If an On-Hold email is enabled, inspect its received HTML now and prove no
   capability link exists.
9. In WordPress Admin, change the checkout-created order explicitly to
   `processing` and confirm WooCommerce records `date_paid`. Record this as a
   synthetic paid-state simulation, not proof of a gateway.
10. Verify the signed webhook creates exactly one commerce mirror, reading,
   active grant, and post-payment Email job.
11. Verify the automatic Woo status event did not send a Customer Processing
    email before the grant existed.
12. Verify the app's signed WordPress request triggers exactly one Customer
    Processing email after the grant exists and contains
    `開始填寫解讀資料`.
13. Confirm the WordPress transport accepted the email, inspect the provider
    log and test inbox, and verify the received raw `href` is exactly the
    state-aware link.
14. Open the link and complete the intake.
15. Verify final submission requires two separate unchecked confirmations for
   data accuracy and immediate personalized-service commencement. Confirm both
   approved versions, content hashes, and timestamps are stored against the
   immutable intake; service starts only after the server successfully locks
   that intake and creates one fulfillment.
16. Verify the worker stores one result despite duplicate claim/callback
    attempts.
17. Verify the app tells WordPress the result is durable, WordPress changes
    `processing` to `completed`, and the Customer Completed Order Email uses
    the same link with the result-ready subject/heading.
18. Compare the Processing and Completed email `href` values exactly. They must
    be the same link; the Completed email must not create a second grant.
19. Open the same link again and confirm it shows the stored result rather than
    reopening the form.
20. Exercise recovery, email resend, expired-link rotation, full-refund
    revocation, delayed-webhook replay, and duplicate notification behavior.
21. Turn `vol_commerce_launch_enabled` back off on staging when the test window
    ends or immediately if any prerequisite fails.

This phase proves the WordPress, app, Supabase, worker, email, and same-link
journey without a charge. It does not prove the ECPay boundary.

## Phase C - Reconciliation And Signed-Bridge Failure Tests

Use a new checkout-created staging order:

1. pause or deliberately drop the Woo webhook;
2. move the offline-gateway order to `processing` and confirm `date_paid`;
3. invoke the authenticated Woo reconciliation route;
4. verify reconciliation creates exactly one entitlement, grant, and
   Processing-email notification;
5. restore and replay the delayed webhook; and
6. verify the replay creates no second entitlement, grant, notification, intake,
   or result.

Exercise the app-to-WordPress `/access-email` boundary with:

- missing and invalid signatures;
- stale and future timestamps;
- one-byte body mutation after signing;
- unknown fields and unsupported message kinds;
- wrong product, unpaid, cancelled, fully refunded, or missing-`date_paid`
  orders;
- conflicting grant references;
- an exact idempotency replay; and
- duplicate result-ready and recovery calls.

Only the exact authorized request may send. An exact replay must return the same
WordPress notification receipt without sending again. After the configured
email queue age has elapsed, verify paid-access health remains green for a
Woo-accepted message without a provider delivery webhook. If a real provider
event integration exists, separately test signed duplicate, delayed,
out-of-order, unknown-message, bounce, complaint, and suppression events.

## Phase D - Checkout Compatibility

The live WordPress inventory includes Checkout Field Editor. Test both classic
checkout and Checkout Blocks, including:

- the second Email field appears once and in the correct position;
- the field cannot be bypassed client-side or through Store API requests;
- capitalization and spelling follow the approved exact-match behavior;
- field metadata is not exposed in customer Emails;
- terms and Email evidence are stamped exactly once and remain immutable;
- the fixed price, tax, coupon, fee, shipping, variation, extra-product, and
  quantity guards all fail closed;
- an order-pay retry is blocked when the launch gate or terms cohort is
  invalid; and
- the ECPay plugin uses the normal WooCommerce payment lifecycle required by
  the bridge.

Run the bridge's PHP tests and syntax checks on the staging PHP version before
any ECPay test.

## Phase E - ECPay Boundary Test

Use ECPay's supported sandbox configuration or another test method explicitly
approved by the owner. Remove cloned live merchant credentials before enabling
sandbox, and verify the return/callback URLs resolve only to staging.

Create one matrix row for each ECPay method that will remain enabled:

| Method | Additional required cases |
| --- | --- |
| Credit card | success, decline, cancel/abandon, retry, duplicate callback |
| Installment | each enabled term, decline, retry, transaction metadata |
| ATM | instructions, `on-hold`, payment, expiry, late callback |
| CVS | instructions, `on-hold`, payment, expiry, late callback |
| Barcode | instructions, `on-hold`, payment, expiry, late callback |
| iPASS | redirect/app return, cancel, success, duplicate callback |

Launch with only the smallest fully tested set; credit card is the recommended
first method. Disable every untested method.

A WordPress offline gateway cannot prove:

- ECPay redirect and return behavior;
- signed server callback verification;
- gateway transaction ID recording;
- exact paid/failed/cancelled status transitions;
- failed or cancelled payment followed by a successful retry;
- duplicate, delayed, and out-of-order ECPay callbacks;
- ECPay/WooCommerce hook compatibility; or
- full-refund, payment-reversal, or chargeback behavior exposed by the installed
  module.

For each synchronous method, prove the verified server callback—not the browser
return—records the gateway transaction ID, `date_paid`, and `processing`.
For ATM, CVS, and barcode, prove the pre-payment On-Hold/instruction email never
contains the reading link and access appears only after the paid callback.

The draft commercial policy allows full cancellation until the server accepts
the final intake and atomically creates the generation job. After the customer
separately accepts immediate personalized-service commencement, voluntary
change-of-mind refunds stop to the extent Taiwan law permits; this boundary
still requires legal review. Technical full refunds, reversals, and chargebacks
must still revoke access terminally. Partial refunds are unsupported for V1:
do not offer them in staff procedures or leave an enabled gateway flow that can
create one.

Repeat the complete journey after a sandbox payment and retain only redacted
evidence: order ID, gateway transaction reference, webhook delivery ID,
WordPress notification receipt, actual mail-provider message ID only when
available, reading ID, state transitions, and timestamps. Never record the raw
access link or personal birth/relationship data in the test report.

## Pass Criteria

- [ ] Exact Vercel project ID was asserted before every staging env/deploy action
- [ ] No staging component connects to production Vercel, Supabase, WordPress,
      Woo credentials, ECPay credentials, or secrets
- [ ] Production `vol_commerce_launch_enabled` remains `no`
- [ ] No staging test creates a live ECPay charge
- [ ] Sanitized WordPress staging contains no real-customer outbound work
- [ ] App and WordPress health pass before the staging gate is temporarily enabled
- [ ] Woo Processing and Completed emails are enabled; authenticated mail
      transport, SPF/DKIM/DMARC, provider logs, and click-tracking controls pass
- [ ] Checkout-created test order contains all immutable consent and Email proof
- [ ] Any On-Hold/instruction email contains no reading link
- [ ] One paid order creates exactly one entitlement and one active reading
- [ ] A missed webhook is recovered by reconciliation and delayed replay stays
      idempotent
- [ ] Woo Processing Email is delayed until the secure grant exists
- [ ] Woo Completed Email is sent only after the stored result is durable
- [ ] Both received Emails use the exact same unchanged state-aware `href`
- [ ] Submitted data cannot be edited or replaced through the customer flow
- [ ] Data-accuracy and service-start confirmations are separately displayed,
      accepted, versioned, hashed, and stored
- [ ] Duplicate webhooks, Emails, submissions, queue claims, and callbacks stay idempotent
- [ ] Failed/cancelled retry succeeds when later paid; refund remains terminal
- [ ] Recovery never reveals whether an order exists
- [ ] Signed app-to-WordPress negative/replay matrix passes
- [ ] Woo-accepted email health remains green without a nonexistent delivery
      webhook
- [ ] Transport rejection, provider logs, inbox/spam, and corrected-Email support
      paths are tested
- [ ] Bounce/complaint suppression is tested only if verified provider events
      are integrated; otherwise no unsupported delivery claim remains
- [ ] Every ECPay method left enabled passes its sandbox matrix; all others are
      disabled
- [ ] Full refund/reversal stays terminal and partial refunds are unsupported
      and disabled for V1
- [ ] Rollback procedures are rehearsed
- [ ] Staging `vol_commerce_launch_enabled` is returned to `no`

Only after all criteria pass should the owner be asked separately to approve
the production migration/deployment. Enabling the production WordPress launch
gate requires an additional final approval.
