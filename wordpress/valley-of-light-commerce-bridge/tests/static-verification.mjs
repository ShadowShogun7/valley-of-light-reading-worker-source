import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const read = (path) => readFile(join(root, path), "utf8");

const [
  bootstrap,
  checkoutGuard,
  productPolicy,
  readingProduct,
  launchGate,
  checkoutTerms,
  orderMetadata,
  emailConfirmation,
  accessEmailPolicy,
  accessEmail,
] =
  await Promise.all([
    read("valley-of-light-commerce-bridge.php"),
    read("src/CheckoutGuard.php"),
    read("src/ProductPolicy.php"),
    read("src/ReadingProduct.php"),
    read("src/LaunchGate.php"),
    read("src/CheckoutTerms.php"),
    read("src/OrderMetadata.php"),
    read("src/BillingEmailConfirmation.php"),
    read("src/AccessEmailPolicy.php"),
    read("src/AccessEmail.php"),
  ]);

for (const requiredClass of [
  "src/CommerceInvariant.php",
  "src/CheckoutTerms.php",
  "src/AccessEmailPolicy.php",
  "src/AccessEmail.php",
  "src/BillingEmailConfirmation.php",
  "src/ProductPolicy.php",
  "src/CheckoutGuard.php",
]) {
  assert.ok(
    bootstrap.includes(`require_once VOL_COMMERCE_BRIDGE_DIR . '${requiredClass}';`),
    `Bootstrap must load ${requiredClass}.`,
  );
}

assert.ok(
  bootstrap.indexOf("(new ProductPolicy())->register()") <
    bootstrap.indexOf("(new LaunchGate())->register()"),
  "Runtime product guards must register before the launch gate evaluates health.",
);
assert.ok(
  bootstrap.indexOf("(new BillingEmailConfirmation())->register()") <
    bootstrap.indexOf("(new LaunchGate())->register()"),
  "Email-confirmation guards must register before the launch gate evaluates health.",
);
assert.ok(
  bootstrap.indexOf("(new AccessEmail())->register()") <
    bootstrap.indexOf("(new LaunchGate())->register()"),
  "Access-email guards must register before the launch gate evaluates health.",
);
assert.match(
  bootstrap,
  /Version: 0\.3\.0[\s\S]*VOL_COMMERCE_BRIDGE_VERSION', '0\.3\.0'/,
  "Plugin header and runtime version must move together.",
);

for (const hook of [
  "woocommerce_after_checkout_validation",
  "woocommerce_checkout_order_processed",
  "woocommerce_store_api_checkout_order_processed",
  "woocommerce_before_pay_action",
]) {
  assert.match(checkoutGuard, new RegExp(`'${hook}'`), `${hook} must remain guarded.`);
}

for (const hook of [
  "woocommerce_product_get_tax_status",
  "woocommerce_product_is_taxable",
  "woocommerce_coupon_is_valid_for_product",
  "woocommerce_coupon_is_valid",
  "woocommerce_coupons_enabled",
  "woocommerce_before_product_object_save",
]) {
  assert.match(productPolicy, new RegExp(`'${hook}'`), `${hook} must remain guarded.`);
}

for (const invariant of [
  "discount_total",
  "fee_total",
  "shipping_total",
  "tax_total",
  "coupon_count",
  "fee_count",
  "shipping_count",
  "tax_line_count",
]) {
  assert.match(readingProduct, new RegExp(`'${invariant}'`), `${invariant} must be checked.`);
}

for (const healthCheck of [
  "'price'",
  "'regular_price'",
  "'not_on_sale'",
  "'non_taxable'",
  "'currency'",
  "'global_coupons_disabled'",
  "'runtime_tax_and_coupon_guards'",
  "'runtime_checkout_guards'",
  "'checkout_terms_lifecycle'",
  "'billing_email_confirmation'",
  "'access_email_bridge'",
  "'transactional_email_transport_verified'",
]) {
  assert.match(readingProduct, new RegExp(healthCheck), `${healthCheck} must remain in health.`);
}

