<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use Automattic\WooCommerce\Blocks\Domain\Services\CheckoutFields;
use Automattic\WooCommerce\Blocks\Package;
use WC_Cart;
use WC_Order;
use WP_Error;

final class BillingEmailConfirmationPolicy
{
    private const DIGEST_CONTEXT = "vol-billing-email-confirmation-v1\0";
    private const ACCEPTANCE_SOURCES = [
        'classic-checkout-server-validation',
        'store-api-server-validation',
    ];

    public static function valuesMatch(
        string $normalizedBillingEmail,
        string $normalizedConfirmationEmail
    ): bool {
        return '' !== $normalizedBillingEmail
            && '' !== $normalizedConfirmationEmail
            && strlen($normalizedBillingEmail) <= 254
            && strlen($normalizedConfirmationEmail) <= 254
            && hash_equals($normalizedBillingEmail, $normalizedConfirmationEmail);
    }

    public static function digest(string $normalizedBillingEmail, string $secret): string
    {
        if ('' === $normalizedBillingEmail || '' === $secret) {
            return '';
        }

        return hash_hmac(
            'sha256',
            self::DIGEST_CONTEXT . $normalizedBillingEmail,
            $secret
        );
    }

    /**
     * @param array<string, mixed> $evidence
     * @return string[]
     */
    public static function evidenceFailures(
        array $evidence,
        string $normalizedBillingEmail,
        string $secret
    ): array {
        $failures = [];
        $digest = $evidence['digest'] ?? null;
        $confirmedAt = $evidence['confirmed_at'] ?? null;
        $acceptanceSource = $evidence['acceptance_source'] ?? null;
        $expectedDigest = self::digest($normalizedBillingEmail, $secret);

        if (
            '' === $normalizedBillingEmail
            || strlen($normalizedBillingEmail) > 254
        ) {
            $failures[] = 'billing_email';
        }

        if (
            ! is_string($digest)
            || 1 !== preg_match('/^[a-f0-9]{64}$/D', $digest)
            || '' === $expectedDigest
            || ! hash_equals($expectedDigest, $digest)
        ) {
            $failures[] = 'billing_email_confirmation_digest';
        }

        if (
            ! is_string($confirmedAt)
            || ! self::isValidTimestamp($confirmedAt)
        ) {
            $failures[] = 'billing_email_confirmation_confirmed_at';
        }

        if (
            ! is_string($acceptanceSource)
            || ! in_array($acceptanceSource, self::ACCEPTANCE_SOURCES, true)
        ) {
            $failures[] = 'billing_email_confirmation_acceptance_source';
        }

        return $failures;
    }

    private static function isValidTimestamp(string $timestamp): bool
    {
        if (
            1 !== preg_match(
                '/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$/D',
                $timestamp
            )
        ) {
            return false;
        }

        try {
            new \DateTimeImmutable($timestamp);
            $errors = \DateTimeImmutable::getLastErrors();

            return false === $errors
                || (0 === $errors['warning_count'] && 0 === $errors['error_count']);
        } catch (\Exception) {
            return false;
        }
    }
}

final class BillingEmailConfirmation
{
    private const CLASSIC_FIELD_KEY = 'billing_email_confirmation';
    private const STORE_API_FIELD_ID =
        'vale-of-light/billing-email-confirmation';
    private const DIGEST_KEY = '_vol_billing_email_confirmation_digest';
    private const CONFIRMED_AT_KEY = '_vol_billing_email_confirmed_at';
    private const ACCEPTANCE_SOURCE_KEY =
        '_vol_billing_email_confirmation_acceptance_source';
    private const CLASSIC_ACCEPTANCE_SOURCE =
        'classic-checkout-server-validation';
    private const STORE_API_ACCEPTANCE_SOURCE =
        'store-api-server-validation';

