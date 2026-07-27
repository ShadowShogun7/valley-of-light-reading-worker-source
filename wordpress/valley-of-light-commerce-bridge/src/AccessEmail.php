<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

use WC_Email;
use WC_Order;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

final class AccessEmail
{
    private const ROUTE_NAMESPACE = 'vale-of-light/v1';
    private const ROUTE_PATH = '/access-email';
    private const GRANT_ID_KEY = '_vol_access_grant_id';
    private const GRANT_EXPIRES_AT_KEY = '_vol_access_grant_expires_at';
    private const RESULT_READY_AT_KEY = '_vol_result_ready_at';
    private const IDEMPOTENCY_OPTION_PREFIX = 'vol_access_email_';

    /** @var array<int, string> */
    private static array $emailContexts = [];
    private static int $authorizedCompletionOrderId = 0;
    private static bool $normalizingStatus = false;

    public function register(): void
    {
        add_action('rest_api_init', [$this, 'registerRoute']);
        add_filter(
            'woocommerce_email_enabled_customer_processing_order',
            [self::class, 'filterCustomerEmailEnabled'],
            PHP_INT_MAX,
            3
        );
        add_filter(
            'woocommerce_email_enabled_customer_completed_order',
            [self::class, 'filterCustomerEmailEnabled'],
            PHP_INT_MAX,
            3
        );
        add_action(
            'woocommerce_email_after_order_table',
            [self::class, 'renderAccessLink'],
            20,
            4
        );
        add_filter(
            'woocommerce_email_subject_customer_processing_order',
            [self::class, 'filterSubject'],
            20,
            3
        );
        add_filter(
            'woocommerce_email_subject_customer_completed_order',
            [self::class, 'filterSubject'],
            20,
            3
        );
        add_filter(
            'woocommerce_email_heading_customer_processing_order',
            [self::class, 'filterHeading'],
            20,
            3
        );
        add_filter(
            'woocommerce_email_heading_customer_completed_order',
            [self::class, 'filterHeading'],
            20,
            3
        );
        add_filter(
            'woocommerce_payment_complete_order_status',
            [self::class, 'forcePaidReadingToProcessing'],
            PHP_INT_MAX,
            3
        );
        add_action(
            'woocommerce_order_status_changed',
            [self::class, 'preventPrematureCompletion'],
            1,
            4
        );
        add_filter(
            'woocommerce_order_actions',
            [self::class, 'addAdminResendAction'],
            10,
            2
        );
        add_action(
            'woocommerce_order_action_vol_resend_reading_access_email',
            [self::class, 'handleAdminResend']
        );
    }

    public function registerRoute(): void
    {
        register_rest_route(
            self::ROUTE_NAMESPACE,
            self::ROUTE_PATH,
            [
                'methods' => 'POST',
                'callback' => [$this, 'respond'],
                'permission_callback' => [$this, 'authorize'],
            ]
        );
    }

    public function authorize(WP_REST_Request $request): bool|WP_Error
    {
        if (! self::configurationIsValid()) {
            return new WP_Error(
                'vol_access_email_not_configured',
                __('安全通知服務尚未完成設定。', 'vale-of-light-commerce-bridge'),
                ['status' => 503]
            );
        }

        $body = (string) $request->get_body();
        if (
            ! AccessEmailPolicy::verifyNotificationSignature(
                $body,
                self::header($request, 'x-vol-timestamp'),
                self::header($request, 'x-vol-signature'),
                self::notificationSigningSecret(),
                time()
            )
        ) {
            return new WP_Error(
                'vol_access_email_invalid_signature',
                __('安全通知驗證失敗。', 'vale-of-light-commerce-bridge'),
                ['status' => 401]
            );
        }

        return true;
    }

