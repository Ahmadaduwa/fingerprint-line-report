"""คำนวณสถานะ มา / สาย / ขาด / ลา จากข้อมูล Synctime (ไม่ยุ่งกับ DB หรือ LINE)"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional

# รูปแบบวันที่ที่เจอได้ในโปรแกรม HIP (คอลัมน์เก็บเป็น text) — ลองเรียงตามลำดับ
_DT_FORMATS = [
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M",
    "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p",
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d",
]

WEEKDAY_COLS = ["monwork", "tuework", "wedwork", "thuwork", "friwork", "satwork", "sunwork"]


def parse_dt(value):
    """แปลง text วันที่/เวลา เป็น datetime รองรับปี พ.ศ. คืน None ถ้าแปลงไม่ได้"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    s = re.sub(r"\.\d+$", "", str(value).strip())
    for fmt in _DT_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
        except ValueError:
            continue
        if dt.year > 2400:  # พ.ศ.
            dt = dt.replace(year=dt.year - 543)
        return dt
    return None


def parse_date(value):
    dt = parse_dt(value)
    return dt.date() if dt else None


def parse_hm(value):
    """'08:00' -> time(8, 0)"""
    if not value:
        return None
    m = re.match(r"^\s*(\d{1,2})[:.](\d{2})", str(value))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return time(h, mi) if h < 24 and mi < 60 else None


@dataclass
class Shift:
    code: str
    name: str
    start: Optional[time]
    end: Optional[time]

    @property
    def is_dayoff(self):
        # กะวันหยุดของ HIP ตั้งเวลาเป็น 00:00–00:00 (เช่นกะ 99)
        return self.start == time(0, 0) and self.end == time(0, 0)


@dataclass
class Person:
    enroll: int
    code: str
    name: str
    level: Optional[str] = None
    shift_code: Optional[str] = None


@dataclass
class Result:
    person: Person
    status: str  # present | late | absent | leave | pending | dayoff
    first_scan: Optional[datetime] = None
    last_scan: Optional[datetime] = None
    late_minutes: int = 0
    shift: Optional[Shift] = None
    leave_name: Optional[str] = None


@dataclass
class Summary:
    day: date
    is_workday: bool
    holiday: Optional[str]
    results: list = field(default_factory=list)
    total_scans: int = 0


    def by(self, status):
        return [r for r in self.results if r.status == status]


def compute(day, people, scans, shifts, daily_shift, leaves, holidays, school,
            default_shift_code=None, late_grace=0, now=None, late_cutoff=None):
    """
    day          : date ที่จะสรุป
    people       : list[Person] (active)
    scans        : dict enroll -> list[datetime] (เฉพาะของวันนั้น)
    shifts       : dict shiftcode -> Shift
    daily_shift  : dict enroll -> shiftcode (StudentShift ของวันนั้น)
    leaves       : dict studentcode -> leave name (TranLeave ของวันนั้น)
    holidays     : dict date -> reason
    school       : dict แถว School (ใช้ starttime/endtime และวันทำงาน)
    late_cutoff  : time กำหนดเวลาตัดสาย เช่น time(7, 30)
    """
    now = now or datetime.now()
    holiday = holidays.get(day)
    weekday_on = bool(int(school.get(WEEKDAY_COLS[day.weekday()]) or 0))
    is_workday = weekday_on and holiday is None

    effective_start = late_cutoff or parse_hm(school.get("starttime")) or time(7, 30)
    school_shift = Shift("", "เวลาทำงานบริษัท", effective_start, parse_hm(school.get("endtime")))
    fallback = shifts.get(default_shift_code) if default_shift_code else None
    fallback = fallback or school_shift


    summary = Summary(day=day, is_workday=is_workday, holiday=holiday,
                      total_scans=sum(len(v) for v in scans.values()))

    for p in people:
        times = sorted(scans.get(p.enroll, []))
        code = daily_shift.get(p.enroll) or p.shift_code
        shift = shifts.get(code) if code else None
        shift = shift or fallback
        r = Result(person=p, status="", shift=shift,
                   first_scan=times[0] if times else None,
                   last_scan=times[-1] if len(times) > 1 else None)

        if p.code in leaves:
            r.status, r.leave_name = "leave", leaves[p.code]
        elif not is_workday or shift.is_dayoff:
            r.status = "present" if times else "dayoff"
        elif times:
            r.status = "present"
            if shift.start:
                due = datetime.combine(day, shift.start) + timedelta(minutes=late_grace)
                if r.first_scan > due:
                    r.status = "late"
                    r.late_minutes = int((r.first_scan - datetime.combine(day, shift.start)).total_seconds() // 60)
        elif day == now.date() and shift.start and now.time() < shift.start:
            r.status = "pending"
        else:
            r.status = "absent"
        summary.results.append(r)

    summary.results.sort(key=lambda r: (r.person.level or "", r.person.code))
    return summary
