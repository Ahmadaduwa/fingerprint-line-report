import sys
import unittest
from datetime import date, datetime, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from attendance import Person, Shift, compute, parse_dt  # noqa: E402
from line_api import split_text  # noqa: E402
from report import build_message  # noqa: E402

SCHOOL = {"starttime": "08:00", "endtime": "17:30", "monwork": 1, "tuework": 1, "wedwork": 1,
          "thuwork": 1, "friwork": 1, "satwork": 0, "sunwork": 0}
SHIFTS = {"01": Shift("01", "กะงานปกติ", time(8, 0), time(17, 0)),
          "99": Shift("99", "กะวันหยุด", time(0, 0), time(0, 0)),
          "N": Shift("N", "กะบ่าย", time(13, 0), time(22, 0))}
FRI = date(2026, 10, 16)


def people(*codes, shift="01"):
    return [Person(enroll=int(c), code=c, name=f"p{c}", shift_code=shift) for c in codes]


class ParseTest(unittest.TestCase):
    def test_formats(self):
        want = datetime(2026, 10, 16, 8, 5, 3)
        for s in ["2026-10-16 08:05:03", "2026/10/16 08:05:03", "16/10/2026 08:05:03",
                  "16-10-2026 08:05:03", "16/10/2569 08:05:03", "2026-10-16 08:05:03.000",
                  "10/16/2026 8:05:03 AM"]:
            self.assertEqual(parse_dt(s), want, s)
        self.assertIsNone(parse_dt("abc"))
        self.assertIsNone(parse_dt(None))


class ComputeTest(unittest.TestCase):
    def run_(self, ppl, scans, day=FRI, now=datetime(2026, 10, 16, 18, 0), **kw):
        args = dict(day=day, people=ppl, scans=scans, shifts=SHIFTS, daily_shift={}, leaves={},
                    holidays={}, school=SCHOOL, now=now)
        args.update(kw)
        return {r.person.code: r for r in compute(**args).results}

    def test_present_late_absent(self):
        r = self.run_(people("1", "2", "3"), {
            1: [datetime(2026, 10, 16, 7, 50), datetime(2026, 10, 16, 17, 5)],
            2: [datetime(2026, 10, 16, 8, 20)],
        })
        self.assertEqual(r["1"].status, "present")
        self.assertEqual(r["1"].last_scan, datetime(2026, 10, 16, 17, 5))
        self.assertEqual((r["2"].status, r["2"].late_minutes), ("late", 20))
        self.assertEqual(r["3"].status, "absent")

    def test_grace(self):
        r = self.run_(people("1"), {1: [datetime(2026, 10, 16, 8, 4)]}, late_grace=5)
        self.assertEqual(r["1"].status, "present")

    def test_leave_beats_late_and_absent(self):
        r = self.run_(people("1", "2"), {1: [datetime(2026, 10, 16, 13, 0)]},
                      leaves={"1": "ลากิจ", "2": "ลาป่วย"})
        self.assertEqual((r["1"].status, r["1"].leave_name), ("leave", "ลากิจ"))
        self.assertEqual(r["2"].status, "leave")

    def test_daily_shift_override_and_pending(self):
        now = datetime(2026, 10, 16, 9, 30)
        r = self.run_(people("1", "2"), {}, daily_shift={1: "N", 2: "99"}, now=now)
        self.assertEqual(r["1"].status, "pending")   # กะบ่ายยังไม่ถึงเวลา
        self.assertEqual(r["2"].status, "dayoff")    # กะวันหยุด

    def test_weekend_and_holiday(self):
        sat = date(2026, 10, 17)
        r = self.run_(people("1", "2"), {1: [datetime(2026, 10, 17, 9, 0)]}, day=sat)
        self.assertEqual((r["1"].status, r["2"].status), ("present", "dayoff"))
        r = self.run_(people("1"), {}, holidays={FRI: "วันปิยมหาราช"})
        self.assertEqual(r["1"].status, "dayoff")

    def test_message(self):
        s = compute(day=FRI, people=people("1", "2", "3"),
                    scans={1: [datetime(2026, 10, 16, 7, 55)], 2: [datetime(2026, 10, 16, 8, 30)]},
                    shifts=SHIFTS, daily_shift={}, leaves={}, holidays={}, school=SCHOOL,
                    now=datetime(2026, 10, 16, 18, 0))
        msg = build_message(s, company="HIP")
        self.assertIn("วันศุกร์ที่ 16 ต.ค. 2569", msg)
        self.assertIn("✅ มา 2  ⏰ สาย 1  ❌ ขาด 1  📝 ลา 0", msg)
        self.assertIn("• p2 (2) เข้า 08:30 สาย 30 นาที", msg)


class SplitTest(unittest.TestCase):
    def test_split(self):
        text = "\n".join(f"line {i:04d}" for i in range(2000))
        chunks = split_text(text)
        self.assertTrue(all(len(c) <= 5000 for c in chunks))
        self.assertEqual("\n".join(chunks), text)


if __name__ == "__main__":
    unittest.main()
