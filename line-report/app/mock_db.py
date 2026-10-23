"""
จำลองฐานข้อมูล Synctime / hiptime ของ HIP TIME 4.0
สร้างข้อมูลพนักงานตรงกับหน้าจอโปรแกรมจริง (เช่น ID 1, 2, 3, 10, 99, 159, 1111)
ใช้สำหรับทดสอบโหมด Offline หรือเมื่อไม่มี SQL Server เชื่อมต่อ
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from attendance import Person, Shift as ShiftDTO, parse_date, parse_dt, parse_hm

class MockSynctimeDB:
    def __init__(self, schoolname: str = "STW_TeacherCheck (จำลอง)", starttime: str = "07:30", endtime: str = "16:30"):
        self.schoolname = schoolname
        self.starttime = starttime
        self.endtime = endtime
        self.is_connected = True

    def test_connection(self) -> Dict:
        return {
            "ok": True,
            "message": "เชื่อมต่อโหมดจำลอง (Mock DB) สำเร็จ ข้อมูลเสมือนจริงพร้อมใช้งาน",
            "server": "MOCK-SERVER\\SQLEXPRESS (จำลอง)",
            "database": "hiptime",
            "driver": "MockDriver",
            "employee_count": len(self.people()),
        }

    def school(self) -> Dict:
        return {
            "id": 1,
            "schoolcode": "SCH01",
            "schoolname": self.schoolname,
            "starttime": self.starttime,
            "endtime": self.endtime,
            "monwork": 1,
            "tuework": 1,
            "wedwork": 1,
            "thuwork": 1,
            "friwork": 1,
            "satwork": 0,
            "sunwork": 0,
            "active": 1,
            "autodownload": 1,
        }

    def people(self, levels: Optional[List[str]] = None) -> List[Person]:
        # พนักงานจำลองอิงตามหน้าจอ HIP Time 4.0 จริง
        all_people = [
            Person(enroll=1, code="1", name="นายสมชาย (1)", level="ADMIN", shift_code="01"),
            Person(enroll=2, code="2", name="นางสาวสมศรี (2)", level="OFFICE", shift_code="01"),
            Person(enroll=3, code="3", name="นายมานะ (3)", level="OFFICE", shift_code="01"),
            Person(enroll=10, code="10", name="นายวิชัย (10)", level="SECURITY", shift_code="01"),
            Person(enroll=99, code="99", name="นางสุภา (99)", level="OFFICE", shift_code="01"),
            Person(enroll=159, code="jw", name="นายจิรวัฒน์ (jw)", level="TECH", shift_code="01"),
            Person(enroll=1111, code="ade", name="นายอดิศักดิ์ (ade)", level="TECH", shift_code="01"),
        ]
        if levels:
            all_people = [p for p in all_people if p.level in levels]
        return all_people

    def shifts(self) -> Dict[str, ShiftDTO]:
        return {
            "01": ShiftDTO(code="01", name="กะปกติ", start=parse_hm(self.starttime), end=parse_hm(self.endtime)),
            "99": ShiftDTO(code="99", name="กะวันหยุด", start=parse_hm("00:00"), end=parse_hm("00:00")),
        }

    def daily_shift(self, day: date) -> Dict[int, str]:
        return {}

    def leaves(self, day: date) -> Dict[str, str]:
        # จำลองพนักงานรหัส 99 ลาป่วยในวันทำงาน
        if day.weekday() < 5:
            return {"99": "ลาป่วย"}
        return {}

    def holidays(self) -> Dict[date, str]:
        return {}

    def scans(self, day: date) -> Dict[int, List[datetime]]:
        # วันหยุดไม่มีสแกน
        if day.weekday() >= 5:
            return {}

        # สร้างการสแกนจำลองตามเงื่อนไข 07:30
        # คนที่ 1: สแกน 07:15 -> ทันเวลา (Present)
        # คนที่ 2: สแกน 07:42 -> สาย (Late เพราะหลัง 07:30)
        # คนที่ 3: สแกน 07:25 -> ทันเวลา (Present)
        # คนที่ 159: สแกน 07:10 และ 16:35 -> ทันเวลา (Present)
        # คนที่ 1111: สแกน 07:55 -> สาย (Late)
        # คนที่ 10: ไม่สแกนเลย -> ขาด (Absent)
        # คนที่ 99: ลาป่วย (Leave)
        return {
            1: [datetime.combine(day, parse_hm("07:15")), datetime.combine(day, parse_hm("16:30"))],
            2: [datetime.combine(day, parse_hm("07:42"))],
            3: [datetime.combine(day, parse_hm("07:25"))],
            159: [datetime.combine(day, parse_hm("07:10")), datetime.combine(day, parse_hm("16:35"))],
            1111: [datetime.combine(day, parse_hm("07:55"))],
        }

    def check(self) -> Dict:
        return {
            "sample_transcantime": [
                {"enrollnumber": 1, "datetimescan": "2026-10-23 07:15:00"},
                {"enrollnumber": 2, "datetimescan": "2026-10-23 07:42:00"},
            ],
            "total_people": len(self.people()),
            "status": "Mock DB Ready",
        }
