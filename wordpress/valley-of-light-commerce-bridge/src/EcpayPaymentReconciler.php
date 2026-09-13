<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use Throwable;
use WC_Order;

final class EcpayPaymentQueryPolicy
{
    /**
     * @param array<string, mixed> $response
     * @return string[]
     */
    public static function failures(
        array $response,
        string $expectedMerchantTradeNo,
        string $expectedTotal
    ): array {
        $checks = [
            'merchant_trade_no' =>
                '' !== $expectedMerchantTradeNo
                && is_string($response['MerchantTradeNo'] ?? null)
                && hash_equals(
                    $expectedMerchantTradeNo,
                    (string) $response['MerchantTradeNo']
                ),
            'trade_status' =>
                '1' === (string) ($response['TradeStatus'] ?? ''),
            'trade_amount' => CommerceInvariant::decimalEquals(
                $response['TradeAmt'] ?? null,
                $expectedTotal
            ),
            'payment_type' =>
                'Credit_CreditCard' ===
                (string) ($response['PaymentType'] ?? ''),
            'trade_no' =>
                is_string($response['TradeNo'] ?? null)
                && '' !== trim((string) $response['TradeNo']),
            'payment_date' =>
                is_string($response['PaymentDate'] ?? null)
                && '' !== trim((string) $response['PaymentDate']),
        ];

        return array_keys(
            array_filter($checks, static fn (bool $passed): bool => ! $passed)
        );
    }
}

final class EcpayPaymentReconciler
{
    private const PAYMENT_METHOD = 'Wooecpay_Gateway_Credit';
    private const MERCHANT_TRADE_NO_KEY =
        '_wooecpay_payment_merchant_trade_no';
    private const ACTION = 'vol_ecpay_reconcile_paid_reading';
    private const ACTION_GROUP = 'vale-of-light-commerce';
    private const MAX_SCHEDULED_ATTEMPTS = 3;
    private static bool $registered = false;

    public function register(): void
    {
        add_action(
            'woocommerce_store_api_checkout_order_processed',
            [$this, 'scheduleStoreApiOrder'],
            20,
            1
        );
        add_action(
            'woocommerce_checkout_order_processed',
            [$this, 'scheduleClassicOrder'],
            20,
            3
        );
        add_action(
            self::ACTION,
            [$this, 'reconcileScheduled'],
            10,
            2
        );
        add_action(
            'woocommerce_thankyou',
            [$this, 'reconcileOnThankYou'],
            5,
            1
        );
        self::$registered = true;
    }

    public function scheduleStoreApiOrder(WC_Order $order): void
    {
        $this->schedule($order, 1, 120);
    }

    /**
     * @param array<string, mixed> $data
     */
    public function scheduleClassicOrder(
        int $orderId,
        array $data,
        WC_Order $order
    ): void {
        $this->schedule($order, 1, 120);
    }

    public function reconcileOnThankYou(int $orderId): void
    {
        $this->reconcile($orderId, 0);
    }

    public function reconcileScheduled(int $orderId, int $attempt): void
    {
        if ($this->reconcile($orderId, $attempt)) {
            return;
        }

        $order = wc_get_order($orderId);
        if (
            ! $order instanceof WC_Order
            || $order->is_paid()
            || $attempt >= self::MAX_SCHEDULED_ATTEMPTS
        ) {
            return;
        }

        $nextDelay = 1 === $attempt ? 300 : 900;
        $this->schedule($order, $attempt + 1, $nextDelay);
    }

    public static function runtimeHooksRegistered(): bool
    {
        return self::$registered;
    }

    private function reconcile(int $orderId, int $attempt): bool
    {
        $order = wc_get_order($orderId);
        if (! $order instanceof WC_Order || $order->is_paid()) {
            return $order instanceof WC_Order && $order->is_paid();
        }
        if ([] !== $this->eligibilityFailures($order)) {
            return false;
        }

        $lockKey = 'vol_ecpay_reconcile_lock_' . $orderId;
        if (! $this->acquireLock($lockKey)) {
            return false;
        }

        try {
            $response = $this->queryTrade($order);
            if (null === $response) {
                return false;
            }

            $merchantTradeNo = trim(
                (string) $order->get_meta(
                    self::MERCHANT_TRADE_NO_KEY,
                    true
                )
            );
            if (
                [] !== EcpayPaymentQueryPolicy::failures(
                    $response,
                    $merchantTradeNo,
                    (string) $order->get_total()
                )
            ) {
                return false;
            }

            $order->update_meta_data(
                '_vol_ecpay_reconciled_at',
                gmdate('c')
            );
            $order->update_meta_data(
                '_vol_ecpay_reconciliation_source',
                'verified-query-trade-info'
            );
            $order->add_order_note(
                __(
                    'ECPay server query verified payment after a delayed callback.',
                    'vale-of-light-commerce-bridge'
                )
            );
            $order->save();
            $order->payment_complete(
                trim((string) $response['TradeNo'])
            );

            return $order->is_paid();
        } catch (Throwable $error) {
            $logger = function_exists('wc_get_logger')
                ? wc_get_logger()
                : null;
            if (null !== $logger) {
                $logger->warning(
                    'ECPay payment reconciliation did not complete.',
                    [
                        'source' => 'vale-of-light-commerce-bridge',
                        'order_id' => $orderId,
                        'attempt' => $attempt,
                        'error_type' => get_class($error),
                    ]
                );
            }

            return false;
        } finally {
            delete_option($lockKey);
        }
    }

