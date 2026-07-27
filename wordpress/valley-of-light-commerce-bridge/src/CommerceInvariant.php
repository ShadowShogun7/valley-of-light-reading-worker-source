<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

final class CommerceInvariant
{
    /**
     * Validate a normalized cart or order snapshot without depending on WordPress.
     *
     * @param array<string, mixed> $snapshot
     * @return string[]
     */
    public static function failures(
        array $snapshot,
        int $expectedProductId,
        string $expectedCurrency,
        string $expectedTotal
    ): array {
        $checks = [
            'item_count' => self::integerEquals($snapshot['item_count'] ?? null, 1),
            'product_id' => self::integerEquals(
                $snapshot['product_id'] ?? null,
                $expectedProductId
            ),
            'variation_id' => self::integerEquals($snapshot['variation_id'] ?? null, 0),
            'quantity' => self::decimalEquals($snapshot['quantity'] ?? null, '1'),
            'currency' => is_string($snapshot['currency'] ?? null)
                && $expectedCurrency === $snapshot['currency'],
            'line_subtotal' => self::decimalEquals(
                $snapshot['line_subtotal'] ?? null,
                $expectedTotal
            ),
            'line_total' => self::decimalEquals(
                $snapshot['line_total'] ?? null,
                $expectedTotal
            ),
            'subtotal' => self::decimalEquals(
                $snapshot['subtotal'] ?? null,
                $expectedTotal
            ),
            'contents_total' => self::decimalEquals(
                $snapshot['contents_total'] ?? null,
                $expectedTotal
            ),
            'total' => self::decimalEquals($snapshot['total'] ?? null, $expectedTotal),
            'line_subtotal_tax' => self::decimalEquals(
                $snapshot['line_subtotal_tax'] ?? null,
                '0'
            ),
            'line_total_tax' => self::decimalEquals(
                $snapshot['line_total_tax'] ?? null,
                '0'
            ),
            'subtotal_tax' => self::decimalEquals(
                $snapshot['subtotal_tax'] ?? null,
                '0'
            ),
            'tax_total' => self::decimalEquals($snapshot['tax_total'] ?? null, '0'),
            'discount_total' => self::decimalEquals(
                $snapshot['discount_total'] ?? null,
                '0'
            ),
            'discount_tax' => self::decimalEquals(
                $snapshot['discount_tax'] ?? null,
                '0'
            ),
            'fee_total' => self::decimalEquals($snapshot['fee_total'] ?? null, '0'),
            'fee_tax' => self::decimalEquals($snapshot['fee_tax'] ?? null, '0'),
            'shipping_total' => self::decimalEquals(
                $snapshot['shipping_total'] ?? null,
                '0'
            ),
            'shipping_tax' => self::decimalEquals(
                $snapshot['shipping_tax'] ?? null,
                '0'
            ),
            'coupon_count' => self::integerEquals($snapshot['coupon_count'] ?? null, 0),
            'fee_count' => self::integerEquals($snapshot['fee_count'] ?? null, 0),
            'shipping_count' => self::integerEquals(
                $snapshot['shipping_count'] ?? null,
                0
            ),
            'tax_line_count' => self::integerEquals(
                $snapshot['tax_line_count'] ?? null,
                0
            ),
        ];

        return array_keys(array_filter($checks, static fn (bool $passed): bool => ! $passed));
    }

    public static function decimalEquals(mixed $actual, string $expected): bool
    {
        $normalizedActual = self::normalizeDecimal($actual);
        $normalizedExpected = self::normalizeDecimal($expected);

        return null !== $normalizedActual
            && null !== $normalizedExpected
            && $normalizedExpected === $normalizedActual;
    }

    private static function integerEquals(mixed $actual, int $expected): bool
    {
        if (is_int($actual)) {
            return $expected === $actual;
        }

        return is_string($actual)
            && 1 === preg_match('/^(?:0|[1-9][0-9]*)$/D', $actual)
            && (string) $expected === $actual;
    }

    private static function normalizeDecimal(mixed $value): ?string
    {
        if (! is_int($value) && ! is_float($value) && ! is_string($value)) {
            return null;
        }

        if (is_float($value) && ! is_finite($value)) {
            return null;
        }

        $raw = trim((string) $value);
        if (1 !== preg_match('/^([+-]?)([0-9]+)(?:\.([0-9]+))?$/D', $raw, $matches)) {
            return null;
        }

        $integer = ltrim($matches[2], '0');
        $integer = '' === $integer ? '0' : $integer;
        $fraction = rtrim($matches[3] ?? '', '0');
        $isZero = '0' === $integer && '' === $fraction;
        $sign = '-' === $matches[1] && ! $isZero ? '-' : '';

        return $sign . $integer . ('' === $fraction ? '' : '.' . $fraction);
    }
}
