# Vale of Light Commerce Bridge

Production WordPress/WooCommerce bridge for the fixed V1 relationship reading.

## Public route

`/start-reading/` first redirects to a stable query-bearing version of the
same route so Kinsta never serves a cached cart mutation. The dynamic request
then selects the server-owned reading product, forces quantity one, clears any
stale cart state, and redirects to the native WooCommerce checkout. The route
never accepts a product id, price, or customer email from the browser.

The production Kinsta configuration also includes `/start-reading/` as a
single custom autopurge path. That keeps the cached first-hop redirect current;
the query-bearing cart mutation must still remain `BYPASS` and `no-store`.

## Order handoff

The plugin records the checkout terms version and timestamp only after the
classic checkout has passed its required terms checkbox or the Checkout Block
has reached WooCommerce's validated `order_processed` boundary. That original
evidence is immutable: a reused pending order or order-payment retry is never
silently restamped. The thank-you page then shows a masked-email instruction.
Verified paid-order access is still created only by the signed application
webhook.

## WooCommerce access emails

Version `0.3.0` uses WooCommerce's built-in customer emails without allowing
their normal payment event to race ahead of entitlement creation:

- the reading product's automatic Processing and Completed customer emails are
  suppressed, including deferred Woo email jobs;
- after the app has revalidated payment and created the Supabase entitlement,
  it calls the signed `POST /wp-json/vale-of-light/v1/access-email` endpoint;
- the endpoint accepts only an order ID, grant UUID, expiry, reviewed message
  kind, template version, and idempotency key;
- WordPress stores only the non-secret grant UUID and expiry, then reconstructs
  the exact `/r#...` token in memory while Woo renders the email;
- `intake_invitation` triggers Woo's Customer Processing Order email;
- `result_ready` is the only authorized transition from `processing` to
  `completed` and triggers Woo's Customer Completed Order email; and
- `access_recovery` or the protected admin order action resends the same current
  link without creating a new reading.

The route checks a five-minute timestamp window and an HMAC over the exact raw
body, rejects unknown fields and unpaid/ineligible orders, and keeps a
non-autoloaded idempotency receipt. A repeated accepted request returns the
same synthetic Woo receipt instead of sending again. Link credentials are
never stored in order metadata, order notes, WordPress options, or server logs.

Configure these values above the WordPress `stop editing` line, preferably from
host-managed secrets rather than literal source-controlled values:

```php
define('VOL_APP_BASE_URL', 'https://app.valeoflight.com');
define('VOL_ACCESS_SIGNING_SECRET', getenv('VOL_ACCESS_SIGNING_SECRET') ?: '');
define(
    'VOL_APP_TO_WORDPRESS_SIGNING_SECRET',
    getenv('VOL_APP_TO_WORDPRESS_SIGNING_SECRET') ?: ''
);
define(
    'VOL_EMAIL_TRANSPORT_VERIFIED',
    filter_var(
        getenv('VOL_EMAIL_TRANSPORT_VERIFIED'),
        FILTER_VALIDATE_BOOLEAN
    )
);
```

`VOL_ACCESS_SIGNING_SECRET` must exactly match the app's
`VALLEY_ACCESS_SIGNING_SECRET`. The notification secret must exactly match
`VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET` and must be different from the
access secret. Both secrets require at least 32 characters. Missing, weak,
identical, or non-HTTPS configuration makes launch health report
`access_email_bridge: false` and keeps checkout closed.

Woo's default email feature is a template/trigger system, not an inbox delivery
service. Production still requires an authenticated SMTP/API transport with a
domain sender, SPF/DKIM/DMARC, logs, and resend support. A successful
`wp_mail()` call means the transport accepted the message; it does not prove
delivery to the buyer's inbox. Keep `VOL_EMAIL_TRANSPORT_VERIFIED` false until
an end-to-end order email has reached a real inbox, appears in the
authenticated provider's logs, and the support resend procedure has been
tested. This explicit launch attestation is reported separately as
`transactional_email_transport_verified`; checkout remains closed while it is
false.

