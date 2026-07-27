<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WC_Product;

final class LaunchGate
{
    private const OPTION = 'vol_commerce_launch_enabled';

    public function register(): void
    {
        add_action('init', [$this, 'registerSetting']);
        add_filter('woocommerce_is_purchasable', [$this, 'filterPurchasable'], 20, 2);
    }

    public function registerSetting(): void
    {
        register_setting(
            'general',
            self::OPTION,
            [
                'type' => 'string',
                'default' => 'no',
                'sanitize_callback' => static fn (mixed $value): string =>
                    'yes' === (string) $value ? 'yes' : 'no',
                'show_in_rest' => [
                    'schema' => [
                        'type' => 'string',
                        'enum' => ['yes', 'no'],
                    ],
                ],
            ]
        );
    }

    public function filterPurchasable(bool $purchasable, WC_Product $product): bool
    {
        if (ReadingProduct::configuredId() !== $product->get_id()) {
            return $purchasable;
        }

        return $purchasable
            && self::allowsPayment();
    }

    public static function isEnabled(): bool
    {
        return 'yes' === get_option(self::OPTION, 'no');
    }

    public static function allowsPayment(): bool
    {
        return self::isEnabled()
            && ReadingProduct::configurationIsValid();
    }
}
