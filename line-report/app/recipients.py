"""
จัดการรายชื่อผู้รับรายงาน LINE (User ID / Group ID) บันทึกใน data/recipients.json
"""
import json
import logging
import os
import re
from datetime import datetime

log = logging.getLogger(__name__)

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
DATA_FILE = os.path.join(DATA_DIR, "recipients.json")

# รูปแบบ ID ของ LINE: U (User), C (Group), R (Room) ตามด้วย hex 32 ตัว
ID_PATTERN = re.compile(r"^[UCR][a-f0-9]{32}$", re.IGNORECASE)


def ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        initial = []
        # Fallback จาก env ถ้ามี
        default_id = os.environ.get("LINE_TARGET_ID") or os.environ.get("LINE_TO")
        if default_id and ID_PATTERN.match(default_id.strip()):
            initial.append({
                "id": default_id.strip(),
                "name": "ผู้ดูแลระบบ (Admin)",
                "active": True,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        save_recipients(initial)


def get_recipients():
    ensure_data_file()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("ไม่สามารถอ่าน %s: %s", DATA_FILE, e)
        return []


def save_recipients(recipients):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(recipients, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DATA_FILE)


def get_active_target_ids():
    """ดึงเฉพาะ ID ของคนที่เปิดใช้งาน (active=True)"""
    return [r["id"] for r in get_recipients() if r.get("active", True)]


def add_recipient(target_id: str, name: str = ""):
    target_id = target_id.strip()
    name = name.strip() or ("กลุ่ม" if target_id.startswith("C") else "ผู้ใช้งาน")
    
    if not ID_PATTERN.match(target_id):
        raise ValueError("รูปแบบ ID ไม่ถูกต้อง (ต้องขึ้นต้นด้วย U หรือ C หรือ R ตามด้วยรหัส 32 ตัวอักษร)")

    recipients = get_recipients()
    for r in recipients:
        if r["id"].lower() == target_id.lower():
            r["name"] = name
            r["active"] = True
            save_recipients(recipients)
            return r

    new_item = {
        "id": target_id,
        "name": name,
        "active": True,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    recipients.append(new_item)
    save_recipients(recipients)
    return new_item


def remove_recipient(target_id: str):
    recipients = get_recipients()
    filtered = [r for r in recipients if r["id"].lower() != target_id.lower()]
    if len(filtered) != len(recipients):
        save_recipients(filtered)
        return True
    return False


def toggle_recipient(target_id: str, active: bool):
    recipients = get_recipients()
    found = False
    for r in recipients:
        if r["id"].lower() == target_id.lower():
            r["active"] = bool(active)
            found = True
            break
    if found:
        save_recipients(recipients)
    return found
