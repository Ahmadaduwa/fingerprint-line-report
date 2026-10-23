"""
จัดการการตั้งค่าระบบผ่าน Web UI และบันทึกใน data/settings.json
ค่าเริ่มต้น:
- เวลาตัดสาย: 07:30 น.
- เวลา Auto Download ของ HIP: 09:00 น.
- เวลาส่งสรุปรายงานเข้า LINE: 09:30 น.
- ฐานข้อมูล: hiptime (รองรับทั้ง Windows Auth และ SQL Auth)
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict, List

log = logging.getLogger("line-settings")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "late_time": "07:30",
    "auto_download_time": "09:00",
    "send_times": ["09:30"],
    "late_grace_minutes": 0,
    "db_host": os.environ.get("DB_HOST", "127.0.0.1"),
    "db_port": int(os.environ.get("DB_PORT", "1433")),
    "db_name": os.environ.get("DB_NAME", "hiptime"),
    "db_user": os.environ.get("DB_USER", "sa"),
    "db_password": os.environ.get("DB_PASSWORD", ""),
    "db_auth": os.environ.get("DB_AUTH", "windows"),  # "windows" หรือ "sql"
    "company_name": os.environ.get("COMPANY_NAME", "STW_TeacherCheck"),
    "show_present": True,
    "send_on_dayoff": False,
    "mock_mode": False,
}


def load_settings() -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged
    except Exception as e:
        log.warning("ไม่สามารถอ่าน %s ได้ ใช้ค่าเริ่มต้น: %s", SETTINGS_FILE, e)
        return dict(DEFAULT_SETTINGS)


def save_settings(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    current = load_settings() if os.path.exists(SETTINGS_FILE) else dict(DEFAULT_SETTINGS)
    current.update(new_settings)

    # Validate some key settings
    if "send_times" in current and isinstance(current["send_times"], str):
        current["send_times"] = [x.strip() for x in current["send_times"].split(",") if x.strip()]
    if not current.get("send_times"):
        current["send_times"] = ["09:30"]

    tmp_file = SETTINGS_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, SETTINGS_FILE)
    log.info("บันทึกการตั้งค่าลง %s เรียบร้อยแล้ว", SETTINGS_FILE)
    return current


def get_setting(key: str, default: Any = None) -> Any:
    cfg = load_settings()
    return cfg.get(key, default)
