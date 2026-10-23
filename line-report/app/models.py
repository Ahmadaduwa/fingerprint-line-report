from __future__ import annotations
from datetime import datetime
from typing import Optional
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
    schoolcode: Mapped[Optional[str]] = mapped_column(String(50))
    schoolname: Mapped[Optional[str]] = mapped_column(String(255))
    starttime: Mapped[Optional[str]] = mapped_column(String(50))
    endtime: Mapped[Optional[str]] = mapped_column(String(50))
    monwork: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    tuework: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    wedwork: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    thuwork: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    friwork: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    satwork: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    sunwork: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    active: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    autodownload: Mapped[Optional[int]] = mapped_column(Integer, default=0)


class Student(Base):
    __tablename__ = "Student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollnumber: Mapped[Optional[int]] = mapped_column(BigInteger)
    studentcode: Mapped[Optional[str]] = mapped_column(String(50))
    studentname: Mapped[Optional[str]] = mapped_column(String(255))
    levelcode: Mapped[Optional[str]] = mapped_column(String(50))
    shiftcode: Mapped[Optional[str]] = mapped_column(String(50))
    active: Mapped[Optional[int]] = mapped_column(Integer, default=1)


class Level(Base):
    __tablename__ = "Level"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    levelcode: Mapped[str] = mapped_column(String(50))
    levelname: Mapped[Optional[str]] = mapped_column(String(255))


class Shift(Base):
    __tablename__ = "Shift"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shiftcode: Mapped[str] = mapped_column(String(50))
    shiftname: Mapped[Optional[str]] = mapped_column(String(255))
    starttime: Mapped[Optional[str]] = mapped_column(String(50))
    endtime: Mapped[Optional[str]] = mapped_column(String(50))


class Transcantime(Base):
    __tablename__ = "Transcantime"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    enrollnumber: Mapped[Optional[int]] = mapped_column(BigInteger)
    datetimescan: Mapped[Optional[str]] = mapped_column(String(50))
    adddate: Mapped[Optional[datetime]] = mapped_column(DateTime)


class StudentShift(Base):
    __tablename__ = "StudentShift"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    enrollnumber: Mapped[Optional[int]] = mapped_column(BigInteger)
    tdate: Mapped[Optional[str]] = mapped_column(String(50))
    shiftcode: Mapped[Optional[str]] = mapped_column(String(50))


class Leave(Base):
    __tablename__ = "Leave"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    leavecode: Mapped[str] = mapped_column(String(50))
    leavename: Mapped[Optional[str]] = mapped_column(String(255))


class TranLeave(Base):
    __tablename__ = "TranLeave"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    studentcode: Mapped[Optional[str]] = mapped_column(String(50))
    leavedate: Mapped[Optional[str]] = mapped_column(String(50))
    leavecode: Mapped[Optional[str]] = mapped_column(String(50))


class Holiday(Base):
    __tablename__ = "Holiday"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holdate: Mapped[Optional[str]] = mapped_column(String(50))
    holreason: Mapped[Optional[str]] = mapped_column(String(255))

