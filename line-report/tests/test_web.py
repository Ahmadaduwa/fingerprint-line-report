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

    def test_validation_endpoints(self):
        import io

        class MockHandler(RequestHandler):
            def __init__(self, path, body=None, headers=None):
                self.path = path
                body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
                self.rfile = io.BytesIO(body_bytes)
                self.wfile = io.BytesIO()
                self.headers = headers or {}
                if body is not None:
                    self.headers["Content-Length"] = str(len(body_bytes))
                self.status_code = None
                self.response_headers = {}

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.response_headers[keyword] = value

            def end_headers(self):
                pass

            def get_json(self):
                return json.loads(self.wfile.getvalue().decode("utf-8"))

        # Test login invalid types
        h = MockHandler("/api/login", body={"username": 12345, "password": None})
        h.do_POST()
        self.assertEqual(h.status_code, 400)
        self.assertFalse(h.get_json()["ok"])

        # Create valid session for authenticated endpoints
        token = create_session()
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Test /api/recipients with invalid target_id
        h = MockHandler("/api/recipients", body={"id": "bad-id", "name": "Test"}, headers=auth_headers)
        h.do_POST()
        self.assertEqual(h.status_code, 400)
        self.assertFalse(h.get_json()["ok"])

        # Test /api/recipients/toggle with invalid ID
        h = MockHandler("/api/recipients/toggle", body={"id": "not-valid", "active": True}, headers=auth_headers)
        h.do_POST()
        self.assertEqual(h.status_code, 400)
        self.assertFalse(h.get_json()["ok"])

        # Test /api/recipients/delete with invalid ID
        h = MockHandler("/api/recipients/delete", body={"id": "not-valid"}, headers=auth_headers)
        h.do_POST()
        self.assertEqual(h.status_code, 400)
        self.assertFalse(h.get_json()["ok"])

        # Test /api/test-send with invalid target_id
        h = MockHandler("/api/test-send", body={"id": "bad-id-123", "text": "hello"}, headers=auth_headers)
        h.do_POST()
        self.assertEqual(h.status_code, 400)
        self.assertFalse(h.get_json()["ok"])


if __name__ == "__main__":
    unittest.main()