Woo acceptance receipts use synthetic `woo.*` identifiers solely for
idempotency. They are not SMTP provider message IDs and cannot produce
delivered, bounce, or complaint events. If a PHP process stops after the mail
transport accepts a message but before the idempotency receipt is finalized,
the bridge deliberately blocks automatic retries for that indeterminate
request. An operator must inspect the SMTP log and use the reading-order resend
action if needed; this avoids an automatic duplicate email.

Each order also stores the reading product ID and fixed reading SKU at the
validated checkout boundary. Later access/result/recovery emails validate that
immutable pair against the order line and fixed price/currency contract, so a
future product-ID rotation for new sales does not strand an already-paid
customer.

## Payment Email confirmation

The reading checkout asks the buyer to enter the payment Email twice and says
clearly that the post-payment secure data-entry link will be sent there. The
second value is required only when the configured reading product is in the
cart:

- classic/shortcode checkout adds a required Email field immediately after the
  billing Email and validates both server-side;
- Checkout Blocks registers a native `contact` additional field, conditionally
  requires it for the reading product, and declares an exact-match rule against
  the Store API billing Email; and
- the final classic-order and Store API `order_processed` boundaries compare
  server-owned values again before any payment handoff.

The comparison is exact after WordPress Email sanitization and whitespace
trimming. Letter case is not silently changed. This deliberately catches a
confirmation whose capitalization differs from the billing Email as well as
ordinary spelling mistakes.

The bridge never treats a browser-side success flag as proof. It stores a
SHA-256 HMAC of the normalized billing Email, the server confirmation time, and
the accepted checkout path. The HMAC key is derived from the WordPress
authentication salts. The second plaintext value used by Checkout Blocks is
removed from the order after the proof is created and is hidden from order
confirmation views and WooCommerce emails.

Every initial gateway handoff and order-payment retry verifies that proof
against the order's current billing Email. Editing the billing Email after
confirmation, rotating the WordPress authentication salts while an unpaid
order remains open, partial/tampered metadata, or an unsupported checkout path
therefore fails closed. Support must cancel and recreate that unpaid order so
the buyer can explicitly confirm the destination again.

Orders created by a bridge version older than `0.2.2` have no Email
confirmation proof and cannot start a new payment attempt. Do not backfill the
proof. Already-paid orders do not need a new gateway handoff and remain
available to the signed paid-order receiver.

An already-paid reading's billing Email must not be edited in WooCommerce or
Supabase as a one-sided support action. The access-email endpoint revalidates
the original confirmation digest against Woo's current billing Email, and the
app independently checks that Woo and Supabase still agree before it claims a
delivery. A future correction workflow must update and verify Woo first, renew
the WordPress confirmation proof through an audited staff action, then update
Supabase and rotate the access grant. That cross-system workflow is not
implemented in version `0.3.0`.

### Compatibility assumptions

- WordPress 6.5+, PHP 8.1+, and WooCommerce 8.9+ are required. WooCommerce 8.9
  is the minimum because that is the first supported release of
  `woocommerce_register_additional_checkout_field`.
- Checkout Blocks must use the standard WooCommerce Store API lifecycle and
  fire `woocommerce_store_api_checkout_order_processed` before the gateway.
  Classic checkout must fire `woocommerce_after_checkout_validation`,
  `woocommerce_checkout_create_order`, and
  `woocommerce_checkout_order_processed`.
- The payment plugin, including 綠界, must enter payment through WooCommerce's
  normal checkout or order-pay lifecycle. A gateway or custom checkout that
  bypasses those hooks is unsupported and must not be enabled for this product.
- WordPress authentication keys and salts must be unique, secret, and stable
  for the lifetime of any unpaid order.

Launch health reports `billing_email_confirmation: false` and keeps the reading
non-purchasable if the native Blocks field is unavailable/unregistered, the
server hooks are missing, or the WordPress authentication salts are unsafe.

## Configuration

