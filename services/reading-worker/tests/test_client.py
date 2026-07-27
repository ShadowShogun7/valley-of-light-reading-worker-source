from __future__ import annotations

import hashlib
import hmac
import unittest

from reading_worker.client import sign_body, verify_body_signature


class SignatureTests(unittest.TestCase):
    def test_signature_matches_node_protocol(self) -> None:
        raw_body = b'{"limit":5}'
        timestamp = "1785081600"
        secret = "worker-secret-with-more-than-thirty-two-bytes"
        expected_digest = hmac.new(
            secret.encode(),
            timestamp.encode() + b"." + raw_body,
            hashlib.sha256,
        ).digest()
        import base64

        expected = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode()
        self.assertEqual(sign_body(raw_body, timestamp, secret), expected)
        self.assertTrue(
            verify_body_signature(
                raw_body,
                timestamp,
                expected,
                secret,
                now_seconds=int(timestamp),
            )
        )

    def test_signature_rejects_stale_timestamp_and_changed_body(self) -> None:
        body = b'{"limit":5}'
        timestamp = "1785081600"
        secret = "worker-secret-with-more-than-thirty-two-bytes"
        signature = sign_body(body, timestamp, secret)
        self.assertFalse(
            verify_body_signature(
                body,
                timestamp,
                signature,
                secret,
                now_seconds=int(timestamp) + 301,
            )
        )
        self.assertFalse(
            verify_body_signature(
                b'{"limit":6}',
                timestamp,
                signature,
                secret,
                now_seconds=int(timestamp),
            )
        )


if __name__ == "__main__":
    unittest.main()
