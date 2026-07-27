<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

final class PrivacyPolicy
{
    public function register(): void
    {
        add_action('admin_init', [$this, 'suggestContent']);
    }

    public function suggestContent(): void
    {
        if (! function_exists('wp_add_privacy_policy_content')) {
            return;
        }

        wp_add_privacy_policy_content(
            esc_html__('Vale of Light Commerce Bridge', 'vale-of-light-commerce-bridge'),
            wp_kses_post(
                '<p>'
                . esc_html__(
                    '本網站會在結帳時要求再次輸入付款 Email，並在伺服器確認兩次輸入完全相同。WooCommerce 訂單只保存以網站安全金鑰產生的 Email 確認摘要、確認時間與確認來源，不保存第二份明文 Email；訂單本身仍會依 WooCommerce 的正常流程保存付款 Email。本網站也會保存本次結帳所呈現的條款版本、呈現時間與固定解讀商品識別，供訂單處理、爭議處理及法令遵循使用。此橋接外掛不保存出生資料、關係問卷或產生的解讀內容；相關資料由獨立的安全解讀應用程式依其隱私政策處理。訂單資料的保存與刪除依本網站既有的 WooCommerce 訂單保存政策及法定義務辦理。',
                    'vale-of-light-commerce-bridge'
                )
                . '</p>'
            )
        );
    }
}