    public function register(): void
    {
        add_filter(
            'woocommerce_checkout_fields',
            [self::class, 'addClassicField'],
            PHP_INT_MAX
        );
        add_action(
            'woocommerce_after_checkout_validation',
            [self::class, 'validateClassicCheckout'],
            PHP_INT_MAX - 10,
            2
        );
        add_action(
            'woocommerce_checkout_create_order',
            [self::class, 'stampClassicEvidence'],
            20,
            2
        );
        add_action(
            'woocommerce_init',
            [self::class, 'registerStoreApiField'],
            20
        );
        add_action(
            'woocommerce_store_api_checkout_order_processed',
            [self::class, 'stampStoreApiEvidence'],
            20
        );
    }

    /**
     * @param array<string, array<string, array<string, mixed>>> $fields
     * @return array<string, array<string, array<string, mixed>>>
     */
    public static function addClassicField(array $fields): array
    {
        $cart = WC()->cart ?? null;
        if (
            ! $cart instanceof WC_Cart
            || ! ReadingProduct::cartContainsReading($cart)
            || ! isset($fields['billing'])
        ) {
            return $fields;
        }

        $emailPriority = (int) (
            $fields['billing']['billing_email']['priority'] ?? 110
        );
        $fields['billing'][self::CLASSIC_FIELD_KEY] = [
            'type' => 'email',
            'label' => __(
                '再次輸入付款 Email',
                'vale-of-light-commerce-bridge'
            ),
            'description' => __(
                '付款確認後，安全資料填寫連結會寄到上方的付款 Email。請再次輸入完全相同的 Email，避免寄錯。',
                'vale-of-light-commerce-bridge'
            ),
            'placeholder' => __(
                '請再次輸入完全相同的 Email',
                'vale-of-light-commerce-bridge'
            ),
            'required' => true,
            'validate' => ['email'],
            'priority' => $emailPriority + 1,
            'autocomplete' => 'off',
            'custom_attributes' => [
                'autocomplete' => 'off',
                'autocapitalize' => 'none',
                'maxlength' => '254',
            ],
        ];

        return $fields;
    }

    /**
     * @param array<string, mixed> $data
     */
    public static function validateClassicCheckout(
        array $data,
        WP_Error $errors
    ): void {
        $cart = WC()->cart ?? null;
        if (
            ! $cart instanceof WC_Cart
            || ! ReadingProduct::cartContainsReading($cart)
        ) {
            return;
        }

        if (
            ! BillingEmailConfirmationPolicy::valuesMatch(
                self::normalizeEmail($data['billing_email'] ?? null),
                self::normalizeEmail($data[self::CLASSIC_FIELD_KEY] ?? null)
            )
        ) {
            $errors->add(
                'vol_billing_email_confirmation_mismatch',
                self::mismatchMessage()
            );
        }
    }

    /**
     * @param array<string, mixed> $data
     */
    public static function stampClassicEvidence(
        WC_Order $order,
        array $data
    ): void {
        if (! ReadingProduct::orderContainsReading($order)) {
            return;
        }

        $billingEmail = self::normalizeEmail($order->get_billing_email());
        $confirmationEmail = self::normalizeEmail(
            $data[self::CLASSIC_FIELD_KEY] ?? null
        );

        if (
            BillingEmailConfirmationPolicy::valuesMatch(
                $billingEmail,
                $confirmationEmail
            )
        ) {
            self::stamp(
                $order,
                $billingEmail,
                self::CLASSIC_ACCEPTANCE_SOURCE
            );
        }
    }

