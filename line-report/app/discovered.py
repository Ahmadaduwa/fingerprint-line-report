"""
จัดการรายชื่อผู้ใช้/กลุ่ม LINE ที่แอดบอทหรือทักเข้ามา (Discovered via Webhook)
บันทึกใน data/discovered.json เพื่อให้แอดมินเลือกเพิ่มเข้าผู้รับรายงานได้ในคลิกเดียว
"""
import json
import logging
import os
from datetime import datetime

from sanitizer import is_valid_target_id, sanitize_text, sanitize_url, validate_target_id

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
    if not is_valid_target_id(target_id):
        return None

    cleaned_id = validate_target_id(target_id)
    default_name = "กลุ่ม" if target_type == "group" else "ผู้ใช้งาน"
    cleaned_name = sanitize_text(name, max_length=80) or default_name
    cleaned_pic = sanitize_url(picture_url)
    cleaned_type = "group" if target_type == "group" else "user"

    items = get_discovered()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in items:
        if item["id"].lower() == cleaned_id.lower():
            if cleaned_name:
                item["name"] = cleaned_name
            if cleaned_pic:
                item["picture_url"] = cleaned_pic
            item["last_seen"] = now_str
            save_discovered(items)
            return item

    new_item = {
        "id": cleaned_id,
        "name": cleaned_name,
        "type": cleaned_type,
        "picture_url": cleaned_pic,
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
    if not is_valid_target_id(target_id):
        return False
    items = get_discovered()
    filtered = [i for i in items if i["id"].lower() != target_id.strip().lower()]
    if len(filtered) != len(items):
        save_discovered(filtered)
        return True
    return False
