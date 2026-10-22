"""ส่งข้อความผ่าน LINE Messaging API (แทน LINE Notify ที่ปิดบริการแล้ว)"""
import logging
import uuid

import requests

log = logging.getLogger(__name__)

API = "https://api.line.me/v2/bot/message"
MAX_TEXT = 5000      # ความยาวสูงสุดของ text message
MAX_MESSAGES = 5     # จำนวน message สูงสุดต่อ 1 request


def split_text(text, limit=MAX_TEXT):
    """ตัดข้อความยาวเป็นหลายก้อนตามบรรทัด"""
    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) + 1 > limit:
            chunks.append(cur.rstrip("\n"))
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur.rstrip("\n"))
    return chunks


class LineClient:
    def __init__(self, token, targets):
        """targets: list ของ userId / groupId / roomId, ถ้าว่างจะ broadcast ให้ทุกคนที่เป็นเพื่อนกับ OA"""
        self.token = token
        self.targets = targets

    def send_text(self, text):
        messages = [{"type": "text", "text": t} for t in split_text(text)]
        for i in range(0, len(messages), MAX_MESSAGES):
            batch = messages[i:i + MAX_MESSAGES]
            if self.targets:
                for to in self.targets:
                    self._post("push", {"to": to, "messages": batch})
            else:
                self._post("broadcast", {"messages": batch})

    def _post(self, endpoint, body):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            # ถ้า retry ด้วย key เดิม LINE จะไม่ส่งซ้ำ
            "X-Line-Retry-Key": str(uuid.uuid4()),
        }
        for attempt in range(3):
            try:
                r = requests.post(f"{API}/{endpoint}", json=body, headers=headers, timeout=15)
            except requests.RequestException as e:
                log.warning("LINE %s ล้มเหลว (ครั้งที่ %d): %s", endpoint, attempt + 1, e)
                continue
            if r.status_code == 200 or r.status_code == 409:  # 409 = ส่งไปแล้วด้วย retry key นี้
                log.info("ส่ง LINE %s สำเร็จ%s", endpoint, f" -> {body.get('to')}" if "to" in body else "")
                return
            if r.status_code < 500 and r.status_code != 429:
                raise RuntimeError(f"LINE {endpoint} error {r.status_code}: {r.text}")
            log.warning("LINE %s ตอบ %d (ครั้งที่ %d): %s", endpoint, r.status_code, attempt + 1, r.text)
        raise RuntimeError(f"LINE {endpoint} ส่งไม่สำเร็จหลังลอง 3 ครั้ง")


def get_profile(token, user_id):
    """ดึงชื่อและรูปโปรไฟล์ของผู้ใช้จาก LINE"""
    try:
        r = requests.get(
            f"https://api.line.me/v2/bot/profile/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.warning("ดึง profile %s ไม่สำเร็จ: %s", user_id, e)
    return {}


def get_group_summary(token, group_id):
    """ดึงชื่อกลุ่มและรูปกลุ่มจาก LINE"""
    try:
        r = requests.get(
            f"https://api.line.me/v2/bot/group/{group_id}/summary",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.warning("ดึง group summary %s ไม่สำเร็จ: %s", group_id, e)
    return {}


def reply_text(token, reply_token, text):
    """ตอบกลับข้อความอัตโนมัติผ่าน replyToken (ฟรี ไม่คิดโควต้า push)"""
    if not reply_token:
        return
    try:
        body = {
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": text}]
        }
        requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=5
        )
    except Exception as e:
        log.warning("LINE reply ล้มเหลว: %s", e)

