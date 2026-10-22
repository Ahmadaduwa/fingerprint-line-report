"""อ่านข้อมูลจาก DB Synctime (อ่านอย่างเดียว ไม่เขียนอะไรลง DB)"""
import logging
from collections import defaultdict
from datetime import timedelta

import pymssql

from attendance import Person, Shift, parse_date, parse_dt, parse_hm

log = logging.getLogger(__name__)


class SynctimeDB:
    def __init__(self, host, port, user, password, database):
        self.cfg = dict(server=host, port=port, user=user, password=password,
                        database=database, login_timeout=10, timeout=60, charset="UTF-8")

    def _rows(self, sql, params=None):
        with pymssql.connect(**self.cfg) as conn:
            with conn.cursor(as_dict=True) as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()

    def school(self):
        rows = self._rows("SELECT TOP 1 * FROM School WHERE ISNULL(active, 1) = 1 ORDER BY id")
        return rows[0] if rows else {}

    def people(self, levels=None):
        rows = self._rows(
            "SELECT enrollnumber, studentcode, studentname, levelcode, shiftcode "
            "FROM Student WHERE ISNULL(active, 1) = 1 AND ISNULL(enrollnumber, 0) > 0")
        people = [Person(enroll=int(r["enrollnumber"]), code=(r["studentcode"] or "").strip(),
                         name=(r["studentname"] or "").strip() or str(r["enrollnumber"]),
                         level=r["levelcode"], shift_code=r["shiftcode"]) for r in rows]
        if levels:
            people = [p for p in people if p.level in levels]
        return people

    def level_names(self):
        return {r["levelcode"]: r["levelname"] for r in self._rows("SELECT levelcode, levelname FROM Level")}

    def shifts(self):
        return {r["shiftcode"]: Shift(r["shiftcode"], r["shiftname"] or r["shiftcode"],
                                      parse_hm(r["starttime"]), parse_hm(r["endtime"]))
                for r in self._rows("SELECT shiftcode, shiftname, starttime, endtime FROM Shift")}

    def scans(self, day):
        """
        เวลาสแกนของวัน day แยกตาม enrollnumber
        datetimescan เป็น text จึงกรองใน SQL ด้วย adddate (เวลาที่ดึงเข้า DB) ไว้ก่อน แล้วค่อยกรองวันจริงใน Python
        """
        rows = self._rows(
            "SELECT enrollnumber, datetimescan FROM Transcantime WHERE adddate >= %s",
            (day - timedelta(days=1),))
        out, bad = defaultdict(list), 0
        for r in rows:
            dt = parse_dt(r["datetimescan"])
            if dt is None:
                bad += 1
                continue
            if dt.date() == day:
                out[int(r["enrollnumber"])].append(dt)
        if bad:
            log.warning("แปลง datetimescan ไม่ได้ %d แถว (ดูด้วย: python main.py --check)", bad)
        return out

    def daily_shift(self, day):
        rows = self._rows("SELECT enrollnumber, tdate, shiftcode FROM StudentShift")
        return {int(r["enrollnumber"]): r["shiftcode"] for r in rows if parse_date(r["tdate"]) == day}

    def leaves(self, day):
        names = {r["leavecode"]: r["leavename"] for r in self._rows("SELECT leavecode, leavename FROM Leave")}
        rows = self._rows("SELECT studentcode, leavedate, leavecode FROM TranLeave")
        return {(r["studentcode"] or "").strip(): names.get(r["leavecode"]) or r["leavecode"] or "ลา"
                for r in rows if parse_date(r["leavedate"]) == day}

    def holidays(self):
        return {parse_date(r["holdate"]): r["holreason"] or "วันหยุด"
                for r in self._rows("SELECT holdate, holreason FROM Holiday")}

    def check(self):
        """สำหรับตรวจรูปแบบข้อมูลจริง: ตัวอย่าง datetimescan และจำนวนที่แปลงไม่ได้"""
        rows = self._rows("SELECT TOP 2000 datetimescan FROM Transcantime ORDER BY id DESC")
        samples = [r["datetimescan"] for r in rows[:10]]
        bad = [r["datetimescan"] for r in rows if parse_dt(r["datetimescan"]) is None]
        tdates = [r["tdate"] for r in self._rows("SELECT TOP 5 tdate FROM StudentShift ORDER BY id DESC")]
        ldates = [r["leavedate"] for r in self._rows("SELECT TOP 5 leavedate FROM TranLeave ORDER BY id DESC")]
        return dict(scan_rows=len(rows), scan_samples=samples, scan_unparsed=bad[:10],
                    unparsed_count=len(bad), studentshift_tdate=tdates, tranleave_leavedate=ldates)