    public function respond(WP_REST_Request $request): WP_REST_Response|WP_Error
    {
        $rawBody = (string) $request->get_body();
        try {
            $payload = json_decode(
                $rawBody,
                true,
                16,
                JSON_THROW_ON_ERROR
            );
        } catch (\Throwable) {
            return self::error(
                'vol_access_email_invalid_request',
                __('安全通知內容無效。', 'vale-of-light-commerce-bridge'),
                400
            );
        }
        if (
            ! is_array($payload)
            || [] !== AccessEmailPolicy::requestFailures($payload, time())
        ) {
            return self::error(
                'vol_access_email_invalid_request',
                __('安全通知內容無效。', 'vale-of-light-commerce-bridge'),
                400
            );
        }

        $order = wc_get_order((int) $payload['orderId']);
        if (
            ! $order instanceof WC_Order
            || ! self::orderIsDeliverable($order)
        ) {
            return self::error(
                'vol_access_email_order_not_eligible',
                __('訂單目前不符合安全通知條件。', 'vale-of-light-commerce-bridge'),
                409
            );
        }

        $grantResult = self::persistGrantReference(
            $order,
            (string) $payload['grantId'],
            (string) $payload['grantExpiresAt']
        );
        if (is_wp_error($grantResult)) {
            return $grantResult;
        }

        $requestHash = hash('sha256', $rawBody);
        $claim = self::claimIdempotency(
            (string) $payload['idempotencyKey'],
            $requestHash,
            $order->get_id(),
            (string) $payload['messageKind']
        );
        if (is_wp_error($claim)) {
            return $claim;
        }
        if ('sent' === ($claim['status'] ?? null)) {
            return self::success(
                (string) $payload['messageKind'],
                (string) $claim['provider_message_id'],
                true
            );
        }

        $providerMessageId = self::providerMessageId(
            (string) $payload['idempotencyKey'],
            $requestHash
        );
        $claimId = is_string($claim['claim_id'] ?? null)
            ? (string) $claim['claim_id']
            : '';
        if ('' === $claimId) {
            return self::error(
                'vol_access_email_claim_invalid',
                __('安全通知狀態無效。', 'vale-of-light-commerce-bridge'),
                503
            );
        }
        $sent = self::sendRequestedEmail(
            $order,
            (string) $payload['messageKind']
        );
        $finished = self::finishIdempotency(
            (string) $payload['idempotencyKey'],
            $requestHash,
            $claimId,
            $sent ? 'sent' : 'failed',
            $sent ? $providerMessageId : null
        );
        if (! $finished) {
            return self::error(
                'vol_access_email_state_conflict',
                __('安全通知狀態無法確認，請由客服檢查寄送紀錄。', 'vale-of-light-commerce-bridge'),
                503
            );
        }
        if (! $sent) {
            return self::error(
                'vol_access_email_send_failed',
                __('WooCommerce 未接受這封通知，系統稍後會重試。', 'vale-of-light-commerce-bridge'),
                503
            );
        }

        return self::success(
            (string) $payload['messageKind'],
            $providerMessageId,
            false
        );
    }

    public static function configurationIsValid(): bool
    {
        return [] === AccessEmailPolicy::configurationFailures(
            self::appBaseUrl(),
            self::accessSigningSecret(),
            self::notificationSigningSecret()
        )
            && self::runtimeHooksRegistered()
            && self::requiredCustomerEmailsEnabled()
            && self::mailTransportIsVerified();
    }

    public static function mailTransportIsVerified(): bool
    {
        return defined('VOL_EMAIL_TRANSPORT_VERIFIED')
            && true === constant('VOL_EMAIL_TRANSPORT_VERIFIED');
    }

    public static function runtimeHooksRegistered(): bool
    {
        return false !== has_filter(
            'woocommerce_email_enabled_customer_processing_order',
            [self::class, 'filterCustomerEmailEnabled']
        )
            && false !== has_filter(
                'woocommerce_email_enabled_customer_completed_order',
                [self::class, 'filterCustomerEmailEnabled']
            )
            && false !== has_action(
                'woocommerce_email_after_order_table',
                [self::class, 'renderAccessLink']
            )
            && false !== has_filter(
                'woocommerce_payment_complete_order_status',
                [self::class, 'forcePaidReadingToProcessing']
            )
            && false !== has_action(
                'woocommerce_order_status_changed',
                [self::class, 'preventPrematureCompletion']
            );
    }

    public static function filterCustomerEmailEnabled(
        bool $enabled,
        mixed $object,
        mixed $email = null
    ): bool {
        if (
            ! $object instanceof WC_Order
            || ! ReadingProduct::orderContainsReading($object)
        ) {
            return $enabled;
        }

        return $enabled && isset(self::$emailContexts[$object->get_id()]);
    }

    public static function forcePaidReadingToProcessing(
        string $status,
        int $orderId,
        mixed $order = null
    ): string {
        if (! $order instanceof WC_Order) {
            $order = wc_get_order($orderId);
        }

        return $order instanceof WC_Order
            && ReadingProduct::orderContainsReading($order)
            ? 'processing'
            : $status;
    }