The configured product id is stored as the non-autoloaded WordPress option
`vol_reading_product_id`. New activations start with product id `0` and fail
closed until the option is explicitly configured.

The plugin fails closed unless that product also uses SKU
`vol-astrology-synastry`, is a published virtual simple product sold
individually for `TWD 1,280`, and remains purchasable and in stock. Existing
sites keep their explicitly saved option.

The product policy forces the configured product to remain non-taxable and
clears sale pricing whenever WooCommerce saves it. Coupons are disabled for a
cart containing the reading, and the product is rejected by both product-level
and cart-level coupon validation. V1 launch health also requires the global
WooCommerce coupon setting to remain disabled; the product/cart guards are a
second fail-closed layer.

Immediately before payment, the bridge revalidates the classic checkout, the
Checkout Block Store API order, and an existing order-payment retry. The only
accepted commercial snapshot is one configured simple product, quantity one,
currency `TWD`, subtotal and final total exactly `1,280`, with no variation,
coupon, discount, fee, shipping, or tax line. Any drift stops the request before
the gateway handoff, including a zero-value coupon or fee line.

The same pre-payment guard also stops an existing order-payment retry when the
production launch switch is off, the current product/store configuration has
drifted, the terms-version policy is invalid, or the order lacks an eligible
original terms snapshot. Orders remain identifiable through their immutable
reading-product metadata even if the current product option is later damaged.

### Terms-version rotation

`CheckoutTerms::PAYMENT_ELIGIBLE_VERSIONS` is an explicit cohort list. The first
entry is the version stamped on new orders; later entries are older versions
that are still allowed to finish payment. Rotation is a coordinated rollout:

1. keep the launch switch off for new purchases;
2. deploy the paid-reading receiver so it accepts both the old and new versions;
3. deploy this bridge with the new version first and the old version retained;
4. re-enable only after health and no-charge tests pass;
5. wait until every old ECPay payment, callback, and legitimate retry window is
   closed and reconcile all old-version orders; and
6. remove the old version from the receiver and bridge only after that evidence
   is recorded.

Never change only the receiver's single expected version while an older order
can still be charged. Never overwrite
`_vol_checkout_terms_version_presented` or
`_vol_checkout_terms_presented_at` to make an old order look current. If an old
cohort must be retired early, the bridge blocks a fresh gateway handoff; support
must cancel/recreate the order and obtain a new explicit customer acceptance.
An already-started ECPay payment cannot be recalled by WordPress, which is why
the receiver overlap must begin before the WordPress rotation.

Orders created by a bridge version older than `0.2.1` do not contain the new
acceptance-source marker and therefore fail the payment retry guard. Do not
backfill that marker: reconcile any such staging order manually, or cancel it
and create a new checkout where the customer can explicitly accept the terms.

`vol_commerce_launch_enabled` is a fail-closed launch switch. It defaults to
`no` and makes the fixed reading non-purchasable everywhere until the signed
webhook, transactional email, private reading store, and result worker have
passed launch verification. An authenticated administrator can set it to
`yes` through the registered WordPress settings REST field for the final
go-live. The same purchasability check also stays closed if the stored tax
status, regular/current price, sale schedule, store currency, or runtime
tax/coupon guards drift from the fixed contract.

The authenticated, non-cacheable
`POST /wp-json/vale-of-light/v1/commerce-health` endpoint reports the
fixed-product, guest-checkout, checkout-page, terms-page, and launch-gate
checks without returning credentials. It deliberately does not expose a GET
variant because custom cacheable REST GET responses can be replayed without
their original authorization context by an upstream full-page cache.

## Verification

The amount and checkout-shape rules are kept in a WordPress-independent class
so they can be exercised deterministically:

```sh
php tests/CommerceInvariantTest.php
php tests/CheckoutTermsTest.php
php tests/BillingEmailConfirmationTest.php
php tests/AccessEmailPolicyTest.php
node tests/static-verification.mjs
```

Run a PHP syntax check over the plugin as part of packaging:

```sh
find . -name '*.php' -print0 | xargs -0 -n1 php -l
```
