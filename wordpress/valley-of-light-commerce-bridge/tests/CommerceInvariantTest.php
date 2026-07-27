<?php

declare(strict_types=1);

use ValeOfLight\CommerceBridge\CommerceInvariant;

require_once dirname(__DIR__) . '/src/CommerceInvariant.php';

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

$valid = [
    'item_count' => 1,
    'product_id' => 13,
    'variation_id' => 0,
    'quantity' => 1,
    'currency' => 'TWD',
    'line_subtotal' => '1280.00',
    'line_total' => 1280.0,
    'subtotal' => '1280',
    'contents_total' => 1280,
    'total' => '1280.0000',
    'line_subtotal_tax' => '0',
    'line_total_tax' => 0.0,
    'subtotal_tax' => '0.00',
    'tax_total' => 0,
    'discount_total' => 0,
    'discount_tax' => 0,
    'fee_total' => 0,
    'fee_tax' => 0,
    'shipping_total' => 0,
    'shipping_tax' => 0,
    'coupon_count' => 0,
    'fee_count' => 0,
    'shipping_count' => 0,
    'tax_line_count' => 0,
];

$failures = static fn (array $snapshot): array => CommerceInvariant::failures(
    $snapshot,
    13,
    'TWD',
    '1280'
);

$assertSame([], $failures($valid), 'The exact fixed-price checkout must pass.');

$driftCases = [
    'item_count' => 2,
    'product_id' => 14,
    'variation_id' => 99,
    'quantity' => '1.5',
    'currency' => 'USD',
    'line_subtotal' => '1279.999',
    'line_total' => '1279',
    'subtotal' => '1281',
    'contents_total' => '1270',
    'total' => '1280.01',
    'line_subtotal_tax' => '0.01',
    'line_total_tax' => '1',
    'subtotal_tax' => '0.0001',
    'tax_total' => '64',
    'discount_total' => '1',
    'discount_tax' => '0.01',
    'fee_total' => '10',
    'fee_tax' => '0.5',
    'shipping_total' => '60',
    'shipping_tax' => '3',
    'coupon_count' => 1,
    'fee_count' => 1,
    'shipping_count' => 1,
    'tax_line_count' => 1,
];

foreach ($driftCases as $field => $driftedValue) {
    $snapshot = $valid;
    $snapshot[$field] = $driftedValue;
    $assertSame(
        [$field],
        $failures($snapshot),
        sprintf('Drift in %s must fail closed.', $field)
    );
}

$assertSame(
    true,
    CommerceInvariant::decimalEquals('001280.0000', '1280'),
    'Equivalent decimal representations must compare exactly.'
);
$assertSame(
    false,
    CommerceInvariant::decimalEquals('1.28e3', '1280'),
    'Scientific notation must not enter the price boundary.'
);
$assertSame(
    false,
    CommerceInvariant::decimalEquals('1280 TWD', '1280'),
    'Currency-decorated values must not enter the price boundary.'
);
$assertSame(
    true,
    CommerceInvariant::decimalEquals('-0.000', '0'),
    'Signed zero must normalize to zero.'
);
$assertSame(
    false,
    CommerceInvariant::decimalEquals(INF, '0'),
    'Non-finite numbers must be rejected.'
);

fwrite(STDOUT, sprintf("CommerceInvariant: %d assertions passed.\n", $assertions));
