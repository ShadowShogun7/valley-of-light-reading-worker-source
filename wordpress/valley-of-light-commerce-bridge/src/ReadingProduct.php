<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WC_Cart;
use WC_Order;
use WC_Order_Item_Product;
use WC_Product;

final class ReadingProduct
{
    public const EXPECTED_SKU = 'vol-astrology-synastry';
    public const EXPECTED_CURRENCY = 'TWD';
    public const EXPECTED_TOTAL = '1280';

    public static function configuredId(): int
    {
        return (int) get_option('vol_reading_product_id', 0);
    }

    public static function get(): ?WC_Product
    {
        $productId = self::configuredId();
        if ($productId <= 0) {
            return null;
        }

        $product = wc_get_product($productId);
        if (
            ! $product instanceof WC_Product
            || self::EXPECTED_SKU !== (string) $product->get_sku()
        ) {
            return null;
        }

        return $product;
    }

    public static function cartContainsReading(WC_Cart $cart): bool
    {
        $productId = self::configuredId();

        foreach ($cart->get_cart() as $cartItem) {
            if ($productId === (int) ($cartItem['product_id'] ?? 0)) {
                return true;
            }
        }

        return false;
    }

    public static function cartHasExpectedShape(WC_Cart $cart): bool
    {
        $items = $cart->get_cart();
        if (1 !== count($items)) {
            return false;
        }

        $item = reset($items);

        return is_array($item)
            && self::configuredId() === (int) ($item['product_id'] ?? 0)
            && 1 === (int) ($item['quantity'] ?? 0);
    }

    public static function orderContainsReading(WC_Order $order): bool
    {
        $productId = self::configuredId();
        $acceptedProductId = OrderMetadata::acceptedReadingProductId($order);

        if (
            $acceptedProductId > 0
            && self::EXPECTED_SKU
                === OrderMetadata::acceptedReadingProductSku($order)
        ) {
            foreach ($order->get_items('line_item') as $item) {
                if ($acceptedProductId === (int) $item->get_product_id()) {
                    return true;
                }
            }
        }

        foreach ($order->get_items('line_item') as $item) {
            if ($productId === (int) $item->get_product_id()) {
                return true;
            }

            $product = $item->get_product();
            if (
                $product instanceof WC_Product
                && self::EXPECTED_SKU === (string) $product->get_sku()
            ) {
                return true;
            }
        }

        return false;
    }

    public static function orderHasExpectedItems(WC_Order $order): bool
    {
        $items = $order->get_items('line_item');
        if (1 !== count($items)) {
            return false;
        }

        $item = reset($items);
        if (
            false === $item
            || self::configuredId() !== (int) $item->get_product_id()
            || 0 !== (int) $item->get_variation_id()
            || 1 !== (int) $item->get_quantity()
        ) {
            return false;
        }

        return true;
    }

    public static function orderIsEligible(WC_Order $order): bool
    {
        return [] === self::acceptedOrderInvariantFailures($order);
    }

    /**
     * @return string[]
     */
    public static function cartInvariantFailures(WC_Cart $cart): array
    {
        $items = $cart->get_cart();
        $item = 1 === count($items) ? reset($items) : null;

        return CommerceInvariant::failures(
            [
                'item_count' => count($items),
                'product_id' => is_array($item) ? ($item['product_id'] ?? null) : null,
                'variation_id' => is_array($item) ? ($item['variation_id'] ?? 0) : null,
                'quantity' => is_array($item) ? ($item['quantity'] ?? null) : null,
                'currency' => get_woocommerce_currency(),
                'line_subtotal' => is_array($item) ? ($item['line_subtotal'] ?? null) : null,
                'line_total' => is_array($item) ? ($item['line_total'] ?? null) : null,
                'line_subtotal_tax' => is_array($item)
                    ? ($item['line_subtotal_tax'] ?? null)
                    : null,
                'line_total_tax' => is_array($item) ? ($item['line_tax'] ?? null) : null,
                'subtotal' => $cart->get_subtotal(),
                'contents_total' => $cart->get_cart_contents_total(),
                'total' => $cart->get_total('edit'),
                'subtotal_tax' => $cart->get_subtotal_tax(),
                'tax_total' => $cart->get_total_tax(),
                'discount_total' => $cart->get_discount_total(),
                'discount_tax' => $cart->get_discount_tax(),
                'fee_total' => $cart->get_fee_total(),
                'fee_tax' => $cart->get_fee_tax(),
                'shipping_total' => $cart->get_shipping_total(),
                'shipping_tax' => $cart->get_shipping_tax(),
                'coupon_count' => count($cart->get_applied_coupons()),
                'fee_count' => count($cart->get_fees()),
                'shipping_count' => $cart->needs_shipping() ? 1 : 0,
                'tax_line_count' => count($cart->get_taxes()),
            ],
            self::configuredId(),
            self::EXPECTED_CURRENCY,
            self::EXPECTED_TOTAL
        );
    }

    /**
     * @return string[]
     */
    public static function orderInvariantFailures(WC_Order $order): array
    {
        return self::orderInvariantFailuresForProductId(
            $order,
            self::configuredId()
        );
    }

