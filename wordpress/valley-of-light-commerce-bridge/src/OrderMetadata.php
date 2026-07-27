<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WC_Order;

final class OrderMetadata
{
    private const TERMS_VERSION_KEY = '_vol_checkout_terms_version_presented';
    private const TERMS_PRESENTED_AT_KEY = '_vol_checkout_terms_presented_at';
    private const TERMS_ACCEPTANCE_SOURCE_KEY = '_vol_checkout_terms_acceptance_source';
    private const READING_PRODUCT_ID_KEY = '_vol_reading_product_id';
    private const READING_PRODUCT_SKU_KEY = '_vol_reading_product_sku';
    private const CLASSIC_ACCEPTANCE_SOURCE = 'classic-required-terms-checkbox';
    private const STORE_API_ACCEPTANCE_SOURCE = 'store-api-validated-checkout';

    public function register(): void
    {
        add_action('woocommerce_checkout_create_order', [$this, 'stampClassicCheckout'], 10, 2);
        add_action(
            'woocommerce_store_api_checkout_order_processed',
            [$this, 'stampStoreApiCheckout'],
            10,
            1
        );
    }

    /**
     * @param array<string, mixed> $data
     */
    public function stampClassicCheckout(WC_Order $order, array $data): void
    {
        if (
            1 !== (int) ($data['terms-field'] ?? 0)
            || 1 !== (int) ($data['terms'] ?? 0)
        ) {
            return;
        }

        $this->stamp($order, self::CLASSIC_ACCEPTANCE_SOURCE);
    }

    public function stampStoreApiCheckout(WC_Order $order): void
    {
        if ($this->stamp($order, self::STORE_API_ACCEPTANCE_SOURCE)) {
            $order->save();
        }
    }

    /**
     * @return string[]
     */
    public static function acceptanceEvidenceFailures(WC_Order $order): array
    {
        $failures = CheckoutTerms::evidenceFailures(
            [
                'version_presented' => $order->get_meta(self::TERMS_VERSION_KEY, true),
                'presented_at' => $order->get_meta(self::TERMS_PRESENTED_AT_KEY, true),
                'product_id' => $order->get_meta(self::READING_PRODUCT_ID_KEY, true),
                'acceptance_source' =>
                    $order->get_meta(self::TERMS_ACCEPTANCE_SOURCE_KEY, true),
            ],
            ReadingProduct::configuredId()
        );
        if (
            ReadingProduct::EXPECTED_SKU
            !== self::acceptedReadingProductSku($order)
        ) {
            $failures[] = 'reading_product_sku';
        }

        return array_values(array_unique($failures, SORT_STRING));
    }

    /**
     * Validate immutable evidence on an already-created order without binding
     * it to whichever product ID is currently configured for new checkouts.
     *
     * @return string[]
     */
    public static function acceptedOrderEvidenceFailures(
        WC_Order $order
    ): array {
        $version = $order->get_meta(self::TERMS_VERSION_KEY, true);
        $eligibleVersions = is_string($version) ? [$version] : [];
        $failures = CheckoutTermsPolicy::evidenceFailures(
            [
                'version_presented' => $version,
                'presented_at' => $order->get_meta(
                    self::TERMS_PRESENTED_AT_KEY,
                    true
                ),
                'product_id' => $order->get_meta(
                    self::READING_PRODUCT_ID_KEY,
                    true
                ),
                'acceptance_source' => $order->get_meta(
                    self::TERMS_ACCEPTANCE_SOURCE_KEY,
                    true
                ),
            ],
            self::acceptedReadingProductId($order),
            $eligibleVersions
        );
        if (
            ReadingProduct::EXPECTED_SKU
            !== self::acceptedReadingProductSku($order)
        ) {
            $failures[] = 'reading_product_sku';
        }

        return array_values(array_unique($failures, SORT_STRING));
    }

    public static function acceptedReadingProductId(WC_Order $order): int
    {
        $value = $order->get_meta(self::READING_PRODUCT_ID_KEY, true);
        if (is_int($value)) {
            return $value > 0 ? $value : 0;
        }
        if (
            ! is_string($value)
            || 1 !== preg_match('/^[1-9][0-9]{0,18}$/D', $value)
            || (int) $value <= 0
            || (string) (int) $value !== $value
        ) {
            return 0;
        }

        return (int) $value;
    }

    public static function acceptedReadingProductSku(WC_Order $order): string
    {
        return trim(
            (string) $order->get_meta(self::READING_PRODUCT_SKU_KEY, true)
        );
    }

    private function stamp(WC_Order $order, string $acceptanceSource): bool
    {
        if (
            ! ReadingProduct::orderHasExpectedItems($order)
            || self::hasAnyAcceptanceEvidence($order)
        ) {
            return false;
        }

        $order->update_meta_data(
            self::TERMS_VERSION_KEY,
            CheckoutTerms::currentVersion()
        );
        $order->update_meta_data(self::TERMS_PRESENTED_AT_KEY, gmdate('c'));
        $order->update_meta_data(
            self::TERMS_ACCEPTANCE_SOURCE_KEY,
            $acceptanceSource
        );
        $order->update_meta_data(
            self::READING_PRODUCT_ID_KEY,
            ReadingProduct::configuredId()
        );
        $order->update_meta_data(
            self::READING_PRODUCT_SKU_KEY,
            ReadingProduct::EXPECTED_SKU
        );

        return true;
    }

    private static function hasAnyAcceptanceEvidence(WC_Order $order): bool
    {
        foreach (
            [
                self::TERMS_VERSION_KEY,
                self::TERMS_PRESENTED_AT_KEY,
                self::TERMS_ACCEPTANCE_SOURCE_KEY,
                self::READING_PRODUCT_ID_KEY,
                self::READING_PRODUCT_SKU_KEY,
            ] as $key
        ) {
            if ($order->meta_exists($key)) {
                return true;
            }
        }

        return false;
    }
}
