<?php

declare(strict_types=1);

use ValeOfLight\CommerceBridge\CheckoutTerms;
use ValeOfLight\CommerceBridge\CheckoutTermsPolicy;

require_once dirname(__DIR__) . '/src/CheckoutTerms.php';

$assertions = 0;

$assertSame = static function (mixed $expected, mixed $actual, string $label) use (&$assertions): void {
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

$current = 'commerce-terms-2026-08-10';
$previous = 'commerce-terms-2026-07-26';
$rotatingVersions = [$current, $previous];

$assertSame(
    [],
    CheckoutTermsPolicy::configurationFailures($current, $rotatingVersions),
    'A current plus explicitly retained previous terms cohort must be valid.'
);
$assertSame(
    ['current_version_first'],
    CheckoutTermsPolicy::configurationFailures($current, [$previous, $current]),
    'The current version must be first so new-order stamping cannot be ambiguous.'
);
$assertSame(
    ['duplicate_payment_eligible_version'],
    CheckoutTermsPolicy::configurationFailures($current, [$current, $current]),
    'Duplicate payment cohorts must fail configuration validation.'
);
$assertSame(
    ['current_version', 'payment_eligible_version_format'],
    CheckoutTermsPolicy::configurationFailures('draft terms', ['draft terms']),
    'Free-form terms labels must not become production versions.'
);
$assertSame(
    ['current_version', 'payment_eligible_version_format'],
    CheckoutTermsPolicy::configurationFailures(
        'commerce-terms-2026-02-30',
        ['commerce-terms-2026-02-30']
    ),
    'An impossible calendar date must not become a production terms version.'
);
$assertSame(
    true,
    CheckoutTerms::configurationIsValid(),
    'The production checkout terms lifecycle must be internally valid.'
);
$assertSame(
    'commerce-terms-2026-07-26-draft',
    CheckoutTerms::currentVersion(),
    'Staging must not mint a production-looking consent cohort from draft legal copy.'
);

$evidence = [
    'version_presented' => $previous,
    'presented_at' => '2026-07-26T08:30:00+00:00',
    'product_id' => '13',
    'acceptance_source' => 'classic-required-terms-checkbox',
];

$assertSame(
    [],
    CheckoutTermsPolicy::evidenceFailures($evidence, 13, $rotatingVersions),
    'A delayed order keeps the terms version it accepted and remains payable while retained.'
);

$newEvidence = $evidence;
$newEvidence['version_presented'] = $current;
$assertSame(
    [],
    CheckoutTermsPolicy::evidenceFailures($newEvidence, 13, $rotatingVersions),
    'New orders may use the new terms cohort during the overlap window.'
);

$retiredEvidence = $evidence;
$assertSame(
    ['checkout_terms_version_presented'],
    CheckoutTermsPolicy::evidenceFailures($retiredEvidence, 13, [$current]),
    'A retired cohort must fail before a new gateway handoff, never be silently restamped.'
);

$missingTimestamp = $evidence;
$missingTimestamp['presented_at'] = '';
$assertSame(
    ['checkout_terms_presented_at'],
    CheckoutTermsPolicy::evidenceFailures($missingTimestamp, 13, $rotatingVersions),
    'Missing immutable presentation time must fail closed.'
);

$impossibleTimestamp = $evidence;
$impossibleTimestamp['presented_at'] = '2026-02-30T08:30:00+00:00';
$assertSame(
    ['checkout_terms_presented_at'],
    CheckoutTermsPolicy::evidenceFailures($impossibleTimestamp, 13, $rotatingVersions),
    'An impossible presentation date must fail closed.'
);

$wrongProduct = $evidence;
$wrongProduct['product_id'] = 14;
$assertSame(
    ['reading_product_id'],
    CheckoutTermsPolicy::evidenceFailures($wrongProduct, 13, $rotatingVersions),
    'Terms evidence cannot be moved to a different product.'
);

$assertSame(
    ['reading_product_id'],
    CheckoutTermsPolicy::evidenceFailures($evidence, 0, $rotatingVersions),
    'An invalid current product configuration must fail evidence validation.'
);

$unknownSource = $evidence;
$unknownSource['acceptance_source'] = 'manual-admin-restamp';
$assertSame(
    ['checkout_terms_acceptance_source'],
    CheckoutTermsPolicy::evidenceFailures($unknownSource, 13, $rotatingVersions),
    'Only a validated customer-acceptance boundary may create terms evidence.'
);

fwrite(STDOUT, sprintf("CheckoutTerms: %d assertions passed.\n", $assertions));