    public static function preventPrematureCompletion(
        int $orderId,
        string $from,
        string $to,
        WC_Order $order
    ): void {
        if (
            self::$normalizingStatus
            || 'completed' !== $to
            || self::$authorizedCompletionOrderId === $orderId
            || ! ReadingProduct::orderContainsReading($order)
        ) {
            return;
        }

        self::$normalizingStatus = true;
        try {
            $order->update_status(
                'processing',
                __(
                    '完整關係解讀尚未完成；系統已保留訂單於處理中，完成後才會標記完成。',
                    'vale-of-light-commerce-bridge'
                ),
                true
            );
        } finally {
            self::$normalizingStatus = false;
        }
    }

    /**
     * @param array<string, string> $actions
     * @return array<string, string>
     */
    public static function addAdminResendAction(
        array $actions,
        mixed $order = null
    ): array
    {
        if (
            ! $order instanceof WC_Order
            || ! ReadingProduct::orderContainsReading($order)
        ) {
            return $actions;
        }

        $actions['vol_resend_reading_access_email'] = __(
            '重新寄送關係解讀安全連結',
            'vale-of-light-commerce-bridge'
        );

        return $actions;
    }

    public static function handleAdminResend(WC_Order $order): void
    {
        if (
            ! current_user_can('manage_woocommerce')
            || ! self::configurationIsValid()
            || ! self::orderIsDeliverable($order)
            || '' === self::accessUrlForOrder($order)
        ) {
            $order->add_order_note(
                __(
                    '安全連結未重新寄送：訂單狀態、存取授權或通知設定未通過安全檢查。',
                    'vale-of-light-commerce-bridge'
                )
            );

            return;
        }

        $sent = self::sendCoreEmail($order, 'access_recovery');
        $order->add_order_note(
            $sent
                ? __(
                    '已由管理員重新寄送現有的關係解讀安全連結。',
                    'vale-of-light-commerce-bridge'
                )
                : __(
                    '安全連結重新寄送失敗；請檢查 WooCommerce Email 與 SMTP 紀錄。',
                    'vale-of-light-commerce-bridge'
                )
        );
    }

    public static function renderAccessLink(
        WC_Order $order,
        bool $sentToAdmin,
        bool $plainText,
        mixed $email
    ): void {
        $messageKind = self::$emailContexts[$order->get_id()] ?? null;
        $emailId = is_object($email) && isset($email->id)
            ? (string) $email->id
            : '';
        if (
            $sentToAdmin
            || null === $messageKind
            || ! in_array(
                $emailId,
                ['customer_processing_order', 'customer_completed_order'],
                true
            )
            || ! ReadingProduct::orderContainsReading($order)
        ) {
            return;
        }

        $accessUrl = self::accessUrlForOrder($order);
        if ('' === $accessUrl) {
            return;
        }
        $copy = self::messageCopy($messageKind);
        if ($plainText) {
            echo "\n" . esc_html($copy['body']) . "\n";
            echo esc_url($accessUrl) . "\n\n";

            return;
        }
        ?>
        <div style="margin:28px 0;padding:24px;border:1px solid #d9b56d;border-radius:12px">
            <h2 style="margin-top:0"><?php echo esc_html($copy['heading']); ?></h2>
            <p><?php echo esc_html($copy['body']); ?></p>
            <p style="margin:24px 0 0">
                <a
                    href="<?php echo esc_url($accessUrl); ?>"
                    style="display:inline-block;padding:12px 20px;border-radius:999px;background:#d9b56d;color:#101726;text-decoration:none;font-weight:700"
                ><?php echo esc_html($copy['button']); ?></a>
            </p>
            <p style="font-size:12px;color:#666">
                <?php
                echo esc_html__(
                    '請勿轉寄此信；連結可開啟本訂單的私人資料與解讀。',
                    'vale-of-light-commerce-bridge'
                );
                ?>
            </p>
        </div>
        <?php
    }

    public static function filterSubject(
        string $subject,
        mixed $order,
        mixed $email = null
    ): string {
        if (! $order instanceof WC_Order) {
            return $subject;
        }
        $messageKind = self::$emailContexts[$order->get_id()] ?? null;

        return null === $messageKind
            ? $subject
            : self::messageCopy($messageKind)['subject'];
    }

    public static function filterHeading(
        string $heading,
        mixed $order,
        mixed $email = null
    ): string {
        if (! $order instanceof WC_Order) {
            return $heading;
        }
        $messageKind = self::$emailContexts[$order->get_id()] ?? null;

        return null === $messageKind
            ? $heading
            : self::messageCopy($messageKind)['heading'];
    }

