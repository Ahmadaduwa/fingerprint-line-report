"""
Input validation and sanitization utilities
สำหรับตรวจสอบและทำความสะอาดข้อมูลนำเข้า (ป้องกัน XSS, Control Characters, Invalid IDs)
"""
import html
import re
from urllib.parse import urlparse

# รูปแบบ ID ของ LINE: U (User), C (Group), R (Room) ตามด้วย hex 32 ตัว
ID_PATTERN = re.compile(r"^[UCR][a-f0-9]{32}$", re.IGNORECASE)

# ตัวอักษรควบคุมที่ไม่อนุญาต (control characters ยกเว้น newline/tab)
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def validate_target_id(target_id: str) -> str:
    """
    ตรวจสอบและทำความสะอาด LINE Target ID
    คืนค่า target_id ที่ถูกต้อง หรือโยน ValueError ถ้าไม่ถูกต้อง
    """
    if not isinstance(target_id, str):
        raise ValueError("Target ID ต้องเป็นข้อความตัวอักษร")
    cleaned = target_id.strip()
    if not ID_PATTERN.match(cleaned):
        raise ValueError("รูปแบบ ID ไม่ถูกต้อง (ต้องขึ้นต้นด้วย U, C หรือ R ตามด้วยรหัส 32 ตัวอักษร)")
    return cleaned


def is_valid_target_id(target_id: str) -> bool:
    """ตรวจสอบว่า target_id ถูกต้องหรือไม่ โดยไม่โยน exception"""
    try:
        validate_target_id(target_id)
        return True
    except (ValueError, TypeError):
        return False


def sanitize_text(text: str, max_length: int = 100, escape: bool = True) -> str:
    """
    ทำความสะอาดข้อความทั่วไป (ชื่อผู้รับ, ชื่อตำแหน่ง, หมายเหตุ)
    - กำจัด null bytes และ control characters
    - ตัดช่องว่างหัวท้าย
    - ทำ HTML escape เพื่อป้องกัน XSS
    - จำกัดความยาวสูงสุด
    """
    if not isinstance(text, str):
        return ""
    cleaned = CONTROL_CHAR_PATTERN.sub("", text).strip()
    if escape:
        cleaned = html.escape(cleaned)
    return cleaned[:max_length]


def sanitize_url(url: str, max_length: int = 500) -> str:
    """
    ตรวจสอบและทำความสะอาด URL (เช่น รูปโปรไฟล์)
    อนุญาตเฉพาะ scheme http และ https เท่านั้น (ป้องกัน javascript: URI)
    """
    if not isinstance(url, str):
        return ""
    cleaned = url.strip()
    if not cleaned:
        return ""
    try:
        parsed = urlparse(cleaned)
        if parsed.scheme.lower() not in ("http", "https"):
            return ""
        return cleaned[:max_length]
    except Exception:
        return ""


def sanitize_message(text: str, max_length: int = 5000) -> str:
    """
    ทำความสะอาดข้อความที่จะส่งเข้า LINE
    จำกัดความยาวไม่เกินโควต้าของ LINE (5000 ตัวอักษร)
    """
    if not isinstance(text, str):
        return ""
    cleaned = text.replace("\x00", "").strip()
    return cleaned[:max_length]
