import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from sanitizer import (  # noqa: E402
    is_valid_target_id,
    sanitize_message,
    sanitize_text,
    sanitize_url,
    validate_target_id,
)


class TestSanitizer(unittest.TestCase):
    def test_validate_target_id_valid(self):
        valid_u = "U79b78adfc1c2eacfe1a004bc0beea7f1"
        valid_c = "C1234567890abcdef1234567890abcdef"
        valid_r = "Rabcdef1234567890abcdef1234567890"

        self.assertEqual(validate_target_id(valid_u), valid_u)
        self.assertEqual(validate_target_id(valid_c), valid_c)
        self.assertEqual(validate_target_id(valid_r), valid_r)

        # Whitespace handling
        self.assertEqual(validate_target_id(f"  {valid_u}  "), valid_u)

    def test_validate_target_id_invalid(self):
        invalid_ids = [
            "",
            "   ",
            "U123",                         # Too short
            "U79b78adfc1c2eacfe1a004bc0beea7f199",  # Too long
            "X79b78adfc1c2eacfe1a004bc0beea7f1",  # Wrong prefix
            "U79b78adfc1c2eacfe1a004bc0beea7fZ",  # Non-hex char 'Z'
            None,
            12345,
            ["U79b78adfc1c2eacfe1a004bc0beea7f1"],
        ]
        for bad_id in invalid_ids:
            with self.subTest(bad_id=bad_id):
                with self.assertRaises(ValueError):
                    validate_target_id(bad_id)

    def test_is_valid_target_id(self):
        valid_id = "U79b78adfc1c2eacfe1a004bc0beea7f1"
        self.assertTrue(is_valid_target_id(valid_id))
        self.assertFalse(is_valid_target_id("invalid-id"))
        self.assertFalse(is_valid_target_id(None))
        self.assertFalse(is_valid_target_id(""))

    def test_sanitize_text(self):
        # HTML escaping
        raw_xss = "<script>alert('xss')</script>"
        sanitized = sanitize_text(raw_xss)
        self.assertEqual(sanitized, "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")

        # Control characters removal
        with_ctrl = "Hello\x00\x08\x1fWorld\x7f"
        self.assertEqual(sanitize_text(with_ctrl), "HelloWorld")

        # Max length
        long_text = "A" * 150
        self.assertEqual(len(sanitize_text(long_text, max_length=50)), 50)

        # Empty and non-string handling
        self.assertEqual(sanitize_text(None), "")
        self.assertEqual(sanitize_text(123), "")

    def test_sanitize_url(self):
        # Valid URLs
        http_url = "http://example.com/profile.png"
        https_url = "https://profile.line-scdn.net/abc123xyz"
        self.assertEqual(sanitize_url(http_url), http_url)
        self.assertEqual(sanitize_url(https_url), https_url)

        # Dangerous or invalid schemes
        self.assertEqual(sanitize_url("javascript:alert(1)"), "")
        self.assertEqual(sanitize_url("file:///etc/passwd"), "")
        self.assertEqual(sanitize_url("data:text/html,<script>alert(1)</script>"), "")
        self.assertEqual(sanitize_url("ftp://example.com/pic.jpg"), "")
        self.assertEqual(sanitize_url("not a url"), "")
        self.assertEqual(sanitize_url(None), "")

    def test_sanitize_message(self):
        normal_msg = "สรุปเวลาทำงาน 09:00"
        self.assertEqual(sanitize_message(normal_msg), normal_msg)

        # Null bytes stripped
        null_msg = "สวัสดี\x00ครับ"
        self.assertEqual(sanitize_message(null_msg), "สวัสดีครับ")

        # Max length (LINE 5000 chars)
        long_msg = "X" * 6000
        self.assertEqual(len(sanitize_message(long_msg, max_length=5000)), 5000)

        # Non-string
        self.assertEqual(sanitize_message(None), "")


if __name__ == "__main__":
    unittest.main()