    /**
     * @return array{heading:string,body:string,button:string,subject:string}
     */
    private static function messageCopy(string $messageKind): array
    {
        if ('result_ready' === $messageKind) {
            return [
                'heading' => __(
                    '你的完整關係解讀已完成',
                    'vale-of-light-commerce-bridge'
                ),
                'body' => __(
                    '你的解讀已完成。請使用付款後收到的同一個安全連結查看；之後再次開啟，也會回到同一份已鎖定的結果。',
                    'vale-of-light-commerce-bridge'
                ),
                'button' => __(
                    '查看完整關係解讀',
                    'vale-of-light-commerce-bridge'
                ),
                'subject' => __(
                    '你的完整關係解讀已完成',
                    'vale-of-light-commerce-bridge'
                ),
            ];
        }
        if ('access_recovery' === $messageKind) {
            return [
                'heading' => __(
                    '你的關係解讀安全連結',
                    'vale-of-light-commerce-bridge'
                ),
                'body' => __(
                    '請使用下方同一個安全連結繼續填寫資料，或回到已完成的解讀。',
                    'vale-of-light-commerce-bridge'
                ),
                'button' => __(
                    '重新開啟我的關係解讀',
                    'vale-of-light-commerce-bridge'
                ),
                'subject' => __(
                    '你的關係解讀安全連結',
                    'vale-of-light-commerce-bridge'
                ),
            ];
        }

        return [
            'heading' => __(
                '付款成功，請完成你的關係解讀資料',
                'vale-of-light-commerce-bridge'
            ),
            'body' => __(
                '付款已確認。請使用下方安全連結完成兩人的出生資料與關係問題；送出後資料會鎖定。',
                'vale-of-light-commerce-bridge'
            ),
            'button' => __(
                '開始填寫解讀資料',
                'vale-of-light-commerce-bridge'
            ),
            'subject' => __(
                '付款成功，請完成你的關係解讀資料',
                'vale-of-light-commerce-bridge'
            ),
        ];
    }

    private static function sendRequestedEmail(
        WC_Order $order,
        string $messageKind
    ): bool {
        if ('result_ready' === $messageKind) {
            $order->update_meta_data(self::RESULT_READY_AT_KEY, gmdate('c'));
            $order->save();
            if ('completed' !== $order->get_status()) {
                self::$authorizedCompletionOrderId = $order->get_id();
                try {
                    $order->update_status(
                        'completed',
                        __(
                            '完整關係解讀已安全儲存，訂單已完成。',
                            'vale-of-light-commerce-bridge'
                        ),
                        true
                    );
                } finally {
                    self::$authorizedCompletionOrderId = 0;
                }
            }
        } elseif (
            'intake_invitation' === $messageKind
            && 'completed' === $order->get_status()
            && '' === (string) $order->get_meta(
                self::RESULT_READY_AT_KEY,
                true
            )
        ) {
            self::$normalizingStatus = true;
            try {
                $order->update_status(
                    'processing',
                    __(
                        '付款已確認；訂單將在關係解讀完成後才標記完成。',
                        'vale-of-light-commerce-bridge'
                    ),
                    true
                );
            } finally {
                self::$normalizingStatus = false;
            }
        }

        return self::sendCoreEmail($order, $messageKind);
    }

    private static function sendCoreEmail(
        WC_Order $order,
        string $messageKind
    ): bool {
        $emailId = 'result_ready' === $messageKind
            || (
                'access_recovery' === $messageKind
                && 'completed' === $order->get_status()
            )
            ? 'customer_completed_order'
            : 'customer_processing_order';
        $mailer = WC()->mailer();
        $target = null;
        foreach ($mailer->get_emails() as $candidate) {
            if (
                $candidate instanceof WC_Email
                && $emailId === (string) $candidate->id
            ) {
                $target = $candidate;
                break;
            }
        }
        if (! $target instanceof WC_Email) {
            return false;
        }

        $sent = null;
        $orderId = $order->get_id();
        $capture = static function (
            bool $accepted,
            string $sentEmailId,
            WC_Email $sentEmail
        ) use (&$sent, $emailId, $orderId): void {
            if (
                $emailId === $sentEmailId
                && $sentEmail->object instanceof WC_Order
                && $orderId === $sentEmail->object->get_id()
            ) {
                $sent = $accepted;
            }
        };
        add_action('woocommerce_email_sent', $capture, PHP_INT_MAX, 3);
        self::$emailContexts[$orderId] = $messageKind;
        try {
            $target->trigger($orderId, $order);
        } finally {
            unset(self::$emailContexts[$orderId]);
            remove_action('woocommerce_email_sent', $capture, PHP_INT_MAX);
        }

        return true === $sent;
    }

