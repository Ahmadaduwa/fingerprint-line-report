"""
อ่านข้อมูลจาก DB Synctime ด้วย SQLAlchemy ORM (อ่านอย่างเดียว)
"""
import logging
from collections import defaultdict
from datetime import timedelta
from urllib.parse import quote_plus

from sqlalchemy import create_engine, select, or_
from sqlalchemy.orm import sessionmaker

from attendance import Person, Shift as ShiftDTO, parse_date, parse_dt, parse_hm
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

log = logging.getLogger(__name__)


class SynctimeDB:
    def __init__(self, host, port, user, password, database):
        safe_pass = quote_plus(password)
        db_url = f"mssql+pymssql://{user}:{safe_pass}@{host}:{port}/{database}?charset=utf8"
        self.engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"login_timeout": 10, "timeout": 60}
        )
        self.Session = sessionmaker(bind=self.engine)

    def _session(self):
        return self.Session()

    def school(self):
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

    def people(self, levels=None):
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

    def level_names(self):
        with self._session() as session:
            levels = session.scalars(select(LevelModel)).all()
            return {l.levelcode: l.levelname for l in levels}

    def shifts(self):
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

    def scans(self, day):
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

    def daily_shift(self, day):
        with self._session() as session:
            rows = session.execute(
                select(StudentShiftModel.enrollnumber, StudentShiftModel.tdate, StudentShiftModel.shiftcode)
            ).all()
            return {
                int(enroll): shift
                for enroll, tdate, shift in rows
                if enroll and parse_date(tdate) == day
            }

    def leaves(self, day):
        with self._session() as session:
            leaves_master = session.scalars(select(LeaveModel)).all()
            names = {l.leavecode: l.leavename for l in leaves_master}

            tran_leaves = session.scalars(select(TranLeaveModel)).all()
            return {
                (t.studentcode or "").strip(): names.get(t.leavecode) or t.leavecode or "ลา"
                for t in tran_leaves
                if parse_date(t.leavedate) == day
            }

    def holidays(self):
        with self._session() as session:
            hols = session.scalars(select(HolidayModel)).all()
            return {
                parse_date(h.holdate): h.holreason or "วันหยุด"
                for h in hols
                if parse_date(h.holdate)
            }

    def check(self):
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
