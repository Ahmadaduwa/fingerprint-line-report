# Specification: STW_TeacherCheck — Real DB & LINE Auto-Webhook Integration

## 1. Objectives
ทำให้ระบบ `STW_TeacherCheck` (Go Edition) เชื่อมต่อฐานข้อมูล SQL Server จริง (ทั้งบนเครื่อง Windows 7 32-bit และ Docker `hip_sqlserver`) และเชื่อมต่อ LINE Messaging API (`@143smwig` / `STW_FaceCheck`) พร้อมตั้งค่า Webhook อัตโนมัติผ่าน Cloudflare Tunnel รุ่นรองรับ Windows 7 32-bit โดยที่ผู้ใช้ไม่ต้องตั้งค่าด้วยมือ

## 2. Root Causes Identified
1. **SQL Server TLS 1.0 Rejection (`protocol version 301`)**:
   - SQL Server 2012 บน Windows 7 บังคับเข้ารหัส Login Packet ด้วย TLS 1.0 (`0x0301`)
   - Go 1.20 ปฏิเสธ TLS 1.0 เว้นแต่จะระบุ `encrypt=disable` หรือตั้งค่า `MinVersion: tls.VersionTLS10`
2. **SQL Query Placeholder Bug**:
   - `GetScans()` ใน `go-stw/db/database.go` ใช้ `WHERE adddate >= ?` แต่ driver `"sqlserver"` ของ `go-mssqldb` ต้องใช้ `@p1`
3. **Config & Reconnect Bugs**:
   - `config/settings.go` บังคับเขียนทับ `DBHost` และ `DBAuth`
   - `POST /api/settings` บันทึกไฟล์แต่ไม่เรียก `initDB()` เพื่อเชื่อมต่อใหม่
   - `GET /api/status` ตอบ `db_connected: true` เสมอแม้ Query จะล้มเหลว
4. **LINE Webhook & Windows 7 32-bit Cloudflare Tunnel**:
   - `cloudflared` รุ่นล่าสุดคอมไพล์ด้วย Go 1.21+ ซึ่งเรียก `ProcessPrng` ที่ไม่มีใน Windows 7
   - ผู้ใช้ไม่สะดวกก๊อปปี้ URL `trycloudflare.com` ไปวางใน LINE Developers Console ทุกครั้งที่เปิดเครื่อง

## 3. Technical Design

### 3.1 Database Connection (`go-stw/db/database.go`)
- เพิ่ม `encrypt=disable;trustservercertificate=true` ใน `buildConnString()` เพื่อข้าม TLS Handshake บน SQL Server 2012 (Windows 7) และรองรับ SQL Server 2019 (`hip_sqlserver`)
- แก้ SQL Query ใน `GetScans()` ให้ใช้ `@p1` แทน `?`
- เพิ่มระบบ **Auto-Discovery / Fallback** ใน `Connect()`:
  - ทดสอบ `Ping()` จริงทุกครั้ง
  - หากเชื่อมต่อด้วยค่าที่ตั้งไว้ไม่สำเร็จ ให้ลองสลับชื่อฐานข้อมูล (`Synctime`, `hiptime`) และสลับโหมดการยืนยันตัวตนอัตโนมัติ
- เมื่อกดบันทึกตั้งค่าในหน้าเว็บ (`POST /api/settings`) ให้สั่ง Reconnect DB ทันที และรายงานสถานะ `db_connected` ตามผล Query จริง

### 3.2 LINE API & Auto-Webhook (`go-stw/line/client.go` & `go-stw/tunnel/tunnel.go`)
- รองรับการอ่านค่า `LINE_CHANNEL_ACCESS_TOKEN` จากไฟล์ `.env` หรือตั้งค่าผ่านหน้าเว็บโดยแอดมิน (ไม่ฝัง Token ในโค้ดเพื่อความปลอดภัยของ Public Repo)
- เพิ่มฟังก์ชันใน `line.Client`:
  - `SetWebhookEndpoint(url string) error` (`PUT https://api.line.me/v2/bot/channel/webhook/endpoint`)
  - `GetWebhookEndpoint() (string, bool, error)` (`GET https://api.line.me/v2/bot/channel/webhook/endpoint`)
  - `BroadcastText(text string) error` (`POST https://api.line.me/v2/bot/message/broadcast`) สำหรับส่งหาเพื่อนทุกคนของบอทเมื่อยังไม่มีผู้รับเฉพาะเจาะจง
- สร้างแพ็กเกจ `tunnel`:
  - รัน `cloudflared tunnel --url http://127.0.0.1:8090 --no-autoupdate` ใน Background
  - ดักจับ URL `https://xxxx.trycloudflare.com` จาก Log แล้วเรียก `lineClient.SetWebhookEndpoint("https://xxxx.trycloudflare.com/webhook")` อัตโนมัติทันที
  - บันทึกไฟล์ `cloudflared.exe` รุ่น **2023.8.2 (32-bit x86, Go 1.20)** ที่รันบน Windows 7 32-bit ได้จริงลงใน `release-windows7/cloudflared.exe` พร้อม `--no-autoupdate`
