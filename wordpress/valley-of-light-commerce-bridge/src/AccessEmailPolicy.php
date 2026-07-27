<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

final class AccessEmailPolicy
{
    public const REQUEST_VERSION = 'woo-access-email-v1';
    public const MAX_BODY_BYTES = 8192;
    public const MAX_CLOCK_SKEW_SECONDS = 300;
    public const MAX_GRANT_LIFETIME_SECONDS = 91 * 86400;
    public const MESSAGE_KINDS = [
        'intake_invitation',
        'result_ready',
        'access_recovery',
    ];

    /**
     * @return string[]
     */
    public static function configurationFailures(
        string $appBaseUrl,
        string $accessSigningSecret,
        string $notificationSigningSecret
    ): array {
        $failures = [];
        if (! self::appBaseUrlIsValid($appBaseUrl)) {
            $failures[] = 'app_base_url';
        }

        if (! self::secretIsValid($accessSigningSecret)) {
            $failures[] = 'access_signing_secret';
        }
        if (! self::secretIsValid($notificationSigningSecret)) {
            $failures[] = 'notification_signing_secret';
        }
        if (
            self::secretIsValid($accessSigningSecret)
            && self::secretIsValid($notificationSigningSecret)
            && hash_equals($accessSigningSecret, $notificationSigningSecret)
        ) {
            $failures[] = 'signing_secret_separation';
        }

        return $failures;
    }

    public static function signNotificationBody(
        string $body,
        string $timestamp,
        string $secret
    ): string {
        if (
            '' === $body
            || strlen($body) > self::MAX_BODY_BYTES
            || 1 !== preg_match('/^[0-9]{10}$/D', $timestamp)
            || ! self::secretIsValid($secret)
        ) {
            return '';
        }

        return self::base64Url(
            hash_hmac('sha256', $timestamp . '.' . $body, $secret, true)
        );
    }

    public static function verifyNotificationSignature(
        string $body,
        ?string $timestamp,
        ?string $signature,
        string $secret,
        int $now
    ): bool {
        if (
            null === $timestamp
            || null === $signature
            || strlen($body) > self::MAX_BODY_BYTES
            || 1 !== preg_match('/^[0-9]{10}$/D', $timestamp)
            || 1 !== preg_match('/^[A-Za-z0-9_-]{43}$/D', $signature)
            || abs($now - (int) $timestamp) > self::MAX_CLOCK_SKEW_SECONDS
        ) {
            return false;
        }

        $expected = self::signNotificationBody($body, $timestamp, $secret);

        return '' !== $expected && hash_equals($expected, $signature);
    }

    /**
     * @param array<string, mixed> $payload
     * @return string[]
     */
    public static function requestFailures(array $payload, int $now): array
    {
        $failures = [];
        $requiredKeys = [
            'version',
            'orderId',
            'grantId',
            'grantExpiresAt',
            'messageKind',
            'templateVersion',
            'idempotencyKey',
        ];
        $actualKeys = array_keys($payload);
        sort($requiredKeys);
        sort($actualKeys);

        if ($requiredKeys !== $actualKeys) {
            $failures[] = 'request_shape';
        }
        if (self::REQUEST_VERSION !== ($payload['version'] ?? null)) {
            $failures[] = 'version';
        }
        if (
            ! is_string($payload['orderId'] ?? null)
            || 1 !== preg_match('/^[1-9][0-9]{0,18}$/D', $payload['orderId'])
            || (int) $payload['orderId'] <= 0
            || (string) (int) $payload['orderId'] !== $payload['orderId']
        ) {
            $failures[] = 'order_id';
        }
        if (
            ! is_string($payload['grantId'] ?? null)
            || 1 !== preg_match(
                '/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/D',
                $payload['grantId']
            )
        ) {
            $failures[] = 'grant_id';
        }

        $expiresAt = self::parseTimestamp($payload['grantExpiresAt'] ?? null);
        if (
            null === $expiresAt
            || $expiresAt <= $now
            || $expiresAt > $now + self::MAX_GRANT_LIFETIME_SECONDS
        ) {
            $failures[] = 'grant_expires_at';
        }
        if (
            ! is_string($payload['messageKind'] ?? null)
            || ! in_array($payload['messageKind'], self::MESSAGE_KINDS, true)
        ) {
            $failures[] = 'message_kind';
        }
        foreach (['templateVersion', 'idempotencyKey'] as $key) {
            if (
                ! is_string($payload[$key] ?? null)
                || 1 !== preg_match('/^[A-Za-z0-9._:-]{8,160}$/D', $payload[$key])
            ) {
                $failures[] = self::camelToSnake($key);
            }
        }

        return array_values(array_unique($failures));
    }

    public static function buildAccessUrl(
        string $appBaseUrl,
        string $grantId,
        string $grantExpiresAt,
        string $accessSigningSecret,
        ?int $now = null
    ): string {
        if (
            ! self::appBaseUrlIsValid($appBaseUrl)
            || ! self::secretIsValid($accessSigningSecret)
            || 1 !== preg_match(
                '/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/D',
                $grantId
            )
        ) {
            return '';
        }

        $expiresAt = self::parseTimestamp($grantExpiresAt);
        $now ??= time();
        if (
            null === $expiresAt
            || $expiresAt <= $now
            || $expiresAt > $now + self::MAX_GRANT_LIFETIME_SECONDS
        ) {
            return '';
        }

        $message = "v1\n" . $grantId . "\n" . $expiresAt;
        $signature = self::base64Url(
            hash_hmac('sha256', $message, $accessSigningSecret, true)
        );
        $token = sprintf(
            'v1.%s.%d.%s',
            $grantId,
            $expiresAt,
            $signature
        );

        return rtrim($appBaseUrl, '/') . '/r#' . rawurlencode($token);
    }

    private static function parseTimestamp(mixed $value): ?int
    {
        if (
            ! is_string($value)
            || 1 !== preg_match(
                '/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$/D',
                $value
            )
        ) {
            return null;
        }

        try {
            $date = new \DateTimeImmutable($value);
            $errors = \DateTimeImmutable::getLastErrors();
            if (
                false !== $errors
                && (
                    0 !== $errors['warning_count']
                    || 0 !== $errors['error_count']
                )
            ) {
                return null;
            }

            return $date->getTimestamp();
        } catch (\Throwable) {
            return null;
        }
    }

    private static function secretIsValid(string $secret): bool
    {
        return strlen($secret) >= 32 && strlen($secret) <= 512;
    }

    private static function appBaseUrlIsValid(string $appBaseUrl): bool
    {
        $parts = parse_url($appBaseUrl);

        return is_array($parts)
            && 'https' === ($parts['scheme'] ?? null)
            && is_string($parts['host'] ?? null)
            && '' !== $parts['host']
            && ! isset($parts['user'])
            && ! isset($parts['pass'])
            && ! isset($parts['query'])
            && ! isset($parts['fragment'])
            && (
                ! isset($parts['path'])
                || in_array($parts['path'], ['', '/'], true)
            );
    }

    private static function base64Url(string $value): string
    {
        return rtrim(strtr(base64_encode($value), '+/', '-_'), '=');
    }

    private static function camelToSnake(string $value): string
    {
        return strtolower(
            (string) preg_replace('/(?<!^)[A-Z]/', '_$0', $value)
        );
    }
}
