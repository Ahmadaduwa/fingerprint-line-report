import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from attendance import compute, parse_hm
from db import SynctimeDB
import log_buffer
from mock_db import MockSynctimeDB
import settings


class TestSettingsAndMock(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        settings.DATA_DIR = self.test_dir
        settings.SETTINGS_FILE = os.path.join(self.test_dir, "settings.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_settings_defaults_and_override(self):
        cfg = settings.load_settings()
        self.assertEqual(cfg["late_time"], "07:30")
        self.assertEqual(cfg["auto_download_time"], "09:00")
        self.assertEqual(cfg["send_times"], ["09:30"])
        self.assertEqual(cfg["db_name"], "hiptime")

        # Save update
        settings.save_settings({"late_time": "07:45", "send_times": ["09:30", "18:00"]})
        updated = settings.load_settings()
        self.assertEqual(updated["late_time"], "07:45")
        self.assertEqual(updated["send_times"], ["09:30", "18:00"])

    def test_mock_db_attendance_0730_late(self):
        mock_db = MockSynctimeDB()
        self.assertTrue(mock_db.test_connection()["ok"])

        # Test day: Monday (workday)
        test_day = date(2026, 10, 26)  # Monday
        now = datetime(2026, 10, 26, 9, 30)

        late_cutoff = parse_hm("07:30")
        summary = compute(
            day=test_day,
            people=mock_db.people(),
            scans=mock_db.scans(test_day),
            shifts=mock_db.shifts(),
            daily_shift=mock_db.daily_shift(test_day),
            leaves=mock_db.leaves(test_day),
            holidays=mock_db.holidays(),
            school=mock_db.school(),
            late_cutoff=late_cutoff,
            now=now,
        )

        # Person 1 scanned at 07:15 -> Present
        # Person 2 scanned at 07:42 -> Late (after 07:30)
        # Person 3 scanned at 07:25 -> Present
        # Person 10 no scan -> Absent
        # Person 99 leave -> Leave
        by_status = {s: [r.person.enroll for r in summary.by(s)] for s in ("present", "late", "absent", "leave")}
        self.assertIn(1, by_status["present"])
        self.assertIn(2, by_status["late"])
        self.assertIn(3, by_status["present"])
        self.assertIn(10, by_status["absent"])
        self.assertIn(99, by_status["leave"])

    def test_log_buffer_capture(self):
        buf = log_buffer.setup_logging(data_dir=self.test_dir)
        import logging
        test_log = logging.getLogger("test-logger")

        test_log.info("Info message for testing")
        test_log.warning("Warning message for testing")
        try:
            raise ValueError("Simulated error message")
        except Exception:
            test_log.exception("Caught exception for testing")

        logs = buf.get_logs(limit=10)
        self.assertGreaterEqual(len(logs), 3)

        error_logs = buf.get_logs(limit=10, level="ERROR")
        self.assertEqual(len(error_logs), 1)
        self.assertIn("Simulated error message", error_logs[0]["error_details"])

    def test_db_test_connection_mock(self):
        db = SynctimeDB(host="mock", mock=True)
        res = db.test_connection()
        self.assertTrue(res["ok"])
        self.assertEqual(res["database"], "hiptime")
        self.assertGreater(res["employee_count"], 0)


if __name__ == "__main__":
    unittest.main()
