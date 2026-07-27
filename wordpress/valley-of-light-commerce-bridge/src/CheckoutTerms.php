<?php

declare(strict_types=1);

namespace ValeOfLight\CommerceBridge;

final class CheckoutTermsPolicy
{
    private const MAX_ELIGIBLE_VERSIONS = 8;
    private const ACCEPTANCE_SOURCES = [
        'classic-required-terms-checkbox',
        'store-api-validated-checkout',
    ];

    /**
     * @param string[] $paymentEligibleVersions
     * @return string[]
     */
    public static function configurationFailures(
        string $currentVersion,
        array $paymentEligibleVersions
    ): array {
        $failures = [];

        if (! self::isValidVersion($currentVersion)) {
            $failures[] = 'current_version';
        }

        if (
            [] === $paymentEligibleVersions
            || count($paymentEligibleVersions) > self::MAX_ELIGIBLE_VERSIONS
        ) {
            $failures[] = 'payment_eligible_versions';
        }

        foreach ($paymentEligibleVersions as $version) {
            if (! is_string($version) || ! self::isValidVersion($version)) {
                $failures[] = 'payment_eligible_version_format';
                break;
            }
        }

        if (
            [] !== $paymentEligibleVersions
            && $currentVersion !== ($paymentEligibleVersions[0] ?? null)
        ) {
            $failures[] = 'current_version_first';
        }

        if (
            count($paymentEligibleVersions)
            !== count(array_unique($paymentEligibleVersions, SORT_STRING))
        ) {
            $failures[] = 'duplicate_payment_eligible_version';
        }

        return array_values(array_unique($failures, SORT_STRING));
    }

    /**
     * @param array<string, mixed> $evidence
     * @param string[] $paymentEligibleVersions
     * @return string[]
     */
    public static function evidenceFailures(
        array $evidence,
        int $expectedProductId,
        array $paymentEligibleVersions
    ): array {
        $failures = [];
        $version = $evidence['version_presented'] ?? null;
        $presentedAt = $evidence['presented_at'] ?? null;
        $productId = $evidence['product_id'] ?? null;
        $acceptanceSource = $evidence['acceptance_source'] ?? null;

        if (
            ! is_string($version)
            || ! self::isValidVersion($version)
            || ! in_array($version, $paymentEligibleVersions, true)
        ) {
            $failures[] = 'checkout_terms_version_presented';
        }

        if (! is_string($presentedAt) || ! self::isValidTimestamp($presentedAt)) {
            $failures[] = 'checkout_terms_presented_at';
        }

        if (! self::productIdEquals($productId, $expectedProductId)) {
            $failures[] = 'reading_product_id';
        }

        if (
            ! is_string($acceptanceSource)
            || ! in_array($acceptanceSource, self::ACCEPTANCE_SOURCES, true)
        ) {
            $failures[] = 'checkout_terms_acceptance_source';
        }

        return $failures;
    }

    private static function isValidVersion(string $version): bool
    {
        if (
            strlen($version) > 80
            || 1 !== preg_match(
                '/^commerce-terms-([0-9]{4})-([0-9]{2})-([0-9]{2})(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?$/D',
                $version,
                $matches
            )
        ) {
            return false;
        }

        return checkdate((int) $matches[2], (int) $matches[3], (int) $matches[1]);
    }

    private static function isValidTimestamp(string $timestamp): bool
    {
        if (
            1 !== preg_match(
                '/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$/D',
                $timestamp
            )
        ) {
            return false;
        }

        try {
            new \DateTimeImmutable($timestamp);

            $errors = \DateTimeImmutable::getLastErrors();

            return false === $errors
                || (0 === $errors['warning_count'] && 0 === $errors['error_count']);
        } catch (\Exception) {
            return false;
        }
    }

    private static function productIdEquals(mixed $actual, int $expected): bool
    {
        if ($expected <= 0) {
            return false;
        }

        if (is_int($actual)) {
            return $actual === $expected;
        }

        return is_string($actual)
            && 1 === preg_match('/^[1-9][0-9]*$/D', $actual)
            && (string) $expected === $actual;
    }
}

final class CheckoutTerms
{
    private const CURRENT_VERSION = 'commerce-terms-2026-07-26-draft';

    /**
     * Keep every still-payable order cohort here during a terms rotation.
     *
     * The current version must be first. A previous version may be removed only
     * after its ECPay payment window and callback/retry window are closed and
     * the paid-reading receiver no longer needs to accept that cohort.
     */
    private const PAYMENT_ELIGIBLE_VERSIONS = [
        self::CURRENT_VERSION,
    ];

    public static function currentVersion(): string
    {
        return self::CURRENT_VERSION;
    }

    /**
     * @return string[]
     */
    public static function paymentEligibleVersions(): array
    {
        return self::PAYMENT_ELIGIBLE_VERSIONS;
    }

    public static function configurationIsValid(): bool
    {
        return [] === CheckoutTermsPolicy::configurationFailures(
            self::CURRENT_VERSION,
            self::PAYMENT_ELIGIBLE_VERSIONS
        );
    }

    /**
     * @param array<string, mixed> $evidence
     * @return string[]
     */
    public static function evidenceFailures(array $evidence, int $expectedProductId): array
    {
        if (! self::configurationIsValid()) {
            return ['checkout_terms_configuration'];
        }

        return CheckoutTermsPolicy::evidenceFailures(
            $evidence,
            $expectedProductId,
            self::PAYMENT_ELIGIBLE_VERSIONS
        );
    }
}
