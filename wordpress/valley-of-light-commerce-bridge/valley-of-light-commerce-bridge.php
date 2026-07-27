<?php
/**
 * Plugin Name: Vale of Light Commerce Bridge
 * Description: Fixed-product checkout and post-payment handoff for the Vale of Light relationship reading.
 * Version: 0.3.0
 * Requires at least: 6.5
 * Requires PHP: 8.1
 * Requires Plugins: woocommerce
 * WC requires at least: 8.9
 * Author: Vale of Light
 * Text Domain: vale-of-light-commerce-bridge
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

define('VOL_COMMERCE_BRIDGE_VERSION', '0.3.0');
define('VOL_COMMERCE_BRIDGE_FILE', __FILE__);
define('VOL_COMMERCE_BRIDGE_DIR', plugin_dir_path(__FILE__));

require_once VOL_COMMERCE_BRIDGE_DIR . 'src/CommerceInvariant.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/CheckoutTerms.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/AccessEmailPolicy.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/ReadingProduct.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/BillingEmailConfirmation.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/ProductPolicy.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/LaunchGate.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/DirectCheckout.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/CartPolicy.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/CheckoutGuard.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/OrderMetadata.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/ThankYouMessage.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/AccessEmail.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/HealthStatus.php';
require_once VOL_COMMERCE_BRIDGE_DIR . 'src/PrivacyPolicy.php';

use ValeOfLight\CommerceBridge\CartPolicy;
use ValeOfLight\CommerceBridge\AccessEmail;
use ValeOfLight\CommerceBridge\BillingEmailConfirmation;
use ValeOfLight\CommerceBridge\CheckoutGuard;
use ValeOfLight\CommerceBridge\DirectCheckout;
use ValeOfLight\CommerceBridge\HealthStatus;
use ValeOfLight\CommerceBridge\LaunchGate;
use ValeOfLight\CommerceBridge\OrderMetadata;
use ValeOfLight\CommerceBridge\PrivacyPolicy;
use ValeOfLight\CommerceBridge\ProductPolicy;
use ValeOfLight\CommerceBridge\ThankYouMessage;

function vol_commerce_bridge_boot(): void
{
    if (! class_exists('WooCommerce')) {
        add_action(
            'admin_notices',
            static function (): void {
                echo '<div class="notice notice-error"><p>';
                echo esc_html__('Vale of Light Commerce Bridge requires WooCommerce.', 'vale-of-light-commerce-bridge');
                echo '</p></div>';
            }
        );

        return;
    }

    (new ProductPolicy())->register();
    (new BillingEmailConfirmation())->register();
    (new AccessEmail())->register();
    (new LaunchGate())->register();
    (new DirectCheckout())->register();
    (new CartPolicy())->register();
    (new CheckoutGuard())->register();
    (new OrderMetadata())->register();
    (new ThankYouMessage())->register();
    (new HealthStatus())->register();
    (new PrivacyPolicy())->register();
}
add_action('plugins_loaded', 'vol_commerce_bridge_boot');

register_activation_hook(
    __FILE__,
    static function (): void {
        if (false === get_option('vol_reading_product_id', false)) {
            add_option('vol_reading_product_id', 0, '', false);
        }
        if (false === get_option('vol_commerce_launch_enabled', false)) {
            add_option('vol_commerce_launch_enabled', 'no', '', false);
        }

        DirectCheckout::addRewriteRule();
        flush_rewrite_rules(false);
    }
);

register_deactivation_hook(
    __FILE__,
    static function (): void {
        flush_rewrite_rules(false);
    }
);
