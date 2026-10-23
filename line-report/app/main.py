"""
สรุปการมา / สาย / ขาด / ลา จาก DB Synctime/hiptime แล้วส่งเข้า LINE Messaging API
พร้อม Web UI จัดการผู้รับรายงาน, ตั้งค่าเวลา, และดู Log ข้อผิดพลาด (พอร์ต 8090)

  python main.py                      รันเป็น background service (Scheduler + Web UI)
  python main.py --mock               รันด้วยระบบจำลอง (ไม่ต้องต่อ SQL Server)
  python main.py --now                ส่งสรุปของวันนี้ทันที
  python main.py --date 2026-10-23    ส่งสรุปของวันที่ระบุ
  python main.py --dry-run [...]      แสดงข้อความ ไม่ส่ง LINE
  python main.py --check              ตรวจรูปแบบวันที่ในข้อมูลจริง
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import threading
import time as _time
from datetime import date, datetime, timedelta
from typing import List, Optional

from attendance import compute, parse_hm
from db import SynctimeDB
from line_api import LineClient
from log_buffer import setup_logging
import recipients
from report import build_message, thai_date
import settings
from web import WebState, run_web_server

# ติดตั้ง Logging ทั้ง File (data/app.log), Console, และ Memory Buffer สำหรับดูผ่านเว็บ
setup_logging()
log = logging.getLogger("line-report")


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name, "").strip()
    return v if v else default


def env_list(name: str) -> List[str]:
    return [x.strip() for x in (env(name, "") or "").split(",") if x.strip()]


def load_db(is_mock: bool = False) -> SynctimeDB:
    cfg = settings.load_settings()
    mock_active = is_mock or cfg.get("mock_mode", False) or env("DB_MOCK", "0") == "1"

    host = env("DB_HOST", cfg.get("db_host", "127.0.0.1"))
    port = int(env("DB_PORT", str(cfg.get("db_port", 1433))))
    user = env("DB_USER", cfg.get("db_user", "sa"))
    password = env("DB_PASSWORD", cfg.get("db_password", ""))
    database = env("DB_NAME", cfg.get("db_name", "hiptime"))
    auth_type = env("DB_AUTH", cfg.get("db_auth", "auto"))

    return SynctimeDB(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        auth_type=auth_type,
        mock=mock_active,
    )


def make_report(db: SynctimeDB, day: date, now: datetime):
    cfg = settings.load_settings()
    school = db.school()
    late_cutoff = parse_hm(cfg.get("late_time", "07:30"))

    summary = compute(
        day=day,
        people=db.people(levels=env_list("LEVELS") or None),
        scans=db.scans(day),
        shifts=db.shifts(),
        daily_shift=db.daily_shift(day),
        leaves=db.leaves(day),
        holidays=db.holidays(),
        school=school,
        default_shift_code=env("DEFAULT_SHIFT"),
        late_grace=int(cfg.get("late_grace_minutes", 0)),
        now=now,
        late_cutoff=late_cutoff,
    )
    company = cfg.get("company_name") or env("COMPANY_NAME", (school.get("schoolname") or "").strip())

    if summary.is_workday and summary.total_scans == 0 and summary.by("absent"):
        # ไม่มีใครสแกนเลยทั้งวัน มักแปลว่ายังไม่ได้ดึง log จากเครื่องเข้า DB
        return summary, (f"⚠️ สรุปการมาทำงาน {company}\n{thai_date(day)}\n\n"
                         "ยังไม่มีข้อมูลการสแกนของวันนี้ในระบบเลย\n"
                         "ตรวจสอบว่าโปรแกรม HIP TIME ดึงข้อมูลจากเครื่องสแกนแล้วหรือยัง (รอบ 09:00 น.)")

    show_present = cfg.get("show_present", True)
    return summary, build_message(summary, company=company, now=now if day == now.date() else None,
                                  show_present=show_present)


def run_once(db: SynctimeDB, token: Optional[str], day: date, dry_run: bool = False, now: Optional[datetime] = None):
    now = now or datetime.now()
    summary, text = make_report(db, day, now)
    cfg = settings.load_settings()

    if not summary.is_workday and not cfg.get("send_on_dayoff", False) and env("SEND_ON_DAYOFF", "0") != "1" and not summary.by("present"):
        log.info("%s เป็นวันหยุด ไม่ส่งรายงาน", day)
        return
    if dry_run or not token:
        print(text)
        return

    targets = recipients.get_active_target_ids()
    if not targets:
        # Fallback จาก env ถ้ายังไม่มีใน JSON
        targets = env_list("LINE_TO") or env_list("LINE_TARGET_ID")

    if not targets:
        log.warning("ไม่มีรายชื่อผู้รับที่เปิดใช้งาน (ข้ามการส่ง ไม่ broadcast)")
        return

    line = LineClient(token, targets)
    line.send_text(text)
    log.info("ส่งสรุปการมาทำงานเข้า LINE ไปยัง %d ผู้รับ เรียบร้อยแล้ว", len(targets))


def next_run(times: List, now: datetime):
    cands = []
    for t in times:
        for d in (now.date(), now.date() + timedelta(days=1)):
            dt = datetime.combine(d, t)
            if dt > now:
                cands.append(dt)
    return min(cands) if cands else None


def serve(db: SynctimeDB, token: Optional[str]):
    cfg = settings.load_settings()
    configured_times = cfg.get("send_times") or ["09:30"]
    times = [t for t in (parse_hm(x) for x in configured_times) if t]
    if not times:
        times = [parse_hm("09:30")]

    log.info("เริ่มระบบ Service ส่งรายงาน LINE ทุกวันเวลา: %s", ", ".join(t.strftime("%H:%M") for t in sorted(times)))

    web_port = int(env("WEB_PORT", "8090"))
    web_thread = threading.Thread(
        target=run_web_server,
        args=(db, token, times, web_port),
        daemon=True,
        name="web-server"
    )
    web_thread.start()

    while True:
        # อัปเดตเวลารอบถัดไปโดยคำนึงถึงการตั้งค่าล่าสุดจากหน้าเว็บ
        current_cfg = settings.load_settings()
        curr_times_raw = current_cfg.get("send_times") or ["09:30"]
        active_times = [t for t in (parse_hm(x) for x in curr_times_raw) if t] or times
        WebState.send_times = active_times

        at = next_run(active_times, datetime.now())
        log.info("รอบส่งรายงานถัดไป: %s", at)
        while (wait := (at - datetime.now()).total_seconds()) > 0:
            _time.sleep(min(wait, 30))

        try:
            run_once(db, token, at.date(), now=at)
            WebState.last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            WebState.last_run_status = "ส่งสำเร็จตามรอบเวลา"
        except Exception as e:
            log.exception("ส่งสรุปไม่สำเร็จ: %s", e)
            WebState.last_run_status = f"ส่งไม่สำเร็จ: {e}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--now", action="store_true", help="ส่งสรุปของวันนี้ทันที")
    ap.add_argument("--date", help="ส่งสรุปของวันที่ (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="แสดงข้อความ ไม่ส่ง LINE")
    ap.add_argument("--check", action="store_true", help="ตรวจรูปแบบวันที่ในข้อมูลจริง")
    ap.add_argument("--mock", action="store_true", help="รันด้วยฐานข้อมูลจำลอง (เสมือนจริง)")
    args = ap.parse_args()

    db = load_db(is_mock=args.mock)
    if args.check:
        print(json.dumps(db.check(), ensure_ascii=False, indent=2, default=str))
        return

    token = None
    if not args.dry_run:
        token = env("LINE_CHANNEL_ACCESS_TOKEN")
        if not token:
            log.warning("ยังไม่ได้ตั้ง LINE_CHANNEL_ACCESS_TOKEN (สามารถตั้งค่าหรือดูหน้าเว็บได้ที่ http://localhost:8090)")

    if args.now or args.date or args.dry_run:
        day = date.fromisoformat(args.date) if args.date else date.today()
        run_once(db, token, day, dry_run=args.dry_run)
    else:
        serve(db, token)


if __name__ == "__main__":
    main()
