import hmac
import json
import logging
import os
import secrets
import time
from datetime import date, datetime
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from discovered import get_discovered, record_discovered, remove_discovered
from line_api import get_group_summary, get_profile, reply_text
from recipients import add_recipient, get_active_target_ids, get_recipients, remove_recipient, toggle_recipient
from report import thai_date
from sanitizer import is_valid_target_id, sanitize_message, sanitize_text

log = logging.getLogger("line-web")

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class WebState:
    db = None
    token = ""
    send_times = []
    last_run_time = None
    last_run_status = "ยังไม่เคยส่ง"
    last_run_error = None
    # active sessions: {token: expire_timestamp}
    sessions = {}


def get_web_credentials():
    username = os.environ.get("WEB_USERNAME", "admin").strip() or "admin"
    password = os.environ.get("WEB_PASSWORD", "admin1234").strip() or "admin1234"
    return username, password


def create_session():
    # Session มีอายุ 7 วัน
    token = secrets.token_hex(24)
    expire_at = time.time() + (7 * 24 * 3600)
    WebState.sessions[token] = expire_at
    return token


def is_valid_session(token):
    if not token or token not in WebState.sessions:
        return False
    if time.time() > WebState.sessions[token]:
        del WebState.sessions[token]
        return False
    return True


def get_html_page():
    html_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>LINE Report Web UI</h1>"


class RequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200, set_cookie=None):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _get_auth_token(self):
        # 1. จาก Authorization Header
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        
        # 2. จาก Cookie
        cookie_header = self.headers.get("Cookie", "")
        if cookie_header:
            c = cookies.SimpleCookie()
            try:
                c.load(cookie_header)
                if "report_session" in c:
                    return c["report_session"].value
            except Exception:
                pass
        return None

    def _is_authenticated(self):
        token = self._get_auth_token()
        return is_valid_session(token)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("", "/", "/index.html"):
            self._send_html(get_html_page())
            return

        if path == "/api/me":
            auth = self._is_authenticated()
            username, _ = get_web_credentials()
            self._send_json({"authenticated": auth, "username": username if auth else None})
            return

        # ป้องกัน Endpoint เบื้องหลังด้วย Authentication
        if not self._is_authenticated():
            self._send_json({"error": "Unauthorized", "authenticated": False}, status=401)
            return

        if path == "/api/status":
            from main import make_report, next_run
            now = datetime.now()
            preview_text = ""
            stats = None
            company_name = ""
            
            if WebState.db:
                try:
                    summary, preview_text = make_report(WebState.db, now.date(), now)
                    company_name = (WebState.db.school().get("schoolname") or "").strip()
                    stats = {
                        "present": len(summary.by("present")),
                        "late": len(summary.by("late")),
                        "absent": len(summary.by("absent")),
                        "leave": len(summary.by("leave")),
                        "total_people": len(summary.results),
                        "total_scans": summary.total_scans,
                        "is_workday": summary.is_workday,
                    }
                except Exception as e:
                    preview_text = f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}"

            recipients = get_recipients()
            active_ids = get_active_target_ids()
            times = WebState.send_times or ["09:00", "18:00"]
            next_dt = next_run(times, now) if times else None

            data = {
                "company_name": company_name or "โรงเรียนแสงธรรมวิทยา",
                "today_thai": thai_date(now.date()),
                "recipients": recipients,
                "discovered": get_discovered(),
                "active_count": len(active_ids),
                "send_times": [t.strftime("%H:%M") if hasattr(t, "strftime") else str(t) for t in times],
                "next_run": next_dt.strftime("%Y-%m-%d %H:%M:%S") if next_dt else None,
                "last_run_time": WebState.last_run_time,
                "last_run_status": WebState.last_run_status,
                "attendance": stats,
                "preview_text": preview_text,
            }
            self._send_json(data)
            return

        self.send_error(404, "Not Found")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_json()

        # 1. LINE Webhook Endpoint (ไม่ต้องมี Token เพื่อให้ LINE ส่งเข้ามาได้)
        if path in ("/webhook", "/api/webhook"):
            events = payload.get("events", [])
            for ev in events:
                ev_type = ev.get("type")
                source = ev.get("source", {})
                src_type = source.get("type", "user")
                reply_token = ev.get("replyToken")

                if src_type == "user":
                    user_id = source.get("userId")
                    if user_id and is_valid_target_id(user_id):
                        prof = get_profile(WebState.token, user_id)
                        display_name = prof.get("displayName") or "ผู้ใช้งาน LINE"
                        pic = prof.get("pictureUrl") or ""
                        record_discovered(user_id, name=display_name, target_type="user", picture_url=pic)
                        if ev_type in ("follow", "message") and reply_token:
                            reply_text(
                                WebState.token,
                                reply_token,
                                f"สวัสดีครับคุณ {display_name} 👋\n\nระบบสรุปเวลาทำงานบันทึก LINE ID ของคุณแล้ว:\n{user_id}\n\nกรุณาแจ้งแอดมินให้กดเปิดรับรายงานในระบบครับ"
                            )
                elif src_type == "group":
                    group_id = source.get("groupId")
                    if group_id and is_valid_target_id(group_id):
                        grp = get_group_summary(WebState.token, group_id)
                        group_name = grp.get("groupName") or "กลุ่ม LINE"
                        pic = grp.get("pictureUrl") or ""
                        record_discovered(group_id, name=group_name, target_type="group", picture_url=pic)
                        if ev_type in ("join", "message") and reply_token:
                            reply_text(
                                WebState.token,
                                reply_token,
                                f"สวัสดีครับกลุ่ม {group_name} 👋\n\nระบบสรุปเวลาทำงานบันทึก Group ID แล้ว:\n{group_id}\n\nกรุณาแจ้งแอดมินให้กดเปิดรับรายงานในระบบครับ"
                            )
            self._send_json({"ok": True})
            return

        # 2. Login Endpoint (ไม่ต้องมี Token ก่อน)
        if path == "/api/login":
            raw_user = payload.get("username", "")
            raw_pass = payload.get("password", "")
            if not isinstance(raw_user, str) or not isinstance(raw_pass, str):
                self._send_json({"ok": False, "error": "รูปแบบข้อมูลไม่ถูกต้อง"}, status=400)
                return
            req_user = raw_user.strip()[:100]
            req_pass = raw_pass.strip()[:100]
            web_user, web_pass = get_web_credentials()

            if hmac.compare_digest(req_user, web_user) and hmac.compare_digest(req_pass, web_pass):
                token = create_session()
                cookie = f"report_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800"
                self._send_json({"ok": True, "token": token, "username": web_user}, set_cookie=cookie)
            else:
                self._send_json({"ok": False, "error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}, status=401)
            return

        # 3. Logout Endpoint
        if path == "/api/logout":
            token = self._get_auth_token()
            if token and token in WebState.sessions:
                del WebState.sessions[token]
            clear_cookie = "report_session=; Path=/; HttpOnly; Max-Age=0"
            self._send_json({"ok": True}, set_cookie=clear_cookie)
            return

        # ทุกคำขอที่เหลือต้องผ่าน Login แล้วเท่านั้น
        if not self._is_authenticated():
            self._send_json({"error": "Unauthorized", "authenticated": False}, status=401)
            return

        # 4. Discovered: เพิ่มเข้าผู้รับรายงาน
        if path == "/api/discovered/add-to-recipients":
            target_id = payload.get("id", "").strip()
            name = payload.get("name", "").strip()
            if not target_id:
                self._send_json({"ok": False, "error": "ไม่มี User ID"}, status=400)
                return
            try:
                item = add_recipient(target_id, name)
                self._send_json({"ok": True, "item": item, "recipients": get_recipients(), "discovered": get_discovered()})
            except ValueError as e:
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return

        # 5. Discovered: ลบออกจากรายการค้นพบ
        if path == "/api/discovered/delete":
            target_id = payload.get("id", "").strip()
            if not is_valid_target_id(target_id):
                self._send_json({"ok": False, "error": "รูปแบบ ID ไม่ถูกต้อง"}, status=400)
                return
            ok = remove_discovered(target_id)
            self._send_json({"ok": ok, "discovered": get_discovered()})
            return

        if path == "/api/recipients":
            target_id = payload.get("id", "").strip()
            name = payload.get("name", "").strip()
            if not target_id:
                self._send_json({"ok": False, "error": "กรุณาระบุ User ID หรือ Group ID"}, status=400)
                return
            try:
                item = add_recipient(target_id, name)
                self._send_json({"ok": True, "item": item, "recipients": get_recipients()})
            except ValueError as e:
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return

        if path == "/api/recipients/toggle":
            target_id = payload.get("id", "").strip()
            if not is_valid_target_id(target_id):
                self._send_json({"ok": False, "error": "รูปแบบ ID ไม่ถูกต้อง"}, status=400)
                return
            active = bool(payload.get("active", True))
            ok = toggle_recipient(target_id, active)
            self._send_json({"ok": ok, "recipients": get_recipients()})
            return

        if path == "/api/recipients/delete":
            target_id = payload.get("id", "").strip()
            if not is_valid_target_id(target_id):
                self._send_json({"ok": False, "error": "รูปแบบ ID ไม่ถูกต้อง"}, status=400)
                return
            ok = remove_recipient(target_id)
            self._send_json({"ok": ok, "recipients": get_recipients()})
            return

        if path == "/api/test-send":
            target_id = payload.get("id", "").strip()
            if target_id and not is_valid_target_id(target_id):
                self._send_json({"ok": False, "error": "รูปแบบ ID ผู้รับไม่ถูกต้อง"}, status=400)
                return

            from line_api import LineClient
            if not WebState.token:
                self._send_json({"ok": False, "error": "ไม่มี LINE_CHANNEL_ACCESS_TOKEN ในระบบ"}, status=400)
                return

            targets = [target_id] if target_id else get_active_target_ids()
            if not targets:
                self._send_json({"ok": False, "error": "ไม่มีผู้รับที่ระบุ หรือไม่มีผู้รับที่เปิดใช้งานอยู่"}, status=400)
                return

            client = LineClient(WebState.token, targets)
            default_msg = (
                f"🔔 ทดสอบการแจ้งเตือนจากระบบสรุปการมาทำงาน\n"
                f"เวลาทดสอบ: {datetime.now().strftime('%H:%M:%S')}\n"
                f"ระบบพร้อมส่งสรุปเวลา {', '.join(t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t) for t in WebState.send_times)} น."
            )
            raw_text = payload.get("text")
            test_msg = sanitize_message(raw_text) if raw_text else default_msg

            try:
                client.send_text(test_msg)
                self._send_json({"ok": True, "message": f"ส่งข้อความทดสอบไปยัง {len(targets)} รายการเรียบร้อยแล้ว"})
            except Exception as e:
                log.exception("ส่งข้อความทดสอบล้มเหลว: %s", e)
                self._send_json({"ok": False, "error": str(e)}, status=500)
            return

        if path == "/api/send-now":
            from main import run_once
            targets = get_active_target_ids()
            if not targets:
                self._send_json({"ok": False, "error": "ไม่มีผู้รับที่เปิดใช้งานอยู่ในระบบ กรุณาเพิ่ม User ID ก่อน"}, status=400)
                return

            if not WebState.token:
                self._send_json({"ok": False, "error": "ไม่มี LINE_CHANNEL_ACCESS_TOKEN ในระบบ"}, status=400)
                return

            try:
                run_once(WebState.db, WebState.token, date.today(), dry_run=False)
                WebState.last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                WebState.last_run_status = "ส่งสำเร็จ (กดส่งเอง)"
                self._send_json({"ok": True, "message": f"ส่งสรุปประจำวันไปยัง {len(targets)} รายการเรียบร้อยแล้ว"})
            except Exception as e:
                log.exception("กดส่งตอนนี้ล้มเหลว: %s", e)
                WebState.last_run_error = str(e)
                self._send_json({"ok": False, "error": str(e)}, status=500)
            return

        self.send_error(404, "Not Found")


def run_web_server(db, token, send_times, port=8090):
    WebState.db = db
    WebState.token = token
    WebState.send_times = send_times

    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), RequestHandler)
        log.info("🌐 Web UI พร้อมใช้งานที่ http://0.0.0.0:%d", port)
        server.serve_forever()
    except Exception as e:
        log.error("❌ ไม่สามารถเริ่ม Web Server บนพอร์ต %d ได้: %s", port, e)
