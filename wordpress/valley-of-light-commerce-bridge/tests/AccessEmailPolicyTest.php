<?php

declare(strict_types=1);

use ValeOfLight\CommerceBridge\AccessEmailPolicy;

require_once dirname(__DIR__) . '/src/AccessEmailPolicy.php';

$assertions = 0;

$assertSame = static function (
    mixed $expected,
    mixed $actual,
    string $label
) use (&$assertions): void {
    ++$assertions;
    if ($expected !== $actual) {
        fwrite(
            STDERR,
            sprintf(
                "%s\nExpected: %s\nActual: %s\n",
                $label,
                var_export($expected, true),
                var_export($actual, true)
            )
        );
        exit(1);
    }
};

$appBaseUrl = 'https://app.valeoflight.com';
$accessSecret = 'access-secret-abcdefghijklmnopqrstuvwxyz';
$notificationSecret = 'notification-secret-abcdefghijklmnopqrstuvwxyz';
$now = 1785067200;
$expiresAt = '2026-08-25T12:00:00.000Z';
$grantId = '123e4567-e89b-42d3-a456-426614174000';

$assertSame(
    [],
    AccessEmailPolicy::configurationFailures(
        $appBaseUrl,
        $accessSecret,
        $notificationSecret
    ),
    'Distinct strong secrets and the production HTTPS app origin must pass.'
);
$assertSame(
    ['app_base_url'],
    AccessEmailPolicy::configurationFailures(
        'http://app.valeoflight.com',
        $accessSecret,
        $notificationSecret
    ),
    'The email bridge must not create an HTTP capability link.'
);
$assertSame(
    ['signing_secret_separation'],
    AccessEmailPolicy::configurationFailures(
        $appBaseUrl,
        $accessSecret,
        $accessSecret
    ),
    'Notification and access-token secrets must remain separate.'
);

$body = '{"version":"woo-access-email-v1"}';
$timestamp = '1787745600';
$signature = AccessEmailPolicy::signNotificationBody(
    $body,
    $timestamp,
    $notificationSecret
);
$assertSame(
    '1ZaCdOfdkrkap6vKn2KoR7u6six2_eS1odKpmh-iTZU',
    $signature,
    'PHP must match the Node HMAC/base64url notification signature.'
);
$assertSame(
    true,
    AccessEmailPolicy::verifyNotificationSignature(
        $body,
        $timestamp,
        $signature,
        $notificationSecret,
        1787745600
    ),
    'A current exact signed body must pass.'
);
$assertSame(
    false,
    AccessEmailPolicy::verifyNotificationSignature(
        $body . ' ',
        $timestamp,
        $signature,
        $notificationSecret,
        1787745600
    ),
    'Any body mutation must invalidate the signature.'
);
$assertSame(
    false,
    AccessEmailPolicy::verifyNotificationSignature(
        $body,
        $timestamp,
        $signature,
        $notificationSecret,
        1787745600 + AccessEmailPolicy::MAX_CLOCK_SKEW_SECONDS + 1
    ),
    'A stale signed request must fail.'
);

$payload = [
    'version' => AccessEmailPolicy::REQUEST_VERSION,
    'orderId' => '13',
    'grantId' => $grantId,
    'grantExpiresAt' => $expiresAt,
    'messageKind' => 'intake_invitation',
    'templateVersion' => 'paid-intake-woo-v1',
    'idempotencyKey' => 'paid-intake-reading-1234-v1',
];
$assertSame(
    [],
    AccessEmailPolicy::requestFailures($payload, $now),
    'The signed app notification contract must accept one valid request.'
);
$unexpected = $payload;
$unexpected['billingEmail'] = 'buyer@example.com';
$assertSame(
    ['request_shape'],
    AccessEmailPolicy::requestFailures($unexpected, $now),
    'The narrow endpoint must reject personal data and unknown fields.'
);
$invalidKind = $payload;
$invalidKind['messageKind'] = 'arbitrary_email';
$assertSame(
    ['message_kind'],
    AccessEmailPolicy::requestFailures($invalidKind, $now),
    'Only the three reviewed reading-email purposes are accepted.'
);
$overflowOrder = $payload;
$overflowOrder['orderId'] = '9999999999999999999';
$assertSame(
    ['order_id'],
    AccessEmailPolicy::requestFailures($overflowOrder, $now),
    'An order ID that cannot round-trip through the PHP integer type must fail.'
);
$expired = $payload;
$expired['grantExpiresAt'] = '2026-07-26T11:59:59.000Z';
$assertSame(
    ['grant_expires_at'],
    AccessEmailPolicy::requestFailures($expired, $now),
    'An expired grant must never be emailed.'
);

$assertSame(
    'https://app.valeoflight.com/r#v1.'
        . '123e4567-e89b-42d3-a456-426614174000.'
        . '1787659200.'
        . 'Hkqt02ZW7Tc6yVOU9ZAAuW64WIMQ7hoDtBRsIiDW-jg',
    AccessEmailPolicy::buildAccessUrl(
        $appBaseUrl,
        $grantId,
        $expiresAt,
        $accessSecret,
        $now
    ),
    'WordPress must reconstruct exactly the existing app token without storing it.'
);
$assertSame(
    '',
    AccessEmailPolicy::buildAccessUrl(
        $appBaseUrl,
        $grantId,
        '2026-07-26T11:59:59.000Z',
        $accessSecret,
        $now
    ),
    'WordPress must fail closed instead of rendering an expired link.'
);

fwrite(
    STDOUT,
    sprintf("AccessEmailPolicy: %d assertions passed.\n", $assertions)
);