assert.match(
  accessEmail,
  /configurationIsValid[\s\S]*mailTransportIsVerified\(\)/,
  "The access-email endpoint must fail closed until the production mail transport is verified.",
);
assert.match(
  accessEmail,
  /VOL_EMAIL_TRANSPORT_VERIFIED[\s\S]*true === constant/,
  "Mail readiness must require an explicit boolean launch attestation.",
);
assert.match(
  accessEmail,
  /compareAndSwapOption[\s\S]*option_value[\s\S]*maybe_serialize/,
  "Failed notification retries must acquire an atomic database claim.",
);
assert.match(
  accessEmail,
  /vol_access_email_state_indeterminate/,
  "An abandoned in-flight send must fail closed instead of risking an automatic duplicate.",
);
assert.match(
  accessEmail,
  /finishIdempotency[\s\S]*claimId[\s\S]*compareAndSwapOption/,
  "A late sender must be fenced from finishing a newer notification claim.",
);
assert.match(
  accessEmail,
  /addAdminResendAction[\s\S]*orderContainsReading/,
  "The manual resend action must be shown only for reading orders.",
);
assert.match(
  orderMetadata,
  /_vol_reading_product_sku[\s\S]*acceptedOrderEvidenceFailures/,
  "Paid-order delivery must use immutable stamped product evidence.",
);
assert.match(
  readingProduct,
  /acceptedOrderInvariantFailures[\s\S]*acceptedReadingProductId/,
  "Historical paid orders must not depend on the product ID configured for new sales.",
);

assert.match(
  launchGate,
  /self::isEnabled\(\)[\s\S]*ReadingProduct::configurationIsValid\(\)/,
  "Purchasability must fail closed when the commerce configuration drifts.",
);

assert.match(
  checkoutGuard,
  /validatePaymentRetry[\s\S]*paymentEnvironmentIsEligible/,
  "Existing order-pay retries must run the payment-environment guard.",
);
assert.match(
  readingProduct,
  /orderContainsReading[\s\S]*acceptedReadingProductId[\s\S]*EXPECTED_SKU/,
  "Existing reading orders must remain identifiable when the configured product drifts.",
);
assert.match(
  checkoutGuard,
  /LaunchGate::allowsPayment\(\)/,
  "Every guarded gateway handoff must respect the production launch gate.",
);
assert.match(
  checkoutGuard,
  /OrderMetadata::acceptanceEvidenceFailures\(\$order\)/,
  "Every guarded gateway handoff must validate the order's original terms evidence.",
);
assert.match(
  checkoutGuard,
  /BillingEmailConfirmation::evidenceFailures\(\$order\)/,
  "Every guarded gateway handoff must validate server-owned email confirmation evidence.",
);
assert.match(
  checkoutTerms,
  /PAYMENT_ELIGIBLE_VERSIONS[\s\S]*CURRENT_VERSION/,
  "Terms rotation must declare the still-payable order cohorts explicitly.",
);
assert.match(
  checkoutTerms,
  /commerce-terms-2026-07-26-draft/,
  "Draft legal copy must mint only an explicitly draft consent cohort.",
);
assert.match(
  orderMetadata,
  /woocommerce_store_api_checkout_order_processed/,
  "Store API terms evidence must be stamped only after validated checkout processing.",
);
assert.match(
  orderMetadata,
  /stampStoreApiCheckout[\s\S]*\$order->save\(\)/,
  "Store API terms evidence must be persisted before the payment gateway runs.",
);
assert.doesNotMatch(
  orderMetadata,
  /woocommerce_store_api_checkout_update_order_from_request/,
  "Draft Store API updates must not be treated as customer acceptance.",
);

