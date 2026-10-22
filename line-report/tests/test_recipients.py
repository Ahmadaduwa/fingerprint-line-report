import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import recipients  # noqa: E402
from recipients import (  # noqa: E402
    add_recipient,
    get_active_target_ids,
    get_recipients,
    remove_recipient,
    toggle_recipient,
)


class TestRecipients(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        recipients.DATA_DIR = self.test_dir
        recipients.DATA_FILE = os.path.join(self.test_dir, "recipients.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_add_and_get(self):
        uid = "U79b78adfc1c2eacfe1a004bc0beea7f1"
        res = add_recipient(uid, "ผอ.")
        self.assertEqual(res["id"], uid)
        self.assertEqual(res["name"], "ผอ.")
        
        all_r = get_recipients()
        self.assertEqual(len(all_r), 1)
        self.assertEqual(get_active_target_ids(), [uid])

    def test_sanitization_xss_in_name(self):
        uid = "U79b78adfc1c2eacfe1a004bc0beea7f1"
        res = add_recipient(uid, "<script>alert('xss')</script>")
        self.assertEqual(res["name"], "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")

    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            add_recipient("invalid-id", "Test")

    def test_toggle_and_remove(self):
        uid = "U79b78adfc1c2eacfe1a004bc0beea7f1"
        add_recipient(uid, "ผอ.")
        toggle_recipient(uid, False)
        self.assertEqual(get_active_target_ids(), [])
        
        removed = remove_recipient(uid)
        self.assertTrue(removed)
        self.assertEqual(len(get_recipients()), 0)


if __name__ == "__main__":
    unittest.main()
