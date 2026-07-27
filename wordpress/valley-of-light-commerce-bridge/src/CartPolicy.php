<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WC_Cart;

final class CartPolicy
{
    public function register(): void
    {
        add_action('woocommerce_check_cart_items', [$this, 'validate']);
    }

    public function validate(): void
    {
        $cart = WC()->cart;
        if (
            ! $cart instanceof WC_Cart
            || ! ReadingProduct::cartContainsReading($cart)
            || ReadingProduct::cartHasExpectedShape($cart)
        ) {
            return;
        }

        wc_add_notice(
            esc_html__(
                '完整關係解讀必須單獨購買，且每筆訂單限購一份。請重新從購買按鈕進入結帳。',
                'vale-of-light-commerce-bridge'
            ),
            'error'
        );
    }
}