    /**
     * @return string[]
     */
    public static function acceptedOrderInvariantFailures(
        WC_Order $order
    ): array {
        $productId = OrderMetadata::acceptedReadingProductId($order);
        if (
            $productId <= 0
            || self::EXPECTED_SKU
                !== OrderMetadata::acceptedReadingProductSku($order)
        ) {
            return ['reading_product_evidence'];
        }

        return self::orderInvariantFailuresForProductId($order, $productId);
    }

    /**
     * @return string[]
     */
    private static function orderInvariantFailuresForProductId(
        WC_Order $order,
        int $productId
    ): array
    {
        $items = $order->get_items('line_item');
        $item = 1 === count($items) ? reset($items) : null;
        $hasExpectedItemObject = $item instanceof WC_Order_Item_Product;

        return CommerceInvariant::failures(
            [
                'item_count' => count($items),
                'product_id' => $hasExpectedItemObject ? $item->get_product_id() : null,
                'variation_id' => $hasExpectedItemObject ? $item->get_variation_id() : null,
                'quantity' => $hasExpectedItemObject ? $item->get_quantity() : null,
                'currency' => $order->get_currency(),
                'line_subtotal' => $hasExpectedItemObject ? $item->get_subtotal() : null,
                'line_total' => $hasExpectedItemObject ? $item->get_total() : null,
                'line_subtotal_tax' => $hasExpectedItemObject
                    ? $item->get_subtotal_tax()
                    : null,
                'line_total_tax' => $hasExpectedItemObject ? $item->get_total_tax() : null,
                'subtotal' => $order->get_subtotal(),
                'contents_total' => $order->get_subtotal() - $order->get_discount_total(),
                'total' => $order->get_total(),
                'subtotal_tax' => $hasExpectedItemObject ? $item->get_subtotal_tax() : null,
                'tax_total' => $order->get_total_tax(),
                'discount_total' => $order->get_discount_total(),
                'discount_tax' => $order->get_discount_tax(),
                'fee_total' => $order->get_total_fees(),
                'fee_tax' => self::sumOrderItemTaxes($order, 'fee'),
                'shipping_total' => $order->get_shipping_total(),
                'shipping_tax' => $order->get_shipping_tax(),
                'coupon_count' => count($order->get_items('coupon')),
                'fee_count' => count($order->get_items('fee')),
                'shipping_count' => count($order->get_items('shipping')),
                'tax_line_count' => count($order->get_items('tax')),
            ],
            $productId,
            self::EXPECTED_CURRENCY,
            self::EXPECTED_TOTAL
        );
    }

    /**
     * @return array<string, bool>
     */
    public static function healthChecks(): array
    {
        $product = self::get();

        return [
            'configured_id' => self::configuredId() > 0,
            'matching_sku' => $product instanceof WC_Product,
            'published' => $product instanceof WC_Product && 'publish' === $product->get_status(),
            'simple' => $product instanceof WC_Product && $product->is_type('simple'),
            'virtual' => $product instanceof WC_Product && $product->is_virtual(),
            'sold_individually' => $product instanceof WC_Product && $product->is_sold_individually(),
            'base_purchasable' => $product instanceof WC_Product
                && 'publish' === $product->get_status()
                && '' !== (string) $product->get_price(),
            'in_stock' => $product instanceof WC_Product && $product->is_in_stock(),
            'price' => $product instanceof WC_Product
                && CommerceInvariant::decimalEquals(
                    $product->get_price('edit'),
                    self::EXPECTED_TOTAL
                ),
            'regular_price' => $product instanceof WC_Product
                && CommerceInvariant::decimalEquals(
                    $product->get_regular_price('edit'),
                    self::EXPECTED_TOTAL
                ),
            'not_on_sale' => $product instanceof WC_Product
                && '' === (string) $product->get_sale_price('edit')
                && null === $product->get_date_on_sale_from('edit')
                && null === $product->get_date_on_sale_to('edit'),
            'non_taxable' => $product instanceof WC_Product
                && 'none' === (string) $product->get_tax_status('edit'),
            'currency' => self::EXPECTED_CURRENCY === get_woocommerce_currency(),
            'global_coupons_disabled' => 'yes' !== get_option('woocommerce_enable_coupons'),
            'runtime_tax_and_coupon_guards' => ProductPolicy::runtimeGuardsRegistered(),
            'runtime_checkout_guards' => CheckoutGuard::runtimeGuardsRegistered(),
            'checkout_terms_lifecycle' => CheckoutTerms::configurationIsValid(),
            'billing_email_confirmation' =>
                BillingEmailConfirmation::configurationIsValid(),
            'access_email_bridge' => AccessEmail::configurationIsValid(),
            'transactional_email_transport_verified' =>
                AccessEmail::mailTransportIsVerified(),
        ];
    }

    public static function configurationIsValid(): bool
    {
        return ! in_array(false, self::healthChecks(), true);
    }

    private static function sumOrderItemTaxes(WC_Order $order, string $itemType): string
    {
        $taxTotal = 0.0;

        foreach ($order->get_items($itemType) as $item) {
            if (is_callable([$item, 'get_total_tax'])) {
                $taxTotal += (float) $item->get_total_tax();
            }
        }

        return (string) $taxTotal;
    }
}
