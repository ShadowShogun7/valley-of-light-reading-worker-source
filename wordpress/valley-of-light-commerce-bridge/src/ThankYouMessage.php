<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WC_Order;

final class ThankYouMessage
{
    public function register(): void
    {
        add_action('woocommerce_thankyou', [$this, 'render'], 8);
    }

    public function render(int $orderId): void
    {
        $order = wc_get_order($orderId);
        if (! $order instanceof WC_Order) {
            return;
        }

        if (! ReadingProduct::orderIsEligible($order)) {
            return;
        }

        $maskedEmail = $this->maskEmail((string) $order->get_billing_email());
        $status = (string) $order->get_status();

        if (in_array($status, ['processing', 'completed'], true)) {
            $title = __('付款已確認，我們正在寄出資料填寫連結', 'vale-of-light-commerce-bridge');
            $message = sprintf(
                /* translators: %s is a masked billing email address. */
                __('安全連結會寄到 %s，請留意收件匣與垃圾郵件匣。', 'vale-of-light-commerce-bridge'),
                $maskedEmail
            );
            $detail = __('完整解讀的製作時間會從你送出完整關係資料後開始計算。', 'vale-of-light-commerce-bridge');
        } elseif (in_array($status, ['pending', 'on-hold', 'checkout-draft'], true)) {
            $title = __('訂單已收到，正在等待綠界確認付款', 'vale-of-light-commerce-bridge');
            $message = sprintf(
                /* translators: %s is a masked billing email address. */
                __('付款確認後，安全資料填寫連結才會寄到 %s。ATM 與超商付款通常需要較長的入帳確認時間。', 'vale-of-light-commerce-bridge'),
                $maskedEmail
            );
            $detail = __('在收到付款確認信之前，不需要填寫出生或關係資料。', 'vale-of-light-commerce-bridge');
        } elseif (in_array($status, ['failed', 'cancelled', 'refunded'], true)) {
            $title = __('這筆訂單目前不會建立解讀', 'vale-of-light-commerce-bridge');
            $message = __('付款失敗、訂單取消或退款後，系統不會寄出資料填寫連結。', 'vale-of-light-commerce-bridge');
            $detail = __('如果你已被扣款但看到這個狀態，請保留訂單編號並聯絡客服。', 'vale-of-light-commerce-bridge');
        } else {
            $title = __('訂單狀態更新中', 'vale-of-light-commerce-bridge');
            $message = __('系統正在確認這筆訂單；只有綠界與 WooCommerce 確認付款後才會寄出資料填寫連結。', 'vale-of-light-commerce-bridge');
            $detail = __('請稍後查看付款信箱與訂單狀態。', 'vale-of-light-commerce-bridge');
        }
        ?>
        <section class="vol-reading-handoff" aria-labelledby="vol-reading-handoff-title">
            <h2 id="vol-reading-handoff-title">
                <?php echo esc_html($title); ?>
            </h2>
            <p>
                <?php echo esc_html($message); ?>
            </p>
            <p>
                <?php echo esc_html($detail); ?>
            </p>
        </section>
        <?php
    }

    private function maskEmail(string $email): string
    {
        if (! is_email($email)) {
            return esc_html__('你的付款信箱', 'vale-of-light-commerce-bridge');
        }

        [$local, $domain] = explode('@', $email, 2);
        $visible = function_exists('mb_substr') ? mb_substr($local, 0, 1) : substr($local, 0, 1);

        return $visible . str_repeat('•', max(3, min(8, strlen($local) - 1))) . '@' . $domain;
    }
}
