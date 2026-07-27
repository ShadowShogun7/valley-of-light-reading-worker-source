<?php

declare(strict_types=1);

use ValeOfLight\CommerceBridge\BillingEmailConfirmationPolicy;

require_once dirname(__DIR__) . '/src/BillingEmailConfirmation.php';

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

$email = 'buyer@example.com';
$secret = str_repeat('a', 32);
$otherSecret = str_repeat('b', 32);

$assertSame(
    true,
    BillingEmailConfirmationPolicy::valuesMatch($email, $email),
    'Two identical normalized emails must match.'
);
$assertSame(
    false,
    BillingEmailConfirmationPolicy::valuesMatch($email, 'Buyer@example.com'),
    'Confirmation is exact after normalization; a case change must not match.'
);
$assertSame(
    false,
    BillingEmailConfirmationPolicy::valuesMatch('', ''),
    'Two empty values must never count as confirmation.'
);
$assertSame(
    false,
    BillingEmailConfirmationPolicy::valuesMatch($email, ''),
    'A missing confirmation must fail closed.'
);

$digest = BillingEmailConfirmationPolicy::digest($email, $secret);
$assertSame(
    64,
    strlen($digest),
    'The persisted proof must be a SHA-256 HMAC.'
);
$assertSame(
    $digest,
    BillingEmailConfirmationPolicy::digest($email, $secret),
    'The proof must be deterministic for the same normalized email and secret.'
);
$assertSame(
    false,
    hash_equals(
        $digest,
        BillingEmailConfirmationPolicy::digest('other@example.com', $secret)
    ),
    'A different billing email must invalidate the proof.'
);
$assertSame(
    false,
    hash_equals(
        $digest,
        BillingEmailConfirmationPolicy::digest($email, $otherSecret)
    ),
    'A different WordPress secret must invalidate the proof.'
);
$assertSame(
    '',
    BillingEmailConfirmationPolicy::digest($email, ''),
    'A missing server secret must never produce a proof.'
);

$evidence = [
    'digest' => $digest,
    'confirmed_at' => '2026-07-26T12:00:00+00:00',
    'acceptance_source' => 'classic-checkout-server-validation',
];
$assertSame(
    [],
    BillingEmailConfirmationPolicy::evidenceFailures(
        $evidence,
        $email,
        $secret
    ),
    'Valid classic server evidence must pass.'
);

$storeApiEvidence = $evidence;
$storeApiEvidence['acceptance_source'] = 'store-api-server-validation';
$assertSame(
    [],
    BillingEmailConfirmationPolicy::evidenceFailures(
        $storeApiEvidence,
        $email,
        $secret
    ),
    'Valid Store API server evidence must pass.'
);

$assertSame(
    ['billing_email_confirmation_digest'],
    BillingEmailConfirmationPolicy::evidenceFailures(
        $evidence,
        'changed@example.com',
        $secret
    ),
    'Changing the order billing email after confirmation must fail.'
);

$tamperedDigest = $evidence;
$tamperedDigest['digest'] = str_repeat('0', 64);
$assertSame(
    ['billing_email_confirmation_digest'],
    BillingEmailConfirmationPolicy::evidenceFailures(
        $tamperedDigest,
        $email,
        $secret
    ),
    'A tampered digest must fail.'
);

$invalidTimestamp = $evidence;
$invalidTimestamp['confirmed_at'] = '2026-02-30T12:00:00+00:00';
$assertSame(
    ['billing_email_confirmation_confirmed_at'],
    BillingEmailConfirmationPolicy::evidenceFailures(
        $invalidTimestamp,
        $email,
        $secret
    ),
    'An impossible confirmation timestamp must fail.'
);

$unknownSource = $evidence;
$unknownSource['acceptance_source'] = 'client-javascript-only';
$assertSame(
    ['billing_email_confirmation_acceptance_source'],
    BillingEmailConfirmationPolicy::evidenceFailures(
        $unknownSource,
        $email,
        $secret
    ),
    'Client-only evidence must never be accepted.'
);

$assertSame(
    [
        'billing_email',
        'billing_email_confirmation_digest',
    ],
    BillingEmailConfirmationPolicy::evidenceFailures(
        $evidence,
        '',
        $secret
    ),
    'A missing billing email must fail both identity and proof checks.'
);

$missingEvidence = [];
$assertSame(
    [
        'billing_email_confirmation_digest',
        'billing_email_confirmation_confirmed_at',
        'billing_email_confirmation_acceptance_source',
    ],
    BillingEmailConfirmationPolicy::evidenceFailures(
        $missingEvidence,
        $email,
        $secret
    ),
    'A legacy order without confirmation evidence must fail closed.'
);

fwrite(
    STDOUT,
    sprintf("BillingEmailConfirmation: %d assertions passed.\n", $assertions)
);
