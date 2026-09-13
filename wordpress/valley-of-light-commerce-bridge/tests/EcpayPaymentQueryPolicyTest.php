<?php

declare(strict_types=1);

use ValeOfLight\CommerceBridge\EcpayPaymentQueryPolicy;

require_once dirname(__DIR__) . '/src/CommerceInvariant.php';
require_once dirname(__DIR__) . '/src/EcpayPaymentReconciler.php';

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

$valid = [
    'MerchantTradeNo' => 'VOL00000139SNabcde',
    'TradeStatus' => '1',
    'TradeAmt' => '1280',
    'PaymentType' => 'Credit_CreditCard',
    'TradeNo' => '2607281234567890',
    'PaymentDate' => '2026/07/28 16:37:30',
];

$assertSame(
    [],
    EcpayPaymentQueryPolicy::failures(
        $valid,
        'VOL00000139SNabcde',
        '1280'
    ),
    'A matching verified paid credit query may reconcile the Woo order.'
);

$wrongOrder = $valid;
$wrongOrder['MerchantTradeNo'] = 'VOL00000999SNabcde';
$assertSame(
    ['merchant_trade_no'],
    EcpayPaymentQueryPolicy::failures(
        $wrongOrder,
        'VOL00000139SNabcde',
        '1280'
    ),
    'A paid response must never move a different Woo order.'
);

$unpaid = $valid;
$unpaid['TradeStatus'] = '0';
$assertSame(
    ['trade_status'],
    EcpayPaymentQueryPolicy::failures(
        $unpaid,
        'VOL00000139SNabcde',
        '1280'
    ),
    'An unpaid ECPay query must remain pending.'
);

$wrongAmount = $valid;
$wrongAmount['TradeAmt'] = '1279';
$assertSame(
    ['trade_amount'],
    EcpayPaymentQueryPolicy::failures(
        $wrongAmount,
        'VOL00000139SNabcde',
        '1280'
    ),
    'A mismatched amount must fail closed.'
);

$wrongMethod = $valid;
$wrongMethod['PaymentType'] = 'ATM_TAISHIN';
$assertSame(
    ['payment_type'],
    EcpayPaymentQueryPolicy::failures(
        $wrongMethod,
        'VOL00000139SNabcde',
        '1280'
    ),
    'The credit-card reconciler must not accept another payment method.'
);

$missingProof = $valid;
$missingProof['TradeNo'] = '';
$missingProof['PaymentDate'] = '';
$assertSame(
    ['trade_no', 'payment_date'],
    EcpayPaymentQueryPolicy::failures(
        $missingProof,
        'VOL00000139SNabcde',
        '1280'
    ),
    'A response without an ECPay trade reference and payment date must fail.'
);

fwrite(
    STDOUT,
    sprintf(
        "EcpayPaymentQueryPolicy: %d assertions passed.\n",
        $assertions
    )
);