for (const hook of [
  "woocommerce_email_enabled_customer_processing_order",
  "woocommerce_email_enabled_customer_completed_order",
  "woocommerce_email_after_order_table",
  "woocommerce_payment_complete_order_status",
  "woocommerce_order_status_changed",
]) {
  assert.match(
    accessEmail,
    new RegExp(`'${hook}'`),
    `${hook} must remain part of access-email enforcement.`,
  );
}
assert.match(
  accessEmail,
  /register_rest_route\([\s\S]*ROUTE_PATH[\s\S]*permission_callback/,
  "The app-to-WordPress email route must always use its signature permission callback.",
);
assert.match(
  accessEmailPolicy,
  /hash_hmac\('sha256', \$timestamp \. '\.' \. \$body/,
  "WordPress must verify the exact signed request body.",
);
assert.match(
  accessEmail,
  /GRANT_ID_KEY[\s\S]*GRANT_EXPIRES_AT_KEY/,
  "WordPress may persist only the non-secret grant reference and expiry.",
);
assert.doesNotMatch(
  accessEmail.match(
    /private static function persistGrantReference[\s\S]*?private static function accessUrlForOrder/,
  )?.[0] ?? "",
  /access_url|raw_token|token_hash|\/r#/i,
  "The order must never store a raw capability URL or token.",
);
assert.match(
  accessEmail,
  /filterCustomerEmailEnabled[\s\S]*emailContexts/,
  "Premature and deferred automatic Woo customer emails must remain suppressed.",
);
assert.match(
  accessEmail,
  /result_ready[\s\S]*update_status\([\s\S]*'completed'/,
  "Only the result-ready notification path may complete the reading order.",
);
assert.match(
  orderMetadata,
  /hasAnyAcceptanceEvidence\(\$order\)/,
  "Existing or partial terms evidence must never be silently restamped.",
);
assert.doesNotMatch(
  checkoutGuard.match(
    /public static function validatePaymentRetry[\s\S]*?public static function runtimeGuardsRegistered/,
  )?.[0] ?? "",
  /update_meta_data/,
  "The order-pay retry guard must not rewrite accepted terms evidence.",
);

for (const hook of [
  "woocommerce_checkout_fields",
  "woocommerce_after_checkout_validation",
  "woocommerce_checkout_create_order",
  "woocommerce_init",
  "woocommerce_store_api_checkout_order_processed",
]) {
  assert.match(
    emailConfirmation,
    new RegExp(`'${hook}'`),
    `${hook} must remain part of email-confirmation enforcement.`,
  );
}
assert.match(
  emailConfirmation,
  /woocommerce_register_additional_checkout_field[\s\S]*'location' => 'contact'/,
  "Checkout Blocks must use WooCommerce's native server-aware additional-field API.",
);
assert.ok(
  emailConfirmation.includes(
    "'$data' => '/customer/billing_address/email'",
  ),
  "The Blocks field must declare an exact match against the billing email.",
);
assert.match(
  emailConfirmation,
  /stampStoreApiEvidence[\s\S]*BillingEmailConfirmationPolicy::valuesMatch[\s\S]*self::stamp/,
  "Store API processing must independently compare the server-owned order email before stamping proof.",
);
assert.match(
  emailConfirmation,
  /stampClassicEvidence[\s\S]*BillingEmailConfirmationPolicy::valuesMatch[\s\S]*self::stamp/,
  "Classic checkout must independently compare validated server values before stamping proof.",
);
assert.match(
  emailConfirmation,
  /hash_hmac\([\s\S]*'sha256'/,
  "The order must retain keyed proof rather than trusting a client flag.",
);
assert.match(
  emailConfirmation,
  /delete_meta_data\([\s\S]*CheckoutFields::get_group_key\('other'\)/,
  "The Store API's duplicate plaintext confirmation must be removed after proof is stamped.",
);
assert.match(
  emailConfirmation,
  /show_in_order_confirmation' => false/,
  "The duplicate confirmation value must not be rendered in order emails or confirmation views.",
);
assert.doesNotMatch(
  emailConfirmation,
  /<script|wp_enqueue_script|wp_add_inline_script/i,
  "Email confirmation must not depend on client-only JavaScript.",
);

console.log("Commerce bridge static verification passed.");
