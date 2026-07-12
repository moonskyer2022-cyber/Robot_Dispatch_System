import unittest

from backend.auth import (
    create_session_token,
    login_allowed,
    record_login_failure,
    verify_session_token,
)


class SessionTokenTests(unittest.TestCase):
    def test_valid_token_round_trip(self):
        token = create_session_token("operator")
        self.assertEqual("operator", verify_session_token(token))

    def test_tampered_token_is_rejected(self):
        token = create_session_token("operator")
        payload, signature = token.split(".", 1)
        replacement = "A" if signature[0] != "A" else "B"
        tampered = f"{payload}.{replacement}{signature[1:]}"
        self.assertIsNone(verify_session_token(tampered))

    def test_login_failures_are_rate_limited(self):
        client_key = "auth-test-rate-limit"
        for _ in range(5):
            self.assertTrue(login_allowed(client_key))
            record_login_failure(client_key)
        self.assertFalse(login_allowed(client_key))


if __name__ == "__main__":
    unittest.main()