    private static function orderIsDeliverable(WC_Order $order): bool
    {
        return ReadingProduct::orderContainsReading($order)
            && ReadingProduct::orderIsEligible($order)
            && [] === OrderMetadata::acceptedOrderEvidenceFailures($order)
            && [] === BillingEmailConfirmation::evidenceFailures($order)
            && in_array($order->get_status(), ['processing', 'completed'], true)
            && null !== $order->get_date_paid()
            && is_email($order->get_billing_email());
    }

    private static function requiredCustomerEmailsEnabled(): bool
    {
        if (! function_exists('WC') || null === WC()) {
            return false;
        }

        $required = [
            'customer_processing_order' => false,
            'customer_completed_order' => false,
        ];
        foreach (WC()->mailer()->get_emails() as $email) {
            if (
                $email instanceof WC_Email
                && array_key_exists((string) $email->id, $required)
            ) {
                $required[(string) $email->id] =
                    'yes' === (string) $email->enabled;
            }
        }

        return ! in_array(false, $required, true);
    }

    private static function persistGrantReference(
        WC_Order $order,
        string $grantId,
        string $grantExpiresAt
    ): true|WP_Error {
        $existingId = (string) $order->get_meta(self::GRANT_ID_KEY, true);
        $existingExpiry = (string) $order->get_meta(
            self::GRANT_EXPIRES_AT_KEY,
            true
        );
        if (('' === $existingId) !== ('' === $existingExpiry)) {
            return self::error(
                'vol_access_email_grant_conflict',
                __('訂單的安全連結紀錄不完整。', 'vale-of-light-commerce-bridge'),
                409
            );
        }
        if ('' !== $existingId) {
            if (
                hash_equals($existingId, $grantId)
                && hash_equals($existingExpiry, $grantExpiresAt)
            ) {
                return true;
            }
            $existingTimestamp = strtotime($existingExpiry);
            $newTimestamp = strtotime($grantExpiresAt);
            if (
                false === $existingTimestamp
                || false === $newTimestamp
                || $existingTimestamp > time()
                || $newTimestamp <= $existingTimestamp
            ) {
                return self::error(
                    'vol_access_email_grant_conflict',
                    __('訂單的安全連結紀錄發生衝突。', 'vale-of-light-commerce-bridge'),
                    409
                );
            }
        }

        $order->update_meta_data(self::GRANT_ID_KEY, $grantId);
        $order->update_meta_data(
            self::GRANT_EXPIRES_AT_KEY,
            $grantExpiresAt
        );
        $order->save();

        return true;
    }

    private static function accessUrlForOrder(WC_Order $order): string
    {
        return AccessEmailPolicy::buildAccessUrl(
            self::appBaseUrl(),
            (string) $order->get_meta(self::GRANT_ID_KEY, true),
            (string) $order->get_meta(
                self::GRANT_EXPIRES_AT_KEY,
                true
            ),
            self::accessSigningSecret()
        );
    }

    /**
     * @return array<string, mixed>|WP_Error
     */
    private static function claimIdempotency(
        string $idempotencyKey,
        string $requestHash,
        int $orderId,
        string $messageKind
    ): array|WP_Error {
        $option = self::idempotencyOption($idempotencyKey);
        $state = get_option($option, false);
        if (is_array($state)) {
            if (
                ! is_string($state['request_hash'] ?? null)
                || ! hash_equals($state['request_hash'], $requestHash)
                || (int) ($state['order_id'] ?? 0) !== $orderId
                || ($state['message_kind'] ?? null) !== $messageKind
            ) {
                return self::error(
                    'vol_access_email_idempotency_conflict',
                    __('安全通知識別碼發生衝突。', 'vale-of-light-commerce-bridge'),
                    409
                );
            }
            if (
                'sent' === ($state['status'] ?? null)
                && is_string($state['provider_message_id'] ?? null)
            ) {
                return $state;
            }
            if (
                'sending' === ($state['status'] ?? null)
            ) {
                $recent = (int) ($state['claimed_at'] ?? 0)
                    > time() - AccessEmailPolicy::MAX_CLOCK_SKEW_SECONDS;

                return self::error(
                    $recent
                        ? 'vol_access_email_in_progress'
                        : 'vol_access_email_state_indeterminate',
                    $recent
                        ? __('相同的安全通知正在處理中。', 'vale-of-light-commerce-bridge')
                        : __(
                            '先前的安全通知狀態無法確認，請由客服檢查寄送紀錄。',
                            'vale-of-light-commerce-bridge'
                        ),
                    409
                );
            }
            if ('failed' !== ($state['status'] ?? null)) {
                return self::error(
                    'vol_access_email_idempotency_conflict',
                    __('安全通知識別碼發生衝突。', 'vale-of-light-commerce-bridge'),
                    409
                );
            }
        }

        $claim = [
            'request_hash' => $requestHash,
            'order_id' => $orderId,
            'message_kind' => $messageKind,
            'status' => 'sending',
            'claimed_at' => time(),
            'claim_id' => wp_generate_uuid4(),
            'provider_message_id' => null,
        ];
        if (false === $state) {
            if (! add_option($option, $claim, '', false)) {
                return self::error(
                    'vol_access_email_in_progress',
                    __('相同的安全通知正在處理中。', 'vale-of-light-commerce-bridge'),
                    409
                );
            }
        } else {
            if (! self::compareAndSwapOption($option, $state, $claim)) {
                return self::error(
                    'vol_access_email_in_progress',
                    __('相同的安全通知正在處理中。', 'vale-of-light-commerce-bridge'),
                    409
                );
            }
        }

        return $claim;
    }

