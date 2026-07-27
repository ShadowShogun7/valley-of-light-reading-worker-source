<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use Automattic\WooCommerce\StoreApi\Exceptions\RouteException;
use Exception;
use WC_Cart;
use WC_Order;
use WP_Error;

final class CheckoutGuard
{
    private const ERROR_CODE = 'vol_reading_checkout_invariant_failed';

    public function register(): void
    {
        add_action(
            'woocommerce_after_checkout_validation',
            [self::class, 'validateClassicCart'],
            PHP_INT_MAX,
            2
        );
        add_action(
            'woocommerce_checkout_order_processed',
            [self::class, 'validateClassicOrder'],
            PHP_INT_MAX,
            3
        );
        add_action(
            'woocommerce_store_api_checkout_order_processed',
            [self::class, 'validateStoreApiOrder'],
            PHP_INT_MAX
        );
        add_action(
            'woocommerce_before_pay_action',
            [self::class, 'validatePaymentRetry'],
            PHP_INT_MAX
        );
    }

    /**
     * @param array<string, mixed> $data
     */
    public static function validateClassicCart(array $data, WP_Error $errors): void
    {
        $cart = WC()->cart ?? null;
        if (! $cart instanceof WC_Cart || ! ReadingProduct::cartContainsReading($cart)) {
            return;
        }

        $cart->calculate_totals();
        if ([] === ReadingProduct::cartInvariantFailures($cart)) {
            return;
        }

        $errors->add(self::ERROR_CODE, self::errorMessage());
    }

    /**
     * @param array<string, mixed> $data
     * @throws Exception When a reading order no longer matches the fixed commercial contract.
     */
    public static function validateClassicOrder(int $orderId, array $data, WC_Order $order): void
    {
        if (! ReadingProduct::orderContainsReading($order)) {
            return;
        }

        self::assertOrderEligible($order);
    }

    /**
     * @throws RouteException When a Store API reading order is not safe to pay.
     * @throws Exception When the installed WooCommerce version lacks RouteException.
     */
    public static function validateStoreApiOrder(WC_Order $order): void
    {
        if (! ReadingProduct::orderContainsReading($order)) {
            return;
        }

        $status = self::paymentEnvironmentIsEligible() ? 409 : 503;
        $failures = self::orderEligibilityFailures($order);
        if ([] === $failures) {
            return;
        }

        if (class_exists(RouteException::class)) {
            throw new RouteException(
                self::ERROR_CODE,
                self::errorMessageForFailures($failures),
                $status
            );
        }

        throw new Exception(self::errorMessageForFailures($failures));
    }

    public static function validatePaymentRetry(WC_Order $order): void
    {
        if (! ReadingProduct::orderContainsReading($order)) {
            return;
        }

        $status = self::paymentEnvironmentIsEligible() ? 409 : 503;
        $failures = self::orderEligibilityFailures($order);
        if ([] === $failures) {
            return;
        }

        wp_die(
            esc_html(self::errorMessageForFailures($failures)),
            esc_html__('付款安全檢查未通過', 'vale-of-light-commerce-bridge'),
            ['response' => $status]
        );
    }

    public static function runtimeGuardsRegistered(): bool
    {
        return false !== has_action(
            'woocommerce_after_checkout_validation',
            [self::class, 'validateClassicCart']
        )
            && false !== has_action(
                'woocommerce_checkout_order_processed',
                [self::class, 'validateClassicOrder']
            )
            && false !== has_action(
                'woocommerce_store_api_checkout_order_processed',
                [self::class, 'validateStoreApiOrder']
            )
            && false !== has_action(
                'woocommerce_before_pay_action',
                [self::class, 'validatePaymentRetry']
            );
    }

    /**
     * @throws Exception When the order is not safe to send to a payment gateway.
     */
    private static function assertOrderEligible(WC_Order $order): void
    {
        $failures = self::orderEligibilityFailures($order);
        if ([] !== $failures) {
            throw new Exception(self::errorMessageForFailures($failures));
        }
    }

    /**
     * @return string[]
     */
    private static function orderEligibilityFailures(WC_Order $order): array
    {
        $failures = ReadingProduct::orderInvariantFailures($order);

        if (! self::paymentEnvironmentIsEligible()) {
            $failures[] = 'payment_environment';
        }

        return array_values(
            array_unique(
                array_merge(
                    $failures,
                    OrderMetadata::acceptanceEvidenceFailures($order),
                    BillingEmailConfirmation::evidenceFailures($order)
                ),
                SORT_STRING
            )
        );
    }

    private static function paymentEnvironmentIsEligible(): bool
    {
        return LaunchGate::allowsPayment()
            && CheckoutTerms::configurationIsValid();
    }

    private static function errorMessage(): string
    {
        return __(
            '這筆完整關係解讀目前無法安全送出付款，可能是結帳內容、金額或服務設定已變更。系統尚未把本次付款送往金流；請重新從購買按鈕進入結帳，若仍出現此訊息請聯絡客服。',
            'vale-of-light-commerce-bridge'
        );
    }

    /**
     * @param string[] $failures
     */
    private static function errorMessageForFailures(array $failures): string
    {
        if (
            [] !== $failures
            && [] === array_filter(
                $failures,
                static fn (string $failure): bool =>
                    ! BillingEmailConfirmation::isEvidenceFailure($failure)
            )
        ) {
            return BillingEmailConfirmation::orderEvidenceErrorMessage();
        }

        return self::errorMessage();
    }
}