    public static function registerStoreApiField(): void
    {
        if (! function_exists('woocommerce_register_additional_checkout_field')) {
            return;
        }

        try {
            woocommerce_register_additional_checkout_field(
                [
                    'id' => self::STORE_API_FIELD_ID,
                    'label' => __(
                        '再次輸入付款 Email（付款後安全連結會寄到這個信箱）',
                        'vale-of-light-commerce-bridge'
                    ),
                    'optionalLabel' => __(
                        '再次輸入付款 Email（付款後安全連結會寄到這個信箱）',
                        'vale-of-light-commerce-bridge'
                    ),
                    'location' => 'contact',
                    'type' => 'text',
                    'required' => self::readingCartCondition(),
                    'hidden' => self::nonReadingCartCondition(),
                    'attributes' => [
                        'autocomplete' => 'off',
                        'autocapitalize' => 'none',
                        'maxLength' => 254,
                        'aria-label' => __(
                            '再次輸入付款 Email；安全資料填寫連結會寄到這個信箱',
                            'vale-of-light-commerce-bridge'
                        ),
                        'title' => self::mismatchMessage(),
                    ],
                    'show_in_order_confirmation' => false,
                    'sanitize_callback' => [self::class, 'normalizeEmail'],
                    'validation' => [
                        'type' => 'string',
                        'format' => 'email',
                        'const' => [
                            '$data' => '/customer/billing_address/email',
                        ],
                        'errorMessage' => self::mismatchMessage(),
                    ],
                ]
            );
        } catch (\Throwable) {
            self::logStoreApiRegistrationFailure();
        }
    }

    public static function stampStoreApiEvidence(WC_Order $order): void
    {
        if (! ReadingProduct::orderContainsReading($order)) {
            return;
        }

        $checkoutFields = self::storeApiCheckoutFields();
        if (! $checkoutFields instanceof CheckoutFields) {
            return;
        }

        $confirmationEmail = self::normalizeEmail(
            $checkoutFields->get_field_from_object(
                self::STORE_API_FIELD_ID,
                $order,
                'other'
            )
        );
        $billingEmail = self::normalizeEmail($order->get_billing_email());

        if (
            BillingEmailConfirmationPolicy::valuesMatch(
                $billingEmail,
                $confirmationEmail
            )
        ) {
            self::stamp(
                $order,
                $billingEmail,
                self::STORE_API_ACCEPTANCE_SOURCE
            );
        }

        // The order already owns the billing email. Retain only the keyed proof,
        // not a second plaintext copy of the same personal data.
        $order->delete_meta_data(
            CheckoutFields::get_group_key('other')
                . self::STORE_API_FIELD_ID
        );
        $order->save();
    }

    /**
     * @return string[]
     */
    public static function evidenceFailures(WC_Order $order): array
    {
        return BillingEmailConfirmationPolicy::evidenceFailures(
            [
                'digest' => $order->get_meta(self::DIGEST_KEY, true),
                'confirmed_at' => $order->get_meta(
                    self::CONFIRMED_AT_KEY,
                    true
                ),
                'acceptance_source' => $order->get_meta(
                    self::ACCEPTANCE_SOURCE_KEY,
                    true
                ),
            ],
            self::normalizeEmail($order->get_billing_email()),
            self::digestSecret()
        );
    }

    public static function isEvidenceFailure(string $failure): bool
    {
        return 'billing_email' === $failure
            || str_starts_with(
                $failure,
                'billing_email_confirmation_'
            );
    }

    public static function configurationIsValid(): bool
    {
        return self::runtimeGuardsRegistered()
            && self::storeApiFieldIsRegistered()
            && self::digestSecretIsValid();
    }

    public static function runtimeGuardsRegistered(): bool
    {
        return false !== has_filter(
            'woocommerce_checkout_fields',
            [self::class, 'addClassicField']
        )
            && false !== has_action(
                'woocommerce_after_checkout_validation',
                [self::class, 'validateClassicCheckout']
            )
            && false !== has_action(
                'woocommerce_checkout_create_order',
                [self::class, 'stampClassicEvidence']
            )
            && false !== has_action(
                'woocommerce_init',
                [self::class, 'registerStoreApiField']
            )
            && false !== has_action(
                'woocommerce_store_api_checkout_order_processed',
                [self::class, 'stampStoreApiEvidence']
            );
    }

    public static function normalizeEmail(mixed $value): string
    {
        if (! is_string($value)) {
            return '';
        }

        $email = sanitize_email(trim($value));

        return false !== is_email($email) ? $email : '';
    }

    public static function mismatchMessage(): string
    {
        return __(
            '兩次輸入的付款 Email 不一致。請確認並再次輸入完全相同的 Email；付款確認後，安全資料填寫連結會寄到這個信箱。',
            'vale-of-light-commerce-bridge'
        );
    }

