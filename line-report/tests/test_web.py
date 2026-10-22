import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import recipients  # noqa: E402
from web import (  # noqa: E402
    RequestHandler,
    WebState,
    create_session,
    get_web_credentials,
    is_valid_session,
)


class TestWebAuthAndAPI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        recipients.DATA_DIR = self.test_dir
        recipients.DATA_FILE = os.path.join(self.test_dir, "recipients.json")
        WebState.sessions.clear()
        os.environ["WEB_USERNAME"] = "testadmin"
        os.environ["WEB_PASSWORD"] = "testpass123"

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        WebState.sessions.clear()

    def test_credentials_and_session(self):
        user, pwd = get_web_credentials()
        self.assertEqual(user, "testadmin")
        self.assertEqual(pwd, "testpass123")

        # Session creation & validation
        token = create_session()
        self.assertTrue(is_valid_session(token))
        self.assertFalse(is_valid_session("invalid-token"))

    def test_recipients_api_integration(self):
        uid = "U79b78adfc1c2eacfe1a004bc0beea7f1"
        recipients.add_recipient(uid, "หัวหน้างาน")
        
        all_r = recipients.get_recipients()
        self.assertEqual(len(all_r), 1)
        self.assertEqual(all_r[0]["id"], uid)
        self.assertEqual(all_r[0]["name"], "หัวหน้างาน")


if __name__ == "__main__":
    unittest.main()
