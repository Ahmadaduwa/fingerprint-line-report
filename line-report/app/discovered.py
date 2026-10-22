"""
จัดการรายชื่อผู้ใช้/กลุ่ม LINE ที่แอดบอทหรือทักเข้ามา (Discovered via Webhook)
บันทึกใน data/discovered.json เพื่อให้แอดมินเลือกเพิ่มเข้าผู้รับรายงานได้ในคลิกเดียว
"""
import json
import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
DISCOVERED_FILE = os.path.join(DATA_DIR, "discovered.json")


def ensure_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DISCOVERED_FILE):
        with open(DISCOVERED_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def get_discovered():
    ensure_file()
    try:
        with open(DISCOVERED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("ไม่สามารถอ่าน %s: %s", DISCOVERED_FILE, e)
        return []


def save_discovered(items):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = DISCOVERED_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DISCOVERED_FILE)


def record_discovered(target_id: str, name: str = "", target_type: str = "user", picture_url: str = ""):
    target_id = target_id.strip()
    if not target_id:
        return None

    items = get_discovered()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in items:
        if item["id"].lower() == target_id.lower():
            if name:
                item["name"] = name
            if picture_url:
                item["picture_url"] = picture_url
            item["last_seen"] = now_str
            save_discovered(items)
            return item

    new_item = {
        "id": target_id,
        "name": name or ("กลุ่ม" if target_type == "group" else "ผู้ใช้งาน"),
        "type": target_type,
        "picture_url": picture_url or "",
        "first_seen": now_str,
        "last_seen": now_str,
    }
    # ใส่ไว้บนสุด
    items.insert(0, new_item)
    # เก็บสูงสุด 50 รายการล่าสุด
    items = items[:50]
    save_discovered(items)
    return new_item


def remove_discovered(target_id: str):
    items = get_discovered()
    filtered = [i for i in items if i["id"].lower() != target_id.lower()]
    if len(filtered) != len(items):
        save_discovered(filtered)
        return True
    return False
