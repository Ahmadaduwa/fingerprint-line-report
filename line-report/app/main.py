"""
สรุปการมา / สาย / ขาด / ลา จาก DB Synctime แล้วส่งเข้า LINE Messaging API
พร้อม Web UI จัดการผู้รับรายงาน (พอร์ต 8090)

  python main.py                      รันเป็น service (Scheduler + Web UI)
  python main.py --now                ส่งสรุปของวันนี้ทันที
  python main.py --date 2026-10-17    ส่งสรุปของวันที่ระบุ
  python main.py --dry-run [...]      แสดงข้อความ ไม่ส่ง LINE
  python main.py --check              ตรวจรูปแบบวันที่ในข้อมูลจริง
"""
import argparse
import json
import logging
import os
import threading
import time as _time
from datetime import date, datetime, timedelta

from attendance import compute, parse_hm
from db import SynctimeDB
from line_api import LineClient
import recipients
from report import build_message, thai_date
from web import WebState, run_web_server

log = logging.getLogger("line-report")


def env(name, default=None):
    v = os.environ.get(name, "").strip()
    return v if v else default


def env_list(name):
    return [x.strip() for x in env(name, "").split(",") if x.strip()]


def load_db():
    return SynctimeDB(host=env("DB_HOST", "sqlserver"), port=int(env("DB_PORT", "1433")),
                      user=env("DB_USER", "sa"), password=env("DB_PASSWORD", ""),
                      database=env("DB_NAME", "Synctime"))


def make_report(db, day, now):
    school = db.school()
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
        late_grace=int(env("LATE_GRACE_MINUTES", "0")),
        now=now,
    )
    company = env("COMPANY_NAME", (school.get("schoolname") or "").strip())

    if summary.is_workday and summary.total_scans == 0 and summary.by("absent"):
        # ไม่มีใครสแกนเลยทั้งวัน มักแปลว่ายังไม่ได้ดึง log จากเครื่องเข้า DB ไม่ใช่ทุกคนขาด
        return summary, (f"⚠️ สรุปการมาทำงาน {company}\n{thai_date(day)}\n\n"
                         "ยังไม่มีข้อมูลการสแกนของวันนี้ในระบบเลย\n"
                         "ตรวจสอบว่าโปรแกรม HIP TIME ดึงข้อมูลจากเครื่องสแกนแล้วหรือยัง")
    return summary, build_message(summary, company=company, now=now if day == now.date() else None,
                                  show_present=env("SHOW_PRESENT", "1") == "1")


def run_once(db, token, day, dry_run=False, now=None):
    now = now or datetime.now()
    summary, text = make_report(db, day, now)
    if not summary.is_workday and env("SEND_ON_DAYOFF", "0") != "1" and not summary.by("present"):
        log.info("%s เป็นวันหยุด ไม่ส่ง", day)
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


def next_run(times, now):
    cands = []
    for t in times:
        for d in (now.date(), now.date() + timedelta(days=1)):
            dt = datetime.combine(d, t)
            if dt > now:
                cands.append(dt)
    return min(cands) if cands else None


def serve(db, token):
    times = [t for t in (parse_hm(x) for x in env_list("SEND_TIMES") or ["09:00", "18:00"]) if t]
    log.info("เริ่ม service ส่งเวลา %s", ", ".join(t.strftime("%H:%M") for t in sorted(times)))

    web_port = int(env("WEB_PORT", "8090"))
    web_thread = threading.Thread(
        target=run_web_server,
        args=(db, token, times, web_port),
        daemon=True,
        name="web-server"
    )
    web_thread.start()

    while True:
        at = next_run(times, datetime.now())
        log.info("รอบถัดไป %s", at)
        while (wait := (at - datetime.now()).total_seconds()) > 0:
            _time.sleep(min(wait, 60))
        try:
            run_once(db, token, at.date(), now=at)
            WebState.last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            WebState.last_run_status = "ส่งสำเร็จตามรอบเวลา"
        except Exception as e:
            log.exception("ส่งสรุปไม่สำเร็จ")
            WebState.last_run_status = f"ส่งไม่สำเร็จ: {e}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--now", action="store_true", help="ส่งสรุปของวันนี้ทันที")
    ap.add_argument("--date", help="ส่งสรุปของวันที่ (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="แสดงข้อความ ไม่ส่ง LINE")
    ap.add_argument("--check", action="store_true", help="ตรวจรูปแบบวันที่ในข้อมูลจริง")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db = load_db()
    if args.check:
        print(json.dumps(db.check(), ensure_ascii=False, indent=2, default=str))
        return

    token = None
    if not args.dry_run:
        token = env("LINE_CHANNEL_ACCESS_TOKEN")
        if not token:
            raise SystemExit("ต้องตั้ง LINE_CHANNEL_ACCESS_TOKEN (หรือใช้ --dry-run)")

    if args.now or args.date or args.dry_run:
        day = date.fromisoformat(args.date) if args.date else date.today()
        run_once(db, token, day, dry_run=args.dry_run)
    else:
        serve(db, token)


if __name__ == "__main__":
    main()
