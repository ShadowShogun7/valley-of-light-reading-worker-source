<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WC_Cart;
use WC_Product;

final class DirectCheckout
{
    private const QUERY_VAR = 'vol_start_reading';
    private const CACHE_BYPASS_PARAM = 'purchase';
    private const CACHE_BYPASS_VALUE = 'reading';

    public function register(): void
    {
        add_action('init', [self::class, 'addRewriteRule']);
        add_filter('query_vars', [$this, 'addQueryVar']);
        add_action('template_redirect', [$this, 'redirectToCheckout'], 1);
    }

    public static function addRewriteRule(): void
    {
        add_rewrite_rule(
            '^start-reading/?$',
            'index.php?' . self::QUERY_VAR . '=1',
            'top'
        );
    }

    /**
     * @param string[] $queryVars
     * @return string[]
     */
    public function addQueryVar(array $queryVars): array
    {
        $queryVars[] = self::QUERY_VAR;

        return $queryVars;
    }

    public function redirectToCheckout(): void
    {
        if ('1' !== (string) get_query_var(self::QUERY_VAR)) {
            return;
        }

        header('X-Robots-Tag: noindex, nofollow, noarchive', true);

        if ('GET' !== strtoupper((string) ($_SERVER['REQUEST_METHOD'] ?? 'GET'))) {
            status_header(405);
            header('Allow: GET');
            exit;
        }

        if (
            self::CACHE_BYPASS_VALUE
            !== sanitize_key(wp_unslash((string) ($_GET[self::CACHE_BYPASS_PARAM] ?? '')))
        ) {
            wp_safe_redirect(
                add_query_arg(
                    self::CACHE_BYPASS_PARAM,
                    self::CACHE_BYPASS_VALUE,
                    home_url('/start-reading/')
                ),
                302,
                'Vale of Light Commerce Bridge'
            );
            exit;
        }

        if (! defined('DONOTCACHEPAGE')) {
            define('DONOTCACHEPAGE', true);
        }

        nocache_headers();
        $this->enforceRateLimit();

        $product = $this->readingProduct();
        if (! $product instanceof WC_Product || ! $product->is_purchasable()) {
            wp_die(
                esc_html__('目前暫時無法購買完整關係解讀，請稍後再試或聯絡客服。', 'vale-of-light-commerce-bridge'),
                esc_html__('解讀暫時無法購買', 'vale-of-light-commerce-bridge'),
                ['response' => 503]
            );
        }

        if (null === WC()->cart && function_exists('wc_load_cart')) {
            wc_load_cart();
        }

        if (null === WC()->cart) {
            wp_die(
                esc_html__('目前無法準備結帳，請重新整理後再試一次。', 'vale-of-light-commerce-bridge'),
                esc_html__('結帳暫時無法使用', 'vale-of-light-commerce-bridge'),
                ['response' => 503]
            );
        }

        if (! $this->normalizeCart(WC()->cart, $product)) {
            wp_die(
                esc_html__('目前無法準備結帳，請重新整理後再試一次。', 'vale-of-light-commerce-bridge'),
                esc_html__('結帳暫時無法使用', 'vale-of-light-commerce-bridge'),
                ['response' => 503]
            );
        }

        WC()->cart->calculate_totals();
        WC()->cart->set_session();
        if (null !== WC()->session) {
            WC()->session->set_customer_session_cookie(true);
        }

        wp_safe_redirect(wc_get_checkout_url(), 302, 'Vale of Light Commerce Bridge');
        exit;
    }

    private function readingProduct(): ?WC_Product
    {
        return ReadingProduct::get();
    }

    private function normalizeCart(WC_Cart $cart, WC_Product $product): bool
    {
        $items = $cart->get_cart();
        $readingItemKey = null;

        foreach ($items as $cartItemKey => $cartItem) {
            if ($product->get_id() === (int) ($cartItem['product_id'] ?? 0)) {
                $readingItemKey = (string) $cartItemKey;
                break;
            }
        }

        if (null === $readingItemKey) {
            $addedItemKey = $cart->add_to_cart($product->get_id(), 1);
            if (! is_string($addedItemKey) || '' === $addedItemKey) {
                return false;
            }

            $readingItemKey = $addedItemKey;
        } elseif (! $cart->set_quantity($readingItemKey, 1, false)) {
            return false;
        }

        foreach (array_keys($cart->get_cart()) as $cartItemKey) {
            if ($readingItemKey !== (string) $cartItemKey) {
                $cart->remove_cart_item((string) $cartItemKey);
            }
        }

        $cart->remove_coupons();

        return ReadingProduct::cartHasExpectedShape($cart);
    }

    private function enforceRateLimit(): void
    {
        $clientAddress = class_exists('WC_Geolocation')
            ? (string) \WC_Geolocation::get_ip_address()
            : '';

        if ('' === $clientAddress) {
            return;
        }

        $rateKey = 'vol_checkout_start_' . substr(
            hash_hmac('sha256', $clientAddress, wp_salt('nonce')),
            0,
            32
        );
        $attempts = (int) get_transient($rateKey);

        if ($attempts >= 20) {
            header('Retry-After: 60');
            wp_die(
                esc_html__('結帳請求過於頻繁，請等待一分鐘後再試。', 'vale-of-light-commerce-bridge'),
                esc_html__('請稍候', 'vale-of-light-commerce-bridge'),
                ['response' => 429]
            );
        }

        set_transient($rateKey, $attempts + 1, MINUTE_IN_SECONDS);
    }
}
