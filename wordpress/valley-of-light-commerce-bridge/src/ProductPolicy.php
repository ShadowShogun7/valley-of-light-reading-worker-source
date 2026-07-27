<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WC_Cart;
use WC_Product;

final class ProductPolicy
{
    public function register(): void
    {
        add_filter(
            'woocommerce_product_get_tax_status',
            [self::class, 'filterTaxStatus'],
            PHP_INT_MAX,
            2
        );
        add_filter(
            'woocommerce_product_is_taxable',
            [self::class, 'filterTaxable'],
            PHP_INT_MAX,
            2
        );
        add_filter(
            'woocommerce_coupon_is_valid_for_product',
            [self::class, 'filterCouponForProduct'],
            PHP_INT_MAX,
            4
        );
        add_filter(
            'woocommerce_coupon_is_valid',
            [self::class, 'filterCouponForCart'],
            PHP_INT_MAX,
            3
        );
        add_filter(
            'woocommerce_coupons_enabled',
            [self::class, 'filterCouponsEnabled'],
            PHP_INT_MAX
        );
        add_action(
            'woocommerce_before_product_object_save',
            [self::class, 'enforceBeforeSave'],
            PHP_INT_MAX,
            2
        );
        add_action('init', [self::class, 'reconcileConfiguredProduct'], 20);
    }

    public static function filterTaxStatus(string $taxStatus, WC_Product $product): string
    {
        return self::isReadingProduct($product) ? 'none' : $taxStatus;
    }

    public static function filterTaxable(bool $taxable, WC_Product $product): bool
    {
        return self::isReadingProduct($product) ? false : $taxable;
    }

    public static function filterCouponForProduct(
        bool $valid,
        WC_Product $product,
        mixed $coupon,
        array $values = []
    ): bool {
        return self::isReadingProduct($product) ? false : $valid;
    }

    public static function filterCouponForCart(
        bool $valid,
        mixed $coupon,
        mixed $discounts = null
    ): bool {
        return self::currentCartContainsReading() ? false : $valid;
    }

    public static function filterCouponsEnabled(bool $enabled): bool
    {
        return self::currentCartContainsReading() ? false : $enabled;
    }

    public static function enforceBeforeSave(WC_Product $product, mixed $dataStore = null): void
    {
        if (! self::isReadingProduct($product)) {
            return;
        }

        self::applyStoredPolicy($product);
    }

    public static function reconcileConfiguredProduct(): void
    {
        $productId = ReadingProduct::configuredId();
        if ($productId <= 0) {
            return;
        }

        $product = wc_get_product($productId);
        if (! $product instanceof WC_Product || ! self::storedPolicyNeedsUpdate($product)) {
            return;
        }

        self::applyStoredPolicy($product);
        try {
            $product->save();
        } catch (\Throwable $error) {
            if (function_exists('wc_get_logger')) {
                wc_get_logger()->error(
                    'Unable to reconcile the fixed reading product tax and sale policy.',
                    [
                        'source' => 'vale-of-light-commerce-bridge',
                        'product_id' => $productId,
                        'exception' => get_class($error),
                    ]
                );
            }
        }
    }

    public static function runtimeGuardsRegistered(): bool
    {
        return false !== has_filter(
            'woocommerce_product_get_tax_status',
            [self::class, 'filterTaxStatus']
        )
            && false !== has_filter(
                'woocommerce_product_is_taxable',
                [self::class, 'filterTaxable']
            )
            && false !== has_filter(
                'woocommerce_coupon_is_valid_for_product',
                [self::class, 'filterCouponForProduct']
            )
            && false !== has_filter(
                'woocommerce_coupon_is_valid',
                [self::class, 'filterCouponForCart']
            )
            && false !== has_filter(
                'woocommerce_coupons_enabled',
                [self::class, 'filterCouponsEnabled']
            )
            && false !== has_action(
                'woocommerce_before_product_object_save',
                [self::class, 'enforceBeforeSave']
            );
    }

    private static function currentCartContainsReading(): bool
    {
        if (! function_exists('WC')) {
            return false;
        }

        $cart = WC()->cart ?? null;

        return $cart instanceof WC_Cart && ReadingProduct::cartContainsReading($cart);
    }

    private static function isReadingProduct(WC_Product $product): bool
    {
        return ReadingProduct::configuredId() > 0
            && ReadingProduct::configuredId() === $product->get_id();
    }

    private static function storedPolicyNeedsUpdate(WC_Product $product): bool
    {
        return 'none' !== (string) $product->get_tax_status('edit')
            || '' !== (string) $product->get_sale_price('edit')
            || null !== $product->get_date_on_sale_from('edit')
            || null !== $product->get_date_on_sale_to('edit')
            || (
                '' !== (string) $product->get_regular_price('edit')
                && ! CommerceInvariant::decimalEquals(
                    $product->get_price('edit'),
                    (string) $product->get_regular_price('edit')
                )
            );
    }

    private static function applyStoredPolicy(WC_Product $product): void
    {
        $product->set_tax_status('none');
        $product->set_sale_price('');
        $product->set_date_on_sale_from(null);
        $product->set_date_on_sale_to(null);

        $regularPrice = (string) $product->get_regular_price('edit');
        if ('' !== $regularPrice) {
            $product->set_price($regularPrice);
        }
    }
}