    /**
     * @return string[]
     */
    private function eligibilityFailures(WC_Order $order): array
    {
        $failures = [];
        if (self::PAYMENT_METHOD !== $order->get_payment_method()) {
            $failures[] = 'payment_method';
        }
        if (! ReadingProduct::orderContainsReading($order)) {
            $failures[] = 'reading_order';
        }

        return array_values(
            array_unique(
                array_merge(
                    $failures,
                    ReadingProduct::acceptedOrderInvariantFailures($order),
                    OrderMetadata::acceptedOrderEvidenceFailures($order),
                    BillingEmailConfirmation::evidenceFailures($order)
                ),
                SORT_STRING
            )
        );
    }

    /**
     * @return null|array<string, mixed>
     */
    private function queryTrade(WC_Order $order): ?array
    {
        if (
            ! class_exists(
                '\Helpers\Payment\Wooecpay_Payment_Helper'
            )
            || ! class_exists('\Ecpay\Sdk\Factories\Factory')
        ) {
            return null;
        }

        $merchantTradeNo = trim(
            (string) $order->get_meta(
                self::MERCHANT_TRADE_NO_KEY,
                true
            )
        );
        if ('' === $merchantTradeNo) {
            return null;
        }

        $helper = new \Helpers\Payment\Wooecpay_Payment_Helper();
        $api = $helper->get_ecpay_payment_api_info('QueryTradeInfo');
        if (
            ! is_array($api)
            || ! is_string($api['merchant_id'] ?? null)
            || ! is_string($api['hashKey'] ?? null)
            || ! is_string($api['hashIv'] ?? null)
            || ! is_string($api['action'] ?? null)
        ) {
            return null;
        }

        $factory = new \Ecpay\Sdk\Factories\Factory(
            [
                'hashKey' => $api['hashKey'],
                'hashIv' => $api['hashIv'],
            ]
        );
        $service = $factory->create(
            'PostWithCmvVerifiedEncodedStrResponseService'
        );
        $response = $service->post(
            [
                'MerchantID' => $api['merchant_id'],
                'MerchantTradeNo' => $merchantTradeNo,
                'TimeStamp' => time(),
            ],
            $api['action']
        );

        return is_array($response) ? $response : null;
    }

    private function schedule(
        WC_Order $order,
        int $attempt,
        int $delay
    ): void {
        if (
            $order->is_paid()
            || self::PAYMENT_METHOD !== $order->get_payment_method()
            || ! ReadingProduct::orderContainsReading($order)
        ) {
            return;
        }

        $args = [$order->get_id(), $attempt];
        if (
            function_exists('as_has_scheduled_action')
            && function_exists('as_schedule_single_action')
        ) {
            if (
                ! as_has_scheduled_action(
                    self::ACTION,
                    $args,
                    self::ACTION_GROUP
                )
            ) {
                as_schedule_single_action(
                    time() + $delay,
                    self::ACTION,
                    $args,
                    self::ACTION_GROUP,
                    true
                );
            }

            return;
        }

        if (
            ! wp_next_scheduled(self::ACTION, $args)
        ) {
            wp_schedule_single_event(
                time() + $delay,
                self::ACTION,
                $args
            );
        }
    }

    private function acquireLock(string $lockKey): bool
    {
        if (add_option($lockKey, (string) time(), '', false)) {
            return true;
        }

        $createdAt = (int) get_option($lockKey, 0);
        if ($createdAt <= 0 || $createdAt > time() - 300) {
            return false;
        }

        delete_option($lockKey);

        return add_option($lockKey, (string) time(), '', false);
    }
}
