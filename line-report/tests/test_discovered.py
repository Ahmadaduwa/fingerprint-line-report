import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import discovered  # noqa: E402


class TestDiscovered(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        discovered.DATA_DIR = self.test_dir
        discovered.DISCOVERED_FILE = os.path.join(self.test_dir, "discovered.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_record_and_get(self):
        uid = "U79b78adfc1c2eacfe1a004bc0beea7f1"
        item = discovered.record_discovered(uid, name="ครูสมชาย", target_type="user")
        self.assertIsNotNone(item)
        self.assertEqual(item["id"], uid)
        self.assertEqual(item["name"], "ครูสมชาย")

        all_d = discovered.get_discovered()
        self.assertEqual(len(all_d), 1)
        self.assertEqual(all_d[0]["id"], uid)

    def test_remove(self):
        uid = "U79b78adfc1c2eacfe1a004bc0beea7f1"
        discovered.record_discovered(uid, name="ครูสมชาย")
        removed = discovered.remove_discovered(uid)
        self.assertTrue(removed)
        self.assertEqual(len(discovered.get_discovered()), 0)


if __name__ == "__main__":
    unittest.main()
