"""สร้างข้อความสรุปสำหรับส่ง LINE"""
THAI_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
               "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def thai_date(d):
    return f"วัน{THAI_DAYS[d.weekday()]}ที่ {d.day} {THAI_MONTHS[d.month - 1]} {d.year + 543}"


def hm(dt):
    return dt.strftime("%H:%M") if dt else "-"


def _who(r):
    return f"{r.person.name} ({r.person.code})" if r.person.code and r.person.code != r.person.name else r.person.name


def build_message(summary, company="", now=None, show_present=True):
    s = summary
    present, late = s.by("present"), s.by("late")
    absent, leave, pending = s.by("absent"), s.by("leave"), s.by("pending")
    counted = [r for r in s.results if r.status != "dayoff"]

    lines = [f"📋 สรุปการมาทำงาน{(' ' + company) if company else ''}", thai_date(s.day)]
    if now:
        lines[-1] += f" (ข้อมูลถึง {now:%H:%M} น.)"
    if not s.is_workday:
        lines.append(f"🏖 {s.holiday or 'วันหยุด'}")
    lines.append("")
    lines.append(f"👥 ทั้งหมด {len(counted)} คน")
    lines.append(f"✅ มา {len(present) + len(late)}  ⏰ สาย {len(late)}  ❌ ขาด {len(absent)}  📝 ลา {len(leave)}")
    if pending:
        lines.append(f"🕐 ยังไม่ถึงเวลาเข้างาน {len(pending)}")

    def section(title, items, fmt):
        if items:
            lines.append("")
            lines.append(title)
            lines.extend(f"• {fmt(r)}" for r in items)

    section("⏰ มาสาย", sorted(late, key=lambda r: -r.late_minutes),
            lambda r: f"{_who(r)} เข้า {hm(r.first_scan)} สาย {r.late_minutes} นาที")
    section("❌ ขาด / ยังไม่สแกน" if s.day == (now.date() if now else None) else "❌ ขาด", absent,
            lambda r: _who(r))
    section("📝 ลา", leave,
            lambda r: f"{_who(r)} - {r.leave_name}" + (f" (สแกน {hm(r.first_scan)})" if r.first_scan else ""))
    if show_present:
        section("✅ มาตรงเวลา", present,
                lambda r: f"{_who(r)} {hm(r.first_scan)}" + (f" - {hm(r.last_scan)}" if r.last_scan else ""))
    return "\n".join(lines)