    private static function finishIdempotency(
        string $idempotencyKey,
        string $requestHash,
        string $claimId,
        string $status,
        ?string $providerMessageId
    ): bool {
        $option = self::idempotencyOption($idempotencyKey);
        $state = get_option($option, false);
        if (
            ! is_array($state)
            || ! is_string($state['request_hash'] ?? null)
            || ! hash_equals($state['request_hash'], $requestHash)
            || ! is_string($state['claim_id'] ?? null)
            || ! hash_equals($state['claim_id'], $claimId)
            || 'sending' !== ($state['status'] ?? null)
        ) {
            return false;
        }
        $finished = $state;
        $finished['status'] = $status;
        $finished['finished_at'] = time();
        $finished['provider_message_id'] = $providerMessageId;

        return self::compareAndSwapOption($option, $state, $finished);
    }

    /**
     * @param array<string, mixed> $expected
     * @param array<string, mixed> $replacement
     */
    private static function compareAndSwapOption(
        string $option,
        array $expected,
        array $replacement
    ): bool {
        global $wpdb;

        $updated = $wpdb->update(
            $wpdb->options,
            ['option_value' => maybe_serialize($replacement)],
            [
                'option_name' => $option,
                'option_value' => maybe_serialize($expected),
            ],
            ['%s'],
            ['%s', '%s']
        );
        wp_cache_delete($option, 'options');

        return 1 === $updated;
    }

    private static function idempotencyOption(string $key): string
    {
        return self::IDEMPOTENCY_OPTION_PREFIX . hash('sha256', $key);
    }

    private static function providerMessageId(
        string $idempotencyKey,
        string $requestHash
    ): string {
        return 'woo.' . substr(
            hash('sha256', $idempotencyKey . "\0" . $requestHash),
            0,
            40
        );
    }

    private static function appBaseUrl(): string
    {
        return defined('VOL_APP_BASE_URL')
            ? trim((string) constant('VOL_APP_BASE_URL'))
            : '';
    }

    private static function accessSigningSecret(): string
    {
        return defined('VOL_ACCESS_SIGNING_SECRET')
            ? (string) constant('VOL_ACCESS_SIGNING_SECRET')
            : '';
    }

    private static function notificationSigningSecret(): string
    {
        return defined('VOL_APP_TO_WORDPRESS_SIGNING_SECRET')
            ? (string) constant('VOL_APP_TO_WORDPRESS_SIGNING_SECRET')
            : '';
    }

    private static function header(
        WP_REST_Request $request,
        string $name
    ): ?string {
        $value = $request->get_header($name);

        return is_string($value) && '' !== $value ? trim($value) : null;
    }

    private static function success(
        string $messageKind,
        string $providerMessageId,
        bool $duplicate
    ): WP_REST_Response {
        $response = new WP_REST_Response(
            [
                'accepted' => true,
                'duplicate' => $duplicate,
                'messageKind' => $messageKind,
                'providerMessageId' => $providerMessageId,
            ],
            200
        );
        $response->header(
            'Cache-Control',
            'no-store, private, max-age=0'
        );

        return $response;
    }

    private static function error(
        string $code,
        string $message,
        int $status
    ): WP_Error {
        return new WP_Error($code, $message, ['status' => $status]);
    }
}
