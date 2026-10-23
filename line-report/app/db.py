"""
อ่านข้อมูลจาก DB Synctime / hiptime ด้วย SQLAlchemy ORM (อ่านอย่างเดียว)
รองรับทั้ง Windows Authentication (บน Windows 7) และ SQL Server Authentication (sa)
พร้อมโหมด Mock สำหรับทดสอบแบบไม่ต้องต่อ SQL Server
"""
from __future__ import annotations
import logging
import platform
import sys
from collections import defaultdict
from datetime import timedelta
from urllib.parse import quote_plus
from typing import Dict, List, Optional

from sqlalchemy import create_engine, select, or_, text
from sqlalchemy.orm import sessionmaker

from attendance import Person, Shift as ShiftDTO, parse_date, parse_dt, parse_hm
from mock_db import MockSynctimeDB
from models import (
    Holiday as HolidayModel,
    Leave as LeaveModel,
    Level as LevelModel,
    School as SchoolModel,
    Shift as ShiftModel,
    Student as StudentModel,
    StudentShift as StudentShiftModel,
    TranLeave as TranLeaveModel,
    Transcantime as TranscantimeModel,
)

log = logging.getLogger("line-db")


class SynctimeDB:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1433,
        user: str = "sa",
        password: str = "",
        database: str = "hiptime",
        auth_type: str = "auto",
        mock: bool = False,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database or "hiptime"
        self.auth_type = auth_type
        self.mock = mock
        self._engine = None
        self._session_factory = None

        if self.mock or self.host.lower() == "mock":
            self.mock_impl = MockSynctimeDB()
        else:
            self.mock_impl = None
            self._init_engine()

    def _init_engine(self):
        # ตรวจสอบการเลือก Driver ระหว่าง Windows Auth หรือ SQL Auth
        is_windows = platform.system().lower() == "windows"
        use_win_auth = (
            self.auth_type == "windows"
            or (self.auth_type == "auto" and is_windows and not self.password)
        )

        db_url = None
        if use_win_auth:
            # ใช้ Windows Authentication ผ่าน pyodbc (มี Driver มากับ Windows 7)
            server_str = self.host
            if "\\" not in server_str and self.port and self.port != 1433:
                server_str = f"{self.host},{self.port}"
            odbc_params = f"DRIVER={{SQL Server}};SERVER={server_str};DATABASE={self.database};Trusted_Connection=yes;"
            db_url = f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_params)}"
            log.info("ตั้งค่าเชื่อมต่อ SQL Server ด้วย Windows Authentication: %s (DB: %s)", server_str, self.database)
        else:
            # ใช้ SQL Server Authentication (sa + password)
            safe_pass = quote_plus(self.password or "")
            # กรณี host มี backslash เช่น SS-PC\SQLEXPRESS บน pymssql
            clean_host = self.host
            db_url = f"mssql+pymssql://{self.user}:{safe_pass}@{clean_host}:{self.port}/{self.database}?charset=utf8"
            log.info("ตั้งค่าเชื่อมต่อ SQL Server ด้วย SQL Auth (user=%s, host=%s, db=%s)", self.user, clean_host, self.database)

        self._engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"login_timeout": 8, "timeout": 30}
        )
        self._session_factory = sessionmaker(bind=self._engine)

    def test_connection(self) -> Dict:
        """ทดสอบการเชื่อมต่อฐานข้อมูล พร้อมส่งข้อความวินิจฉัยภาษาไทยหากผิดพลาด"""
        if self.mock_impl:
            return self.mock_impl.test_connection()

        try:
            with self._engine.connect() as conn:
                res = conn.execute(text("SELECT @@VERSION AS ver, DB_NAME() AS db")).first()
                ver_str = str(res[0]) if res else "Unknown"
                db_str = str(res[1]) if res else self.database

                school_row = self.school()
                people_count = len(self.people())

                return {
                    "ok": True,
                    "message": "เชื่อมต่อฐานข้อมูล SQL Server สำเร็จเรียบร้อย",
                    "server_version": ver_str.split("\n")[0],
                    "database": db_str,
                    "school_name": school_row.get("schoolname") or "ไม่ได้ตั้งชื่อบริษัท/โรงเรียน",
                    "employee_count": people_count,
                }
        except Exception as e:
            err_msg = str(e)
            advice = "ตรวจสอบการตั้งค่า IP/Port และชื่อ Instance ของ SQL Server"
            if "Login failed" in err_msg:
                advice = "รหัสผ่าน SQL Server ('sa') ไม่ถูกต้อง หรือสิทธิ์ผู้ใช้ Windows ไม่มีสิทธิ์เข้าถึง DB"
            elif "Adaptive Server is unavailable" in err_msg or "Cannot connect" in err_msg or "Could not open a connection" in err_msg:
                advice = "ไม่สามารถติดต่อ SQL Server ได้: ตรวจสอบว่าเปิด Service SQL Server หรือยัง, และเปิดพอร์ต 1433 ใน SQL Server Configuration Manager หรือยัง"
            elif "Cannot open database" in err_msg:
                advice = f"ไม่พบฐานข้อมูล '{self.database}': ตรวจสอบชื่อ DB ในโปรแกรม HIP Time ว่าตั้งชื่ออะไร (เช่น hiptime หรือ Synctime)"

            log.error("ทดสอบเชื่อมต่อฐานข้อมูลไม่สำเร็จ: %s | คำแนะนำ: %s", err_msg, advice)
            return {
                "ok": False,
                "error": err_msg,
                "advice": advice,
                "host": self.host,
                "database": self.database,
            }

    def _session(self):
        if self.mock_impl:
            raise RuntimeError("Mock DB doesn't use raw session")
        return self._session_factory()

    def school(self) -> Dict:
        if self.mock_impl:
            return self.mock_impl.school()
        with self._session() as session:
            stmt = (
                select(SchoolModel)
                .where(or_(SchoolModel.active == 1, SchoolModel.active.is_(None)))
                .order_by(SchoolModel.id)
                .limit(1)
            )
            row = session.scalars(stmt).first()
            if not row:
                return {}
            return {
                "id": row.id,
                "schoolcode": row.schoolcode,
                "schoolname": row.schoolname,
                "starttime": row.starttime,
                "endtime": row.endtime,
                "monwork": row.monwork,
                "tuework": row.tuework,
                "wedwork": row.wedwork,
                "thuwork": row.thuwork,
                "friwork": row.friwork,
                "satwork": row.satwork,
                "sunwork": row.sunwork,
                "active": row.active,
            }

    def people(self, levels=None) -> List[Person]:
        if self.mock_impl:
            return self.mock_impl.people(levels)
        with self._session() as session:
            stmt = select(StudentModel).where(
                or_(StudentModel.active == 1, StudentModel.active.is_(None)),
                StudentModel.enrollnumber.is_not(None),
                StudentModel.enrollnumber > 0
            )
            if levels:
                stmt = stmt.where(StudentModel.levelcode.in_(levels))

            students = session.scalars(stmt).all()
            return [
                Person(
                    enroll=int(s.enrollnumber),
                    code=(s.studentcode or "").strip(),
                    name=(s.studentname or "").strip() or str(s.enrollnumber),
                    level=s.levelcode,
                    shift_code=s.shiftcode
                )
                for s in students
            ]

    def level_names(self) -> Dict[str, str]:
        if self.mock_impl:
            return {"ADMIN": "ผู้บริหาร", "OFFICE": "สำนักงาน", "SECURITY": "รปภ.", "TECH": "ไอที/ช่าง"}
        with self._session() as session:
            levels = session.scalars(select(LevelModel)).all()
            return {l.levelcode: l.levelname for l in levels}

    def shifts(self) -> Dict[str, ShiftDTO]:
        if self.mock_impl:
            return self.mock_impl.shifts()
        with self._session() as session:
            shifts = session.scalars(select(ShiftModel)).all()
            return {
                s.shiftcode: ShiftDTO(
                    s.shiftcode,
                    s.shiftname or s.shiftcode,
                    parse_hm(s.starttime),
                    parse_hm(s.endtime)
                )
                for s in shifts
            }

    def scans(self, day) -> Dict[int, List]:
        if self.mock_impl:
            return self.mock_impl.scans(day)
        with self._session() as session:
            cutoff = day - timedelta(days=1)
            stmt = select(
                TranscantimeModel.enrollnumber,
                TranscantimeModel.datetimescan
            ).where(TranscantimeModel.adddate >= cutoff)

            rows = session.execute(stmt).all()
            out, bad = defaultdict(list), 0
            for enrollnumber, datetimescan in rows:
                dt = parse_dt(datetimescan)
                if dt is None:
                    bad += 1
                    continue
                if dt.date() == day and enrollnumber is not None:
                    out[int(enrollnumber)].append(dt)

            if bad:
                log.warning("แปลง datetimescan ไม่ได้ %d แถว (ดูด้วย: python main.py --check)", bad)
            return out

    def daily_shift(self, day) -> Dict[int, str]:
        if self.mock_impl:
            return self.mock_impl.daily_shift(day)
        with self._session() as session:
            rows = session.execute(
                select(StudentShiftModel.enrollnumber, StudentShiftModel.tdate, StudentShiftModel.shiftcode)
            ).all()
            return {
                int(enroll): shift
                for enroll, tdate, shift in rows
                if enroll and parse_date(tdate) == day
            }

    def leaves(self, day) -> Dict[str, str]:
        if self.mock_impl:
            return self.mock_impl.leaves(day)
        with self._session() as session:
            leaves_master = session.scalars(select(LeaveModel)).all()
            names = {l.leavecode: l.leavename for l in leaves_master}

            tran_leaves = session.scalars(select(TranLeaveModel)).all()
            return {
                (t.studentcode or "").strip(): names.get(t.leavecode) or t.leavecode or "ลา"
                for t in tran_leaves
                if parse_date(t.leavedate) == day
            }

    def holidays(self) -> Dict:
        if self.mock_impl:
            return self.mock_impl.holidays()
        with self._session() as session:
            hols = session.scalars(select(HolidayModel)).all()
            return {
                parse_date(h.holdate): h.holreason or "วันหยุด"
                for h in hols
                if parse_date(h.holdate)
            }

    def check(self) -> Dict:
        if self.mock_impl:
            return self.mock_impl.check()
        with self._session() as session:
            scans = session.scalars(
                select(TranscantimeModel.datetimescan)
                .order_by(TranscantimeModel.id.desc())
                .limit(2000)
            ).all()
            samples = list(scans[:10])
            bad = [s for s in scans if parse_dt(s) is None]

            tdates = list(session.scalars(
                select(StudentShiftModel.tdate)
                .order_by(StudentShiftModel.id.desc())
                .limit(5)
            ).all())

            ldates = list(session.scalars(
                select(TranLeaveModel.leavedate)
                .order_by(TranLeaveModel.id.desc())
                .limit(5)
            ).all())

            return dict(
                scan_rows=len(scans),
                scan_samples=samples,
                scan_unparsed=bad[:10],
                unparsed_count=len(bad),
                studentshift_tdate=tdates,
                tranleave_leavedate=ldates
            )
