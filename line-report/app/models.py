"""
SQLAlchemy ORM Models สำหรับตารางใน DB Synctime (HIP TIME 4.0)
"""
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class School(Base):
    __tablename__ = "School"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schoolcode: Mapped[str | None] = mapped_column(String(50))
    schoolname: Mapped[str | None] = mapped_column(String(255))
    starttime: Mapped[str | None] = mapped_column(String(50))
    endtime: Mapped[str | None] = mapped_column(String(50))
    monwork: Mapped[int | None] = mapped_column(Integer, default=1)
    tuework: Mapped[int | None] = mapped_column(Integer, default=1)
    wedwork: Mapped[int | None] = mapped_column(Integer, default=1)
    thuwork: Mapped[int | None] = mapped_column(Integer, default=1)
    friwork: Mapped[int | None] = mapped_column(Integer, default=1)
    satwork: Mapped[int | None] = mapped_column(Integer, default=0)
    sunwork: Mapped[int | None] = mapped_column(Integer, default=0)
    active: Mapped[int | None] = mapped_column(Integer, default=1)
    autodownload: Mapped[int | None] = mapped_column(Integer, default=0)


class Student(Base):
    __tablename__ = "Student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollnumber: Mapped[int | None] = mapped_column(BigInteger)
    studentcode: Mapped[str | None] = mapped_column(String(50))
    studentname: Mapped[str | None] = mapped_column(String(255))
    levelcode: Mapped[str | None] = mapped_column(String(50))
    shiftcode: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[int | None] = mapped_column(Integer, default=1)


class Level(Base):
    __tablename__ = "Level"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    levelcode: Mapped[str] = mapped_column(String(50))
    levelname: Mapped[str | None] = mapped_column(String(255))


class Shift(Base):
    __tablename__ = "Shift"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shiftcode: Mapped[str] = mapped_column(String(50))
    shiftname: Mapped[str | None] = mapped_column(String(255))
    starttime: Mapped[str | None] = mapped_column(String(50))
    endtime: Mapped[str | None] = mapped_column(String(50))


class Transcantime(Base):
    __tablename__ = "Transcantime"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    enrollnumber: Mapped[int | None] = mapped_column(BigInteger)
    datetimescan: Mapped[str | None] = mapped_column(String(50))
    adddate: Mapped[datetime | None] = mapped_column(DateTime)


class StudentShift(Base):
    __tablename__ = "StudentShift"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    enrollnumber: Mapped[int | None] = mapped_column(BigInteger)
    tdate: Mapped[str | None] = mapped_column(String(50))
    shiftcode: Mapped[str | None] = mapped_column(String(50))


class Leave(Base):
    __tablename__ = "Leave"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    leavecode: Mapped[str] = mapped_column(String(50))
    leavename: Mapped[str | None] = mapped_column(String(255))


class TranLeave(Base):
    __tablename__ = "TranLeave"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    studentcode: Mapped[str | None] = mapped_column(String(50))
    leavedate: Mapped[str | None] = mapped_column(String(50))
    leavecode: Mapped[str | None] = mapped_column(String(50))


class Holiday(Base):
    __tablename__ = "Holiday"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holdate: Mapped[str | None] = mapped_column(String(50))
    holreason: Mapped[str | None] = mapped_column(String(255))
