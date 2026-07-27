<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WP_REST_Request;
use WP_REST_Response;

final class HealthStatus
{
    public function register(): void
    {
        add_action('rest_api_init', [$this, 'registerRoute']);
    }

    public function registerRoute(): void
    {
        register_rest_route(
            'vale-of-light/v1',
            '/commerce-health',
            [
                'methods' => 'POST',
                'callback' => [$this, 'respond'],
                'permission_callback' => static fn (): bool => current_user_can('manage_woocommerce'),
            ]
        );
    }

    public function respond(WP_REST_Request $request): WP_REST_Response
    {
        $checks = ReadingProduct::healthChecks();
        $checks['guest_checkout'] = 'yes' === get_option('woocommerce_enable_guest_checkout');
        $checks['account_creation_disabled'] =
            'yes' !== get_option('woocommerce_enable_signup_and_login_from_checkout')
            && 'yes' !== get_option('woocommerce_enable_myaccount_registration');
        $checks['checkout_page'] =
            wc_get_page_id('checkout') > 0
            && 'publish' === get_post_status(wc_get_page_id('checkout'));
        $checks['terms_page'] = wc_terms_and_conditions_page_id() > 0;
        $checks['launch_enabled'] = LaunchGate::isEnabled();

        $response = new WP_REST_Response(
            [
                'checkout_path' => '/start-reading/',
                'plugin_version' => VOL_COMMERCE_BRIDGE_VERSION,
                'ready' => ! in_array(false, $checks, true),
                'checks' => $checks,
                'product_id' => ReadingProduct::configuredId(),
                'checkout_terms_current_version' => CheckoutTerms::currentVersion(),
                'checkout_terms_payment_eligible_versions' =>
                    CheckoutTerms::paymentEligibleVersions(),
            ]
        );
        $response->header('Cache-Control', 'no-store, private, max-age=0');

        return $response;
    }
}