    public static function orderEvidenceErrorMessage(): string
    {
        return __(
            '付款 Email 的確認紀錄不完整，或付款 Email 已在確認後變更。為避免安全資料填寫連結寄錯，系統尚未把本次付款送往金流；請重新從購買按鈕建立結帳並輸入兩次完全相同的 Email。',
            'vale-of-light-commerce-bridge'
        );
    }

    private static function stamp(
        WC_Order $order,
        string $normalizedBillingEmail,
        string $acceptanceSource
    ): bool {
        if (
            self::hasAnyEvidence($order)
            || ! self::digestSecretIsValid()
        ) {
            return false;
        }

        $digest = BillingEmailConfirmationPolicy::digest(
            $normalizedBillingEmail,
            self::digestSecret()
        );
        if ('' === $digest) {
            return false;
        }

        $order->update_meta_data(self::DIGEST_KEY, $digest);
        $order->update_meta_data(self::CONFIRMED_AT_KEY, gmdate('c'));
        $order->update_meta_data(
            self::ACCEPTANCE_SOURCE_KEY,
            $acceptanceSource
        );

        return true;
    }

    private static function hasAnyEvidence(WC_Order $order): bool
    {
        foreach (
            [
                self::DIGEST_KEY,
                self::CONFIRMED_AT_KEY,
                self::ACCEPTANCE_SOURCE_KEY,
            ] as $key
        ) {
            if ($order->meta_exists($key)) {
                return true;
            }
        }

        return false;
    }

    /**
     * @return array<string, mixed>
     */
    private static function readingCartCondition(): array
    {
        return [
            'type' => 'object',
            'properties' => [
                'cart' => [
                    'type' => 'object',
                    'properties' => [
                        'items' => [
                            'type' => 'array',
                            'contains' => [
                                'const' => ReadingProduct::configuredId(),
                            ],
                        ],
                    ],
                    'required' => ['items'],
                ],
            ],
            'required' => ['cart'],
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private static function nonReadingCartCondition(): array
    {
        return [
            'type' => 'object',
            'properties' => [
                'cart' => [
                    'type' => 'object',
                    'properties' => [
                        'items' => [
                            'type' => 'array',
                            'not' => [
                                'contains' => [
                                    'const' => ReadingProduct::configuredId(),
                                ],
                            ],
                        ],
                    ],
                    'required' => ['items'],
                ],
            ],
            'required' => ['cart'],
        ];
    }

    private static function storeApiFieldIsRegistered(): bool
    {
        $checkoutFields = self::storeApiCheckoutFields();

        return $checkoutFields instanceof CheckoutFields
            && $checkoutFields->is_field(self::STORE_API_FIELD_ID);
    }

    private static function storeApiCheckoutFields(): ?CheckoutFields
    {
        if (
            ! function_exists('woocommerce_register_additional_checkout_field')
            || ! class_exists(Package::class)
            || ! class_exists(CheckoutFields::class)
        ) {
            return null;
        }

        try {
            $checkoutFields = Package::container()->get(CheckoutFields::class);

            return $checkoutFields instanceof CheckoutFields
                ? $checkoutFields
                : null;
        } catch (\Throwable) {
            return null;
        }
    }

    private static function digestSecretIsValid(): bool
    {
        $salt = (string) wp_salt('auth');

        return strlen($salt) >= 32
            && false === stripos($salt, 'put your unique phrase here');
    }

    private static function digestSecret(): string
    {
        if (! self::digestSecretIsValid()) {
            return '';
        }

        return hash(
            'sha256',
            "vol-billing-email-confirmation-secret-v1\0"
                . (string) wp_salt('auth'),
            true
        );
    }

    private static function logStoreApiRegistrationFailure(): void
    {
        if (! function_exists('wc_get_logger')) {
            return;
        }

        wc_get_logger()->critical(
            'Store API email-confirmation field registration failed; reading checkout remains closed.',
            ['source' => 'vale-of-light-commerce-bridge']
        );
    }
}
